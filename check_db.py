from app.db.base import SessionLocal
from app.models.models import Verfuegbarkeit, Person
from app.models.enums import Wochentag

db = SessionLocal()
person = db.query(Person).first()
if person:
    print(f"Person: {person.vorname} {person.nachname}")
    verfug = db.query(Verfuegbarkeit).filter(
        Verfuegbarkeit.person_id == person.id,
        Verfuegbarkeit.wochentag == Wochentag.MO
    ).all()
    print(f"Montag-Verfügbarkeiten: {sorted([v.stunde for v in verfug])}")
    print(f"Anzahl: {len(verfug)}")
    print(f"Erwartet: 8 (mit halben Stunden)")
else:
    print("Keine Personen in DB!")
