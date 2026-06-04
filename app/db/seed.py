"""Seed-Daten: 33 Personen + 13 Ausschüsse aus der Ausgangstabelle.

Verfügbarkeit-Slots je Tag: 07 | 16 | 17 | 18 | 19 Uhr.
True = verfügbar, False = nicht verfügbar (Reihenfolge 07,16,17,18,19).

Ausführung:
    python -m app.db.seed
"""
from __future__ import annotations

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

# (key, name, gremium, {Mo:[5 bool], Di:..., Mi:..., Do:..., Fr:...})
J, N = True, False
PERSONS_DATA = [
    ("p01", "Kerstin", "Suchan-Mayr", "Bürgermeisterin",
     [[J,J,J,J,J],[J,J,J,J,J],[J,J,J,J,J],[J,J,J,J,J],[J,J,J,J,J]]),
    ("p02", "Rafael", "Mugrauer", "Stadtrat",
     [[N,N,J,J,J],[N,N,J,J,J],[N,N,J,J,J],[N,N,J,J,J],[J,J,J,J,J]]),
    ("p03", "Birgit", "Seiler", "Stadträtin",
     [[N,J,J,J,J],[N,J,J,J,J],[N,J,J,J,J],[N,J,J,J,J],[N,J,J,J,J]]),
    ("p04", "Andreas", "Hofstetter", "Stadtrat",
     [[J,J,J,J,J],[J,J,J,J,J],[J,J,J,J,J],[J,J,J,J,J],[J,J,J,J,J]]),
    ("p05", "Andrea", "Prohaska", "Stadträtin",
     [[J,J,J,J,J],[J,J,J,J,J],[J,J,J,J,J],[J,J,J,J,J],[J,J,J,J,J]]),
    ("p06", "Heinz", "Ströcker", "Stadtrat",
     [[J,J,J,J,J],[J,J,J,J,J],[J,J,J,J,J],[J,J,J,J,J],[J,J,J,J,J]]),
    ("p07", "Hans", "Hintersteiner", "Stadtrat",
     [[J,J,J,J,J],[J,J,J,J,J],[J,J,J,J,J],[J,J,J,J,J],[J,J,J,J,J]]),
    ("p08", "Eva", "Killinger-Spitz", "Stadträtin",
     [[J,J,J,J,J],[J,J,J,J,J],[J,J,J,J,J],[J,J,J,J,J],[J,J,J,J,J]]),
    ("p09", "Andreas", "Pum", "Stadtrat",
     [[J,J,J,J,J],[J,J,J,J,J],[J,J,J,J,J],[J,J,J,J,J],[J,J,J,J,J]]),
    ("p10", "Karl", "Bunzenberger", "Stadtrat",
     [[N,N,J,J,J],[J,J,J,J,J],[N,N,J,J,J],[N,N,J,J,J],[N,N,J,J,N]]),
    ("p11", "Hannes", "Lugmayr", "Stadtrat",
     [[N,N,J,J,J],[J,J,J,J,J],[N,N,J,J,J],[N,N,J,J,J],[N,N,J,J,N]]),
    ("p12", "Claudia", "Aufreiter", "Gemeinderätin",
     [[N,J,J,J,N],[J,J,J,J,J],[N,J,J,J,J],[N,J,J,J,J],[J,J,J,J,J]]),
    ("p13", "Mario", "Grandl", "Gemeinderat",
     [[N,J,J,N,J],[J,J,J,J,J],[N,J,J,J,J],[N,J,J,J,J],[J,J,J,J,J]]),
    ("p14", "Kristina", "Pillmayr", "Gemeinderätin",
     [[N,N,J,J,J],[J,J,J,J,J],[J,J,J,J,J],[N,N,J,J,N],[N,J,J,J,N]]),
    ("p15", "Mathias", "Mayrl", "Gemeinderat",
     [[J,N,J,J,J],[J,J,J,J,J],[N,J,J,J,J],[J,J,J,J,J],[J,J,N,J,J]]),
    ("p16", "Andrea", "Lindner", "Gemeinderätin",
     [[N,J,J,J,N],[J,J,J,J,J],[J,J,J,J,J],[N,J,J,N,N],[N,J,N,N,N]]),
    ("p17", "Karin", "Atzenhofer-K.", "Gemeinderätin",
     [[N,N,J,J,J],[J,J,J,J,J],[J,J,J,J,J],[N,N,J,J,N],[N,J,J,N,N]]),
    ("p18", "Max", "Nöbauer", "Gemeinderat",
     [[N,N,J,J,N],[J,J,J,J,J],[J,J,J,J,J],[N,J,J,N,N],[N,J,N,N,N]]),
    ("p19", "Julia", "Spanyar", "Gemeinderätin",
     [[N,N,J,J,J],[J,J,J,J,J],[J,J,J,J,J],[N,J,J,J,N],[N,J,J,N,N]]),
    ("p20", "Christian", "Aufreiter", "Gemeinderat",
     [[N,J,J,J,J],[J,J,J,J,J],[J,J,J,J,J],[N,J,J,N,N],[N,J,J,N,N]]),
    ("p21", "Pia", "Hofko", "Gemeinderätin",
     [[N,J,N,J,J],[J,J,J,J,J],[N,J,J,J,J],[N,J,J,N,J],[N,J,J,N,N]]),
    ("p22", "Andreas", "Binder", "Gemeinderat",
     [[N,N,J,J,N],[J,J,J,J,J],[J,J,J,J,J],[N,J,J,N,J],[N,J,N,N,N]]),
    ("p23", "Claudia", "Biadt", "Gemeinderätin",
     [[N,N,J,J,N],[J,J,J,J,J],[J,J,J,J,J],[N,N,J,J,N],[N,J,N,N,N]]),
    ("p24", "Florian", "Schnetzinger", "Gemeinderat",
     [[N,J,J,N,N],[J,J,J,J,J],[N,J,J,J,J],[N,N,J,J,N],[N,J,J,N,N]]),
    ("p25", "Theresa", "Purkarthofer", "Gemeinderätin",
     [[N,N,J,J,N],[J,J,J,J,J],[J,J,J,J,J],[N,N,J,N,J],[N,N,J,J,N]]),
    ("p26", "Karl", "Tröbinger", "Gemeinderat",
     [[N,J,J,J,N],[J,J,J,J,J],[J,J,J,J,J],[N,N,J,J,N],[N,J,J,N,N]]),
    ("p27", "Hannah", "Wallner", "Gemeinderätin",
     [[J,N,N,J,J],[J,J,N,J,J],[J,J,J,J,J],[N,N,J,J,N],[J,J,N,N,N]]),
    ("p28", "Christoph", "Krondorfer", "Gemeinderat",
     [[N,N,J,J,N],[J,J,J,J,J],[J,J,J,J,J],[N,N,J,N,J],[N,N,J,J,N]]),
    ("p29", "Sabine", "Abraham", "Gemeinderätin",
     [[N,N,J,J,N],[J,J,J,J,J],[J,J,J,J,J],[N,N,J,J,N],[N,J,J,N,N]]),
    ("p30", "Günter", "Helmreich", "Gemeinderat",
     [[J,J,J,J,J],[J,J,J,J,J],[J,J,J,J,J],[J,J,J,J,J],[J,J,J,J,J]]),
    ("p31", "Petra", "Hocrathner", "Gemeinderätin",
     [[N,J,J,N,J],[J,J,J,J,J],[N,J,J,J,J],[N,N,J,N,J],[N,J,J,N,N]]),
    ("p32", "Daniel", "Glötzer", "Gemeinderat",
     [[N,N,J,J,J],[J,J,J,J,J],[J,J,J,J,J],[N,J,J,J,N],[N,J,J,N,N]]),
    ("p33", "Lothar", "Hasenleitner", "Gemeinderat",
     [[J,J,J,J,J],[J,J,J,J,J],[J,J,J,J,J],[J,J,J,J,J],[J,J,J,J,J]]),
]

