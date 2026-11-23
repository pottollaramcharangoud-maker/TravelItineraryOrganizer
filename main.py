import csv
import json
import os
from datetime import datetime

import reports
import ui
from insights import InsightsEngine
from logging_config import get_logger
from nlp import describe, run_query
from models import Trip
from service import ItineraryService
from sqlite_storage import create_storage, storage_label
from storage import Storage
from validation import (
    CATEGORIES,
    STATUSES,
    prompt_choice,
    prompt_date,
    prompt_number,
    prompt_text,
    prompt_yes_no,
    validate_trip,
)

logger = get_logger("console")

BASE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE, "data")
EXPORT_DIR = os.path.join(BASE, "exports")
CONFIG_PATH = os.path.join(DATA_DIR, "config.json")

MENU = [
    ("1", "Add trip"),
    ("2", "View all trips"),
    ("3", "Search / filter trips"),
    ("4", "Update trip"),
    ("5", "Delete trip"),
    ("6", "Summary & analytics"),
    ("7", "Threshold warnings"),
    ("8", "Export reports"),
    ("9", "Bulk import CSV"),
    ("10", "Seed sample data"),
    ("11", "Toggle storage format (JSON/CSV)"),
    ("12", "Launch graphical interface (Tkinter)"),
    ("13", "Smart insights"),
    ("14", "Toggle database backend (File/SQLite)"),
    ("0", "Exit"),
]


def load_config():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as handle:
            config = json.load(handle)
        if config.get("format") not in ("json", "csv"):
            raise ValueError("invalid format")
        return config
    except (FileNotFoundError, json.JSONDecodeError, ValueError, OSError):
        return {"format": "json", "cost_limit": 10000.0, "backend": "file"}


def save_config(config):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as handle:
        json.dump(config, handle, indent=2)


