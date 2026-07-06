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

def test_users_ohne_token_401(client):
    assert client.get("/api/users").status_code == 401
    assert client.post("/api/users", json={
        "email": "x@y.z", "vorname": "X", "nachname": "Y"}).status_code == 401
    assert client.delete("/api/users/1").status_code == 401
    assert client.post("/api/users/1/reset-password").status_code == 401


def test_users_als_benutzer_403(client, benutzer):
    headers = login(client, "benutzer@test.local", "benutzer123")
    assert client.get("/api/users", headers=headers).status_code == 403
    r = client.post("/api/users", headers=headers, json={
        "email": "neu@test.local", "vorname": "Neu", "nachname": "User"})
    assert r.status_code == 403


def test_users_als_super_admin_ok(client, super_admin):
    headers = login(client, "admin@test.local", "admin123")
    r = client.get("/api/users", headers=headers)
    assert r.status_code == 200
    assert len(r.json()) == 1

    r = client.post("/api/users", headers=headers, json={
        "email": "neu@test.local", "vorname": "Neu", "nachname": "User"})
    assert r.status_code == 200
    assert "temp_password" in r.json()


def test_user_update_obmann_ausschuesse(client, super_admin, obmann, ausschuesse):
    a1, _ = ausschuesse
    headers = login(client, "admin@test.local", "admin123")
    r = client.put(f"/api/users/{obmann.id}", headers=headers,
                   json={"obmann_ausschuss_ids": [a1.id]})
    assert r.status_code == 200
    assert r.json()["obmann_ausschuss_ids"] == [a1.id]


def test_deaktivierter_user_401(client, db_session, benutzer):
    headers = login(client, "benutzer@test.local", "benutzer123")
    benutzer.aktiv = False
    db_session.commit()
    assert client.get("/api/auth/me", headers=headers).status_code == 401


# ------------------------------------------------------------- /api/auth

def test_auth_me(client, benutzer):
    headers = login(client, "benutzer@test.local", "benutzer123")
    r = client.get("/api/auth/me", headers=headers)
    assert r.status_code == 200
    assert r.json()["email"] == "benutzer@test.local"

    assert client.get("/api/auth/me").status_code == 401


def test_register_nur_super_admin(client, super_admin, benutzer):
    params = {"email": "reg@test.local", "password": "pass123",
              "vorname": "Reg", "nachname": "Istriert"}

    assert client.post("/api/auth/register", params=params).status_code == 401

    headers = login(client, "benutzer@test.local", "benutzer123")
    assert client.post("/api/auth/register", params=params,
                       headers=headers).status_code == 403

    headers = login(client, "admin@test.local", "admin123")
    assert client.post("/api/auth/register", params=params,
                       headers=headers).status_code == 200


# ----------------------------------------------------------- /api/obmann

def test_obmann_dashboard_als_benutzer_403(client, benutzer):
    headers = login(client, "benutzer@test.local", "benutzer123")
    assert client.get("/api/obmann/ausschuesse", headers=headers).status_code == 403


def test_obmann_sieht_nur_eigene_ausschuesse(client, db_session, obmann, ausschuesse):
    a1, a2 = ausschuesse
    obmann.obmann_ausschuss_ids = json.dumps([a1.id])
    db_session.commit()

    headers = login(client, "obmann@test.local", "obmann123")
    r = client.get("/api/obmann/ausschuesse", headers=headers)
    assert r.status_code == 200
    ids = [a["id"] for a in r.json()]
    assert ids == [a1.id]


def test_obmann_ohne_zuweisung_sieht_nichts(client, obmann, ausschuesse):
    headers = login(client, "obmann@test.local", "obmann123")
    r = client.get("/api/obmann/ausschuesse", headers=headers)
    assert r.status_code == 200
    assert r.json() == []


def test_obmann_calculate_fremder_ausschuss_403(client, db_session, obmann, ausschuesse):
    a1, a2 = ausschuesse
    obmann.obmann_ausschuss_ids = json.dumps([a1.id])
    db_session.commit()

    headers = login(client, "obmann@test.local", "obmann123")
    r = client.post(f"/api/obmann/calculate/{a2.id}", headers=headers)
    assert r.status_code == 403


def test_super_admin_sieht_alle_ausschuesse(client, super_admin, ausschuesse):
    headers = login(client, "admin@test.local", "admin123")
    r = client.get("/api/obmann/ausschuesse", headers=headers)
    assert r.status_code == 200
    assert len(r.json()) == 2
