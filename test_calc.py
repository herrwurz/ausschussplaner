from app.db.base import SessionLocal
from app.services.calculation_service import run_calculation
from app.models.models import Gemeinderatsperiode, Ausschuss
from app.schemas.schemas import BerechnungRequest

db = SessionLocal()
periode = db.query(Gemeinderatsperiode).first()
ausschuesse = db.query(Ausschuss).filter(Ausschuss.periode_id == periode.id).all()
ausschuss_ids = [a.id for a in ausschuesse]

try:
    req = BerechnungRequest(
        periode_id=periode.id,
        ausschuss_ids=ausschuss_ids,
        planungswochen=2,
        freitag_modus='nein',
        max_alternativen=10,
        min_verfuegbarkeit=0
    )

    result = run_calculation(db=db, req=req)

    print(f'Analyse count: {len(result.analysen)}')
    for i, analyse in enumerate(result.analysen[:3]):
        print(f'  [{i}] {analyse.ausschuss_name}: {len(analyse.top_termine)} Termine')
        for term in analyse.top_termine[:2]:
            print(f'      - Woche {term.woche} {term.wochentag} {term.start}')

except Exception as e:
    import traceback
    print(f'FEHLER: {e}')
    traceback.print_exc()
