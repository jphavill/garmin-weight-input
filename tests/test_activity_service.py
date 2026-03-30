from datetime import datetime, timedelta, timezone

import pytest

from core.errors import InvalidActivityTypeError
from services.activity_service import (
    _extract_activity_type_key,
    assert_activity_is_hiking,
    build_rucking_update_payload,
)


def test_extract_activity_type_from_name_key() -> None:
    activity = {
        "activityTypeDTO": {
            "nameKey": "activity_type_hiking",
        }
    }
    assert _extract_activity_type_key(activity) == "hiking"


def test_assert_activity_is_hiking_rejects_old_activity() -> None:
    old_start = (datetime.now(timezone.utc) - timedelta(hours=9)).isoformat()
    activity = {
        "activityId": 123,
        "activityName": "Test Hiking",
        "startTimeGMT": old_start,
        "activityTypeDTO": {"typeKey": "hiking"},
    }

    with pytest.raises(InvalidActivityTypeError) as exc:
        assert_activity_is_hiking(activity)

    assert exc.value.details["message"] == "Latest activity is older than 8 hours"


def test_build_rucking_update_payload_sets_type_weight_and_name() -> None:
    activity = {
        "activityId": 123,
        "activityName": "Halifax Hiking",
        "activityTypeDTO": {"typeKey": "hiking"},
        "summaryDTO": {"beginPackWeight": 0},
    }

    payload = build_rucking_update_payload(activity, 18000)

    assert payload["activityTypeDTO"]["typeKey"] == "rucking"
    assert payload["summaryDTO"]["beginPackWeight"] == 18000
    assert payload["activityName"] == "Halifax Rucking"
    assert activity["activityName"] == "Halifax Hiking"
