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

    # JWT Secret (für Person-Portal)
    secret_key: str | None = None

    # Email (SMTP für Einladungen)
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_from: str = "noreply@ausschussplaner.local"
    smtp_password: str = ""

    # Standard-Sitzungsregeln (Defaults, in DB überschreibbar)
    default_block_minutes: int = 90
    default_session_minutes: int = 75
    default_pause_minutes: int = 15
    default_council_minutes: int = 240

    # Planung
    planning_weeks: int = 2


@lru_cache
def get_settings() -> Settings:
    """Cached Settings-Singleton."""
    return Settings()
