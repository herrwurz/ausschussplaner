# Analyse: Warum falsche Sitzungstermine ausgegeben werden

Stand: 2026-07-05 · Analysierte Dateien: `app/services/scheduler.py`, `app/services/calculation_service.py`, `app/api/routes/calculation.py`, `app/models/*`, `app/db/seed.py`, `tests/test_scheduler.py`, `docs/SCHEDULING.md`, `frontend/src/pages/Terminberechnung.jsx`

## Kernaussage

Die Engine wurde irgendwann **komplett neu geschrieben** (slot-basiert statt `required_hours`-basiert), aber **Tests, Doku und Teile der Spezifikation wurden nicht mitgezogen**. `tests/test_scheduler.py` importiert Funktionen, die es nicht mehr gibt (`allowed_starts`, `calculate_committee`, `is_present`, `required_hours`) und den Enum-Wert `AusschussTyp.POLY`, der nicht mehr existiert. **Die Engine läuft daher komplett ohne Testabdeckung** — die Tests schlagen bereits beim Import fehl. Das erklärt, warum sich die fehlerhafte Logik bisher nicht eindeutig identifizieren ließ: `docs/SCHEDULING.md` und die Tests beschreiben eine andere Engine als die, die tatsächlich läuft.

Darunter liegen **fünf konkrete Fehler, die direkt falsche Termine erzeugen** (F1–F5), plus eine Reihe von Regel-Abweichungen gegenüber der Spezifikation.

---

## F1 — `start_datum` wird nie auf Montag normalisiert ⚠️ Hauptverdächtiger für falsche Datumsausgabe

**Ort:** `calculation_service.py:172` und `scheduler.py:255–266`

```python
start_date = req.start_datum or date.today()
```

Die gesamte Datumsberechnung (`datum = start_date + (woche-1)*7 + offset[wochentag]`, mit MO=0 … FR=4) **setzt voraus, dass `start_date` ein Montag ist**. Das wird nirgends geprüft oder korrigiert:

- Frontend (`Terminberechnung.jsx:74`): freies Datumsfeld, `startDatum || null` — der Benutzer kann jedes Datum wählen.
- Backend-Default: `date.today()` — heute z. B. ein **Sonntag**.

