"""Tests: Termin verschieben (C1) und absagen (C2)."""
from __future__ import annotations

from app.models.enums import AusschussTyp, TerminStatus, Wochentag
from app.models.models import Ausschuss, Sitzungsvorschlag


def _fix(db_session, ausschuss_id: int, *, woche=1, tag=Wochentag.MO, start=16 * 60, end=17 * 60 + 30):
    v = Sitzungsvorschlag(
        ausschuss_id=ausschuss_id,
        woche=woche,
        wochentag=tag,
        start_minute=start,
        end_minute=end,
        anwesend_count=0,
        mitglieder_count=0,
        quote=0,
        obmann_da=False,
        stv_da=False,
        status=TerminStatus.TOP,
        fehlende="",
        abgesagt=False,
        notiz="",
    )
    db_session.add(v)
    db_session.commit()
    db_session.refresh(v)
    return v


def test_termin_verschieben_ok(client, db_session):
    a = Ausschuss(name="Bildung", typ=AusschussTyp.STANDARD, aktiv=True)
    db_session.add(a)
    db_session.commit()
    v = _fix(db_session, a.id)

    r = client.patch(f"/api/calculate/results/{v.id}", json={
        "woche": 2,
        "wochentag": "DI",
        "start_minute": 17 * 60,
        "end_minute": 18 * 60 + 30,
    })
    assert r.status_code == 200
    body = r.json()
    assert body["woche"] == 2
    assert body["wochentag"] == "Di"
    assert body["start_minute"] == 17 * 60


def test_termin_verschieben_konflikt_409(client, db_session):
    a1 = Ausschuss(name="A", typ=AusschussTyp.STANDARD, aktiv=True)
    a2 = Ausschuss(name="B", typ=AusschussTyp.STANDARD, aktiv=True)
    db_session.add_all([a1, a2])
    db_session.commit()
    v1 = _fix(db_session, a1.id, start=16 * 60, end=17 * 60 + 30)
    _fix(db_session, a2.id, start=16 * 60 + 30, end=18 * 60)  # überlappt

    r = client.patch(f"/api/calculate/results/{v1.id}", json={
        "woche": 1,
        "wochentag": "MO",
        "start_minute": 16 * 60,
        "end_minute": 17 * 60 + 30,
    })
    assert r.status_code == 409
    assert "Zeitkonflikt" in r.json()["detail"]


def test_termin_absagen_und_aus_liste(client, db_session):
    a = Ausschuss(name="Kontrolle", typ=AusschussTyp.STANDARD, aktiv=True)
    db_session.add(a)
    db_session.commit()
    v = _fix(db_session, a.id)

    r = client.post(f"/api/calculate/results/{v.id}/absagen", json={"notiz": "Quorum fehlt"})
    assert r.status_code == 200
    assert r.json()["abgesagt"] is True
    assert r.json()["notiz"] == "Quorum fehlt"

    assert client.get("/api/calculate/results").json() == []
    cancelled = client.get("/api/calculate/results", params={"include_cancelled": True}).json()
    assert len(cancelled) == 1
    assert cancelled[0]["abgesagt"] is True


def test_absage_blockiert_verschieben(client, db_session):
    a = Ausschuss(name="Sport", typ=AusschussTyp.STANDARD, aktiv=True)
    db_session.add(a)
    db_session.commit()
    v = _fix(db_session, a.id)
    client.post(f"/api/calculate/results/{v.id}/absagen", json={"notiz": "entfällt"})

    r = client.patch(f"/api/calculate/results/{v.id}", json={
        "woche": 3,
        "wochentag": "MI",
        "start_minute": 19 * 60,
        "end_minute": 20 * 60 + 30,
    })
    assert r.status_code == 400
