from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import garth
from garth.exc import GarthException
from datetime import date
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


class WeightInput(BaseModel):
    weight: float


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.post("/weight")
def set_weight(data: WeightInput):
    try:
        get_api()
        
        payload = {
            "date": str(date.today()),
            "unitKey": "kg",
            "value": data.weight
        }
        
        garth.client.post("connectapi", "/weight-service/user-weight", json=payload)
        
        return {"success": True, "weight": data.weight}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
