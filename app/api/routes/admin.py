"""Admin Web-UI Routes."""
from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from html import escape
from urllib.parse import urlparse
import os

from datetime import date, datetime
from app.db.base import get_db
from app.models.models import (
    Person, Ausschuss, Jahresplan, Abwesenheit, Mitgliedschaft, Sitzungsregel, Verfuegbarkeit,
    Gemeinderatsperiode, PeriodePerson
)
from app.models.enums import AbwesenheitsArt, Rolle, Wochentag, AusschussTyp
from math import ceil

router = APIRouter(prefix="/admin", tags=["Admin"])

ADMIN_PASSWORD = "admin123"

# Template-Setup: suche templates/ im Root-Verzeichnis
template_dir = os.path.join(os.path.dirname(__file__), "..", "..", "templates")
templates = Jinja2Templates(directory=template_dir)


def escape_html(text: str) -> str:
    """HTML-escape user input to prevent XSS."""
    if not text:
        return ""
    return escape(str(text))


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
    return request.cookies.get("admin_session") == "logged_in"


def calculate_quorum(member_count: int) -> int:
    """Calculate quorum as 50% of members + Obmann must be present.

    Returns: ceil(total_members / 2) — minimum members needed for quorum.
    Obmann is mandatory (separate requirement).
    """
    return ceil(member_count / 2)


@router.get("/login", response_class=HTMLResponse)
async def login_page(error: str = ""):
    error_html = f"<div class='alert alert-danger' role='alert'>Falsches Passwort. Bitte versuchen Sie es erneut.</div>" if error else ""
    return f"""<html><head><title>Login</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<style>body{{background:linear-gradient(135deg,#667eea,#764ba2);min-height:100vh}}
.login-container{{max-width:400px;margin-top:150px}}</style>
</head><body><div class="container"><div class="login-container mx-auto">
<div class="card"><div class="card-body p-5">
<h2 class="text-center mb-4">AusschussPlaner</h2>
{error_html}
<form method="post" action="/admin/login">
<div class="mb-3"><label class="form-label">Password</label>
<input type="password" name="password" class="form-control" required autofocus>
<small class="text-muted">Demo: admin123</small></div>
<button type="submit" class="btn btn-primary w-100">Login</button>
</form></div></div></div></div></body></html>"""


@router.post("/login")
async def login(request: Request):
    form = await request.form()
    if form.get("password") == ADMIN_PASSWORD:
        response = RedirectResponse(url="/admin", status_code=status.HTTP_302_FOUND)
        response.set_cookie("admin_session", "logged_in", max_age=86400, httponly=True, samesite="Strict")
        return response
    return HTMLResponse(await login_page(error="true"))


@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)
    response.delete_cookie("admin_session")
    return response


@router.get("", response_class=HTMLResponse)
async def dashboard(request: Request):
    if not is_logged_in(request):
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)
    return """<html><head><title>Dashboard</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<style>body{background:#f5f7fa}.sidebar{background:#2c3e50;color:white;padding:20px;min-height:100vh}.sidebar a{color:white;display:block;padding:10px;text-decoration:none}.card{margin:10px 0}</style>
</head><body><div class="row g-0"><div class="col-md-3 sidebar">
<h4>AusschussPlaner</h4><a href="/admin">Dashboard</a><a href="/admin/perioden">Perioden</a><a href="/admin/personen">Personen</a><a href="/admin/ausschuesse">Ausschuesse</a><a href="/admin/abwesenheiten">Abwesenheiten</a><a href="/admin/verfuegbarkeiten">Verfügbarkeiten</a><a href="/admin/jahrespläne">Jahrespläne</a><a href="/admin/sitzungsregeln">Sitzungsregeln</a><a href="/admin/logout">Logout</a>
</div><div class="col-md-9 p-4">
<h1>Dashboard</h1>
<div class="row"><div class="col-md-6"><div class="card"><div class="card-body"><h5 class="card-title">Perioden & Stammdaten</h5><ul class="list-unstyled"><li><a href="/admin/perioden">Perioden verwalten</a></li><li><a href="/admin/personen">Personen verwalten</a></li><li><a href="/admin/ausschuesse">Ausschuesse verwalten</a></li><li><a href="/admin/abwesenheiten">Abwesenheiten verwalten</a></li></ul></div></div></div><div class="col-md-6"><div class="card"><div class="card-body"><h5 class="card-title">Planung</h5><ul class="list-unstyled"><li><a href="/admin/jahrespläne">Jahrespläne</a></li><li><a href="/admin/sitzungsregeln">Sitzungsregeln</a></li></ul></div></div></div></div>
</div></div></body></html>"""


