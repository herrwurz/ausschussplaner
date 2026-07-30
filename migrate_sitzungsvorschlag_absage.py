"""Migration: abgesagt + notiz auf sitzungsvorschlag.

Idempotent. Ausführung auch beim App-Start (Coolify/SQLite-Volumes).
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

    added: list[str] = []
    with engine.begin() as conn:
        if "abgesagt" not in cols:
            conn.execute(
                text("ALTER TABLE sitzungsvorschlag ADD COLUMN abgesagt BOOLEAN NOT NULL DEFAULT 0")
            )
            added.append("abgesagt")
        if "notiz" not in cols:
            conn.execute(
                text("ALTER TABLE sitzungsvorschlag ADD COLUMN notiz VARCHAR(1000) NOT NULL DEFAULT ''")
            )
            added.append("notiz")

    if not added:
        print("Bereits migriert - abgesagt/notiz vorhanden.")
        return
    print(f"Migration OK - Spalten hinzugefuegt: {', '.join(added)}")


if __name__ == "__main__":
    main()
