from datetime import datetime, timedelta, timezone
from typing import Any


def extract_activity_type_key(activity: dict[str, Any]) -> str | None:
    def normalize_name_key(name_key: str) -> str:
        normalized = name_key.strip().lower()
        if normalized.startswith("activity_type_"):
            return normalized.replace("activity_type_", "", 1)
        return normalized

    activity_type_dto = activity.get("activityTypeDTO")
    if isinstance(activity_type_dto, dict):
        nested_type = activity_type_dto.get("type")
        if isinstance(nested_type, dict):
            nested_type_key = nested_type.get("typeKey")
            if isinstance(nested_type_key, str) and nested_type_key:
                return nested_type_key.lower()

        direct_type_key = activity_type_dto.get("typeKey")
        if isinstance(direct_type_key, str) and direct_type_key:
            return direct_type_key.lower()

        type_name = activity_type_dto.get("typeName") or activity_type_dto.get("displayName")
        if isinstance(type_name, str) and type_name:
            return type_name.strip().lower()

        dto_name_key = activity_type_dto.get("nameKey")
        if isinstance(dto_name_key, str) and dto_name_key:
            return normalize_name_key(dto_name_key)

    activity_type = activity.get("activityType")
    if isinstance(activity_type, dict):
        type_key = activity_type.get("typeKey")
        if isinstance(type_key, str) and type_key:
            return type_key.lower()

        name_key = activity_type.get("nameKey")
        if isinstance(name_key, str) and name_key:
            return normalize_name_key(name_key)

    for key in ("activityTypeKey", "activityType"):
        value = activity.get(key)
        if isinstance(value, str) and value:
            return value.lower()

    return None


def is_hiking(activity: dict[str, Any]) -> bool:
    return extract_activity_type_key(activity) == "hiking"


def is_within_hours(activity: dict[str, Any], hours: int) -> bool:
    start_dt = parse_activity_start_datetime(activity)
    if start_dt is None:
        return True
    return datetime.now(timezone.utc) - start_dt <= timedelta(hours=hours)


def parse_activity_start_datetime(activity: dict[str, Any]) -> datetime | None:
    gmt_value = activity.get("startTimeGMT")
    local_value = activity.get("startTimeLocal")

    parsed_gmt = parse_datetime_value(gmt_value)
    if parsed_gmt is not None:
        return parsed_gmt.astimezone(timezone.utc)

    parsed_local = parse_datetime_value(local_value)
    if parsed_local is not None:
        if parsed_local.tzinfo is None:
            parsed_local = parsed_local.replace(tzinfo=datetime.now().astimezone().tzinfo)
        return parsed_local.astimezone(timezone.utc)

    return None


def parse_datetime_value(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None

    raw = value.strip()
    candidates = [
        raw,
        raw.replace("Z", "+00:00"),
    ]

    for candidate in candidates:
        try:
            return datetime.fromisoformat(candidate)
        except ValueError:
            pass

    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            pass

    return None
