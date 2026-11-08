from collections.abc import AsyncIterator
from uuid import UUID

import pytest
import pytest_asyncio
from fastapi import APIRouter, Depends
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.deps import require_global_role, require_org_role
from app.core.database import Base, get_db
from app.core.security import hash_password
from app.main import app
from app.models.models import GlobalRole, Organization, OrganizationMember, OrgRole, User

TEST_PASSWORD = "test-password-123"

_test_router = APIRouter()


@_test_router.get(
    "/__test__/rbac/global-admin",
    dependencies=[Depends(require_global_role(GlobalRole.SUPER_ADMIN))],
)
async def global_admin_action() -> dict[str, str]:
    return {"result": "allowed"}


@_test_router.get("/__test__/rbac/organizations/{org_id}/organizer")
async def organizer_action(
    org_id: UUID,
    current_user: User = Depends(
        require_org_role("org_id", [OrgRole.ORGANIZER])
    ),
) -> dict[str, str]:
    return {
        "result": "allowed",
        "user_id": str(current_user.id),
        "organization_id": str(org_id),
    }


app.include_router(_test_router)


@pytest.fixture(autouse=True)
def secret_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SECRET_KEY", "pytest-only-secret-key-with-32-bytes-minimum")


@pytest_asyncio.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
    )
    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        try:
            yield session
        finally:
            await session.rollback()

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncIterator[AsyncClient]:
    async def override_get_db() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest_asyncio.fixture
async def async_client(client: AsyncClient) -> AsyncClient:
    return client


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    user = User(
        email="student@example.com",
        hashed_password=hash_password(TEST_PASSWORD),
        full_name="Test Student",
        global_role=GlobalRole.USER,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def user_headers(
    client: AsyncClient,
    test_user: User,
) -> dict[str, str]:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": test_user.email, "password": TEST_PASSWORD},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def test_admin(db_session: AsyncSession) -> User:
    admin = User(
        email="admin@example.com",
        hashed_password=hash_password(TEST_PASSWORD),
        full_name="Test Administrator",
        global_role=GlobalRole.SUPER_ADMIN,
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    return admin


@pytest_asyncio.fixture
async def admin_headers(
    client: AsyncClient,
    test_admin: User,
) -> dict[str, str]:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": test_admin.email, "password": TEST_PASSWORD},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def test_organization(db_session: AsyncSession) -> Organization:
    organization = Organization(name="Test Organization")
    db_session.add(organization)
    await db_session.commit()
    await db_session.refresh(organization)
    return organization


@pytest_asyncio.fixture
async def organizer_membership(
    db_session: AsyncSession,
    test_user: User,
    test_organization: Organization,
) -> OrganizationMember:
    membership = OrganizationMember(
        user_id=test_user.id,
        organization_id=test_organization.id,
        role_in_org=OrgRole.ORGANIZER,
    )
    db_session.add(membership)
    await db_session.commit()
    await db_session.refresh(membership)
    return membership
