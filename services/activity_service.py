from copy import deepcopy
from datetime import datetime, timedelta, timezone
import re
import time
from typing import Any, Optional

from garminconnect import Garmin

from core.errors import (
    GarminUpstreamError,
    InvalidActivityTypeError,
    InvalidGarminPayloadError,
    ResourceNotFoundError,
)


def get_latest_activity(client: Garmin) -> dict[str, Any]:
    activities = client.get_activities(0, 1)
    if not activities:
        raise ResourceNotFoundError("No Garmin activities found")
    return activities[0]


def _extract_authenticated_session(client: Garmin) -> Any:
    garth_client = getattr(client, "garth", None)
    if garth_client is not None and callable(getattr(garth_client, "request", None)):
        return garth_client

    candidates: list[Any] = [
        getattr(client, "session", None),
        getattr(client, "_session", None),
        getattr(client, "garmin_connect_session", None),
        getattr(client, "_garmin_connect_session", None),
    ]

    garth_client = getattr(client, "garth", None)
    if garth_client is not None:
        candidates.extend([
            getattr(garth_client, "session", None),
            getattr(garth_client, "_session", None),
        ])

    for candidate in candidates:
        if candidate is not None and callable(getattr(candidate, "get", None)) and callable(getattr(candidate, "post", None)):
            return candidate

    raise InvalidGarminPayloadError("Unable to find authenticated Garmin HTTP session on client")


def _extract_requests_session(session: Any) -> Optional[Any]:
    candidates = [
        getattr(session, "session", None),
        getattr(session, "_session", None),
    ]
    for candidate in candidates:
        if candidate is not None and callable(getattr(candidate, "get", None)) and callable(getattr(candidate, "post", None)):
            return candidate
    return None


def get_activity_details(client: Garmin, activity_id: int) -> dict[str, Any]:
    if callable(getattr(client, "get_activity", None)):
        details = client.get_activity(activity_id)
        if isinstance(details, dict) and details:
            return details

    session = _extract_authenticated_session(client)
    requests_session = _extract_requests_session(session)
    try:
        if requests_session is not None:
            response = requests_session.get(
                f"https://connect.garmin.com/gc-api/activity-service/activity/{activity_id}",
                headers={"Accept": "application/json, text/javascript, */*; q=0.01"},
            )
        elif callable(getattr(session, "request", None)):
            response = session.request(
                "GET",
                "connect",
                f"/gc-api/activity-service/activity/{activity_id}",
                headers={"Accept": "application/json, text/javascript, */*; q=0.01"},
            )
        else:
            raise InvalidGarminPayloadError("Unable to issue Garmin activity details request")
    except Exception as exc:
        status_code = _extract_status_code(exc)
        raise GarminUpstreamError(
            f"Failed to fetch Garmin activity details for {activity_id}",
            status_code=status_code or 500,
            response_body=str(exc),
        ) from exc
    if response.status_code >= 400:
        raise GarminUpstreamError(
            f"Failed to fetch Garmin activity details for {activity_id}",
            status_code=response.status_code,
            response_body=response.text,
        )

    details = response.json()
    if not isinstance(details, dict):
        raise InvalidGarminPayloadError(
            f"Garmin returned unexpected activity details for {activity_id}"
        )
    return details


def assert_activity_is_hiking(activity: dict[str, Any]) -> None:
    if _is_activity_older_than_hours(activity, 8):
        raise InvalidActivityTypeError(
            {
                "message": "Latest activity is older than 8 hours",
                "activity_id": activity.get("activityId"),
                "current_type": _extract_activity_type_key(activity),
                "activity_name": activity.get("activityName"),
                "start_time": activity.get("startTimeLocal") or activity.get("startTimeGMT"),
                "activity_type_dto": activity.get("activityTypeDTO"),
            }
        )

    activity_type = _extract_activity_type_key(activity)
    if activity_type != "hiking":
        raise InvalidActivityTypeError(
            {
                "message": "Latest activity is not hiking",
                "activity_id": activity.get("activityId"),
                "current_type": activity_type,
                "activity_name": activity.get("activityName"),
                "start_time": activity.get("startTimeLocal") or activity.get("startTimeGMT"),
                "activity_type_dto": activity.get("activityTypeDTO"),
            }
        )


def _is_activity_older_than_hours(activity: dict[str, Any], hours: int) -> bool:
    start_dt = _extract_activity_start_datetime(activity)
    if start_dt is None:
        return False
    return datetime.now(timezone.utc) - start_dt > timedelta(hours=hours)


