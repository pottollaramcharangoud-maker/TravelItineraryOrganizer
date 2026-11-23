import contextlib
import csv
import json
import os
import shutil
import tempfile

try:
    import fcntl
except ImportError:
    fcntl = None
try:
    import msvcrt
except ImportError:
    msvcrt = None

from logging_config import get_logger
from models import Trip

logger = get_logger("storage")

FIELDNAMES = [
    "id", "destination", "start_date", "end_date", "category",
    "notes", "estimated_cost", "status", "created_at",
]


@contextlib.contextmanager
def _locked(path, exclusive=True):
    lock_path = path + ".lock"
    with open(lock_path, "a+", encoding="utf-8") as lock:
        lock.seek(0, os.SEEK_END)
        if lock.tell() == 0:
            lock.write("0")
            lock.flush()
        lock.seek(0)
        if fcntl:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH)
        elif msvcrt:
            msvcrt.locking(lock.fileno(), msvcrt.LK_LOCK if exclusive else msvcrt.LK_RLCK, 1)
        try:
            yield
        finally:
            if fcntl:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
            elif msvcrt:
                lock.seek(0)
                msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)


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
        records = []
        try:
            with _locked(self.path, exclusive=False):
                if os.path.exists(self.path):
                    if self.fmt == "json":
                        with open(self.path, "r", encoding="utf-8") as handle:
                            data = json.load(handle)
                        if not isinstance(data, list):
                            raise ValueError("JSON root must be a list")
                        records = [Trip.from_dict(item) for item in data]
                    else:
                        with open(self.path, "r", encoding="utf-8", newline="") as handle:
                            reader = csv.DictReader(handle)
                            records = [Trip.from_dict(row) for row in reader]
        except (FileNotFoundError, json.JSONDecodeError, ValueError, csv.Error, OSError) as exc:
            logger.warning("Storage read failed for %s: %s", self.path, exc)
            print(f"  ! Storage read failed ({exc}). Reinitializing clean template.")
            self._write([])
            return []
        logger.info("Loaded %d records from %s", len(records), self.path)
        return records

    def save(self, trips):
        self._write([trip.to_dict() for trip in trips])

    def restore_backup(self):
        backup = self.path + ".bak"
        if not os.path.exists(backup):
            return False
        shutil.copy2(backup, self.path)
        logger.warning("Restored %s from backup", self.path)
        return True

    def _write(self, rows):
        folder = os.path.dirname(self.path) or "."
        with _locked(self.path):
            descriptor, temporary = tempfile.mkstemp(prefix=".tmp_", dir=folder)
            try:
                with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as handle:
                    if self.fmt == "json":
                        json.dump(rows, handle, indent=2, ensure_ascii=False)
                    else:
                        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
                        writer.writeheader()
                        for row in rows:
                            writer.writerow({key: row.get(key, "") for key in FIELDNAMES})
                if os.path.exists(self.path):
                    shutil.copy2(self.path, self.path + ".bak")
                os.replace(temporary, self.path)
                logger.info("Saved %d records to %s", len(rows), self.path)
            except Exception:
                if os.path.exists(temporary):
                    os.remove(temporary)
                raise
