"""Load and query the saved scikit-learn model."""

import os
from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from backend.app.schemas.prediction import (
    PredictionExplanation,
    PredictionRequest,
)

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

    def explain(
        self, request: PredictionRequest
    ) -> list[PredictionExplanation]:
        """Decompose Ridge's log-price prediction into feature contributions."""
        model = self.model.regressor_
        transformed = model.named_steps["preprocess"]
        ridge = model.named_steps["ridge"]
        department = request.department_code
        features = pd.DataFrame(
            [
                {
                    "built_area_m2": request.built_area_m2,
                    "rooms": request.rooms,
                    "property_type": request.property_type,
                    "department_code": department,
                    "commune_id": f"{department}-{request.commune_code}",
                    "postal_code": request.postal_code,
                }
            ]
        )
        values = transformed.transform(features)
        contributions = np.asarray(values.toarray()).ravel() * ridge.coef_
        names = transformed.get_feature_names_out()

        prefix_to_label = {
            "built_area_m2": "La surface du logement",
            "rooms": "Le nombre de pièces",
            "property_type": "Le type de logement",
            "department_code": "La localisation",
            "commune_id": "La localisation",
            "postal_code": "La localisation",
        }
        factor_contributions: dict[str, float] = {}
        for name, contribution in zip(names, contributions, strict=True):
            if contribution == 0:
                continue
            feature_name = name.split("__", maxsplit=1)[-1]
            source = next(
                (key for key in prefix_to_label if feature_name.startswith(key)),
                None,
            )
            if source:
                label = prefix_to_label[source]
                factor_contributions[label] = (
                    factor_contributions.get(label, 0.0) + float(contribution)
                )

        return [
            PredictionExplanation(
                factor=factor,
                direction="hausse" if contribution > 0 else "baisse",
                contribution_percent=round((np.exp(abs(contribution)) - 1) * 100, 1),
            )
            for factor, contribution in sorted(
                factor_contributions.items(),
                key=lambda item: abs(item[1]),
                reverse=True,
            )[:4]
            if abs(contribution) >= 0.005
        ]


@lru_cache(maxsize=1)
def get_prediction_service() -> PredictionService:
    """Load the model once; MODEL_PATH can override its local default."""
    model_path = Path(os.getenv("MODEL_PATH", str(DEFAULT_MODEL_PATH)))
    return PredictionService(model_path)
