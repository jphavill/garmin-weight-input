from fastapi.testclient import TestClient

import api.routes as routes
from app import app

client = TestClient(app)


def test_health_endpoint() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_weight_endpoint_success(monkeypatch) -> None:
    def fake_log_weight(weight: float) -> dict:
        return {"success": True, "weight": weight}

    monkeypatch.setattr(routes, "log_weight", fake_log_weight)

    response = client.post("/weight", json={"weight": 78.1})
    assert response.status_code == 200
    assert response.json() == {"success": True, "weight": 78.1}


def test_hike_to_ruck_converts_kg_to_grams(monkeypatch) -> None:
    captured = {}

    def fake_get_client() -> object:
        return object()

    def fake_convert(client_obj: object, pack_weight_kg: float) -> dict:
        captured["pack_weight_kg"] = pack_weight_kg
        return {
            "message": "Latest hiking activity converted to rucking",
            "activity_id": 1,
            "old_type": "hiking",
            "new_type": "rucking",
            "pack_weight_grams": 18000,
            "original_activity_name": "A Hiking",
            "new_activity_name": "A Rucking",
            "garmin_activity_name_after_update": "A Rucking",
            "update_method": "connectapi_put_minimal",
        }

    monkeypatch.setattr(routes, "get_garmin_client", fake_get_client)
    monkeypatch.setattr(routes, "convert_latest_hike_to_ruck", fake_convert)

    response = client.post("/hike-to-ruck", json={"pack_weight": 18.0})
    assert response.status_code == 200
    data = response.json()
    assert captured["pack_weight_kg"] == 18.0
    assert data["pack_weight_grams"] == 18000
    assert data["pack_weight"] == 18.0
