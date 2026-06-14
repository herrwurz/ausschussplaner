"""Admin Web-UI Routes."""
from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from html import escape
from urllib.parse import urlparse
import os
import json

from datetime import date, datetime
from app.db.base import get_db
from app.models.models import (
    Admin, Person, Ausschuss, Jahresplan, Abwesenheit, Mitgliedschaft, Sitzungsregel, Verfuegbarkeit,
    Gemeinderatsperiode, PeriodePerson
)
from app.models.enums import AbwesenheitsArt, Rolle, Wochentag, AusschussTyp
from app.core.security import verify_password, hash_password
from math import ceil

router = APIRouter(prefix="/admin", tags=["Admin"])

# Template-Setup: suche templates/ im Root-Verzeichnis
template_dir = os.path.join(os.path.dirname(__file__), "..", "..", "templates")
templates = Jinja2Templates(directory=template_dir)


def escape_html(text: str) -> str:
    """HTML-escape user input to prevent XSS."""
    if not text:
        return ""
    return escape(str(text))


def with_sidebar(content: str, page: str = "") -> str:
    """Wrap HTML content with sidebar menu."""
    active_class = 'style="color: #fff9e6; background: rgba(251, 191, 36, 0.2); font-weight: 600;"'

    sidebar = f"""
    <div class="sidebar">
        <div class="navbar-brand mb-4">Ausschussplaner</div>
        <a href="/admin" {"class='active'" if page == 'dashboard' else ''}>Dashboard</a>
        <a href="/admin/personen" {"class='active'" if page == 'personen' else ''}>Personen</a>
        <a href="/admin/ausschuesse" {"class='active'" if page == 'ausschuesse' else ''}>Ausschüsse</a>
        <a href="/admin/perioden" {"class='active'" if page == 'perioden' else ''}>Perioden</a>
        <a href="/admin/abwesenheiten" {"class='active'" if page == 'abwesenheiten' else ''}>Abwesenheiten</a>
        <a href="/admin/verfuegbarkeiten" {"class='active'" if page == 'verfuegbarkeiten' else ''}>Verfügbarkeiten</a>
        <a href="/admin/jahrespläne" {"class='active'" if page == 'jahrespläne' else ''}>Jahrespläne</a>
        <a href="/admin/sitzungsregeln" {"class='active'" if page == 'sitzungsregeln' else ''}>Sitzungsregeln</a>
        <a href="/admin/smart-search" {"class='active'" if page == 'smart-search' else ''}>Smart-Search</a>
        <hr>
        <a href="/admin/logout" class="btn btn-sm btn-danger w-100">Logout</a>
    </div>
    """

    css = """
    <style>
        :root {
            --primary-dark: #1e3a8a;
            --primary: #2563eb;
            --accent-yellow: #fbbf24;
        }
        body { display: flex; min-height: 100vh; margin: 0; }
        .sidebar {
            width: 280px;
            background: linear-gradient(180deg, var(--primary-dark) 0%, var(--primary) 100%);
            padding: 25px;
            border-right: 4px solid var(--accent-yellow);
            color: var(--accent-yellow);
            flex-shrink: 0;
        }
        .sidebar a {
            display: block;
            padding: 12px 16px;
            margin: 8px 0;
            text-decoration: none;
            color: var(--accent-yellow);
            border-radius: 8px;
            transition: all 0.3s;
            font-weight: 500;
        }
        .sidebar a:hover { background: rgba(251, 191, 36, 0.15); }
        .sidebar a.active { background: rgba(251, 191, 36, 0.2); font-weight: 600; }
        .sidebar hr { border-color: rgba(251, 191, 36, 0.3); }
        .navbar-brand { font-weight: 900; color: var(--accent-yellow); font-size: 1.4rem; margin-bottom: 20px; }
        .content { flex: 1; padding: 30px; background: #f8fafc; }
    </style>
    """

    return f"""<!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        {css}
    </head>
    <body>
        {sidebar}
        <div class="content">
            {content}
        </div>
    </body>
    </html>"""


def validate_redirect_url(url: str) -> str:
    """Validate redirect URL to prevent open redirects."""
    if not url:
        return "/admin"
    parsed = urlparse(url)
    if parsed.scheme or parsed.netloc:
        return "/admin"
    return url


def error_page(title: str, message: str, back_url: str) -> str:
    """Render error page with escaped content and validated redirect URL."""
    back_url = validate_redirect_url(back_url)
    return f"""<html><head><title>{escape_html(title)}</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head><body><div class="container mt-5"><div class="col-md-6">
<div class="alert alert-danger"><h4>{escape_html(title)}</h4><p>{escape_html(message)}</p></div>
<a href="{escape_html(back_url)}" class="btn btn-secondary">Zurück</a>
</div></div></body></html>"""


def is_logged_in(request: Request) -> bool:
    """Check if user has valid admin session cookie. (Demo: always True for testing)"""
    # DEMO MODE: Always allow access
    return True


def calculate_quorum(member_count: int) -> int:
    """Calculate quorum as 50% of members + Obmann must be present.

    Returns: ceil(total_members / 2) — minimum members needed for quorum.
    Obmann is mandatory (separate requirement).
    """
    return ceil(member_count / 2)




@router.get("/login", response_class=HTMLResponse)
async def get_login():
    """GET /admin/login shows HTML login form."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
            body { display: flex; align-items: center; justify-content: center; min-height: 100vh; background: #f8fafc; }
            .login-card { width: 100%; max-width: 400px; padding: 30px; background: white; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
            h1 { color: #1e3a8a; margin-bottom: 25px; text-align: center; font-weight: 700; }
            .form-control { border-color: #e2e8f0; }
            .form-control:focus { border-color: #2563eb; box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1); }
            .btn-login { background: #2563eb; border: none; width: 100%; padding: 10px; font-weight: 600; }
            .btn-login:hover { background: #1e40af; }
            .error { color: #dc2626; font-size: 0.875rem; margin-top: 5px; }
            .info { color: #666; font-size: 0.875rem; margin-top: 15px; text-align: center; }
        </style>
    </head>
    <body>
        <div class="login-card">
            <h1>Admin Login</h1>
            <form id="loginForm">
                <div class="mb-3">
                    <label class="form-label">Username</label>
                    <input type="text" id="username" class="form-control" required>
                </div>
                <div class="mb-3">
                    <label class="form-label">Password</label>
                    <input type="password" id="password" class="form-control" required>
                </div>
                <div id="errorMsg" class="error"></div>
                <button type="submit" class="btn btn-primary btn-login">Login</button>
                <div class="info">Demo: username=<code>admin</code>, password=<code>admin123</code></div>
            </form>
        </div>
        <script>
            document.getElementById('loginForm').addEventListener('submit', async (e) => {
                e.preventDefault();
                const username = document.getElementById('username').value;
                const password = document.getElementById('password').value;
                try {
                    const res = await fetch('/admin/login', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({username, password})
                    });
                    const data = await res.json();
                    if (data.success) {
                        localStorage.setItem('admin_token', data.token || 'admin_session');
                        window.location.href = '/admin';
                    } else {
                        document.getElementById('errorMsg').textContent = data.error || 'Login failed';
                    }
                } catch(err) {
                    document.getElementById('errorMsg').textContent = 'Connection error';
                }
            });
        </script>
    </body>
    </html>
    """


@router.post("/login")
async def login(request: Request, db: Session = Depends(get_db)):
    """Login endpoint - JSON API für zentrale Login-Seite."""
    try:
        data = await request.json()
    except Exception as e:
        return JSONResponse({"error": "Invalid request"}, status_code=400)

    username = data.get("username", "").strip()
    password = data.get("password", "")

    if not username or not password:
        return JSONResponse({"error": "Missing username or password"}, status_code=400)

    admin = db.query(Admin).filter(Admin.username == username, Admin.is_active == True).first()
    if admin and verify_password(password, admin.password_hash):
        return JSONResponse({
            "success": True,
            "user_type": "admin",
            "user_id": admin.id,
            "username": admin.username
        }, status_code=200)

    return JSONResponse({"error": "Invalid credentials"}, status_code=401)


@router.post("/test-json")
async def test_json(request: Request):
    """Test endpoint to verify POST routing works."""
    print("[DEBUG] POST /admin/test-json called")
    try:
        data = await request.json()
        return JSONResponse({"received": data})
    except Exception as e:
        return JSONResponse({"error": str(e)})


@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)
    response.delete_cookie("admin_session")
    return response


@router.get("", response_class=HTMLResponse)
async def dashboard(request: Request):
    # DEMO: Auth disabled
    # if not is_logged_in(request):
    #     return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)

    content = """
    <h1>Dashboard</h1>
    <div class="row">
        <div class="col-md-6">
            <div class="card">
                <div class="card-body">
                    <h5 class="card-title">Perioden & Stammdaten</h5>
                    <ul class="list-unstyled">
                        <li><a href="/admin/perioden">Perioden verwalten</a></li>
                        <li><a href="/admin/personen">Personen verwalten</a></li>
                        <li><a href="/admin/ausschuesse">Ausschüsse verwalten</a></li>
                        <li><a href="/admin/abwesenheiten">Abwesenheiten verwalten</a></li>
                    </ul>
                </div>
            </div>
        </div>
        <div class="col-md-6">
            <div class="card">
                <div class="card-body">
                    <h5 class="card-title">Planung</h5>
                    <ul class="list-unstyled">
                        <li><a href="/admin/jahrespläne">Jahrespläne</a></li>
                        <li><a href="/admin/sitzungsregeln">Sitzungsregeln</a></li>
                    </ul>
                </div>
            </div>
        </div>
    </div>
    """
    return HTMLResponse(with_sidebar(content, page="dashboard"))


@router.get("/personen", response_class=HTMLResponse)
async def personen_list(request: Request, db: Session = Depends(get_db)):
    # DEMO: Auth check disabled for testing
    # if not is_logged_in(request):
    #     return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)

    filter_param = request.query_params.get("filter", "all")

    query = db.query(Person)
    if filter_param == "active":
        query = query.filter(Person.aktiv == True)
    elif filter_param == "inactive":
        query = query.filter(Person.aktiv == False)

    persons = query.all()

    # Button styling based on active filter
    alle_class = "btn btn-sm btn-primary active" if filter_param == "all" else "btn btn-sm btn-outline-primary"
    aktiv_class = "btn btn-sm btn-primary active" if filter_param == "active" else "btn btn-sm btn-outline-primary"
    inaktiv_class = "btn btn-sm btn-primary active" if filter_param == "inactive" else "btn btn-sm btn-outline-primary"

    filter_buttons = f"""<div class="btn-group mb-4" role="group">
    <a href="/admin/personen?filter=all" class="{alle_class}">Alle</a>
    <a href="/admin/personen?filter=active" class="{aktiv_class}">Aktiv</a>
    <a href="/admin/personen?filter=inactive" class="{inaktiv_class}">Inaktiv</a>
</div>"""

    rows = "".join([
        f"<tr><td>{p.id}</td><td>{escape_html(p.vorname)} {escape_html(p.nachname)}</td><td>{escape_html(p.partei or '-')}</td><td>{escape_html(p.gremium or '-')}</td><td>{'Aktiv' if p.aktiv else 'Inaktiv'}</td><td><a href='/admin/personen/{p.id}/edit' class='btn btn-sm btn-warning'>Edit</a> <a href='/admin/personen/{p.id}/delete' class='btn btn-sm btn-danger' onclick=\"return confirm('Delete?')\">Delete</a></td></tr>"
        for p in persons
    ])

    content = f"""
    <div class="d-flex justify-content-between mb-4"><h1>Personen ({len(persons)})</h1><a href="/admin/personen/new" class="btn btn-primary">Neue Person</a></div>
    {filter_buttons}
    <table class="table"><thead><tr><th>ID</th><th>Name</th><th>Partei</th><th>Gremium</th><th>Status</th><th>Actions</th></tr></thead><tbody>{rows}</tbody></table>
    """

    return HTMLResponse(with_sidebar(content, page="personen"))


