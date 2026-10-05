"""Endpoints for French department, commune, and postal-code options."""

from fastapi import APIRouter, HTTPException, Path, status

from backend.app.schemas.locations import CommuneOption, DepartmentOption
from backend.app.services.geography import (
    GeographyProviderError,
    get_department_communes,
    get_departments,
)

router = APIRouter(prefix="/api/v1/locations", tags=["locations"])


@router.get("/departments", response_model=list[DepartmentOption])
def list_departments() -> list[DepartmentOption]:
    """List departments from the official French geographic reference."""
    try:
        return list(get_departments())
    except GeographyProviderError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)
        ) from error


@router.get(
    "/departments/{department_code}/communes", response_model=list[CommuneOption]
)
def list_communes(
    department_code: str = Path(pattern=r"^[0-9A-Z]{2,3}$"),
) -> list[CommuneOption]:
    """List communes and postal codes for a selected department."""
    try:
        communes = get_department_communes(department_code)
    except GeographyProviderError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)
        ) from error
    if not communes:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Unknown department."
        )
    return list(communes)
