import json
import os
import sqlite3

from logging_config import get_logger
from models import Trip
from storage import Storage

logger = get_logger("sqlite_storage")


class SQLiteStorage:
    def __init__(self, path):
        self.path = path
        folder = os.path.dirname(path)
        if folder:
            os.makedirs(folder, exist_ok=True)
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute(
                "CREATE TABLE IF NOT EXISTS trips (id INTEGER PRIMARY KEY, payload TEXT NOT NULL)"
            )

    def _connect(self):
        return sqlite3.connect(self.path, timeout=15)

    def load(self):
        try:
            with self._connect() as connection:
                rows = connection.execute("SELECT payload FROM trips ORDER BY id").fetchall()
            trips = [Trip.from_dict(json.loads(row[0])) for row in rows]
            logger.info("Loaded %d records from %s", len(trips), self.path)
            return trips
        except (sqlite3.Error, ValueError, json.JSONDecodeError, TypeError) as exc:
            logger.warning("SQLite read failed for %s: %s", self.path, exc)
            return []

    def save(self, trips):
        payload = [(trip.id, json.dumps(trip.to_dict(), ensure_ascii=False)) for trip in trips]
        try:
            with self._connect() as connection:
                with connection:
                    connection.execute("DELETE FROM trips")
                    connection.executemany("INSERT INTO trips (id, payload) VALUES (?, ?)", payload)
            logger.info("Saved %d records to %s", len(payload), self.path)
        except sqlite3.Error as exc:
            logger.error("SQLite write failed for %s: %s", self.path, exc)
            raise


def create_storage(config, data_dir):
    if config.get("backend") == "sqlite":
        return SQLiteStorage(os.path.join(data_dir, "itinerary.db"))
    fmt = config.get("format", "json")
    if fmt not in ("json", "csv"):
        fmt = "json"
    return Storage(os.path.join(data_dir, f"itinerary.{fmt}"), fmt)


def storage_label(config):
    if config.get("backend") == "sqlite":
        return "SQLite"
    return str(config.get("format", "json")).upper()
