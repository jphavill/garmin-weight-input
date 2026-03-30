from services.activity_payloads import (
    build_minimal_update_payload,
    compute_grams_from_kg,
    derive_rucking_activity_title,
)


def test_compute_grams_from_kg() -> None:
    assert compute_grams_from_kg(18.0) == 18000


def test_derive_rucking_activity_title() -> None:
    assert derive_rucking_activity_title("Halifax Hiking") == "Halifax Rucking"


def test_build_minimal_update_payload() -> None:
    source_activity = {
        "activityId": 123,
        "activityTypeDTO": {"typeKey": "hiking", "typeId": 17},
        "summaryDTO": {"beginPackWeight": 0},
    }

    payload = build_minimal_update_payload(source_activity, 123, 18000)

    assert payload == {
        "activityId": 123,
        "activityTypeDTO": {"typeKey": "rucking", "typeId": 17},
        "summaryDTO": {"beginPackWeight": 18000},
    }
    assert source_activity["activityTypeDTO"]["typeKey"] == "hiking"
