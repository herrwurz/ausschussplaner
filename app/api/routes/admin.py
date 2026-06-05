"""Admin Web-UI Routes."""
from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from html import escape
from urllib.parse import urlparse
import os

from app.db.base import get_db
from app.models.models import Person, Ausschuss, Jahresplan, Abwesenheit, Mitgliedschaft, Sitzungsregel, Verfuegbarkeit
from app.models.enums import AbwesenheitsArt, Rolle, Wochentag

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
<h4>AusschussPlaner</h4><a href="/admin">Dashboard</a><a href="/admin/personen">Personen</a><a href="/admin/ausschuesse">Ausschuesse</a><a href="/admin/abwesenheiten">Abwesenheiten</a><a href="/admin/verfuegbarkeiten">Verfügbarkeiten</a><a href="/admin/jahrespläne">Jahrespläne</a><a href="/admin/sitzungsregeln">Sitzungsregeln</a><a href="/admin/logout">Logout</a>
</div><div class="col-md-9 p-4">
<h1>Dashboard</h1>
<div class="row"><div class="col-md-6"><div class="card"><div class="card-body"><h5 class="card-title">Stammdaten</h5><ul class="list-unstyled"><li><a href="/admin/personen">Personen verwalten</a></li><li><a href="/admin/ausschuesse">Ausschuesse verwalten</a></li><li><a href="/admin/abwesenheiten">Abwesenheiten verwalten</a></li></ul></div></div></div><div class="col-md-6"><div class="card"><div class="card-body"><h5 class="card-title">Planung</h5><ul class="list-unstyled"><li><a href="/admin/jahrespläne">Jahrespläne</a></li><li><a href="/admin/sitzungsregeln">Sitzungsregeln</a></li></ul></div></div></div></div>
</div></div></body></html>"""


@router.get("/personen", response_class=HTMLResponse)
async def personen_list(request: Request, db: Session = Depends(get_db)):
    if not is_logged_in(request):
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)

    persons = db.query(Person).all()
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
    ausschuesse = db.query(Ausschuss).all()
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
    jahrespläne = db.query(Jahresplan).order_by(Jahresplan.jahr.desc()).all()
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
