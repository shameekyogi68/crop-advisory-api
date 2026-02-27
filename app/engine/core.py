import pandas as pd
from datetime import datetime
import json
import os
from pathlib import Path

# --- Configuration ---
# Use pathlib to find data relative to THIS file
BASE_DIR = Path(__file__).resolve().parent.parent # Points to app/
DATA_DIR = BASE_DIR / 'data'

# Allow module to load data once
_df_map = None
_df_db = None
_taluk_data = None

def load_data(map_path=None, db_path=None, json_path=None):
    """
    Loads data into global variables. 
    Designed to be called on API Startup.
    """
    global _df_map, _df_db, _taluk_data
    
    if map_path is None:
        map_path = DATA_DIR / 'final_map.csv'
    if db_path is None:
        db_path = DATA_DIR / 'crop_db.csv'
    if json_path is None:
        json_path = DATA_DIR / 'taluk_profiles/taluk_profiles.json'
        
    try:
        _df_map = pd.read_csv(map_path)
        _df_db = pd.read_csv(db_path)
        # Ensure IDs are strings
        _df_db['crop_id'] = _df_db['crop_id'].astype(str)
        
        if os.path.exists(json_path):
             with open(json_path, 'r') as f:
                 _taluk_data = json.load(f)
        else:
            print(f"Warning: Taluk Profiles not found at {json_path}")
            _taluk_data = {}

        print(f"Data Loaded Successfully. Map: {len(_df_map)} rows, DB: {len(_df_db)} rows, Profiles: {len(_taluk_data)} taluks.")
    except Exception as e:
        print(f"Critical Error loading data: {e}")
        raise e

# --- Core Logic ---

def get_season(date_obj):
    """
    Determines agricultural season(s) based on date.
    Returns a LIST of seasons to handle transitions.
    """
    month = date_obj.month
    day = date_obj.day
    
    seasons = []
    
    # Primary Season Logic
    if 6 <= month <= 9:
        seasons.append('Kharif')
    elif 10 <= month <= 12 or month == 1:
        seasons.append('Rabi') 
    else: # 2 to 5
        seasons.append('Summer')
    
    # Transition Logic (Lookahead)
    # May 15-31: End of Summer, Start of Kharif Prep
    if month == 5 and day >= 15:
        seasons.append('Kharif')
        
    # Sept 15-30: End of Kharif, Start of Rabi
    if month == 9 and day >= 15:
        seasons.append('Rabi')
        
    # Jan 15-31: End of Rabi, Start of Summer
    if month == 1 and day >= 15:
        seasons.append('Summer')
        
    # Dedupe but preserve order: [Primary, Transition]
    unique_seasons = []
    for s in seasons:
        if s not in unique_seasons:
            unique_seasons.append(s)
            
    return unique_seasons

def parse_lat_long_range(rule):
    """Parses '13.20-13.30' into (13.20, 13.30). Returns None if invalid."""
    try:
        if '-' in rule:
            parts = rule.split('-')
            return float(parts[0]), float(parts[1])
        elif '<' in rule:
            val = float(rule.replace('<', '').strip())
            return -999.0, val
        elif '>' in rule:
            val = float(rule.replace('>', '').strip())
            return val, 999.0
        return None
    except:
        return None

def get_zone(lat, long):
    """Finds matching Zone"""
    if _df_map is None:
        raise RuntimeError("Data not loaded. Call load_data() first.")

    zones = _df_map[['Division', 'Zone_Name', 'Lat_Rule', 'Long_Rule']].drop_duplicates()
    matched_zones = []
    
    for _, row in zones.iterrows():
        lat_range = parse_lat_long_range(row['Lat_Rule'])
        long_range = parse_lat_long_range(row['Long_Rule'])
        
        if lat_range and long_range:
            if (lat_range[0] <= lat <= lat_range[1]) and (long_range[0] <= long <= long_range[1]):
                matched_zones.append(row)
                
    if not matched_zones:
        return None
    return matched_zones[0]

# Sowing Windows
SOWING_WINDOWS = {
    'Kharif': {'start': (5, 25), 'end': (8, 15)}, 
    'Rabi': {'start': (9, 15), 'end': (11, 30)},
    'Summer': {'start': (1, 15), 'end': (2, 28)}
}

NEXT_SEASON = {
    'Summer': 'Kharif',
    'Kharif': 'Rabi',
    'Rabi': 'Summer'
}