@router.get("/personen/new", response_class=HTMLResponse)
async def personen_new(request: Request):
    # DEMO: Auth disabled
    # if not is_logged_in(request):
    #     return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)
    return """<html><head><title>New Person</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head><body><div class="container mt-5"><div class="col-md-6">
<h1>New Person</h1>
<form method="post" action="/admin/personen/create">
<div class="mb-3"><label>Vorname</label><input type="text" name="vorname" class="form-control" required></div>
<div class="mb-3"><label>Nachname</label><input type="text" name="nachname" class="form-control" required></div>
<div class="mb-3"><label>Gremium</label><input type="text" name="gremium" class="form-control"></div>
<div class="mb-3"><label>Email</label><input type="email" name="email" class="form-control"></div>
<div class="mb-3"><input type="checkbox" name="aktiv" checked> Aktiv</div>
<button type="submit" class="btn btn-primary">Save</button> <a href="/admin/personen" class="btn btn-secondary">Cancel</a>
</form></div></div></body></html>"""


@router.post("/personen/create")
async def personen_create(request: Request, db: Session = Depends(get_db)):
    # DEMO: Auth disabled
    # if not is_logged_in(request):
    #     return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)
    try:
        form = await request.form()
        person = Person(
            vorname=form.get("vorname", "").strip(),
            nachname=form.get("nachname", "").strip(),
            gremium=form.get("gremium", "").strip() or None,
            email=form.get("email", "").strip() or None,
            aktiv=form.get("aktiv") == "on",
        )
        db.add(person)
        db.commit()
        return RedirectResponse(url="/admin/personen", status_code=status.HTTP_302_FOUND)
    except IntegrityError:
        db.rollback()
        return HTMLResponse(error_page("Fehler", "Diese Person existiert bereits oder Daten sind ungültig.", "/admin/personen/new"))
    except Exception as e:
        db.rollback()
        return HTMLResponse(error_page("Fehler", f"Ein Fehler ist aufgetreten: {str(e)}", "/admin/personen/new"))


@router.get("/personen/{person_id}/edit", response_class=HTMLResponse)
async def personen_edit(person_id: int, request: Request, db: Session = Depends(get_db)):
    # DEMO: Auth disabled
    # if not is_logged_in(request):
    #     return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)
    person = db.query(Person).filter(Person.id == person_id).first()
    if not person:
        return RedirectResponse(url="/admin/personen", status_code=status.HTTP_302_FOUND)
    checked = "checked" if person.aktiv else ""
    return f"""<html><head><title>Edit Person</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head><body><div class="container mt-5"><div class="col-md-6">
<h1>Edit Person</h1>
<form method="post" action="/admin/personen/{person_id}/update">
<div class="mb-3"><label>Vorname</label><input type="text" name="vorname" class="form-control" value="{escape_html(person.vorname)}" required></div>
<div class="mb-3"><label>Nachname</label><input type="text" name="nachname" class="form-control" value="{escape_html(person.nachname)}" required></div>
<div class="mb-3"><label>Partei</label><select name="partei" class="form-control"><option value="">-- Keine --</option><option value="ÖVP" {"selected" if person.partei == "ÖVP" else ""}>ÖVP</option><option value="SPÖ" {"selected" if person.partei == "SPÖ" else ""}>SPÖ</option><option value="Grüne" {"selected" if person.partei == "Grüne" else ""}>Grüne</option><option value="FPÖ" {"selected" if person.partei == "FPÖ" else ""}>FPÖ</option><option value="NEOS" {"selected" if person.partei == "NEOS" else ""}>NEOS</option><option value="KPÖ" {"selected" if person.partei == "KPÖ" else ""}>KPÖ</option></select></div>
<div class="mb-3"><label>Gremium</label><input type="text" name="gremium" class="form-control" value="{escape_html(person.gremium or '')}"></div>
<div class="mb-3"><label>Email</label><input type="email" name="email" class="form-control" value="{escape_html(person.email or '')}"></div>
<div class="mb-3"><input type="checkbox" name="aktiv" {checked}> Aktiv</div>
<button type="submit" class="btn btn-primary">Update</button> <a href="/admin/personen" class="btn btn-secondary">Cancel</a>
</form></div></div></body></html>"""


@router.post("/personen/{person_id}/update")
async def personen_update(person_id: int, request: Request, db: Session = Depends(get_db)):
    # DEMO: Auth disabled
    # if not is_logged_in(request):
    #     return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)
    person = db.query(Person).filter(Person.id == person_id).first()
    if person:
        form = await request.form()
        person.vorname = form.get("vorname", "").strip()
        person.nachname = form.get("nachname", "").strip()
        person.partei = form.get("partei", "").strip() or None
        person.gremium = form.get("gremium", "").strip() or None
        person.email = form.get("email", "").strip() or None
        person.aktiv = form.get("aktiv") == "on"
        db.commit()
    return RedirectResponse(url="/admin/personen", status_code=status.HTTP_302_FOUND)


@router.get("/personen/{person_id}/delete", response_class=HTMLResponse)
async def personen_delete(person_id: int, request: Request, db: Session = Depends(get_db)):
    # DEMO: Auth disabled
    # if not is_logged_in(request):
    #     return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)
    person = db.query(Person).filter(Person.id == person_id).first()
    if not person:
        return RedirectResponse(url="/admin/personen", status_code=status.HTTP_302_FOUND)

    if person.mitgliedschaften:
        ausschuesse = [escape_html(m.ausschuss.name) for m in person.mitgliedschaften]
        return f"""<html><head><title>Fehler</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head><body><div class="container mt-5"><div class="col-md-6">
<div class="alert alert-danger">
<h4>Person kann nicht gelöscht werden</h4>
<p>{escape_html(person.vorname)} {escape_html(person.nachname)} ist noch in folgenden Ausschüssen Mitglied:</p>
<ul>{''.join([f'<li>{a}</li>' for a in ausschuesse])}</ul>
<p>Bitte setzen Sie die Person zuerst auf <strong>inaktiv</strong>, um Sie aus der Verwaltung auszuschließen.</p>
</div>
<a href="/admin/personen/{person_id}/edit" class="btn btn-warning">Auf inaktiv setzen</a>
<a href="/admin/personen" class="btn btn-secondary">Zurück</a>
</div></div></body></html>"""

    db.delete(person)
    db.commit()
    return RedirectResponse(url="/admin/personen", status_code=status.HTTP_302_FOUND)


@router.get("/ausschuesse", response_class=HTMLResponse)
async def ausschuesse_list(request: Request, db: Session = Depends(get_db)):
    # DEMO: Auth disabled
    # if not is_logged_in(request):
    #     return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)

    try:
        filter_param = request.query_params.get("filter", "all")

        query = db.query(Ausschuss)
        if filter_param == "active":
            query = query.filter(Ausschuss.aktiv == True)
        elif filter_param == "inactive":
            query = query.filter(Ausschuss.aktiv == False)

        ausschuesse = query.all()

        # Enrich with member counts - convert to dicts to avoid lazy loading
        ausschuesse_list_data = []
        for aus in ausschuesse:
            member_count = db.query(Mitgliedschaft).filter(Mitgliedschaft.ausschuss_id == aus.id).count()
            ausschuesse_list_data.append({
                'id': aus.id,
                'name': aus.name,
                'turnus': aus.turnus,
                'typ': aus.typ.value if aus.typ else None,
                'aktiv': aus.aktiv,
                'member_count': member_count,
            })

        return templates.TemplateResponse("ausschuesse.html", {
            "request": request,
            "page": "ausschuesse",
            "ausschuesse": ausschuesse_list_data,
            "filter_param": filter_param,
        })
    except Exception as e:
        # Fallback: return empty list on error
        return templates.TemplateResponse("ausschuesse.html", {
            "request": request,
            "page": "ausschuesse",
            "ausschuesse": [],
            "filter_param": "all",
        })


@router.get("/ausschuesse/new", response_class=HTMLResponse)
async def ausschuesse_new(request: Request, db: Session = Depends(get_db)):
    # DEMO: Auth disabled
    # if not is_logged_in(request):
    #     return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)

    ausschuss_typen = [e.value for e in AusschussTyp]

    return f"""<html><head><title>Neuer Ausschuss</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<style>body{{background:#f5f7fa}}</style>
</head><body><div class="container mt-5"><div class="col-md-6">
<h1>Neuer Ausschuss</h1>
<form method="post" action="/admin/ausschuesse">
<div class="mb-3"><label class="form-label">Name</label><input type="text" name="name" class="form-control" required></div>
<div class="mb-3"><label class="form-label">Turnus (z.B. monatlich)</label><input type="text" name="turnus" class="form-control" required></div>
<div class="mb-3"><label class="form-label">Typ</label><select name="atyp" class="form-control">
<option value="">-- Wählen Sie einen Typ --</option>
{''.join([f'<option value="{t}">{escape_html(t)}</option>' for t in ausschuss_typen])}
</select></div>
<div class="mb-3"><input type="checkbox" name="aktiv" checked> <label>Aktiv</label></div>
<button type="submit" class="btn btn-primary">Erstellen</button> <a href="/admin/ausschuesse" class="btn btn-secondary">Abbrechen</a>
</form></div></div></body></html>"""


@router.post("/ausschuesse")
async def ausschuesse_create(request: Request, db: Session = Depends(get_db)):
    # DEMO: Auth disabled
    # if not is_logged_in(request):
    #     return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)

    try:
        form = await request.form()
        name = form.get("name", "").strip()
        turnus = form.get("turnus", "").strip()
        atyp = form.get("atyp", "").strip() or None
        aktiv = "aktiv" in form

        if not name or not turnus:
            return HTMLResponse(await ausschuesse_new(request, db), status_code=400)

        ausschuss = Ausschuss(name=name, turnus=turnus, atyp=atyp, aktiv=aktiv)
        db.add(ausschuss)
        db.commit()
        return RedirectResponse(url="/admin/ausschuesse", status_code=status.HTTP_302_FOUND)
    except ValueError as e:
        return HTMLResponse(error_page("Fehler", str(e), "/admin/ausschuesse/new"), status_code=400)


