import csv
import json
import os

from models import Trip

FIELDNAMES = [
    "id", "destination", "start_date", "end_date", "category",
    "notes", "estimated_cost", "status", "created_at",
]


class Storage:
    def __init__(self, path, fmt="json"):
        self.path = path
        self.fmt = fmt.lower()
        self._ensure()

    def _ensure(self):
        folder = os.path.dirname(self.path)
        if folder:
            os.makedirs(folder, exist_ok=True)
        if not os.path.exists(self.path):
            self._write([])

    def load(self):
        try:
            if self.fmt == "json":
                with open(self.path, "r", encoding="utf-8") as handle:
                    data = json.load(handle)
                if not isinstance(data, list):
                    raise ValueError("JSON root must be a list")
                return [Trip.from_dict(item) for item in data]
            with open(self.path, "r", encoding="utf-8", newline="") as handle:
                reader = csv.DictReader(handle)
                return [Trip.from_dict(row) for row in reader]
        except (FileNotFoundError, json.JSONDecodeError, ValueError, csv.Error, OSError) as exc:
            print(f"  ! Storage read failed ({exc}). Reinitializing clean template.")
            self._write([])
            return []

    def save(self, trips):
        self._write([trip.to_dict() for trip in trips])

    def _write(self, rows):
        if self.fmt == "json":
            with open(self.path, "w", encoding="utf-8") as handle:
                json.dump(rows, handle, indent=2, ensure_ascii=False)
            return
        with open(self.path, "w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
            writer.writeheader()
            for row in rows:
                writer.writerow({key: row.get(key, "") for key in FIELDNAMES})
