from typing import Any

from garminconnect import Garmin

from core.errors import (
    ActivityNotFoundError,
    ActivityTooOldError,
    ActivityTypeMismatchError,
    GarminUpdateError,
)
from services.activity_payloads import (
    build_minimal_update_payload,
    compute_grams_from_kg,
    derive_rucking_activity_title,
)
from services.activity_rules import extract_activity_type_key, is_hiking, is_within_hours
from services.garmin_gateway import (
    get_activity_details,
    get_latest_activity_summary,
    set_activity_name,
    update_activity_minimal,
)


def convert_latest_hike_to_ruck(client: Garmin, pack_weight_kg: float) -> dict[str, Any]:
    latest_activity = get_latest_activity_summary(client)

    activity_id = latest_activity.get("activityId")
    if not isinstance(activity_id, int):
        raise ActivityNotFoundError("Garmin latest activity payload missing valid activityId")

    activity_details = get_activity_details(client, activity_id)
    old_type = extract_activity_type_key(activity_details) or extract_activity_type_key(latest_activity)

    if not is_within_hours(activity_details, 8):
        raise ActivityTooOldError(
            {
                "message": "Latest activity is older than 8 hours",
                "activity_id": activity_id,
                "current_type": old_type,
                "activity_name": activity_details.get("activityName"),
                "start_time": activity_details.get("startTimeLocal") or activity_details.get("startTimeGMT"),
                "activity_type_dto": activity_details.get("activityTypeDTO"),
            }
        )

    if not is_hiking(activity_details):
        raise ActivityTypeMismatchError(
            {
                "message": "Latest activity is not hiking",
                "activity_id": activity_id,
                "current_type": old_type,
                "activity_name": activity_details.get("activityName"),
                "start_time": activity_details.get("startTimeLocal") or activity_details.get("startTimeGMT"),
                "activity_type_dto": activity_details.get("activityTypeDTO"),
            }
        )

    pack_weight_grams = compute_grams_from_kg(pack_weight_kg)
    payload = build_minimal_update_payload(activity_details, activity_id, pack_weight_grams)
    update_activity_minimal(client, activity_id, payload)

    original_name = activity_details.get("activityName")
    new_name = derive_rucking_activity_title(original_name)

    if isinstance(new_name, str) and new_name and new_name != original_name:
        set_activity_name(client, activity_id, new_name)

    refreshed = get_activity_details(client, activity_id)
    updated_name = refreshed.get("activityName")
    if isinstance(new_name, str) and new_name and updated_name != new_name:
        raise GarminUpdateError(
            "Activity rename was requested but Garmin returned a different name",
            status_code=502,
            response_body=f"expected={new_name!r} actual={updated_name!r}",
            activity_id=activity_id,
        )

    return {
        "message": "Latest hiking activity converted to rucking",
        "activity_id": activity_id,
        "old_type": old_type,
        "new_type": "rucking",
        "pack_weight_grams": pack_weight_grams,
        "original_activity_name": original_name,
        "new_activity_name": new_name,
        "garmin_activity_name_after_update": updated_name,
        "update_method": "connectapi_put_minimal",
    }
