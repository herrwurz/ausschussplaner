"""FastAPI-Einstiegspunkt für AusschussPlaner."""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import (
    absences,
    auth,
    calculation,
    committees,
    export,
    jahresplan,
    obmann,
    perioden,
    person,
    persons,
    rules,
    users,
)
from app.core.config import get_settings
from app.db.base import Base, SessionLocal, engine
from app.db.seed import seed_data

settings = get_settings()

# Production-Build des React-Frontends (wird im Docker-Image mitgeliefert)
FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"


DEMO_ADMIN_EMAIL = "admin@ausschussplaner.local"


def ensure_admin_user(db) -> None:
    """Legt den Admin-User an bzw. setzt sein Passwort (nur wenn ADMIN_PASSWORD gesetzt).

    Ermöglicht das Erst-Setup in Deployments ohne Shell-Zugriff (z. B. Coolify).
    Entfernt dabei den früher geseedeten Demo-Admin (bekanntes Passwort im Repo),
    sofern ein anderer Admin konfiguriert ist.
    """
    if not settings.admin_password:
        return
    from app.models.enums import BenutzerRolle
    from app.models.models import User
    from app.services.auth_service import PasswordService

    if settings.admin_email != DEMO_ADMIN_EMAIL:
        demo = db.query(User).filter(User.email == DEMO_ADMIN_EMAIL).first()
        if demo:
            db.delete(demo)
            print(f"⚠️  Demo-Admin entfernt: {DEMO_ADMIN_EMAIL}")

    user = db.query(User).filter(User.email == settings.admin_email).first()
    if user:
        user.password_hash = PasswordService.hash_password(settings.admin_password)
        user.aktiv = True
    else:
        db.add(User(
            email=settings.admin_email,
            password_hash=PasswordService.hash_password(settings.admin_password),
            vorname="System",
            nachname="Administrator",
            rolle=BenutzerRolle.SUPER_ADMIN,
            aktiv=True,
        ))
    db.commit()
    print(f"✅ Admin-User sichergestellt: {settings.admin_email}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Erzeugt Tabellen beim Start (für Dev; in Prod via Alembic) und lädt Seed-Daten."""
    Base.metadata.create_all(bind=engine)

    # Seed-Daten laden wenn Tabellen leer sind
    db = SessionLocal()
    try:
        from app.models.models import Person
        if db.query(Person).count() == 0:
            seed_data(db)
            print("✅ Seed-Daten geladen")
        ensure_admin_user(db)
    finally:
        db.close()

    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Regelbasierte Terminplanung für Gemeinde-Ausschüsse. "
        "Berechnet beschlussfähige Sitzungstermine nach Masterprompt-Logik."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(obmann.router, prefix="/api")
app.include_router(persons.router, prefix="/api")
app.include_router(committees.router, prefix="/api")
app.include_router(absences.router, prefix="/api")
app.include_router(rules.router, prefix="/api")
app.include_router(calculation.router, prefix="/api")
app.include_router(export.router, prefix="/api")
app.include_router(jahresplan.router, prefix="/api")
app.include_router(perioden.router, prefix="/api")
app.include_router(person.router, prefix="/api")
# app.include_router(admin.router)  # Replaced with React-based admin frontend


@app.get("/health", tags=["System"])
def health():
    return {"status": "ok", "version": settings.app_version}


if FRONTEND_DIST.is_dir():
    # Production: gebautes React-Frontend same-origin ausliefern.
    # API-Routen, /docs und /health sind vorher registriert und haben Vorrang;
    # alle übrigen Pfade beantwortet die SPA (React Router übernimmt clientseitig).
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa_fallback(full_path: str):
        candidate = (FRONTEND_DIST / full_path).resolve()
        if (
            full_path
            and candidate.is_file()
            and candidate.is_relative_to(FRONTEND_DIST.resolve())
        ):
            return FileResponse(candidate)
        return FileResponse(FRONTEND_DIST / "index.html")
else:
    @app.get("/", tags=["System"])
    def root():
        return {
            "name": settings.app_name,
            "docs": "/docs",
            "health": "/health",
        }
