import sys
import os
from pathlib import Path

# Add root to sys.path to find 'app'
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.engine.core import recommend_crops, load_data

# Initialize Data
try:
    load_data()
except Exception as e:
    print(f"Stats: Data load skipped/failed: {e}")

# Test Scenarios designed to stress test the logic
scenarios = [
    {
        "name": "Scenario 1A: Brahmavara - Summer",
        "lat": 13.42, "long": 74.72, "date": "2025-04-10"
    },
    {
        "name": "Scenario 2: Karkala - Kharif",
        "lat": 13.22, "long": 74.98, "date": "2025-07-20"
    },
    {
        "name": "Scenario 4: Transition - Late Summer/Kharif Prep (May 25)",
        "lat": 13.35, "long": 74.75, "date": "2025-05-25"
    }
]

print("=== REAL WORLD VALIDATION REPORT V2 ===")
for sc in scenarios:
    print(f"\nRunning {sc['name']}...")
    try:
        # Pass new irrigation flag
        res = recommend_crops(sc['lat'], sc['long'], sc['date'])
        
        # Analyze Result
        if "error" in res:
            print(f"❌ ERROR: {res['error']}")
            continue
            
        ctx = res['context']
        recs = res['recommendations']
        
        print(f"📍 Location: {ctx['location']}")
        print(f"🗓️ Season: {ctx.get('seasons_detected', 'Unknown')}")
        print(f"🌾 Crops Found: {len(recs)}")
        
        if len(recs) > 0:
            # Print top crops to verify filtering
            for r in recs:
                # Highlight if it's an advisory result
                crop_name = r.get('crop_name', 'Unknown')
                adv_text = r.get('advisory', {}).get('en', 'No Advisory')
                
                print(f"   - {crop_name} | Advisory: {adv_text}")
        else:
            print("⚠️ No crops found!")
            
    except Exception as e:
        print(f"🔥 CRITICAL FAILURE: {e}")
