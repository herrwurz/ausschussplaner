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
    ("p32", "Daniel", "Glötzer", "Gemeinderat", True,
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

# Ausschüsse personenweise abgeglichen. Bei Doppel-Obmann / fehlendem Obmann
# wurde die plausibelste Zuordnung gewählt (siehe Kommentare).
COMMITTEES_DATA = [
    ("Infrastruktur", AusschussTyp.STANDARD, [
        ("p06", OB), ("p02", ST), ("p10", MI), ("p15", MI),
        ("p22", MI), ("p23", MI), ("p24", MI), ("p30", MI)]),
    ("Bildung", AusschussTyp.STANDARD, [
        ("p05", OB), ("p12", ST), ("p17", MI), ("p20", MI),
        ("p21", MI), ("p25", MI), ("p27", MI), ("p31", MI)]),
    ("Sport", AusschussTyp.STANDARD, [
        ("p04", OB), ("p13", ST), ("p19", MI), ("p20", MI),
        ("p25", MI), ("p28", MI), ("p32", MI)]),
    ("Klima", AusschussTyp.STANDARD, [
        ("p07", OB), ("p14", ST), ("p17", MI), ("p20", MI),
        ("p21", MI), ("p22", MI), ("p23", MI), ("p25", MI),
        ("p27", MI), ("p31", MI)]),
    # Kontrolle: Seiler=Obmann (Stadträtin), Hochrathner steht im Bild ebenfalls
    # als Obmann -> als Mitglied geführt (Konflikt in Quelle).
    ("Kontrolle", AusschussTyp.KONTROLL, [
        ("p03", OB), ("p24", ST), ("p12", MI), ("p17", MI),
        ("p18", MI), ("p19", MI), ("p26", MI), ("p28", MI), ("p31", MI)]),
    ("Kultur", AusschussTyp.STANDARD, [
        ("p10", OB), ("p16", ST), ("p03", MI), ("p13", MI),
        ("p14", MI), ("p15", MI), ("p17", MI), ("p19", MI),
        ("p28", MI), ("p29", MI)]),
    # Hochwasserschutz: Aufreiter Claudia=Obmann, Nöbauer=Stv,
    # Schnetzinger ebenfalls Stv -> als Mitglied geführt.
    ("Hochwasserschutz", AusschussTyp.STANDARD, [
        ("p12", OB), ("p18", ST), ("p04", MI), ("p24", MI)]),
    ("Mittelschule", AusschussTyp.POLY, [
        ("p18", OB), ("p04", MI), ("p05", MI), ("p09", MI),
        ("p12", MI), ("p16", MI), ("p28", MI), ("p29", MI)]),
    # Poly: Killinger-Spitz=Obmann, Prohaska=Stv, Ströcker ebenfalls Stv
    # -> als Mitglied geführt.
    ("Poly", AusschussTyp.POLY, [
        ("p08", OB), ("p05", ST), ("p06", MI), ("p09", MI),
        ("p14", MI), ("p21", MI), ("p25", MI), ("p32", MI)]),
    # Soziales: kein Obmann in Quelle -> Binder (Stv) führt; bleibt Stv,
    # damit Beschlussfähigkeit korrekt 'kein Obmann' meldet (nachvollziehbar).
    ("Soziales", AusschussTyp.STANDARD, [
        ("p22", ST), ("p10", MI), ("p11", MI), ("p13", MI),
        ("p16", MI), ("p26", MI), ("p27", MI), ("p29", MI)]),
    # Stadtentwicklung: Mugrauer & Pum beide Obmann -> Mugrauer Obmann, Pum Stv.
    ("Stadtentwicklung", AusschussTyp.STANDARD, [
        ("p02", OB), ("p09", ST), ("p05", MI), ("p11", MI),
        ("p15", MI), ("p20", MI), ("p22", MI)]),
    ("Tiefbau", AusschussTyp.STANDARD, [
        ("p11", OB), ("p24", ST), ("p02", MI), ("p07", MI),
        ("p10", MI), ("p15", MI), ("p23", MI), ("p26", MI)]),
    # Zivilschutz: kein Obmann in Quelle -> Seiler (Stv) führt.
    ("Zivilschutz", AusschussTyp.STANDARD, [
        ("p03", ST), ("p08", MI)]),
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
        print(f"✓ Seed abgeschlossen: {len(PERSONS_DATA)} Personen "
              f"({aktiv} aktiv), {len(COMMITTEES_DATA)} Ausschüsse")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
