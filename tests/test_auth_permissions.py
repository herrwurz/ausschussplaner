"""Tests für Auth-Absicherung: Benutzerverwaltung + Obmann-Dashboard."""
from __future__ import annotations

import json

import pytest

from app.models.enums import AusschussTyp, BenutzerRolle
from app.models.models import Ausschuss
from app.services.auth_service import AuthService


@pytest.fixture
def super_admin(db_session):
    return AuthService.create_user(
        db_session, email="admin@test.local", password="admin123",
        vorname="Super", nachname="Admin", rolle=BenutzerRolle.SUPER_ADMIN,
    )


@pytest.fixture
def benutzer(db_session):
    return AuthService.create_user(
        db_session, email="benutzer@test.local", password="benutzer123",
        vorname="Normal", nachname="Benutzer", rolle=BenutzerRolle.BENUTZER,
    )


@pytest.fixture
def obmann(db_session):
    return AuthService.create_user(
        db_session, email="obmann@test.local", password="obmann123",
        vorname="Otto", nachname="Obmann", rolle=BenutzerRolle.OBMANN,
    )


@pytest.fixture
def ausschuesse(db_session):
    a1 = Ausschuss(name="Bildung", typ=AusschussTyp.STANDARD, aktiv=True)
    a2 = Ausschuss(name="Kontrolle", typ=AusschussTyp.STANDARD, aktiv=True)
    db_session.add_all([a1, a2])
    db_session.commit()
    return a1, a2


def login(client, email: str, password: str) -> dict:
    r = client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


# ---------------------------------------------------------------- /api/users

def test_users_ohne_token_401(anon_client):
    assert anon_client.get("/api/users").status_code == 401
    assert anon_client.post("/api/users", json={
        "email": "x@y.z", "vorname": "X", "nachname": "Y"}).status_code == 401
    assert anon_client.delete("/api/users/1").status_code == 401
    assert anon_client.post("/api/users/1/reset-password").status_code == 401


def test_admin_api_ohne_token_401(anon_client):
    assert anon_client.get("/api/persons").status_code == 401
    assert anon_client.post("/api/persons", json={"vorname": "A", "nachname": "B"}).status_code == 401
    assert anon_client.get("/api/committees").status_code == 401
    assert anon_client.get("/api/rules").status_code == 401
    assert anon_client.post("/api/calculate", json={}).status_code == 401


def test_users_als_benutzer_403(anon_client, benutzer):
    headers = login(anon_client, "benutzer@test.local", "benutzer123")
    assert anon_client.get("/api/users", headers=headers).status_code == 403
    r = anon_client.post("/api/users", headers=headers, json={
        "email": "neu@test.local", "vorname": "Neu", "nachname": "User"})
    assert r.status_code == 403


def test_users_als_super_admin_ok(anon_client, super_admin):
    headers = login(anon_client, "admin@test.local", "admin123")
    r = anon_client.get("/api/users", headers=headers)
    assert r.status_code == 200
    assert len(r.json()) == 1

    r = anon_client.post("/api/users", headers=headers, json={
        "email": "neu@test.local", "vorname": "Neu", "nachname": "User"})
    assert r.status_code == 200
    assert "temp_password" in r.json()


def test_user_update_obmann_ausschuesse(anon_client, super_admin, obmann, ausschuesse):
    a1, _ = ausschuesse
    headers = login(anon_client, "admin@test.local", "admin123")
    r = anon_client.put(f"/api/users/{obmann.id}", headers=headers,
                   json={"obmann_ausschuss_ids": [a1.id]})
    assert r.status_code == 200
    assert r.json()["obmann_ausschuss_ids"] == [a1.id]


def test_deaktivierter_user_401(anon_client, db_session, benutzer):
    headers = login(anon_client, "benutzer@test.local", "benutzer123")
    benutzer.aktiv = False
    db_session.commit()
    assert anon_client.get("/api/auth/me", headers=headers).status_code == 401


# ------------------------------------------------------------- /api/auth

def test_auth_me(anon_client, benutzer):
    headers = login(anon_client, "benutzer@test.local", "benutzer123")
    r = anon_client.get("/api/auth/me", headers=headers)
    assert r.status_code == 200
    assert r.json()["email"] == "benutzer@test.local"

    assert anon_client.get("/api/auth/me").status_code == 401


