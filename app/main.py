"""FastAPI-Einstiegspunkt für AusschussPlaner."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import absences, calculation, committees, jahresplan, persons, rules, admin, person
from app.core.config import get_settings
from app.db.base import Base, engine, SessionLocal
from app.db.seed import seed_data

settings = get_settings()


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

app.include_router(persons.router, prefix="/api")
app.include_router(committees.router, prefix="/api")
app.include_router(absences.router, prefix="/api")
app.include_router(rules.router, prefix="/api")
app.include_router(calculation.router, prefix="/api")
app.include_router(jahresplan.router, prefix="/api")
app.include_router(person.router, prefix="/api")
app.include_router(admin.router)


@app.get("/health", tags=["System"])
def health():
    return {"status": "ok", "version": settings.app_version}


@app.get("/", tags=["System"])
def root():
    return {
        "name": settings.app_name,
        "docs": "/docs",
        "health": "/health",
    }