@router.get("/ausschuesse/{ausschuss_id}/edit", response_class=HTMLResponse)
async def ausschuesse_edit(ausschuss_id: int, request: Request, db: Session = Depends(get_db)):
    # DEMO: Auth disabled
    # if not is_logged_in(request):
    #     return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)
    ausschuss = db.query(Ausschuss).filter(Ausschuss.id == ausschuss_id).first()
    if not ausschuss:
        return RedirectResponse(url="/admin/ausschuesse", status_code=status.HTTP_302_FOUND)
    checked = "checked" if ausschuss.aktiv else ""
    return f"""<html><head><title>Edit Ausschuss</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head><body><div class="container mt-5"><div class="col-md-6">
<h1>Edit Ausschuss</h1>
<form method="post" action="/admin/ausschuesse/{ausschuss_id}/update">
<div class="mb-3"><label>Name</label><input type="text" name="name" class="form-control" value="{ausschuss.name}" required></div>
<div class="mb-3"><label>Turnus</label><input type="text" name="turnus" class="form-control" value="{ausschuss.turnus}"></div>
<div class="mb-3"><input type="checkbox" name="aktiv" {checked}> Aktiv</div>
<button type="submit" class="btn btn-primary">Update</button> <a href="/admin/ausschuesse" class="btn btn-secondary">Cancel</a>
</form></div></div></body></html>"""


@router.post("/ausschuesse/{ausschuss_id}/update")
async def ausschuesse_update(ausschuss_id: int, request: Request, db: Session = Depends(get_db)):
    # DEMO: Auth disabled
    # if not is_logged_in(request):
    #     return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)
    ausschuss = db.query(Ausschuss).filter(Ausschuss.id == ausschuss_id).first()
    if ausschuss:
        form = await request.form()
        ausschuss.name = form.get("name", "").strip()
        ausschuss.turnus = form.get("turnus", "").strip() or None
        ausschuss.aktiv = form.get("aktiv") == "on"
        db.commit()
    return RedirectResponse(url="/admin/ausschuesse", status_code=status.HTTP_302_FOUND)


@router.get("/ausschuesse/{ausschuss_id}/delete", response_class=HTMLResponse)
async def ausschuesse_delete(ausschuss_id: int, request: Request, db: Session = Depends(get_db)):
    # DEMO: Auth disabled
    # if not is_logged_in(request):
    #     return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)
    ausschuss = db.query(Ausschuss).filter(Ausschuss.id == ausschuss_id).first()
    if not ausschuss:
        return RedirectResponse(url="/admin/ausschuesse", status_code=status.HTTP_302_FOUND)

    if ausschuss.mitgliedschaften:
        mitglieder = [m.person.vorname + " " + m.person.nachname for m in ausschuss.mitgliedschaften]
        return f"""<html><head><title>Fehler</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head><body><div class="container mt-5"><div class="col-md-6">
<div class="alert alert-danger">
<h4>Ausschuss kann nicht gelöscht werden</h4>
<p><strong>{ausschuss.name}</strong> hat noch {len(mitglieder)} Mitglied(er):</p>
<ul>{''.join([f'<li>{m}</li>' for m in mitglieder])}</ul>
<p>Bitte entfernen Sie zuerst alle Mitglieder aus diesem Ausschuss.</p>
</div>
<a href="/admin/ausschuesse/{ausschuss_id}/mitgliedschaften" class="btn btn-info">Mitgliedschaften verwalten</a>
<a href="/admin/ausschuesse" class="btn btn-secondary">Zurück</a>
</div></div></body></html>"""

    db.delete(ausschuss)
    db.commit()
    return RedirectResponse(url="/admin/ausschuesse", status_code=status.HTTP_302_FOUND)


@router.get("/ausschuesse/{ausschuss_id}/mitgliedschaften", response_class=HTMLResponse)
async def mitgliedschaften_list(ausschuss_id: int, request: Request, db: Session = Depends(get_db)):
    # DEMO: Auth disabled
    # if not is_logged_in(request):
    #     return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)
    ausschuss = db.query(Ausschuss).filter(Ausschuss.id == ausschuss_id).first()
    if not ausschuss:
        return RedirectResponse(url="/admin/ausschuesse", status_code=status.HTTP_302_FOUND)
    mitgliedschaften = db.query(Mitgliedschaft).filter(Mitgliedschaft.ausschuss_id == ausschuss_id).all()
    rows = "".join([
        f"<tr><td>{escape_html(m.person.vorname)} {escape_html(m.person.nachname)}</td><td>{escape_html(m.rolle.value)}</td><td><a href='/admin/ausschuesse/{ausschuss_id}/mitgliedschaften/{m.id}/delete' class='btn btn-sm btn-danger' onclick=\"return confirm('Remove?')\">Remove</a></td></tr>"
        for m in mitgliedschaften
    ])
    return f"""<html><head><title>Mitgliedschaften</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<style>body{{background:#f5f7fa}}.sidebar{{background:#2c3e50;color:white;padding:20px;min-height:100vh}}.sidebar a{{color:white;display:block;padding:10px;text-decoration:none}}</style>
</head><body><div class="row g-0"><div class="col-md-3 sidebar">
<h4>Ausschussplaner</h4><a href="/admin">Dashboard</a><a href="/admin/ausschuesse">Ausschuesse</a><a href="/admin/logout">Logout</a>
</div><div class="col-md-9 p-4">
<div class="d-flex justify-content-between mb-4"><h1>{ausschuss.name} — Mitgliedschaften</h1><a href='/admin/ausschuesse/{ausschuss_id}/mitgliedschaften/add' class='btn btn-primary'>Add Member</a></div>
<table class="table"><thead><tr><th>Person</th><th>Rolle</th><th>Actions</th></tr></thead><tbody>{rows}</tbody></table>
<a href="/admin/ausschuesse" class="btn btn-secondary mt-3">Back</a>
</div></div></body></html>"""


@router.get("/ausschuesse/{ausschuss_id}/mitgliedschaften/add", response_class=HTMLResponse)
async def mitgliedschaften_add_form(ausschuss_id: int, request: Request, db: Session = Depends(get_db)):
    # DEMO: Auth disabled
    # if not is_logged_in(request):
    #     return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)
    ausschuss = db.query(Ausschuss).filter(Ausschuss.id == ausschuss_id).first()
    if not ausschuss:
        return RedirectResponse(url="/admin/ausschuesse", status_code=status.HTTP_302_FOUND)
    existing_member_ids = {m.person_id for m in ausschuss.mitgliedschaften}
    persons = db.query(Person).filter(Person.aktiv == True, ~Person.id.in_(existing_member_ids)).order_by(Person.nachname).all()
    person_options = "".join([f"<option value='{p.id}'>{p.vorname} {p.nachname}</option>" for p in persons])
    rolle_options = "".join([f"<option value='{rolle.value}'>{rolle.value}</option>" for rolle in Rolle])
    return f"""<html><head><title>Add Member</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head><body><div class="container mt-5"><div class="col-md-6">
<h1>Add Member to {ausschuss.name}</h1>
<form method="post" action="/admin/ausschuesse/{ausschuss_id}/mitgliedschaften/create">
<div class="mb-3"><label>Person</label><select name="person_id" class="form-select" required>{person_options or '<option>Alle Personen sind bereits Mitglied</option>'}</select></div>
<div class="mb-3"><label>Rolle</label><select name="rolle" class="form-select" required>{rolle_options}</select></div>
<button type="submit" class="btn btn-primary" {'disabled' if not persons else ''}>Add</button> <a href="/admin/ausschuesse/{ausschuss_id}/mitgliedschaften" class="btn btn-secondary">Cancel</a>
</form></div></div></body></html>"""


@router.post("/ausschuesse/{ausschuss_id}/mitgliedschaften/create")
async def mitgliedschaften_create(ausschuss_id: int, request: Request, db: Session = Depends(get_db)):
    # DEMO: Auth disabled
    # if not is_logged_in(request):
    #     return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)
    try:
        form = await request.form()
        person_id = int(form.get("person_id", 0))
        if not person_id:
            return HTMLResponse(error_page("Fehler", "Bitte wählen Sie eine Person aus.", f"/admin/ausschuesse/{ausschuss_id}/mitgliedschaften/add"))
        rolle_str = form.get("rolle", "").strip()
        if not rolle_str:
            return HTMLResponse(error_page("Fehler", "Bitte wählen Sie eine Rolle aus.", f"/admin/ausschuesse/{ausschuss_id}/mitgliedschaften/add"))
        mitgliedschaft = Mitgliedschaft(
            ausschuss_id=ausschuss_id,
            person_id=person_id,
            rolle=Rolle(rolle_str)
        )
        db.add(mitgliedschaft)
        db.commit()
        return RedirectResponse(url=f"/admin/ausschuesse/{ausschuss_id}/mitgliedschaften", status_code=status.HTTP_302_FOUND)
    except ValueError as e:
        return HTMLResponse(error_page("Fehler", f"Ungültige Eingabe: {str(e)}", f"/admin/ausschuesse/{ausschuss_id}/mitgliedschaften/add"))
    except IntegrityError:
        db.rollback()
        return HTMLResponse(error_page("Fehler", "Diese Person ist bereits ein Mitglied dieses Ausschusses.", f"/admin/ausschuesse/{ausschuss_id}/mitgliedschaften/add"))


@router.get("/ausschuesse/{ausschuss_id}/mitgliedschaften/{mitgliedschaft_id}/delete")
async def mitgliedschaften_delete(ausschuss_id: int, mitgliedschaft_id: int, request: Request, db: Session = Depends(get_db)):
    # DEMO: Auth disabled
    # if not is_logged_in(request):
    #     return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)
    mitgliedschaft = db.query(Mitgliedschaft).filter(Mitgliedschaft.id == mitgliedschaft_id).first()
    if mitgliedschaft:
        db.delete(mitgliedschaft)
        db.commit()
    return RedirectResponse(url=f"/admin/ausschuesse/{ausschuss_id}/mitgliedschaften", status_code=status.HTTP_302_FOUND)


@router.get("/verfuegbarkeiten", response_class=HTMLResponse)
async def verfuegbarkeiten_list(request: Request, db: Session = Depends(get_db)):
    # DEMO: Auth disabled
    # if not is_logged_in(request):
    #     return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)
    persons = db.query(Person).filter(Person.aktiv == True).order_by(Person.nachname).all()
    content = f"""
    <h1>Verfügbarkeiten</h1>
    <form method="get" action="/admin/verfuegbarkeiten/edit">
        <div class="mb-3"><label>Person</label><select name="person_id" class="form-select" required onchange="this.form.submit()">
        <option value="">-- Bitte wählen --</option>
        {''.join([f'<option value="{p.id}">{p.vorname} {p.nachname}</option>' for p in persons])}
        </select></div>
    </form>
    """
    return HTMLResponse(with_sidebar(content, page="verfuegbarkeiten"))


