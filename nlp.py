import calendar
import re
from datetime import date, timedelta

from validation import CATEGORIES, STATUSES

STOP_WORDS = (
    "under", "below", "less", "than", "over", "above", "more", "budget", "up", "to",
    "trips", "trip", "show", "find", "list", "showme", "please",
    "this", "next", "week", "month", "before", "after", "with", "in", "at", "for",
) + tuple(CATEGORIES) + tuple(word for status in STATUSES for word in status.split())

AMOUNT = re.compile(r"(?:under|below|less\s+than|budget|up\s+to|over|above|more\s+than)\s*[$₹]?\s*([\d,]+(?:\.\d+)?)")
PLACE = re.compile(r"\b(?:to|in|at|for)\s+([a-z][a-z\s]*?)(?=\s+(?:under|below|over|above|less|more|budget|this|next|with|before|after|planned|booked|completed|cancelled|leisure|business|adventure|family|cultural|solo)|$)")


def _month_bounds(year, month):
    last = calendar.monthrange(year, month)[1]
    return date(year, month, 1), date(year, month, last)


def parse_query(text):
    raw = str(text or "").strip()
    lowered = raw.lower()
    result = {
        "raw": raw,
        "keyword": "",
        "category": None,
        "status": None,
        "max_cost": None,
        "min_cost": None,
        "date_from": None,
        "date_to": None,
    }

    match = PLACE.search(lowered)
    if match:
        words = [word for word in match.group(1).split() if word not in STOP_WORDS]
        result["keyword"] = " ".join(words).strip()

    if not result["keyword"] and lowered:
        candidates = [
            word for word in re.findall(r"[a-z]+", lowered)
            if word not in STOP_WORDS and not word.isdigit()
        ]
        result["keyword"] = " ".join(candidates)

    for category in CATEGORIES:
        if re.search(r"\b" + re.escape(category.lower()) + r"\b", lowered):
            result["category"] = category
            break

    for status in STATUSES:
        if re.search(r"\b" + re.escape(status.lower()) + r"\b", lowered):
            result["status"] = status
            break

    amounts = AMOUNT.findall(lowered)
    if amounts:
        value = float(amounts[0].replace(",", ""))
        upper_tokens = ("under", "below", "less", "budget", "up")
        lower_tokens = ("over", "above", "more")
        if any(token in lowered for token in upper_tokens):
            result["max_cost"] = value
        if any(token in lowered for token in lower_tokens):
            result["min_cost"] = value

    today = date.today()
    if "this week" in lowered:
        result["date_from"] = today
        result["date_to"] = today + timedelta(days=7)
    elif "next week" in lowered:
        start = today + timedelta(days=(7 - today.weekday()))
        result["date_from"] = start
        result["date_to"] = start + timedelta(days=7)
    elif "this month" in lowered:
        result["date_from"], result["date_to"] = _month_bounds(today.year, today.month)
    elif "next month" in lowered:
        year = today.year + (1 if today.month == 12 else 0)
        month = 1 if today.month == 12 else today.month + 1
        result["date_from"], result["date_to"] = _month_bounds(year, month)
    return result


def describe(parsed):
    parts = []
    if parsed["keyword"]:
        parts.append("destination ~ '" + parsed["keyword"] + "'")
    if parsed["category"]:
        parts.append("category=" + parsed["category"])
    if parsed["status"]:
        parts.append("status=" + parsed["status"])
    if parsed["max_cost"] is not None:
        parts.append("cost <= " + f"{parsed['max_cost']:.2f}")
    if parsed["min_cost"] is not None:
        parts.append("cost >= " + f"{parsed['min_cost']:.2f}")
    if parsed["date_from"]:
        parts.append("start " + parsed["date_from"].isoformat() + ".." + parsed["date_to"].isoformat())
    return "; ".join(parts) or "no filters parsed"


def run_query(service, text):
    parsed = parse_query(text)
    matches = service.search(parsed["keyword"], parsed["category"], parsed["status"], fuzzy=True)
    results = []
    for trip in matches:
        if parsed["max_cost"] is not None and trip.estimated_cost > parsed["max_cost"]:
            continue
        if parsed["min_cost"] is not None and trip.estimated_cost < parsed["min_cost"]:
            continue
        if parsed["date_from"]:
            try:
                start = date.fromisoformat(trip.start_date)
            except ValueError:
                continue
            if not (parsed["date_from"] <= start <= parsed["date_to"]):
                continue
        results.append(trip)
    return parsed, results
