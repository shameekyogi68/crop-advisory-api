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

# 4. Show PERFECT OUTPUT (With Farming Guide)
print("\n--- 📤 OUTPUT (JSON Response) ---")
print(json.dumps(result, indent=2))

print("\n--- 🌾 FARMER FRIENDLY VIEW ---")
if 'recommendations' in result and result['recommendations']:
    for r in result['recommendations']:
        guide = r.get('farming_guide', {})
        print(f"\nCrop: {r['crop_name']}")
        print(f"   ⏳ Duration: {guide.get('duration', 'N/A')}")
        print(f"   💧 Water: {guide.get('water', 'N/A')}")
        print(f"   💰 Yield: {guide.get('yield_est', 'N/A')}")
        print(f"   📏 Spacing: {guide.get('spacing', 'N/A')}")
        print(f"   🛠️ Maintenance: {guide.get('maintenance', 'N/A')}")
else:
    print("No recommendations found.")