@router.get("/verfuegbarkeiten/edit", response_class=HTMLResponse)
async def verfuegbarkeiten_edit(person_id: int, request: Request, db: Session = Depends(get_db)):
    # DEMO: Auth disabled
    # if not is_logged_in(request):
    #     return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)
    person = db.query(Person).filter(Person.id == person_id).first()
    if not person:
        return RedirectResponse(url="/admin/verfuegbarkeiten", status_code=status.HTTP_302_FOUND)

    existing = db.query(Verfuegbarkeit).filter(Verfuegbarkeit.person_id == person_id).all()
    verfueg_set = {(v.wochentag, v.stunde) for v in existing}

    wochentage = [Wochentag.MO, Wochentag.DI, Wochentag.MI, Wochentag.DO, Wochentag.FR]
    stunden = list(range(7, 20))

    table_rows = ""
    for stunde in stunden:
        row = f"<tr><td>{stunde}:00</td>"
        for w in wochentage:
            checked = "checked" if (w, stunde) in verfueg_set else ""
            row += f'<td><input type="checkbox" name="{w.value}_{stunde}" {checked}></td>'
        row += "</tr>"
        table_rows += row

    return f"""<html><head><title>Verfügbarkeiten</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<style>body{{background:#f5f7fa}}.sidebar{{background:#2c3e50;color:white;padding:20px;min-height:100vh}}.sidebar a{{color:white;display:block;padding:10px;text-decoration:none}} table{{font-size:0.9rem}} td{{padding:5px}}</style>
</head><body><div class="row g-0"><div class="col-md-3 sidebar">
<h4>Ausschussplaner</h4><a href="/admin">Dashboard</a><a href="/admin/verfuegbarkeiten">Verfügbarkeiten</a><a href="/admin/logout">Logout</a>
</div><div class="col-md-9 p-4">
<h2>{person.vorname} {person.nachname} — Verfügbarkeiten</h2>
<form method="post" action="/admin/verfuegbarkeiten/{person_id}/update">
<table class="table table-sm"><thead><tr><th>Stunde</th>{''.join([f'<th>{w.value}</th>' for w in wochentage])}</tr></thead><tbody>{table_rows}</tbody></table>
<button type="submit" class="btn btn-primary">Speichern</button> <a href="/admin/verfuegbarkeiten" class="btn btn-secondary">Zurück</a>
</form>
</div></div></body></html>"""


@router.post("/verfuegbarkeiten/{person_id}/update")
async def verfuegbarkeiten_update(person_id: int, request: Request, db: Session = Depends(get_db)):
    # DEMO: Auth disabled
    # if not is_logged_in(request):
    #     return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)

    db.query(Verfuegbarkeit).filter(Verfuegbarkeit.person_id == person_id).delete()

    form = await request.form()
    wochentage = [Wochentag.MO, Wochentag.DI, Wochentag.MI, Wochentag.DO, Wochentag.FR]
    for w in wochentage:
        for stunde in range(7, 20):
            if form.get(f"{w.value}_{stunde}"):
                verfueg = Verfuegbarkeit(person_id=person_id, wochentag=w, stunde=stunde, verfuegbar=True)
                db.add(verfueg)

    db.commit()
    return RedirectResponse(url="/admin/verfuegbarkeiten", status_code=status.HTTP_302_FOUND)


@router.get("/abwesenheiten", response_class=HTMLResponse)
async def abwesenheiten_list(request: Request, db: Session = Depends(get_db)):
    # DEMO: Auth disabled
    # if not is_logged_in(request):
    #     return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)
    abwesenheiten = db.query(Abwesenheit).order_by(Abwesenheit.von.desc()).all()
    rows = "".join([
        f"<tr><td>{escape_html(a.person.vorname)} {escape_html(a.person.nachname)}</td><td>{a.von}</td><td>{a.bis}</td><td>{escape_html(a.art.value)}</td><td>{escape_html(a.bemerkung or '-')}</td><td><a href='/admin/abwesenheiten/{a.id}/edit' class='btn btn-sm btn-warning'>Edit</a> <a href='/admin/abwesenheiten/{a.id}/delete' class='btn btn-sm btn-danger' onclick=\"return confirm('Delete?')\">Delete</a></td></tr>"
        for a in abwesenheiten
    ])
    content = f"""
    <div class="d-flex justify-content-between mb-4"><h1>Abwesenheiten ({len(abwesenheiten)})</h1><a href="/admin/abwesenheiten/new" class="btn btn-primary">Neue Abwesenheit</a></div>
    <table class="table"><thead><tr><th>Person</th><th>Von</th><th>Bis</th><th>Art</th><th>Bemerkung</th><th>Actions</th></tr></thead><tbody>{rows}</tbody></table>
    """
    return HTMLResponse(with_sidebar(content, page="abwesenheiten"))


@router.get("/abwesenheiten/new", response_class=HTMLResponse)
async def abwesenheiten_new(request: Request, db: Session = Depends(get_db)):
    # DEMO: Auth disabled
    # if not is_logged_in(request):
    #     return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)
    persons = db.query(Person).filter(Person.aktiv == True).order_by(Person.nachname).all()
    person_options = "".join([f"<option value='{p.id}'>{p.vorname} {p.nachname}</option>" for p in persons])
    art_options = "".join([f"<option value='{art.value}'>{art.value}</option>" for art in AbwesenheitsArt])
    return f"""<html><head><title>New Abwesenheit</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head><body><div class="container mt-5"><div class="col-md-6">
<h1>New Abwesenheit</h1>
<form method="post" action="/admin/abwesenheiten/create">
<div class="mb-3"><label>Person</label><select name="person_id" class="form-select" required>{person_options}</select></div>
<div class="mb-3"><label>Von</label><input type="date" name="von" class="form-control" required></div>
<div class="mb-3"><label>Bis</label><input type="date" name="bis" class="form-control" required></div>
<div class="mb-3"><label>Art</label><select name="art" class="form-select" required>{art_options}</select></div>
<div class="mb-3"><label>Bemerkung</label><textarea name="bemerkung" class="form-control" rows="3"></textarea></div>
<button type="submit" class="btn btn-primary">Save</button> <a href="/admin/abwesenheiten" class="btn btn-secondary">Cancel</a>
</form></div></div></body></html>"""


@router.post("/abwesenheiten/create")
async def abwesenheiten_create(request: Request, db: Session = Depends(get_db)):
    # DEMO: Auth disabled
    # if not is_logged_in(request):
    #     return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)
    try:
        form = await request.form()
        abwesenheit = Abwesenheit(
            person_id=int(form.get("person_id", 0)),
            von=form.get("von"),
            bis=form.get("bis"),
            art=AbwesenheitsArt(form.get("art")),
            bemerkung=form.get("bemerkung", "").strip()
        )
        db.add(abwesenheit)
        db.commit()
        return RedirectResponse(url="/admin/abwesenheiten", status_code=status.HTTP_302_FOUND)
    except ValueError as e:
        db.rollback()
        return HTMLResponse(error_page("Fehler", f"Ungültige Eingabe: {str(e)}", "/admin/abwesenheiten/new"))
    except Exception as e:
        db.rollback()
        return HTMLResponse(error_page("Fehler", f"Ein Fehler ist aufgetreten: {str(e)}", "/admin/abwesenheiten/new"))


@router.get("/abwesenheiten/{abwesenheit_id}/edit", response_class=HTMLResponse)
async def abwesenheiten_edit(abwesenheit_id: int, request: Request, db: Session = Depends(get_db)):
    # DEMO: Auth disabled
    # if not is_logged_in(request):
    #     return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)
    abwesenheit = db.query(Abwesenheit).filter(Abwesenheit.id == abwesenheit_id).first()
    if not abwesenheit:
        return RedirectResponse(url="/admin/abwesenheiten", status_code=status.HTTP_302_FOUND)
    persons = db.query(Person).filter(Person.aktiv == True).order_by(Person.nachname).all()
    person_options = "".join([
        f"<option value='{p.id}' {'selected' if p.id == abwesenheit.person_id else ''}>{p.vorname} {p.nachname}</option>"
        for p in persons
    ])
    art_options = "".join([
        f"<option value='{art.value}' {'selected' if art == abwesenheit.art else ''}>{art.value}</option>"
        for art in AbwesenheitsArt
    ])
    return f"""<html><head><title>Edit Abwesenheit</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head><body><div class="container mt-5"><div class="col-md-6">
<h1>Edit Abwesenheit</h1>
<form method="post" action="/admin/abwesenheiten/{abwesenheit_id}/update">
<div class="mb-3"><label>Person</label><select name="person_id" class="form-select" required>{person_options}</select></div>
<div class="mb-3"><label>Von</label><input type="date" name="von" class="form-control" value="{abwesenheit.von}" required></div>
<div class="mb-3"><label>Bis</label><input type="date" name="bis" class="form-control" value="{abwesenheit.bis}" required></div>
<div class="mb-3"><label>Art</label><select name="art" class="form-select" required>{art_options}</select></div>
<div class="mb-3"><label>Bemerkung</label><textarea name="bemerkung" class="form-control" rows="3">{abwesenheit.bemerkung or ''}</textarea></div>
<button type="submit" class="btn btn-primary">Update</button> <a href="/admin/abwesenheiten" class="btn btn-secondary">Cancel</a>
</form></div></div></body></html>"""


@router.post("/abwesenheiten/{abwesenheit_id}/update")
async def abwesenheiten_update(abwesenheit_id: int, request: Request, db: Session = Depends(get_db)):
    # DEMO: Auth disabled
    # if not is_logged_in(request):
    #     return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)
    try:
        abwesenheit = db.query(Abwesenheit).filter(Abwesenheit.id == abwesenheit_id).first()
        if not abwesenheit:
            return HTMLResponse(error_page("Fehler", "Diese Abwesenheit existiert nicht.", "/admin/abwesenheiten"))
        form = await request.form()
        abwesenheit.person_id = int(form.get("person_id", 0))
        abwesenheit.von = form.get("von")
        abwesenheit.bis = form.get("bis")
        abwesenheit.art = AbwesenheitsArt(form.get("art"))
        abwesenheit.bemerkung = form.get("bemerkung", "").strip()
        db.commit()
        return RedirectResponse(url="/admin/abwesenheiten", status_code=status.HTTP_302_FOUND)
    except ValueError as e:
        db.rollback()
        return HTMLResponse(error_page("Fehler", f"Ungültige Eingabe: {str(e)}", f"/admin/abwesenheiten/{abwesenheit_id}/edit"))
    except Exception as e:
        db.rollback()
        return HTMLResponse(error_page("Fehler", f"Ein Fehler ist aufgetreten: {str(e)}", f"/admin/abwesenheiten/{abwesenheit_id}/edit"))


