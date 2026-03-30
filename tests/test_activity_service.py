import pytest
from typing import Any

from core.errors import (
    ActivityTooOldError,
    ActivityTypeMismatchError,
    GarminUpdateError,
)
from services.hike_to_ruck_service import convert_latest_hike_to_ruck


def test_convert_latest_hike_to_ruck_success(monkeypatch) -> None:
    calls: dict[str, object] = {}

    def fake_get_latest(_client: object) -> dict:
        return {"activityId": 123}

    def fake_get_details(_client: object, _activity_id: int) -> dict:
        if calls.get("updated"):
            return {"activityId": 123, "activityName": "A Rucking", "activityTypeDTO": {"typeKey": "rucking"}}
        return {
            "activityId": 123,
            "activityName": "A Hiking",
            "startTimeGMT": "2030-01-01T00:00:00+00:00",
            "activityTypeDTO": {"typeKey": "hiking"},
            "summaryDTO": {"beginPackWeight": 0},
        }

    def fake_update_minimal(_client: object, activity_id: int, payload: dict) -> dict:
        calls["update_activity_id"] = activity_id
        calls["payload"] = payload
        calls["updated"] = True
        return {"status": "ok"}

    def fake_set_name(_client: object, activity_id: int, name: str) -> None:
        calls["rename"] = (activity_id, name)

    monkeypatch.setattr("services.hike_to_ruck_service.get_latest_activity_summary", fake_get_latest)
    monkeypatch.setattr("services.hike_to_ruck_service.get_activity_details", fake_get_details)
    monkeypatch.setattr("services.hike_to_ruck_service.update_activity_minimal", fake_update_minimal)
    monkeypatch.setattr("services.hike_to_ruck_service.set_activity_name", fake_set_name)

    fake_client: Any = object()
    result = convert_latest_hike_to_ruck(fake_client, 18.0)

    assert calls["update_activity_id"] == 123
    payload = calls["payload"]
    assert isinstance(payload, dict)
    assert payload["activityId"] == 123
    assert payload["activityTypeDTO"]["typeKey"] == "rucking"
    assert payload["summaryDTO"]["beginPackWeight"] == 18000
    assert calls["rename"] == (123, "A Rucking")
    assert result["update_method"] == "connectapi_put_minimal"
    assert result["pack_weight_grams"] == 18000


def test_convert_latest_hike_to_ruck_rejects_old_activity(monkeypatch) -> None:
    def fake_get_latest(_client: object) -> dict:
        return {"activityId": 123}

    def fake_get_details(_client: object, _activity_id: int) -> dict:
        return {
            "activityId": 123,
            "activityName": "Test Hiking",
            "startTimeGMT": "2020-01-01T00:00:00+00:00",
            "activityTypeDTO": {"typeKey": "hiking"},
        }

    monkeypatch.setattr("services.hike_to_ruck_service.get_latest_activity_summary", fake_get_latest)
    monkeypatch.setattr("services.hike_to_ruck_service.get_activity_details", fake_get_details)

    with pytest.raises(ActivityTooOldError):
        fake_client: Any = object()
        convert_latest_hike_to_ruck(fake_client, 18.0)


def test_convert_latest_hike_to_ruck_rejects_non_hiking(monkeypatch) -> None:
    def fake_get_latest(_client: object) -> dict:
        return {"activityId": 123}

    def fake_get_details(_client: object, _activity_id: int) -> dict:
        return {
            "activityId": 123,
            "activityName": "Test Run",
            "startTimeGMT": "2999-01-01T00:00:00+00:00",
            "activityTypeDTO": {"typeKey": "running"},
        }

    monkeypatch.setattr("services.hike_to_ruck_service.get_latest_activity_summary", fake_get_latest)
    monkeypatch.setattr("services.hike_to_ruck_service.get_activity_details", fake_get_details)

    with pytest.raises(ActivityTypeMismatchError):
        fake_client: Any = object()
        convert_latest_hike_to_ruck(fake_client, 18.0)


def test_convert_latest_hike_to_ruck_fails_when_name_not_applied(monkeypatch) -> None:
    def fake_get_latest(_client: object) -> dict:
        return {"activityId": 123}

    def fake_get_details(_client: object, _activity_id: int) -> dict:
        return {
            "activityId": 123,
            "activityName": "A Hiking",
            "startTimeGMT": "2999-01-01T00:00:00+00:00",
            "activityTypeDTO": {"typeKey": "hiking"},
            "summaryDTO": {"beginPackWeight": 0},
        }

    def fake_update_minimal(_client: object, _activity_id: int, _payload: dict) -> dict:
        return {"status": "ok"}

    def fake_set_name(_client: object, _activity_id: int, _name: str) -> None:
        return

    monkeypatch.setattr("services.hike_to_ruck_service.get_latest_activity_summary", fake_get_latest)
    monkeypatch.setattr("services.hike_to_ruck_service.get_activity_details", fake_get_details)
    monkeypatch.setattr("services.hike_to_ruck_service.update_activity_minimal", fake_update_minimal)
    monkeypatch.setattr("services.hike_to_ruck_service.set_activity_name", fake_set_name)

    with pytest.raises(GarminUpdateError):
        fake_client: Any = object()
        convert_latest_hike_to_ruck(fake_client, 18.0)
