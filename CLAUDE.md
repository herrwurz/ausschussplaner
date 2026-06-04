# AusschussPlaner — CLAUDE.md

Regelbasiertes Sitzungstermin-Backend für Gemeinde-Ausschüsse (Österreich).

## Stack

- **Python 3.11+** (venv: `.venv\Scripts\python.exe`)
- FastAPI, SQLAlchemy 2, Alembic, Pydantic v2, pytest
- SQLite (dev) — via Alembic portierbar auf PostgreSQL
- Ruff (lint/format), MyPy (types), pre-commit hooks

## Entwicklungsumgebung

```powershell
# Tests ausführen — immer .venv verwenden, nicht System-Python
& ".\.venv\Scripts\python.exe" -m pytest tests/ -v

# Server starten
& ".\.venv\Scripts\python.exe" -m uvicorn app.main:app --reload

# Linting
& ".\.venv\Scripts\python.exe" -m ruff check .
& ".\.venv\Scripts\python.exe" -m ruff format .
```

## Projektstruktur

```
app/
  main.py                    # FastAPI-App, Router-Registrierung, CORS
  core/config.py             # Pydantic Settings (.env)
  db/base.py                 # Engine, Session, Base, get_db-Dependency
  db/seed.py                 # Echtdaten: 33 Personen, 13 Ausschüsse
  models/models.py           # ORM: Person, Verfuegbarkeit, Ausschuss, Mitgliedschaft,
                             #       Abwesenheit, Sitzungsregel, Jahresplan, Sitzungsvorschlag
  models/enums.py            # AusschussTyp, Rolle, Wochentag, AbwesenheitsArt, TerminStatus
  schemas/schemas.py         # Pydantic-Request/Response-Schemas
  services/
    scheduler.py             # Kern-Berechnungsengine — KEIN DB-Zugriff, rein testbar
    calculation_service.py   # DB ↔ Engine-Bridge
    person_service.py        # Agenden-Übernahme / Nachfolge
    jahresplan_service.py    # Jahresplan anlegen, auflisten, kopieren
  api/routes/
    persons.py               # CRUD + deactivate/activate + transfer-agenda + Verfügbarkeit
    committees.py            # CRUD + Mitgliedschaftsverwaltung
    absences.py              # Abwesenheits-CRUD
    rules.py                 # Sitzungsregel-Singleton (GET + PUT)
    calculation.py           # POST /calculate
    jahresplan.py            # GET/POST /jahresplan, POST /jahresplan/copy
tests/
  conftest.py                # In-Memory-SQLite-Fixture, TestClient mit DB-Override
  test_scheduler.py          # Engine-Unit-Tests (Masterprompt-Regeln)
  test_api.py                # API-Integrationstests
```

## Architekturprinzipien

**Entkoppelte Engine:** `services/scheduler.py` hat keinen DB-Import. Nur `calculation_service.py` lädt Daten aus der DB und übergibt sie als DataClasses an die Engine. So bleiben Engine-Tests schnell und DB-unabhängig.

**Singleton-Regel:** `Sitzungsregel` existiert immer genau einmal. PUT ersetzt, GET legt bei Bedarf an.

**Berechnungsregeln (Masterprompt):**
- Nur Personen mit Rolle Obmann / Obmann-Stv. / Mitglied zählen
- Verfügbarkeit in vollen Stunden; der gesamte Sitzungsblock muss abgedeckt sein
- Erlaubte Starts: volle und halbe Stunden (07:00–19:30)
- Beschlussfähigkeit: Obmann + X weitere (X je nach AusschussTyp)
- Priorität: 100 % → beschlussfähig → Obmann+Stv. → nur Obmann → nicht beschlussfähig
- Freitagstermine haben niedrigere Priorität

## API-Endpunkte (Kurzübersicht)

| Methode | Pfad | Zweck |
|---------|------|-------|
| GET/POST | `/api/persons` | Personen |
| PUT | `/api/persons/{id}/verfuegbarkeit` | Vollständige Verfügbarkeit setzen |
| POST | `/api/persons/{id}/deactivate` | Deaktivieren |
| POST | `/api/persons/transfer-agenda` | Agenden-Übernahme |
| GET/POST/PATCH | `/api/committees` | Ausschüsse |
| GET/POST/DELETE | `/api/absences` | Abwesenheiten |
| GET/PUT | `/api/rules` | Sitzungsregel |
| POST | `/api/calculate` | Terminvorschläge berechnen |
| GET/POST | `/api/jahresplan` | Jahrespläne |
| POST | `/api/jahresplan/copy` | Jahresplan kopieren |

## Bekannte offene Punkte

- Sitzungsvorschlag-Persistenz (Ergebnisse speichern)
- Frontend
- Abwesenheits-Integration in `test_api.py`
