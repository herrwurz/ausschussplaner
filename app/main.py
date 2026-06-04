"""FastAPI-Einstiegspunkt für AusschussPlaner."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import absences, calculation, committees, persons, rules
from app.core.config import get_settings
from app.db.base import Base, engine

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Erzeugt Tabellen beim Start (für Dev; in Prod via Alembic)."""
    Base.metadata.create_all(bind=engine)
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
