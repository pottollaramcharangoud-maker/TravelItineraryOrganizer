import os

RESET = "\033[0m"
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
BOLD = "\033[1m"


def color(text, code):
    return f"{code}{text}{RESET}"


def clear():
    os.system("cls" if os.name == "nt" else "clear")


def banner(fmt="json", count=0):
    print(color("=" * 62, CYAN))
    print(color("       TRAVEL ITINERARY ORGANIZER  |  v1.0", BOLD + CYAN))
    print(color("       StudentLife Hack - Project #52", CYAN))
    print(color("=" * 62, CYAN))
    print(f"  Storage: {fmt.upper()}   Records: {count}")
    print()


def menu(options):
    print(color("  MAIN MENU", BOLD))
    print(color("  " + "-" * 40, CYAN))
    for key, label in options:
        print(f"  {key:>2}. {label}")
    print(color("  " + "-" * 40, CYAN))
    print()


def section(title):
    print()
    print(color("  " + title.upper(), BOLD + GREEN))
    print(color("  " + "=" * len(title), GREEN))


def success(message):
    print(color("  + " + message, GREEN))


def warn(message):
    print(color("  ! " + message, YELLOW))


def error(message):
    print(color("  x " + message, RED))


HEADERS = ["ID", "Destination", "Start", "End", "Category", "Cost", "Status", "Timing"]
WIDTHS = [4, 20, 12, 12, 12, 10, 12, 10]


def _row(cells):
    return " | ".join(str(cell)[:width].ljust(width) for cell, width in zip(cells, WIDTHS))


def table(trips, page_size=12):
    if not trips:
        warn("No records to display.")
        return
    separator = "-+-".join("-" * width for width in WIDTHS)
    pages = (len(trips) + page_size - 1) // page_size
    for page in range(pages):
        chunk = trips[page * page_size:(page + 1) * page_size]
        print()
        print(color(_row(HEADERS), BOLD + CYAN))
        print(separator)
        for trip in chunk:
            print(_row([
                trip.id, trip.destination, trip.start_date, trip.end_date,
                trip.category, f"{trip.estimated_cost:.2f}", trip.status, trip.timing(),
            ]))
        print(f"  Page {page + 1}/{pages} - showing {len(chunk)} of {len(trips)} records")
        if page < pages - 1:
            try:
                input("  Press Enter for next page...")
            except (EOFError, KeyboardInterrupt):
                print()
                return
