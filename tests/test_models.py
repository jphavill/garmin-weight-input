import pytest

from models.requests import ConvertLatestHikeToRuckRequest


def test_convert_request_accepts_valid_pack_weight() -> None:
    request = ConvertLatestHikeToRuckRequest(pack_weight=18.0)
    assert request.pack_weight == 18.0


@pytest.mark.parametrize("value", [0, -1, 100.1])
def test_convert_request_rejects_invalid_pack_weight(value: float) -> None:
    with pytest.raises(Exception):
        ConvertLatestHikeToRuckRequest(pack_weight=value)
