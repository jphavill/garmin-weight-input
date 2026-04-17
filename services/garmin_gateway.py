from typing import Any

from garminconnect import Garmin

from core.errors import ActivityNotFoundError, GarminUpdateError


def get_latest_activity_summary(client: Garmin) -> dict[str, Any]:
    activities = client.get_activities(0, 1)
    if not isinstance(activities, list) or not activities:
        raise ActivityNotFoundError("No Garmin activities found")
    latest = activities[0]
    if not isinstance(latest, dict):
        raise ActivityNotFoundError("Garmin latest activity payload is not a dict")
    return latest


def get_activity_details(client: Garmin, activity_id: int) -> dict[str, Any]:
    if callable(getattr(client, "get_activity", None)):
        details = client.get_activity(str(activity_id))
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
            raise GarminUpdateError(
                f"Unable to fetch Garmin activity details for {activity_id}",
                status_code=500,
                response_body="No compatible Garmin session available",
                activity_id=activity_id,
            )
    except GarminUpdateError:
        raise
    except Exception as exc:
        status_code = _extract_status_code(exc) or 500
        raise GarminUpdateError(
            f"Failed to fetch Garmin activity details for {activity_id}",
            status_code=status_code,
            response_body=str(exc),
            activity_id=activity_id,
        ) from exc

    if response.status_code >= 400:
        raise GarminUpdateError(
            f"Failed to fetch Garmin activity details for {activity_id}",
            status_code=response.status_code,
            response_body=response.text,
            activity_id=activity_id,
        )

    details = response.json()
    if not isinstance(details, dict):
        raise GarminUpdateError(
            f"Garmin returned unexpected activity details for {activity_id}",
            status_code=502,
            response_body=str(details),
            activity_id=activity_id,
        )

    return details


def update_activity_minimal(client: Garmin, activity_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    session = _extract_authenticated_session(client)
    if not callable(getattr(session, "request", None)):
        raise GarminUpdateError(
            f"Failed to update Garmin activity {activity_id}",
            status_code=500,
            response_body="Authenticated Garmin request() method unavailable",
            activity_id=activity_id,
        )

    response = _request_connectapi_put(
        session=session,
        activity_id=activity_id,
        payload=payload,
        failure_message=f"Failed to update Garmin activity {activity_id}",
    )

    return _decode_response(response)


def set_activity_name(client: Garmin, activity_id: int, activity_name: str) -> None:
    if callable(getattr(client, "set_activity_name", None)):
        client.set_activity_name(str(activity_id), activity_name)
        return

    session = _extract_authenticated_session(client)
    if not callable(getattr(session, "request", None)):
        raise GarminUpdateError(
            f"Failed to update Garmin activity {activity_id} name",
            status_code=500,
            response_body="Authenticated Garmin request() method unavailable",
            activity_id=activity_id,
        )

    _request_connectapi_put(
        session=session,
        activity_id=activity_id,
        payload={"activityId": activity_id, "activityName": activity_name},
        failure_message=f"Failed to update Garmin activity {activity_id} name",
    )


def _extract_authenticated_session(client: Garmin) -> Any:
    native_client = getattr(client, "client", None)
    if native_client is not None and callable(getattr(native_client, "request", None)):
        return native_client

    candidates = [
        getattr(client, "session", None),
        getattr(client, "_session", None),
        getattr(client, "garmin_connect_session", None),
        getattr(client, "_garmin_connect_session", None),
    ]
    for candidate in candidates:
        if candidate is not None and callable(getattr(candidate, "request", None)):
            return candidate

    return client


def _extract_requests_session(session: Any) -> Any | None:
    candidates = [
        getattr(session, "session", None),
        getattr(session, "_session", None),
    ]
    for candidate in candidates:
        if candidate is not None and callable(getattr(candidate, "get", None)):
            return candidate
    return None


def _request_connectapi_put(
    session: Any,
    activity_id: int,
    payload: dict[str, Any],
    failure_message: str,
) -> Any:
    try:
        response = session.request(
            "PUT",
            "connectapi",
            f"/activity-service/activity/{activity_id}",
            json=payload,
            api=True,
        )
    except Exception as exc:
        raise GarminUpdateError(
            failure_message,
            status_code=_extract_status_code(exc) or 500,
            response_body=str(exc),
            activity_id=activity_id,
        ) from exc

    if response.status_code >= 400:
        raise GarminUpdateError(
            failure_message,
            status_code=response.status_code,
            response_body=response.text,
            activity_id=activity_id,
        )

    return response


def _decode_response(response: Any) -> dict[str, Any]:
    try:
        data = response.json()
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {"status": "ok", "body": getattr(response, "text", "")}


def _extract_status_code(exc: Exception) -> int | None:
    response = getattr(exc, "response", None)
    if response is not None:
        return getattr(response, "status_code", None)

    nested_error = getattr(exc, "error", None)
    nested_response = getattr(nested_error, "response", None)
    if nested_response is not None:
        return getattr(nested_response, "status_code", None)

    return None
