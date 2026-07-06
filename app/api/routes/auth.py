"""Authentication Routes - Login, Logout, User Info."""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_super_admin
from app.db.base import get_db
from app.models.enums import BenutzerRolle
from app.models.models import User
from app.services.auth_service import AuthService, TokenService

router = APIRouter(prefix="/auth", tags=["Authentication"])


class LoginRequest(BaseModel):
    """Login Request."""
    email: str
    password: str


class LoginResponse(BaseModel):
    """Login Response."""
    access_token: str
    token_type: str
    user: dict


class UserResponse(BaseModel):
    """User Info Response."""
    id: int
    email: str
    vorname: str
    nachname: str
    rolle: str
    aktiv: bool


@router.post("/login", response_model=LoginResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    """Login mit Email + Passwort."""
    user = AuthService.authenticate_user(db, req.email, req.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Erstelle JWT Token
    token_data = {
        "sub": str(user.id),
        "email": user.email,
        "rolle": user.rolle.value,
        "vorname": user.vorname,
        "nachname": user.nachname,
    }
    access_token = TokenService.create_access_token(data=token_data)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "vorname": user.vorname,
            "nachname": user.nachname,
            "rolle": user.rolle.value,
        },
    }


@router.get("/me", response_model=UserResponse)
def get_me(user: User = Depends(get_current_user)):
    """Get aktiven Benutzer-Info (benötigt Auth-Header)."""
    return {
        "id": user.id,
        "email": user.email,
        "vorname": user.vorname,
        "nachname": user.nachname,
        "rolle": user.rolle.value,
        "aktiv": user.aktiv,
    }


@router.post("/register", response_model=UserResponse)
def register_user(
    email: str,
    password: str,
    vorname: str,
    nachname: str,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_super_admin),
):
    """Registriere neuen Benutzer (nur SUPER_ADMIN kann das tun!)."""
    existing = AuthService.get_user_by_email(db, email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    user = AuthService.create_user(
        db,
        email=email,
        password=password,
        vorname=vorname,
        nachname=nachname,
        rolle=BenutzerRolle.BENUTZER,
    )

    return {
        "id": user.id,
        "email": user.email,
        "vorname": user.vorname,
        "nachname": user.nachname,
        "rolle": user.rolle.value,
        "aktiv": user.aktiv,
    }
