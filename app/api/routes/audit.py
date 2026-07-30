"""API: Änderungsprotokoll (Audit-Log)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import require_staff
from app.db.base import get_db
from app.models.models import AuditLog
from app.schemas.schemas import AuditLogOut
from app.services.audit_service import ACTION_LABELS

router = APIRouter(
    prefix="/audit",
    tags=["Audit-Log"],
    dependencies=[Depends(require_staff)],
)


@router.get("", response_model=list[AuditLogOut])
def list_audit_logs(
    db: Session = Depends(get_db),
    limit: int = Query(100, ge=1, le=500),
    action: str | None = Query(None, description="Exakter Action-Code oder Präfix z.B. termin."),
    entity_type: str | None = None,
    entity_id: int | None = None,
):
    """Neueste Änderungen zuerst."""
    q = db.query(AuditLog)
    if action:
        if action.endswith("."):
            q = q.filter(AuditLog.action.startswith(action))
        else:
            q = q.filter(AuditLog.action == action)
    if entity_type:
        q = q.filter(AuditLog.entity_type == entity_type)
    if entity_id is not None:
        q = q.filter(AuditLog.entity_id == entity_id)

    rows = q.order_by(AuditLog.created_at.desc(), AuditLog.id.desc()).limit(limit).all()
    return [
        AuditLogOut(
            id=r.id,
            created_at=r.created_at,
            user_id=r.user_id,
            user_email=r.user_email,
            action=r.action,
            action_label=ACTION_LABELS.get(r.action, r.action),
            entity_type=r.entity_type,
            entity_id=r.entity_id,
            detail=r.detail,
        )
        for r in rows
    ]
