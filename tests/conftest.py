"""Pytest-Fixtures: In-Memory-DB + TestClient."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_current_user
from app.db.base import Base, get_db
from app.main import app
from app.models.enums import BenutzerRolle
from app.models.models import User
from app.services.auth_service import PasswordService


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


def _make_staff(db_session) -> User:
    user = User(
        email="test-staff@ausschussplaner.local",
        password_hash=PasswordService.hash_password("test-staff-pass"),
        vorname="Test",
        nachname="Staff",
        rolle=BenutzerRolle.SUPER_ADMIN,
        aktiv=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def client(db_session):
    """Authentifizierter Staff-Client (Admin-APIs)."""
    staff = _make_staff(db_session)

    def override_get_db():
        yield db_session

    def override_user():
        return staff

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_user
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def anon_client(db_session):
    """Unauthentifizierter Client (für Auth-/401-Tests)."""
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    # kein get_current_user-Override
    yield TestClient(app)
    app.dependency_overrides.clear()
