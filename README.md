# Crop Recommendation API

A precise, zone-specific crop recommendation engine for Udupi district, deployed via FastAPI.

## Structure
- **`app/`**: Production Source Code
  - `main.py`: API Server
  - `engine/`: Logic Core
  - `data/`: Curated Datasets
- **`datasets/`**: Original Raw Data (Source)
- **`docs/`**: Engineering & Agronomic Audit Reports
- **`tests/`**: Verification Scripts
- `render.yaml`: Deployment Config


## Local Development
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Run server:
   ```bash
   uvicorn app.main:app --reload
   ```
3. Test:
   ```bash
   curl -X POST "http://127.0.0.1:8000/recommend" -H "Content-Type: application/json" -d '{"latitude": 13.34, "longitude": 74.74, "date": "2026-06-15", "irrigation_access": true}'
   ```
