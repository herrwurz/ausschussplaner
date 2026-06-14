# Admin Panel — Phase 1: Personen-Management (React)

## Status
✅ **Complete** — Minimal React-based Admin Panel mit Person CRUD (Create, Read, Update, Delete)

## Implementierung

### 1. Frontend-Routes
- **`/admin`** → Redirect zu `/admin/login`
- **`/admin/login`** → AdminLogin Component (Demo-Passwort: `admin123`)
- **`/admin/panel`** → AdminPanel Component (Mit Auth-Check)

### 2. Components
- **`frontend/src/pages/AdminLogin.jsx`** — Login-Seite mit Passwort-Auth
- **`frontend/src/pages/AdminPanel.jsx`** — Person CRUD Interface
- **`frontend/src/styles/AdminPanel.css`** — Styling (Blau-Gelb-Theme)

### 3. CRUD-Operationen
Alle Operationen nutzen die bestehenden FastAPI-Endpoints:

| Operation | Endpoint | Methode | Status |
|-----------|----------|---------|--------|
| **Create** | `/api/persons` | POST | ✅ |
| **Read** | `/api/persons` | GET | ✅ |
| **Update** | `/api/persons/{id}` | PATCH | ✅ |
| **Delete** | `/api/persons/{id}` | DELETE | ✅ |

### 4. Features
- ✅ Liste alle Personen (Vorname, Nachname, Email, Gremium, Status)
- ✅ Neue Person erstellen
- ✅ Person bearbeiten (alle Felder)
- ✅ Person löschen (mit Bestätigung)
- ✅ Error-Handling und Benutzer-Feedback
- ✅ Responsive Design (Desktop + Mobile)
- ✅ Logout-Funktion

## Verwendung

### Lokal entwickeln:
```bash
# Backend starten
cd c:\Projekte\ausschussplaner
python -m uvicorn app.main:app --port 8000

# Frontend starten (in neuem Terminal)
cd frontend
npm run dev
# → http://localhost:5174 (oder 5173, je nach verfügbarem Port)
```

### Admin-Panel öffnen:
1. Gehe zu **`http://localhost:5174/admin`**
2. Login mit Passwort: **`admin123`**
3. Personen-Management Seite öffnet sich
4. CRUD-Operationen durchführen

## API-Schnelltest

```bash
# Test CREATE
curl -X POST http://localhost:8000/api/persons \
  -H "Content-Type: application/json" \
  -d '{
    "vorname": "Test",
    "nachname": "User",
    "email": "test@local",
    "gremium": "TestGroup",
    "aktiv": true
  }'

# Test READ
curl http://localhost:8000/api/persons

# Test UPDATE (mit PATCH)
curl -X PATCH http://localhost:8000/api/persons/1 \
  -H "Content-Type: application/json" \
  -d '{"gremium": "NewGroup"}'

# Test DELETE
curl -X DELETE http://localhost:8000/api/persons/1
```

## Code-Struktur

```
frontend/
  src/
    pages/
      AdminLogin.jsx       # Login mit Passwort-Demo
      AdminPanel.jsx       # Person CRUD Manager
    styles/
      AdminPanel.css       # Styling
    App.jsx                # Routes hinzugefügt

app/
  main.py                  # Jinja2-Admin auskommentiert
  api/routes/persons.py    # Bestehende CRUD-Endpoints
```

## Phase 2: TODO
- [ ] Perioden-Management hinzufügen
- [ ] Ausschüsse-Management hinzufügen
- [ ] Zusätzliche Tabs im Admin Panel
- [ ] Production-Ready Auth (gehashed passwords, signed cookies)

## Testing

Alle CRUD-Operationen wurden manuell getestet:
```bash
bash test_admin_crud.sh
```

Output:
```
1️⃣ CREATE Test:  ✅ ID 34 created
2️⃣ READ Test:    ✅ Person loaded
3️⃣ UPDATE Test:  ✅ Person updated
4️⃣ DELETE Test:  ✅ Status 204 (deleted)
5️⃣ Verify DELETE: ✅ 404 (not found)
```

## Bekannte Limits (Phase 1)

- Demo-Passwort: `admin123` (nur für Entwicklung)
- Keine Validierung von Email-Duplikaten
- Keine Delete-Schutz (noch implementiert im Backend)
- Keine Benutzer-Berechtigungen (einfache Passwort-Auth)

## Transition zur Phase 2

Um Phase 2 zu starten (Perioden + Ausschüsse):
1. Neue Components erstellen: `PeriodenManagement.jsx`, `AusschuesseManagement.jsx`
2. Tabs/Navigation im AdminPanel hinzufügen
3. API-Endpoints verwenden (GET/POST/PATCH/DELETE `/api/committees`, `/api/*)

---

**Fertiggestellt:** 2026-06-12 (heute)
**Nächste Phase:** Perioden + Ausschüsse (später Session)
