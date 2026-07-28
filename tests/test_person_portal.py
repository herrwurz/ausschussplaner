"""Tests für Person Portal - Login und Selbstverwaltung."""
from __future__ import annotations

import pytest
from app.core.security import hash_password

# Check if fastapi-mail is available
try:
    import fastapi_mail
    HAS_FASTAPI_MAIL = True
except ImportError:
    HAS_FASTAPI_MAIL = False


@pytest.fixture
def person_with_password(db_session):
    """Erstelle eine Person mit Passwort für Tests."""
    from app.models.models import Person
    person = Person(
        vorname="Test",
        nachname="Person",
        email="testperson@example.com",
        password_hash=hash_password("testpass123"),
        aktiv=True,
    )
    db_session.add(person)
    db_session.commit()
    db_session.refresh(person)
    return person


def test_person_login_success(client, person_with_password):
    """Test: Erfolgreicher Login mit Email + Passwort."""
    r = client.post("/api/person/login?email=testperson@example.com&password=testpass123")
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["person_id"] == person_with_password.id


def test_person_login_invalid_password(client, person_with_password):
    """Test: Login mit falschem Passwort schlägt fehl."""
    r = client.post("/api/person/login?email=testperson@example.com&password=wrongpass")
    assert r.status_code == 401


def test_person_login_nonexistent_email(client):
    """Test: Login mit nicht-existierender Email schlägt fehl."""
    r = client.post("/api/person/login?email=nonexistent@example.com&password=anypass")
    assert r.status_code == 401


