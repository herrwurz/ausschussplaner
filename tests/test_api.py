"""Integrationstests der API-Endpunkte."""
from __future__ import annotations


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_create_and_list_person(client):
    r = client.post("/api/persons", json={"vorname": "Max", "nachname": "Muster"})
    assert r.status_code == 201
    pid = r.json()["id"]
    assert r.json()["name"] == "Max Muster"

    r2 = client.get("/api/persons")
    assert r2.status_code == 200
    assert any(p["id"] == pid for p in r2.json())


def test_set_verfuegbarkeit(client):
    pid = client.post("/api/persons", json={"vorname": "A", "nachname": "B"}).json()["id"]
    r = client.put(
        f"/api/persons/{pid}/verfuegbarkeit",
        json={"items": [
            {"wochentag": "Mo", "stunde": 16, "verfuegbar": True},
            {"wochentag": "Mo", "stunde": 17, "verfuegbar": True},
        ]},
    )
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_create_committee_with_members(client):
    p1 = client.post("/api/persons", json={"vorname": "Ob", "nachname": "Mann"}).json()["id"]
    p2 = client.post("/api/persons", json={"vorname": "Mit", "nachname": "Glied"}).json()["id"]
    r = client.post("/api/committees", json={
        "name": "Testausschuss",
        "typ": "poly",
        "mitglieder": [
            {"person_id": p1, "rolle": "Obmann"},
            {"person_id": p2, "rolle": "Mitglied"},
        ],
    })
    assert r.status_code == 201
    assert len(r.json()["mitglieder"]) == 2


def test_calculation_flow(client):
    # 3 Personen, alle Di 16-17 verfügbar
    ids = []
    for i, rolle in enumerate(["Obmann", "Mitglied", "Mitglied"]):
        pid = client.post("/api/persons", json={"vorname": f"P{i}", "nachname": "X"}).json()["id"]
        client.put(f"/api/persons/{pid}/verfuegbarkeit", json={"items": [
            {"wochentag": "Di", "stunde": 16, "verfuegbar": True},
            {"wochentag": "Di", "stunde": 17, "verfuegbar": True},
        ]})
        ids.append((pid, rolle))

    client.post("/api/committees", json={
        "name": "Calc", "typ": "poly",
        "mitglieder": [{"person_id": p, "rolle": r} for p, r in ids],
    })

    r = client.post("/api/calculate", json={
        "planungswochen": 1, "freitag_modus": "nein", "max_alternativen": 5,
    })
    assert r.status_code == 200
    data = r.json()
    assert data["zusammenfassung"]["ausschuesse"] == 1
    # Es muss mindestens einen Top-Termin am Dienstag geben
    analyse = data["analysen"][0]
    assert len(analyse["top_termine"]) > 0


def test_rules_get_and_update(client):
    r = client.get("/api/rules")
    assert r.status_code == 200
    assert r.json()["block_minuten"] == 90

    r2 = client.put("/api/rules", json={
        "block_minuten": 120, "sitzung_minuten": 100, "pause_minuten": 20,
        "council_minuten": 240, "quorum_standard": 5, "quorum_poly": 3,
        "quorum_kontroll": 4, "planungswochen": 3, "freitag_modus": "normal",
    })
    assert r2.status_code == 200
    assert r2.json()["block_minuten"] == 120


def test_deactivate_activate_person(client):
    pid = client.post("/api/persons", json={"vorname": "Alt", "nachname": "Mandat"}).json()["id"]
    r = client.post(f"/api/persons/{pid}/deactivate")
    assert r.status_code == 200
    assert r.json()["aktiv"] is False
    r2 = client.post(f"/api/persons/{pid}/activate")
    assert r2.json()["aktiv"] is True


def test_transfer_agenda(client):
    # Quelle mit 2 Mitgliedschaften, Ziel ohne
    quelle = client.post("/api/persons", json={"vorname": "Aus", "nachname": "Scheidend"}).json()["id"]
    ziel = client.post("/api/persons", json={"vorname": "Neu", "nachname": "Mandat"}).json()["id"]

    a1 = client.post("/api/committees", json={
        "name": "A1", "typ": "poly",
        "mitglieder": [{"person_id": quelle, "rolle": "Obmann"}]}).json()["id"]
    client.post("/api/committees", json={
        "name": "A2", "typ": "poly",
        "mitglieder": [{"person_id": quelle, "rolle": "Mitglied"}]})

    r = client.post("/api/persons/transfer-agenda", json={
        "von_person_id": quelle, "zu_person_id": ziel,
        "quelle_deaktivieren": True, "verfuegbarkeit_uebernehmen": False})
    assert r.status_code == 200
    data = r.json()
    assert data["uebertragene_mitgliedschaften"] == 2
    assert data["quelle_deaktiviert"] is True

    # Quelle ist jetzt inaktiv
    assert client.get(f"/api/persons/{quelle}").json()["aktiv"] is False
    # Ziel hat nun die Obmann-Rolle in A1 (Rolle erhalten)
    a1_data = client.get(f"/api/committees/{a1}").json()
    assert any(m["person_id"] == ziel and m["rolle"] == "Obmann" for m in a1_data["mitglieder"])


def test_transfer_agenda_skips_duplicates(client):
    quelle = client.post("/api/persons", json={"vorname": "Q", "nachname": "X"}).json()["id"]
    ziel = client.post("/api/persons", json={"vorname": "Z", "nachname": "Y"}).json()["id"]
    # Beide im selben Ausschuss
    client.post("/api/committees", json={
        "name": "Gemeinsam", "typ": "poly",
        "mitglieder": [
            {"person_id": quelle, "rolle": "Mitglied"},
            {"person_id": ziel, "rolle": "Obmann"}]})
    r = client.post("/api/persons/transfer-agenda", json={
        "von_person_id": quelle, "zu_person_id": ziel}).json()
    assert r["uebertragene_mitgliedschaften"] == 0
    assert r["uebersprungen"] == 1
