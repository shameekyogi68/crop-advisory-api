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


class CropIdentity(BaseModel):
    crop_name: LocalizedText
    variety_name: LocalizedText
    crop_category: LocalizedText

class AgroClimaticSuitability(BaseModel):
    suitable_temperature_range: LocalizedText
    suitable_rainfall_range: LocalizedText
    suitable_soil_types: LocalizedText
    suitable_soil_ph_range: LocalizedText

class MorphologicalCharacteristics(BaseModel):
    plant_height_range: LocalizedText
    growth_habit: LocalizedText
    root_system_type: LocalizedText
    maturity_duration_range: LocalizedText

class SeedSpecifications(BaseModel):
    seed_rate_per_acre: LocalizedText
    germination_period: LocalizedText
    seed_viability_period: LocalizedText

class YieldPotential(BaseModel):
    average_yield_per_acre: LocalizedText
    yield_range_under_normal_conditions: LocalizedText

class SensitivityProfile(BaseModel):
    drought_sensitivity_level: LocalizedText
    waterlogging_sensitivity_level: LocalizedText
    heat_tolerance_level: LocalizedText

class EndUseInformation(BaseModel):
    main_use_type: LocalizedText
    market_category: LocalizedText

class CropKnowledge(BaseModel):
    crop_id: str
    identity: CropIdentity
    agro_climatic_suitability: AgroClimaticSuitability
    morphological_characteristics: MorphologicalCharacteristics
    seed_specifications: SeedSpecifications
    yield_potential: YieldPotential
    sensitivity_profile: SensitivityProfile
    end_use_information: EndUseInformation

class Context(BaseModel):
    location: str
    coordinates: dict
    seasons_detected: List[str]
    date: str
    language: Optional[str] = None

class RecommendationResponse(BaseModel):
    context: Context
    recommendations: List[CropKnowledge]