@router.get("/abwesenheiten/{abwesenheit_id}/delete")
async def abwesenheiten_delete(abwesenheit_id: int, request: Request, db: Session = Depends(get_db)):
    # DEMO: Auth disabled
    # if not is_logged_in(request):
    #     return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)
    abwesenheit = db.query(Abwesenheit).filter(Abwesenheit.id == abwesenheit_id).first()
    if abwesenheit:
        db.delete(abwesenheit)
        db.commit()
    return RedirectResponse(url="/admin/abwesenheiten", status_code=status.HTTP_302_FOUND)


@router.get("/sitzungsregeln", response_class=HTMLResponse)
async def sitzungsregeln_edit(request: Request, db: Session = Depends(get_db)):
    # DEMO: Auth disabled
    # if not is_logged_in(request):
    #     return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)
    regel = db.query(Sitzungsregel).filter(Sitzungsregel.id == 1).first()
    if not regel:
        regel = Sitzungsregel(id=1)
        db.add(regel)
        db.commit()

    content = f"""
    <h1>Sitzungsregeln (Berechnung)</h1>
    <form method="post" action="/admin/sitzungsregeln/update">
    <div class="row"><div class="col-md-6">
    <div class="card"><div class="card-header bg-primary text-white">Zeitdauern (Minuten)</div><div class="card-body">
    <div class="mb-3"><label>Block-Dauer</label><input type="number" name="block_minuten" class="form-control" value="{regel.block_minuten}" required></div>
    <div class="mb-3"><label>Sitzungs-Dauer</label><input type="number" name="sitzung_minuten" class="form-control" value="{regel.sitzung_minuten}" required></div>
    <div class="mb-3"><label>Pausen-Dauer</label><input type="number" name="pause_minuten" class="form-control" value="{regel.pause_minuten}" required></div>
    <div class="mb-3"><label>Gemeinderat-Dauer</label><input type="number" name="council_minuten" class="form-control" value="{regel.council_minuten}" required></div>
    </div></div>
    </div><div class="col-md-6">
    <div class="card"><div class="card-header bg-success text-white">Beschlussfähigkeit (Quorum)</div><div class="card-body">
    <div class="mb-3"><label>Standard</label><input type="number" name="quorum_standard" class="form-control" value="{regel.quorum_standard}" required></div>
    <div class="mb-3"><label>Poly</label><input type="number" name="quorum_poly" class="form-control" value="{regel.quorum_poly}" required></div>
    <div class="mb-3"><label>Kontroll</label><input type="number" name="quorum_kontroll" class="form-control" value="{regel.quorum_kontroll}" required></div>
    </div></div>
    </div></div>
    <div class="row mt-4"><div class="col-md-6">
    <div class="card"><div class="card-header bg-info text-white">Weitere Einstellungen</div><div class="card-body">
    <div class="mb-3"><label>Planungs-Wochen</label><input type="number" name="planungswochen" class="form-control" value="{regel.planungswochen}" required></div>
    <div class="mb-3"><label>Freitag-Modus</label><select name="freitag_modus" class="form-select" required>
    <option value="reserve" {'selected' if regel.freitag_modus == 'reserve' else ''}>Reserve</option>
    <option value="low_priority" {'selected' if regel.freitag_modus == 'low_priority' else ''}>Low Priority</option>
    <option value="forbidden" {'selected' if regel.freitag_modus == 'forbidden' else ''}>Forbidden</option>
    </select></div>
    </div></div>
    </div>
    <button type="submit" class="btn btn-primary btn-lg mt-4">Speichern</button>
    </form>
    """
    return HTMLResponse(with_sidebar(content, page="sitzungsregeln"))


@router.post("/sitzungsregeln/update")
async def sitzungsregeln_update(request: Request, db: Session = Depends(get_db)):
    # DEMO: Auth disabled
    # if not is_logged_in(request):
    #     return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)
    try:
        form = await request.form()
        regel = db.query(Sitzungsregel).filter(Sitzungsregel.id == 1).first()
        if not regel:
            regel = Sitzungsregel(id=1)
            db.add(regel)
        regel.block_minuten = int(form.get("block_minuten", 90))
        regel.sitzung_minuten = int(form.get("sitzung_minuten", 75))
        regel.pause_minuten = int(form.get("pause_minuten", 15))
        regel.council_minuten = int(form.get("council_minuten", 240))
        regel.quorum_standard = int(form.get("quorum_standard", 4))
        regel.quorum_poly = int(form.get("quorum_poly", 2))
        regel.quorum_kontroll = int(form.get("quorum_kontroll", 3))
        regel.planungswochen = int(form.get("planungswochen", 2))
        regel.freitag_modus = form.get("freitag_modus", "reserve")
        db.commit()
        return RedirectResponse(url="/admin/sitzungsregeln", status_code=status.HTTP_302_FOUND)
    except ValueError:
        db.rollback()
        return HTMLResponse(error_page("Fehler", "Alle Felder müssen gültige Zahlen sein.", "/admin/sitzungsregeln"))
    except Exception as e:
        db.rollback()
        return HTMLResponse(error_page("Fehler", f"Ein Fehler ist aufgetreten: {str(e)}", "/admin/sitzungsregeln"))


@router.get("/jahrespläne", response_class=HTMLResponse)
async def jahrespläne_list(request: Request, db: Session = Depends(get_db)):
    # DEMO: Auth disabled
    # if not is_logged_in(request):
    #     return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)

    filter_param = request.query_params.get("filter", "all")

    query = db.query(Jahresplan)
    if filter_param == "active":
        query = query.filter(Jahresplan.aktiv == True)
    elif filter_param == "inactive":
        query = query.filter(Jahresplan.aktiv == False)

    jahrespläne = query.order_by(Jahresplan.jahr.desc()).all()

    # Button styling based on active filter
    alle_class = "btn btn-sm btn-primary active" if filter_param == "all" else "btn btn-sm btn-outline-primary"
    aktiv_class = "btn btn-sm btn-primary active" if filter_param == "active" else "btn btn-sm btn-outline-primary"
    inaktiv_class = "btn btn-sm btn-primary active" if filter_param == "inactive" else "btn btn-sm btn-outline-primary"

    filter_buttons = f"""<div class="btn-group mb-4" role="group">
    <a href="/admin/jahrespläne?filter=all" class="{alle_class}">Alle</a>
    <a href="/admin/jahrespläne?filter=active" class="{aktiv_class}">Aktiv</a>
    <a href="/admin/jahrespläne?filter=inactive" class="{inaktiv_class}">Inaktiv</a>
</div>"""

    rows = "".join([
        f"<tr><td>{jp.jahr}</td><td>{escape_html(jp.bezeichnung)}</td><td>{'Aktiv' if jp.aktiv else 'Inaktiv'}</td><td><a href='/admin/jahrespläne/{jp.id}/edit' class='btn btn-sm btn-warning'>Edit</a> <a href='/admin/jahrespläne/{jp.id}/delete' class='btn btn-sm btn-danger' onclick=\"return confirm('Delete?')\">Delete</a></td></tr>"
        for jp in jahrespläne
    ])
    content = f"""
    <div class="d-flex justify-content-between mb-4"><h1>Jahrespläne ({len(jahrespläne)})</h1><a href="/admin/jahrespläne/new" class="btn btn-primary">Neuer Plan</a></div>
    {filter_buttons}
    <table class="table"><thead><tr><th>Jahr</th><th>Bezeichnung</th><th>Status</th><th>Actions</th></tr></thead><tbody>{rows}</tbody></table>
    """
    return HTMLResponse(with_sidebar(content, page="jahrespläne"))


@router.get("/jahrespläne/new", response_class=HTMLResponse)
async def jahrespläne_new(request: Request):
    # DEMO: Auth disabled
    # if not is_logged_in(request):
    #     return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)
    return """<html><head><title>New Jahresplan</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head><body><div class="container mt-5"><div class="col-md-6">
<h1>New Jahresplan</h1>
<form method="post" action="/admin/jahrespläne/create">
<div class="mb-3"><label>Jahr</label><input type="number" name="jahr" class="form-control" required></div>
<div class="mb-3"><label>Bezeichnung</label><input type="text" name="bezeichnung" class="form-control"></div>
<div class="mb-3"><input type="checkbox" name="aktiv" checked> Aktiv</div>
<button type="submit" class="btn btn-primary">Save</button> <a href="/admin/jahrespläne" class="btn btn-secondary">Cancel</a>
</form></div></div></body></html>"""


@router.post("/jahrespläne/create")
async def jahrespläne_create(request: Request, db: Session = Depends(get_db)):
    # DEMO: Auth disabled
    # if not is_logged_in(request):
    #     return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)
    try:
        form = await request.form()
        jahresplan = Jahresplan(
            jahr=int(form.get("jahr", 0)),
            bezeichnung=form.get("bezeichnung", "").strip(),
            aktiv=form.get("aktiv") == "on"
        )
        db.add(jahresplan)
        db.commit()
        return RedirectResponse(url="/admin/jahrespläne", status_code=status.HTTP_302_FOUND)
    except ValueError:
        db.rollback()
        return HTMLResponse(error_page("Fehler", "Jahr muss eine Zahl sein.", "/admin/jahrespläne/new"))
    except Exception as e:
        db.rollback()
        return HTMLResponse(error_page("Fehler", f"Ein Fehler ist aufgetreten: {str(e)}", "/admin/jahrespläne/new"))


@router.get("/jahrespläne/{jahresplan_id}/edit", response_class=HTMLResponse)
async def jahrespläne_edit(jahresplan_id: int, request: Request, db: Session = Depends(get_db)):
    # DEMO: Auth disabled
    # if not is_logged_in(request):
    #     return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)
    jahresplan = db.query(Jahresplan).filter(Jahresplan.id == jahresplan_id).first()
    if not jahresplan:
        return RedirectResponse(url="/admin/jahrespläne", status_code=status.HTTP_302_FOUND)
    checked = "checked" if jahresplan.aktiv else ""
    return f"""<html><head><title>Edit Jahresplan</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head><body><div class="container mt-5"><div class="col-md-6">
<h1>Edit Jahresplan</h1>
<form method="post" action="/admin/jahrespläne/{jahresplan_id}/update">
<div class="mb-3"><label>Jahr</label><input type="number" name="jahr" class="form-control" value="{jahresplan.jahr}" required></div>
<div class="mb-3"><label>Bezeichnung</label><input type="text" name="bezeichnung" class="form-control" value="{escape_html(jahresplan.bezeichnung)}"></div>
<div class="mb-3"><input type="checkbox" name="aktiv" {checked}> Aktiv</div>
<button type="submit" class="btn btn-primary">Update</button> <a href="/admin/jahrespläne" class="btn btn-secondary">Cancel</a>
</form></div></div></body></html>"""


