import json

from reports import (
    bar_chart,
    export_audit,
    export_csv,
    export_json,
    export_markdown,
    summary_lines,
)
from service import ItineraryService
from storage import Storage


def make_service(tmp_path):
    service = ItineraryService(Storage(str(tmp_path / "trips.json"), "json"))
    service.add({
        "destination": "Paris, France",
        "start_date": "2027-01-01",
        "end_date": "2027-01-05",
        "category": "Leisure",
        "notes": "museum",
        "estimated_cost": 1200.0,
        "status": "Planned",
    })
    return service


def test_summary_lines_contain_metrics(tmp_path):
    summary = make_service(tmp_path).summary()
    text = "\n".join(summary_lines(summary))
    assert "Total records      : 1" in text
    assert "1200.00" in text


def test_bar_chart_empty():
    assert bar_chart({}) == ["  (no data)"]


def test_bar_chart_scales_to_maximum():
    lines = bar_chart({"A": 4, "B": 2}, width=4)
    assert any(line.strip().startswith("A") and "####" in line for line in lines)
    assert any(line.strip().startswith("B") and "##" in line for line in lines)


def test_export_markdown(tmp_path):
    service = make_service(tmp_path)
    path = tmp_path / "report.md"
    export_markdown(service.summary(), service.trips, service.warnings(), str(path))
    content = path.read_text(encoding="utf-8")
    assert "# Travel Itinerary Organizer" in content
    assert "Paris, France" in content
    assert "## Warnings" in content


def test_export_csv(tmp_path):
    service = make_service(tmp_path)
    path = tmp_path / "report.csv"
    export_csv(service.trips, str(path))
    assert "Paris, France" in path.read_text(encoding="utf-8")


def test_export_json(tmp_path):
    service = make_service(tmp_path)
    path = tmp_path / "report.json"
    export_json(service.trips, str(path))
    assert json.loads(path.read_text(encoding="utf-8"))[0]["destination"] == "Paris, France"


def test_export_audit(tmp_path):
    service = make_service(tmp_path)
    path = tmp_path / "audit.txt"
    export_audit(service.summary(), service.trips, service.warnings(), str(path))
    content = path.read_text(encoding="utf-8")
    assert "AUDIT LOG" in content
    assert "Paris, France" in content
