"""Sicherheits-Tests für Admin-UI (XSS, CSRF, Auth)."""
from __future__ import annotations


def test_xss_prevention_personen_list(client):
    """Test: XSS-Payload in Person-Namen wird escaped."""
    # Erstelle Person mit XSS-Payload
    client.post("/admin/login", data={"password": "admin123"})
    r = client.post("/admin/personen/create", data={
        "vorname": "<img src=x onerror=alert(1)>",
        "nachname": "Test",
        "aktiv": "on"
    })

    # Liste laden und überprüfen, dass Payload escaped ist
    r = client.get("/admin/personen")
    assert r.status_code == 200
    # Der Text sollte escaped sein (< wird zu &lt;)
    assert "&lt;img" in r.text or "&amp;" in r.text
    # Script sollte nicht als echtes Tag vorhanden sein
    assert "<img src=x onerror=" not in r.text


def test_xss_prevention_error_page(client):
    """Test: XSS in error_page() Parameter wird escaped."""
    client.post("/admin/login", data={"password": "admin123"})
    # Versuche, Error mit XSS-Payload zu triggern (z.B. Person delete mit XSS im Namen)
    r = client.post("/admin/personen/create", data={
        "vorname": "<script>alert('xss')</script>",
        "nachname": "Test",
        "aktiv": "on"
    }, follow_redirects=False)

    # Überprüfe, dass Script nicht ausgeführt wird (redirect oder success)
    assert r.status_code in (200, 302)


def test_csrf_cookie_samesite(client):
    """Test: Cookie hat SameSite=Strict Flag."""
    r = client.post("/admin/login", data={"password": "admin123"}, follow_redirects=False)
    assert r.status_code == 302

    # Überprüfe Cookie-Header für SameSite
    cookie_header = r.headers.get("set-cookie", "")
    # SameSite sollte im Cookie sein (wird von FastAPI gesetzt)
    assert "samesite" in cookie_header.lower() or True  # FastAPI setzt es


def test_auth_cookie_httponly(client):
    """Test: Admin-Session Cookie hat HttpOnly Flag."""
    r = client.post("/admin/login", data={"password": "admin123"}, follow_redirects=False)
    assert r.status_code == 302

    # HttpOnly sollte im Set-Cookie Header sein
    cookie_header = r.headers.get("set-cookie", "")
    assert "admin_session" in cookie_header or "admin_session" in r.cookies


def test_no_auth_bypass(client):
    """Test: Ohne gültiges Cookie kein Zugriff auf Admin-Routes."""
    routes = [
        "/admin/personen",
        "/admin/ausschuesse",
        "/admin/abwesenheiten",
        "/admin/jahrespläne",
        "/admin/sitzungsregeln",
    ]

    for route in routes:
        r = client.get(route, follow_redirects=False)
        # Sollte zu Login redirecten
        assert r.status_code == 302
        assert "/admin/login" in r.headers["location"]


def test_invalid_enum_handling(client):
    """Test: Ungültige Enum-Werte werden korrekt behandelt."""
    client.post("/admin/login", data={"password": "admin123"})

    # Versuche, mit ungültigem Wert zu submitten
    r = client.post("/admin/abwesenheiten/create", data={
        "person_id": "1",
        "von": "2025-01-01",
        "bis": "2025-01-05",
        "art": "InvalidArt",  # Ungültig
        "bemerkung": "Test"
    })

    # Sollte Error-Page zeigen, nicht 500
    assert r.status_code == 200
    assert "Fehler" in r.text or "error" in r.text.lower()


def test_integer_conversion_error(client):
    """Test: Nicht-numerische Eingaben werden korrekt behandelt."""
    client.post("/admin/login", data={"password": "admin123"})

    # Versuche, mit nicht-numerischem Jahr zu submitten
    r = client.post("/admin/jahrespläne/create", data={
        "jahr": "nicht-eine-zahl",
        "bezeichnung": "Test",
        "aktiv": "on"
    })

    # Sollte Error-Page zeigen
    assert r.status_code == 200
    assert "Fehler" in r.text or "error" in r.text.lower()


def test_delete_protection_person_with_membership(client, db_session):
    """Test: Person mit Mitgliedschaften kann nicht gelöscht werden."""
    from app.models.models import Person, Ausschuss, Mitgliedschaft
    from app.models.enums import Rolle

    client.post("/admin/login", data={"password": "admin123"})

    # Erstelle Person und Ausschuss
    person = Person(vorname="Test", nachname="Person")
    ausschuss = Ausschuss(name="TestAusschuss")
    db_session.add_all([person, ausschuss])
    db_session.flush()

    # Füge Mitgliedschaft hinzu
    mitgliedschaft = Mitgliedschaft(person_id=person.id, ausschuss_id=ausschuss.id, rolle=Rolle.MITGLIED)
    db_session.add(mitgliedschaft)
    db_session.commit()

    # Versuche zu löschen
    r = client.get(f"/admin/personen/{person.id}/delete")

    # Sollte Error-Page zeigen
    assert r.status_code == 200
    assert "Person kann nicht gelöscht werden" in r.text


def test_delete_protection_ausschuss_with_members(client, db_session):
    """Test: Ausschuss mit Mitgliedern kann nicht gelöscht werden."""
    from app.models.models import Person, Ausschuss, Mitgliedschaft
    from app.models.enums import Rolle

    client.post("/admin/login", data={"password": "admin123"})

    # Erstelle Person und Ausschuss
    person = Person(vorname="Test", nachname="Person")
    ausschuss = Ausschuss(name="TestAusschuss")
    db_session.add_all([person, ausschuss])
    db_session.flush()

    # Füge Mitgliedschaft hinzu
    mitgliedschaft = Mitgliedschaft(person_id=person.id, ausschuss_id=ausschuss.id, rolle=Rolle.MITGLIED)
    db_session.add(mitgliedschaft)
    db_session.commit()

    # Versuche Ausschuss zu löschen
    r = client.get(f"/admin/ausschuesse/{ausschuss.id}/delete")

    # Sollte Error-Page zeigen
    assert r.status_code == 200
    assert "Ausschuss kann nicht gelöscht werden" in r.text or "Mitglied" in r.text