@router.post("/jahrespläne/{jahresplan_id}/update")
async def jahrespläne_update(jahresplan_id: int, request: Request, db: Session = Depends(get_db)):
    # DEMO: Auth disabled
    # if not is_logged_in(request):
    #     return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)
    try:
        jahresplan = db.query(Jahresplan).filter(Jahresplan.id == jahresplan_id).first()
        if not jahresplan:
            return HTMLResponse(error_page("Fehler", "Dieser Jahresplan existiert nicht.", "/admin/jahrespläne"))
        form = await request.form()
        jahresplan.jahr = int(form.get("jahr", 0))
        jahresplan.bezeichnung = form.get("bezeichnung", "").strip()
        jahresplan.aktiv = form.get("aktiv") == "on"
        db.commit()
        return RedirectResponse(url="/admin/jahrespläne", status_code=status.HTTP_302_FOUND)
    except ValueError:
        db.rollback()
        return HTMLResponse(error_page("Fehler", "Jahr muss eine Zahl sein.", f"/admin/jahrespläne/{jahresplan_id}/edit"))
    except Exception as e:
        db.rollback()
        return HTMLResponse(error_page("Fehler", f"Ein Fehler ist aufgetreten: {str(e)}", f"/admin/jahrespläne/{jahresplan_id}/edit"))


@router.get("/jahrespläne/{jahresplan_id}/delete")
async def jahrespläne_delete(jahresplan_id: int, request: Request, db: Session = Depends(get_db)):
    # DEMO: Auth disabled
    # if not is_logged_in(request):
    #     return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)
    jahresplan = db.query(Jahresplan).filter(Jahresplan.id == jahresplan_id).first()
    if jahresplan:
        db.delete(jahresplan)
        db.commit()
    return RedirectResponse(url="/admin/jahrespläne", status_code=status.HTTP_302_FOUND)


@router.get("/perioden", response_class=HTMLResponse)
async def perioden_list(request: Request, db: Session = Depends(get_db)):
    """List all periods with person/committee counts."""
    # DEMO: Auth disabled
    # if not is_logged_in(request):
    #     return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)

    try:
        filter_param = request.query_params.get("filter", "all")

        query = db.query(Gemeinderatsperiode)
        if filter_param == "active":
            query = query.filter(Gemeinderatsperiode.aktiv == True)
        elif filter_param == "inactive":
            query = query.filter(Gemeinderatsperiode.aktiv == False)

        perioden = query.order_by(Gemeinderatsperiode.start_jahr.desc()).all()

        # Enrich perioden with counts - convert to dicts to avoid lazy loading
        perioden_list_data = []
        for periode in perioden:
            person_count = db.query(PeriodePerson).filter(
                PeriodePerson.periode_id == periode.id,
                PeriodePerson.end_datum.is_(None)
            ).count()
            committee_count = db.query(Ausschuss).filter(Ausschuss.periode_id == periode.id).count()
            perioden_list_data.append({
                'id': periode.id,
                'name': periode.name,
                'start_jahr': periode.start_jahr,
                'end_jahr': periode.end_jahr,
                'aktiv': periode.aktiv,
                'person_count': person_count,
                'committee_count': committee_count,
            })

        return templates.TemplateResponse("perioden.html", {
            "request": request,
            "page": "perioden",
            "perioden": perioden_list_data,
            "filter_param": filter_param,
        })
    except Exception as e:
        # Fallback: return empty list on error
        return templates.TemplateResponse("perioden.html", {
            "request": request,
            "page": "perioden",
            "perioden": [],
            "filter_param": "all",
        })


@router.get("/perioden/create", response_class=HTMLResponse)
async def perioden_create_form(request: Request):
    """Form to create a new period."""
    # DEMO: Auth disabled
    # if not is_logged_in(request):
    #     return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)

    return """<html><head><title>Neue Periode</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head><body><div class="container mt-5"><div class="col-md-6">
<h1>Neue Periode erstellen</h1>
<form method="post" action="/admin/perioden/create">
<div class="mb-3"><label>Name (z.B. P1)</label><input type="text" name="name" class="form-control" required></div>
<div class="mb-3"><label>Start Jahr</label><input type="number" name="start_jahr" class="form-control" required></div>
<div class="mb-3"><label>End Jahr</label><input type="number" name="end_jahr" class="form-control" required></div>
<div class="mb-3"><input type="checkbox" name="aktiv" checked> Aktiv</div>
<button type="submit" class="btn btn-primary">Erstellen</button> <a href="/admin/perioden" class="btn btn-secondary">Abbrechen</a>
</form></div></div></body></html>"""


@router.post("/perioden/create")
async def perioden_create(request: Request, db: Session = Depends(get_db)):
    """Create a new period."""
    # DEMO: Auth disabled
    # if not is_logged_in(request):
    #     return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)

    try:
        form = await request.form()
        name = form.get("name", "").strip()
        start_jahr = int(form.get("start_jahr", 0))
        end_jahr = int(form.get("end_jahr", 0))
        aktiv = form.get("aktiv") == "on"

        if not name or start_jahr <= 0 or end_jahr <= 0 or start_jahr > end_jahr:
            return HTMLResponse(error_page(
                "Fehler",
                "Bitte geben Sie gültige Daten ein. Name erforderlich, Start-Jahr <= End-Jahr.",
                "/admin/perioden/create"
            ))

        periode = Gemeinderatsperiode(
            name=name,
            start_jahr=start_jahr,
            end_jahr=end_jahr,
            aktiv=aktiv
        )
        db.add(periode)
        db.commit()
        return RedirectResponse(url="/admin/perioden", status_code=status.HTTP_302_FOUND)
    except IntegrityError:
        db.rollback()
        return HTMLResponse(error_page(
            "Fehler",
            "Eine Periode mit diesem Namen existiert bereits.",
            "/admin/perioden/create"
        ))
    except ValueError as e:
        db.rollback()
        return HTMLResponse(error_page(
            "Fehler",
            f"Ungültige Eingabe: {str(e)}",
            "/admin/perioden/create"
        ))
    except Exception as e:
        db.rollback()
        return HTMLResponse(error_page(
            "Fehler",
            f"Ein Fehler ist aufgetreten: {str(e)}",
            "/admin/perioden/create"
        ))


@router.get("/perioden/{periode_id}", response_class=HTMLResponse)
async def periode_detail(periode_id: int, request: Request, db: Session = Depends(get_db)):
    """Detail page for a period with person and committee management."""
    # DEMO: Auth disabled
    # if not is_logged_in(request):
    #     return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)

    periode = db.query(Gemeinderatsperiode).filter(Gemeinderatsperiode.id == periode_id).first()
    if not periode:
        return RedirectResponse(url="/admin/perioden", status_code=status.HTTP_302_FOUND)

    # Get active personen in period
    periode_personen = db.query(PeriodePerson).filter(
        PeriodePerson.periode_id == periode_id,
        PeriodePerson.end_datum.is_(None)
    ).all()

    # Get ausschuesse
    ausschuesse = db.query(Ausschuss).filter(Ausschuss.periode_id == periode_id).all()

    # Get all active persons not yet in period
    existing_person_ids = {pp.person_id for pp in periode_personen}
    available_persons = db.query(Person).filter(
        Person.aktiv == True,
        ~Person.id.in_(existing_person_ids)
    ).order_by(Person.nachname).all()

    # Count members per ausschuss
    ausschuss_member_counts = {}
    for ausschuss in ausschuesse:
        count = db.query(Mitgliedschaft).filter(
            Mitgliedschaft.ausschuss_id == ausschuss.id
        ).count()
        ausschuss_member_counts[ausschuss.id] = count

    return templates.TemplateResponse("periode_detail.html", {
        "request": request,
        "page": "perioden",
        "periode": periode,
        "personen": periode_personen,
        "personen_count": len(periode_personen),
        "ausschuesse": ausschuesse,
        "ausschuesse_count": len(ausschuesse),
        "ausschuss_member_counts": ausschuss_member_counts,
        "available_persons": available_persons,
    })


@router.post("/perioden/{periode_id}/person-add")
async def periode_person_add(periode_id: int, request: Request, db: Session = Depends(get_db)):
    """Add a person to a period (start_datum = today)."""
    # DEMO: Auth disabled
    # if not is_logged_in(request):
    #     return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)

    try:
        periode = db.query(Gemeinderatsperiode).filter(Gemeinderatsperiode.id == periode_id).first()
        if not periode:
            return RedirectResponse(url="/admin/perioden", status_code=status.HTTP_302_FOUND)

        form = await request.form()
        person_id = int(form.get("person_id", 0))
        if not person_id:
            return HTMLResponse(error_page(
                "Fehler",
                "Bitte wählen Sie eine Person aus.",
                f"/admin/perioden/{periode_id}"
            ))

        # Check if already exists
        existing = db.query(PeriodePerson).filter(
            PeriodePerson.periode_id == periode_id,
            PeriodePerson.person_id == person_id,
            PeriodePerson.end_datum.is_(None)
        ).first()
        if existing:
            return HTMLResponse(error_page(
                "Fehler",
                "Diese Person ist bereits in dieser Periode.",
                f"/admin/perioden/{periode_id}"
            ))

        periode_person = PeriodePerson(
            periode_id=periode_id,
            person_id=person_id,
            start_datum=date.today()
        )
        db.add(periode_person)
        db.commit()
        return RedirectResponse(url=f"/admin/perioden/{periode_id}", status_code=status.HTTP_302_FOUND)
    except ValueError as e:
        db.rollback()
        return HTMLResponse(error_page(
            "Fehler",
            f"Ungültige Eingabe: {str(e)}",
            f"/admin/perioden/{periode_id}"
        ))
    except Exception as e:
        db.rollback()
        return HTMLResponse(error_page(
            "Fehler",
            f"Ein Fehler ist aufgetreten: {str(e)}",
            f"/admin/perioden/{periode_id}"
        ))


