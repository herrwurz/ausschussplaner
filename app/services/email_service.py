"""Email-Versand für Einladungen."""
from datetime import datetime, timedelta
import secrets

from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from pydantic import EmailStr

from app.core.config import get_settings

settings = get_settings()


def generate_invite_token() -> tuple[str, datetime]:
    """Generiert einen Einmal-Token mit 48h Gültigkeit."""
    token = secrets.token_urlsafe(32)
    expires = datetime.utcnow() + timedelta(hours=48)
    return token, expires


async def send_invitation_email(email: EmailStr, invite_token: str, person_name: str):
    """Sendet eine Einladungs-Email mit Password-Set-Link."""
    set_password_url = f"http://localhost:5173/person/set-password?token={invite_token}"

    message = MessageSchema(
        subject="AusschussPlaner — Passwort setzen",
        recipients=[email],
        body=f"""
        <h2>Willkommen bei AusschussPlaner!</h2>
        <p>Hallo {person_name},</p>
        <p>Du wurdest zum AusschussPlaner eingeladen. Bitte setze dein Passwort:</p>
        <p><a href="{set_password_url}">Passwort setzen</a></p>
        <p><strong>Hinweis:</strong> Der Link ist 48 Stunden lang gültig.</p>
        """,
        subtype="html"
    )

    try:
        config = ConnectionConfig(
            mail_from=settings.smtp_from,
            mail_password=settings.smtp_password,
            mail_port=settings.smtp_port,
            mail_server=settings.smtp_server,
            mail_starttls=True,
            mail_ssl_tls=False,
            use_credentials=True,
            validate_certs=True
        )
        fm = FastMail(config)
        await fm.send_message(message)
        return True
    except Exception as e:
        print(f"❌ Email-Fehler: {e}")
        return False
