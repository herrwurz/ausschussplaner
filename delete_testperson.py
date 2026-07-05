"""Löscht die Seed-'Test Person' (test@example.com) vollständig aus der DB.

Über die ORM-Cascades werden Mitgliedschaften, Verfügbarkeiten und
Abwesenheiten der Person mitgelöscht.

Ausführung:  python delete_testperson.py
"""
from app.db.base import SessionLocal
from app.models.models import Person

db = SessionLocal()
try:
    kandidaten = db.query(Person).filter(
        (Person.email == "test@example.com")
        | ((Person.vorname == "Test") & (Person.nachname == "Person"))
    ).all()

    if not kandidaten:
        print("Keine Test Person gefunden - nichts zu tun.")
    for p in kandidaten:
        info = (f"{p.name} (id={p.id}, email={p.email}) - "
                f"{len(p.mitgliedschaften)} Mitgliedschaften, "
                f"{len(p.verfuegbarkeiten)} Verfuegbarkeiten, "
                f"{len(p.abwesenheiten)} Abwesenheiten")
        db.delete(p)
        print(f"Geloescht: {info}")
    db.commit()
finally:
    db.close()
