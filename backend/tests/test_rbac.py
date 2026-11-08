import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.models.models import GlobalRole, Organization, OrganizationMember, OrgRole, User


@pytest.mark.asyncio
async def test_global_role_super_admin_protection(
    client: AsyncClient,
    user_headers: dict[str, str],
    admin_headers: dict[str, str],
) -> None:
    path = "/__test__/rbac/global-admin"

    user_response = await client.get(path, headers=user_headers)
    admin_response = await client.get(path, headers=admin_headers)

    assert user_response.status_code == 403
    assert admin_response.status_code == 200


@pytest.mark.asyncio
async def test_org_role_organizer_permission(
    client: AsyncClient,
    db_session: AsyncSession,
    user_headers: dict[str, str],
    admin_headers: dict[str, str],
    test_user: User,
    test_organization: Organization,
    organizer_membership: OrganizationMember,
) -> None:
    assert organizer_membership.role_in_org == OrgRole.ORGANIZER
    path = f"/__test__/rbac/organizations/{test_organization.id}/organizer"

    authorized_response = await client.get(path, headers=user_headers)
    assert authorized_response.status_code == 200
    assert authorized_response.json()["user_id"] == str(test_user.id)

    admin_response = await client.get(path, headers=admin_headers)
    assert admin_response.status_code == 200

    non_member = User(
        email="nonmember@example.com",
        hashed_password=hash_password("non-member-password-123"),
        full_name="Non-member Student",
        global_role=GlobalRole.USER,
    )
    db_session.add(non_member)
    await db_session.commit()

    non_member_token = create_access_token(non_member.id)
    non_member_response = await client.get(
        path,
        headers={"Authorization": f"Bearer {non_member_token}"},
    )

    assert non_member_response.status_code == 403
