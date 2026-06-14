#!/usr/bin/env python3
"""Importiere Daten direkt aus realdata.json mit ALLEN Verfügbarkeiten."""
import json
from sqlalchemy import delete

from app.db.base import SessionLocal
from app.models.models import Person, Ausschuss, Mitgliedschaft, Verfuegbarkeit
from app.models.enums import Rolle, AusschussTyp

# Mapping: Ausschussname -> AusschussTyp
AUSSCHUSS_MAPPING = {
    "Infrastruktur": AusschussTyp.STANDARD,
    "Bildung": AusschussTyp.STANDARD,
    "Sport": AusschussTyp.STANDARD,
    "Klima": AusschussTyp.STANDARD,
    "Kontrolle": AusschussTyp.KONTROLL,
    "Kultur": AusschussTyp.STANDARD,
    "Hochwasserschutz": AusschussTyp.STANDARD,
    "Mittelschule": AusschussTyp.STANDARD,
    "Poly": AusschussTyp.POLY,
    "Soziales": AusschussTyp.STANDARD,
    "Stadtentwicklung": AusschussTyp.STANDARD,
    "Tiefbau": AusschussTyp.STANDARD,
    "Zivilschutz": AusschussTyp.STANDARD,
}

# Wochentag Mapping (Enum-Werte)
WOCHENTAG_MAP = {"Mo": "Mo", "Di": "Di", "Mi": "Mi", "Do": "Do", "Fr": "Fr"}
WOCHENTAG_ABBR_TO_NUM = {"Mo": 1, "Di": 2, "Mi": 3, "Do": 4, "Fr": 5}


def parse_rolle(rolle_str):
    """Parse Rolle-String zu Rolle-Enum."""
    if rolle_str == "-":
        return None
    if rolle_str == "Obmann":
        return Rolle.OBMANN
    if rolle_str == "Obmann-Stv.":
        return Rolle.OBMANN_STELLVERTRETER
    if rolle_str == "Mitglied":
        return Rolle.MITGLIED
    return None


def main():
    """Importiere Daten aus realdata.json."""
    db = SessionLocal()

    print("[*] Cleaning old data...")
    db.execute(delete(Verfuegbarkeit))
    db.execute(delete(Mitgliedschaft))
    db.execute(delete(Ausschuss))
    db.execute(delete(Person))
    db.commit()

    # Lade JSON
    with open("realdata.json", "r", encoding="utf-8") as f:
        json_data = json.load(f)

    print(f"[*] Loading {len(json_data)} persons from realdata.json...")

    # 1. Erstelle alle Ausschüsse
    print("[+] Creating 13 committees...")
    ausschuesse_by_name = {}
    for name, typ in AUSSCHUSS_MAPPING.items():
        ausschuss = Ausschuss(name=name, typ=typ, turnus="monatlich", aktiv=True)
        db.add(ausschuss)
        ausschuesse_by_name[name] = ausschuss
    db.commit()

    # 2. Erstelle alle Personen + Verfügbarkeiten
    print("[+] Creating persons with availability from JSON...")
    personen_by_name = {}
    verfuegbarkeiten_count = 0

    for item in json_data:
        name_parts = item["Name"].strip().split()
        nachname = " ".join(name_parts[:-1])
        vorname = name_parts[-1]
        gremium = item.get("Gremium", "")

        person = Person(vorname=vorname, nachname=nachname, gremium=gremium, aktiv=True)
        db.add(person)
        db.flush()  # Damit wir die ID haben

        personen_by_name[item["Name"]] = person

        # Parse alle Verfügbarkeiten aus dem JSON
        for abbr, num in WOCHENTAG_ABBR_TO_NUM.items():
            for hour in [7, 16, 17, 18, 19]:
                key = f"{abbr} {hour:02d}:00"
                if key in item and item[key] == "Ja":
                    vf = Verfuegbarkeit(person_id=person.id, wochentag=WOCHENTAG_MAP[abbr], stunde=hour)
                    db.add(vf)
                    verfuegbarkeiten_count += 1

    db.commit()

    # 3. Erstelle Mitgliedschaften basierend auf Rollen
    print("[+] Creating committee memberships based on roles...")
    mitgliedschaften_count = 0

    for item in json_data:
        person = personen_by_name[item["Name"]]

        for ausschuss_name, ausschuss in ausschuesse_by_name.items():
            rolle_key = f"Rolle: {ausschuss_name}"
            if rolle_key in item:
                rolle_str = item[rolle_key]
                rolle = parse_rolle(rolle_str)
                if rolle is not None:
                    mitglied = Mitgliedschaft(person_id=person.id, ausschuss_id=ausschuss.id, rolle=rolle)
                    db.add(mitglied)
                    mitgliedschaften_count += 1

    db.commit()

    print(
        f"[OK] Import erfolgreich!\n"
        f"    - {len(json_data)} Personen\n"
        f"    - {len(AUSSCHUSS_MAPPING)} Ausschuesse\n"
        f"    - {mitgliedschaften_count} Mitgliedschaften\n"
        f"    - {verfuegbarkeiten_count} Verfuegbarkeiten (sollten ~825 sein: 33 × 25)"
    )

    db.close()


if __name__ == "__main__":
    main()
