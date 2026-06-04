"""Zentrale Anwendungskonfiguration über Pydantic Settings."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Konfiguration, überschreibbar via Umgebungsvariablen oder .env."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Allgemein
    app_name: str = "AusschussPlaner API"
    app_version: str = "0.1.0"
    debug: bool = False

    # Datenbank
    database_url: str = "sqlite:///./ausschussplaner.db"

    # CORS
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173", "*"]

    # Standard-Sitzungsregeln (Defaults, in DB überschreibbar)
    default_block_minutes: int = 90
    default_session_minutes: int = 75
    default_pause_minutes: int = 15
    default_council_minutes: int = 240

    # Beschlussfähigkeit: Obmann + X weitere Mitglieder
    quorum_standard: int = 4
    quorum_poly: int = 2
    quorum_kontroll: int = 3

    # Planung
    planning_weeks: int = 2


@lru_cache
def get_settings() -> Settings:
    """Cached Settings-Singleton."""
    return Settings()
