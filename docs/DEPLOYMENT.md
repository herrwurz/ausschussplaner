# Deployment auf Hetzner / Coolify

Das Projekt wird als **ein einziger Container** deployt: Das Multi-Stage-Dockerfile
baut das React-Frontend (`npm run build`) und liefert es über FastAPI same-origin
aus. Dadurch gibt es nur eine Domain, keine CORS-Probleme und einen Service in Coolify.

## Architektur im Container

```
Coolify (Traefik, HTTPS) ──> Container Port 8000 (uvicorn)
                              ├── /api/*    FastAPI-Routen
                              ├── /docs     OpenAPI-Doku
                              ├── /health   Healthcheck (nutzt Coolify)
                              └── /*        React-SPA (frontend/dist)
SQLite:  /data/ausschussplaner.db  (Persistent Volume)
```

## Einrichtung in Coolify (Schritt für Schritt)

1. **Neue Resource anlegen:** *Project → Add Resource → Public/Private Repository*
   → GitHub-Repo `herrwurz/ausschussplaner`, Branch `master`.

2. **Build Pack:** `Dockerfile` auswählen (nicht docker-compose nötig —
   das Dockerfile im Root reicht). Port: `8000`.

3. **Persistent Storage:** Volume anlegen mit Mount-Pfad **`/data`**
   (dort liegt die SQLite-DB; ohne Volume sind alle Daten nach jedem Deploy weg!).

4. **Environment Variables** setzen:

   | Variable | Wert | Pflicht |
   |----------|------|---------|
   | `SECRET_KEY` | Zufallswert, z. B. `openssl rand -hex 32` | **JA** — sonst sind JWTs fälschbar |
   | `DATABASE_URL` | `sqlite:////data/ausschussplaner.db` | ja |
   | `ADMIN_EMAIL` | z. B. `admin@deine-domain.at` | empfohlen |
   | `ADMIN_PASSWORD` | sicheres Passwort | empfohlen (legt Admin beim Start an) |
   | `DEBUG` | `false` | ja |

   `ADMIN_PASSWORD` erstellt/aktualisiert den SUPER_ADMIN beim App-Start —
   es ist kein Shell-Zugriff für `create_admin.py` nötig. Nach dem ersten
   Login kann die Variable entfernt werden.

5. **Domain zuweisen** (Coolify → Domains): z. B. `ausschussplaner.deine-domain.at`.
   HTTPS/Let's Encrypt übernimmt Coolify automatisch.

6. **Healthcheck:** Das Dockerfile bringt einen `HEALTHCHECK` auf `/health` mit;
   Coolify zeigt den Status automatisch an.

7. **Deploy** klicken. Beim ersten Start werden die Tabellen angelegt und
   (bei leerer DB) die Seed-Daten geladen.

## Nach dem ersten Deploy

- Login unter `https://<domain>/admin/login` mit `ADMIN_EMAIL` / `ADMIN_PASSWORD`
- Prüfen: `https://<domain>/health` → `{"status": "ok"}`
- **Demo-Zugang absichern:** Falls die Seed-Daten den Demo-Admin
  `admin@ausschussplaner.local` angelegt haben, dieses Konto im Tab *Benutzer*
  deaktivieren oder das Passwort ändern.

## Updates

Push auf `master` → Coolify baut und deployt automatisch (wenn Auto-Deploy
aktiviert ist). Die SQLite-DB im Volume bleibt erhalten. Schema-Änderungen
laufen aktuell über `Base.metadata.create_all` (nur additiv!) — für echte
Migrationen ist Alembic noch nicht eingerichtet (siehe CLAUDE.md, offene Punkte).

## Backups

Die gesamte Anwendung persistiert in **einer Datei**: `/data/ausschussplaner.db`.
In Coolify unter *Backups* ein regelmäßiges Volume-Backup einrichten oder per
Cron auf dem Host sichern:

```bash
cp /var/lib/docker/volumes/<volume-name>/_data/ausschussplaner.db \
   /backup/ausschussplaner-$(date +%F).db
```

## Lokaler Test des Production-Builds

```powershell
# Image bauen und mit compose starten (SECRET_KEY erforderlich)
$env:SECRET_KEY = "nur-lokal-testen"
docker-compose up --build
# → http://localhost:8000  (Frontend + API aus einem Container)
```
