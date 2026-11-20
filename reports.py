import csv
import json
from datetime import datetime

from storage import FIELDNAMES


def bar_chart(counts, width=40):
    if not counts:
        return ["  (no data)"]
    maximum = max(counts.values())
    lines = []
    for label, value in sorted(counts.items(), key=lambda item: item[1], reverse=True):
        filled = int(width * value / maximum) if maximum else 0
        lines.append(f"  {label:<14} {('#' * filled):<{width}} {value}")
    return lines


def summary_lines(summary):
    return [
        f"  Total records      : {summary['total_records']}",
        f"  Total cost         : {summary['total_cost']:.2f}",
        f"  Average cost       : {summary['average_cost']:.2f}",
        f"  Min / Max cost     : {summary['min_cost']:.2f} / {summary['max_cost']:.2f}",
        f"  Total planned days : {summary['total_days']}",
        f"  Active warnings    : {summary['warning_count']}",
    ]


def export_markdown(summary, trips, warnings, path):
    lines = [
        "# Travel Itinerary Organizer - Summary Report",
        "",
        f"Generated: {datetime.now().isoformat(timespec='seconds')}",
        "",
        "## Key Metrics",
        "",
    ]
    lines += [line.strip() for line in summary_lines(summary)]
    lines += ["", "## Distribution by Category", ""]
    lines += [line.strip() for line in bar_chart(summary["by_category"])]
    lines += ["", "## Record Details", "", "| ID | Destination | Start | End | Category | Cost | Status |", "|---|---|---|---|---|---|---|"]
    for trip in trips:
        lines.append(
            f"| {trip.id} | {trip.destination} | {trip.start_date} | {trip.end_date} | "
            f"{trip.category} | {trip.estimated_cost:.2f} | {trip.status} |"
        )
    lines += ["", "## Warnings", ""]
    lines += [f"- {trip.destination}: {message}" for trip, message in warnings] or ["- None"]
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def export_audit(summary, trips, warnings, path):
    lines = [
        "TRAVEL ITINERARY ORGANIZER - AUDIT LOG",
        "=" * 48,
        f"Timestamp : {datetime.now().isoformat(timespec='seconds')}",
        f"Records   : {summary['total_records']}",
        f"Total cost: {summary['total_cost']:.2f}",
        f"Warnings  : {summary['warning_count']}",
        "-" * 48,
    ]
    for trip in trips:
        lines.append(f"[{trip.id}] {trip.destination} | {trip.start_date} -> {trip.end_date} | {trip.category} | {trip.estimated_cost:.2f} | {trip.status}")
    lines.append("-" * 48)
    for trip, message in warnings:
        lines.append(f"WARN [{trip.id}] {trip.destination}: {message}")
    if not warnings:
        lines.append("No warnings recorded.")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def export_csv(trips, path):
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        for trip in trips:
            writer.writerow(trip.to_dict())


def export_json(trips, path):
    with open(path, "w", encoding="utf-8") as handle:
        json.dump([trip.to_dict() for trip in trips], handle, indent=2, ensure_ascii=False)
