from datetime import date, datetime

CATEGORIES = ["Leisure", "Business", "Adventure", "Family", "Cultural", "Solo"]
STATUSES = ["Planned", "Booked", "In Progress", "Completed", "Cancelled"]


def prompt_text(message, allow_blank=False, min_length=1, max_length=200):
    while True:
        value = input(message).strip()
        if not value:
            if allow_blank:
                return ""
            print("  ! Input cannot be empty. Try again.")
            continue
        if len(value) < min_length:
            print(f"  ! Minimum {min_length} characters required.")
            continue
        if len(value) > max_length:
            print(f"  ! Maximum {max_length} characters allowed.")
            continue
        return value


def prompt_number(message, value_type=float, minimum=None, maximum=None):
    while True:
        raw = input(message).strip()
        try:
            value = value_type(raw)
        except (ValueError, TypeError):
            print("  ! Please enter a valid number.")
            continue
        if minimum is not None and value < minimum:
            print(f"  ! Value must be >= {minimum}.")
            continue
        if maximum is not None and value > maximum:
            print(f"  ! Value must be <= {maximum}.")
            continue
        return value


def prompt_date(message, allow_past=True):
    while True:
        raw = input(message).strip()
        try:
            parsed = datetime.strptime(raw, "%Y-%m-%d").date()
        except ValueError:
            print("  ! Use format YYYY-MM-DD (e.g., 2026-12-25).")
            continue
        if not allow_past and parsed < date.today():
            print("  ! Date cannot be in the past.")
            continue
        return parsed


def prompt_choice(message, options):
    while True:
        print("\n  " + message)
        for idx, option in enumerate(options, 1):
            print(f"    {idx}. {option}")
        raw = input("  Select (number): ").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return options[int(raw) - 1]
        print("  ! Invalid selection.")


def prompt_yes_no(message):
    while True:
        raw = input(message + " (y/n): ").strip().lower()
        if raw in ("y", "yes"):
            return True
        if raw in ("n", "no"):
            return False
        print("  ! Enter y or n.")


def parse_date(raw):
    return datetime.strptime(str(raw), "%Y-%m-%d").date()


def validate_trip(fields):
    errors = []
    if not str(fields.get("destination", "")).strip():
        errors.append("destination is required")
    start = end = None
    try:
        start = parse_date(fields.get("start_date"))
    except (ValueError, TypeError):
        errors.append("start_date must be YYYY-MM-DD")
    try:
        end = parse_date(fields.get("end_date"))
    except (ValueError, TypeError):
        errors.append("end_date must be YYYY-MM-DD")
    if start and end and end < start:
        errors.append("end_date cannot be before start_date")
    try:
        cost = float(fields.get("estimated_cost", 0))
        if cost < 0:
            errors.append("estimated_cost cannot be negative")
    except (ValueError, TypeError):
        errors.append("estimated_cost must be numeric")
    if str(fields.get("category", "")) not in CATEGORIES:
        errors.append("category is not recognized")
    if str(fields.get("status", "")) not in STATUSES:
        errors.append("status is not recognized")
    return errors
