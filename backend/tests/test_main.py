from fastapi.testclient import TestClient

from backend.app.api import predictions
from backend.app.main import app
from backend.app.schemas.locations import CommuneOption

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

        def explain(self, _request) -> list:
            return []

    monkeypatch.setattr(
        predictions, "get_prediction_service", lambda: FakePredictionService()
    )
    monkeypatch.setattr(
        predictions,
        "get_department_communes",
        lambda _department: (
            CommuneOption(
                commune_code="056", name="Paris 6e", postal_codes=["75006"]
            ),
        ),
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
        "explanations": [],
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
            "postal_code": "75006",
        },
    )

    assert response.status_code == 422


def test_prediction_rejects_postal_code_outside_commune(monkeypatch) -> None:
    monkeypatch.setattr(
        predictions,
        "get_department_communes",
        lambda _department: (
            CommuneOption(
                commune_code="056", name="Paris 6e", postal_codes=["75006"]
            ),
        ),
    )
    response = client.post(
        "/api/v1/predictions",
        json={
            "property_type": "Appartement",
            "built_area_m2": 75,
            "rooms": 0,
            "department_code": "75",
            "commune_code": "056",
            "postal_code": "75018",
        },
    )

    assert response.status_code == 422


def test_dvf_commune_code_keeps_numeric_suffix_zeros() -> None:
    from backend.app.services.geography import _dvf_commune_code

    assert _dvf_commune_code("01", "01001") == "001"
    assert _dvf_commune_code("75", "75118") == "118"
