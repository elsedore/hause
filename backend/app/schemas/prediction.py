"""Request and response models for house-price predictions."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class PredictionRequest(BaseModel):
    """Property details accepted by the 2025 baseline model."""

    model_config = ConfigDict(str_strip_whitespace=True)

    property_type: Literal["Maison", "Appartement"]
    built_area_m2: float = Field(gt=0, le=10_000)
    rooms: int = Field(ge=0, le=100)
    department_code: str = Field(min_length=1, max_length=3)
    commune_code: str = Field(min_length=1, max_length=3)
    postal_code: str | None = Field(default=None, max_length=10)


class PredictionResponse(BaseModel):
    """Estimated sale price and the model vintage used to produce it."""

    predicted_price_eur: float
    model_vintage: int
