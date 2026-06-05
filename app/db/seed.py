"""Seed-Daten: Personen + Ausschüsse aus der Ausgangstabelle (korrigiert).

Verfügbarkeit-Slots je Tag: 07 | 16 | 17 | 18 | 19 Uhr.
True = verfügbar, False = nicht verfügbar (Reihenfolge 07,16,17,18,19).

Korrekturen ggü. Erstimport:
  - Biadt -> Biladt
  - Hochrathner (vorher Hocrathner)
  - Hofreither (vorher Hofstetter)
  - Hasenleitner Lothar: inaktiv
  - Fabian Plaimauer: neuer Gemeinderat, übernimmt Agenden von Hasenleitner
  - Ausschuss-Mitgliedschaften personenweise neu abgeglichen

Ausführung:  python -m app.db.seed
"""
from __future__ import annotations

from app.core.security import hash_password
from app.db.base import Base, SessionLocal, engine
from app.models.enums import AusschussTyp, Rolle, Wochentag
from app.models.models import (
    Ausschuss,
    Mitgliedschaft,
    Person,
    Sitzungsregel,
    Verfuegbarkeit,
)

SLOTS = [7, 16, 17, 18, 19]
DAYS = [Wochentag.MO, Wochentag.DI, Wochentag.MI, Wochentag.DO, Wochentag.FR]
J, N = True, False

