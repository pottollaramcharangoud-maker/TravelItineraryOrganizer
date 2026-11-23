from sqlite_storage import SQLiteStorage, create_storage, storage_label
from storage import Storage


def sample_trip():
    return {
        "id": 1,
        "destination": "Lisbon, Portugal",
        "start_date": "2027-06-01",
        "end_date": "2027-06-08",
        "category": "Cultural",
        "notes": "tram rides",
        "estimated_cost": 1800.0,
        "status": "Booked",
        "created_at": "2026-01-01T00:00:00",
    }


def test_sqlite_round_trip(tmp_path):
    store = SQLiteStorage(str(tmp_path / "trips.db"))
    from models import Trip

    store.save([Trip.from_dict(sample_trip())])
    loaded = store.load()
    assert len(loaded) == 1
    assert loaded[0].destination == "Lisbon, Portugal"
    assert loaded[0].estimated_cost == 1800.0


def test_sqlite_replace_is_transactional(tmp_path):
    from models import Trip

    store = SQLiteStorage(str(tmp_path / "trips.db"))
    first = sample_trip()
    second = dict(sample_trip(), id=2, destination="Oslo")
    store.save([Trip.from_dict(first), Trip.from_dict(second)])
    store.save([Trip.from_dict(second)])
    assert [trip.id for trip in store.load()] == [2]


def test_sqlite_recovers_from_bad_payload(tmp_path):
    import sqlite3

    path = str(tmp_path / "trips.db")
    store = SQLiteStorage(path)
    with sqlite3.connect(path) as connection:
        connection.execute("INSERT INTO trips (id, payload) VALUES (9, 'not json')")
    assert store.load() == []


def test_create_storage_file_backend(tmp_path):
    store = create_storage({"backend": "file", "format": "json"}, str(tmp_path))
    assert isinstance(store, Storage)


def test_create_storage_sqlite_backend(tmp_path):
    store = create_storage({"backend": "sqlite", "format": "json"}, str(tmp_path))
    assert isinstance(store, SQLiteStorage)


def test_storage_label():
    assert storage_label({"backend": "sqlite"}) == "SQLite"
    assert storage_label({"backend": "file", "format": "csv"}) == "CSV"
