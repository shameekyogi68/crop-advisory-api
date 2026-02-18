from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Any, Dict
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

class BilingualText(BaseModel):
    en: str
    kn: str

class SoilProfile(BaseModel):
    nitrogen: BilingualText
    phosphorus: BilingualText
    potassium: BilingualText
    ph_status: BilingualText
    ph_value: float
    organic_carbon: Optional[BilingualText] = None
    type: BilingualText
    zinc: Optional[BilingualText] = None
    boron: Optional[BilingualText] = None
    iron: Optional[BilingualText] = None
    sulphur: Optional[BilingualText] = None

class ShoppingItem(BaseModel):
    bags: int
    loose_kg: float
    name: BilingualText
    qty_display: BilingualText

class SummaryItem(BaseModel):
    label: BilingualText
    value: BilingualText

class SoilHealthChecklist(BaseModel):
    crop_suitability: Dict[str, Any] # score: Bilingual, warnings: List[Bilingual] 
    drainage: BilingualText
    erosion: BilingualText
    moisture: BilingualText

class Advisory(BaseModel):
    alerts: List[BilingualText]
    management_tips: List[BilingualText]
    savings_msg: Dict = {}
    schedule: List = [] 
    shopping_list: List[ShoppingItem]
    soil_health_checklist: SoilHealthChecklist
    substitutes: List = []
    summary_card: List[SummaryItem]
    voice_script: str = ""

class Meta(BaseModel):
    crop: str
    mode: str = "GPS Zone"
    region: str
    zone: str
    topography: str = "Upland" # Default or mapped
    soil_profile: SoilProfile

class FarmingGuide(BaseModel):
    duration: BilingualText
    water: BilingualText
    yield_est: BilingualText
    suitability: BilingualText
    spacing: BilingualText
    maintenance: BilingualText

class CropRecommendation(BaseModel):
    advisory: Advisory
    farming_guide: FarmingGuide # Restored
    meta: Meta
    status: str = "success"

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
