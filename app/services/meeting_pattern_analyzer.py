"""Intelligente Termin-Muster-Erkennung basierend auf historischen Daten."""
import logging
from datetime import date, timedelta
from collections import defaultdict
from sqlalchemy.orm import Session

from app.models.models import Urlaub

logger = logging.getLogger(__name__)


class MeetingPatternAnalyzer:
    """Analysiert historische Termine und erstellt intelligente Vorschläge."""

    # Historische Daten (manuell gepflegt)
    HISTORICAL_MEETINGS = {
        "GR": {
            2026: [date(2026, 3, 25), date(2026, 6, 25), date(2026, 9, 29), date(2026, 12, 3)],
            2025: [date(2025, 2, 26), date(2025, 3, 31), date(2025, 6, 26), date(2025, 9, 30), date(2025, 11, 19), date(2025, 12, 10)],
            2024: [date(2024, 3, 12), date(2024, 6, 27), date(2024, 9, 19), date(2024, 9, 24), date(2024, 12, 10)],
            2023: [date(2023, 2, 28), date(2023, 3, 28), date(2023, 6, 6), date(2023, 6, 27), date(2023, 9, 25), date(2023, 11, 14), date(2023, 12, 12)],
            2022: [date(2022, 3, 29), date(2022, 5, 25), date(2022, 6, 28), date(2022, 9, 27), date(2022, 11, 10), date(2022, 12, 13)],
        },
        "STR": {
            2026: [date(2026, 2, 11), date(2026, 3, 18), date(2026, 5, 4), date(2026, 6, 16), date(2026, 8, 25), date(2026, 9, 23), date(2026, 10, 15), date(2026, 11, 26)],
        },
    }

    # Keine starren Blockierungen — nur echte Urlaubsdaten aus DB!

    def __init__(self, db: Session = None):
        self.db = db

    def get_forbidden_dates_for_person(self, person_id: int) -> set[date]:
        """Hole alle Urlaubsdaten für eine Person."""
        if not self.db:
            return set()

        urlaube = self.db.query(Urlaub).filter(Urlaub.person_id == person_id).all()
        forbidden = set()

        for urlaub in urlaube:
            current = urlaub.von
            while current <= urlaub.bis:
                forbidden.add(current)
                current += timedelta(days=1)

        return forbidden

    def analyze_meeting_pattern(self, meeting_type: str) -> dict:
        """Analysiere historische Muster für Sitzungstyp."""
        if meeting_type not in self.HISTORICAL_MEETINGS:
            return {}

        meetings = self.HISTORICAL_MEETINGS[meeting_type]
        month_distribution = defaultdict(list)
        weekday_distribution = defaultdict(int)

        for year, dates in meetings.items():
            for dt in dates:
                month_distribution[dt.month].append(dt.day)
                weekday_distribution[dt.weekday()] += 1

        return {
            "month_distribution": dict(month_distribution),
            "weekday_distribution": dict(weekday_distribution),
            "typical_months": sorted([m for m in month_distribution.keys() if m not in []]),
        }

    # Bevorzugte Nachmittags-Stunden (höhere Priorität als frühe Slots wie 07:00)
    PREFERRED_HOURS = [16, 17, 18, 19, 15, 14]
    # Quorum: Mindestanzahl verfügbarer Personen, damit eine Stunde als Kandidat zählt
    QUORUM = 10

    def _rank_hours(self, hour_counts: dict[int, int], total_persons: int) -> list[int]:
        """Sortiere verfügbare Stunden: erst Quorum-Filter, dann Nachmittag bevorzugt,
        dann nach Verfügbarkeit (count) absteigend.
        """
        quorum = min(self.QUORUM, total_persons) if total_persons else 1
        eligible = [h for h, cnt in hour_counts.items() if cnt >= quorum]
        if not eligible:
            # Niemand erreicht das Quorum → nimm die bestbesetzten Stunden trotzdem.
            eligible = list(hour_counts.keys())

        def sort_key(h: int) -> tuple:
            # Niedrigerer Index in PREFERRED_HOURS = höhere Präferenz
            pref = self.PREFERRED_HOURS.index(h) if h in self.PREFERRED_HOURS else len(self.PREFERRED_HOURS)
            return (pref, -hour_counts.get(h, 0), h)

        return sorted(eligible, key=sort_key)

    def suggest_next_meetings(self, meeting_type: str, count: int = 5, persons: list = None, db: Session = None, available_slots: dict = None) -> list[tuple[date, str, int]]:
        """
        Generiere intelligente Terminvorschläge basierend auf:
        1. Historischen Mustern (Tag des Monats)
        2. Persönlichen Urlaubsdaten
        3. Wöchentlichen Verfügbarkeiten (Mo-Fr, Stunden) — quorum-basiert

        ``available_slots`` ist ``{weekday: {hour: available_count}}``.
        Pro Kandidaten-Datum werden mehrere (Top-3) Stunden emittiert.
        """
        if not self.HISTORICAL_MEETINGS.get(meeting_type):
            return []

        pattern = self.analyze_meeting_pattern(meeting_type)
        if not pattern.get("typical_months"):
            return []

        total_persons = len(persons) if persons else 0

        # Verfügbare Zeitslots (Mo=0, Di=1, ...) als {hour: count}
        if available_slots is None:
            nominal = total_persons or 1
            fallback = {h: nominal for h in (14, 15, 16, 17, 18)}
            available_slots = {0: dict(fallback), 1: dict(fallback), 2: dict(fallback), 3: dict(fallback), 4: {}}

        suggestions: list[tuple[date, str, int]] = []
        seen: set[tuple[date, str]] = set()
        today = date.today()
        typical_months = pattern["typical_months"]

        # Sammle Urlaube aller Personen
        all_forbidden_dates = set()
        if persons and db:
            for person in persons:
                all_forbidden_dates.update(self.get_forbidden_dates_for_person(person.id))

        # Generiere Kandidaten für nächste 12 Monate
        for typical_month in typical_months:
            year = today.year
            check_month = typical_month

            while year < today.year + 2:
                historical_days = pattern["month_distribution"].get(check_month, [15])
                for day in historical_days:
                    try:
                        candidate = date(year, check_month, min(day, 28))
                    except ValueError:
                        continue

                    # Prüfe Urlaubsdaten
                    if candidate < today or candidate in all_forbidden_dates:
                        continue

                    weekday = candidate.weekday()  # 0=Mo, 6=So
                    if weekday >= 5:  # Skip Sa-So (Mo-Fr OK)
                        continue

                    hour_counts = available_slots.get(weekday, {})
                    if not hour_counts:
                        continue

                    ranked_hours = self._rank_hours(hour_counts, total_persons)
                    if not ranked_hours:
                        continue

                    # Nähe-Score (30%)
                    days_diff = (candidate - today).days
                    proximity_score = max(30, 100 - (days_diff // 7))

                    # Emit Top-3 Stunden pro Datum, leichter Abschlag je Rang.
                    for rank, hour in enumerate(ranked_hours[:3]):
                        time_str = f"{hour:02d}:00"
                        dedup_key = (candidate, time_str)
                        if dedup_key in seen:
                            continue

                        # Verfügbarkeits-Anteil (count → %) fließt ins Scoring ein.
                        avail_count = hour_counts.get(hour, 0)
                        avail_pct = int((avail_count / total_persons) * 100) if total_persons else 70
                        # Muster + Nähe + Verfügbarkeit, kombiniert.
                        base_score = int(avail_pct * 0.5 + proximity_score * 0.3 + 20)
                        combined_score = base_score - rank  # geringfügiger Rang-Abschlag

                        # Frühe Stunden (z.B. 07:00) abwerten, damit Nachmittags-
                        # Slots bevorzugt werden (siehe PREFERRED_HOURS).
                        if hour not in self.PREFERRED_HOURS:
                            combined_score -= 15

                        # Freitags-Abschlag (10%)
                        if weekday == 4:
                            combined_score = int(combined_score * 0.9)

                        seen.add(dedup_key)
                        suggestions.append((candidate, time_str, combined_score))

                year += 1

        # Sortiere nach Score und Datum
        suggestions.sort(key=lambda x: (-x[2], x[0]))
        logger.debug(f"Generated {len(suggestions)} suggestions for {meeting_type}")
        return suggestions[:count]
