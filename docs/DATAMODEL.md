# Datenmodell

## ER-Übersicht

```
Person 1───* Verfuegbarkeit
Person 1───* Mitgliedschaft *───1 Ausschuss
Person 1───* Abwesenheit
Sitzungsregel (Singleton, id=1)
Jahresplan
Ausschuss 1───* Sitzungsvorschlag
```

## Tabellen

### person
| Spalte     | Typ      | Bemerkung                       |
|------------|----------|---------------------------------|
| id         | int PK   |                                 |
| vorname    | str      |                                 |
| nachname   | str      |                                 |
| titel      | str      | z. B. „Mag.", „DI"              |
| gremium    | str      | z. B. „Stadtrat"                |
| email      | str      |                                 |
| aktiv      | bool     | inaktive werden nicht geplant   |

### verfuegbarkeit
Eindeutig je (person_id, wochentag, stunde).
`stunde` ist eine volle Stunde (0–23). In den Echtdaten: 7, 16, 17, 18, 19.

### ausschuss
`typ` ∈ {standard, poly, kontroll} bestimmt das Standard-Quorum.
`quorum_override` überschreibt das Quorum optional pro Ausschuss.

### mitgliedschaft
Eindeutig je (person_id, ausschuss_id). `rolle` ∈ {Obmann, Obmann Stellvertreter, Mitglied}.
**Nur ein vorhandener Datensatz mit gültiger Rolle macht eine Person zum Mitglied.**

### abwesenheit
Datierter Zeitraum (von–bis) mit Art (Urlaub, Krankheit, …).

### sitzungsregel
Singleton (id=1): Blockdauer, Quoren je Typ, Planungswochen, Freitag-Modus.

### sitzungsvorschlag
Persistierbares Berechnungsergebnis (für spätere Historie/Fixierung).
