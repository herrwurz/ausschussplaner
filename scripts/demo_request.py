"""Demo: Seed laden und eine Berechnung lokal (ohne HTTP) ausführen."""
from __future__ import annotations

from app.db.base import SessionLocal
from app.db.seed import seed
from app.schemas.schemas import BerechnungRequest
from app.services.calculation_service import run_calculation


def main() -> None:
    seed(reset=True)
    db = SessionLocal()
    try:
        resp = run_calculation(
            db, BerechnungRequest(planungswochen=2, freitag_modus="reserve", max_alternativen=5)
        )
        print("Zusammenfassung:", resp.zusammenfassung)
        for a in resp.analysen:
            top = len(a.top_termine)
            print(f"  {a.ausschuss_name:20s} {a.typ.value:9s} "
                  f"Mitglieder={len(a.mitglieder)} Top={top}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
