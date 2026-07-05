"""Diagnose: Warum liefert ein Ausschuss (k)eine Terminvorschläge?

Zeigt Mitglieder, Rollen, Verfügbarkeiten (Standard + je Periode) und rechnet
die Engine direkt. Optional: Text aus einem Word-Dokument extrahieren, um die
Soll-Termine zu vergleichen.

Ausführung:
    python analyse_ausschuss.py                       # Ausschuss "Infrastruktur"
    python analyse_ausschuss.py Kultur                # anderer Ausschuss
    python analyse_ausschuss.py Infrastruktur "C:\\Pfad\\Maximalanalyse.docx"
"""
import re
import sys
import zipfile
from pathlib import Path

from app.db.base import SessionLocal
from app.models.models import Ausschuss, Verfuegbarkeit
from app.services import scheduler as sched
from app.services.calculation_service import _load_committee_input

name_filter = sys.argv[1] if len(sys.argv) > 1 else "Infrastruktur"
docx_pfad = sys.argv[2] if len(sys.argv) > 2 else None

db = SessionLocal()
try:
    ausschuesse = db.query(Ausschuss).filter(Ausschuss.name.like(f"%{name_filter}%")).all()
    if not ausschuesse:
        print(f"!! Kein Ausschuss mit Namen wie '{name_filter}' gefunden.")
        alle = db.query(Ausschuss).all()
        print("Vorhandene Ausschuesse:", [(a.id, a.name, f"periode={a.periode_id}", f"aktiv={a.aktiv}") for a in alle])

    for a in ausschuesse:
        print(f"\n=== {a.name} (id={a.id}, typ={a.typ.value}, periode_id={a.periode_id}, aktiv={a.aktiv}) ===")
        print(f"Mitgliedschaften: {len(a.mitgliedschaften)}")
        for m in a.mitgliedschaften:
            std = db.query(Verfuegbarkeit).filter(
                Verfuegbarkeit.person_id == m.person_id,
                Verfuegbarkeit.periode_id.is_(None),
            ).count()
            per = db.query(Verfuegbarkeit).filter(
                Verfuegbarkeit.person_id == m.person_id,
                Verfuegbarkeit.periode_id.isnot(None),
            ).count()
            print(f"  {m.rolle.value:20s} {m.person.name:30s} aktiv={m.person.aktiv} "
                  f"| Verfuegbarkeit: {std} Standard, {per} perioden-spezifisch")

        ci = _load_committee_input(a, db=db)
        print(f"\nEngine-Input: {len(ci.members)} Mitglieder")
        for mem in ci.members:
            tage = {d.value: sorted(h for h in stunden) for d, stunden in mem.availability.items() if stunden}
            print(f"  {mem.rolle.value:20s} {mem.name:30s} {tage if tage else '!! KEINE VERFUEGBARKEIT'}")

        evals = sched.evaluate_committee_slots(ci, weeks=1)
        print(f"\nEngine-Ergebnis: {len(evals)} Slots evaluiert, Top 10:")
        for e in evals[:10]:
            fehlt = ", ".join(x.name for x in e.missing_members) or "-"
            print(f"  {e.weekday.value} {e.start_time}-{e.end_time}: {e.status.value:22s} "
                  f"{e.attendance_count}/{e.total_members} ({e.quote}%)  fehlt: {fehlt}")
finally:
    db.close()

if docx_pfad:
    print("\n=== Inhalt Word-Dokument ===")
    p = Path(docx_pfad)
    if not p.exists():
        print(f"!! Datei nicht gefunden: {p}")
    else:
        with zipfile.ZipFile(p) as z:
            xml = z.read("word/document.xml").decode("utf-8", errors="replace")
        # Absätze/Tabellenzellen in Zeilen umsetzen, Tags entfernen
        xml = xml.replace("</w:p>", "\n").replace("</w:tc>", " | ")
        text = re.sub(r"<[^>]+>", "", xml)
        text = re.sub(r"\n{3,}", "\n\n", text)
        print(text)
