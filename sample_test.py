import json
from app.engine.core import recommend_crops, load_data

# 1. Initialize System
load_data()

# 2. Test Input (Kannada)
input_payload = {
    "latitude": 13.34,
    "longitude": 74.74,
    "date": "2026-06-15",
    "language": "kn"
}

# 3. Get Output
result = recommend_crops(
    lat=input_payload['latitude'],
    long=input_payload['longitude'],
    date_str=input_payload['date'],
    language=input_payload['language']
)

# 4. Print results
print("--- 📥 INPUT ---")
print(json.dumps(input_payload, indent=2))
print("\n--- 📤 OUTPUT (Snippet) ---")
# Just show the first recommendation for clarity
if result.get('recommendations'):
    sample = result['recommendations'][0]
    output_snippet = {
        "context": result['context'],
        "recommendations": [sample]
    }
    print(json.dumps(output_snippet, indent=2, ensure_ascii=False))
else:
    print(json.dumps(result, indent=2))
