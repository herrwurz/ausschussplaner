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
  main.py                    # FastAPI-App, Router-Registrierung, CORS, Lifespan-Seed
  core/config.py             # Pydantic Settings (.env)
  db/base.py                 # Engine, Session, Base, get_db-Dependency
  db/seed.py                 # Echtdaten: 33 Personen, 13 Ausschüsse (lazy-load)
  models/
    models.py                # ORM: Person, Verfuegbarkeit, Ausschuss, Mitgliedschaft,
                             #      Abwesenheit, Sitzungsregel, Jahresplan, Sitzungsvorschlag
    enums.py                 # AusschussTyp, Rolle, Wochentag, AbwesenheitsArt, TerminStatus
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
    admin.py                 # 🆕 Web-Admin-UI: HTML-Server-Rendering für Stammdaten-Management
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

## API-Endpunkte

### REST API (`/api/`)
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

### Web-Admin-UI (`/admin/`)
🆕 HTML-basierte Verwaltungsoberfläche für Stammdaten (Server-Rendered mit FastAPI + Bootstrap 5.3)

| Route | Funktion |
|-------|----------|
| `/admin/login` | Cookie-basierte Auth (password: `admin123` Demo) |
| `/admin/` | Dashboard mit Navigationsmenu |
| `/admin/personen` | Personen-CRUD mit Delete-Schutz |
| `/admin/ausschuesse` | Ausschuesse-CRUD + Mitgliedschaftsverwaltung |
| `/admin/ausschuesse/{id}/mitgliedschaften` | Personen zu Ausschuss hinzufügen/entfernen |
| `/admin/abwesenheiten` | Abwesenheits-CRUD (Urlaub, Krankheit, etc.) |
| `/admin/verfuegbarkeiten` | Wochentag × Stunde Verfügbarkeits-Matrix pro Person |
| `/admin/jahrespläne` | Jahresplan-CRUD |
| `/admin/sitzungsregeln` | Berechnung konfigurieren (Timeouts, Quorum, etc.) |
| `/admin/logout` | Cookie löschen |

## Web-Admin-UI — Sicherheit & Validierung

**Implementierte Sicherheits-Fixes** (Code-Review: 8/8 findings fixed):
- ✅ **XSS-Prevention:** HTML-Escaping für alle Benutzerdaten (`html.escape()`)
- ✅ **CSRF-Protection:** SameSite=Strict Cookie-Flag
- ✅ **Exception-Handling:** Try/except für `ValueError` (int/Enum-Konversionen)
- ✅ **Input-Validierung:** Enum-Konversionen, Redirect-URL-Validierung
- ✅ **Fehler-Feedback:** Error-Pages statt stille Failures
- ✅ **Datenbank-Constraints:** Delete-Schutz (Personen ohne Mitgliedschaften, Ausschuesse ohne Mitglieder)

**Auth-Model:**
- Cookie-basierte Session (kein SessionMiddleware nötig)
- Plain-text Password Demo (`admin123` — nur für Entwicklung!)
- **TODO (Prod):** Hashed passwords, signed/encrypted cookies, optional 2FA

## Git Workflow

**Branch-Strategie: GitHub Flow (einfach)**
- `master` = Production (stable)
- Feature/Bugfix-Branches → Pull Request → Code Review → Merge

```bash
# Neue Feature starten
git checkout -b feature/new-feature-name
# oder: git checkout -b bugfix/fix-name
# oder: git checkout -b docs/update-docs

# Änderungen committen
git add ...
git commit -m "..."

# Branch zu GitHub pushen
git push -u origin feature/new-feature-name

# Pull Request erstellen & mergen
# https://github.com/herrwurz/ausschussplaner/compare/feature/new-feature-name
```

## Setup & Entwicklung

```powershell
# Erste Schritte
git clone https://github.com/herrwurz/ausschussplaner.git
cd ausschussplaner
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Dependencies
pip install -e .
pip install -e ".[dev]"

# Server starten
python -m uvicorn app.main:app --reload
# Admin-UI: http://127.0.0.1:8000/admin/login (password: admin123)
# API Docs: http://127.0.0.1:8000/docs

# Tests
python -m pytest tests/ -v --cov=app

# Linting
python -m ruff check .
python -m ruff format .

# Docker
docker-compose up
# Server: http://localhost:8000
```

## Bekannte offene Punkte

- **Sitzungsvorschlag-Persistenz:** Ergebnisse der `/api/calculate` noch nicht gespeichert
- **Admin-UI Templating:** HTML noch hardcoded in Routes (→ Jinja2 Template-Engine)
- **Authentication Pro:** Password-Hashing, Token-Signing, Token-Expiry
- **Abwesenheits-Integration:** Tests in `test_api.py`
- **Mobile-Responsive:** Admin-UI ist responsive, aber nicht für sehr kleine Screens optimiert