def check_sowing_window(season, date_obj):
    if season not in SOWING_WINDOWS:
        return 'Optimal', '' 
        
    win = SOWING_WINDOWS[season]
    m, d = date_obj.month, date_obj.day
    current_md = (m, d)
    start_md = win['start']
    end_md = win['end']
    
    if start_md <= current_md <= end_md:
        return 'Optimal', f"Optimal sowing window for {season}."
    elif current_md > end_md:
        return 'Closed', f"Sowing window for {season} closed approx {end_md[1]}/{end_md[0]}."
    else:
        return 'Early', f"Early for {season}."

from .localization import get_bilingual, get_text

def localize(data, lang=None):
    """
    Helper to transform bilingual dict to flat string if lang is provided.
    Works on strings, lists, and dicts recursively.
    """
    if lang is None:
        return data
        
    if isinstance(data, dict):
        if lang in data and len(data) <= 3: # Likely a bilingual dict {"en":..., "kn":...}
            return data[lang]
        return {k: localize(v, lang) for k, v in data.items()}
    elif isinstance(data, list):
        return [localize(item, lang) for item in data]
    return data


def get_static_knowledge(crop_data, language=None):
    """
    Constructs the static knowledge structure from crop database row.
    """
    crop_name = crop_data.get('crop_name', 'Unknown')
    # Variety is usually in parentheses in crop_name: "Paddy (MO-4)"
    variety = "Generic"
    base_name = crop_name
    if '(' in crop_name and ')' in crop_name:
        parts = crop_name.split('(')
        base_name = parts[0].strip()
        variety = parts[1].replace(')', '').strip()

    # Derived fields based on agronomic standards for the region (Udupi/Zone 10)
    # This logic maps available CSV fields to the new structured response
    
    # 1. Identity
    identity = {
        "crop_name": get_bilingual(base_name),
        "variety_name": get_bilingual(variety),
        "crop_category": get_bilingual(crop_data.get('crop_category', 'Cereal'))
    }

    # 2. Agro Climatic Suitability
    # Defaults for Zone 10
    temp_range = "20°C - 35°C"
    rain_range = "1000mm - 4000mm" if base_name == "Paddy" else "500mm - 1500mm"
    soil_types = "Coastal Alluvium, Lateritic" if base_name == "Paddy" else "Red Soil, Loamy"
    ph_range = "4.0 - 7.0"

    agro = {
        "suitable_temperature_range": get_bilingual(temp_range),
        "suitable_rainfall_range": get_bilingual(rain_range),
        "suitable_soil_types": get_bilingual(soil_types),
        "suitable_soil_ph_range": get_bilingual(ph_range)
    }

    # 3. Morphological
    height = "90cm - 120cm" if base_name == "Paddy" else "45cm - 60cm"
    habit = crop_data.get('plant_type', 'Erect')
    root = crop_data.get('root_depth', 'Shallow')
    
    # Use localized terms for dynamic values
    days_val = crop_data.get('crop_duration_days', 120)
    duration_en = f"{days_val} Days"
    duration_kn = f"{days_val} ದಿನಗಳು"
    duration = {"en": duration_en, "kn": duration_kn}

    morph = {
        "plant_height_range": get_bilingual(height),
        "growth_habit": get_bilingual(habit),
        "root_system_type": get_bilingual(root),
        "maturity_duration_range": duration
    }

    # 4. Seed Specs
    seed_rate = "25-30 kg" if base_name == "Paddy" else "5-10 kg"
    germ = "4 - 7 Days"
    viability = "6 - 9 Months"

    seed = {
        "seed_rate_per_acre": get_bilingual(seed_rate),
        "germination_period": get_bilingual(germ),
        "seed_viability_period": get_bilingual(viability)
    }

    # 5. Yield
    yield_val = crop_data.get('average_yield_per_acre', 0)
    unit = crop_data.get('yield_unit', 'quintal')
    unit_label_en = "quintal" if "quintal" in unit.lower() else unit
    unit_label_kn = "ಕ್ವಿಂಟಾಲ್" if "quintal" in unit.lower() else unit
    
    avg_yield_en = f"{yield_val} {unit_label_en}"
    avg_yield_kn = f"{yield_val} {unit_label_kn}"
    avg_yield = {"en": avg_yield_en, "kn": avg_yield_kn}

    y_range_min = yield_val * 0.8
    y_range_max = yield_val * 1.2
    y_range_en = f"{y_range_min:.1f} - {y_range_max:.1f} {unit_label_en}"
    y_range_kn = f"{y_range_min:.1f} - {y_range_max:.1f} {unit_label_kn}"
    y_range = {"en": y_range_en, "kn": y_range_kn}

    yield_pot = {
        "average_yield_per_acre": avg_yield,
        "yield_range_under_normal_conditions": y_range
    }

    # 6. Sensitivity
    sensitivity = {
        "drought_sensitivity_level": get_bilingual(crop_data.get('management_difficulty', 'Medium')),
        "waterlogging_sensitivity_level": get_bilingual("High" if base_name != "Paddy" else "Low"),
        "heat_tolerance_level": get_bilingual("Medium")
    }

    # 7. End Use
    end_use = {
        "main_use_type": get_bilingual("Food Grain" if base_name == "Paddy" else "Commercial"),
        "market_category": get_bilingual("Grade A")
    }

    knowledge = {
        "crop_id": str(crop_data.get('crop_id', 'Unknown')),
        "identity": identity,
        "agro_climatic_suitability": agro,
        "morphological_characteristics": morph,
        "seed_specifications": seed,
        "yield_potential": yield_pot,
        "sensitivity_profile": sensitivity,
        "end_use_information": end_use
    }

    return localize(knowledge, language)


