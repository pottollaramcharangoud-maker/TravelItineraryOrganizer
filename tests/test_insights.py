from datetime import date, timedelta

import pytest

from insights import InsightsEngine
from service import ItineraryService
from storage import Storage


def fields(destination, start, cost, category="Leisure"):
    end = date.fromisoformat(start) + timedelta(days=3)
    return {
        "destination": destination,
        "start_date": start,
        "end_date": end.isoformat(),
        "category": category,
        "notes": "note",
        "estimated_cost": cost,
        "status": "Planned",
    }


@pytest.fixture
def engine(tmp_path):
    service = ItineraryService(Storage(str(tmp_path / "trips.json"), "json"))
    return InsightsEngine(service)


def test_monthly_spend_groups_by_month(engine):
    engine.service.add(fields("A", "2027-01-05", 100))
    engine.service.add(fields("B", "2027-01-20", 200))
    engine.service.add(fields("C", "2027-02-05", 300))
    assert engine.monthly_spend() == [("2027-01", 300), ("2027-02", 300)]


def test_busiest_month(engine):
    engine.service.add(fields("A", "2027-01-05", 100))
    engine.service.add(fields("B", "2027-02-05", 500))
    assert engine.busiest_month() == ("2027-02", 500)


def test_anomalies_flags_outlier(engine):
    for index in range(6):
        engine.service.add(fields(f"Normal {index}", "2027-01-05", 100))
    engine.service.add(fields("Outlier", "2027-01-06", 10000))
    found = engine.anomalies()
    assert len(found) == 1
    assert found[0][0].destination == "Outlier"


def test_anomalies_empty_for_small_dataset(engine):
    engine.service.add(fields("A", "2027-01-05", 100))
    assert engine.anomalies() == []


def test_upcoming_filters_next_30_days(engine):
    today = date.today()
    soon = today + timedelta(days=10)
    later = today + timedelta(days=90)
    past = today - timedelta(days=10)
    engine.service.add(fields("Soon", soon.isoformat(), 100))
    engine.service.add(fields("Later", later.isoformat(), 200))
    engine.service.add(fields("Past", past.isoformat(), 300))
    assert [trip.destination for trip in engine.upcoming()] == ["Soon"]


def test_forecast_uses_upcoming_count_and_average(engine):
    soon = (date.today() + timedelta(days=5)).isoformat()
    engine.service.add(fields("A", soon, 100))
    engine.service.add(fields("B", "2027-01-05", 300))
    assert engine.upcoming() and engine.forecast() == pytest.approx(200.0)


def test_category_mix(engine):
    engine.service.add(fields("A", "2027-01-05", 100, "Leisure"))
    engine.service.add(fields("B", "2027-01-05", 100, "Business"))
    engine.service.add(fields("C", "2027-01-05", 100, "Leisure"))
    assert engine.category_mix()["Leisure"] == 2


def test_linear_forecast_extrapolates_trend(engine):
    engine.service.add(fields("A", "2027-01-05", 100))
    engine.service.add(fields("B", "2027-02-05", 200))
    engine.service.add(fields("C", "2027-03-05", 300))
    assert engine.linear_forecast() == 400.0


def test_linear_forecast_empty(engine):
    assert engine.linear_forecast() == 0.0


def test_report_contains_all_sections(engine):
    engine.service.add(fields("A", "2027-01-05", 100))
    report = engine.report()
    assert {"monthly_spend", "anomalies", "upcoming", "forecast", "category_mix", "busiest_month"} <= set(report)
