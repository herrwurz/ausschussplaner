"""Authentication Service - Password Hashing & JWT Token Management."""
from datetime import timedelta
from typing import Optional

from bcrypt import gensalt, hashpw, checkpw
from sqlalchemy.orm import Session

from app.models.models import User
from app.models.enums import BenutzerRolle


class PasswordService:
    """Passwort-Hashing mit bcrypt."""

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash ein Passwort."""
        salt = gensalt(rounds=12)
        return hashpw(password.encode("utf-8"), salt).decode("utf-8")

    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        """Verifiziere ein Passwort gegen den Hash."""
        return checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


class TokenService:
    """JWT Token Management — nutzt dasselbe Secret wie Person-Portal."""

    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 24 * 60  # 24 Stunden

    @classmethod
    def create_access_token(
        cls,
        data: dict,
        expires_delta: Optional[timedelta] = None,
    ) -> str:
        """Erstelle einen JWT Access Token."""
        from app.core.security import create_access_token
        return create_access_token(data, expires_delta)

    @classmethod
    def decode_token(cls, token: str) -> Optional[dict]:
        """Dekodiere einen JWT Token."""
        from app.core.security import decode_token
        return decode_token(token)


class AuthService:
    """Benutzer-Authentifizierung."""

    @staticmethod
    def create_user(
        db: Session,
        email: str,
        password: str,
        vorname: str,
        nachname: str,
        rolle: BenutzerRolle = BenutzerRolle.BENUTZER,
    ) -> User:
        """Erstelle einen neuen Benutzer."""
        password_hash = PasswordService.hash_password(password)
        user = User(
            email=email,
            password_hash=password_hash,
            vorname=vorname,
            nachname=nachname,
            rolle=rolle,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
        """Authentifiziere einen Benutzer mit Email + Passwort."""
        user = db.query(User).filter(User.email == email).first()
        if not user or not user.aktiv:
            return None
        if not PasswordService.verify_password(password, user.password_hash):
            return None
        return user

    @staticmethod
    def get_user_by_email(db: Session, email: str) -> Optional[User]:
        """Hole Benutzer nach Email."""
        return db.query(User).filter(User.email == email).first()

    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
        """Hole Benutzer nach ID."""
        return db.query(User).filter(User.id == user_id).first()
