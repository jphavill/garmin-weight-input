from datetime import date
from typing import Any

from garminconnect import Garmin

from core.errors import GarminAuthError, GarminUpdateError
from services.activity_rules import extract_activity_type_key


def get_shoe_wear(client: Garmin, start_date: date, end_date: date) -> dict[str, Any]:
    running_raw = _get_activities_by_type(client, start_date, end_date, "running")
    walking_raw = _get_activities_by_type(client, start_date, end_date, "walking")
    hiking_raw = _get_activities_by_type(client, start_date, end_date, "hiking")

    running = [_normalize_activity(activity) for activity in running_raw]
    walking = [_normalize_activity(activity) for activity in walking_raw]
    rucking = [_normalize_activity(activity) for activity in hiking_raw if _is_rucking_activity(activity)]

    running_km = _round_km(sum(activity["distanceKm"] for activity in running))
    walking_km = _round_km(sum(activity["distanceKm"] for activity in walking))
    rucking_km = _round_km(sum(activity["distanceKm"] for activity in rucking))
    total_km = _round_km(running_km + walking_km + rucking_km)

    return {
        "startDate": start_date.isoformat(),
        "endDate": end_date.isoformat(),
        "totals": {
            "totalKm": total_km,
            "runningKm": running_km,
            "walkingKm": walking_km,
            "ruckingKm": rucking_km,
        },
        "activityCounts": {
            "running": len(running),
            "walking": len(walking),
            "rucking": len(rucking),
        },
        "activities": {
            "running": running,
            "walking": walking,
            "rucking": rucking,
        },
    }


def _get_activities_by_type(client: Garmin, start_date: date, end_date: date, activity_type: str) -> list[dict[str, Any]]:
    try:
        activities = client.get_activities_by_date(start_date.isoformat(), end_date.isoformat(), activitytype=activity_type)
    except GarminAuthError:
        raise
    except GarminUpdateError:
        raise
    except Exception as exc:
        raise GarminUpdateError(
            f"Failed to fetch Garmin activities for type={activity_type}",
            status_code=_extract_status_code(exc) or 502,
            response_body=str(exc),
        ) from exc

    if not isinstance(activities, list):
        return []
    return [activity for activity in activities if isinstance(activity, dict)]


def _normalize_activity(activity: dict[str, Any]) -> dict[str, Any]:
    distance_km = _round_km(_extract_distance_meters(activity) / 1000)
    start_time_local = activity.get("startTimeLocal")
    if not isinstance(start_time_local, str):
        fallback = activity.get("startTimeGMT")
        start_time_local = fallback if isinstance(fallback, str) else None

    return {
        "activityId": activity.get("activityId"),
        "activityName": activity.get("activityName") if isinstance(activity.get("activityName"), str) else None,
        "startTimeLocal": start_time_local,
        "distanceKm": distance_km,
    }


def _extract_distance_meters(activity: dict[str, Any]) -> float:
    distance = activity.get("distance")
    if isinstance(distance, (int, float)):
        return float(distance)
    return 0.0


def _is_rucking_activity(activity: dict[str, Any]) -> bool:
    activity_type_key = extract_activity_type_key(activity)
    if activity_type_key in {"rucking", "ruck"}:
        return True

    activity_type_dto = activity.get("activityTypeDTO")
    if isinstance(activity_type_dto, dict):
        nested_type = activity_type_dto.get("type")
        if isinstance(nested_type, dict):
            nested_key = nested_type.get("typeKey")
            if isinstance(nested_key, str) and "ruck" in nested_key.lower():
                return True

        name_key = activity_type_dto.get("nameKey")
        if isinstance(name_key, str) and "ruck" in name_key.lower():
            return True

    summary_dto = activity.get("summaryDTO")
    if isinstance(summary_dto, dict):
        begin_pack_weight = summary_dto.get("beginPackWeight")
        if isinstance(begin_pack_weight, (int, float)) and begin_pack_weight > 0:
            return True

    activity_name = activity.get("activityName")
    return isinstance(activity_name, str) and "ruck" in activity_name.lower()


def _round_km(value: float) -> float:
    return round(value, 2)


def _extract_status_code(exc: Exception) -> int | None:
    response = getattr(exc, "response", None)
    if response is not None:
        return getattr(response, "status_code", None)
    return None