def _extract_activity_start_datetime(activity: dict[str, Any]) -> Optional[datetime]:
    gmt_value = activity.get("startTimeGMT")
    local_value = activity.get("startTimeLocal")

    parsed_gmt = _parse_datetime_value(gmt_value)
    if parsed_gmt is not None:
        return parsed_gmt.astimezone(timezone.utc)

    parsed_local = _parse_datetime_value(local_value)
    if parsed_local is not None:
        if parsed_local.tzinfo is None:
            parsed_local = parsed_local.replace(tzinfo=datetime.now().astimezone().tzinfo)
        return parsed_local.astimezone(timezone.utc)

    return None


def _parse_datetime_value(value: Any) -> Optional[datetime]:
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


def _extract_activity_type_key(activity: dict[str, Any]) -> Optional[str]:
    def _normalize_name_key(name_key: str) -> str:
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
            return _normalize_name_key(dto_name_key)

    activity_type = activity.get("activityType")
    if isinstance(activity_type, dict):
        type_key = activity_type.get("typeKey")
        if isinstance(type_key, str) and type_key:
            return type_key.lower()

        name_key = activity_type.get("nameKey")
        if isinstance(name_key, str) and name_key:
            return _normalize_name_key(name_key)

    for key in ("activityTypeKey", "activityType"):
        value = activity.get(key)
        if isinstance(value, str) and value:
            return value.lower()

    return None


def build_rucking_update_payload(activity: dict[str, Any], pack_weight_grams: int) -> dict[str, Any]:
    payload = deepcopy(activity)

    activity_type_dto = payload.get("activityTypeDTO")
    if not isinstance(activity_type_dto, dict):
        raise InvalidGarminPayloadError("Garmin activity payload missing activityTypeDTO")

    summary_dto = payload.get("summaryDTO")
    if not isinstance(summary_dto, dict):
        raise InvalidGarminPayloadError("Garmin activity payload missing summaryDTO")

    activity_type_dto["typeKey"] = "rucking"
    summary_dto["beginPackWeight"] = pack_weight_grams

    activity_name = payload.get("activityName")
    if isinstance(activity_name, str):
        new_name = re.sub(r"\bHiking\b", "Rucking", activity_name, flags=re.IGNORECASE)
        payload["activityName"] = new_name

    return payload


def _extract_connect_csrf_token(session: Any) -> Optional[str]:
    headers = getattr(session, "headers", {}) or {}
    for key in ("Connect-Csrf-Token", "connect-csrf-token", "X-CSRF-Token", "x-csrf-token"):
        token = headers.get(key)
        if token:
            return token

    cookies = getattr(session, "cookies", None)
    if cookies is None:
        return None

    for cookie_name in (
        "CSRF",
        "csrf",
        "CSRF-TOKEN",
        "XSRF-TOKEN",
        "_csrf",
        "connect_csrf_token",
    ):
        token = cookies.get(cookie_name)
        if token:
            return token

    return None


def update_activity(client: Garmin, activity_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    session = _extract_authenticated_session(client)
    requests_session = _extract_requests_session(session)
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Origin": "https://connect.garmin.com",
        "Referer": f"https://connect.garmin.com/modern/activity/{activity_id}",
    }

    csrf_token = _extract_connect_csrf_token(getattr(session, "session", requests_session or session))
    if csrf_token:
        headers["Connect-Csrf-Token"] = csrf_token

    first_error_status: Optional[int] = None
    first_error_body: Optional[str] = None

    try:
        if requests_session is not None:
            if "Connect-Csrf-Token" not in headers:
                requests_session.get("https://connect.garmin.com/modern/")
                csrf_token = _extract_connect_csrf_token(requests_session)
                if csrf_token:
                    headers["Connect-Csrf-Token"] = csrf_token

            response = requests_session.post(
                f"https://connect.garmin.com/gc-api/activity-service/activity/{activity_id}",
                json=payload,
                headers=headers,
            )
        elif callable(getattr(session, "request", None)):
            response = session.request(
                "POST",
                "connect",
                f"/gc-api/activity-service/activity/{activity_id}",
                json=payload,
                headers=headers,
            )
        else:
            raise InvalidGarminPayloadError("Unable to issue Garmin activity update request")

        if response.status_code < 400:
            return _decode_update_response(response)

        first_error_status = response.status_code
        first_error_body = response.text
    except Exception as exc:
        first_error_status = _extract_status_code(exc) or 500
        first_error_body = str(exc)

    if not callable(getattr(session, "request", None)):
        raise GarminUpstreamError(
            f"Failed to update Garmin activity {activity_id}",
            status_code=first_error_status or 500,
            response_body=first_error_body or "Unknown Garmin update error",
        )

    try:
        fallback_response = session.request(
            "PUT",
            "connectapi",
            f"/activity-service/activity/{activity_id}",
            json=payload,
            api=True,
        )
        if fallback_response.status_code < 400:
            return _decode_update_response(fallback_response)

        fallback_status = fallback_response.status_code
        fallback_body = fallback_response.text
    except Exception as exc:
        fallback_status = _extract_status_code(exc) or 500
        fallback_body = str(exc)

    minimal_payload = {
        "activityId": activity_id,
        "activityTypeDTO": payload.get("activityTypeDTO"),
        "summaryDTO": {
            "beginPackWeight": ((payload.get("summaryDTO") or {}).get("beginPackWeight")),
        },
    }

    try:
        minimal_response = session.request(
            "PUT",
            "connectapi",
            f"/activity-service/activity/{activity_id}",
            json=minimal_payload,
            api=True,
        )
        if minimal_response.status_code < 400:
            return _decode_update_response(minimal_response)

        minimal_status = minimal_response.status_code
        minimal_body = minimal_response.text
    except Exception as exc:
        minimal_status = _extract_status_code(exc) or 500
        minimal_body = str(exc)

    raise GarminUpstreamError(
        f"Failed to update Garmin activity {activity_id}",
        status_code=minimal_status or fallback_status or first_error_status or 500,
        response_body=(
            f"gc-api post failed: status={first_error_status} body={first_error_body}; "
            f"connectapi put(full) failed: status={fallback_status} body={fallback_body}; "
            f"connectapi put(minimal) failed: status={minimal_status} body={minimal_body}"
        ),
    )