def recommend_crops(lat, long, date_str, language=None):
    """
    Main Engine Function (Static Knowledge Version).
    """

    if _df_map is None or _df_db is None:
        raise RuntimeError("Data not loaded. Call load_data() first.")

    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return {"error": "Invalid date format. Use YYYY-MM-DD."}
        
    current_date_obj = date_obj
    primary_season = get_season(current_date_obj)[0]
    next_season = NEXT_SEASON.get(primary_season)
    
    # Check window for primary season
    status, message = check_sowing_window(primary_season, current_date_obj)
    
    target_seasons = []
    season_status = ""
    
    if status == 'Optimal' or status == 'Early':
        # Window is open or early, show Primary + Next
        target_seasons = [primary_season, next_season]
        season_status = f"{primary_season} Sowing Active. Also showing upcoming {next_season} crops."
    else:
        # status == 'Closed' -> Season Lost
        target_seasons = [next_season]
        season_status = f"{primary_season} Sowing Window is Closed (Season Lost). Showing {next_season} crops."

    zone_info = get_zone(lat, long)
    
    if zone_info is None or zone_info.empty:
        return {
            "error": "Location not covered by agronomic map.",
            "location": {"lat": lat, "long": long}
        }

    taluk = zone_info['Division']
    zone_name = zone_info['Zone_Name']
    
    # Use a dictionary to group by season
    grouped_recs = {s: [] for s in target_seasons}
    seen_crops = set() # To dedupe within/across seasons if needed
    
    # Search for crops in target seasons
    relevant_crops = _df_map[
        (_df_map['Division'] == taluk) &
        (_df_map['Zone_Name'] == zone_name) &
        (_df_map['Season'].isin(target_seasons + ['Year-round', 'Perennial']))
    ].copy()
    
    for _, row in relevant_crops.iterrows():
        crop_name = row['Crop']
        variety = row['Variety']
        season_name = row['Season']
        
        # Handle Year-round/Perennial by adding to primary season if possible
        target_season_key = season_name if season_name in target_seasons else primary_season
        
        full_name = f"{crop_name} ({variety})" if pd.notna(variety) and variety else crop_name
        
        # Dedupe key: (CropName, Variety, Season)
        dedupe_key = (crop_name, variety, season_name)
        if dedupe_key in seen_crops:
            continue
            
        db_row = {}
        matched_db = _df_db[_df_db['crop_name'] == full_name]
        if matched_db.empty:
             matched_db = _df_db[_df_db['crop_name'].str.contains(crop_name, regex=False, na=False)]
        
        if not matched_db.empty:
            db_row = matched_db.iloc[0].to_dict()
        else:
            db_row = {
                'crop_name': full_name,
                'crop_id': 'Unknown',
                'crop_category': 'Unknown',
                'crop_duration_days': 120,
                'average_yield_per_acre': 0,
                'yield_unit': 'quintal'
            }
        
        static_intel = get_static_knowledge(db_row, language)
        
        if target_season_key not in grouped_recs:
            grouped_recs[target_season_key] = []
            
        grouped_recs[target_season_key].append(static_intel)
        seen_crops.add(dedupe_key)

    return {
        "context": {
            "location": f"{taluk} - {zone_name}",
            "coordinates": {"lat": lat, "long": long},
            "seasons_detected": target_seasons,
            "season_status": season_status,
            "date": date_str,
            "language": language
        },
        "recommendations": grouped_recs
    }