@router.get("/personen", response_class=HTMLResponse)
async def personen_list(request: Request, db: Session = Depends(get_db)):
    if not is_logged_in(request):
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)

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
        f"<tr><td>{p.id}</td><td>{escape_html(p.vorname)} {escape_html(p.nachname)}</td><td>{escape_html(p.gremium or '-')}</td><td>{'Aktiv' if p.aktiv else 'Inaktiv'}</td><td><a href='/admin/personen/{p.id}/edit' class='btn btn-sm btn-warning'>Edit</a> <a href='/admin/personen/{p.id}/delete' class='btn btn-sm btn-danger' onclick=\"return confirm('Delete?')\">Delete</a></td></tr>"
        for p in persons
    ])

    return f"""<html><head><title>Personen</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<style>body{{background:#f5f7fa}} .sidebar{{background:#2c3e50;color:white;padding:20px}}.sidebar a{{color:white;display:block;padding:10px;text-decoration:none}}</style>
</head><body><div class="row g-0"><div class="col-md-3 sidebar">
<h4>AusschussPlaner</h4><a href="/admin">Dashboard</a><a href="/admin/personen">Personen</a><a href="/admin/ausschuesse">Ausschuesse</a><a href="/admin/abwesenheiten">Abwesenheiten</a><a href="/admin/verfuegbarkeiten">Verfügbarkeiten</a><a href="/admin/jahrespläne">Jahrespläne</a><a href="/admin/sitzungsregeln">Sitzungsregeln</a><a href="/admin/logout">Logout</a>
</div><div class="col-md-9 p-4">
<div class="d-flex justify-content-between mb-4"><h1>Personen ({len(persons)})</h1><a href="/admin/personen/new" class="btn btn-primary">New</a></div>
{filter_buttons}
<table class="table"><thead><tr><th>ID</th><th>Name</th><th>Gremium</th><th>Status</th><th>Actions</th></tr></thead><tbody>{rows}</tbody></table>
</div></div></body></html>"""


@router.get("/personen/new", response_class=HTMLResponse)
async def personen_new(request: Request):
    if not is_logged_in(request):
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)
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
    if not is_logged_in(request):
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)
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
    if not is_logged_in(request):
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)
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
<div class="mb-3"><label>Gremium</label><input type="text" name="gremium" class="form-control" value="{escape_html(person.gremium or '')}"></div>
<div class="mb-3"><label>Email</label><input type="email" name="email" class="form-control" value="{escape_html(person.email or '')}"></div>
<div class="mb-3"><input type="checkbox" name="aktiv" {checked}> Aktiv</div>
<button type="submit" class="btn btn-primary">Update</button> <a href="/admin/personen" class="btn btn-secondary">Cancel</a>
</form></div></div></body></html>"""


@router.post("/personen/{person_id}/update")
async def personen_update(person_id: int, request: Request, db: Session = Depends(get_db)):
    if not is_logged_in(request):
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)
    person = db.query(Person).filter(Person.id == person_id).first()
    if person:
        form = await request.form()
        person.vorname = form.get("vorname", "").strip()
        person.nachname = form.get("nachname", "").strip()
        person.gremium = form.get("gremium", "").strip() or None
        person.email = form.get("email", "").strip() or None
        person.aktiv = form.get("aktiv") == "on"
        db.commit()
    return RedirectResponse(url="/admin/personen", status_code=status.HTTP_302_FOUND)


@router.get("/personen/{person_id}/delete", response_class=HTMLResponse)
async def personen_delete(person_id: int, request: Request, db: Session = Depends(get_db)):
    if not is_logged_in(request):
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)
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
    if not is_logged_in(request):
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)

    filter_param = request.query_params.get("filter", "all")

    query = db.query(Ausschuss)
    if filter_param == "active":
        query = query.filter(Ausschuss.aktiv == True)
    elif filter_param == "inactive":
        query = query.filter(Ausschuss.aktiv == False)

    ausschuesse = query.all()

    # Button styling based on active filter
    alle_class = "btn btn-sm btn-primary active" if filter_param == "all" else "btn btn-sm btn-outline-primary"
    aktiv_class = "btn btn-sm btn-primary active" if filter_param == "active" else "btn btn-sm btn-outline-primary"
    inaktiv_class = "btn btn-sm btn-primary active" if filter_param == "inactive" else "btn btn-sm btn-outline-primary"

    filter_buttons = f"""<div class="btn-group mb-4" role="group">
    <a href="/admin/ausschuesse?filter=all" class="{alle_class}">Alle</a>
    <a href="/admin/ausschuesse?filter=active" class="{aktiv_class}">Aktiv</a>
    <a href="/admin/ausschuesse?filter=inactive" class="{inaktiv_class}">Inaktiv</a>
