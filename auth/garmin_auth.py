import os
from pathlib import Path

from garminconnect import Garmin

from core.errors import GarminAuthError

TOKEN_STORE_PATH = Path(os.getenv("TOKEN_STORE_PATH", "/app/data/garmin_tokens/garmin_tokens.json"))


def _normalize_tokenstore_path(path: Path) -> Path:
    if path.suffix == ".json":
        return path
    return path / "garmin_tokens.json"


def _resolve_tokenstore_path() -> Path:
    candidate = _normalize_tokenstore_path(TOKEN_STORE_PATH)
    if candidate.exists():
        return candidate

    raise GarminAuthError(
        "Garmin token file not found at "
        + str(candidate)
        + ". Run init_auth.py first or set TOKEN_STORE_PATH."
    )


def get_garmin_client() -> Garmin:
    tokenstore = str(_resolve_tokenstore_path())
    try:
        client = Garmin()
        client.login(tokenstore)
        return client
    except Exception as exc:
        raise GarminAuthError(f"Failed to authenticate with Garmin token store: {exc}") from exc
