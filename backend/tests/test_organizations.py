"""Public organization directory, org-admin self-service and super-admin user search."""

import pytest
from sqlalchemy import select

from app.models.models import EventTask, OrgRole
from tests.test_attendance import add_member, make_event, make_user

pytestmark = pytest.mark.asyncio


async def test_public_organization_directory(async_client, test_organization):
    response = await async_client.get("/api/v1/organizations")
    assert response.status_code == 200
    assert [org["name"] for org in response.json()] == ["Test Organization"]

    response = await async_client.get(f"/api/v1/organizations/{test_organization.id}")
    assert response.status_code == 200
    assert response.json()["id"] == str(test_organization.id)


async def test_org_admin_manages_members_by_email(async_client, db_session, test_organization):
    org_admin, admin_headers = await make_user(async_client, db_session, "lead@example.com")
    await add_member(db_session, org_admin, test_organization, OrgRole.ADMIN)
    student, _ = await make_user(async_client, db_session, "newbie@example.com")
    base = f"/api/v1/organizations/{test_organization.id}/members"

    response = await async_client.post(
        base, json={"email": " NewBie@Example.com ", "role": "MEMBER"}, headers=admin_headers
    )
    assert response.status_code == 200
    assert response.json() == {
        "user_id": str(student.id),
        "full_name": "Newbie",
        "email": "newbie@example.com",
        "role": "MEMBER",
    }

    response = await async_client.patch(
        f"{base}/{student.id}", json={"role": "ORGANIZER"}, headers=admin_headers
    )
    assert response.status_code == 200
    assert response.json()["role"] == "ORGANIZER"

    response = await async_client.get(base, headers=admin_headers)
    assert {m["email"]: m["role"] for m in response.json()} == {
        "lead@example.com": "ORG_ADMIN",
        "newbie@example.com": "ORGANIZER",
    }

    response = await async_client.delete(f"{base}/{student.id}", headers=admin_headers)
    assert response.status_code == 204
    response = await async_client.get(base, headers=admin_headers)
    assert [m["email"] for m in response.json()] == ["lead@example.com"]


async def test_add_member_unknown_email(async_client, db_session, test_organization):
    org_admin, headers = await make_user(async_client, db_session, "lead@example.com")
    await add_member(db_session, org_admin, test_organization, OrgRole.ADMIN)
    response = await async_client.post(
        f"/api/v1/organizations/{test_organization.id}/members",
        json={"email": "ghost@example.com", "role": "MEMBER"},
        headers=headers,
    )
    assert response.status_code == 404


async def test_organizer_cannot_manage_members(
    async_client, organizer_membership, user_headers, test_organization
):
    base = f"/api/v1/organizations/{test_organization.id}/members"
    response = await async_client.post(
        base, json={"email": "student@example.com", "role": "ORG_ADMIN"}, headers=user_headers
    )
    assert response.status_code == 403
    # ...but members of any role can see the team list.
    response = await async_client.get(base, headers=user_headers)
    assert response.status_code == 200


async def test_outsider_cannot_list_members(async_client, user_headers, test_organization):
    response = await async_client.get(
        f"/api/v1/organizations/{test_organization.id}/members", headers=user_headers
    )
    assert response.status_code == 403


async def test_last_org_admin_cannot_leave_or_be_demoted(
    async_client, db_session, test_organization
):
    org_admin, headers = await make_user(async_client, db_session, "lead@example.com")
    await add_member(db_session, org_admin, test_organization, OrgRole.ADMIN)
    base = f"/api/v1/organizations/{test_organization.id}/members/{org_admin.id}"

    response = await async_client.patch(base, json={"role": "MEMBER"}, headers=headers)
    assert response.status_code == 409
    response = await async_client.delete(base, headers=headers)
    assert response.status_code == 409

    second, _ = await make_user(async_client, db_session, "second@example.com")
    await add_member(db_session, second, test_organization, OrgRole.ADMIN)
    response = await async_client.patch(base, json={"role": "MEMBER"}, headers=headers)
    assert response.status_code == 200


async def test_removing_member_unassigns_their_tasks(
    async_client, db_session, test_admin, admin_headers, test_organization
):
    member, _ = await make_user(async_client, db_session, "helper@example.com")
    await add_member(db_session, member, test_organization, OrgRole.MEMBER)
    event = await make_event(db_session, test_organization, test_admin)
    event_id = event.id
    response = await async_client.post(
        f"/api/v1/events/{event_id}/tasks",
        json={"title": "Check-in desk", "assignee_id": str(member.id)},
        headers=admin_headers,
    )
    assert response.status_code == 201

    response = await async_client.delete(
        f"/api/v1/organizations/{test_organization.id}/members/{member.id}",
        headers=admin_headers,
    )
    assert response.status_code == 204
    db_session.expire_all()
    task = await db_session.scalar(select(EventTask).where(EventTask.event_id == event_id))
    assert task.assignee_id is None


async def test_org_admin_updates_profile(async_client, db_session, test_organization):
    org_admin, headers = await make_user(async_client, db_session, "lead@example.com")
    await add_member(db_session, org_admin, test_organization, OrgRole.ADMIN)
    response = await async_client.patch(
        f"/api/v1/organizations/{test_organization.id}",
        json={"description": "We build things", "contact_email": "Hello@Org.ro"},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["description"] == "We build things"
    assert response.json()["contact_email"] == "hello@org.ro"


async def test_profile_update_rejects_duplicate_name_and_organizers(
    async_client, db_session, admin_headers, organizer_membership, user_headers, test_organization
):
    response = await async_client.post(
        "/api/v1/admin/organizations",
        json={"name": "Other Org", "contact_email": "o@org.ro"},
        headers=admin_headers,
    )
    assert response.status_code == 201
    url = f"/api/v1/organizations/{test_organization.id}"
    response = await async_client.patch(url, json={"name": "Other Org"}, headers=admin_headers)
    assert response.status_code == 400
    response = await async_client.patch(url, json={"description": "x"}, headers=user_headers)
    assert response.status_code == 403


async def test_super_admin_searches_users(async_client, admin_headers, user_headers, test_user):
    response = await async_client.get("/api/v1/admin/users?search=STUDENT", headers=admin_headers)
    assert response.status_code == 200
    assert [u["email"] for u in response.json()] == ["student@example.com"]

    response = await async_client.get("/api/v1/admin/users?search=test", headers=admin_headers)
    assert len(response.json()) == 2

    response = await async_client.get("/api/v1/admin/users", headers=user_headers)
    assert response.status_code == 403
