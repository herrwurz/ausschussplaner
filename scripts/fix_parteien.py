"""Gleicht die Parteizugehoerigkeit bestehender Personen mit PARTEIEN_MAP ab.

Hintergrund
-----------
``seed_data()`` bricht bei bereits befuellter Datenbank sofort ab
(``if db.query(Person).count() > 0: return``). Korrekturen an den Seed-Daten
erreichen ein laufendes System deshalb nicht. Dieses Skript schliesst die
Luecke fuer das Feld ``partei``: es aendert ausschliesslich vorhandene
Datensaetze und legt weder Personen an noch loescht es welche.

Quelle der Wahrheit bleibt ``PARTEIEN_MAP`` in ``app/db/seed.py``.

Aufruf
------
    python scripts/fix_parteien.py            # Vorschau, aendert nichts
    python scripts/fix_parteien.py --apply    # schreibt die Aenderungen

Das Skript ist wiederholbar: ein zweiter Lauf meldet null Aenderungen.
"""

from __future__ import annotations

import argparse
import os
import sys

# Projektwurzel in den Suchpfad, damit "app" auch beim direkten Aufruf
# aus einem Unterverzeichnis importierbar bleibt.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.base import SessionLocal  # noqa: E402
from app.db.seed import PARTEIEN_MAP, PERSONS_DATA  # noqa: E402
from app.models.models import Person  # noqa: E402


def build_expected() -> dict[tuple[str, str], str | None]:
    """Erwartete Partei je (Vorname, Nachname) aus den Seed-Konstanten."""
    expected: dict[tuple[str, str], str | None] = {}
    for key, vorname, nachname, _gremium, _aktiv, _matrix in PERSONS_DATA:
        wert = (PARTEIEN_MAP.get(key) or "").strip()
        expected[(vorname, nachname)] = wert or None
    return expected


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Parteizugehoerigkeit bestehender Personen abgleichen."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Aenderungen tatsaechlich schreiben (ohne diese Option nur Vorschau)",
    )
    args = parser.parse_args()

    expected = build_expected()
    db = SessionLocal()

    try:
        personen = db.query(Person).all()

        if not personen:
            print("Keine Personen in der Datenbank - nichts zu tun.")
            print("Bei leerer Datenbank uebernimmt seed_data() die Parteien selbst.")
            return 0

        # Namen, die mehrfach vorkommen, sind nicht eindeutig zuordenbar
        namen_zaehler: dict[tuple[str, str], int] = {}
        for p in personen:
            namen_zaehler[(p.vorname, p.nachname)] = (
                namen_zaehler.get((p.vorname, p.nachname), 0) + 1
            )

        aenderungen: list[tuple[str, str | None, str | None]] = []
        unveraendert = 0
        mehrdeutig: list[str] = []
        unbekannt: list[str] = []

        for p in personen:
            name = (p.vorname, p.nachname)
            anzeige = f"{p.vorname} {p.nachname}"

            if namen_zaehler[name] > 1:
                mehrdeutig.append(anzeige)
                continue

            if name not in expected:
                unbekannt.append(anzeige)
                continue

            soll = expected[name]
            ist = (p.partei or "").strip() or None

            if ist == soll:
                unveraendert += 1
            else:
                aenderungen.append((anzeige, ist, soll))
                if args.apply:
                    p.partei = soll

        # ---------------------------------------------------------- Bericht

        print(f"Personen in der Datenbank: {len(personen)}")
        print(f"Bereits korrekt:           {unveraendert}")
        print(f"Zu aendern:                {len(aenderungen)}")

        if aenderungen:
            print("\nAenderungen:")
            breite = max(len(a[0]) for a in aenderungen)
            for anzeige, ist, soll in sorted(aenderungen):
                print(
                    "  %-*s  %-14s -> %s"
                    % (breite, anzeige, ist or "(leer)", soll or "(leer)")
                )

        if mehrdeutig:
            print("\nNicht eindeutig (Name mehrfach vorhanden), uebersprungen:")
            for n in sorted(set(mehrdeutig)):
                print(f"  {n}")

        if unbekannt:
            print("\nIn der Datenbank, aber nicht in PERSONS_DATA:")
            for n in sorted(unbekannt):
                print(f"  {n}")

        db_namen = {(p.vorname, p.nachname) for p in personen}
        fehlend = sorted(n for n in expected if n not in db_namen)
        if fehlend:
            print("\nIn PERSONS_DATA, aber nicht in der Datenbank:")
            for vorname, nachname in fehlend:
                print(f"  {vorname} {nachname}")

        # ---------------------------------------------------------- Schreiben

        if not aenderungen:
            print("\nNichts zu tun.")
            return 0

        if args.apply:
            db.commit()
            print(f"\n{len(aenderungen)} Datensaetze aktualisiert.")
        else:
            db.rollback()
            print("\nVORSCHAU - es wurde nichts geschrieben.")
            print("Zum Anwenden erneut aufrufen mit:  --apply")

        return 0

    except Exception as exc:  # pragma: no cover - Diagnosepfad
        db.rollback()
        print(f"Fehler: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
