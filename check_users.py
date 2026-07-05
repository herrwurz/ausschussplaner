from app.db.base import SessionLocal
from app.models.models import User

db = SessionLocal()
users = db.query(User).all()
if users:
    print("Existierende User:")
    for u in users:
        print(f"  - {u.email}: {u.rolle}")
else:
    print("KEINE User in der Datenbank!")
db.close()
