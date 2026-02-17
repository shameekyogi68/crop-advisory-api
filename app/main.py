from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
from .models import RecommendationResponse, CropRecommendationRequest
from .engine.core import recommend_crops, load_data
import os

# --- Lifespan Manager (Startup/Shutdown) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load Data on Startup
    print("Loading Agricultural Data...")
    try:
        # We rely on core.py defaults which use relative paths
        load_data() 
    except Exception as e:
        print(f"Failed to load data: {e}")
    yield
    print("Shutting down...")

app = FastAPI(
    title="Agronomic Crop Recommendation API",
    description="Backend engine for precise, zone-specific crop advice.",
    version="1.0.0",
    lifespan=lifespan
)

@app.get("/health")
def health_check():
    return {"status": "active", "version": "1.0.0"}

@app.post("/recommend", response_model=RecommendationResponse)
def get_recommendation(request: CropRecommendationRequest):
    """
    Get crop recommendations based on location and date.
    
    - **latitude**: Farm latitude (e.g. 13.34)
    - **longitude**: Farm longitude (e.g. 74.74)
    - **date**: Recommendation date (YYYY-MM-DD)
    """
    
    result = recommend_crops(
        lat=request.latitude,
        long=request.longitude,
        date_str=request.date
    )
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result['error'])
        
    return result
