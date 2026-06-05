"""Integrationstests für die Web-Admin-UI."""
from __future__ import annotations


def test_login_page_loads(client):
    """Test: Login-Seite ist erreichbar."""
    r = client.get("/admin/login")
    assert r.status_code == 200
    assert "AusschussPlaner" in r.text
    assert "Password" in r.text


def test_login_with_correct_password(client):
    """Test: Login mit korrektem Passwort setzt Cookie."""
    r = client.post("/admin/login", data={"password": "admin123"}, follow_redirects=False)
    assert r.status_code == 302
    assert r.headers["location"] == "/admin"
    assert "admin_session" in r.cookies


def test_login_with_wrong_password(client):
    """Test: Login mit falschem Passwort zeigt Error-Page."""
    r = client.post("/admin/login", data={"password": "wrong"})
    assert r.status_code == 200
    assert "Falsches Passwort" in r.text


def test_dashboard_requires_auth(client):
    """Test: Dashboard ohne Auth-Cookie → Redirect zu Login."""
    r = client.get("/admin", follow_redirects=False)
    assert r.status_code == 302
    assert "/admin/login" in r.headers["location"]


def test_dashboard_with_auth(client):
    """Test: Dashboard mit Auth-Cookie zeigt Inhalt."""
    client.post("/admin/login", data={"password": "admin123"})
    r = client.get("/admin")
    assert r.status_code == 200
    assert "Dashboard" in r.text
    assert "Personen" in r.text


def test_personen_list_shows_data(client, db_session):
    """Test: Personen-Liste zeigt alle Personen."""
    client.post("/admin/login", data={"password": "admin123"})
    r = client.get("/admin/personen")
    assert r.status_code == 200
    # Mit Seed-Daten sollten mindestens Personen da sein
    assert "Personen" in r.text
    assert "<table" in r.text


def test_personen_create_form(client):
    """Test: Neue-Person-Form ist erreichbar."""
    client.post("/admin/login", data={"password": "admin123"})
    r = client.get("/admin/personen/new")
    assert r.status_code == 200
    assert "Vorname" in r.text
    assert "Nachname" in r.text


def test_personen_create_post(client):
    """Test: Neue Person erstellen via POST."""
    client.post("/admin/login", data={"password": "admin123"})
    r = client.post("/admin/personen/create", data={
        "vorname": "Test",
        "nachname": "Person",
        "gremium": "Testgremium",
        "email": "test@example.com",
        "aktiv": "on"
    }, follow_redirects=False)
    assert r.status_code == 302
    assert "/admin/personen" in r.headers["location"]


def test_ausschuesse_list(client):
    """Test: Ausschuesse-Liste laden."""
    client.post("/admin/login", data={"password": "admin123"})
    r = client.get("/admin/ausschuesse")
    assert r.status_code == 200
    assert "Ausschuesse" in r.text


def test_abwesenheiten_list(client):
    """Test: Abwesenheiten-Liste laden."""
    client.post("/admin/login", data={"password": "admin123"})
    r = client.get("/admin/abwesenheiten")
    assert r.status_code == 200
    assert "Abwesenheiten" in r.text


def test_verfuegbarkeiten_list(client):
    """Test: Verfügbarkeiten-Seite laden."""
    client.post("/admin/login", data={"password": "admin123"})
    r = client.get("/admin/verfuegbarkeiten")
    assert r.status_code == 200
    assert "Verfügbarkeiten" in r.text


def test_jahrespläne_list(client):
    """Test: Jahrespläne-Liste laden."""
    client.post("/admin/login", data={"password": "admin123"})
    r = client.get("/admin/jahrespläne")
    assert r.status_code == 200
    assert "Jahrespläne" in r.text


def test_sitzungsregeln_edit(client):
    """Test: Sitzungsregeln-Seite laden."""
    client.post("/admin/login", data={"password": "admin123"})
    r = client.get("/admin/sitzungsregeln")
    assert r.status_code == 200
    assert "Sitzungsregeln" in r.text
    assert "block_minuten" in r.text.lower() or "block" in r.text.lower()


def test_logout(client):
    """Test: Logout löscht Cookie."""
    client.post("/admin/login", data={"password": "admin123"})
    r = client.get("/admin/logout", follow_redirects=False)
    assert r.status_code == 302
    assert "/admin/login" in r.headers["location"]
    # Cookie sollte gelöscht sein
    assert r.cookies.get("admin_session") is None or r.cookies["admin_session"].value == ""
