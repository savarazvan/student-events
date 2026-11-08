import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import (
    GlobalRole,
    Organization,
    OrganizationMember,
    OrgRole,
    User,
)


@pytest.mark.asyncio
async def test_create_organization_as_super_admin(
    async_client: AsyncClient,
    admin_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    response = await async_client.post(
        "/api/v1/admin/organizations",
        headers=admin_headers,
        json={
            "name": "Student Volunteers",
            "description": "Volunteer organization",
            "contact_email": "contact@example.com",
        },
    )

    assert response.status_code in {200, 201}
    payload = response.json()
    assert payload["name"] == "Student Volunteers"
    assert payload["description"] == "Volunteer organization"
    assert payload["contact_email"] == "contact@example.com"

    organization = await db_session.scalar(
        select(Organization).where(Organization.name == "Student Volunteers")
    )
    assert organization is not None
    assert str(organization.id) == payload["id"]


@pytest.mark.asyncio
async def test_create_organization_as_regular_user_forbidden(
    async_client: AsyncClient,
    user_headers: dict[str, str],
) -> None:
    response = await async_client.post(
        "/api/v1/admin/organizations",
        headers=user_headers,
        json={
            "name": "Forbidden Organization",
            "description": None,
            "contact_email": "contact@example.com",
        },
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_list_organizations_as_admin(
    async_client: AsyncClient,
    admin_headers: dict[str, str],
    test_organization: Organization,
) -> None:
    response = await async_client.get(
        "/api/v1/admin/organizations",
        headers=admin_headers,
    )

    assert response.status_code == 200
    organizations = response.json()
    assert isinstance(organizations, list)
    assert any(
        organization["id"] == str(test_organization.id)
        and organization["name"] == test_organization.name
        for organization in organizations
    )


@pytest.mark.asyncio
async def test_assign_org_member(
    async_client: AsyncClient,
    admin_headers: dict[str, str],
    db_session: AsyncSession,
    test_user: User,
    test_organization: Organization,
) -> None:
    response = await async_client.post(
        f"/api/v1/admin/organizations/{test_organization.id}/members",
        headers=admin_headers,
        json={
            "user_id": str(test_user.id),
            "role": OrgRole.ORGANIZER.value,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["user_id"] == str(test_user.id)
    assert payload["organization_id"] == str(test_organization.id)
    assert payload["role_in_org"] == OrgRole.ORGANIZER.value

    membership = await db_session.scalar(
        select(OrganizationMember).where(
            OrganizationMember.user_id == test_user.id,
            OrganizationMember.organization_id == test_organization.id,
        )
    )
    assert membership is not None
    assert membership.role_in_org == OrgRole.ORGANIZER


@pytest.mark.asyncio
async def test_update_user_global_role(
    async_client: AsyncClient,
    admin_headers: dict[str, str],
    db_session: AsyncSession,
    test_user: User,
) -> None:
    response = await async_client.patch(
        f"/api/v1/admin/users/{test_user.id}/global-role",
        headers=admin_headers,
        json={"global_role": GlobalRole.SUPER_ADMIN.value},
    )

    assert response.status_code == 200
    assert response.json()["id"] == str(test_user.id)
    assert response.json()["global_role"] == GlobalRole.SUPER_ADMIN.value

    await db_session.refresh(test_user)
    assert test_user.global_role == GlobalRole.SUPER_ADMIN
