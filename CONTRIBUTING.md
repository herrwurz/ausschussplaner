# Mitwirken

## Setup
```bash
pip install -e ".[dev]"
pre-commit install
```

## Workflow
1. Branch von `develop` erstellen: `feature/<kurzbeschreibung>`
2. Änderungen vornehmen, Tests ergänzen
3. `make lint && make test` müssen grün sein
4. Pull Request gegen `develop`

## Konventionen
- Code-Style: `ruff` (Format + Lint)
- Typannotationen erwünscht (`mypy app`)
- Fachlogik gehört in `services/scheduler.py` (DB-frei, testbar)
- Jede neue Regel braucht einen Test in `tests/test_scheduler.py`

## Commit-Messages
Format: `typ: kurzbeschreibung` (z. B. `feat:`, `fix:`, `docs:`, `test:`)
