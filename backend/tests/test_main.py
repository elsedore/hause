from fastapi.testclient import TestClient

from backend.app.api import predictions
from backend.app.main import app

client = TestClient(app)


def test_root_returns_api_status() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"message": "House Price Prediction API", "status": "ok"}


def test_health_returns_healthy_status() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_prediction_uses_prediction_service(monkeypatch) -> None:
    class FakePredictionService:
        def predict(self, request) -> float:
            assert request.built_area_m2 == 75
            return 245_000.0

    monkeypatch.setattr(
        predictions, "get_prediction_service", lambda: FakePredictionService()
    )
    response = client.post(
        "/api/v1/predictions",
        json={
            "property_type": "Appartement",
            "built_area_m2": 75,
            "rooms": 3,
            "department_code": "75",
            "commune_code": "056",
            "postal_code": "75006",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "predicted_price_eur": 245_000.0,
        "model_vintage": 2025,
    }


def test_prediction_rejects_negative_area() -> None:
    response = client.post(
        "/api/v1/predictions",
        json={
            "property_type": "Appartement",
            "built_area_m2": -1,
            "rooms": 0,
            "department_code": "75",
            "commune_code": "056",
        },
    )

    assert response.status_code == 422
