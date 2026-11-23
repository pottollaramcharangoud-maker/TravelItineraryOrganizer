import pytest

from validation import (
    CATEGORIES,
    STATUSES,
    prompt_choice,
    prompt_date,
    prompt_number,
    prompt_text,
    prompt_yes_no,
    validate_trip,
)


def valid_fields(**overrides):
    fields = {
        "destination": "Tokyo, Japan",
        "start_date": "2027-04-01",
        "end_date": "2027-04-10",
        "category": "Cultural",
        "notes": "Cherry blossom season",
        "estimated_cost": 2500.0,
        "status": "Booked",
    }
    fields.update(overrides)
    return fields


def feed(monkeypatch, values):
    iterator = iter(values)
    monkeypatch.setattr("builtins.input", lambda prompt="": next(iterator))


def test_validate_trip_accepts_valid_fields():
    assert validate_trip(valid_fields()) == []


@pytest.mark.parametrize(
    "overrides, expected",
    [
        ({"destination": "  "}, "destination is required"),
        ({"start_date": "04/01/2027"}, "start_date must be YYYY-MM-DD"),
        ({"end_date": "nope"}, "end_date must be YYYY-MM-DD"),
        ({"end_date": "2027-03-30"}, "end_date cannot be before start_date"),
        ({"estimated_cost": -1}, "estimated_cost cannot be negative"),
        ({"estimated_cost": "abc"}, "estimated_cost must be numeric"),
        ({"category": "Unknown"}, "category is not recognized"),
        ({"status": "Unknown"}, "status is not recognized"),
    ],
)
def test_validate_trip_rejects_invalid_fields(overrides, expected):
    assert expected in validate_trip(valid_fields(**overrides))


def test_prompt_text_loops_until_non_empty(monkeypatch):
    feed(monkeypatch, ["", "  ", "Paris"])
    assert prompt_text("Destination: ") == "Paris"


def test_prompt_text_allows_blank(monkeypatch):
    feed(monkeypatch, [""])
    assert prompt_text("Notes: ", allow_blank=True) == ""


def test_prompt_text_enforces_max_length(monkeypatch):
    feed(monkeypatch, ["x" * 201, "ok"])
    assert prompt_text("Value: ", max_length=200) == "ok"


def test_prompt_number_rejects_bad_then_accepts(monkeypatch):
    feed(monkeypatch, ["abc", "-5", "42"])
    assert prompt_number("Cost: ", value_type=int, minimum=0) == 42


def test_prompt_date_loops_until_valid(monkeypatch):
    feed(monkeypatch, ["25-12-2026", "2026-12-25"])
    assert prompt_date("Date: ").isoformat() == "2026-12-25"


def test_prompt_choice_accepts_valid_index(monkeypatch):
    feed(monkeypatch, ["9", "2"])
    assert prompt_choice("Category", CATEGORIES) == CATEGORIES[1]


def test_prompt_yes_no(monkeypatch):
    feed(monkeypatch, ["maybe", "y"])
    assert prompt_yes_no("Continue?") is True
    assert STATUSES[0] == "Planned"