Folge: Ein Slot mit Label „Mo" bekommt als `datum` den Sonntag, „Fr" den Donnerstag usw. — **jedes ausgegebene Datum passt nicht zum Wochentag**. Zusätzlich laufen dadurch die **Abwesenheits-Checks gegen die falschen Kalendertage** (jemand, der Montag auf Urlaub ist, wird am „falschen Montag" geprüft und ggf. als anwesend gezählt).

**Vorschlag:** In `run_calculation` normalisieren: `start_date -= timedelta(days=start_date.weekday())` (bzw. bei Eingabe ≠ Montag auf den nächsten Montag springen — fachlich klären), plus Pydantic-Validator im `BerechnungRequest` und Datumsbeschränkung im Frontend-Datepicker (nur Montage wählbar).

## F2 — Randslots prüfen nicht den ganzen Sitzungsblock

**Ort:** `scheduler.py:41–50` (TIME_SLOTS)

Spezifikation (`docs/SCHEDULING.md` §2–3, Masterprompt): *„der gesamte Sitzungsblock muss abgedeckt sein"*, explizit `07:00–08:30 → [7, 8]`.

Implementiert ist aber:

| Slot | benötigte Stunden (Ist) | benötigt laut Spez |
|---|---|---|
| 07:00–08:30 | `["07:00"]` | 07 **und 08** |
| 19:00–20:30 | `["19:00"]` | 19 **und 20** — Slot dürfte gar nicht existieren (Ende > 20:00!) |

Personen, die nur 07:00–08:00 verfügbar sind, werden für die volle Sitzung 07:00–08:30 als anwesend gezählt; analog beim 19:00-Slot. Der 19:00–20:30-Slot **verletzt zudem die Regel „Sitzungsende ≤ 20:00"**. Beides erzeugt Termine mit zu optimistischer Anwesenheit → falsche „TOP"/„beschlussfähig"-Einstufungen.

**Vorschlag:** 19:00–20:30-Slot entfernen (letzter zulässiger Start bei 90 min ist 18:30) und 07:00-Slot entweder streichen oder mit `["07:00","08:00"]` prüfen (dann muss die Verfügbarkeits-Matrix eine 08:00-Stunde bekommen — fachlich klären, was das 07:00-Häkchen bedeutet). Besser noch: `required_hours` wieder generisch aus `block_minuten` berechnen statt hartcodierter Slot-Liste (siehe V1).

## F3 — Quorumsregel weicht von der Spezifikation ab

**Ort:** `scheduler.py:196–227` (`is_quorate`)

- Spez (`SCHEDULING.md` §5): **standard = Obmann + ≥ 4 weitere**, poly = +2, kontroll = +3 („Obmann + X weitere, X je nach AusschussTyp").
- Implementiert: `len(present_ids) >= len(members) / 2` — **50 %-Regel inklusive Obmann**, für alle Standard-Ausschüsse gleich.
- `CommitteeInput.quorum_override` existiert, wird aber **nirgends verwendet** (Zeile 100 definiert, nie gelesen); `calculation_service.py:120` übergibt fix `None`.
- Die Enum-Typen poly/kontroll wurden entfernt (laut CLAUDE.md ist alles „standard"), ein Ersatzmechanismus (z. B. Quorum je Ausschuss konfigurierbar) fehlt.

Beispiel: 6 Mitglieder, Obmann + 2 anwesend → Engine sagt „beschlussfähig" (3 ≥ 3), Spez verlangt Obmann + 4 = 5 Personen. **Termine werden fälschlich als beschlussfähig ausgewiesen.**

**Vorschlag:** Fachlich festlegen, welche Regel gilt (Masterprompt-Quorum vs. 50 %). Dann: Quorum als Feld am `Ausschuss` (oder in `Sitzungsregel`) pflegbar machen, `quorum_override` tatsächlich auswerten und die Duplikat-Deduplizierung wieder einbauen (die alte Engine deduplizierte gleiche `person_id`; die neue zählt Duplikate doppelt fürs Quorum).

## F4 — Sortier-Priorität widerspricht der Spezifikation, `freitag_modus` wird ignoriert

**Ort:** `scheduler.py:309–325` (`sort_evaluations`), `363–445` (`_backtrack_schedule`)

Spez-Priorität: `100 % → beschlussfähig → Obmann+Stv. → nur Obmann`; **Freitag jeweils eine Stufe schlechter**.

Implementiert:

1. `sort_evaluations` ordnet `chair_present` und `deputy_chair_present` **vor** `quorate`. Ein Slot „Obmann+Stv. da, aber nicht beschlussfähig" schlägt damit einen Slot „Obmann da + beschlussfähig, Stv. fehlt" — genau umgekehrt zur Spez.
2. Freitag ist nur **letztes Tiebreak-Kriterium** (`WEEKDAY_SCORE`), keine Prioritätsstufe. Ein Freitag-Termin mit 100 % schlägt jeden Nicht-Freitag-Termin mit 99 %; laut Spez-Tabelle (Prio 2 vs. 1) wäre das zumindest zu prüfen — vor allem aber:
3. `freitag_modus` („reserve"/„normal"/„nein") wird **komplett ignoriert**. Das Frontend sendet standardmäßig `freitag_modus: "nein"` (`Terminberechnung.jsx:10`) — trotzdem liefert die Engine Freitagstermine. Grep über `app/services/` findet keinerlei Auswertung.
4. Im globalen Backtracking (`_backtrack_schedule:387–394`) besteht der Sortierschlüssel nur aus `full_attendance`, `chair_present` und Wochen-Balance — `quorate`, Anwesenheitsquote, Wochentag und Uhrzeit fehlen. Bei mehreren gleichwertigen Optionen ist die Wahl faktisch **zufällig** (z. B. Freitag 07:00 statt Dienstag 17:00). Das erklärt „unerklärliche" Terminwahlen im Ergebnis.

**Vorschlag:** Eine einzige zentrale Prioritätsfunktion (Statusklasse laut Spez + Freitagsabschlag + Uhrzeit-/Tagespräferenz) definieren und **sowohl** in `sort_evaluations` **als auch** im Backtracking als Schlüssel verwenden. `freitag_modus == "nein"` → Freitagsslots vor der Evaluierung herausfiltern; „reserve" → Statusstufe +1.

## F5 — Default `min_verfuegbarkeit = 100` filtert fast alles weg

**Ort:** `schemas.py:187`, `calculation_service.py:193–201`

Der Schema-Default ist `100`. Damit überleben nur 100 %-Slots die Vorfilterung — Ausschüsse ohne einen einzigen Volltreffer **verschwinden stillschweigend aus dem Ergebnis** (`continue` in Zeile 211f.) bzw. der Endpoint liefert 404 „Keine aktiven Ausschüsse gefunden". Auch der globale Scheduler sieht dann nur 100 %-Optionen und kann keine beschlussfähigen Ausweichtermine vergeben. Aus Benutzersicht: fehlende oder scheinbar willkürliche Termine.

**Vorschlag:** Default auf 0 (oder z. B. 50) senken; Ausschüsse ohne passende Slots explizit mit Hinweis („kein Termin ≥ X % gefunden") im Response ausweisen statt sie wegzulassen.

---

## Weitere Abweichungen und Risiken (nicht unmittelbar, aber real)

**W1 — Erlaubte Startzeiten stark reduziert.** Spez: jede volle/halbe Stunde 07:00–19:30. Implementiert: 8 hartcodierte Slots (07:00, 16:00–19:00). Vormittags-/Nachmittagstermine (07:30–15:30) sind unmöglich. Vermutlich pragmatisch gewollt (Verfügbarkeitsdaten existieren nur für 7, 16–19 Uhr) — sollte aber bewusst entschieden und dokumentiert werden.

**W2 — Halbstunden-Verfügbarkeiten sind tote Daten.** Seed und Modell speichern `stunde = 16.5, 17.5, 18.5`, die Engine prüft aber nur volle Stunden („16:00", „17:00" …). Wer in der Admin-Matrix nur ein Halbstunden-Häkchen setzt, wird von der Engine ignoriert. Entweder Halbstunden aus Modell/UI entfernen oder in der Coverage-Prüfung berücksichtigen.

**W3 — Fixierte Termine werden bei Neuberechnung nicht berücksichtigt.** `run_calculation` liest `Sitzungsvorschlag` nie; das Frontend lädt die fixierten Termine nur zur Anzeige. Neue Vorschläge können mit bereits fixierten Sitzungen kollidieren.

**W4 — `Sitzungsregel` wird fast vollständig ignoriert.** Nur `planungswochen` wird gelesen. `block_minuten` (Slots sind hart 90 min), `freitag_modus`, `max_ausschuesse_pro_tag` haben keinerlei Wirkung — die Admin-Seite `/admin/sitzungsregeln` suggeriert Konfigurierbarkeit, die nicht existiert.

**W5 — Perioden-Vermischung möglich.** Das Frontend sendet kein `periode_id` im Calculate-Payload, nur `ausschuss_ids`. Werden alle Ausschüsse abgewählt (`ausschuss_ids: null`), rechnet das Backend **alle aktiven Ausschüsse aller Perioden** — „Bildung 2025" und „Bildung 2026" konkurrieren dann um Slots. Zudem wird `Mitgliedschaft.periode_id` beim Laden nicht gegen `ausschuss.periode_id` geprüft.

**W6 — Konfliktprüfung pauschal statt mitgliederbasiert.** Der globale Scheduler behandelt alle Ausschüsse als konfliktbehaftet, sobald sich Zeiten am selben Tag überlappen — unabhängig davon, ob sie gemeinsame Mitglieder haben. Konservativ, aber es verdrängt gute Termine unnötig. `max_ausschuesse_pro_tag` wird dabei nicht durchgesetzt.

**W7 — Kleinere Codefehler.**
- `calculation_service.py:236`: Duplikat-Check der „beste"-Liste vergleicht nur `woche` + `start`, **nicht den Wochentag** — ein legitimer Termin am anderen Tag zur gleichen Zeit wird fälschlich übersprungen.
- `scheduler.py:425`: `if option in sorted_options[:5]` — der Kommentar behauptet „top 5 already tried", tatsächlich hat die erste Schleife **alle** Optionen probiert; die zweite Schleife ist redundant und der `in`-Vergleich auf ungefrorenen Dataclasses mit Mitgliederlisten teuer.
- `TerminStatus.ALTERNATIV` wird nie vergeben (`SlotEvaluation.status` kennt den Fall „Obmann+Stv. unter Quorum" nicht); `alternativen`, `risiko`, `empfehlung_text` sind hart leer — Spez-Ausgaben c, e, f fehlen.
- Debug-`print()` in `scheduler.py` (Zeilen 376, 464–465, 472) gehören durch Logging ersetzt.

---

## Empfohlene Reihenfolge der Behebung

1. **Tests reparieren zuerst** (Basis für alles Weitere): `test_scheduler.py` auf die aktuelle Engine-API umschreiben bzw. entscheiden, ob die alte API (`required_hours`, `allowed_starts`) wiederhergestellt wird. Ohne grüne Engine-Tests ist jede weitere Korrektur blind. `docs/SCHEDULING.md` als fachliche Referenz bestätigen oder aktualisieren — aktuell ist unklar, welche Regeln „gelten".
2. **F1** (Montag-Normalisierung + Validierung) — kleinster Eingriff, größter sichtbarer Effekt auf falsche Datumsausgaben.
3. **F5** (min_verfuegbarkeit-Default) und **F4.3** (`freitag_modus == "nein"` filtern) — je 1–2 Zeilen, direkt benutzersichtbar.
4. **F2** (Randslots) und **F3** (Quorum) — erfordern eine fachliche Entscheidung (Bedeutung des 07:00-Häkchens; gültige Quorumsregel), danach kleine Engine-Änderung + Tests.
5. **F4.1/F4.4** (einheitliche Prioritätsfunktion) und **W3** (fixierte Termine in Konfliktprüfung) — mittlerer Umfang.
6. **V1 (Architekturvorschlag):** Hartcodierte `TIME_SLOTS` durch generische Berechnung ersetzen: `allowed_starts(block_minuten, max_ende)` × `required_hours(start, dauer)` wie in der alten Engine/Doku. Damit werden `block_minuten` aus der `Sitzungsregel` wieder wirksam, die Randslot-Fehler (F2) verschwinden strukturell, und die vorhandene Doku/Testbasis passt wieder.

## Nachtrag (2026-07): Umsetzung & weitere Erkenntnisse

Alle Befunde F1–F5 wurden behoben (Montag-Normalisierung, Randslot-Festlegung,
Quorum-Dedup + quorum_override, zentrale Prioritätsfunktion + freitag_modus,
min_verfuegbarkeit-Default 0). Tests neu geschrieben (16 Engine-Tests grün),
Alt-Tests bereinigt. Beim Testen an der Oberfläche kamen **zwei Datenprobleme**
als weitere Ursachen falscher Termine ans Licht:

**D1 — Seed-Verfügbarkeiten waren veraltet.** `seed.py` (PERSONS_DATA) wich von
der Quelle der Wahrheit `realdata.json` ab — mehreren Stadträten (Hofreither,
Prohaska, Ströcker, Hintersteiner, Killinger-Spitz, Pum) fehlten 07:00/16:00
komplett. Korrektur: `sync_verfuegbarkeiten.py --fix` gleicht die DB mit
realdata.json ab.

**D2 — Geseedete "Test Person" blockierte Infrastruktur.** Der Seed setzte eine
Test Person mit Vormittags-Verfügbarkeiten (09–16 Uhr) als Mitglied in den
ERSTEN Ausschuss — dadurch war dort nie ein 100%-Termin möglich. Korrektur:
Seed-Block entfernt, `delete_testperson.py` löscht sie aus Bestands-DBs.
Danach stimmen die Engine-Ergebnisse mit der externen Maximalanalyse überein
(Infrastruktur: Mo–Fr 17:00–18:30 / 18:30–20:00 als Top-Termine).

**F6 (neu) — stv_da-Serialisierung.** `deputy and deputy.person_id in ...`
lieferte `None` statt `False` bei Ausschüssen ohne Stellvertreter → Pydantic-
ValidationError. Behoben durch `is not None and`.

Zusätzlich umgesetzt: Verfügbarkeiten je Periode (periode_id am Modell,
Migrations-Skript, Perioden-Combobox + „Alle"-Übersicht im Admin-Tab),
Sitzungsart-Trennung in der Berechnung (GR/STR getrennt von Ausschüssen),
NaN%-Anzeigefehler und hartcodierte Zusammenfassungswerte im Frontend behoben.

## Verifikation der Befunde

Alle Befunde wurden direkt am Quellcode verifiziert (Zeilenangaben oben). Eindeutig belegbar ohne Laufzeitumgebung: F1 (kein `weekday()`-Aufruf im gesamten Berechnungspfad), F2 (TIME_SLOTS-Literale), F3 (`quorum_override` hat keine Referenz außer der Definition), F4.3 (`freitag_modus` kommt in `app/services/` nicht vor), F5 (Schema-Default 100), Testbruch (Import nicht existenter Symbole + `AusschussTyp.POLY`). Zur Reproduktion empfohlen: `pytest tests/test_scheduler.py -v` (erwartet: ImportError) und ein `/api/calculate`-Aufruf ohne `start_datum` an einem Nicht-Montag (erwartet: `datum` passt nicht zu `wochentag`).
