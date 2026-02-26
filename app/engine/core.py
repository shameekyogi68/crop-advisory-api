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


def get_soil_profile(taluk_data, soil_type):
    """Generates the bilingual Soil Profile object."""
    sp = {}
    # Nutrients from Taluk Profile
    for nutrient in ['nitrogen', 'phosphorus', 'potassium', 'zinc', 'boron', 'iron', 'sulphur']:
        status_key = f"{nutrient}_class"
        status_val = taluk_data.get(status_key, 'medium')
        sp[nutrient] = get_bilingual(status_val)
    
    # pH
    ph_class = taluk_data.get('ph_class', 'neutral')
    sp['ph_status'] = get_bilingual(ph_class)
    sp['ph_value'] = 6.5 # Default or derived average
    
    # Type
    sp['type'] = get_bilingual(soil_type)
    
    return sp

def generate_advisory_content(crop_name, soil_type):
    """Generates dynamic advisory content (Alerts, Tips, Checklist)."""
    # Alerts
    alerts = [
        get_bilingual("weather_good"),
        get_bilingual("gps_mode")
    ]
    if "Zinc" in get_text("zinc", "en"): # Dummy check logic
        alerts.append(get_bilingual("zinc_warning"))
        
    # Management Tips
    tips = [
        get_bilingual("plough_deep"),
        get_bilingual("green_manure"),
        get_bilingual("stubble")
    ]
    
    # Soil Health Checklist
    checklist = {
        "crop_suitability": {
            "score": get_bilingual("medium"),
            "warnings": [get_bilingual("sandy_loss")] if 'sandy' in soil_type.lower() else []
        },
        "drainage": get_bilingual("drainage_excess") if 'sandy' in soil_type.lower() else get_bilingual("normal"),
        "erosion": get_bilingual("erosion_risk"),
        "moisture": get_bilingual("low_moisture") if 'sandy' in soil_type.lower() else get_bilingual("medium")
    }
    
    return alerts, tips, checklist

def generate_shopping_list(crop_name):
    """Generates a sample fertilizer shopping list."""
    # Logic placeholders conform to the user's example
    return [
        {"bags": 2, "loose_kg": 26.4, "name": get_bilingual("urea"), "qty_display": {"en": "2 Bags + 26.4 kg", "kn": "2 ಬ್ಯಾಗ್ + 26.4 ಕೆ.ಜಿ"}},
        {"bags": 0, "loose_kg": 44.7, "name": get_bilingual("dap"), "qty_display": {"en": "44.7 kg (Loose)", "kn": "44.7 ಕೆ.ಜಿ (ಬಿಡಿ)"}},
        {"bags": 1, "loose_kg": 47.2, "name": get_bilingual("mop"), "qty_display": {"en": "1 Bags + 47.2 kg", "kn": "1 ಬ್ಯಾಗ್ + 47.2 ಕೆ.ಜಿ"}},
        {"bags": 1, "loose_kg": 0.0, "name": get_bilingual("zinc_sulfate"), "qty_display": {"en": "1 Bags + 0.0 kg", "kn": "1 ಬ್ಯಾಗ್ + 0.0 ಕೆ.ಜಿ"}}
    ]