OB = Rolle.OBMANN
ST = Rolle.OBMANN_STELLVERTRETER
MI = Rolle.MITGLIED

# (name, typ, [(person_key, rolle), ...])
COMMITTEES_DATA = [
    ("Infrastruktur", AusschussTyp.STANDARD, [
        ("p06", OB), ("p02", ST), ("p10", MI), ("p15", MI),
        ("p22", MI), ("p23", MI), ("p24", MI), ("p30", MI)]),
    ("Bildung", AusschussTyp.STANDARD, [
        ("p05", OB), ("p12", ST), ("p17", MI), ("p20", MI),
        ("p25", MI), ("p27", MI), ("p31", MI)]),
    ("Sport", AusschussTyp.STANDARD, [
        ("p04", OB), ("p13", ST), ("p19", MI), ("p20", MI),
        ("p21", MI), ("p28", MI), ("p32", MI)]),
    ("Klima", AusschussTyp.STANDARD, [
        ("p07", OB), ("p14", ST), ("p17", MI), ("p18", MI),
        ("p20", MI), ("p21", MI), ("p22", MI), ("p23", MI), ("p27", MI)]),
    ("Kontrolle", AusschussTyp.KONTROLL, [
        ("p03", OB), ("p24", ST), ("p13", MI), ("p17", MI),
        ("p19", MI), ("p26", MI), ("p28", MI)]),
    ("Kultur", AusschussTyp.STANDARD, [
        ("p10", OB), ("p16", ST), ("p03", MI), ("p07", MI),
        ("p13", MI), ("p14", MI), ("p15", MI), ("p28", MI)]),
    ("Hochwasserschutz", AusschussTyp.STANDARD, [
        ("p03", OB), ("p18", ST), ("p04", MI), ("p12", MI), ("p29", MI)]),
    ("Mittelschule", AusschussTyp.POLY, [
        ("p18", OB), ("p04", MI), ("p09", MI), ("p12", MI),
        ("p16", MI), ("p28", MI)]),
    ("Poly", AusschussTyp.POLY, [
        ("p08", OB), ("p06", ST), ("p09", MI), ("p14", MI),
        ("p21", MI), ("p32", MI)]),
    ("Soziales", AusschussTyp.STANDARD, [
        ("p11", OB), ("p22", ST), ("p07", MI), ("p13", MI),
        ("p15", MI), ("p25", MI), ("p26", MI), ("p27", MI)]),
    ("Stadtentwicklung", AusschussTyp.STANDARD, [
        ("p02", OB), ("p09", ST), ("p05", MI), ("p12", MI),
        ("p19", MI), ("p20", MI), ("p23", MI)]),
    ("Tiefbau", AusschussTyp.STANDARD, [
        ("p11", OB), ("p13", ST), ("p02", MI), ("p10", MI),
        ("p15", MI), ("p27", MI)]),
    ("Zivilschutz", AusschussTyp.STANDARD, [
        ("p03", ST), ("p08", MI), ("p12", MI), ("p14", MI),
        ("p15", MI), ("p16", MI), ("p23", MI)]),
]


def seed(reset: bool = True) -> None:
    """Befüllt die Datenbank mit den Echtdaten."""
    if reset:
        Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # Sitzungsregel (Singleton)
        if db.get(Sitzungsregel, 1) is None:
            db.add(Sitzungsregel(id=1))

        key_to_id: dict[str, int] = {}
        for key, vor, nach, gremium, avail_matrix in PERSONS_DATA:
            person = Person(vorname=vor, nachname=nach, gremium=gremium, aktiv=True)
            db.add(person)
            db.flush()
            key_to_id[key] = person.id
            for day, row in zip(DAYS, avail_matrix, strict=True):
                for slot_idx, available in enumerate(row):
                    if available:
                        db.add(Verfuegbarkeit(
                            person_id=person.id, wochentag=day,
                            stunde=SLOTS[slot_idx], verfuegbar=True))

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
        print(f"✓ Seed abgeschlossen: {len(PERSONS_DATA)} Personen, {len(COMMITTEES_DATA)} Ausschüsse")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
