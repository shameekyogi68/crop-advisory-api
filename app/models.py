from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Any, Dict, Union
from datetime import datetime

class CropRecommendationRequest(BaseModel):
    latitude: float = Field(..., ge=8.0, le=37.0, description="Latitude of the farm location")
    longitude: float = Field(..., ge=68.0, le=97.0, description="Longitude of the farm location")
    date: str = Field(..., description="Date of recommendation in YYYY-MM-DD format", pattern=r"^\d{4}-\d{2}-\d{2}$")
    language: Optional[str] = Field(None, pattern="^(en|kn)$", description="Preferred language for output (en/kn)")

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

# Helper type for either bilingual dict or flat string
LocalizedText = Union[BilingualText, str]


class SoilProfile(BaseModel):
    nitrogen: LocalizedText
    phosphorus: LocalizedText
    potassium: LocalizedText
    ph_status: LocalizedText
    ph_value: float
    organic_carbon: Optional[LocalizedText] = None
    type: LocalizedText
    zinc: Optional[LocalizedText] = None
    boron: Optional[LocalizedText] = None
    iron: Optional[LocalizedText] = None
    sulphur: Optional[LocalizedText] = None


class ShoppingItem(BaseModel):
    bags: int
    loose_kg: float
    name: LocalizedText
    qty_display: LocalizedText


class SummaryItem(BaseModel):
    label: LocalizedText
    value: LocalizedText


class SoilHealthChecklist(BaseModel):
    crop_suitability: Dict[str, Any] # score: Localized, warnings: List[Localized] 
    drainage: LocalizedText
    erosion: LocalizedText
    moisture: LocalizedText


class Advisory(BaseModel):
    alerts: List[LocalizedText]
    management_tips: List[LocalizedText]

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
    duration: LocalizedText
    water: LocalizedText
    yield_est: LocalizedText
    suitability: LocalizedText
    spacing: LocalizedText
    maintenance: LocalizedText


class CropRecommendation(BaseModel):
    crop_name: str
    season: str
    advisory: LocalizedText
    farming_guide: FarmingGuide
    water_requirement: LocalizedText

    # Technical Fields (Flat)
    crop_id: str
    crop_category: str
    crop_duration_days: int
    harvest_type: Optional[str] = None
    growth_type: Optional[str] = None
    root_depth: Optional[str] = None
    plant_type: Optional[str] = None
    spacing_row_cm: float
    spacing_plant_cm: float
    suitable_for_intercrop: str
    management_difficulty: str
    input_requirement: str
    average_yield_per_acre: float
    yield_unit: str
    zone_source: str = "Agronomic Map"

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
