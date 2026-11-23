from collections import Counter
from datetime import date, timedelta
from statistics import mean, pstdev


class InsightsEngine:
    def __init__(self, service):
        self.service = service

    def _date(self, value):
        try:
            year, month, day = map(int, str(value).split("-"))
            return date(year, month, day)
        except (ValueError, TypeError):
            return None

    def monthly_spend(self):
        totals = Counter()
        for trip in self.service.trips:
            day = self._date(trip.start_date)
            if day:
                totals[day.strftime("%Y-%m")] += trip.estimated_cost
        return sorted(totals.items())

    def anomalies(self):
        costs = [trip.estimated_cost for trip in self.service.trips if trip.estimated_cost > 0]
        if len(costs) < 3:
            return []
        average = mean(costs)
        deviation = pstdev(costs)
        if deviation == 0:
            return []
        found = []
        for trip in self.service.trips:
            if trip.estimated_cost <= 0:
                continue
            score = (trip.estimated_cost - average) / deviation
            if score > 1.8:
                found.append((trip, score))
        return sorted(found, key=lambda item: -item[1])

    def upcoming(self, days=30):
        today = date.today()
        limit = today + timedelta(days=days)
        found = []
        for trip in self.service.trips:
            day = self._date(trip.start_date)
            if day and today <= day <= limit:
                found.append(trip)
        return sorted(found, key=lambda trip: trip.start_date)

    def forecast(self, days=30):
        upcoming = self.upcoming(days)
        costs = [trip.estimated_cost for trip in self.service.trips if trip.estimated_cost > 0]
        return len(upcoming) * (mean(costs) if costs else 0.0)

    def category_mix(self):
        return Counter(trip.category for trip in self.service.trips)

    def busiest_month(self):
        spend = self.monthly_spend()
        return max(spend, key=lambda item: item[1]) if spend else None

    def report(self):
        return {
            "monthly_spend": self.monthly_spend(),
            "anomalies": self.anomalies(),
            "upcoming": self.upcoming(),
            "forecast": self.forecast(),
            "category_mix": self.category_mix(),
            "busiest_month": self.busiest_month(),
        }
