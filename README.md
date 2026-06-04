# AusschussPlaner

Regelbasierte Terminplanung für Gemeinde-Ausschüsse. Das Backend berechnet aus den Verfügbarkeiten von Mandatar:innen automatisch beschlussfähige Sitzungstermine und liefert eine vollständige, nachvollziehbare Analyse je Ausschuss.

Aufgebaut mit **FastAPI**, **SQLAlchemy 2.0** und **SQLite** (problemlos auf PostgreSQL umstellbar).

---

## Inhaltsverzeichnis

- [Kernidee](#kernidee)
- [Architektur](#architektur)
- [Schnellstart](#schnellstart)
- [Datenmodell](#datenmodell)
- [Berechnungslogik](#berechnungslogik)
- [API-Endpunkte](#api-endpunkte)
- [Tests](#tests)
- [Entwicklung](#entwicklung)
- [Deployment](#deployment)
- [Roadmap](#roadmap)

---

## Kernidee

Eine Sitzung ist **gültig**, wenn:

1. alle echten Ausschussmitglieder verfügbar sind (Top-Termin, 100 %), oder
2. der Obmann anwesend ist UND die typabhängige Mindestzahl weiterer Mitglieder erreicht wird (beschlussfähig).

Eine Person zählt **nur dann als Mitglied**, wenn ein echter Rolleneintrag (Obmann / Obmann Stellvertreter / Mitglied) vorliegt. Einträge mit „–" oder leer werden konsequent ignoriert. Alle Auswertungen beziehen sich ausschließlich auf diese echten Mitglieder.

## Architektur

```
app/
├── main.py                 FastAPI-App, Router-Registrierung, CORS
├── core/
│   └── config.py           Pydantic-Settings (.env-fähig)
├── db/
│   ├── base.py             Engine, Session, Base, get_db-Dependency
│   └── seed.py             33 Personen + 13 Ausschüsse (Echtdaten)
├── models/
│   ├── enums.py            AusschussTyp, Rolle, Wochentag, TerminStatus …
│   └── models.py           ORM: Person, Ausschuss, Mitgliedschaft, …
├── schemas/
│   └── schemas.py          Pydantic-Request/Response-Modelle
├── services/
│   ├── scheduler.py        REINE Berechnungs-Engine (DB-frei, testbar)
│   └── calculation_service.py   Bindeglied DB ↔ Engine
└── api/routes/
    ├── persons.py          CRUD Personen + Verfügbarkeiten
    ├── committees.py       CRUD Ausschüsse + Mitgliedschaften
    ├── absences.py         Abwesenheiten
    ├── rules.py            globale Sitzungsregeln
    └── calculation.py      Terminberechnung & Analyse
```

Die Berechnungs-Engine (`services/scheduler.py`) ist bewusst **frei von Datenbank- und Framework-Abhängigkeiten**. Sie arbeitet mit reinen Dataclasses und lässt sich dadurch vollständig isoliert testen — die fachliche Kernlogik ist von Infrastruktur entkoppelt.

## Schnellstart

```bash
# 1. Repository klonen
git clone https://github.com/<user>/ausschussplaner.git
cd ausschussplaner

# 2. Virtuelle Umgebung
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 3. Installieren
pip install -e ".[dev]"            # oder: pip install -r requirements.txt

# 4. Datenbank mit Echtdaten befüllen
python -m app.db.seed

# 5. Server starten
uvicorn app.main:app --reload
```

Danach:

- Interaktive API-Doku (Swagger): http://localhost:8000/docs
- Alternative Doku (ReDoc): http://localhost:8000/redoc
- Health-Check: http://localhost:8000/health

### Beispiel: Berechnung auslösen

```bash
curl -X POST http://localhost:8000/api/calculate \
  -H "Content-Type: application/json" \
  -d '{"planungswochen": 2, "freitag_modus": "reserve", "max_alternativen": 5}'
```

## Datenmodell

| Bereich        | Tabelle(n)                                    |
|----------------|-----------------------------------------------|
| Personen       | `person`, `verfuegbarkeit`                    |
| Ausschüsse     | `ausschuss`, `mitgliedschaft`                 |
| Abwesenheiten  | `abwesenheit`                                 |
| Regeln         | `sitzungsregel`                               |
| Planung        | `jahresplan`, `sitzungsvorschlag`             |

Die Verfügbarkeit wird pro **voller Stunde** gespeichert (in den Echtdaten: 07, 16, 17, 18, 19 Uhr je Wochentag). Ein Eintrag bedeutet „verfügbar"; fehlt er, gilt „nicht verfügbar".

Details siehe [`docs/DATAMODEL.md`](docs/DATAMODEL.md).

## Berechnungslogik

Für jeden Ausschuss werden alle erlaubten Startzeiten (volle **und** halbe Stunde) über den Planungszeitraum geprüft:

1. **Benötigte Stunden** eines 90-Minuten-Blocks: z. B. 16:00–17:30 → braucht 16:00 **und** 17:00.
2. **Anwesenheit**: Person ist anwesend, wenn *alle* benötigten Stunden verfügbar sind. Wird sie erst mitten im Block verfügbar, gilt sie als **nicht anwesend**.
3. **Beschlussfähigkeit** je Typ:
   - Standard-Ausschuss: Obmann + min. 4 weitere Mitglieder
   - Poly-Ausschuss: Obmann + min. 2 weitere Mitglieder
   - Kontroll-Ausschuss: Obmann + min. 3 weitere Mitglieder
4. **Priorisierung**: 100 % > beschlussfähig > Obmann + Stellvertreter > nur Obmann > nicht beschlussfähig. Freitagstermine werden als Reserve nachgereiht.

Ausgegeben werden je Ausschuss: Mitgliederliste, Top-Termine, Alternativen, Detailtabelle, Risikoanalyse und eine textuelle Empfehlung (Fixieren / Flexibel / Kritisch).

Details siehe [`docs/SCHEDULING.md`](docs/SCHEDULING.md).

## API-Endpunkte

| Methode | Pfad                                      | Zweck                              |
|---------|-------------------------------------------|------------------------------------|
| GET     | `/api/persons`                            | Personen auflisten                 |
| POST    | `/api/persons`                            | Person anlegen                     |
| PATCH   | `/api/persons/{id}`                        | Person ändern                      |
| PUT     | `/api/persons/{id}/verfuegbarkeit`        | Verfügbarkeit komplett setzen      |
| GET     | `/api/committees`                         | Ausschüsse auflisten               |
| POST    | `/api/committees`                         | Ausschuss + Mitglieder anlegen     |
| PATCH   | `/api/committees/{id}`                     | Ausschuss/Mitglieder ändern        |
| GET     | `/api/absences`                           | Abwesenheiten auflisten            |
| POST    | `/api/absences`                           | Abwesenheit eintragen              |
| GET/PUT | `/api/rules`                              | globale Sitzungsregeln             |
| POST    | `/api/calculate`                          | Termine berechnen & analysieren    |

## Tests

```bash
pytest                    # alle Tests mit Coverage
pytest tests/test_scheduler.py   # nur die Engine-Tests
```

Die Tests decken sowohl die reine Engine (Masterprompt-Regeln) als auch die API-Endpunkte (über eine In-Memory-SQLite) ab.

## Entwicklung

```bash
make lint        # ruff check
make format      # ruff format
make test        # pytest
pre-commit install   # Hooks aktivieren
```

### Migrationen (Alembic)

```bash
alembic revision --autogenerate -m "beschreibung"
alembic upgrade head
```

## Deployment

```bash
docker compose up --build
```

Für Produktion: `DATABASE_URL` auf PostgreSQL umstellen (`postgresql+psycopg://…`), `DEBUG=false`, CORS-Origins einschränken.

## Roadmap

- [ ] Persistieren der Sitzungsvorschläge (`sitzungsvorschlag` befüllen)
- [ ] Berücksichtigung datierter Abwesenheiten in der Berechnung (aktuell Standardverfügbarkeit)
- [ ] Jahresplan-Kopie als Endpunkt
- [ ] Stadtrat-/Gemeinderat-Sonderregeln (alle / 2-3-Mehrheit)
- [ ] Authentifizierung & Rollen (Admin/Leser)
- [ ] Export als PDF/XLSX
- [ ] Anbindung des bestehenden HTML-Frontends an die API

## Lizenz

MIT — siehe [LICENSE](LICENSE).