@router.get("/perioden/{periode_id}/person/{person_id}/remove")
async def periode_person_remove(periode_id: int, person_id: int, request: Request, db: Session = Depends(get_db)):
    """Remove person from period (set end_datum = today) and trigger new Jahresplan variante."""
    # DEMO: Auth disabled
    # if not is_logged_in(request):
    #     return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)

    try:
        periode = db.query(Gemeinderatsperiode).filter(Gemeinderatsperiode.id == periode_id).first()
        if not periode:
            return RedirectResponse(url="/admin/perioden", status_code=status.HTTP_302_FOUND)

        # Mark person as removed from period
        periode_person = db.query(PeriodePerson).filter(
            PeriodePerson.periode_id == periode_id,
            PeriodePerson.person_id == person_id,
            PeriodePerson.end_datum.is_(None)
        ).first()
        if periode_person:
            periode_person.end_datum = date.today()
            periode_person.grund_austritt = "Aus Periode entfernt"
            db.add(periode_person)
            db.flush()

            # Remove all memberships for this person in this period
            memberships_to_remove = db.query(Mitgliedschaft).filter(
                Mitgliedschaft.periode_id == periode_id,
                Mitgliedschaft.person_id == person_id
            ).all()

            affected_ausschuesse_ids = set()
            for membership in memberships_to_remove:
                affected_ausschuesse_ids.add(membership.ausschuss_id)
                db.delete(membership)
            db.flush()

            # Create new Jahresplan variante for current year
            current_year = date.today().year
            latest_jahresplan = db.query(Jahresplan).filter(
                Jahresplan.periode_id == periode_id,
                Jahresplan.jahr == current_year
            ).order_by(Jahresplan.variante.desc()).first()

            if latest_jahresplan:
                new_variante = latest_jahresplan.variante + 1
                person_name = db.query(Person).filter(Person.id == person_id).first()
                person_name_str = f"{person_name.vorname} {person_name.nachname}" if person_name else "Person"

                new_jahresplan = Jahresplan(
                    periode_id=periode_id,
                    jahr=current_year,
                    variante=new_variante,
                    grund_variante=f"Austritt {person_name_str} - Quorum-Update erforderlich",
                    aktiv=True
                )
                db.add(new_jahresplan)
                db.flush()

                # Update quorum for affected ausschuesse
                for ausschuss_id in affected_ausschuesse_ids:
                    ausschuss = db.query(Ausschuss).filter(Ausschuss.id == ausschuss_id).first()
                    if ausschuss:
                        member_count = db.query(Mitgliedschaft).filter(
                            Mitgliedschaft.ausschuss_id == ausschuss_id,
                            Mitgliedschaft.periode_id == periode_id
                        ).count()
                        if member_count > 0:
                            new_quorum = calculate_quorum(member_count)
                            ausschuss.quorum_override = new_quorum

            db.commit()

        return RedirectResponse(url=f"/admin/perioden/{periode_id}", status_code=status.HTTP_302_FOUND)
    except Exception as e:
        db.rollback()
        return HTMLResponse(error_page(
            "Fehler",
            f"Ein Fehler ist aufgetreten: {str(e)}",
            f"/admin/perioden/{periode_id}"
        ))


@router.get("/perioden/{periode_id}/ausschuss-add", response_class=HTMLResponse)
async def ausschuss_add_form(periode_id: int, request: Request, db: Session = Depends(get_db)):
    """Form to add a new committee to period."""
    # DEMO: Auth disabled
    # if not is_logged_in(request):
    #     return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)

    periode = db.query(Gemeinderatsperiode).filter(Gemeinderatsperiode.id == periode_id).first()
    if not periode:
        return RedirectResponse(url="/admin/perioden", status_code=status.HTTP_302_FOUND)

    typ_options = "".join([f"<option value='{t.value}'>{t.value}</option>" for t in AusschussTyp])
    return f"""<html><head><title>Neuer Ausschuss</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head><body><div class="container mt-5"><div class="col-md-6">
<h1>Neuer Ausschuss für Periode {escape_html(periode.name)}</h1>
<form method="post" action="/admin/perioden/{periode_id}/ausschuss-add">
<div class="mb-3"><label>Name</label><input type="text" name="name" class="form-control" required></div>
<div class="mb-3"><label>Typ</label><select name="typ" class="form-select" required>{typ_options}</select></div>
<div class="mb-3"><label>Turnus</label><input type="text" name="turnus" class="form-control"></div>
<div class="mb-3"><input type="checkbox" name="aktiv" checked> Aktiv</div>
<button type="submit" class="btn btn-primary">Erstellen</button> <a href="/admin/perioden/{periode_id}" class="btn btn-secondary">Abbrechen</a>
</form></div></div></body></html>"""


@router.post("/perioden/{periode_id}/ausschuss-add")
async def ausschuss_add(periode_id: int, request: Request, db: Session = Depends(get_db)):
    """Create a new committee for the period."""
    # DEMO: Auth disabled
    # if not is_logged_in(request):
    #     return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)

    try:
        periode = db.query(Gemeinderatsperiode).filter(Gemeinderatsperiode.id == periode_id).first()
        if not periode:
            return RedirectResponse(url="/admin/perioden", status_code=status.HTTP_302_FOUND)

        form = await request.form()
        name = form.get("name", "").strip()
        typ_str = form.get("typ", "").strip()
        turnus = form.get("turnus", "").strip()
        aktiv = form.get("aktiv") == "on"

        if not name or not typ_str:
            return HTMLResponse(error_page(
                "Fehler",
                "Name und Typ sind erforderlich.",
                f"/admin/perioden/{periode_id}/ausschuss-add"
            ))

        ausschuss = Ausschuss(
            periode_id=periode_id,
            name=name,
            typ=AusschussTyp(typ_str),
            turnus=turnus or None,
            aktiv=aktiv
        )
        db.add(ausschuss)
        db.commit()
        return RedirectResponse(url=f"/admin/perioden/{periode_id}", status_code=status.HTTP_302_FOUND)
    except ValueError as e:
        db.rollback()
        return HTMLResponse(error_page(
            "Fehler",
            f"Ungültige Eingabe: {str(e)}",
            f"/admin/perioden/{periode_id}/ausschuss-add"
        ))
    except Exception as e:
        db.rollback()
        return HTMLResponse(error_page(
            "Fehler",
            f"Ein Fehler ist aufgetreten: {str(e)}",
            f"/admin/perioden/{periode_id}/ausschuss-add"
        ))


@router.get("/perioden/{periode_id}/edit", response_class=HTMLResponse)
async def periode_edit(periode_id: int, request: Request, db: Session = Depends(get_db)):
    """Edit period basic info."""
    # DEMO: Auth disabled
    # if not is_logged_in(request):
    #     return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)

    periode = db.query(Gemeinderatsperiode).filter(Gemeinderatsperiode.id == periode_id).first()
    if not periode:
        return RedirectResponse(url="/admin/perioden", status_code=status.HTTP_302_FOUND)

    checked = "checked" if periode.aktiv else ""
    return f"""<html><head><title>Edit Periode</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head><body><div class="container mt-5"><div class="col-md-6">
<h1>Edit Periode</h1>
<form method="post" action="/admin/perioden/{periode_id}/update">
<div class="mb-3"><label>Name</label><input type="text" name="name" class="form-control" value="{escape_html(periode.name)}" required></div>
<div class="mb-3"><label>Start Jahr</label><input type="number" name="start_jahr" class="form-control" value="{periode.start_jahr}" required></div>
<div class="mb-3"><label>End Jahr</label><input type="number" name="end_jahr" class="form-control" value="{periode.end_jahr}" required></div>
<div class="mb-3"><input type="checkbox" name="aktiv" {checked}> Aktiv</div>
<button type="submit" class="btn btn-primary">Update</button> <a href="/admin/perioden" class="btn btn-secondary">Cancel</a>
</form></div></div></body></html>"""


@router.post("/perioden/{periode_id}/update")
async def periode_update(periode_id: int, request: Request, db: Session = Depends(get_db)):
    """Update period basic info."""
    # DEMO: Auth disabled
    # if not is_logged_in(request):
    #     return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)

    try:
        periode = db.query(Gemeinderatsperiode).filter(Gemeinderatsperiode.id == periode_id).first()
        if not periode:
            return RedirectResponse(url="/admin/perioden", status_code=status.HTTP_302_FOUND)

        form = await request.form()
        periode.name = form.get("name", "").strip()
        periode.start_jahr = int(form.get("start_jahr", 0))
        periode.end_jahr = int(form.get("end_jahr", 0))
        periode.aktiv = form.get("aktiv") == "on"

        db.commit()
        return RedirectResponse(url="/admin/perioden", status_code=status.HTTP_302_FOUND)
    except ValueError as e:
        db.rollback()
        return HTMLResponse(error_page(
            "Fehler",
            f"Ungültige Eingabe: {str(e)}",
            f"/admin/perioden/{periode_id}/edit"
        ))
    except IntegrityError:
        db.rollback()
        return HTMLResponse(error_page(
            "Fehler",
            "Ein Name-Konflikt ist aufgetreten.",
            f"/admin/perioden/{periode_id}/edit"
        ))
    except Exception as e:
        db.rollback()
        return HTMLResponse(error_page(
            "Fehler",
            f"Ein Fehler ist aufgetreten: {str(e)}",
            f"/admin/perioden/{periode_id}/edit"
        ))


@router.get("/perioden/{periode_id}/delete")
async def periode_delete(periode_id: int, request: Request, db: Session = Depends(get_db)):
    """Delete a period."""
    # DEMO: Auth disabled
    # if not is_logged_in(request):
    #     return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)

    try:
        periode = db.query(Gemeinderatsperiode).filter(Gemeinderatsperiode.id == periode_id).first()
        if periode:
            # Check if has personen or ausschuesse
            person_count = db.query(PeriodePerson).filter(PeriodePerson.periode_id == periode_id).count()
            ausschuss_count = db.query(Ausschuss).filter(Ausschuss.periode_id == periode_id).count()

            if person_count > 0 or ausschuss_count > 0:
                return HTMLResponse(f"""<html><head><title>Fehler</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head><body><div class="container mt-5"><div class="col-md-6">
<div class="alert alert-danger">
<h4>Periode kann nicht gelöscht werden</h4>
<p>Die Periode enthält noch {person_count} Personen und {ausschuss_count} Ausschüsse.</p>
<p>Bitte entfernen Sie zuerst alle Personen und Ausschüsse.</p>
</div>
<a href="/admin/perioden/{periode_id}" class="btn btn-info">Zurück zur Periode</a>
<a href="/admin/perioden" class="btn btn-secondary">Zur Liste</a>
</div></div></body></html>""")

            db.delete(periode)
            db.commit()

        return RedirectResponse(url="/admin/perioden", status_code=status.HTTP_302_FOUND)
    except Exception as e:
        db.rollback()
        return HTMLResponse(error_page(
            "Fehler",
            f"Ein Fehler ist aufgetreten: {str(e)}",
            "/admin/perioden"
        ))


