"""Tests for admin list filters (aktiv/inaktiv)."""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db.base import get_db, Base, engine
from app.models.models import Person, Ausschuss, Jahresplan, Gemeinderatsperiode
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session


@pytest.fixture(scope="function")
def db_session():
    """Create an in-memory SQLite database for testing."""
    from sqlalchemy.pool import StaticPool

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    db = SessionLocal()
    yield db
    db.close()


@pytest.fixture
def client(db_session):
    """FastAPI test client with override."""

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def setup_test_data(db: Session):
    """Create test data with active and inactive items."""
    # Create persons
    p1 = Person(vorname="Active", nachname="Person1", aktiv=True)
    p2 = Person(vorname="Inactive", nachname="Person2", aktiv=False)
    p3 = Person(vorname="Active", nachname="Person3", aktiv=True)
    db.add_all([p1, p2, p3])
    db.commit()

    # Create ausschuesse
    from app.models.enums import AusschussTyp
    a1 = Ausschuss(name="Active Committee", typ=AusschussTyp.STANDARD, aktiv=True)
    a2 = Ausschuss(name="Inactive Committee", typ=AusschussTyp.STANDARD, aktiv=False)
    db.add_all([a1, a2])
    db.commit()

    # Create jahrespläne
    j1 = Jahresplan(jahr=2025, bezeichnung="Active Plan", aktiv=True)
    j2 = Jahresplan(jahr=2024, bezeichnung="Inactive Plan", aktiv=False)
    db.add_all([j1, j2])
    db.commit()

    # Create perioden
    g1 = Gemeinderatsperiode(name="P1", start_jahr=2020, end_jahr=2025, aktiv=True)
    g2 = Gemeinderatsperiode(name="P2", start_jahr=2026, end_jahr=2030, aktiv=False)
    db.add_all([g1, g2])
    db.commit()


def test_personen_filter_all(client, db_session):
    """Test /admin/personen with filter=all shows all persons."""
    setup_test_data(db_session)

    # Set login cookie
    client.cookies.set("admin_session", "logged_in")

    response = client.get("/admin/personen?filter=all")
    assert response.status_code == 200
    assert "Personen (3)" in response.text
    assert "Active" in response.text
    assert "Inactive" in response.text


def test_personen_filter_active(client, db_session):
    """Test /admin/personen with filter=active shows only active persons."""
    setup_test_data(db_session)

    # Set login cookie
    client.cookies.set("admin_session", "logged_in")

    response = client.get("/admin/personen?filter=active")
    assert response.status_code == 200
    assert "Personen (2)" in response.text
    # Should show active person count (2), but not inactive details


def test_personen_filter_inactive(client, db_session):
    """Test /admin/personen with filter=inactive shows only inactive persons."""
    setup_test_data(db_session)

    # Set login cookie
    client.cookies.set("admin_session", "logged_in")

    response = client.get("/admin/personen?filter=inactive")
    assert response.status_code == 200
    assert "Personen (1)" in response.text


def test_ausschuesse_filter_all(client, db_session):
    """Test /admin/ausschuesse with filter=all shows all committees."""
    setup_test_data(db_session)

    # Set login cookie
    client.cookies.set("admin_session", "logged_in")

    response = client.get("/admin/ausschuesse?filter=all")
    assert response.status_code == 200
    assert "Ausschuesse (2)" in response.text
    assert "Active Committee" in response.text
    assert "Inactive Committee" in response.text


def test_ausschuesse_filter_active(client, db_session):
    """Test /admin/ausschuesse with filter=active shows only active committees."""
    setup_test_data(db_session)

    # Set login cookie
    client.cookies.set("admin_session", "logged_in")

    response = client.get("/admin/ausschuesse?filter=active")
    assert response.status_code == 200
    assert "Ausschuesse (1)" in response.text
    assert "Active Committee" in response.text


def test_ausschuesse_filter_inactive(client, db_session):
    """Test /admin/ausschuesse with filter=inactive shows only inactive committees."""
    setup_test_data(db_session)

    # Set login cookie
    client.cookies.set("admin_session", "logged_in")

    response = client.get("/admin/ausschuesse?filter=inactive")
    assert response.status_code == 200
    assert "Ausschuesse (1)" in response.text
    assert "Inactive Committee" in response.text


def test_jahrespläne_filter_all(client, db_session):
    """Test /admin/jahrespläne with filter=all shows all plans."""
    setup_test_data(db_session)

    # Set login cookie
    client.cookies.set("admin_session", "logged_in")

    response = client.get("/admin/jahrespläne?filter=all")
    assert response.status_code == 200
    assert "Jahrespläne (2)" in response.text
    assert "Active Plan" in response.text
    assert "Inactive Plan" in response.text


def test_jahrespläne_filter_active(client, db_session):
    """Test /admin/jahrespläne with filter=active shows only active plans."""
    setup_test_data(db_session)

    # Set login cookie
    client.cookies.set("admin_session", "logged_in")

    response = client.get("/admin/jahrespläne?filter=active")
    assert response.status_code == 200
    assert "Jahrespläne (1)" in response.text
    assert "Active Plan" in response.text


def test_jahrespläne_filter_inactive(client, db_session):
    """Test /admin/jahrespläne with filter=inactive shows only inactive plans."""
    setup_test_data(db_session)

    # Set login cookie
    client.cookies.set("admin_session", "logged_in")

    response = client.get("/admin/jahrespläne?filter=inactive")
    assert response.status_code == 200
    assert "Jahrespläne (1)" in response.text
    assert "Inactive Plan" in response.text


def test_personen_default_filter(client, db_session):
    """Test /admin/personen default filter is 'all'."""
    setup_test_data(db_session)

    # Set login cookie
    client.cookies.set("admin_session", "logged_in")

    response = client.get("/admin/personen")
    assert response.status_code == 200
    assert "Personen (3)" in response.text


def test_ausschuesse_default_filter(client, db_session):
    """Test /admin/ausschuesse default filter is 'all'."""
    setup_test_data(db_session)

    # Set login cookie
    client.cookies.set("admin_session", "logged_in")

    response = client.get("/admin/ausschuesse")
    assert response.status_code == 200
    assert "Ausschuesse (2)" in response.text
