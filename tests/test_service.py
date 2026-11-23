from datetime import date, timedelta

import pytest

from service import ItineraryService
from storage import Storage


def fields(destination="Paris", start="2027-01-01", end="2027-01-05", cost=100.0, category="Leisure", status="Planned", notes="note"):
    return {
        "destination": destination,
        "start_date": start,
        "end_date": end,
        "category": category,
        "notes": notes,
        "estimated_cost": cost,
        "status": status,
    }


@pytest.fixture
def service(tmp_path):
    return ItineraryService(Storage(str(tmp_path / "trips.json"), "json"))


def test_add_assigns_sequential_ids_and_persists(service, tmp_path):
    first = service.add(fields(destination="Paris"))
    second = service.add(fields(destination="Tokyo"))
    assert (first.id, second.id) == (1, 2)
    assert len(Storage(str(tmp_path / "trips.json"), "json").load()) == 2


def test_find_update_delete(service):
    trip = service.add(fields())
    assert service.find(trip.id).destination == "Paris"
    assert service.update(trip.id, {"destination": "Rome"}).destination == "Rome"
    assert service.update(9999, {"destination": "Nowhere"}) is None
    assert service.delete(trip.id).id == trip.id
    assert service.find(trip.id) is None
    assert service.delete(9999) is None


def test_replace_all(service):
    service.add(fields())
    service.replace_all([service.add(fields(destination="Oslo"))])
    assert len(service.trips) == 1
    assert service.trips[0].destination == "Oslo"


def test_search_substring_and_filters(service):
    service.add(fields(destination="Paris", notes="museum", category="Cultural", status="Booked"))
    service.add(fields(destination="Tokyo", notes="shopping", category="Leisure", status="Planned"))
    assert len(service.search("par")) == 1
    assert len(service.search("museum")) == 1
    assert len(service.search("", category="Leisure")) == 1
    assert len(service.search("", status="Booked")) == 1
    assert service.search("missing") == []


def test_search_fuzzy_matches_typo(service):
    service.add(fields(destination="Barcelona", notes="city break"))
    assert service.search("Barcelone") == []
    assert len(service.search("Barcelone", fuzzy=True)) == 1


def test_search_fuzzy_ignores_distant_terms(service):
    service.add(fields(destination="Lisbon"))
    assert service.search("zzzzqqq", fuzzy=True) == []


def test_warnings_detect_overdue_and_cost_limit(service):
    today = date.today()
    past = today - timedelta(days=30)
    service.add(fields(destination="Old", start=past.isoformat(), end=(past + timedelta(days=5)).isoformat()))
    service.add(fields(destination="Expensive", cost=15000.0))
    messages = [message for _, message in service.warnings()]
    assert any("Overdue" in message for message in messages)
    assert any("exceeds limit" in message for message in messages)


def test_warnings_detect_invalid_and_zero_duration(service):
    service.add(fields(destination="Broken", start="not-a-date"))
    service.add(fields(destination="OneDay", start="2027-05-01", end="2027-05-01"))
    messages = [message for _, message in service.warnings()]
    assert any("Invalid" in message for message in messages)
    assert any("Non-positive" in message for message in messages)


def test_summary_metrics_and_distributions(service):
    service.add(fields(destination="A", cost=100.0, category="Leisure", status="Planned"))
    service.add(fields(destination="B", cost=300.0, category="Business", status="Booked"))
    summary = service.summary()
    assert summary["total_records"] == 2
    assert summary["total_cost"] == 400.0
    assert summary["average_cost"] == 200.0
    assert summary["min_cost"] == 100.0
    assert summary["max_cost"] == 300.0
    assert summary["total_days"] == 10
    assert summary["by_category"]["Leisure"] == 1
    assert summary["by_status"]["Booked"] == 1
    assert summary["top_costs"][0].destination == "B"


def test_summary_on_empty_service(service):
    summary = service.summary()
    assert summary["total_records"] == 0
    assert summary["average_cost"] == 0.0
    assert summary["warning_count"] == 0
