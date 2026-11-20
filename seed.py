import csv
import json
import random
from datetime import date, datetime, timedelta

from storage import FIELDNAMES
from validation import CATEGORIES, STATUSES

DESTINATIONS = [
    "Paris, France", "Tokyo, Japan", "New York, USA", "London, UK", "Dubai, UAE",
    "Bangkok, Thailand", "Rome, Italy", "Sydney, Australia", "Singapore", "Istanbul, Turkey",
    "Goa, India", "Jaipur, India", "Kerala, India", "Himalayas, Nepal", "Bali, Indonesia",
    "Barcelona, Spain", "Amsterdam, Netherlands", "Seoul, South Korea", "Cairo, Egypt", "Cape Town, South Africa",
]

NOTES = [
    "Flight and hotel booked", "Awaiting visa approval", "Weekend getaway with friends",
    "Conference attendance", "Family vacation planned", "Budget under review",
    "Adventure trekking expedition", "Museums and local cuisine", "Beach resort stay",
    "Client meetings scheduled", "Early-bird discount applied", "Flexible travel dates",
]


def generate(count=40):
    random.seed(52)
    today = date.today()
    rows = []
    for index in range(1, count + 1):
        start = today + timedelta(days=random.randint(-75, 200))
        end = start + timedelta(days=random.randint(1, 21))
        cost = round(random.uniform(80, 4800), 2)
        if index == 5:
            cost = 0.0
        if index == 12:
            cost = 10000.0
        if index == 20:
            end = start
        row = {
            "id": index,
            "destination": random.choice(DESTINATIONS),
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "category": random.choice(CATEGORIES),
            "notes": random.choice(NOTES),
            "estimated_cost": cost,
            "status": random.choice(STATUSES),
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
        rows.append(row)
    return rows


def write_samples(rows, folder):
    csv_path = f"{folder}/sample_trips.csv"
    json_path = f"{folder}/sample_trips.json"
    with open(csv_path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
    with open(json_path, "w", encoding="utf-8") as handle:
        json.dump(rows, handle, indent=2, ensure_ascii=False)
    return csv_path, json_path
