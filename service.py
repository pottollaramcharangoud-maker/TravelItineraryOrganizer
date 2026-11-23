import re
from datetime import date, datetime
from difflib import SequenceMatcher

from logging_config import get_logger
from models import Trip

logger = get_logger("service")


class ItineraryService:
    def __init__(self, storage, cost_limit=10000.0):
        self.storage = storage
        self.cost_limit = cost_limit
        self.trips = self.storage.load()
        logger.info("Service initialized with %d records", len(self.trips))

    def _persist(self):
        self.storage.save(self.trips)

    def replace_all(self, trips):
        self.trips = list(trips)
        self._persist()
        logger.info("Dataset replaced with %d records", len(self.trips))

    def next_id(self):
        return max((trip.id for trip in self.trips), default=0) + 1

    def add(self, data):
        trip = Trip(
            id=self.next_id(),
            destination=data["destination"],
            start_date=data["start_date"],
            end_date=data["end_date"],
            category=data["category"],
            notes=data["notes"],
            estimated_cost=data["estimated_cost"],
            status=data["status"],
            created_at=datetime.now().isoformat(timespec="seconds"),
        )
        self.trips.append(trip)
        self._persist()
        logger.info("Added trip %d: %s", trip.id, trip.destination)
        return trip

    def find(self, trip_id):
        return next((trip for trip in self.trips if trip.id == trip_id), None)

    def update(self, trip_id, data):
        trip = self.find(trip_id)
        if not trip:
            logger.warning("Update failed: trip %d not found", trip_id)
            return None
        for key, value in data.items():
            setattr(trip, key, value)
        self._persist()
        logger.info("Updated trip %d", trip_id)
        return trip

    def delete(self, trip_id):
        trip = self.find(trip_id)
        if trip:
            self.trips.remove(trip)
            self._persist()
            logger.info("Deleted trip %d", trip_id)
        return trip

    def search(self, keyword="", category=None, status=None, fuzzy=False):
        needle = keyword.strip().lower()
        scored = []
        for trip in self.trips:
            if category and trip.category != category:
                continue
            if status and trip.status != status:
                continue
            score = 0.0
            if needle:
                haystack = f"{trip.destination} {trip.notes}".lower()
                if needle in haystack:
                    score = 1.0
                elif fuzzy:
                    words = re.findall(r"\w+", haystack)
                    score = max(
                        [SequenceMatcher(None, needle, word).ratio() for word in words]
                        + [SequenceMatcher(None, needle, haystack).ratio()],
                        default=0.0,
                    )
                    if score < 0.72:
                        continue
                else:
                    continue
            scored.append((score, trip))
        if needle and fuzzy:
            scored.sort(key=lambda item: (-item[0], item[1].id))
        logger.info("Search '%s' returned %d records (fuzzy=%s)", needle, len(scored), fuzzy)
        return [trip for _, trip in scored]

    def warnings(self):
        today = date.today()
        found = []
        for trip in self.trips:
            timing = trip.timing(today)
            if timing == "Overdue":
                found.append((trip, f"Overdue: trip ended on {trip.end_date}"))
            if timing == "Invalid":
                found.append((trip, "Invalid or missing date range"))
            if trip.estimated_cost > self.cost_limit:
                found.append((trip, f"Cost {trip.estimated_cost:.2f} exceeds limit {self.cost_limit:.2f}"))
            if trip.duration_days() <= 0:
                found.append((trip, "Non-positive trip duration"))
        return found

    def summary(self):
        trips = self.trips
        costs = [trip.estimated_cost for trip in trips]
        by_status = {}
        by_category = {}
        by_timing = {}
        for trip in trips:
            by_status[trip.status] = by_status.get(trip.status, 0) + 1
            by_category[trip.category] = by_category.get(trip.category, 0) + 1
            timing = trip.timing()
            by_timing[timing] = by_timing.get(timing, 0) + 1
        return {
            "total_records": len(trips),
            "total_cost": sum(costs),
            "average_cost": sum(costs) / len(costs) if costs else 0.0,
            "min_cost": min(costs) if costs else 0.0,
            "max_cost": max(costs) if costs else 0.0,
            "total_days": sum(trip.duration_days() for trip in trips),
            "by_status": by_status,
            "by_category": by_category,
            "by_timing": by_timing,
            "warning_count": len(self.warnings()),
            "top_costs": sorted(trips, key=lambda t: t.estimated_cost, reverse=True)[:5],
        }
