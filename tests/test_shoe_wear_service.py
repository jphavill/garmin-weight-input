from datetime import date
from typing import Any

from services.shoe_wear_service import get_shoe_wear


class FakeGarminClient:
    def __init__(self, payloads: dict[str, list[dict[str, Any]] | Any]):
        self.payloads = payloads
        self.calls: list[tuple[str, str, str]] = []

    def get_activities_by_date(self, start_date: str, end_date: str, activitytype: str) -> Any:
        self.calls.append((start_date, end_date, activitytype))
        return self.payloads.get(activitytype, [])


def test_get_shoe_wear_makes_exactly_three_filtered_calls() -> None:
    client = FakeGarminClient({"running": [], "walking": [], "hiking": []})

    get_shoe_wear(client, date(2026, 1, 1), date(2026, 1, 31))

    assert client.calls == [
        ("2026-01-01", "2026-01-31", "running"),
        ("2026-01-01", "2026-01-31", "walking"),
        ("2026-01-01", "2026-01-31", "hiking"),
    ]


def test_get_shoe_wear_filters_hiking_to_only_rucking() -> None:
    client = FakeGarminClient(
        {
            "running": [],
            "walking": [],
            "hiking": [
                {"activityId": 1, "activityName": "Ruck Morning", "distance": 3000, "startTimeLocal": "2026-01-01"},
                {
                    "activityId": 2,
                    "activityName": "Normal Hike",
                    "distance": 9000,
                    "startTimeLocal": "2026-01-02",
                    "activityTypeDTO": {"typeKey": "hiking"},
                },
            ],
        }
    )

    result = get_shoe_wear(client, date(2026, 1, 1), date(2026, 1, 31))

    assert result["activityCounts"]["rucking"] == 1
    assert result["totals"]["ruckingKm"] == 3.0


def test_get_shoe_wear_computes_totals_counts_and_zeros() -> None:
    client = FakeGarminClient(
        {
            "running": [{"activityId": 1, "distance": 1234, "startTimeLocal": "2026-01-01", "activityName": "Run"}],
            "walking": [{"activityId": 2, "distance": 2500, "startTimeLocal": "2026-01-02", "activityName": "Walk"}],
            "hiking": [
                {
                    "activityId": 3,
                    "distance": 4200,
                    "startTimeLocal": "2026-01-03",
                    "activityName": "Hill Session",
                    "summaryDTO": {"beginPackWeight": 9000},
                }
            ],
        }
    )

    result = get_shoe_wear(client, date(2026, 1, 1), date(2026, 1, 31))

    assert result["totals"] == {
        "totalKm": 7.93,
        "runningKm": 1.23,
        "walkingKm": 2.5,
        "ruckingKm": 4.2,
    }
    assert result["activityCounts"] == {"running": 1, "walking": 1, "rucking": 1}

    empty_client = FakeGarminClient({"running": [], "walking": [], "hiking": []})
    empty_result = get_shoe_wear(empty_client, date(2026, 2, 1), date(2026, 2, 2))

    assert empty_result["totals"] == {
        "totalKm": 0.0,
        "runningKm": 0.0,
        "walkingKm": 0.0,
        "ruckingKm": 0.0,
    }
    assert empty_result["activityCounts"] == {"running": 0, "walking": 0, "rucking": 0}


def test_get_shoe_wear_handles_missing_optional_fields_safely() -> None:
    client = FakeGarminClient(
        {
            "running": [
                {
                    "activityId": None,
                    "distance": "unknown",
                    "startTimeGMT": "2026-01-05T08:00:00Z",
                }
            ],
            "walking": "unexpected",
            "hiking": ["bad-entry"],
        }
    )

    result = get_shoe_wear(client, date(2026, 1, 1), date(2026, 1, 31))

    assert result["totals"] == {
        "totalKm": 0.0,
        "runningKm": 0.0,
        "walkingKm": 0.0,
        "ruckingKm": 0.0,
    }
    assert result["activityCounts"] == {"running": 1, "walking": 0, "rucking": 0}
