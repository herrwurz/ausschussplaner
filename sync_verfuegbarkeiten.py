"""Abgleich der Verfügbarkeiten in der DB mit realdata.json (Quelle der Wahrheit).

Vergleicht die Standardverfügbarkeit (periode_id = NULL) jeder Person mit den
Werten aus realdata.json und zeigt alle Abweichungen an.

Ausführung:
    python sync_verfuegbarkeiten.py            # nur vergleichen (ändert nichts)
    python sync_verfuegbarkeiten.py --fix      # DB an realdata.json angleichen

--fix ersetzt die Standardverfügbarkeit der gematchten Personen komplett durch
die JSON-Werte (nur volle Stunden 7/16/17/18/19; alte Halbstunden-Einträge
werden entfernt — die Berechnung hat sie nie ausgewertet).
Perioden-spezifische Einträge (periode_id gesetzt) bleiben unberührt.
"""
import json
import sys
from pathlib import Path

from sqlalchemy import text

from app.db.base import engine

JSON_PATH = Path(__file__).parent / "realdata.json"
DAYS = ["Mo", "Di", "Mi", "Do", "Fr"]
HOURS = [7, 16, 17, 18, 19]
FIX = "--fix" in sys.argv


def norm_name(*teile: str) -> frozenset[str]:
    tokens: set[str] = set()
    for teil in teile:
        tokens.update(t for t in teil.lower().replace(",", " ").split() if t)
    return frozenset(tokens)


def json_matrix(eintrag: dict) -> set[tuple[str, int]]:
    slots = set()
    for day in DAYS:
        for hour in HOURS:
            if eintrag.get(f"{day} {hour:02d}:00") == "Ja":
                slots.add((day, hour))
    return slots


def main() -> None:
    if not JSON_PATH.exists():
        raise SystemExit(f"FEHLER: {JSON_PATH} nicht gefunden - bitte realdata.json ins Projektverzeichnis kopieren.")

    daten = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    json_personen = {norm_name(e["Name"]): e for e in daten}

    with engine.connect() as conn:
        db_personen = conn.execute(
            text("SELECT id, vorname, nachname, aktiv FROM person")
        ).all()

    matched: list[tuple[int, str, dict]] = []
    unmatched_db = []
    used_json_keys: set[frozenset] = set()

    for pid, vor, nach, aktiv in db_personen:
        key = norm_name(vor, nach)
        eintrag = json_personen.get(key)
        if eintrag:
            matched.append((pid, f"{vor} {nach}", eintrag))
            used_json_keys.add(key)
        elif aktiv:
            unmatched_db.append(f"{vor} {nach} (id={pid})")

    unmatched_json = [e["Name"] for k, e in json_personen.items() if k not in used_json_keys]

    print(f"Gematcht: {len(matched)} Personen")
    if unmatched_db:
        print("In DB aktiv, aber NICHT in realdata.json:", ", ".join(unmatched_db))
    if unmatched_json:
        print("In realdata.json, aber NICHT in DB:", ", ".join(unmatched_json))
    print()

    gesamt_diffs = 0
    with engine.begin() as conn:
        for pid, name, eintrag in matched:
            soll = json_matrix(eintrag)
            rows = conn.execute(
                text(
                    "SELECT wochentag, stunde FROM verfuegbarkeit "
                    "WHERE person_id = :pid AND periode_id IS NULL AND verfuegbar = 1"
                ),
                {"pid": pid},
            ).all()
            # DB-Wochentage können als Enum-NAME ('MO') oder -WERT ('Mo') vorliegen
            name_map = {"MO": "Mo", "DI": "Di", "MI": "Mi", "DO": "Do", "FR": "Fr"}
            ist = {
                (name_map.get(str(w), str(w)), int(s))
                for w, s in rows
                if float(s) == int(float(s)) and int(float(s)) in HOURS
            }

            fehlt = sorted(soll - ist)   # laut JSON Ja, in DB nicht
            zuviel = sorted(ist - soll)  # in DB Ja, laut JSON Nein
            if fehlt or zuviel:
                gesamt_diffs += 1
                print(f"{name} (id={pid}):")
                if fehlt:
                    print("   fehlt in DB:  ", ", ".join(f"{d} {h}:00" for d, h in fehlt))
                if zuviel:
                    print("   zu viel in DB:", ", ".join(f"{d} {h}:00" for d, h in zuviel))

            if FIX:
                conn.execute(
                    text("DELETE FROM verfuegbarkeit WHERE person_id = :pid AND periode_id IS NULL"),
                    {"pid": pid},
                )
                for day, hour in sorted(soll):
                    conn.execute(
                        text(
                            "INSERT INTO verfuegbarkeit (person_id, periode_id, wochentag, stunde, verfuegbar) "
                            "VALUES (:pid, NULL, :tag, :std, 1)"
                        ),
                        # SQLAlchemy speichert Enum-NAMEN ('MO', 'DI', ...) in der DB
                        {"pid": pid, "tag": day.upper(), "std": float(hour)},
                    )

    print()
    if gesamt_diffs == 0:
        print("Keine Abweichungen - DB entspricht realdata.json.")
    elif FIX:
        print(f"{gesamt_diffs} Personen korrigiert - DB entspricht jetzt realdata.json.")
    else:
        print(f"{gesamt_diffs} Personen mit Abweichungen. Korrektur mit: python sync_verfuegbarkeiten.py --fix")


if __name__ == "__main__":
    main()
