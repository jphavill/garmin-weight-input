from fastapi.testclient import TestClient

import api.routes as routes
from app import app
from core.errors import GarminAuthError

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


def test_shoe_wear_success(monkeypatch) -> None:
    def fake_get_client() -> object:
        return object()

    def fake_shoe_wear(_client: object, _start_date, _end_date) -> dict:
        return {
            "startDate": "2026-01-01",
            "endDate": "2026-01-31",
            "totals": {"totalKm": 10.5, "runningKm": 5.0, "walkingKm": 2.5, "ruckingKm": 3.0},
            "activityCounts": {"running": 1, "walking": 1, "rucking": 1},
            "activities": {
                "running": [{"activityId": 1, "activityName": "Run", "startTimeLocal": "2026-01-02", "distanceKm": 5.0}],
                "walking": [{"activityId": 2, "activityName": "Walk", "startTimeLocal": "2026-01-03", "distanceKm": 2.5}],
                "rucking": [{"activityId": 3, "activityName": "Ruck", "startTimeLocal": "2026-01-04", "distanceKm": 3.0}],
            },
        }

    monkeypatch.setattr(routes, "get_garmin_client", fake_get_client)
    monkeypatch.setattr(routes, "get_shoe_wear", fake_shoe_wear)

    response = client.get("/shoe-wear?start_date=2026-01-01&end_date=2026-01-31")
    assert response.status_code == 200
    assert response.json()["totals"]["totalKm"] == 10.5


def test_shoe_wear_rejects_invalid_date_range() -> None:
    response = client.get("/shoe-wear?start_date=2026-02-01&end_date=2026-01-01")
    assert response.status_code == 400
    assert "start_date must be less than or equal to end_date" in response.json()["detail"]


def test_shoe_wear_maps_auth_failure_to_502(monkeypatch) -> None:
    def fake_get_client() -> object:
        raise GarminAuthError("token invalid")

    monkeypatch.setattr(routes, "get_garmin_client", fake_get_client)

    response = client.get("/shoe-wear?start_date=2026-01-01&end_date=2026-01-31")
    assert response.status_code == 502
    assert response.json()["detail"] == "token invalid"
