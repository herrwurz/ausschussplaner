"""Migration: Verfügbarkeiten je Periode.

Fügt der Tabelle `verfuegbarkeit` die Spalte `periode_id` hinzu und erweitert
den Unique-Constraint auf (person_id, periode_id, wochentag, stunde).
Bestehende Einträge werden zur Standardverfügbarkeit (periode_id = NULL).

SQLite kann Constraints nicht ändern, daher Tabellen-Neuaufbau:
rename -> create (neues Schema) -> copy -> drop.

Das Skript ist idempotent UND reparaturfähig: Bricht ein früherer Lauf nach
dem Rename ab (z.B. weil das Backend die DB gesperrt hatte), holt der nächste
Lauf die Datenübernahme aus `verfuegbarkeit_old` nach.

Ausführung:  python migrate_verfuegbarkeit_periode.py
(Backend vorher stoppen, danach neu starten.)
"""
from sqlalchemy import text

from app.db.base import Base, engine

COPY_SQL = (
    "INSERT INTO verfuegbarkeit (id, person_id, periode_id, wochentag, stunde, verfuegbar) "
    "SELECT id, person_id, NULL, wochentag, stunde, verfuegbar FROM verfuegbarkeit_old "
    "WHERE id NOT IN (SELECT id FROM verfuegbarkeit)"
)


def tabellen(conn) -> list[str]:
    return [r[0] for r in conn.execute(text(
        "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'verfuegbarkeit%'"
    ))]


def spalten(conn, tabelle: str) -> list[str]:
    return [r[1] for r in conn.execute(text(f"PRAGMA table_info({tabelle})"))]


def main() -> None:
    with engine.connect() as conn:
        vorhandene = tabellen(conn)

    if "verfuegbarkeit" not in vorhandene and "verfuegbarkeit_old" not in vorhandene:
        print("Tabelle verfuegbarkeit existiert nicht - create_all legt sie beim Serverstart neu an.")
        return

    with engine.connect() as conn:
        cols = spalten(conn, "verfuegbarkeit") if "verfuegbarkeit" in vorhandene else []

    # Schritt 1: Altes Schema? -> Rename + neue Tabelle anlegen
    if "verfuegbarkeit" in vorhandene and "periode_id" not in cols:
        if "verfuegbarkeit_old" in vorhandene:
            raise SystemExit(
                "FEHLER: verfuegbarkeit_old existiert bereits UND verfuegbarkeit hat altes Schema. "
                "Bitte manuell pruefen (das sollte nicht vorkommen)."
            )
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE verfuegbarkeit RENAME TO verfuegbarkeit_old"))
        vorhandene = ["verfuegbarkeit_old"]

    # Schritt 2: Neue Tabelle sicherstellen (aktuelles Modell-Schema)
    if "verfuegbarkeit" not in vorhandene:
        Base.metadata.create_all(bind=engine, tables=[Base.metadata.tables["verfuegbarkeit"]])

    # Schritt 3: Daten aus _old nachziehen (auch als Reparatur nach abgebrochenem Lauf)
    with engine.connect() as conn:
        vorhandene = tabellen(conn)

    if "verfuegbarkeit_old" in vorhandene:
        with engine.begin() as conn:
            kopiert = conn.execute(text(COPY_SQL)).rowcount
            gesamt = conn.execute(text("SELECT COUNT(*) FROM verfuegbarkeit")).scalar()
            conn.execute(text("DROP TABLE verfuegbarkeit_old"))
        print(f"Migration OK - {kopiert} Eintraege uebernommen, {gesamt} gesamt (als Standardverfuegbarkeit).")
    else:
        with engine.connect() as conn:
            gesamt = conn.execute(text("SELECT COUNT(*) FROM verfuegbarkeit")).scalar()
        print(f"Bereits migriert - nichts zu tun ({gesamt} Eintraege).")


if __name__ == "__main__":
    main()
