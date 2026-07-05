# Berechnungslogik im Detail

Stand: 2026-07 — beschreibt die aktuelle slot-basierte Engine (`app/services/scheduler.py`).

## 1. Mitgliedsdefinition
Nur Personen mit gültiger Rolle (`Obmann`, `Obmann Stellvertreter`, `Mitglied`)
zählen. Duplikate (gleiche `person_id` mehrfach) werden dedupliziert.

## 2. Zeitslots (90 Minuten)
Feste Slot-Liste (`TIME_SLOTS`); ein Slot verlangt, dass **alle** aufgeführten
Verfügbarkeitsstunden gesetzt sind:

| Slot          | benötigte Stunden |
|---------------|-------------------|
| 07:00–08:30   | 07                |
| 16:00–17:30   | 16, 17            |
| 16:30–18:00   | 16, 17            |
| 17:00–18:30   | 17, 18            |
| 17:30–19:00   | 17, 18            |
| 18:00–19:30   | 18, 19            |
| 18:30–20:00   | 18, 19            |
| 19:00–20:30   | 19                |

Fachliche Festlegung (2026-07): Die Randslots 07:00–08:30 und 19:00–20:30 sind
gültige Sitzungszeiten. Das Häkchen „07:00" bzw. „19:00" bedeutet „für den
gesamten Früh-/Spätblock verfügbar" (die Matrix kennt keine 08:00/20:00-Stunden).

## 3. Anwesenheit
Eine Person ist anwesend, wenn alle benötigten Stunden in ihrer Verfügbarkeit
liegen **und** sie am konkreten Datum nicht abwesend ist (Abwesenheiten haben
Vorrang vor der Standardverfügbarkeit).

Verfügbarkeiten sind perioden-fähig: Einträge mit `periode_id = NULL` sind die
Standardverfügbarkeit. Existieren für eine Person Einträge mit der Periode des
berechneten Ausschusses, gelten für diese Person **ausschließlich** diese
(vollständiges Überschreiben, kein Mischen); sonst greift der Standard.

## 4. Startdatum
Die Datumsberechnung setzt einen **Montag** als `start_datum` voraus.
Nicht-Montage (inkl. Default „heute") werden automatisch auf den **nächsten
Montag** normalisiert (`calculation_service.run_calculation`).

## 5. Beschlussfähigkeit
| Typ         | Bedingung                                              |
|-------------|--------------------------------------------------------|
| standard    | Obmann anwesend + mind. 50 % der Mitglieder            |
| stadtrat    | alle Mitglieder anwesend                               |
| gemeinderat | alle Mitglieder ODER mind. 50 % (Obmann/Bgm. immer)    |

`quorum_override` (falls am `CommitteeInput` gesetzt) ersetzt bei `standard`
die 50 %-Regel durch eine absolute Mindestanzahl Anwesender; die Obmann-Pflicht
bleibt bestehen. Fehlt der Obmann, ist der Termin **immer** nicht beschlussfähig.

## 6. Statusklassen & Priorität (niedriger = besser)
Zentrale Funktion: `status_rank()` / `priority_key()` — wird identisch in der
Einzelsortierung **und** im globalen Backtracking verwendet.

| Status               | Bedingung                    | Rang (Mo–Do / Fr) |
|----------------------|------------------------------|-------------------|
| top                  | 100 % Anwesenheit            | 0 / 1             |
| beschlussfähig       | Obmann + Quorum              | 2 / 3             |
| alternativ           | Obmann + Stv., unter Quorum  | 4 / 5             |
| obmann_da            | nur Obmann                   | 6 / 7             |
| nicht_beschlussfähig | sonst                        | 8 / 9             |

Nachrangige Kriterien: mehr Anwesende → höhere Quote → früherer Wochentag →
bevorzugte Uhrzeit.

### freitag_modus
- `nein`: Freitage werden gar nicht evaluiert
- `reserve` (Default): Freitag eine Prioritätsstufe schlechter (siehe Tabelle)
- `normal`: wie reserve (Abschlag wirkt nur als Tiebreak innerhalb der Stufe)

## 7. Globales Scheduling
Backtracking über alle Ausschüsse (wenigste Optionen zuerst), Konflikt =
Zeitüberschneidung am selben Tag derselben Woche. Wochen-Balance wird als
Zwischenkriterium bevorzugt. Ausschüsse ohne Terminoptionen werden übersprungen
und in `GlobalSchedule.conflicts` ausgewiesen. Schlägt das Backtracking fehl,
greift ein Greedy-Fallback (best effort, Konflikte werden gemeldet).

## 8. Ausgabe je Ausschuss
- `top_termine` (100 %), `beschlussfaehig`, `alternativen` (Obmann+Stv. unter
  Quorum), `beste_je_tag` (konfliktfrei zugewiesener Termin zuerst)
- Ausschüsse ohne Slots über der Mindestquote erscheinen mit `empfehlung_text`-
  Hinweis statt stillschweigend zu fehlen
- Risikoanalyse und Empfehlungstext sind noch nicht implementiert (offen)

## Bekannte offene Punkte
- Fixierte Termine (`Sitzungsvorschlag`) fließen nicht in die Konfliktprüfung ein
- `Sitzungsregel.block_minuten` und `max_ausschuesse_pro_tag` werden nicht ausgewertet
- Konfliktprüfung ist pauschal (unabhängig von gemeinsamen Mitgliedern)
- Halbstunden-Verfügbarkeiten (16.5 …) werden gespeichert, aber nicht ausgewertet