</div>"""

    rows = "".join([
        f"<tr><td>{a.id}</td><td>{escape_html(a.name)}</td><td>{escape_html(a.turnus)}</td><td>{'Aktiv' if a.aktiv else 'Inaktiv'}</td><td><a href='/admin/ausschuesse/{a.id}/mitgliedschaften' class='btn btn-sm btn-info'>Members</a> <a href='/admin/ausschuesse/{a.id}/edit' class='btn btn-sm btn-warning'>Edit</a> <a href='/admin/ausschuesse/{a.id}/delete' class='btn btn-sm btn-danger' onclick=\"return confirm('Delete?')\">Delete</a></td></tr>"
        for a in ausschuesse
    ])
    return f"""<html><head><title>Ausschuesse</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<style>body{{background:#f5f7fa}}.sidebar{{background:#2c3e50;color:white;padding:20px}}.sidebar a{{color:white;display:block;padding:10px;text-decoration:none}}</style>
</head><body><div class="row g-0"><div class="col-md-3 sidebar">
<h4>AusschussPlaner</h4><a href="/admin">Dashboard</a><a href="/admin/personen">Personen</a><a href="/admin/ausschuesse">Ausschuesse</a><a href="/admin/abwesenheiten">Abwesenheiten</a><a href="/admin/verfuegbarkeiten">Verfügbarkeiten</a><a href="/admin/jahrespläne">Jahrespläne</a><a href="/admin/sitzungsregeln">Sitzungsregeln</a><a href="/admin/logout">Logout</a>
</div><div class="col-md-9 p-4">
<h1>Ausschuesse ({len(ausschuesse)})</h1>
{filter_buttons}
<table class="table"><thead><tr><th>ID</th><th>Name</th><th>Turnus</th><th>Status</th><th>Actions</th></tr></thead><tbody>{rows}</tbody></table>
</div></div></body></html>"""


@router.get("/ausschuesse/{ausschuss_id}/edit", response_class=HTMLResponse)
async def ausschuesse_edit(ausschuss_id: int, request: Request, db: Session = Depends(get_db)):
    if not is_logged_in(request):
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)
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
    if not is_logged_in(request):
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)
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
    if not is_logged_in(request):
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)
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
    if not is_logged_in(request):
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)
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
<h4>AusschussPlaner</h4><a href="/admin">Dashboard</a><a href="/admin/ausschuesse">Ausschuesse</a><a href="/admin/logout">Logout</a>
</div><div class="col-md-9 p-4">
<div class="d-flex justify-content-between mb-4"><h1>{ausschuss.name} — Mitgliedschaften</h1><a href='/admin/ausschuesse/{ausschuss_id}/mitgliedschaften/add' class='btn btn-primary'>Add Member</a></div>
<table class="table"><thead><tr><th>Person</th><th>Rolle</th><th>Actions</th></tr></thead><tbody>{rows}</tbody></table>
<a href="/admin/ausschuesse" class="btn btn-secondary mt-3">Back</a>
</div></div></body></html>"""


@router.get("/ausschuesse/{ausschuss_id}/mitgliedschaften/add", response_class=HTMLResponse)
async def mitgliedschaften_add_form(ausschuss_id: int, request: Request, db: Session = Depends(get_db)):
    if not is_logged_in(request):
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)
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
    if not is_logged_in(request):
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)
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
    if not is_logged_in(request):
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)
    mitgliedschaft = db.query(Mitgliedschaft).filter(Mitgliedschaft.id == mitgliedschaft_id).first()
    if mitgliedschaft:
        db.delete(mitgliedschaft)
        db.commit()
    return RedirectResponse(url=f"/admin/ausschuesse/{ausschuss_id}/mitgliedschaften", status_code=status.HTTP_302_FOUND)


