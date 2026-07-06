"""Benutzer-Management Routes - CRUD für User."""
import json

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import require_super_admin
from app.db.base import get_db
from app.models.enums import BenutzerRolle
from app.models.models import User
from app.services.auth_service import AuthService, PasswordService

router = APIRouter(
    prefix="/users",
    tags=["Benutzerverwaltung"],
    dependencies=[Depends(require_super_admin)],
)


class UserCreateRequest(BaseModel):
    """User-Erstellung."""
    email: str
    vorname: str
    nachname: str
    rolle: str = "benutzer"


class UserUpdateRequest(BaseModel):
    """User-Update."""
    vorname: str = None
    nachname: str = None
    rolle: str = None
    aktiv: bool = None
    obmann_ausschuss_ids: list[int] = None


class UserOut(BaseModel):
    """User Output."""
    id: int
    email: str
    vorname: str
    nachname: str
    rolle: str
    aktiv: bool

    class Config:
        from_attributes = True


@router.get("", response_model=list)
def list_users(db: Session = Depends(get_db)):
    """Alle Benutzer auflisten."""
    users = db.query(User).all()
    return [
        {
            "id": u.id,
            "email": u.email,
            "vorname": u.vorname,
            "nachname": u.nachname,
            "rolle": u.rolle.value,
            "aktiv": u.aktiv,
            "obmann_ausschuss_ids": _parse_ausschuss_ids(u),
        }
        for u in users
    ]


def _parse_ausschuss_ids(user: User) -> list[int]:
    """Lese die JSON-Liste der Obmann-Ausschüsse (leer bei ungültigem Wert)."""
    try:
        return [int(i) for i in json.loads(user.obmann_ausschuss_ids or "[]")]
    except (TypeError, ValueError):
        return []


@router.post("", response_model=dict)
def create_user(
    req: UserCreateRequest,
    db: Session = Depends(get_db),
):
    """Neuen Benutzer erstellen (nur SUPER_ADMIN)."""
    existing = AuthService.get_user_by_email(db, req.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Benutzer mit dieser Email existiert bereits",
        )

    # Konvertiere rolle String zu Enum
    try:
        rolle_enum = BenutzerRolle(req.rolle.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ungültige Rolle. Erlaubte Werte: {', '.join([r.value for r in BenutzerRolle])}",
        ) from None

    # Generiere temporäres Passwort
    temp_password = f"Temp{req.email.split('@')[0]}123!"

    user = AuthService.create_user(
        db,
        email=req.email,
        password=temp_password,
        vorname=req.vorname,
        nachname=req.nachname,
        rolle=rolle_enum,
    )

    return {
        "id": user.id,
        "email": user.email,
        "vorname": user.vorname,
        "nachname": user.nachname,
        "rolle": user.rolle.value,
        "aktiv": user.aktiv,
        "temp_password": temp_password,
    }


@router.put("/{user_id}", response_model=dict)
def update_user(
    user_id: int,
    req: UserUpdateRequest,
    db: Session = Depends(get_db),
):
    """Benutzer aktualisieren (nur SUPER_ADMIN)."""
    user = AuthService.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Benutzer nicht gefunden",
        )

    if req.vorname:
        user.vorname = req.vorname
    if req.nachname:
        user.nachname = req.nachname
    if req.rolle:
        try:
            user.rolle = BenutzerRolle(req.rolle.lower())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ungültige Rolle. Erlaubte Werte: {', '.join([r.value for r in BenutzerRolle])}",
            ) from None
    if req.aktiv is not None:
        user.aktiv = req.aktiv
    if req.obmann_ausschuss_ids is not None:
        user.obmann_ausschuss_ids = json.dumps(req.obmann_ausschuss_ids)

    db.commit()
    db.refresh(user)

    return {
        "id": user.id,
        "email": user.email,
        "vorname": user.vorname,
        "nachname": user.nachname,
        "rolle": user.rolle.value,
        "aktiv": user.aktiv,
        "obmann_ausschuss_ids": _parse_ausschuss_ids(user),
    }


@router.delete("/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    """Benutzer löschen (nur SUPER_ADMIN)."""
    user = AuthService.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Benutzer nicht gefunden",
        )

    db.delete(user)
    db.commit()

    return {"message": "Benutzer gelöscht"}


@router.post("/{user_id}/reset-password")
def reset_password(user_id: int, db: Session = Depends(get_db)):
    """Passwort zurücksetzen (nur SUPER_ADMIN)."""
    user = AuthService.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Benutzer nicht gefunden",
        )

    # Generiere neues temporäres Passwort
    temp_password = "Reset" + str(user_id).zfill(4) + "!"

    user.password_hash = PasswordService.hash_password(temp_password)
    db.commit()

    return {
        "message": "Passwort zurückgesetzt",
        "temp_password": temp_password,
        "email": user.email,
    }
