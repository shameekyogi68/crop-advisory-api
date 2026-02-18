import json
from app.engine.core import recommend_crops, load_data

# 1. Initialize System
print("Initializing System...")
load_data()  # Load CSVs from app/data/

# 2. Define PERFECT INPUT
# Scenario: Udupi (Coastal), June 15 (Start of Kharif/Monsoon)
# Note: Irrigation access param removed. Returns ALL suitable crops.
input_payload = {
    "latitude": 13.34,
    "longitude": 74.74,
    "date": "2026-06-15"
}

print("\n--- 📥 INPUT (JSON Payload) ---")
print(json.dumps(input_payload, indent=2))

# 3. Get OUTPUT
print("\n--- 🔄 PROCESSING ---")
result = recommend_crops(
    lat=input_payload['latitude'],
    long=input_payload['longitude'],
    date_str=input_payload['date']
)

# 4. Show PERFECT OUTPUT (Bilingual Advisory)
print("\n--- 📤 OUTPUT (JSON Response) ---")
print(json.dumps(result, indent=2, ensure_ascii=False))

print("\n--- 🌾 FARMER ADVISORY (Flat Bilingual View) ---\n")
if 'recommendations' in result and result['recommendations']:
    for r in result['recommendations']:
        cname = r.get('crop_name')
        season = r.get('season')
        guide = r.get('farming_guide', {})
        advisory = r.get('advisory', {}).get('en') # Simple string
        
        print(f"Crop: {cname} ({season})")
        print(f"   Advisory: {advisory}")
        print("   📖 Guide:")
        print(f"      - Duration: {guide.get('duration', {}).get('en')} / {guide.get('duration', {}).get('kn')}")
        print(f"      - Yield: {guide.get('yield_est', {}).get('en')} / {guide.get('yield_est', {}).get('kn')}")
        print(f"      - Water: {r.get('water_requirement', {}).get('en')} / {r.get('water_requirement', {}).get('kn')}")
        print(f"      - Spacing: {guide.get('spacing', {}).get('en')} / {guide.get('spacing', {}).get('kn')}")
        print("-" * 40)
else:
    print("No recommendations found.")
