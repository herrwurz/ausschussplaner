"""Bindeglied zwischen DB und der reinen Berechnungs-Engine."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.enums import AusschussTyp, TerminStatus, Wochentag
from app.models.models import Ausschuss, Sitzungsregel
from app.schemas.schemas import (
    AusschussAnalyse,
    BerechnungRequest,
    BerechnungResponse,
    MitgliedOut,
    TerminVorschlagOut,
)
from app.services import scheduler as sched


def _load_regel(db: Session) -> Sitzungsregel:
    regel = db.get(Sitzungsregel, 1)
    if regel is None:
        regel = Sitzungsregel(id=1)
        db.add(regel)
        db.commit()
        db.refresh(regel)
    return regel


def _committee_to_input(ausschuss: Ausschuss) -> sched.CommitteeInput:
    """ORM-Ausschuss -> Engine-Eingabe inkl. Verfügbarkeiten."""
    members: list[sched.MemberInput] = []
    for ms in ausschuss.mitgliedschaften:
        person = ms.person
        if person is None or not person.aktiv:
            continue
        avail: dict[Wochentag, set[int]] = {d: set() for d in sched.DAYS}
        for v in person.verfuegbarkeiten:
            if v.verfuegbar:
                avail.setdefault(v.wochentag, set()).add(v.stunde)
        members.append(
            sched.MemberInput(
                person_id=person.id,
                name=person.name,
                rolle=ms.rolle,
                availability=avail,
            )
        )
    return sched.CommitteeInput(
        committee_id=ausschuss.id,
        name=ausschuss.name,
        typ=ausschuss.typ,
        members=members,
        quorum_override=ausschuss.quorum_override,
    )


def _slot_to_out(s: sched.Slot) -> TerminVorschlagOut:
    return TerminVorschlagOut(
        woche=s.week,
        wochentag=s.day,
        start=s.start_str,
        ende=s.end_str,
        ausschuss_id=s.committee_id,
        ausschuss_name=s.committee_name,
        obmann_da=s.obmann_present,
        stv_da=s.stv_present,
        anwesend=len(s.present),
        mitglieder=len(s.present) + len(s.missing),
        quote=s.quote,
        status=s.status,
        empfehlung=s.empfehlung,
        fehlende=[m.name for m in s.missing],
    )


def run_calculation(db: Session, req: BerechnungRequest) -> BerechnungResponse:
    """Hauptfunktion: berechnet Vorschläge für die gewünschten Ausschüsse."""
    regel = _load_regel(db)
    quorum_defaults = {
        AusschussTyp.STANDARD: regel.quorum_standard,
        AusschussTyp.POLY: regel.quorum_poly,
        AusschussTyp.KONTROLL: regel.quorum_kontroll,
    }

    stmt = select(Ausschuss).options(
        selectinload(Ausschuss.mitgliedschaften)
    ).where(Ausschuss.aktiv.is_(True))
    if req.ausschuss_ids:
        stmt = stmt.where(Ausschuss.id.in_(req.ausschuss_ids))
    ausschuesse = db.scalars(stmt).unique().all()

    analysen: list[AusschussAnalyse] = []
    top_total = besch_total = krit_total = 0

    for a in ausschuesse:
        cin = _committee_to_input(a)
        result = sched.calculate_committee(
            cin,
            duration_min=regel.block_minuten,
            weeks=req.planungswochen or regel.planungswochen,
            friday_mode=req.freitag_modus,
            max_alternatives=req.max_alternativen,
            quorum_defaults=quorum_defaults,
        )

        tops = [s for s in result.all_slots if s.status == TerminStatus.TOP]
        besch = [s for s in result.all_slots if s.status == TerminStatus.BESCHLUSSFAEHIG]
        alt = [
            s for s in result.all_slots
            if s.status in (TerminStatus.ALTERNATIV, TerminStatus.OBMANN_DA)
        ]

        top_total += sum(1 for s in result.best_per_day if s.status == TerminStatus.TOP)
        besch_total += sum(1 for s in result.best_per_day if s.status == TerminStatus.BESCHLUSSFAEHIG)
        krit_total += sum(
            1 for s in result.best_per_day if s.status == TerminStatus.NICHT_BESCHLUSSFAEHIG
        )

        analysen.append(
            AusschussAnalyse(
                ausschuss_id=a.id,
                ausschuss_name=a.name,
                typ=a.typ,
                mitglieder=[
                    MitgliedOut(person_id=m.person_id, rolle=m.rolle, name=m.name)
                    for m in result.members
                ],
                top_termine=[_slot_to_out(s) for s in tops[:10]],
                beschlussfaehig=[_slot_to_out(s) for s in besch[:10]],
                alternativen=[_slot_to_out(s) for s in alt[:10]],
                beste_je_tag=[_slot_to_out(s) for s in result.best_per_day],
                risiko=sched.risk_analysis(result),
                empfehlung_text=sched.recommendation_text(result),
            )
        )

    return BerechnungResponse(
        analysen=analysen,
        zusammenfassung={
            "ausschuesse": len(analysen),
            "top_termine": top_total,
            "beschlussfaehig": besch_total,
            "kritisch": krit_total,
        },
    )
