import csv
import json
import os

from models import Trip
from storage import FIELDNAMES, Storage


def sample_rows(count=2):
    return [
        {
            "id": index,
            "destination": f"City {index}",
            "start_date": "2027-01-01",
            "end_date": "2027-01-04",
            "category": "Leisure",
            "notes": "note",
            "estimated_cost": 100.0 * index,
            "status": "Planned",
            "created_at": "2026-01-01T00:00:00",
        }
        for index in range(1, count + 1)
    ]


def test_json_round_trip(tmp_path):
    store = Storage(str(tmp_path / "trips.json"), "json")
    store.save([Trip.from_dict(row) for row in sample_rows()])
    loaded = store.load()
    assert len(loaded) == 2
    assert loaded[1].destination == "City 2"
    assert loaded[0].estimated_cost == 100.0


def test_csv_round_trip(tmp_path):
    store = Storage(str(tmp_path / "trips.csv"), "csv")
    store.save([Trip.from_dict(row) for row in sample_rows()])
    loaded = store.load()
    assert [trip.id for trip in loaded] == [1, 2]
    with open(str(tmp_path / "trips.csv"), encoding="utf-8", newline="") as handle:
        assert list(csv.DictReader(handle))[0]["destination"] == "City 1"


def test_first_init_creates_template(tmp_path):
    path = tmp_path / "fresh.json"
    Storage(str(path), "json")
    assert path.exists()
    assert json.loads(path.read_text(encoding="utf-8")) == []


def test_corrupted_json_recovers_with_template(tmp_path, capsys):
    path = tmp_path / "broken.json"
    path.write_text("{not json", encoding="utf-8")
    store = Storage(str(path), "json")
    assert store.load() == []
    assert json.loads(path.read_text(encoding="utf-8")) == []
    assert "Storage read failed" in capsys.readouterr().out


def test_invalid_json_root_recovers(tmp_path):
    path = tmp_path / "object.json"
    path.write_text('{"not": "a list"}', encoding="utf-8")
    assert Storage(str(path), "json").load() == []


def test_lock_file_created(tmp_path):
    path = tmp_path / "locked.json"
    store = Storage(str(path), "json")
    store.save([Trip.from_dict(row) for row in sample_rows(1)])
    assert os.path.exists(str(path) + ".lock")


def test_no_temp_files_left_after_save(tmp_path):
    folder = tmp_path
    Storage(str(folder / "trips.json"), "json").save([Trip.from_dict(row) for row in sample_rows()])
    assert not [name for name in os.listdir(str(folder)) if name.startswith(".tmp_")]


def test_save_creates_backup_and_restore(tmp_path):
    path = tmp_path / "trips.json"
    store = Storage(str(path), "json")
    first = Trip.from_dict(sample_rows(1)[0])
    store.save([first])
    changed = Trip.from_dict(dict(sample_rows(1)[0], destination="Changed"))
    store.save([changed])
    assert os.path.exists(str(path) + ".bak")
    assert store.load()[0].destination == "Changed"
    assert store.restore_backup() is True
    assert store.load()[0].destination == "City 1"


def test_fieldnames_complete():
    assert set(FIELDNAMES) == {
        "id", "destination", "start_date", "end_date",
        "category", "notes", "estimated_cost", "status", "created_at",
    }