# (key, vorname, nachname, gremium, aktiv, [Mo,Di,Mi,Do,Fr] je 5 Slots)
PERSONS_DATA = [
    ("p01", "Kerstin", "Suchan-Mayr", "Bürgermeisterin", True,
     [[J,J,J,J,J],[J,J,J,J,J],[J,J,J,J,J],[J,J,J,J,J],[J,J,J,J,J]]),
    ("p02", "Rafael", "Mugrauer", "Stadtrat", True,
     [[N,N,J,J,J],[N,N,J,J,J],[N,N,J,J,J],[N,N,J,J,J],[J,J,J,J,J]]),
    ("p03", "Birgit", "Seiler", "Stadträtin", True,
     [[N,J,J,J,J],[N,J,J,J,J],[N,J,J,J,J],[N,J,J,J,J],[N,J,J,J,J]]),
    ("p04", "Andreas", "Hofreither", "Stadtrat", True,
     [[J,J,J,J,J],[J,J,J,J,J],[J,J,J,J,J],[J,J,J,J,J],[J,J,J,J,J]]),
    ("p05", "Andrea", "Prohaska", "Stadträtin", True,
     [[J,J,J,J,J],[J,J,J,J,J],[J,J,J,J,J],[J,J,J,J,J],[J,J,J,J,J]]),
    ("p06", "Heinz", "Ströcker", "Stadtrat", True,
     [[J,J,J,J,J],[J,J,J,J,J],[J,J,J,J,J],[J,J,J,J,J],[J,J,J,J,J]]),
    ("p07", "Hans", "Hintersteiner", "Stadtrat", True,
     [[J,J,J,J,J],[J,J,J,J,J],[J,J,J,J,J],[J,J,J,J,J],[J,J,J,J,J]]),
    ("p08", "Eva", "Killinger-Spitz", "Stadträtin", True,
     [[J,J,J,J,J],[J,J,J,J,J],[J,J,J,J,J],[J,J,J,J,J],[J,J,J,J,J]]),
    ("p09", "Andreas", "Pum", "Stadtrat", True,
     [[J,J,J,J,J],[J,J,J,J,J],[J,J,J,J,J],[J,J,J,J,J],[J,J,J,J,J]]),
    ("p10", "Karl", "Bunzenberger", "Stadtrat", True,
     [[N,N,J,J,J],[J,J,J,J,J],[N,N,J,J,J],[N,N,J,J,J],[N,N,J,J,N]]),
    ("p11", "Hannes", "Lugmayr", "Stadtrat", True,
     [[N,N,J,J,J],[J,J,J,J,J],[N,N,J,J,J],[N,N,J,J,J],[N,N,J,J,N]]),
    ("p12", "Claudia", "Aufreiter", "Gemeinderätin", True,
     [[N,J,J,J,N],[J,J,J,J,J],[N,J,J,J,J],[N,J,J,J,J],[J,J,J,J,J]]),
    ("p13", "Mario", "Grandl", "Gemeinderat", True,
     [[N,J,J,N,J],[J,J,J,J,J],[N,J,J,J,J],[N,J,J,J,J],[J,J,J,J,J]]),
    ("p14", "Kristina", "Pillmayr", "Gemeinderätin", True,
     [[N,N,J,J,J],[J,J,J,J,J],[J,J,J,J,J],[N,N,J,J,N],[N,J,J,J,N]]),
    ("p15", "Mathias", "Mayrl", "Gemeinderat", True,
     [[J,N,J,J,J],[J,J,J,J,J],[N,J,J,J,J],[J,J,J,J,J],[J,J,N,J,J]]),
    ("p16", "Andrea", "Lindner", "Gemeinderätin", True,
     [[N,J,J,J,N],[J,J,J,J,J],[J,J,J,J,J],[N,J,J,N,N],[N,J,N,N,N]]),
    ("p17", "Karin", "Atzenhofer-K.", "Gemeinderätin", True,
     [[N,N,J,J,J],[J,J,J,J,J],[J,J,J,J,J],[N,N,J,J,N],[N,J,J,N,N]]),
    ("p18", "Max", "Nöbauer", "Gemeinderat", True,
     [[N,N,J,J,N],[J,J,J,J,J],[J,J,J,J,J],[N,J,J,N,N],[N,J,N,N,N]]),
    ("p19", "Julia", "Spanyar", "Gemeinderätin", True,
     [[N,N,J,J,J],[J,J,J,J,J],[J,J,J,J,J],[N,J,J,J,N],[N,J,J,N,N]]),
    ("p20", "Christian", "Aufreiter", "Gemeinderat", True,
     [[N,J,J,J,J],[J,J,J,J,J],[J,J,J,J,J],[N,J,J,N,N],[N,J,J,N,N]]),
    ("p21", "Pia", "Hofko", "Gemeinderätin", True,
     [[N,J,N,J,J],[J,J,J,J,J],[N,J,J,J,J],[N,J,J,N,J],[N,J,J,N,N]]),
    ("p22", "Andreas", "Binder", "Gemeinderat", True,
     [[N,N,J,J,N],[J,J,J,J,J],[J,J,J,J,J],[N,J,J,N,J],[N,J,N,N,N]]),
    ("p23", "Claudia", "Biladt", "Gemeinderätin", True,
     [[N,N,J,J,N],[J,J,J,J,J],[J,J,J,J,J],[N,N,J,J,N],[N,J,N,N,N]]),
    ("p24", "Florian", "Schnetzinger", "Gemeinderat", True,
     [[N,J,J,N,N],[J,J,J,J,J],[N,J,J,J,J],[N,N,J,J,N],[N,J,J,N,N]]),
    ("p25", "Theresa", "Purkarthofer", "Gemeinderätin", True,
     [[N,N,J,J,N],[J,J,J,J,J],[J,J,J,J,J],[N,N,J,N,J],[N,N,J,J,N]]),
    ("p26", "Karl", "Tröbinger", "Gemeinderat", True,
     [[N,J,J,J,N],[J,J,J,J,J],[J,J,J,J,J],[N,N,J,J,N],[N,J,J,N,N]]),
    ("p27", "Hannah", "Wallner", "Gemeinderätin", True,
     [[J,N,N,J,J],[J,J,N,J,J],[J,J,J,J,J],[N,N,J,J,N],[J,J,N,N,N]]),
    ("p28", "Christoph", "Krondorfer", "Gemeinderat", True,
     [[N,N,J,J,N],[J,J,J,J,J],[J,J,J,J,J],[N,N,J,N,J],[N,N,J,J,N]]),
    ("p29", "Sabine", "Abraham", "Gemeinderätin", True,
     [[N,N,J,J,N],[J,J,J,J,J],[J,J,J,J,J],[N,N,J,J,N],[N,J,J,N,N]]),
    ("p30", "Günter", "Helmreich", "Gemeinderat", True,
     [[J,J,J,J,J],[J,J,J,J,J],[J,J,J,J,J],[J,J,J,J,J],[J,J,J,J,J]]),
    ("p31", "Petra", "Hochrathner", "Gemeinderätin", True,
     [[N,J,J,N,J],[J,J,J,J,J],[N,J,J,J,J],[N,N,J,N,J],[N,J,J,N,N]]),
    ("p32", "Daniel", "Glötzner", "Gemeinderat", True,
     [[N,N,J,J,J],[J,J,J,J,J],[J,J,J,J,J],[N,J,J,J,N],[N,J,J,N,N]]),
    # Hasenleitner Lothar: INAKTIV (Agenden an Plaimauer übergeben)
    ("p33", "Lothar", "Hasenleitner", "Gemeinderat", False,
     [[J,J,J,J,J],[J,J,J,J,J],[J,J,J,J,J],[J,J,J,J,J],[J,J,J,J,J]]),
    # Fabian Plaimauer: NEU, übernimmt Hasenleitners Agenden.
    # Verfügbarkeit zunächst wie Hasenleitner (anpassbar via API).
    ("p34", "Fabian", "Plaimauer", "Gemeinderat", True,
     [[J,J,J,J,J],[J,J,J,J,J],[J,J,J,J,J],[J,J,J,J,J],[J,J,J,J,J]]),
]

