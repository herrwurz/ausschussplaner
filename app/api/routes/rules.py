"""API-Routen für Sitzungsregeln (Singleton)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_staff, require_super_admin
from app.db.base import get_db
from app.models.models import Sitzungsregel, User
from app.schemas.schemas import SitzungsregelBase, SitzungsregelOut

router = APIRouter(
    prefix="/rules",
    tags=["Sitzungsregeln"],
    dependencies=[Depends(require_staff)],
)


def _get_or_create(db: Session) -> Sitzungsregel:
    regel = db.get(Sitzungsregel, 1)
    if regel is None:
        regel = Sitzungsregel(id=1)
        db.add(regel)
        db.commit()
        db.refresh(regel)
    return regel


@router.get("", response_model=SitzungsregelOut)
def get_rules(db: Session = Depends(get_db)):
    return _get_or_create(db)


@router.put("", response_model=SitzungsregelOut)
def update_rules(
    payload: SitzungsregelBase,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_super_admin),
):
    """Sitzungsregeln ändern — nur Super-Admin (nicht Sekretariat)."""
    regel = _get_or_create(db)
    for k, v in payload.model_dump().items():
        setattr(regel, k, v)
    db.commit()
    db.refresh(regel)
    return regel