def test_register_nur_super_admin(anon_client, super_admin, benutzer):
    params = {"email": "reg@test.local", "password": "pass123",
              "vorname": "Reg", "nachname": "Istriert"}

    assert anon_client.post("/api/auth/register", params=params).status_code == 401

    headers = login(anon_client, "benutzer@test.local", "benutzer123")
    assert anon_client.post("/api/auth/register", params=params,
                       headers=headers).status_code == 403

    headers = login(anon_client, "admin@test.local", "admin123")
    assert anon_client.post("/api/auth/register", params=params,
                       headers=headers).status_code == 200


# ----------------------------------------------------------- /api/obmann

def test_obmann_dashboard_als_benutzer_403(anon_client, benutzer):
    headers = login(anon_client, "benutzer@test.local", "benutzer123")
    assert anon_client.get("/api/obmann/ausschuesse", headers=headers).status_code == 403


def test_obmann_sieht_nur_eigene_ausschuesse(anon_client, db_session, obmann, ausschuesse):
    a1, a2 = ausschuesse
    obmann.obmann_ausschuss_ids = json.dumps([a1.id])
    db_session.commit()

    headers = login(anon_client, "obmann@test.local", "obmann123")
    r = anon_client.get("/api/obmann/ausschuesse", headers=headers)
    assert r.status_code == 200
    ids = [a["id"] for a in r.json()]
    assert ids == [a1.id]


def test_obmann_ohne_zuweisung_sieht_nichts(anon_client, obmann, ausschuesse):
    headers = login(anon_client, "obmann@test.local", "obmann123")
    r = anon_client.get("/api/obmann/ausschuesse", headers=headers)
    assert r.status_code == 200
    assert r.json() == []


def test_obmann_calculate_fremder_ausschuss_403(anon_client, db_session, obmann, ausschuesse):
    a1, a2 = ausschuesse
    obmann.obmann_ausschuss_ids = json.dumps([a1.id])
    db_session.commit()

    headers = login(anon_client, "obmann@test.local", "obmann123")
    r = anon_client.post(f"/api/obmann/calculate/{a2.id}", headers=headers)
    assert r.status_code == 403


def test_obmann_admin_api_403(anon_client, obmann):
    """Obmann darf Admin-CRUD nicht nutzen."""
    headers = login(anon_client, "obmann@test.local", "obmann123")
    assert anon_client.get("/api/persons", headers=headers).status_code == 403
    assert anon_client.get("/api/committees", headers=headers).status_code == 403


def test_super_admin_sieht_alle_ausschuesse(anon_client, super_admin, ausschuesse):
    headers = login(anon_client, "admin@test.local", "admin123")
    r = anon_client.get("/api/obmann/ausschuesse", headers=headers)
    assert r.status_code == 200
    assert len(r.json()) == 2


# ------------------------------------------------------ Admin-Bootstrap

def test_ensure_admin_entfernt_demo_admin(db_session, monkeypatch):
    """Demo-Admin wird gelöscht, sobald ein richtiger Admin konfiguriert ist."""
    from app import main
    from app.models.models import User

    AuthService.create_user(
        db_session, email=main.DEMO_ADMIN_EMAIL, password="admin123",
        vorname="System", nachname="Administrator",
        rolle=BenutzerRolle.SUPER_ADMIN,
    )

    monkeypatch.setattr(main.settings, "admin_email", "echt@gemeinde.at")
    monkeypatch.setattr(main.settings, "admin_password", "sicheres-passwort")
    main.ensure_admin_user(db_session)

    assert db_session.query(User).filter(
        User.email == main.DEMO_ADMIN_EMAIL).first() is None
    neuer = db_session.query(User).filter(User.email == "echt@gemeinde.at").first()
    assert neuer is not None
    assert neuer.rolle == BenutzerRolle.SUPER_ADMIN


def test_ensure_admin_ohne_passwort_tut_nichts(db_session, monkeypatch):
    """Ohne ADMIN_PASSWORD bleibt alles unangetastet (lokale Dev-Umgebung)."""
    from app import main
    from app.models.models import User

    AuthService.create_user(
        db_session, email=main.DEMO_ADMIN_EMAIL, password="admin123",
        vorname="System", nachname="Administrator",
        rolle=BenutzerRolle.SUPER_ADMIN,
    )

    monkeypatch.setattr(main.settings, "admin_password", None)
    main.ensure_admin_user(db_session)

    assert db_session.query(User).filter(
        User.email == main.DEMO_ADMIN_EMAIL).first() is not None
