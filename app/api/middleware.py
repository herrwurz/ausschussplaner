"""Auth Middleware - Überprüfe Benutzer-Rollen."""
from fastapi import HTTPException, status, Request
from app.services.auth_service import TokenService
from app.db.base import SessionLocal
from app.models.models import User


def get_token_from_header(request: Request) -> str:
    """Extrahiere Token aus Authorization Header."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    return auth_header.split(" ")[1]


def verify_token(token: str) -> dict:
    """Verifiziere JWT Token."""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Kein Token",
        )

    payload = TokenService.decode_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Ungültiger Token",
        )

    return payload


def get_current_user(token: str) -> User:
    """Hole aktuellen Benutzer aus Token."""
    payload = verify_token(token)
    user_id = int(payload["sub"])

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Benutzer nicht gefunden",
            )
        return user
    finally:
        db.close()


def require_admin(token: str) -> User:
    """Überprüfe, dass Benutzer Admin ist."""
    user = get_current_user(token)
    if user.rolle.value not in ["super_admin", "benutzer"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Nur Admins haben Zugriff",
        )
    return user


def require_super_admin(token: str) -> User:
    """Überprüfe, dass Benutzer Super Admin ist."""
    user = get_current_user(token)
    if user.rolle.value != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Nur Super Admins haben Zugriff",
        )
    return user


def require_obmann(token: str) -> User:
    """Überprüfe, dass Benutzer Obmann ist."""
    user = get_current_user(token)
    if user.rolle.value != "obmann":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Nur Obmänner haben Zugriff",
        )
    return user
