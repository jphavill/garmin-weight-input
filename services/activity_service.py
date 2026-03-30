from copy import deepcopy
from typing import Any

from garminconnect import Garmin

from core.errors import InvalidActivityTypeError
from services.activity_payloads import derive_rucking_activity_title
from services.activity_rules import extract_activity_type_key, is_hiking, is_within_hours
from services.garmin_gateway import get_activity_details, get_latest_activity_summary
from services.hike_to_ruck_service import convert_latest_hike_to_ruck


def get_latest_activity(client: Garmin) -> dict[str, Any]:
    return get_latest_activity_summary(client)


def _extract_activity_type_key(activity: dict[str, Any]) -> str | None:
    return extract_activity_type_key(activity)


def assert_activity_is_hiking(activity: dict[str, Any]) -> None:
    activity_id = activity.get("activityId")
    activity_type = extract_activity_type_key(activity)
    details = {
        "activity_id": activity_id,
        "current_type": activity_type,
        "activity_name": activity.get("activityName"),
        "start_time": activity.get("startTimeLocal") or activity.get("startTimeGMT"),
        "activity_type_dto": activity.get("activityTypeDTO"),
    }
    if not is_within_hours(activity, 8):
        raise InvalidActivityTypeError({"message": "Latest activity is older than 8 hours", **details})
    if not is_hiking(activity):
        raise InvalidActivityTypeError({"message": "Latest activity is not hiking", **details})


def build_rucking_update_payload(activity: dict[str, Any], pack_weight_grams: int) -> dict[str, Any]:
    payload = deepcopy(activity)
    activity_type_dto = payload.get("activityTypeDTO")
    if not isinstance(activity_type_dto, dict):
        activity_type_dto = {}
        payload["activityTypeDTO"] = activity_type_dto
    activity_type_dto["typeKey"] = "rucking"

    summary_dto = payload.get("summaryDTO")
    if not isinstance(summary_dto, dict):
        summary_dto = {}
        payload["summaryDTO"] = summary_dto
    summary_dto["beginPackWeight"] = pack_weight_grams

    payload["activityName"] = derive_rucking_activity_title(payload.get("activityName"))
    return payload
