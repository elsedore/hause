"""Public response models for the French geographic reference data."""

from pydantic import BaseModel


class DepartmentOption(BaseModel):
    code: str
    name: str


class CommuneOption(BaseModel):
    commune_code: str
    name: str
    postal_codes: list[str]