OB = Rolle.OBMANN
ST = Rolle.OBMANN_STELLVERTRETER
MI = Rolle.MITGLIED

# Ausschüsse — vollständig abgeglichen mit Quelltabelle (alle 13 Ausschüsse).
COMMITTEES_DATA = [
    # 1. Infrastruktur
    ("Infrastruktur", AusschussTyp.STANDARD, [
        ("p06", OB), ("p02", ST), ("p10", MI), ("p15", MI),
        ("p22", MI), ("p23", MI), ("p24", MI), ("p30", MI)]),
    # 2. Bildung
    ("Bildung", AusschussTyp.STANDARD, [
        ("p05", OB), ("p12", ST), ("p17", MI), ("p20", MI),
        ("p21", MI), ("p25", MI), ("p27", MI), ("p31", MI)]),
    # 3. Sport — Ströcker (p06) ist Mitglied
    ("Sport", AusschussTyp.STANDARD, [
        ("p04", OB), ("p13", ST), ("p06", MI), ("p19", MI),
        ("p20", MI), ("p25", MI), ("p28", MI), ("p32", MI)]),
    # 4. Klima — nur 8 Mitglieder (ohne Atzenhofer und Binder)
    ("Klima", AusschussTyp.STANDARD, [
        ("p07", OB), ("p14", ST), ("p20", MI), ("p21", MI),
        ("p23", MI), ("p25", MI), ("p27", MI), ("p31", MI)]),
    # 5. Kontrolle — Hochrathner (p31) Obmann, Schnetzinger (p24) Stv.
    ("Kontrolle", AusschussTyp.KONTROLL, [
        ("p31", OB), ("p24", ST), ("p12", MI), ("p17", MI),
        ("p18", MI), ("p22", MI), ("p28", MI)]),
    # 6. Kultur — Seiler (p03) Obmann, Lindner (p16) Stv.
    ("Kultur", AusschussTyp.STANDARD, [
        ("p03", OB), ("p16", ST), ("p14", MI), ("p17", MI),
        ("p19", MI), ("p26", MI), ("p28", MI), ("p29", MI)]),
    # 7. Hochwasserschutz — Bunzenberger (p10) Obmann, Hintersteiner (p07) Stv.
    ("Hochwasserschutz", AusschussTyp.STANDARD, [
        ("p10", OB), ("p07", ST), ("p03", MI), ("p04", MI),
        ("p11", MI), ("p13", MI), ("p15", MI), ("p24", MI)]),
    # 8. Mittelschule — Aufreiter Claudia (p12) Obmann, Nöbauer (p18) Stv.
    ("Mittelschule", AusschussTyp.STANDARD, [
        ("p12", OB), ("p18", ST), ("p04", MI), ("p05", MI),
        ("p09", MI), ("p16", MI), ("p28", MI), ("p29", MI)]),
    # 9. Poly — nur 4 Mitglieder; Nöbauer (p18) Obmann, Prohaska (p05) Stv.
    ("Poly", AusschussTyp.POLY, [
        ("p18", OB), ("p05", ST), ("p09", MI), ("p12", MI)]),
    # 10. Soziales — Killinger-Spitz (p08) Obmann, Ströcker (p06) Stv.
    ("Soziales", AusschussTyp.STANDARD, [
        ("p08", OB), ("p06", ST), ("p14", MI), ("p16", MI),
        ("p21", MI), ("p25", MI), ("p27", MI), ("p32", MI)]),
    # 11. Stadtentwicklung — Mugrauer (p02) Obmann, Binder (p22) Stv.
    ("Stadtentwicklung", AusschussTyp.STANDARD, [
        ("p02", OB), ("p22", ST), ("p07", MI), ("p10", MI),
        ("p13", MI), ("p23", MI), ("p26", MI), ("p29", MI)]),
    # 12. Tiefbau — Pum (p09) Obmann, Schnetzinger (p24) Stv.
    ("Tiefbau", AusschussTyp.STANDARD, [
        ("p09", OB), ("p24", ST), ("p02", MI), ("p05", MI),
        ("p11", MI), ("p15", MI), ("p20", MI), ("p22", MI)]),
    # 13. Zivilschutz — Lugmayr (p11) Obmann, Seiler (p03) Stv.
    ("Zivilschutz", AusschussTyp.STANDARD, [
        ("p11", OB), ("p03", ST), ("p08", MI), ("p10", MI),
        ("p15", MI), ("p17", MI), ("p23", MI), ("p26", MI)]),
]

