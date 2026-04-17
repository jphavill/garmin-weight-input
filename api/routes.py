from datetime import date

from fastapi import APIRouter, HTTPException

from auth.garmin_auth import get_garmin_client
from core.errors import (
    ActivityNotFoundError,
    ActivityTooOldError,
    ActivityTypeMismatchError,
    GarminAuthError,
    GarminUpdateError,
)
from models.requests import ConvertLatestHikeToRuckRequest, WeightInput
from services.hike_to_ruck_service import convert_latest_hike_to_ruck
from services.shoe_wear_service import get_shoe_wear
from services.weight_service import log_weight

router = APIRouter()


@router.get("/health")
def health_check() -> dict:
    return {"status": "healthy"}


@router.post("/weight")
def set_weight(data: WeightInput) -> dict:
    try:
        return log_weight(data.weight)
    except GarminAuthError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/hike-to-ruck")
def convert_latest_hike_to_ruck_route(request: ConvertLatestHikeToRuckRequest) -> dict:
    activity_id = None
    try:
        client = get_garmin_client()
        result = convert_latest_hike_to_ruck(client, request.pack_weight)
        activity_id = result.get("activity_id")
        result["pack_weight"] = request.pack_weight
        return result
    except ActivityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ActivityTooOldError as exc:
        activity_id = activity_id or exc.details.get("activity_id")
        raise HTTPException(status_code=400, detail=exc.details) from exc
    except ActivityTypeMismatchError as exc:
        activity_id = activity_id or exc.details.get("activity_id")
        raise HTTPException(status_code=400, detail=exc.details) from exc
    except GarminAuthError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except GarminUpdateError as exc:
        activity_id = activity_id or exc.activity_id
        raise HTTPException(
            status_code=502,
            detail={
                "message": "Garmin request failed",
                "status_code": exc.status_code,
                "activity_id": activity_id,
                "response_body": exc.response_body,
            },
        ) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/shoe-wear")
def shoe_wear(start_date: date, end_date: date) -> dict:
    if start_date > end_date:
        raise HTTPException(status_code=400, detail="start_date must be less than or equal to end_date")

    try:
        client = get_garmin_client()
        return get_shoe_wear(client, start_date, end_date)
    except (GarminAuthError, GarminUpdateError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
