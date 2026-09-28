"""Prediction endpoint."""

from fastapi import APIRouter, HTTPException, status

from backend.app.schemas.prediction import PredictionRequest, PredictionResponse
from backend.app.services.prediction import get_prediction_service

router = APIRouter(prefix="/api/v1", tags=["predictions"])


@router.post("/predictions", response_model=PredictionResponse)
def create_prediction(request: PredictionRequest) -> PredictionResponse:
    """Estimate a property's sale price using the saved 2025 Ridge model."""
    try:
        service = get_prediction_service()
    except FileNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "The prediction model is not available. Train or provide the "
                "artifact and set MODEL_PATH if it is stored elsewhere."
            ),
        ) from error

    return PredictionResponse(
        predicted_price_eur=service.predict(request), model_vintage=2025
    )