# Agenden, die Plaimauer (p34) von Hasenleitner (p33) übernimmt.
# Hasenleitner hat in der Quelltabelle keine Ausschussrollen -> leer.
# Mechanik dennoch demonstriert: hier könnten Mitgliedschaften stehen.
AGENDA_TRANSFER = {"from": "p33", "to": "p34"}


def seed(reset: bool = True) -> None:
    """Befüllt die Datenbank mit den Echtdaten."""
    if reset:
        Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        if db.get(Sitzungsregel, 1) is None:
            db.add(Sitzungsregel(id=1))

        key_to_id: dict[str, int] = {}
        for key, vor, nach, gremium, aktiv, matrix in PERSONS_DATA:
            person = Person(vorname=vor, nachname=nach, gremium=gremium, aktiv=aktiv)
            db.add(person)
            db.flush()
            key_to_id[key] = person.id
            for day, row in zip(DAYS, matrix, strict=True):
                for idx, available in enumerate(row):
                    if available:
                        db.add(Verfuegbarkeit(
                            person_id=person.id, wochentag=day,
                            stunde=SLOTS[idx], verfuegbar=True))

        for name, typ, members in COMMITTEES_DATA:
            a = Ausschuss(name=name, typ=typ, aktiv=True)
            db.add(a)
            db.flush()
            seen: set[int] = set()
            for pkey, rolle in members:
                pid = key_to_id[pkey]
                if pid in seen:
                    continue
                seen.add(pid)
                db.add(Mitgliedschaft(ausschuss_id=a.id, person_id=pid, rolle=rolle))

        db.commit()
        aktiv = sum(1 for p in PERSONS_DATA if p[4])
        print(f"OK Seed abgeschlossen: {len(PERSONS_DATA)} Personen "
              f"({aktiv} aktiv), {len(COMMITTEES_DATA)} Ausschuesse")
    finally:
        db.close()


def seed_data(db=None) -> None:
    """Lädt Seed-Daten (wird beim Startup aufgerufen, wenn DB leer ist)."""
    if db is None:
        db = SessionLocal()
        should_close = True
    else:
        should_close = False

    try:
        # Nur laden wenn noch keine Personen existieren
        if db.query(Person).count() > 0:
            return

        # Sitzungsregel
        if db.query(Sitzungsregel).count() == 0:
            db.add(Sitzungsregel(id=1))

        # Personen + Verfügbarkeiten
        key_to_id: dict[str, int] = {}
        for key, vor, nach, gremium, aktiv, matrix in PERSONS_DATA:
            person = Person(vorname=vor, nachname=nach, gremium=gremium, aktiv=aktiv)
            db.add(person)
            db.flush()
            key_to_id[key] = person.id
            for day, row in zip(DAYS, matrix, strict=True):
                for idx, available in enumerate(row):
                    if available:
                        db.add(Verfuegbarkeit(
                            person_id=person.id, wochentag=day,
                            stunde=SLOTS[idx], verfuegbar=True))

        # Ausschüsse + Mitgliedschaften
        for name, typ, members in COMMITTEES_DATA:
            a = Ausschuss(name=name, typ=typ, aktiv=True)
            db.add(a)
            db.flush()
            seen: set[int] = set()
            for pkey, rolle in members:
                pid = key_to_id[pkey]
                if pid in seen:
                    continue
                seen.add(pid)
                db.add(Mitgliedschaft(ausschuss_id=a.id, person_id=pid, rolle=rolle))

        # Test-Person für Person Portal
        test_person = Person(
            vorname="Test",
            nachname="Person",
            email="test@example.com",
            password_hash=hash_password("test123"),
            gremium="Demo",
            aktiv=True,
        )
        db.add(test_person)

        db.commit()
        aktiv = sum(1 for p in PERSONS_DATA if p[4])
        print(f"✅ Seed-Daten geladen: {len(PERSONS_DATA)} Personen "
              f"({aktiv} aktiv), {len(COMMITTEES_DATA)} Ausschüsse")
        print(f"💡 Test Person Portal: test@example.com / test123")
    finally:
        if should_close:
            db.close()


if __name__ == "__main__":
    seed()
