"""Legt den Standard-Admin-User an bzw. setzt sein Passwort zurück.

Hintergrund: seed_data() läuft beim Serverstart nur, wenn die DB komplett
leer ist. Bestehende Datenbanken (mit Personen, aber ohne User) haben daher
keinen Admin-Login.

Ausführung:  python create_admin.py
"""
from app.db.base import Base, SessionLocal, engine
from app.models.enums import BenutzerRolle
from app.models.models import User
from app.services.auth_service import PasswordService

ADMIN_EMAIL = "admin@ausschussplaner.local"
ADMIN_PASSWORT = "admin123"  # nur für Entwicklung!


def main() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == ADMIN_EMAIL).first()
        if user:
            user.password_hash = PasswordService.hash_password(ADMIN_PASSWORT)
            user.aktiv = True
            print(f"Admin existierte bereits - Passwort zurueckgesetzt: {ADMIN_EMAIL} / {ADMIN_PASSWORT}")
        else:
            db.add(User(
                email=ADMIN_EMAIL,
                password_hash=PasswordService.hash_password(ADMIN_PASSWORT),
                vorname="System",
                nachname="Administrator",
                rolle=BenutzerRolle.SUPER_ADMIN,
                aktiv=True,
            ))
            print(f"Admin angelegt: {ADMIN_EMAIL} / {ADMIN_PASSWORT}")
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    main()
