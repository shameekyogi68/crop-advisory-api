from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Any
from datetime import datetime

class CropRecommendationRequest(BaseModel):
    latitude: float = Field(..., ge=8.0, le=37.0, description="Latitude of the farm location")
    longitude: float = Field(..., ge=68.0, le=97.0, description="Longitude of the farm location")
    date: str = Field(..., description="Date of recommendation in YYYY-MM-DD format", pattern=r"^\d{4}-\d{2}-\d{2}$")

    @field_validator('date')
    def validate_date(cls, v):
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError("Incorrect date format, should be YYYY-MM-DD")
        return v

class FarmingGuide(BaseModel):
    duration: str = Field(..., description="Simple duration text (e.g. '4 months')")
    water: str = Field(..., description="Water need explanation")
    yield_est: str = Field(..., description="Estimated yield text")
    suitability: str = Field(..., description="Why this crop is suitable here")
    spacing: str = Field(..., description="Planting spacing")
    maintenance: str = Field(..., description="Effort/Input level")

class CropRecommendation(BaseModel):
    crop_name: str
    season: Optional[str] = None
    advisory: Optional[str] = None
    farming_guide: Optional[FarmingGuide] = None
    # Kept for backward compatibility but can be hidden if needed
    water_requirement: Optional[str] = None
    
    class Config:
        extra = "allow" 

class Context(BaseModel):
    location: str
    coordinates: dict
    seasons_detected: List[str]
    date: str

class RecommendationResponse(BaseModel):
    context: Context
    recommendations: List[CropRecommendation]
