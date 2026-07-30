"""Tests für Änderungsprotokoll (Audit-Log)."""
from __future__ import annotations

from app.models.enums import AusschussTyp, TerminStatus, Wochentag
from app.models.models import Ausschuss, AuditLog, Sitzungsvorschlag


def test_audit_termin_fixieren_und_liste(client, db_session):
    a = Ausschuss(name="Bildung", typ=AusschussTyp.STANDARD, aktiv=True)
    db_session.add(a)
    db_session.commit()

    r = client.post("/api/calculate/results", json={
        "ausschuss_id": a.id,
        "ausschuss_name": "Bildung",
        "woche": 1,
        "wochentag": "MO",
        "start_minute": 16 * 60,
        "end_minute": 17 * 60 + 30,
    })
    assert r.status_code == 201
    vid = r.json()["id"]

    logs = client.get("/api/audit", params={"action": "termin."}).json()
    assert any(x["action"] == "termin.fixieren" and x["entity_id"] == vid for x in logs)
    assert any("Bildung" in (x["detail"] or "") for x in logs)

    assert client.delete(f"/api/calculate/results/{vid}").status_code == 204
    logs2 = client.get("/api/audit", params={"action": "termin.loeschen"}).json()
    assert len(logs2) >= 1


def test_audit_person_anlegen(client):
    r = client.post("/api/persons", json={"vorname": "Anna", "nachname": "Audit"})
    assert r.status_code == 201
    pid = r.json()["id"]

    logs = client.get("/api/audit", params={"entity_type": "person", "entity_id": pid}).json()
    assert len(logs) >= 1
    assert logs[0]["action"] == "person.anlegen"
    assert "Anna" in logs[0]["detail"]


def test_audit_ohne_token_401(anon_client):
    assert anon_client.get("/api/audit").status_code == 401


def test_write_audit_persistiert(db_session, client):
    """Direkter DB-Check nach API-Aktion."""
    a = Ausschuss(name="Sport", typ=AusschussTyp.STANDARD, aktiv=True)
    db_session.add(a)
    db_session.commit()
    v = Sitzungsvorschlag(
        ausschuss_id=a.id, woche=1, wochentag=Wochentag.DI,
        start_minute=19 * 60, end_minute=20 * 60 + 30,
        anwesend_count=0, mitglieder_count=0, quote=0,
        obmann_da=False, stv_da=False, status=TerminStatus.TOP,
    )
    db_session.add(v)
    db_session.commit()

    r = client.post(f"/api/calculate/results/{v.id}/absagen", json={"notiz": "fällt aus"})
    assert r.status_code == 200
    entry = (
        db_session.query(AuditLog)
        .filter(AuditLog.action == "termin.absagen", AuditLog.entity_id == v.id)
        .first()
    )
    assert entry is not None
    assert "fällt aus" in entry.detail