def test_get_person_me(client, person_with_password):
    """Test: GET /api/person/me gibt aktuelle Person zurück."""
    # Login zuerst
    login_r = client.post("/api/person/login?email=testperson@example.com&password=testpass123")
    token = login_r.json()["access_token"]

    # Hole Profildaten
    r = client.get(
        "/api/person/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 200
    data = r.json()
    assert data["vorname"] == "Test"
    assert data["nachname"] == "Person"
    assert data["email"] == "testperson@example.com"


def test_update_person_me(client, person_with_password):
    """Test: PUT /api/person/me aktualisiert Profil."""
    login_r = client.post("/api/person/login?email=testperson@example.com&password=testpass123")
    token = login_r.json()["access_token"]

    r = client.put(
        "/api/person/me",
        json={"vorname": "Updated", "gremium": "Gemeinderat"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 200
    assert r.json()["vorname"] == "Updated"
    assert r.json()["gremium"] == "Gemeinderat"


def test_change_password(client, person_with_password):
    """Test: PUT /api/person/me/password ändert Passwort."""
    login_r = client.post("/api/person/login?email=testperson@example.com&password=testpass123")
    token = login_r.json()["access_token"]

    # Ändere Passwort (Query-Params)
    r = client.put(
        "/api/person/me/password?old_password=testpass123&new_password=newpass456",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 200

    # Versuche mit altem Passwort zu loggen (sollte fehlschlagen)
    r2 = client.post("/api/person/login?email=testperson@example.com&password=testpass123")
    assert r2.status_code == 401

    # Versuche mit neuem Passwort zu loggen (sollte funktionieren)
    r3 = client.post("/api/person/login?email=testperson@example.com&password=newpass456")
    assert r3.status_code == 200


def test_set_verfuegbarkeiten(client, person_with_password):
    """Test: PUT /api/person/me/verfuegbarkeiten speichert Verfügbarkeiten."""
    login_r = client.post("/api/person/login?email=testperson@example.com&password=testpass123")
    token = login_r.json()["access_token"]

    r = client.put(
        "/api/person/me/verfuegbarkeiten",
        json={
            "items": [
                {"wochentag": "Mo", "stunde": 16, "verfuegbar": True},
                {"wochentag": "Mo", "stunde": 17, "verfuegbar": True},
                {"wochentag": "Di", "stunde": 18, "verfuegbar": True},
            ]
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 200
    assert len(r.json()) == 3


def test_get_verfuegbarkeiten(client, person_with_password):
    """Test: GET /api/person/me/verfuegbarkeiten gibt Verfügbarkeiten zurück."""
    login_r = client.post("/api/person/login?email=testperson@example.com&password=testpass123")
    token = login_r.json()["access_token"]

    # Setze zuerst Verfügbarkeiten
    client.put(
        "/api/person/me/verfuegbarkeiten",
        json={
            "items": [
                {"wochentag": "Mo", "stunde": 16, "verfuegbar": True},
            ]
        },
        headers={"Authorization": f"Bearer {token}"}
    )

    # Hole Verfügbarkeiten
    r = client.get(
        "/api/person/me/verfuegbarkeiten",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 200
    assert len(r.json()) >= 1


def test_create_absence(client, person_with_password):
    """Test: POST /api/person/me/absences erstellt Abwesenheit."""
    login_r = client.post("/api/person/login?email=testperson@example.com&password=testpass123")
    token = login_r.json()["access_token"]

    r = client.post(
        "/api/person/me/absences",
        json={
            "person_id": person_with_password.id,
            "von": "2025-08-01",
            "bis": "2025-08-10",
            "art": "Urlaub",
            "bemerkung": "Sommerurlaub",
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 200
    data = r.json()
    assert data["von"] == "2025-08-01"
    assert data["bis"] == "2025-08-10"


def test_get_my_committees(client, person_with_password, db_session):
    """Test: GET /api/person/me/committees gibt meine Ausschüsse."""
    from app.models.models import Ausschuss, Mitgliedschaft
    from app.models.enums import Rolle

    # Erstelle Ausschuss und Mitgliedschaft
    ausschuss = Ausschuss(name="Testausschuss")
    db_session.add(ausschuss)
    db_session.flush()

    mitgliedschaft = Mitgliedschaft(
        person_id=person_with_password.id,
        ausschuss_id=ausschuss.id,
        rolle=Rolle.MITGLIED
    )
    db_session.add(mitgliedschaft)
    db_session.commit()

    login_r = client.post("/api/person/login?email=testperson@example.com&password=testpass123")
    token = login_r.json()["access_token"]

    r = client.get(
        "/api/person/me/committees",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 200
    committees = r.json()
    assert len(committees) >= 1
    assert any(c["ausschuss_name"] == "Testausschuss" for c in committees)


def test_get_dashboard(client, person_with_password):
    """Test: GET /api/person/me/dashboard gibt Dashboard Stats."""
    login_r = client.post("/api/person/login?email=testperson@example.com&password=testpass123")
    token = login_r.json()["access_token"]

    r = client.get(
        "/api/person/me/dashboard",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 200
    data = r.json()
    assert "name" in data
    assert "email" in data
    assert "verfugbar_stunden" in data
    assert "ausschuesse" in data


def test_update_partei(client, person_with_password):
    """Test: Partei-Update im Profil funktioniert."""
    login_r = client.post("/api/person/login?email=testperson@example.com&password=testpass123")
    token = login_r.json()["access_token"]

    r = client.put(
        "/api/person/me",
        json={"partei": "SPÖ"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 200
    assert r.json()["partei"] == "SPÖ"

    # Verifiziere Update persisted
    r2 = client.get(
        "/api/person/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert r2.json()["partei"] == "SPÖ"


@pytest.mark.skipif(not HAS_FASTAPI_MAIL, reason="fastapi-mail not installed")
def test_send_invitation(client, db_session):
    """Test: Admin sendet Einladung und generiert Token."""
    from app.models.models import Person

    # Erstelle Person ohne Passwort
    person = Person(
        vorname="Eingeladen",
        nachname="Person",
        email="invited@example.com",
        aktiv=True,
    )
    db_session.add(person)
    db_session.commit()
    db_session.refresh(person)

    # Sende Einladung
    r = client.post(f"/api/persons/{person.id}/send-invitation")
    assert r.status_code == 200
    assert "message" in r.json()

    # Verifiziere Token wurde gesetzt
    db_session.refresh(person)
    assert person.invite_token is not None
    assert person.invite_expires is not None


@pytest.mark.skipif(not HAS_FASTAPI_MAIL, reason="fastapi-mail not installed")
def test_set_password_with_token(client, db_session):
    """Test: Person setzt Passwort mit Einladungs-Token."""
    from app.models.models import Person
    from app.services.email_service import generate_invite_token

    # Erstelle Person mit Token
    token, expires = generate_invite_token()
    person = Person(
        vorname="Eingeladen",
        nachname="Person",
        email="invited2@example.com",
        invite_token=token,
        invite_expires=expires,
        aktiv=True,
    )
    db_session.add(person)
    db_session.commit()

    # Setze Passwort
    r = client.post(f"/api/person/set-password?token={token}&new_password=NewPass123")
    assert r.status_code == 200
    assert "successfully" in r.json()["message"]

    # Verifiziere Token wurde gelöscht
    db_session.refresh(person)
    assert person.invite_token is None
    assert person.invite_expires is None
    assert person.password_hash is not None

    # Verifiziere Login mit neuem Passwort funktioniert
    r2 = client.post("/api/person/login?email=invited2@example.com&password=NewPass123")
    assert r2.status_code == 200
    assert "access_token" in r2.json()


def test_set_password_invalid_token(client):
    """Test: Set-Password mit ungültigem Token schlägt fehl."""
    r = client.post("/api/person/set-password?token=invalid_token&new_password=SomePass123")
    assert r.status_code == 404


@pytest.mark.skipif(not HAS_FASTAPI_MAIL, reason="fastapi-mail not installed")
def test_set_password_expired_token(client, db_session):
    """Test: Set-Password mit abgelaufenem Token schlägt fehl."""
    from app.models.models import Person
    from datetime import datetime, timedelta

    person = Person(
        vorname="Test",
        nachname="Expired",
        email="expired@example.com",
        invite_token="expired_token",
        invite_expires=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=1),  # vor 1 Stunde abgelaufen
        aktiv=True,
    )
    db_session.add(person)
    db_session.commit()

    r = client.post("/api/person/set-password?token=expired_token&new_password=NewPass123")
    assert r.status_code == 410  # Gone


def test_get_my_absences(client, person_with_password):
    """Test: GET /api/person/me/absences gibt Abwesenheiten zurück."""
    login_r = client.post("/api/person/login?email=testperson@example.com&password=testpass123")
    token = login_r.json()["access_token"]

    # Hole Abwesenheiten (sollte leer sein)
    r = client.get(
        "/api/person/me/absences",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 200
    initial_count = len(r.json())

    # Erstelle Abwesenheit (JSON-Body)
    create_r = client.post(
        "/api/person/me/absences",
        json={
            "person_id": person_with_password.id,
            "von": "2025-06-01",
            "bis": "2025-06-05",
            "art": "Urlaub",
            "bemerkung": "Test",
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    assert create_r.status_code in [200, 201], f"Expected 200/201, got {create_r.status_code}: {create_r.text}"

    # Hole Abwesenheiten wieder (sollte jetzt mehr haben)
    r2 = client.get(
        "/api/person/me/absences",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert r2.status_code == 200
    assert len(r2.json()) > initial_count


def test_no_auth_returns_401(client):
    """Test: Zugriff ohne Token wird abgelehnt."""
    r = client.get("/api/person/me")
    assert r.status_code == 401
