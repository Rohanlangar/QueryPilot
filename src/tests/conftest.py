"""
QueryPilot — Test Fixtures and Configuration

Sets up an in-memory async SQLite database, overrides the get_db dependency,
and provides authenticated test clients and mock objects.
"""

import asyncio
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.config import settings
from app.db.database import Base, get_db
import app.models  # Register all models
from app.main import app
from app.core.security import hash_password, create_access_token
from app.models.user import User
from app.models.rbac import Role


# In-memory SQLite for testing
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestingSessionLocal = async_sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False
)


@pytest_asyncio.fixture(scope="function")
async def db_session():
    """Create a fresh database schema for each test function."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestingSessionLocal() as session:
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession):
    """FastAPI test client with database dependency overridden."""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def test_roles(db_session: AsyncSession):
    """Ensure standard roles exist in the test database."""
    roles = [
        Role(name="admin", description="Admin role", can_manage_users=True, can_manage_connections=True, can_manage_policies=True, can_view_audit=True),
        Role(name="analyst", description="Analyst role", can_manage_users=False, can_manage_connections=True, can_manage_policies=False, can_view_audit=False),
        Role(name="viewer", description="Viewer role", can_manage_users=False, can_manage_connections=False, can_manage_policies=False, can_view_audit=False),
    ]
    for r in roles:
        db_session.add(r)
    await db_session.commit()
    return roles


@pytest_asyncio.fixture(scope="function")
async def test_user(db_session: AsyncSession, test_roles):
    """Create a standard analyst user."""
    user = User(
        email="analyst@querypilot.ai",
        username="analyst",
        hashed_password=hash_password("Password123!"),
        full_name="Test Analyst",
        role="analyst",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture(scope="function")
async def test_admin(db_session: AsyncSession, test_roles):
    """Create an admin user."""
    admin = User(
        email="admin@querypilot.ai",
        username="admin",
        hashed_password=hash_password("AdminPass123!"),
        full_name="Test Admin",
        role="admin",
        is_active=True,
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    return admin


@pytest.fixture
def auth_headers(test_user: User):
    """Auth headers for analyst user."""
    token = create_access_token({"sub": test_user.id, "role": test_user.role, "email": test_user.email})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_headers(test_admin: User):
    """Auth headers for admin user."""
    token = create_access_token({"sub": test_admin.id, "role": test_admin.role, "email": test_admin.email})
    return {"Authorization": f"Bearer {token}"}
