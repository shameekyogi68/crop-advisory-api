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

def load_data(map_path=None, db_path=None):
    """
    Loads data into global variables. 
    Designed to be called on API Startup.
    """
    global _df_map, _df_db
    
    if map_path is None:
        map_path = DATA_DIR / 'final_map.csv'
    if db_path is None:
        db_path = DATA_DIR / 'crop_db.csv'
        
    try:
        _df_map = pd.read_csv(map_path)
        _df_db = pd.read_csv(db_path)
        # Ensure IDs are strings
        _df_db['crop_id'] = _df_db['crop_id'].astype(str)
        print(f"Data Loaded Successfully. Map: {len(_df_map)} rows, DB: {len(_df_db)} rows.")
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

def format_farming_guide(crop_data):
    """
    Transforms raw agronomic data into farmer-friendly text.
    """
    # 1. Duration logic
    days = crop_data.get('crop_duration_days', 0)
    duration_text = "Unknown"
    if days > 0:
        months = round(days / 30, 1)
        duration_text = f"{int(days)} Days (approx {months} months)"
    
    # 2. Water logic
    w_req = crop_data.get('water_requirement', 'Medium')
    water_text = f"Requires {w_req} water."
    if w_req == 'High':
        water_text = "Needs abundant water (flood irrigation typically)."
    elif w_req == 'Low':
        water_text = "Drought tolerant. Needs minimal watering."
        
    # 3. Yield logic
    yld = crop_data.get('average_yield_per_acre', 0)
    unit = crop_data.get('yield_unit', 'units')
    yield_text = f"Expected yield: {yld} {unit}/acre"
    
    # 4. Suitability Summary
    # Simple logic based on inputs
    suitability = "Good for this season."

    # 5. Spacing
    row = crop_data.get('spacing_row_cm', 0)
    plant = crop_data.get('spacing_plant_cm', 0)
    spacing_text = f"{row}x{plant} cm" if row > 0 else "Standard spacing"

    # 6. Maintenance
    diff = crop_data.get('management_difficulty', 'Medium')
    inp = crop_data.get('input_requirement', 'Medium')
    maint_text = f"{diff} difficulty, {inp} inputs."
    
    return {
        "duration": duration_text,
        "water": water_text,
        "yield_est": yield_text,
        "suitability": suitability,
        "spacing": spacing_text,
        "maintenance": maint_text
    }

def recommend_crops(lat, long, date_str):
    """
    Main Engine Function.
    """
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
        
    all_recs = []
    
    primary_season = target_seasons[0] if target_seasons else None

    for season in target_seasons:
        sowing_status, sowing_msg = check_sowing_window(season, date_obj)
        
        relevant_crops = _df_map[
            (_df_map['Division'] == zone_info['Division']) &
            (_df_map['Zone_Name'] == zone_info['Zone_Name']) &
            (_df_map['Season'].isin([season, 'Year-round', 'Perennial']))
        ].copy()
        
        for _, row in relevant_crops.iterrows():
            crop_name = row['Crop']
            variety = row['Variety']
            full_name = f"{crop_name} ({variety})"
            
            # DB Lookup using Global DB
            profile = _df_db[_df_db['crop_name'] == full_name]
            if profile.empty:
                 profile = _df_db[_df_db['crop_name'].str.contains(crop_name, regex=False)]
            
            rec_data = {}
            if not profile.empty:
                 rec_data = profile.iloc[0].to_dict()
                 rec_data['zone_source'] = "Agronomic Map"
            else:
                rec_data = dict(row)
                rec_data['crop_name'] = full_name
                rec_data['message'] = "Profile pending"

            # --- FILTER REMOVED: User requested ALL crops regardless of irrigation ---
            # We assume user can arrange water or wants to know possibilities.

            # --- FILTER 2: SOWING WINDOW ---
            is_perennial = row['Season'] in ['Year-round', 'Perennial']
            advisory_parts = []
            
            if not is_perennial:
                if sowing_status == 'Closed':
                    duration = rec_data.get('crop_duration_days', 120)
                    if duration > 90:
                        continue 
                    else:
                        advisory_parts.append(f"Late Season (Catch Crop).")
                elif sowing_status == 'Early':
                    advisory_parts.append("Preparation Phase.")
            
            # Transition Context
            if len(target_seasons) > 1:
                if season in target_seasons[1:]: 
                     advisory_parts.append(f"PLANNING: Upcoming {season}.")
                elif season == target_seasons[0]:
                     if not advisory_parts: 
                         advisory_parts.append(f"Current Season.")

            rec_data['advisory'] = " ".join(advisory_parts) if advisory_parts else "Optimal."
            
            # --- FARMER FRIENDLY FORMATTING ---
            rec_data['farming_guide'] = format_farming_guide(rec_data)
            
            all_recs.append(rec_data)

    seen = set()
    unique_recs = []
    for r in all_recs:
        if r['crop_name'] not in seen:
            seen.add(r['crop_name'])
            unique_recs.append(r)
            
    return {
        "context": {
            "location": f"{zone_info['Division']} - {zone_info['Zone_Name']}",
            "coordinates": {"lat": lat, "long": long},
            "seasons_detected": target_seasons,
            "date": date_str
        },
        "recommendations": unique_recs 
    }