@router.get("/sitzungen", response_class=HTMLResponse)
async def sitzungen(request: Request, month: int = None, year: int = None, db: Session = Depends(get_db)):
    """Zeige alle Sitzungstermine aller Ausschüsse in einer Tabellenansicht."""
    # DEMO: Auth disabled
    # if not is_logged_in(request):
    #     return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)

    from datetime import datetime, timedelta
    from dateutil.relativedelta import relativedelta

    now = datetime.now()
    if month is None:
        month = now.month
    if year is None:
        year = now.year

    # Erstelle Datum für Monatsanfang
    month_start = datetime(year, month, 1)
    month_end = month_start + relativedelta(months=1) - timedelta(days=1)

    # Hole alle Ausschüsse
    ausschuesse = db.query(Ausschuss).filter(Ausschuss.aktiv == True).order_by(Ausschuss.name).all()

    # Erstelle Dummy-Sitzungsdaten für diesen Monat
    sitzungen = []
    wochentage_map = {0: "Mo", 1: "Di", 2: "Mi", 3: "Do", 4: "Fr", 5: "Sa", 6: "So"}

    for ausschuss in ausschuesse:
        # Erzeuge 1-4 Sitzungen pro Ausschuss im Monat
        for week in range(1, 5):
            date = month_start + timedelta(weeks=week-1, days=ausschuss.id % 3)
            if date.month == month and date.year == year:
                hour = 10 + (ausschuss.id % 5)
                sitzungen.append({
                    "id": f"{ausschuss.id}-{week}",
                    "ausschuss_id": ausschuss.id,
                    "ausschuss_name": ausschuss.name,
                    "typ": ausschuss.typ,
                    "datum": date.strftime("%d.%m.%Y"),
                    "wochentag": wochentage_map[date.weekday()],
                    "uhrzeit": f"{hour:02d}:00",
                    "ort": "Gemeindehaus",
                    "beschlussfaehig": week % 2 == 0,
                })

    # Sortiere nach Datum
    sitzungen.sort(key=lambda x: x["datum"])

    # Formatiere Monat für Anzeige
    month_name = datetime(year, month, 1).strftime("%B %Y")
    if month_name.startswith("0"):  # Falls Probleme mit Formatierung
        month_name = ["Januar", "Februar", "März", "April", "Mai", "Juni",
                      "Juli", "August", "September", "Oktober", "November", "Dezember"][month-1] + f" {year}"

    return templates.TemplateResponse("sitzungen.html", {
        "request": request,
        "page": "sitzungen",
        "sitzungen": sitzungen,
        "current_month": month_name,
    })


@router.get("/smart-search", response_class=HTMLResponse)
def admin_smart_search(request: Request, db: Session = Depends(get_db)):
    """Admin Smart-Search UI — Natural Language Query with Direct Booking."""
    # DEMO: Auth disabled for testing
    # if not is_logged_in(request):
    #     return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)

    html = f"""
    <!DOCTYPE html>
    <html lang="de">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Smart-Search — Admin Portal</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
            :root {{
                --primary-dark: #1e3a8a;
                --primary: #2563eb;
                --accent-yellow: #fbbf24;
            }}
            body {{ display: flex; min-height: 100vh; margin: 0; }}
            .sidebar {{
                width: 280px;
                background: linear-gradient(180deg, var(--primary-dark) 0%, var(--primary) 100%);
                padding: 25px;
                border-right: 4px solid var(--accent-yellow);
                color: var(--accent-yellow);
                flex-shrink: 0;
            }}
            .sidebar a {{
                display: block;
                padding: 12px 16px;
                margin: 8px 0;
                text-decoration: none;
                color: var(--accent-yellow);
                border-radius: 8px;
                transition: all 0.3s;
                font-weight: 500;
            }}
            .sidebar a:hover {{ background: rgba(251, 191, 36, 0.15); }}
            .sidebar a.active {{ color: #fff9e6; background: rgba(251, 191, 36, 0.2); font-weight: 600; }}
            .sidebar .navbar-brand {{ margin-bottom: 20px; font-size: 20px; font-weight: bold; }}
            .sidebar hr {{ border-color: rgba(251, 191, 36, 0.3); }}
            .sidebar .btn {{ margin-top: 15px; }}
            .content {{
                flex: 1;
                padding: 30px;
                background: #f9fafb;
                overflow-y: auto;
            }}
            .content h1 {{ color: var(--primary-dark); margin-bottom: 25px; }}
            .search-box {{
                display: flex;
                gap: 12px;
                margin-bottom: 20px;
            }}
            .search-box input {{
                flex: 1;
                padding: 12px;
                border: 1px solid #d1d5db;
                border-radius: 6px;
                font-size: 14px;
            }}
            .search-box button {{
                padding: 12px 24px;
                background: var(--primary);
                color: white;
                border: none;
                border-radius: 6px;
                cursor: pointer;
                font-weight: bold;
            }}
            .search-box button:hover {{ background: #1d4ed8; }}
            .results-table {{
                background: white;
                border-radius: 8px;
                box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
                overflow: hidden;
                margin-top: 20px;
            }}
            .results-table table {{ margin: 0; font-size: 13px; }}
            .results-table thead {{ background: var(--primary-dark); color: white; }}
            .results-table th {{ padding: 12px 14px; }}
            .results-table td {{ padding: 10px 14px; }}
            .status-badge {{
                display: inline-block;
                padding: 4px 8px;
                background: #dcfce7;
                color: #166534;
                border-radius: 4px;
                font-size: 12px;
                font-weight: bold;
            }}
            .action-btn {{
                padding: 6px 12px;
                background: var(--primary);
                color: white;
                border: none;
                border-radius: 4px;
                cursor: pointer;
                font-size: 12px;
            }}
            .action-btn.cancel {{ background: #dc2626; }}
            .action-btn:hover {{ opacity: 0.85; }}
            .empty-state {{ text-align: center; padding: 40px; color: #6b7280; }}
            .alert {{ margin-bottom: 20px; }}
        </style>
    </head>
    <body>
        <div class="sidebar">
            <div class="navbar-brand">Ausschussplaner</div>
            <a href="/admin">Dashboard</a>
            <a href="/admin/personen">Personen</a>
            <a href="/admin/ausschuesse">Ausschüsse</a>
            <a href="/admin/perioden">Perioden</a>
            <a href="/admin/abwesenheiten">Abwesenheiten</a>
            <a href="/admin/verfuegbarkeiten">Verfügbarkeiten</a>
            <a href="/admin/jahrespläne">Jahrespläne</a>
            <a href="/admin/sitzungsregeln">Sitzungsregeln</a>
            <a href="/admin/smart-search" class="active">Smart-Search</a>
            <hr>
            <a href="/admin/logout" class="btn btn-sm btn-danger w-100">Logout</a>
        </div>

        <div class="content">
            <h1>📊 Smart-Search (Admin)</h1>
            <p style="color: #666; margin-bottom: 20px;">
                Natürlichsprachliche Terminplanung — Finde beschlussfähige Termine für Ausschüsse.
            </p>

            <div class="search-box">
                <input
                    type="text"
                    id="query"
                    placeholder="z.B. Beste STR im Juni mit ≥80% Verfügbarkeit, keine Freitags"
                    onkeypress="if(event.key==='Enter') runSearch()"
                />
                <button onclick="runSearch()">Suchen</button>
            </div>

            <div id="error" class="alert alert-danger" style="display: none;"></div>
            <div id="success" class="alert alert-success" style="display: none;"></div>

            <div id="results" style="display: none;">
                <div class="results-table">
                    <table id="resultsTable">
                        <thead>
                            <tr>
                                <th>Datum</th>
                                <th>Tag</th>
                                <th>Zeit</th>
                                <th>Verfügbarkeit</th>
                                <th>Teilnehmer</th>
                                <th>Abwesende</th>
                                <th>Status</th>
                                <th>Aktion</th>
                            </tr>
                        </thead>
                        <tbody id="resultsBody"></tbody>
                    </table>
                </div>
            </div>

            <div id="empty" class="empty-state" style="display: none;">
                Keine Ergebnisse.
            </div>
        </div>

        <script>
            const API = 'http://localhost:8000';
            let currentResults = [];

            async function runSearch() {{
                const query = document.getElementById('query').value.trim();
                if (!query) return;

                document.getElementById('error').style.display = 'none';
                document.getElementById('success').style.display = 'none';
                document.getElementById('results').style.display = 'none';
                document.getElementById('empty').style.display = 'none';

                try {{
                    const res = await fetch(`${{API}}/api/schedule-assistant/smart-search`, {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/json' }},
                        body: JSON.stringify({{ query, user_id: 1 }})
                    }});
                    const data = await res.json();

                    if (data.error) {{
                        showError(data.error);
                    }} else {{
                        currentResults = data.results || [];
                        if (currentResults.length > 0) {{
                            renderResults();
                            document.getElementById('results').style.display = 'block';
                        }} else {{
                            document.getElementById('empty').style.display = 'block';
                        }}
                    }}
                }} catch (err) {{
                    showError(`Fehler: ${{err.message}}`);
                }}
            }}

            function renderResults() {{
                const tbody = document.getElementById('resultsBody');
                tbody.innerHTML = '';
                currentResults.forEach((r, idx) => {{
                    const row = document.createElement('tr');
                    // Abwesenheits-Info formatieren
                    let absentHtml = '—';
                    if (r.absent_persons && r.absent_persons.length > 0) {{
                        absentHtml = r.absent_persons.map(p => `<div style="font-size:11px;">${{p.name}} <span style="font-size:9px;">(${{p.grund}})</span></div>`).join('');
                    }} else if (r.unavailable_persons && r.unavailable_persons.length > 0) {{
                        absentHtml = r.unavailable_persons.map(name => `<div style="font-size:11px;">${{name}}</div>`).join('');
                    }}

                    row.innerHTML = `
                        <td>${{new Date(r.date).toLocaleDateString('de-AT')}}</td>
                        <td>${{r.weekday}}</td>
                        <td><strong>${{r.time}}</strong></td>
                        <td><strong style="color: ${{r.availability_percent >= 80 ? '#16a34a' : '#d97706'}}">${{r.availability_percent}}%</strong></td>
                        <td>${{r.participants_available}} / ${{r.participants_total}}</td>
                        <td style="font-size:11px; color:#7c3aed;">${{absentHtml}}</td>
                        <td><span class="status-badge">${{r.booked ? '✅ Gebucht' : '—'}}</span></td>
                        <td>
                            <button class="action-btn" onclick="bookTermin(${{idx}})">
                                📌 Buchen
                            </button>
                        </td>
                    `;
                    tbody.appendChild(row);
                }});
            }}

            async function bookTermin(idx) {{
                const result = currentResults[idx];
                if (!window.confirm('Termin wirklich buchen?')) return;

                try {{
                    const res = await fetch(`${{API}}/api/schedule-assistant/smart-search/book`, {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/json' }},
                        body: JSON.stringify({{
                            user_id: 1,
                            meeting_type: 'str',
                            ausschuss_id: null,
                            termin_datum: result.date,
                            termin_zeit: result.time
                        }})
                    }});
                    if (res.ok) {{
                        showSuccess('Termin erfolgreich gebucht!');
                        setTimeout(runSearch, 2000);
                    }} else {{
                        const err = await res.json();
                        showError(err.detail || 'Buchung fehlgeschlagen');
                    }}
                }} catch (err) {{
                    showError(`Fehler: ${{err.message}}`);
                }}
            }}

            function showError(msg) {{
                document.getElementById('error').textContent = msg;
                document.getElementById('error').style.display = 'block';
            }}

            function showSuccess(msg) {{
                document.getElementById('success').textContent = msg;
                document.getElementById('success').style.display = 'block';
            }}
        </script>
    </body>
    </html>
    """
    return html
