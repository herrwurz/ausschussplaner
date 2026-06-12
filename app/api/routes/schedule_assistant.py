"""API-Routen für Schedule-Assistant Chatbot."""
import threading
import time

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.services.schedule_assistant import ScheduleAssistant

router = APIRouter(prefix="/schedule-assistant", tags=["Schedule-Assistant"])

# Session-Management mit TTL
# Sessions werden nach 30 Minuten Inaktivität entfernt, um Memory-Leaks
# zu verhindern. Zugriff ist durch ein Lock gegen Race Conditions geschützt.
SESSION_TTL_SECONDS = 30 * 60
assistant_sessions: dict[str, ScheduleAssistant] = {}
_session_last_seen: dict[str, float] = {}
_session_lock = threading.Lock()


def _purge_expired_sessions() -> None:
    """Entferne Sessions, die länger als SESSION_TTL_SECONDS inaktiv waren."""
    now = time.monotonic()
    expired = [
        sid
        for sid, last_seen in _session_last_seen.items()
        if now - last_seen > SESSION_TTL_SECONDS
    ]
    for sid in expired:
        assistant_sessions.pop(sid, None)
        _session_last_seen.pop(sid, None)


class MessageRequest(BaseModel):
    """User-Message für Chatbot."""
    user_id: int | None = None
    message: str


class MessageResponse(BaseModel):
    """Bot-Response."""
    response: str
    history: list[dict]


@router.post("/chat", response_model=MessageResponse)
def chat(payload: MessageRequest, db: Session = Depends(get_db)):
    """Chatbot-Endpoint: Verarbeite User-Input mit Verfügbarkeitsdaten."""
    session_id = str(payload.user_id or "default")

    with _session_lock:
        _purge_expired_sessions()

        # Erstelle oder hole Assistant-Session mit DB
        if session_id not in assistant_sessions:
            assistant_sessions[session_id] = ScheduleAssistant(db=db)
        else:
            # Update DB reference (für neue Requests)
            assistant_sessions[session_id].db = db

        assistant = assistant_sessions[session_id]
        _session_last_seen[session_id] = time.monotonic()

    response = assistant.process_user_input(payload.message)
    history = assistant.get_conversation_history()

    return MessageResponse(response=response, history=history)


@router.post("/reset")
def reset_conversation(user_id: int | None = None):
    """Setze Conversation für User zurück."""
    session_id = str(user_id or "default")
    with _session_lock:
        assistant_sessions.pop(session_id, None)
        _session_last_seen.pop(session_id, None)
    return {"status": "reset", "user_id": user_id}


@router.get("/planned-meetings")
def get_planned_meetings(db: Session = Depends(get_db)):
    """Hole alle geplanten Sitzungen aus der Datenbank."""
    from app.models.models import PlannedMeeting

    meetings = db.query(PlannedMeeting).order_by(PlannedMeeting.termin_datum).all()

    return [
        {
            "id": m.id,
            "meeting_type": m.meeting_type,
            "ausschuss_name": m.ausschuss.name if m.ausschuss else None,
            "termin_datum": m.termin_datum.isoformat(),
            "termin_zeit": m.termin_zeit,
            "verfuegbarkeit_score": m.verfuegbarkeit_score,
            "created_at": m.created_at.isoformat(),
        }
        for m in meetings
    ]


@router.delete("/planned-meetings/{meeting_id}")
def delete_planned_meeting(meeting_id: int, db: Session = Depends(get_db)):
    """Lösche geplante Sitzung."""
    from app.models.models import PlannedMeeting

    meeting = db.query(PlannedMeeting).filter(PlannedMeeting.id == meeting_id).first()
    if not meeting:
        return {"error": "Meeting nicht gefunden"}

    db.delete(meeting)
    db.commit()
    return {"status": "deleted", "id": meeting_id}
