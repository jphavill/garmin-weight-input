import auth.garmin_auth as garmin_auth
import pytest
from core.errors import GarminAuthError


def test_resolve_tokenstore_path_returns_existing_token_file(monkeypatch, tmp_path) -> None:
    token_file = tmp_path / "garmin_tokens" / "garmin_tokens.json"
    token_file.parent.mkdir(parents=True)
    token_file.write_text("{}")

    monkeypatch.setattr(garmin_auth, "TOKEN_STORE_PATH", token_file)

    assert garmin_auth._resolve_tokenstore_path() == token_file


def test_resolve_tokenstore_path_raises_when_file_missing(monkeypatch, tmp_path) -> None:
    missing_token_file = tmp_path / "garmin_tokens" / "garmin_tokens.json"
    monkeypatch.setattr(garmin_auth, "TOKEN_STORE_PATH", missing_token_file)

    with pytest.raises(GarminAuthError, match="Garmin token file not found"):
        garmin_auth._resolve_tokenstore_path()


def test_get_garmin_client_logs_in_with_resolved_tokenstore(monkeypatch, tmp_path) -> None:
    token_file = tmp_path / "garmin_tokens" / "garmin_tokens.json"
    token_file.parent.mkdir(parents=True)
    token_file.write_text("{}")

    class FakeGarmin:
        def __init__(self):
            self.tokenstore = None

        def login(self, tokenstore: str) -> None:
            self.tokenstore = tokenstore

    monkeypatch.setattr(garmin_auth, "Garmin", FakeGarmin)
    monkeypatch.setattr(garmin_auth, "_resolve_tokenstore_path", lambda: token_file)

    client = garmin_auth.get_garmin_client()
    assert isinstance(client, FakeGarmin)
    assert client.tokenstore == str(token_file)


def test_get_garmin_client_maps_login_failures_to_auth_error(monkeypatch, tmp_path) -> None:
    token_file = tmp_path / "garmin_tokens" / "garmin_tokens.json"
    token_file.parent.mkdir(parents=True)
    token_file.write_text("{}")

    class FakeGarmin:
        def login(self, tokenstore: str) -> None:
            raise RuntimeError("bad token")

    monkeypatch.setattr(garmin_auth, "Garmin", FakeGarmin)
    monkeypatch.setattr(garmin_auth, "_resolve_tokenstore_path", lambda: token_file)

    with pytest.raises(GarminAuthError, match="Failed to authenticate"):
        garmin_auth.get_garmin_client()