@router.get("/verfuegbarkeiten", response_class=HTMLResponse)
async def verfuegbarkeiten_list(request: Request, db: Session = Depends(get_db)):
    if not is_logged_in(request):
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)
    persons = db.query(Person).filter(Person.aktiv == True).order_by(Person.nachname).all()
    return f"""<html><head><title>Verfügbarkeiten</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<style>body{{background:#f5f7fa}}.sidebar{{background:#2c3e50;color:white;padding:20px;min-height:100vh}}.sidebar a{{color:white;display:block;padding:10px;text-decoration:none}}</style>
</head><body><div class="row g-0"><div class="col-md-3 sidebar">
<h4>AusschussPlaner</h4><a href="/admin">Dashboard</a><a href="/admin/personen">Personen</a><a href="/admin/ausschuesse">Ausschuesse</a><a href="/admin/abwesenheiten">Abwesenheiten</a><a href="/admin/verfuegbarkeiten">Verfügbarkeiten</a><a href="/admin/jahrespläne">Jahrespläne</a><a href="/admin/sitzungsregeln">Sitzungsregeln</a><a href="/admin/logout">Logout</a>
</div><div class="col-md-9 p-4">
<h1>Verfügbarkeiten</h1>
<form method="get" action="/admin/verfuegbarkeiten/edit">
<div class="mb-3"><label>Person</label><select name="person_id" class="form-select" required onchange="this.form.submit()">
<option value="">-- Bitte wählen --</option>
{''.join([f'<option value="{p.id}">{p.vorname} {p.nachname}</option>' for p in persons])}
</select></div>
</form>
</div></div></body></html>"""


