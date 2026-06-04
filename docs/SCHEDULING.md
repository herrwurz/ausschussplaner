# Berechnungslogik im Detail

## 1. Mitgliedsdefinition
Nur Personen mit gültiger Rolle (`Obmann`, `Obmann Stellvertreter`, `Mitglied`)
zählen. Duplikate (gleiche Person mehrfach) werden dedupliziert.

## 2. Benötigte Stunden eines Blocks
```python
required_hours(start_min, duration_min)
# 07:00–08:30  -> [7, 8]
# 16:00–17:30  -> [16, 17]
# 17:00–18:30  -> [17, 18]
# 18:30–20:00  -> [18, 19]
```
Formel: von `floor(start/60)` bis `floor((start+dauer-1)/60)`.

## 3. Anwesenheit
Eine Person ist anwesend, wenn **alle** benötigten Stunden in ihrer
Verfügbarkeit liegen. Wird sie erst innerhalb des Blocks verfügbar
(z. B. 18:00 = Nein, 19:00 = Ja bei 18:30-Start), gilt sie als nicht anwesend.

## 4. Erlaubte Startzeiten
Jede volle und halbe Stunde von 07:00 bis 19:30. Sitzungsende darf 20:00
nicht überschreiten (konfigurierbar).

## 5. Beschlussfähigkeit
| Typ       | Bedingung                              |
|-----------|----------------------------------------|
| standard  | Obmann + ≥ 4 weitere anwesend          |
| poly      | Obmann + ≥ 2 weitere anwesend          |
| kontroll  | Obmann + ≥ 3 weitere anwesend          |

Fehlt der Obmann, ist der Termin **immer** nicht beschlussfähig.

## 6. Statusklassen & Priorität (niedriger = besser)
| Status                  | Bedingung                         | Prio (Mo–Do / Fr) |
|-------------------------|-----------------------------------|-------------------|
| top                     | 100 % Anwesenheit                 | 1 / 2             |
| beschlussfähig          | Obmann + Quorum                   | 3 / 4             |
| alternativ              | Obmann + Stv., unter Quorum       | 5 / 6             |
| obmann_da               | nur Obmann                        | 7                 |
| nicht_beschlussfähig    | sonst                             | 9                 |

## 7. Ausgabe je Ausschuss (a–f)
- **a** Mitgliederliste (echte Mitglieder, mit Verfügbarkeit)
- **b** Top-Termine (100 %)
- **c** Alternativen (beschlussfähig + alternativ)
- **d** Detailtabelle (beste Option je Tag)
- **e** Risikoanalyse (wer blockiert wie viele Termine?)
- **f** Empfehlung (Fixieren / Flexibel / Kritisch)
