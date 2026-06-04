# API-Referenz (Kurzform)

Die vollständige, interaktive Referenz ist nach Start unter `/docs` verfügbar.

## Beispiel-Workflow

```bash
# Person anlegen
curl -X POST localhost:8000/api/persons \
  -H "Content-Type: application/json" \
  -d '{"vorname":"Max","nachname":"Muster","gremium":"Stadtrat"}'

# Verfügbarkeit setzen (ersetzt komplett)
curl -X PUT localhost:8000/api/persons/1/verfuegbarkeit \
  -H "Content-Type: application/json" \
  -d '{"items":[{"wochentag":"Mo","stunde":16,"verfuegbar":true},
                {"wochentag":"Mo","stunde":17,"verfuegbar":true}]}'

# Ausschuss mit Mitgliedern
curl -X POST localhost:8000/api/committees \
  -H "Content-Type: application/json" \
  -d '{"name":"Finanz","typ":"standard",
       "mitglieder":[{"person_id":1,"rolle":"Obmann"}]}'

# Berechnung
curl -X POST localhost:8000/api/calculate \
  -H "Content-Type: application/json" \
  -d '{"planungswochen":2,"freitag_modus":"reserve","max_alternativen":5}'
```
