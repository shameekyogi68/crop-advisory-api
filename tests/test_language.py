import sys
import os
from pathlib import Path

# Add root directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import get_recommendation
from app.models import CropRecommendationRequest
from app.engine.core import load_data

def test_language_selection():
    load_data()
    print("--- 🧪 Testing Language Selection ---")

    # 1. Test English
    req_en = CropRecommendationRequest(latitude=13.34, longitude=74.74, date="2026-06-15", language="en")
    res_en = get_recommendation(req_en)
    
    first_rec_en = res_en['recommendations'][0]
    expected_keys = ['crop_name', 'season', 'advisory', 'farming_guide', 'water_requirement']
    
    print("\n[Case 1: English]")
    if isinstance(first_rec_en['advisory'], str):
        print("✅ Advisory is a flat string")
    else:
        print(f"❌ Advisory is unexpected type: {type(first_rec_en['advisory'])}")

    if isinstance(first_rec_en['farming_guide']['duration'], str):
        print("✅ Farming Guide fields are flat strings")
    else:
        print("❌ Farming Guide fields are not flat strings")

    # 2. Test Kannada
    req_kn = CropRecommendationRequest(latitude=13.34, longitude=74.74, date="2026-06-15", language="kn")
    res_kn = get_recommendation(req_kn)
    first_rec_kn = res_kn['recommendations'][0]
    
    print("\n[Case 2: Kannada]")
    if "ಪರಿಪೂರ್ಣ" in first_rec_kn['advisory']: # 'Optimal' in Kannada
        print("✅ Received Kannada text in Advisory")
    else:
        print(f"❌ Expected Kannada text, got: {first_rec_kn['advisory']}")

    # 3. Test Bilingual (Default)
    req_bi = CropRecommendationRequest(latitude=13.34, longitude=74.74, date="2026-06-15")
    res_bi = get_recommendation(req_bi)
    first_rec_bi = res_bi['recommendations'][0]
    
    print("\n[Case 3: Bilingual (Default)]")
    if isinstance(first_rec_bi['advisory'], dict) and 'en' in first_rec_bi['advisory']:
        print("✅ Advisory is a bilingual dictionary")
    else:
        print(f"❌ Advisory is not a bilingual dict: {first_rec_bi['advisory']}")

if __name__ == "__main__":
    test_language_selection()
