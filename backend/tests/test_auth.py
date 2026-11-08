import pytest
from httpx import AsyncClient

from app.models.models import GlobalRole, User

TEST_PASSWORD = "test-password-123"

@pytest.mark.asyncio
async def test_register_user_success(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "new.student@example.com",
            "password": "student-password-123",
            "full_name": "New Student",
        },
    )

    assert response.status_code in {200, 201}
    payload = response.json()
    assert payload["email"] == "new.student@example.com"
    assert payload["full_name"] == "New Student"
    assert payload["global_role"] == GlobalRole.USER.value
    assert payload["is_active"] is True
    assert payload["organization_memberships"] == []
    assert "hashed_password" not in payload
    assert "id" in payload


@pytest.mark.asyncio
async def test_register_duplicate_email(
    client: AsyncClient,
    test_user: User,
) -> None:
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": test_user.email,
            "password": "different-password-123",
            "full_name": "Duplicate Student",
        },
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_login_success(
    client: AsyncClient,
    test_user: User,
) -> None:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": test_user.email, "password": TEST_PASSWORD},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["access_token"]
    assert payload["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(
    client: AsyncClient,
    test_user: User,
) -> None:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": test_user.email, "password": "wrong-password-123"},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_me_unauthorized(client: AsyncClient) -> None:
    response = await client.get("/api/v1/auth/me")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_me_authenticated(
    client: AsyncClient,
    test_user: User,
    user_headers: dict[str, str],
) -> None:
    response = await client.get("/api/v1/auth/me", headers=user_headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == str(test_user.id)
    assert payload["email"] == test_user.email
    assert payload["full_name"] == test_user.full_name
    assert payload["global_role"] == GlobalRole.USER.value
    assert payload["organization_memberships"] == []
