import os
from pathlib import Path

from garminconnect import Garmin

from core.errors import GarminAuthError

TOKEN_FILE = Path(os.getenv("TOKEN_FILE", "/app/data/garth_token"))


def _require_token_file() -> str:
    if not TOKEN_FILE.exists():
        raise GarminAuthError(
            f"Garmin token file not found at {TOKEN_FILE}. Run init_auth.py first."
        )
    return str(TOKEN_FILE)


def get_garmin_client() -> Garmin:
    tokenstore = _require_token_file()
    try:
        client = Garmin()
        client.login(tokenstore)
        return client
    except Exception as exc:
        raise GarminAuthError(f"Failed to authenticate with Garmin token store: {exc}") from exc
