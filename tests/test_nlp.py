from datetime import date, timedelta

from nlp import describe, parse_query, run_query
from service import ItineraryService
from storage import Storage


def trip(destination, cost, category="Leisure", status="Planned", days=10):
    start = date.today() + timedelta(days=days)
    return {
        "destination": destination,
        "start_date": start.isoformat(),
        "end_date": (start + timedelta(days=3)).isoformat(),
        "category": category,
        "notes": "test",
        "estimated_cost": cost,
        "status": status,
    }


def service_with(tmp_path):
    service = ItineraryService(Storage(str(tmp_path / "trips.json"), "json"))
    service.add(trip("Paris, France", 1000, "Cultural", "Booked", 5))
    service.add(trip("Tokyo, Japan", 4000, "Adventure", "Planned", 60))
    return service


def test_parse_query_extracts_destination():
    assert parse_query("trips to Paris under 2000")["keyword"] == "paris"


def test_parse_query_extracts_cost_filters():
    parsed = parse_query("show trips under 3000")
    assert parsed["max_cost"] == 3000
    assert parsed["min_cost"] is None


def test_parse_query_extracts_min_cost():
    assert parse_query("trips over 2000")["min_cost"] == 2000


def test_parse_query_extracts_category_and_status():
    parsed = parse_query("booked cultural trips")
    assert parsed["category"] == "Cultural"
    assert parsed["status"] == "Booked"


def test_parse_query_extracts_next_month_range():
    parsed = parse_query("trips next month")
    assert parsed["date_from"] is not None
    assert parsed["date_to"] >= parsed["date_from"]


def test_describe_produces_readable_summary():
    parsed = parse_query("trips to Paris under 2000")
    text = describe(parsed)
    assert "paris" in text
    assert "2000.00" in text


def test_run_query_applies_all_filters(tmp_path):
    service = service_with(tmp_path)
    parsed, results = run_query(service, "trips to Paris under 2000 booked")
    assert parsed["keyword"] == "paris"
    assert len(results) == 1
    assert results[0].destination == "Paris, France"


def test_run_query_rejects_over_budget(tmp_path):
    service = service_with(tmp_path)
    _, results = run_query(service, "trips under 2000")
    assert all(trip.estimated_cost <= 2000 for trip in results)


def test_run_query_fuzzy_destination(tmp_path):
    service = service_with(tmp_path)
    _, results = run_query(service, "Paris")
    assert len(results) == 1
