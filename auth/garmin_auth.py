import os
from pathlib import Path

from garminconnect import Garmin

from core.errors import GarminAuthError

TOKEN_FILE = Path(os.getenv("TOKEN_FILE", "/app/data/garth_token"))


def _resolve_tokenstore_path() -> Path:
    candidates = [
        TOKEN_FILE,
        Path(__file__).resolve().parents[1] / "data" / "garth_token",
    ]

    for candidate in candidates:
        if candidate.exists():
            return candidate

    raise GarminAuthError(
        "Garmin token file not found. Checked: "
        + ", ".join(str(path) for path in candidates)
        + ". Run init_auth.py first or set TOKEN_FILE."
    )


def get_garmin_client() -> Garmin:
    tokenstore = str(_resolve_tokenstore_path())
    try:
        client = Garmin()
        client.login(tokenstore)
        return client
    except Exception as exc:
        raise GarminAuthError(f"Failed to authenticate with Garmin token store: {exc}") from exc