def _decode_update_response(response: Any) -> dict[str, Any]:
    try:
        data = response.json()
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {"status": "ok", "body": getattr(response, "text", "")}


def _extract_status_code(exc: Exception) -> Optional[int]:
    response = getattr(exc, "response", None)
    if response is not None:
        return getattr(response, "status_code", None)

    nested_error = getattr(exc, "error", None)
    nested_response = getattr(nested_error, "response", None)
    if nested_response is not None:
        return getattr(nested_response, "status_code", None)

    return None


def convert_latest_hike_to_ruck(client: Garmin, pack_weight_grams: int) -> dict[str, Any]:
    latest_activity = get_latest_activity(client)

    activity_id = latest_activity.get("activityId")
    if not isinstance(activity_id, int):
        raise InvalidGarminPayloadError("Garmin latest activity payload missing valid activityId")

    activity_details = get_activity_details(client, activity_id)
    old_type = _extract_activity_type_key(activity_details) or _extract_activity_type_key(latest_activity)
    assert_activity_is_hiking(activity_details)
    original_name = activity_details.get("activityName")

    payload = build_rucking_update_payload(activity_details, pack_weight_grams)
    new_name = payload.get("activityName")
    update_activity(client, activity_id, payload)

    updated_name = None
    try:
        updated_name = _read_activity_name_with_retry(client, activity_id)

        if isinstance(new_name, str) and new_name and updated_name != new_name:
            set_activity_name(client, activity_id, new_name)
            updated_name = _read_activity_name_with_retry(client, activity_id)
    except Exception:
        pass

    return {
        "message": "Latest hiking activity converted to rucking",
        "activity_id": activity_id,
        "old_type": old_type,
        "new_type": "rucking",
        "pack_weight_grams": pack_weight_grams,
        "original_activity_name": original_name,
        "new_activity_name": new_name,
        "garmin_activity_name_after_update": updated_name,
    }


def set_activity_name(client: Garmin, activity_id: int, activity_name: str) -> None:
    if callable(getattr(client, "set_activity_name", None)):
        client.set_activity_name(str(activity_id), activity_name)
        return

    session = _extract_authenticated_session(client)
    if callable(getattr(session, "request", None)):
        session.request(
            "PUT",
            "connectapi",
            f"/activity-service/activity/{activity_id}",
            json={"activityId": activity_id, "activityName": activity_name},
            api=True,
        )
        return

    raise InvalidGarminPayloadError("Unable to issue explicit Garmin activity name update request")


def _read_activity_name_with_retry(client: Garmin, activity_id: int, attempts: int = 3) -> Optional[str]:
    last_name: Optional[str] = None
    for attempt in range(attempts):
        updated_activity = get_activity_details(client, activity_id)
        last_name = updated_activity.get("activityName")
        if isinstance(last_name, str) and last_name:
            return last_name
        if attempt < attempts - 1:
            time.sleep(1)
    return last_name
