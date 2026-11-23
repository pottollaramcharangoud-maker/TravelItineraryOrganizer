from datetime import date

from models import Trip


def make_trip(**overrides):
    data = {
        "id": 1,
        "destination": "Paris, France",
        "start_date": "2027-01-01",
        "end_date": "2027-01-05",
        "category": "Leisure",
        "notes": "Flight booked",
        "estimated_cost": 1200.0,
        "status": "Planned",
        "created_at": "2026-01-01T00:00:00",
    }
    data.update(overrides)
    return Trip.from_dict(data)


def test_from_dict_applies_defaults():
    trip = Trip.from_dict({"id": 7, "destination": "Goa"})
    assert trip.id == 7
    assert trip.category == ""
    assert trip.estimated_cost == 0.0
    assert trip.status == "Planned"


def test_to_dict_round_trip():
    trip = make_trip()
    assert Trip.from_dict(trip.to_dict()) == trip


def test_duration_days_includes_both_endpoints():
    assert make_trip().duration_days() == 5
    assert make_trip(start_date="2027-01-01", end_date="2027-01-01").duration_days() == 1


def test_duration_days_invalid_range_returns_zero():
    assert make_trip(start_date="bad", end_date="2027-01-05").duration_days() == 0


def test_timing_upcoming():
    trip = make_trip(start_date="2027-03-01", end_date="2027-03-05")
    assert trip.timing(date(2026, 11, 20)) == "Upcoming"


def test_timing_ongoing():
    trip = make_trip(start_date="2026-11-01", end_date="2026-11-30")
    assert trip.timing(date(2026, 11, 20)) == "Ongoing"


def test_timing_overdue():
    trip = make_trip(start_date="2026-10-01", end_date="2026-10-31")
    assert trip.timing(date(2026, 11, 20)) == "Overdue"


def test_timing_completed_and_cancelled():
    today = date(2026, 11, 20)
    assert make_trip(status="Completed").timing(today) == "Completed"
    assert make_trip(status="Cancelled").timing(today) == "Cancelled"


def test_timing_invalid_dates():
    assert make_trip(start_date="oops").timing(date(2026, 11, 20)) == "Invalid"