@router.get("/verfuegbarkeiten/edit", response_class=HTMLResponse)
async def verfuegbarkeiten_edit(person_id: int, request: Request, db: Session = Depends(get_db)):
    if not is_logged_in(request):
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)
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
<h4>AusschussPlaner</h4><a href="/admin">Dashboard</a><a href="/admin/verfuegbarkeiten">Verfügbarkeiten</a><a href="/admin/logout">Logout</a>
</div><div class="col-md-9 p-4">
<h2>{person.vorname} {person.nachname} — Verfügbarkeiten</h2>
<form method="post" action="/admin/verfuegbarkeiten/{person_id}/update">
<table class="table table-sm"><thead><tr><th>Stunde</th>{''.join([f'<th>{w.value}</th>' for w in wochentage])}</tr></thead><tbody>{table_rows}</tbody></table>
<button type="submit" class="btn btn-primary">Speichern</button> <a href="/admin/verfuegbarkeiten" class="btn btn-secondary">Zurück</a>
</form>
</div></div></body></html>"""


@router.post("/verfuegbarkeiten/{person_id}/update")
async def verfuegbarkeiten_update(person_id: int, request: Request, db: Session = Depends(get_db)):
    if not is_logged_in(request):
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)

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
    if not is_logged_in(request):
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)
    abwesenheiten = db.query(Abwesenheit).order_by(Abwesenheit.von.desc()).all()
    rows = "".join([
        f"<tr><td>{escape_html(a.person.vorname)} {escape_html(a.person.nachname)}</td><td>{a.von}</td><td>{a.bis}</td><td>{escape_html(a.art.value)}</td><td>{escape_html(a.bemerkung or '-')}</td><td><a href='/admin/abwesenheiten/{a.id}/edit' class='btn btn-sm btn-warning'>Edit</a> <a href='/admin/abwesenheiten/{a.id}/delete' class='btn btn-sm btn-danger' onclick=\"return confirm('Delete?')\">Delete</a></td></tr>"
        for a in abwesenheiten
    ])
    return f"""<html><head><title>Abwesenheiten</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<style>body{{background:#f5f7fa}}.sidebar{{background:#2c3e50;color:white;padding:20px}}.sidebar a{{color:white;display:block;padding:10px;text-decoration:none}}</style>
</head><body><div class="row g-0"><div class="col-md-3 sidebar">
<h4>AusschussPlaner</h4><a href="/admin">Dashboard</a><a href="/admin/personen">Personen</a><a href="/admin/ausschuesse">Ausschuesse</a><a href="/admin/abwesenheiten">Abwesenheiten</a><a href="/admin/verfuegbarkeiten">Verfügbarkeiten</a><a href="/admin/jahrespläne">Jahrespläne</a><a href="/admin/sitzungsregeln">Sitzungsregeln</a><a href="/admin/logout">Logout</a>
</div><div class="col-md-9 p-4">
<div class="d-flex justify-content-between mb-4"><h1>Abwesenheiten ({len(abwesenheiten)})</h1><a href="/admin/abwesenheiten/new" class="btn btn-primary">New</a></div>
<table class="table"><thead><tr><th>Person</th><th>Von</th><th>Bis</th><th>Art</th><th>Bemerkung</th><th>Actions</th></tr></thead><tbody>{rows}</tbody></table>
</div></div></body></html>"""


@router.get("/abwesenheiten/new", response_class=HTMLResponse)
async def abwesenheiten_new(request: Request, db: Session = Depends(get_db)):
    if not is_logged_in(request):
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)
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
    if not is_logged_in(request):
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)
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
    if not is_logged_in(request):
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)
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
    if not is_logged_in(request):
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)
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
    if not is_logged_in(request):
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)
    abwesenheit = db.query(Abwesenheit).filter(Abwesenheit.id == abwesenheit_id).first()
    if abwesenheit:
        db.delete(abwesenheit)
        db.commit()
    return RedirectResponse(url="/admin/abwesenheiten", status_code=status.HTTP_302_FOUND)


@router.get("/sitzungsregeln", response_class=HTMLResponse)
async def sitzungsregeln_edit(request: Request, db: Session = Depends(get_db)):
    if not is_logged_in(request):
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)
    regel = db.query(Sitzungsregel).filter(Sitzungsregel.id == 1).first()
    if not regel:
        regel = Sitzungsregel(id=1)
        db.add(regel)
        db.commit()
    return f"""<html><head><title>Sitzungsregeln</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<style>body{{background:#f5f7fa}}.sidebar{{background:#2c3e50;color:white;padding:20px;min-height:100vh}}.sidebar a{{color:white;display:block;padding:10px;text-decoration:none}}</style>
</head><body><div class="row g-0"><div class="col-md-3 sidebar">
<h4>AusschussPlaner</h4><a href="/admin">Dashboard</a><a href="/admin/personen">Personen</a><a href="/admin/ausschuesse">Ausschuesse</a><a href="/admin/abwesenheiten">Abwesenheiten</a><a href="/admin/verfuegbarkeiten">Verfügbarkeiten</a><a href="/admin/jahrespläne">Jahrespläne</a><a href="/admin/sitzungsregeln">Sitzungsregeln</a><a href="/admin/logout">Logout</a>
</div><div class="col-md-9 p-4">
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
</div></div></body></html>"""


@router.post("/sitzungsregeln/update")
async def sitzungsregeln_update(request: Request, db: Session = Depends(get_db)):
    if not is_logged_in(request):
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)
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
    if not is_logged_in(request):
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)

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
    return f"""<html><head><title>Jahrespläne</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<style>body{{background:#f5f7fa}}.sidebar{{background:#2c3e50;color:white;padding:20px;min-height:100vh}}.sidebar a{{color:white;display:block;padding:10px;text-decoration:none}}</style>
</head><body><div class="row g-0"><div class="col-md-3 sidebar">
<h4>AusschussPlaner</h4><a href="/admin">Dashboard</a><a href="/admin/personen">Personen</a><a href="/admin/ausschuesse">Ausschuesse</a><a href="/admin/abwesenheiten">Abwesenheiten</a><a href="/admin/verfuegbarkeiten">Verfügbarkeiten</a><a href="/admin/jahrespläne">Jahrespläne</a><a href="/admin/sitzungsregeln">Sitzungsregeln</a><a href="/admin/logout">Logout</a>
</div><div class="col-md-9 p-4">
<div class="d-flex justify-content-between mb-4"><h1>Jahrespläne ({len(jahrespläne)})</h1><a href="/admin/jahrespläne/new" class="btn btn-primary">New</a></div>
{filter_buttons}
<table class="table"><thead><tr><th>Jahr</th><th>Bezeichnung</th><th>Status</th><th>Actions</th></tr></thead><tbody>{rows}</tbody></table>
</div></div></body></html>"""


@router.get("/jahrespläne/new", response_class=HTMLResponse)
async def jahrespläne_new(request: Request):
    if not is_logged_in(request):
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)
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
    if not is_logged_in(request):
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)
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
    if not is_logged_in(request):
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)
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
    if not is_logged_in(request):
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)
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
    if not is_logged_in(request):
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)
    jahresplan = db.query(Jahresplan).filter(Jahresplan.id == jahresplan_id).first()
    if jahresplan:
        db.delete(jahresplan)
        db.commit()
    return RedirectResponse(url="/admin/jahrespläne", status_code=status.HTTP_302_FOUND)


@router.get("/perioden", response_class=HTMLResponse)
async def perioden_list(request: Request, db: Session = Depends(get_db)):
    """List all periods with person/committee counts."""
    if not is_logged_in(request):
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)

    filter_param = request.query_params.get("filter", "all")

    query = db.query(Gemeinderatsperiode)
    if filter_param == "active":
        query = query.filter(Gemeinderatsperiode.aktiv == True)
    elif filter_param == "inactive":
        query = query.filter(Gemeinderatsperiode.aktiv == False)

    perioden = query.order_by(Gemeinderatsperiode.start_jahr.desc()).all()

    # Count personen and committees for each periode
    periode_persons_count = {}
    periode_committees_count = {}
    for periode in perioden:
        person_count = db.query(PeriodePerson).filter(
            PeriodePerson.periode_id == periode.id,
            PeriodePerson.end_datum.is_(None)
        ).count()
        committee_count = db.query(Ausschuss).filter(Ausschuss.periode_id == periode.id).count()
        periode_persons_count[periode.id] = person_count
        periode_committees_count[periode.id] = committee_count

    return templates.TemplateResponse("perioden.html", {
        "request": request,
        "page": "perioden",
        "perioden": perioden,
        "periode_persons_count": periode_persons_count,
        "periode_committees_count": periode_committees_count,
        "filter_param": filter_param,
    })


@router.get("/perioden/create", response_class=HTMLResponse)
async def perioden_create_form(request: Request):
    """Form to create a new period."""
    if not is_logged_in(request):
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)

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
    if not is_logged_in(request):
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)

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
    if not is_logged_in(request):
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)

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
    if not is_logged_in(request):
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)

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
    if not is_logged_in(request):
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)

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
    if not is_logged_in(request):
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)

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
    if not is_logged_in(request):
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)

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
    if not is_logged_in(request):
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)

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
    if not is_logged_in(request):
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)

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
    if not is_logged_in(request):
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)

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
    if not is_logged_in(request):
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)

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
