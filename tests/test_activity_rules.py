from datetime import datetime, timedelta, timezone

from services.activity_rules import extract_activity_type_key, is_hiking, is_within_hours


def test_extract_activity_type_from_name_key() -> None:
    activity = {"activityTypeDTO": {"nameKey": "activity_type_hiking"}}
    assert extract_activity_type_key(activity) == "hiking"


def test_is_hiking_detects_hiking_type() -> None:
    activity = {"activityTypeDTO": {"typeKey": "hiking"}}
    assert is_hiking(activity) is True


def test_is_within_hours_rejects_old_activity() -> None:
    old_start = (datetime.now(timezone.utc) - timedelta(hours=9)).isoformat()
    activity = {"startTimeGMT": old_start}
    assert is_within_hours(activity, 8) is False
