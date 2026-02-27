import sys
import os
from pathlib import Path

# Add root directory to sys.path to allow importing 'app'
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from app.main import app, get_recommendation
    from app.models import CropRecommendationRequest
    from app.engine.core import load_data
    print("✅ Imports Successful")
except ImportError as e:
    print(f"❌ Import Failed: {e}")
    exit(1)

# Manually trigger load_data
try:
    # Adjust path for test script location
    # engine uses __file__ relative, so it should work if we run this script 
    # but we need to ensure we don't break relative paths.
    # Actually, load_data() handles this.
    load_data()
    print("✅ Data Loading Successful")
except Exception as e:
    print(f"❌ Data Loading Failed: {e}")
    exit(1)

# Test Request
req = CropRecommendationRequest(
    latitude=13.34, 
    longitude=74.74, 
    date="2025-06-15"
)

try:
    res = get_recommendation(req)
    if res['context']['seasons_detected'] == ['Kharif'] and len(res['recommendations']) > 0:
        print("✅ Recommendation Logic Successful")
        # Access via new nested structure
        rec = res['recommendations'][0]
        print(f"Sample: {rec['identity']['crop_name']}")
        print(f"Agro: {rec['agro_climatic_suitability']['suitable_soil_types']}")
    else:
        print("❌ Unexpected Result Logic")
        print(res)
except Exception as e:
    print(f"❌ Execution Failed: {e}")
    import traceback
    traceback.print_exc()
