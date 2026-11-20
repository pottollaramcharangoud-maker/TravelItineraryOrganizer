from datetime import date, datetime

from models import Trip


class ItineraryService:
    def __init__(self, storage, cost_limit=10000.0):
        self.storage = storage
        self.cost_limit = cost_limit
        self.trips = self.storage.load()

    def _persist(self):
        self.storage.save(self.trips)

    def replace_all(self, trips):
        self.trips = list(trips)
        self._persist()

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
        return trip

    def find(self, trip_id):
        return next((trip for trip in self.trips if trip.id == trip_id), None)

    def update(self, trip_id, data):
        trip = self.find(trip_id)
        if not trip:
            return None
        for key, value in data.items():
            setattr(trip, key, value)
        self._persist()
        return trip

    def delete(self, trip_id):
        trip = self.find(trip_id)
        if trip:
            self.trips.remove(trip)
            self._persist()
        return trip

    def search(self, keyword="", category=None, status=None):
        needle = keyword.strip().lower()
        results = []
        for trip in self.trips:
            if needle and needle not in trip.destination.lower() and needle not in trip.notes.lower():
                continue
            if category and trip.category != category:
                continue
            if status and trip.status != status:
                continue
            results.append(trip)
        return results

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
