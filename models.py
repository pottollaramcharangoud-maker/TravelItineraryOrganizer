from dataclasses import asdict, dataclass
from datetime import date


@dataclass
class Trip:
    id: int
    destination: str
    start_date: str
    end_date: str
    category: str
    notes: str
    estimated_cost: float
    status: str
    created_at: str

    def to_dict(self):
        return asdict(self)

    @staticmethod
    def from_dict(data):
        return Trip(
            id=int(data.get("id", 0)),
            destination=str(data.get("destination", "")),
            start_date=str(data.get("start_date", "")),
            end_date=str(data.get("end_date", "")),
            category=str(data.get("category", "")),
            notes=str(data.get("notes", "")),
            estimated_cost=float(data.get("estimated_cost", 0.0)),
            status=str(data.get("status", "Planned")),
            created_at=str(data.get("created_at", "")),
        )

    def start(self):
        return date.fromisoformat(self.start_date)

    def end(self):
        return date.fromisoformat(self.end_date)

    def duration_days(self):
        try:
            return (self.end() - self.start()).days + 1
        except ValueError:
            return 0

    def timing(self, today=None):
        today = today or date.today()
        if self.status in ("Cancelled", "Completed"):
            return self.status
        try:
            start, end = self.start(), self.end()
        except ValueError:
            return "Invalid"
        if end < today:
            return "Overdue"
        if start > today:
            return "Upcoming"
        return "Ongoing"