class App:
    def __init__(self):
        self.config = load_config()
        self.fmt = self.config.get("format", "json")
        self.cost_limit = float(self.config.get("cost_limit", 10000.0))
        self.storage = create_storage(self.config, DATA_DIR)
        self.service = ItineraryService(self.storage, self.cost_limit)

    def _storage_path(self):
        return os.path.join(DATA_DIR, f"itinerary.{self.fmt}")

    def run(self):
        logger.info("Console application started with %d records", len(self.service.trips))
        while True:
            ui.clear()
            ui.banner(storage_label(self.config), len(self.service.trips))
            ui.menu(MENU)
            try:
                choice = input("  Select option: ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                ui.success("Goodbye. Data saved.")
                break
            if choice == "0":
                ui.success("Goodbye. Data saved.")
                break
            action = {
                "1": self.add_trip,
                "2": self.view_all,
                "3": self.search,
                "4": self.update_trip,
                "5": self.delete_trip,
                "6": self.summary,
                "7": self.warnings,
                "8": self.export,
                "9": self.import_csv,
                "10": self.seed,
                "11": self.toggle_storage,
                "12": self.launch_gui,
                "13": self.insights,
                "14": self.toggle_backend,
            }.get(choice)
            if action:
                try:
                    action()
                except (EOFError, KeyboardInterrupt):
                    ui.warn("Operation cancelled.")
            else:
                ui.error("Invalid option. Try again.")
            try:
                input("\n  Press Enter to continue...")
            except (EOFError, KeyboardInterrupt):
                ui.success("Goodbye. Data saved.")
                break

    def add_trip(self):
        ui.section("Add New Trip")
        destination = prompt_text("  Destination: ")
        start = prompt_date("  Start date (YYYY-MM-DD): ")
        end = prompt_date("  End date (YYYY-MM-DD): ")
        while end < start:
            ui.warn("End date must be on or after start date.")
            end = prompt_date("  End date (YYYY-MM-DD): ")
        category = prompt_choice("Category", CATEGORIES)
        notes = prompt_text("  Notes (optional): ", allow_blank=True, max_length=300)
        cost = prompt_number("  Estimated cost: ", minimum=0.0)
        status = prompt_choice("Status", STATUSES)
        fields = {
            "destination": destination,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "category": category,
            "notes": notes,
            "estimated_cost": cost,
            "status": status,
        }
        errors = validate_trip(fields)
        if errors:
            for item in errors:
                ui.error(item)
            return
        trip = self.service.add(fields)
        ui.success(f"Trip #{trip.id} added to {trip.destination}.")

    def view_all(self):
        ui.section("All Trips")
        trips = sorted(self.service.trips, key=lambda trip: trip.id)
        ui.table(trips)

    def search(self):
        ui.section("Search / Filter")
        if prompt_yes_no("  Use natural-language query (e.g. 'trips to Paris under 3000 next month')?"):
            text = prompt_text("  Query: ")
            parsed, results = run_query(self.service, text)
            ui.success(describe(parsed))
            ui.success(f"Found {len(results)} matching record(s).")
            ui.table(sorted(results, key=lambda trip: trip.id))
            return
        keyword = prompt_text("  Keyword in destination/notes (blank=any): ", allow_blank=True)
        category = None
        status = None
        if prompt_yes_no("  Filter by category?"):
            category = prompt_choice("Category", CATEGORIES)
        if prompt_yes_no("  Filter by status?"):
            status = prompt_choice("Status", STATUSES)
        fuzzy = bool(keyword) and prompt_yes_no("  Enable fuzzy matching?")
        results = self.service.search(keyword, category, status, fuzzy=fuzzy)
        ui.success(f"Found {len(results)} matching record(s).")
        ui.table(sorted(results, key=lambda trip: trip.id))

    def _edited_value(self, label, current, kind="text"):
        if kind == "text":
            value = input(f"  {label} [{current}] (blank=keep): ").strip()
            return value or current
        if kind == "number":
            raw = input(f"  {label} [{current}] (blank=keep): ").strip()
            if not raw:
                return current
            while True:
                try:
                    return float(raw)
                except ValueError:
                    ui.warn("Enter a valid number or leave blank.")
                    raw = input(f"  {label} [{current}]: ").strip()
        if kind == "date":
            raw = input(f"  {label} [{current}] (blank=keep): ").strip()
            if not raw:
                return current
            while True:
                try:
                    return prompt_date_value(raw)
                except ValueError:
                    ui.warn("Use YYYY-MM-DD.")
                    raw = input(f"  {label} [{current}]: ").strip()
        return current

    def update_trip(self):
        ui.section("Update Trip")
        trip_id = prompt_number("  Trip ID: ", value_type=int, minimum=1)
        trip = self.service.find(trip_id)
        if not trip:
            ui.error(f"Trip #{trip_id} not found.")
            return
        ui.table([trip])
        print()
        updated = {
            "destination": self._edited_value("Destination", trip.destination),
            "start_date": self._edited_value("Start date", trip.start_date, "date"),
            "end_date": self._edited_value("End date", trip.end_date, "date"),
            "category": prompt_choice("Category (choose current to keep)", CATEGORIES + [trip.category]),
            "notes": self._edited_value("Notes", trip.notes),
            "estimated_cost": self._edited_value("Estimated cost", trip.estimated_cost, "number"),
            "status": prompt_choice("Status (choose current to keep)", STATUSES + [trip.status]),
        }
        errors = validate_trip(updated)
        if errors:
            for item in errors:
                ui.error(item)
            return
        self.service.update(trip_id, updated)
        ui.success(f"Trip #{trip_id} updated.")

    def delete_trip(self):
        ui.section("Delete Trip")
        trip_id = prompt_number("  Trip ID: ", value_type=int, minimum=1)
        trip = self.service.find(trip_id)
        if not trip:
            ui.error(f"Trip #{trip_id} not found.")
            return
        ui.table([trip])
        if prompt_yes_no(f"  Delete trip #{trip_id} ({trip.destination})?"):
            self.service.delete(trip_id)
            ui.success(f"Trip #{trip_id} deleted.")
        else:
            ui.warn("Deletion cancelled.")

    def summary(self):
        ui.section("Summary & Analytics")
        data = self.service.summary()
        for line in reports.summary_lines(data):
            print(line)
        for title, key in (
            ("By Category", "by_category"),
            ("By Status", "by_status"),
            ("By Timing", "by_timing"),
        ):
            print()
            print(ui.color(f"  {title}", ui.BOLD + ui.CYAN))
            for line in reports.bar_chart(data[key]):
                print(line)
        print()
        print(ui.color("  Highest Estimated Costs", ui.BOLD + ui.CYAN))
        ui.table(data["top_costs"])

    def warnings(self):
        ui.section("Threshold Warnings")
        found = self.service.warnings()
        if not found:
            ui.success("No threshold breaches detected.")
            return
        ui.warn(f"{len(found)} warning(s) found:")
        for trip, message in found:
            print(f"  [{trip.id}] {trip.destination}: {message}")

    def export(self):
        ui.section("Export Reports")
        kind = prompt_choice("Export format", ["Markdown", "CSV", "Audit log", "JSON"])
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        summary = self.service.summary()
        trips = list(self.service.trips)
        warnings = self.service.warnings()
        suffix = {"Markdown": "md", "CSV": "csv", "Audit log": "txt", "JSON": "json"}[kind]
        path = os.path.join(EXPORT_DIR, f"itinerary_summary_{stamp}.{suffix}")
        if kind == "Markdown":
            reports.export_markdown(summary, trips, warnings, path)
        elif kind == "CSV":
            reports.export_csv(trips, path)
        elif kind == "Audit log":
            reports.export_audit(summary, trips, warnings, path)
        else:
            reports.export_json(trips, path)
        ui.success(f"Report exported to {path}")

    def import_csv(self):
        ui.section("Bulk Import CSV")
        default = os.path.join(DATA_DIR, "sample_trips.csv")
        path = input(f"  CSV path (blank for {default}): ").strip() or default
        try:
            with open(path, "r", encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
        except (FileNotFoundError, OSError, csv.Error) as exc:
            ui.error(f"Cannot read CSV: {exc}")
            return
        valid, errors = [], []
        next_id = self.service.next_id()
        for line, row in enumerate(rows, start=2):
            problems = validate_trip(row)
            if problems:
                errors.append((line, "; ".join(problems)))
                continue
            row["id"] = next_id
            row["estimated_cost"] = float(row["estimated_cost"])
            row["created_at"] = datetime.now().isoformat(timespec="seconds")
            valid.append(Trip.from_dict(row))
            next_id += 1
        if valid:
            self.service.replace_all(list(self.service.trips) + valid)
        ui.success(f"Imported {len(valid)} valid row(s); {len(errors)} rejected.")
        if errors:
            print("  Row-by-row error log:")
            for line, reason in errors:
                print(f"    Row {line}: {reason}")

    def seed(self):
        ui.section("Seed Sample Data")
        import seed

        rows = seed.generate(40)
        csv_path, json_path = seed.write_samples(rows, DATA_DIR)
        ui.success(f"Sample datasets written: {csv_path}, {json_path}")
        if prompt_yes_no("  Replace current dataset with these 40 records?"):
            self.service.replace_all([Trip.from_dict(row) for row in rows])
            ui.success("Dataset seeded with 40 records.")
        elif prompt_yes_no("  Append them to current dataset?"):
            starting = self.service.next_id()
            for offset, row in enumerate(rows):
                row["id"] = starting + offset
            self.service.replace_all(list(self.service.trips) + [Trip.from_dict(row) for row in rows])
            ui.success("Sample records appended.")

    def insights(self):
        ui.section("Smart Insights")
        engine = InsightsEngine(self.service)
        report = engine.report()
        print("  Monthly spend trend:")
        for month, total in report["monthly_spend"]:
            print(f"    {month} : {total:.2f}")
        busiest = report["busiest_month"]
        if busiest:
            print(f"  Busiest month: {busiest[0]} ({busiest[1]:.2f})")
        print(f"  Upcoming trips (next 30 days): {len(report['upcoming'])}")
        print(f"  Forecast spend: {report['forecast']:.2f}")
        print(f"  Projected next-month spend (trend): {report['projected_spend']:.2f}")
        print(f"  Cost anomalies: {len(report['anomalies'])}")
        for trip, score in report["anomalies"]:
            print(f"    #{trip.id} {trip.destination}: {score:.2f} sigma")

    def toggle_backend(self):
        new_backend = "sqlite" if self.config.get("backend", "file") != "sqlite" else "file"
        target = create_storage({"backend": new_backend, "format": self.fmt}, DATA_DIR)
        target.save(self.service.trips)
        self.config["backend"] = new_backend
        self.storage = target
        self.service = ItineraryService(self.storage, self.cost_limit)
        save_config(self.config)
        label = storage_label(self.config)
        logger.info("Storage backend switched to %s", label)
        ui.success(f"Database backend switched to {label} (data preserved).")

    def launch_gui(self):
        try:
            import gui
        except ImportError as exc:
            ui.error(f"Cannot start GUI: {exc}")
            return
        ui.success("Launching graphical interface...")
        gui.launch()

    def toggle_storage(self):
        new_fmt = "csv" if self.fmt == "json" else "json"
        target = Storage(os.path.join(DATA_DIR, f"itinerary.{new_fmt}"), new_fmt)
        target.save(self.service.trips)
        self.fmt = new_fmt
        self.storage = target
        self.service = ItineraryService(self.storage, self.cost_limit)
        self.config["format"] = new_fmt
        save_config(self.config)
        ui.success(f"Storage switched to {new_fmt.upper()} (data preserved).")


def prompt_date_value(raw):
    from datetime import datetime

    return datetime.strptime(raw, "%Y-%m-%d").date()


if __name__ == "__main__":
    App().run()