def generate_farming_guide(crop_data):
    """Generates the bilingual FarmingGuide object."""
    # 1. Duration
    days = crop_data.get('crop_duration_days', 0)
    months = round(days / 30, 1)
    
    label_days_en = get_text("days", "en")
    label_days_kn = get_text("days", "kn")
    label_approx_en = get_text("approx", "en")
    label_approx_kn = get_text("approx", "kn")
    label_months_en = get_text("months", "en")
    label_months_kn = get_text("months", "kn")
    
    dur_en = f"{int(days)} {label_days_en} ({label_approx_en} {months} {label_months_en})"
    dur_kn = f"{int(days)} {label_days_kn} ({label_approx_kn} {months} {label_months_kn})"
    
    # 2. Water
    w_req = crop_data.get('water_requirement', 'Medium')
    if w_req == 'High':
        wat_en = get_text("needs_water_high", "en")
        wat_kn = get_text("needs_water_high", "kn")
    elif w_req == 'Low':
        wat_en = get_text("needs_water_low", "en")
        wat_kn = get_text("needs_water_low", "kn")
    else:
        wat_en = get_text("needs_water_medium", "en")
        wat_kn = get_text("needs_water_medium", "kn")

    # 3. Yield
    yld = crop_data.get('average_yield_per_acre', 0)
    unit = crop_data.get('yield_unit', 'quintal')
    
    # Map units if possible
    unit_key = "quintal_acre" if "quintal" in unit.lower() else "tons_acre"
    unit_en = get_text(unit_key, "en")
    unit_kn = get_text(unit_key, "kn")
    
    yld_label_en = get_text("expected_yield", "en")
    yld_label_kn = get_text("expected_yield", "kn")
    
    yld_en = f"{yld_label_en}: {yld} {unit_en}"
    yld_kn = f"{yld_label_kn}: {yld} {unit_kn}"

    # 4. Spacing
    row = crop_data.get('spacing_row_cm', 0)
    plant = crop_data.get('spacing_plant_cm', 0)
    label_cm_en = get_text("spacing_cm", "en")
    label_cm_kn = get_text("spacing_cm", "kn")
    
    if row > 0:
        spac_en = f"{row}x{plant} {label_cm_en}"
        spac_kn = f"{row}x{plant} {label_cm_kn}"
    else:
        spac_en = get_text("standard_spacing", "en")
        spac_kn = get_text("standard_spacing", "kn")

    # 5. Maintenance
    diff = crop_data.get('management_difficulty', 'Medium')
    inp = crop_data.get('input_requirement', 'Medium')
    
    diff_en = get_text(diff, "en")
    diff_kn = get_text(diff, "kn")
    inp_en = get_text(inp, "en")
    inp_kn = get_text(inp, "kn")
    
    label_diff_en = get_text("difficulty", "en")
    label_diff_kn = get_text("difficulty", "kn")
    label_inp_en = get_text("inputs", "en")
    label_inp_kn = get_text("inputs", "kn")
    
    maint_en = f"{diff_en} {label_diff_en}, {inp_en} {label_inp_en}."
    maint_kn = f"{diff_kn} {label_diff_kn}, {inp_kn} {label_inp_kn}."

    return {
        "duration": {"en": dur_en, "kn": dur_kn},
        "water": {"en": wat_en, "kn": wat_kn},
        "yield_est": {"en": yld_en, "kn": yld_kn},
        "suitability": get_bilingual("good_season"),
        "spacing": {"en": spac_en, "kn": spac_kn},
        "maintenance": {"en": maint_en, "kn": maint_kn}
    }

