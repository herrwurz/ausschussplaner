"""Änderungsprotokoll (Audit-Log)."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.models import AuditLog, User

# Anzeigenamen für die Admin-UI
ACTION_LABELS: dict[str, str] = {
    "termin.fixieren": "Termin fixiert",
    "termin.verschieben": "Termin verschoben",
    "termin.absagen": "Termin abgesagt",
    "termin.loeschen": "Termin gelöscht",
    "person.anlegen": "Person angelegt",
    "person.aendern": "Person geändert",
    "person.loeschen": "Person gelöscht",
    "person.deaktivieren": "Person deaktiviert",
    "person.aktivieren": "Person aktiviert",
    "person.verfuegbarkeit": "Verfügbarkeit gesetzt",
    "person.agenda_transfer": "Agenda übertragen",
    "ausschuss.anlegen": "Ausschuss angelegt",
    "ausschuss.aendern": "Ausschuss geändert",
    "ausschuss.loeschen": "Ausschuss gelöscht",
    "ausschuss.kopieren": "Ausschuss kopiert",
    "abwesenheit.anlegen": "Abwesenheit angelegt",
    "abwesenheit.aendern": "Abwesenheit geändert",
    "abwesenheit.loeschen": "Abwesenheit gelöscht",
    "benutzer.anlegen": "Benutzer angelegt",
    "benutzer.aendern": "Benutzer geändert",
    "benutzer.loeschen": "Benutzer gelöscht",
    "benutzer.passwort_reset": "Passwort zurückgesetzt",
}


def write_audit(
    db: Session,
    user: User | None,
    *,
    action: str,
    entity_type: str = "",
    entity_id: int | None = None,
    detail: str = "",
) -> AuditLog:
    """Fügt einen Audit-Eintrag zur Session hinzu (kein eigenes commit)."""
    entry = AuditLog(
        user_id=user.id if user else None,
        user_email=(user.email if user else "") or "",
        action=action,
        entity_type=entity_type or "",
        entity_id=entity_id,
        detail=(detail or "")[:2000],
    )
    db.add(entry)
    return entry
