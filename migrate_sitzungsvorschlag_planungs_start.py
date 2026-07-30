"""Migration: planungs_start_datum auf sitzungsvorschlag.

Fügt der Tabelle `sitzungsvorschlag` die Spalte `planungs_start_datum` (DATE, nullable)
hinzu. Bestehende Fixierungen bleiben ohne Ankerdatum (Frontend fällt auf aktuelle Woche zurück).

Das Skript ist idempotent.

Ausführung:  python migrate_sitzungsvorschlag_planungs_start.py
(Backend vorher stoppen, danach neu starten.)
"""
from sqlalchemy import text

from app.db.base import engine


def spalten(conn, tabelle: str) -> list[str]:
    return [r[1] for r in conn.execute(text(f"PRAGMA table_info({tabelle})"))]


def main() -> None:
    with engine.connect() as conn:
        tables = [
            r[0]
            for r in conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table' AND name='sitzungsvorschlag'")
            )
        ]

    if not tables:
        print("Tabelle sitzungsvorschlag existiert nicht - create_all legt sie beim Serverstart neu an.")
        return

    with engine.connect() as conn:
        cols = spalten(conn, "sitzungsvorschlag")

    if "planungs_start_datum" in cols:
        with engine.connect() as conn:
            gesamt = conn.execute(text("SELECT COUNT(*) FROM sitzungsvorschlag")).scalar()
        print(f"Bereits migriert - nichts zu tun ({gesamt} Eintraege).")
        return

    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE sitzungsvorschlag ADD COLUMN planungs_start_datum DATE"))
        gesamt = conn.execute(text("SELECT COUNT(*) FROM sitzungsvorschlag")).scalar()
    print(f"Migration OK - Spalte planungs_start_datum hinzugefuegt ({gesamt} Eintraege).")


if __name__ == "__main__":
    main()
