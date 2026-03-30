from fastapi import APIRouter, HTTPException

from auth.garmin_auth import get_garmin_client
from core.errors import (
    GarminAuthError,
    GarminUpstreamError,
    InvalidActivityTypeError,
    InvalidGarminPayloadError,
    ResourceNotFoundError,
)
from models.requests import ConvertLatestHikeToRuckRequest, WeightInput
from services.activity_service import convert_latest_hike_to_ruck
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
        pack_weight_grams = int(round(request.pack_weight * 1000))
        result = convert_latest_hike_to_ruck(client, pack_weight_grams)
        activity_id = result.get("activity_id")
        result["pack_weight"] = request.pack_weight
        return result
    except ResourceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InvalidActivityTypeError as exc:
        raise HTTPException(status_code=400, detail=exc.details) from exc
    except GarminAuthError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except GarminUpstreamError as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "message": "Garmin request failed",
                "status_code": exc.status_code,
                "activity_id": activity_id,
                "response_body": exc.response_body,
            },
        ) from exc
    except InvalidGarminPayloadError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
