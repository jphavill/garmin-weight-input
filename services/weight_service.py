from auth.garmin_auth import get_garmin_client


def log_weight(weight: float) -> dict:
    client = get_garmin_client()
    client.add_weigh_in(weight, "kg")
    return {"success": True, "weight": weight}
