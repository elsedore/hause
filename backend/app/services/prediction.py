"""Load and query the saved scikit-learn model."""

import os
from functools import lru_cache
from pathlib import Path

import joblib
import pandas as pd

from backend.app.schemas.prediction import PredictionRequest

DEFAULT_MODEL_PATH = (
    Path(__file__).resolve().parents[3] / "ml/models/ridge_2025_full.joblib"
)


class PredictionService:
    """Small inference wrapper that prepares one row for the trained pipeline."""

    def __init__(self, model_path: Path) -> None:
        if not model_path.is_file():
            raise FileNotFoundError(f"Model artifact not found: {model_path}")
        self.model = joblib.load(model_path)

    def predict(self, request: PredictionRequest) -> float:
        """Return the model's estimated sale price in euros."""
        department = request.department_code
        commune = request.commune_code
        features = pd.DataFrame(
            [
                {
                    "built_area_m2": request.built_area_m2,
                    "rooms": request.rooms,
                    "property_type": request.property_type,
                    "department_code": department,
                    "commune_id": f"{department}-{commune}",
                    "postal_code": request.postal_code or "__missing__",
                }
            ]
        )
        prediction = float(self.model.predict(features)[0])
        return round(max(prediction, 0.0), 2)


@lru_cache(maxsize=1)
def get_prediction_service() -> PredictionService:
    """Load the model once; MODEL_PATH can override its local default."""
    model_path = Path(os.getenv("MODEL_PATH", str(DEFAULT_MODEL_PATH)))
    return PredictionService(model_path)
