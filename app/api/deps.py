"""Gemeinsame API-Dependencies: Authentifizierung & Autorisierung."""
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.models.enums import BenutzerRolle
from app.models.models import User
from app.services.auth_service import TokenService

# Admin-Panel / Staff-API (ohne Benutzerverwaltung)
STAFF_ROLLEN = frozenset({
    BenutzerRolle.SUPER_ADMIN,
    BenutzerRolle.SEKRETARIAT,
    BenutzerRolle.BENUTZER,
})


def get_current_user(
    db: Session = Depends(get_db),
    authorization: str = Header(None),
) -> User:
    """Hole den aktuellen Benutzer aus dem Bearer-Token (401 wenn ungültig)."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nicht authentifiziert",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization.split(" ", 1)[1]
    payload = TokenService.decode_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Ungültiger Token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = int(payload["sub"])
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Ungültiger Token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None

    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.aktiv:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Benutzer nicht gefunden oder deaktiviert",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def require_staff(user: User = Depends(get_current_user)) -> User:
    """Admin-Panel: Super-Admin, Sekretariat und Legacy-Benutzer."""
    if user.rolle not in STAFF_ROLLEN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Kein Zugriff auf die Admin-API",
        )
    return user


def require_super_admin(user: User = Depends(get_current_user)) -> User:
    """Erlaube nur SUPER_ADMIN (403 sonst)."""
    if user.rolle != BenutzerRolle.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Nur Super-Admin darf diese Aktion ausführen",
        )
    return user
