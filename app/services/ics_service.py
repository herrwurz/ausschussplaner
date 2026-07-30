"""ICS-Kalender-Export für fixierte Sitzungstermine."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from app.models.enums import Wochentag
from app.models.models import Sitzungsvorschlag

DAY_OFFSET = {
    Wochentag.MO: 0,
    Wochentag.DI: 1,
    Wochentag.MI: 2,
    Wochentag.DO: 3,
    Wochentag.FR: 4,
}


def _fold(line: str) -> str:
    """ICS line folding at 75 octets (approx. chars for ASCII)."""
    if len(line) <= 75:
        return line
    parts = [line[:75]]
    rest = line[75:]
    while rest:
        parts.append(" " + rest[:74])
        rest = rest[74:]
    return "\r\n".join(parts)


def _escape(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
    )


def _dt_utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def build_sitzungen_ics(
    vorschlaege: list[Sitzungsvorschlag],
    *,
    ausschuss_namen: dict[int, str],
    calendar_name: str = "AusschussPlaner Sitzungen",
) -> str:
    """Erzeugt eine VCALENDAR-Datei (UTC-Timestamps, floating local times as DATE-TIME)."""
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//AusschussPlaner//DE",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{_escape(calendar_name)}",
    ]
    stamp = _dt_utc_stamp()

    for v in vorschlaege:
        name = ausschuss_namen.get(v.ausschuss_id, f"Ausschuss #{v.ausschuss_id}")
        anchor = v.planungs_start_datum
        if anchor is None:
            # Ohne Ankerdatum: relativer Montag der aktuellen Woche (wie Portal-Fallback)
            today = date.today()
            anchor = today - timedelta(days=today.weekday())

        day = anchor + timedelta(days=(v.woche - 1) * 7 + DAY_OFFSET[v.wochentag])
        start_h, start_m = divmod(v.start_minute, 60)
        end_h, end_m = divmod(v.end_minute, 60)
        dtstart = f"{day.strftime('%Y%m%d')}T{start_h:02d}{start_m:02d}00"
        dtend = f"{day.strftime('%Y%m%d')}T{end_h:02d}{end_m:02d}00"
        uid = f"sitzung-{v.id}@ausschussplaner.local"
        summary = _escape(name)
        desc_parts = [f"Woche {v.woche}", v.wochentag.value]
        if v.quote:
            desc_parts.append(f"Quote {v.quote}%")
        description = _escape(" · ".join(desc_parts))

        lines.extend(
            [
                "BEGIN:VEVENT",
                f"UID:{uid}",
                f"DTSTAMP:{stamp}",
                f"DTSTART:{dtstart}",
                f"DTEND:{dtend}",
                f"SUMMARY:{summary}",
                f"DESCRIPTION:{description}",
                "END:VEVENT",
            ]
        )

    lines.append("END:VCALENDAR")
    return "\r\n".join(_fold(line) for line in lines) + "\r\n"