def recommend_crops(lat, long, date_str, language=None):
    """
    Main Engine Function (Bilingual Advisory Version).
    """

    # ... (Keep existing setup) ...
    # [Pre-amble same as before]

    if _df_map is None or _df_db is None:
        raise RuntimeError("Data not loaded. Call load_data() first.")

    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return {"error": "Invalid date format. Use YYYY-MM-DD."}
        
    target_seasons = get_season(date_obj)
    zone_info = get_zone(lat, long)
    
    if zone_info is None or zone_info.empty:
        return {
            "error": "Location not covered by agronomic map.",
            "location": {"lat": lat, "long": long}
        }

    taluk = zone_info['Division']
    zone_name = zone_info['Zone_Name']
    zone_type = "coastal" if "Coastal" in zone_name else "hinterland"
    
    taluk = zone_info['Division']
    zone_name = zone_info['Zone_Name']
    zone_type = "coastal" if "Coastal" in zone_name else "hinterland"
    
    # Use cached data
    taluk_data = _taluk_data.get(taluk, {}) if _taluk_data else {}
    
    all_recs = []
    
    relevant_crops = _df_map[
        (_df_map['Division'] == taluk) &
        (_df_map['Zone_Name'] == zone_name) &
        (_df_map['Season'].isin(target_seasons + ['Year-round', 'Perennial']))
    ].copy()
    
    for _, row in relevant_crops.iterrows():
        crop_name = row['Crop']
        variety = row['Variety']
        full_name = f"{crop_name} ({variety})" if pd.notna(variety) and variety else crop_name
        
        db_row = {}
        matched_db = _df_db[_df_db['crop_name'] == full_name]
        if matched_db.empty:
             matched_db = _df_db[_df_db['crop_name'].str.contains(crop_name, regex=False, na=False)]
        
        if not matched_db.empty:
            db_row = matched_db.iloc[0].to_dict()
        else:
            # Fallback for keys needed by formatting
            db_row = {
                'crop_duration_days': 120, 
                'water_requirement': 'Medium', 
                'average_yield_per_acre': 0,
                'yield_unit': 'quintal',
                'spacing_row_cm': 0,
                'spacing_plant_cm': 0,
                'management_difficulty': 'Medium',
                'input_requirement': 'Medium'
            }
        
        crop_display_name = full_name
        soil_type_input = taluk_data.get('soil_texture_class', 'Red Soil') 
        
        # Generator Calls
        farming_guide_obj = generate_farming_guide(db_row)
        
        # Advisory Text (Simple Bilingual)
        advisory_obj = {
            "en": "Optimal.",
            "kn": "ಪರಿಪೂರ್ಣ."
        }
        
        # Water Requirement (Bilingual)
        w_req_val = db_row.get('water_requirement', 'Medium')
        w_req_obj = {
            "en": w_req_val,
            "kn": get_text(w_req_val, "kn") if get_text(w_req_val, "kn") != w_req_val else w_req_val # Fallback logic or map explicitly
        }
        # explicit map for High/Medium/Low if not in dict
        if w_req_val == 'High': w_req_obj['kn'] = "ಹೆಚ್ಚು"
        elif w_req_val == 'Medium': w_req_obj['kn'] = "ಮಧ್ಯಮ"
        elif w_req_val == 'Low': w_req_obj['kn'] = "ಕಡಿಮೆ"

        rec_data = {
            "crop_name": crop_display_name,
            "season": row['Season'],
            "advisory": advisory_obj,
            "farming_guide": farming_guide_obj,
            "water_requirement": w_req_obj,
            
            # Technical Fields
            "crop_id": db_row.get('crop_id', 'Unknown'),
            "crop_category": db_row.get('crop_category', 'Unknown'),
            "crop_duration_days": int(db_row.get('crop_duration_days', 0)),
            "harvest_type": db_row.get('harvest_type', 'Single'),
            "growth_type": db_row.get('growth_type', 'Annual'),
            "root_depth": db_row.get('root_depth', 'Shallow'),
            "plant_type": db_row.get('plant_type', 'Erect'),
            "spacing_row_cm": float(db_row.get('spacing_row_cm', 0)),
            "spacing_plant_cm": float(db_row.get('spacing_plant_cm', 0)),
            "suitable_for_intercrop": db_row.get('suitable_for_intercrop', 'No'),
            "management_difficulty": db_row.get('management_difficulty', 'Medium'),
            "input_requirement": db_row.get('input_requirement', 'Medium'),
            "average_yield_per_acre": float(db_row.get('average_yield_per_acre', 0)),
            "yield_unit": db_row.get('yield_unit', 'quintal'),
            "zone_source": "Agronomic Map"
        }
        
        all_recs.append(rec_data)

    # Dedupe by crop name
    unique_recs = []
    seen_crops = set()
    for r in all_recs:
        cname = r['crop_name']
        if cname not in seen_crops:
             unique_recs.append(r)
             seen_crops.add(cname)

    # Apply final localization if language selected
    return localize({
        "context": {
            "location": f"{taluk} - {zone_name}",
            "coordinates": {"lat": lat, "long": long},
            "seasons_detected": target_seasons,
            "date": date_str,
            "language": language
        },

        "recommendations": unique_recs
    }, language)

