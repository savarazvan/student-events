"""Event organizing team: task planning, assignment rules and permissions."""

from datetime import datetime, timedelta, timezone

import pytest

from app.models.models import EventStatus, OrgRole
from tests.test_attendance import add_member, make_event, make_user

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def team(async_client, db_session, test_admin, test_organization):
    """An event plus an organizer, a member and an outsider of the organizing org."""
    organizer, organizer_headers = await make_user(async_client, db_session, "org@example.com")
    await add_member(db_session, organizer, test_organization, OrgRole.ORGANIZER)
    member, member_headers = await make_user(async_client, db_session, "member@example.com")
    await add_member(db_session, member, test_organization, OrgRole.MEMBER)
    outsider, outsider_headers = await make_user(async_client, db_session, "out@example.com")
    event = await make_event(db_session, test_organization, test_admin)
    return {
        "event": event,
        "organizer": (organizer, organizer_headers),
        "member": (member, member_headers),
        "outsider": (outsider, outsider_headers),
    }


async def create_task(client, event, headers, **payload):
    return await client.post(f"/api/v1/events/{event.id}/tasks", json=payload, headers=headers)


async def test_organizer_plans_and_assigns_tasks(async_client, team):
    event = team["event"]
    member, member_headers = team["member"]
    _, organizer_headers = team["organizer"]
    due = (datetime.now(timezone.utc) + timedelta(hours=5)).isoformat()

    response = await create_task(
        async_client,
        event,
        organizer_headers,
        title="Check-in desk",
        description="Scan tickets at the entrance",
        assignee_id=str(member.id),
        due_at=due,
    )
    assert response.status_code == 201
    task = response.json()
    assert task["assignee_name"] == "Member" and task["status"] == "TODO"

    notifications = (
        await async_client.get("/api/v1/me/notifications", headers=member_headers)
    ).json()["items"]
    assert notifications[0]["type"] == "TASK_ASSIGNED"
    assert "Check-in desk" in notifications[0]["message"]

    response = await async_client.get(f"/api/v1/events/{event.id}/tasks", headers=member_headers)
    assert response.status_code == 200
    assert [t["title"] for t in response.json()] == ["Check-in desk"]

    response = await async_client.get("/api/v1/me/tasks", headers=member_headers)
    assert [(t["title"], t["event"]["id"]) for t in response.json()] == [
        ("Check-in desk", str(event.id))
    ]


async def test_task_assignee_must_belong_to_organization(async_client, team):
    outsider, _ = team["outsider"]
    _, organizer_headers = team["organizer"]
    response = await create_task(
        async_client, team["event"], organizer_headers, title="Photos", assignee_id=str(outsider.id)
    )
    assert response.status_code == 422


async def test_members_cannot_plan_and_outsiders_cannot_see(async_client, team):
    event = team["event"]
    _, member_headers = team["member"]
    _, outsider_headers = team["outsider"]
    response = await create_task(async_client, event, member_headers, title="Snacks")
    assert response.status_code == 403
    response = await async_client.get(f"/api/v1/events/{event.id}/tasks", headers=outsider_headers)
    assert response.status_code == 403


async def test_assignee_can_only_change_status(async_client, db_session, team, test_organization):
    event = team["event"]
    member, member_headers = team["member"]
    _, organizer_headers = team["organizer"]
    other, other_headers = await make_user(async_client, db_session, "other@example.com")
    await add_member(db_session, other, test_organization, OrgRole.MEMBER)
    task_id = (
        await create_task(
            async_client, event, organizer_headers, title="Snacks", assignee_id=str(member.id)
        )
    ).json()["id"]
    url = f"/api/v1/events/{event.id}/tasks/{task_id}"

    response = await async_client.patch(url, json={"status": "IN_PROGRESS"}, headers=member_headers)
    assert response.status_code == 200 and response.json()["status"] == "IN_PROGRESS"

    response = await async_client.patch(url, json={"title": "Pizza"}, headers=member_headers)
    assert response.status_code == 403
    response = await async_client.patch(url, json={"status": "DONE"}, headers=other_headers)
    assert response.status_code == 403

    # Done tasks drop out of "my tasks" unless requested.
    await async_client.patch(url, json={"status": "DONE"}, headers=member_headers)
    assert (await async_client.get("/api/v1/me/tasks", headers=member_headers)).json() == []
    response = await async_client.get("/api/v1/me/tasks?include_done=true", headers=member_headers)
    assert len(response.json()) == 1


async def test_reassign_notifies_new_assignee_and_delete(
    async_client, db_session, team, test_organization
):
    event = team["event"]
    member, _ = team["member"]
    _, organizer_headers = team["organizer"]
    second, second_headers = await make_user(async_client, db_session, "second@example.com")
    await add_member(db_session, second, test_organization, OrgRole.MEMBER)
    task_id = (
        await create_task(
            async_client, event, organizer_headers, title="Sound", assignee_id=str(member.id)
        )
    ).json()["id"]
    url = f"/api/v1/events/{event.id}/tasks/{task_id}"

    response = await async_client.patch(
        url, json={"assignee_id": str(second.id)}, headers=organizer_headers
    )
    assert response.status_code == 200 and response.json()["assignee_name"] == "Second"
    items = (await async_client.get("/api/v1/me/notifications", headers=second_headers)).json()
    assert items["items"][0]["type"] == "TASK_ASSIGNED"

    response = await async_client.patch(url, json={"title": None}, headers=organizer_headers)
    assert response.status_code == 422

    response = await async_client.delete(url, headers=organizer_headers)
    assert response.status_code == 204
    response = await async_client.delete(url, headers=organizer_headers)
    assert response.status_code == 404


async def test_no_new_tasks_on_finished_events(async_client, db_session, team):
    event = team["event"]
    _, organizer_headers = team["organizer"]
    event.status = EventStatus.COMPLETED
    await db_session.commit()
    response = await create_task(async_client, event, organizer_headers, title="Late")
    assert response.status_code == 409
