from copy import deepcopy
import re
from typing import Any


def compute_grams_from_kg(pack_weight_kg: float) -> int:
    return int(round(pack_weight_kg * 1000))


def derive_rucking_activity_title(activity_name: str | None) -> str | None:
    if not isinstance(activity_name, str):
        return None
    return re.sub(r"\bHiking\b", "Rucking", activity_name, flags=re.IGNORECASE)


def build_minimal_update_payload(activity: dict[str, Any], activity_id: int, pack_weight_grams: int) -> dict[str, Any]:
    activity_type_dto = deepcopy(activity.get("activityTypeDTO"))
    if not isinstance(activity_type_dto, dict):
        activity_type_dto = {}
    activity_type_dto["typeKey"] = "rucking"

    return {
        "activityId": activity_id,
        "activityTypeDTO": activity_type_dto,
        "summaryDTO": {
            "beginPackWeight": pack_weight_grams,
        },
    }
