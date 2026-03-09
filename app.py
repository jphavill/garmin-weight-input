from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import garth
from garth.exc import GarthException
from datetime import datetime, timezone
import os
from pathlib import Path

app = FastAPI()

TOKEN_FILE = Path(os.getenv("TOKEN_FILE", "/app/data/garth_token"))
GARMIN_EMAIL = os.getenv("GARMIN_EMAIL", "")
GARMIN_PASSWORD = os.getenv("GARMIN_PASSWORD", "")


def get_api():
    if TOKEN_FILE.exists():
        try:
            garth.resume(TOKEN_FILE)
            return
        except GarthException:
            pass
    
    if not GARMIN_EMAIL or not GARMIN_PASSWORD:
        raise RuntimeError("GARMIN_EMAIL and GARMIN_PASSWORD must be set")
    
    garth.login(GARMIN_EMAIL, GARMIN_PASSWORD)
    garth.save(TOKEN_FILE)


def _fmt_ts(dt: datetime) -> str:
    return dt.replace(tzinfo=None).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]


class WeightInput(BaseModel):
    weight: float


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.post("/weight")
def set_weight(data: WeightInput):
    try:
        get_api()
        
        try:
            profile = garth.connectapi("/userprofile-service/userprofile/profile")
            username = profile.get("displayName") if profile else "unknown"
        except Exception as e:
            username = f"error: {e}"
        
        dt = datetime.now()
        dt_gmt = datetime.now(timezone.utc)
        
        payload = {
            "dateTimestamp": _fmt_ts(dt),
            "gmtTimestamp": _fmt_ts(dt_gmt),
            "unitKey": "kg",
            "sourceType": "MANUAL",
            "value": data.weight
        }
        
        result = garth.client.post("connectapi", "/weight-service/user-weight", json=payload, api=True)
        
        return {"success": True, "weight": data.weight, "username": username, "result": str(result)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
