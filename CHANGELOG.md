# Changelog

Alle nennenswerten Änderungen dieses Projekts werden hier dokumentiert.
Format orientiert sich an [Keep a Changelog](https://keepachangelog.com/de/).

## [Unreleased]

### Geändert
- Stammdaten-Korrekturen: Biadt→Biladt, Hocrathner→Hochrathner, Hofstetter→Hofreither
- Hasenleitner Lothar auf inaktiv gesetzt
- Ausschuss-Mitgliedschaften personenweise neu gegen die Quelltabelle abgeglichen

### Hinzugefügt
- Fabian Plaimauer als neuer Gemeinderat (übernimmt Hasenleitners Agenden)
- Endpunkt `POST /api/persons/transfer-agenda`: überträgt alle Mitgliedschaften
  (Rollen bleiben erhalten) von einer Person auf eine andere
- Endpunkte `POST /api/persons/{id}/deactivate` und `/activate`
- Tests für Agenden-Übernahme und Aktivierung/Deaktivierung

## [0.1.0] - 2025-06

### Hinzugefügt
- FastAPI-Backend mit SQLAlchemy 2.0 und SQLite
- Datenmodell: Person, Verfügbarkeit, Ausschuss, Mitgliedschaft, Abwesenheit,
  Sitzungsregel, Jahresplan, Sitzungsvorschlag
- Berechnungs-Engine (Masterprompt-konform): Stundenbasis, volle/halbe Starts,
  Beschlussfähigkeit je Ausschusstyp, Priorisierung, Risikoanalyse
- REST-API für Personen, Ausschüsse, Abwesenheiten, Regeln, Berechnung
- Seed mit 33 Personen und 13 Ausschüssen aus den Echtdaten
- Test-Suite (Engine + API), CI-Workflow, Docker-Setup, Alembic
