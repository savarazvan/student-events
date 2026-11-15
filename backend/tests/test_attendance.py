"""Registration rules, tickets, QR check-in, attendance stats and event lifecycle."""

from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.models import (
    Event,
    EventCategory,
    EventRegistrationStatus,
    EventStatus,
    GlobalRole,
    Organization,
    OrganizationMember,
    OrgRole,
    Ticket,
    User,
)
from tests.conftest import TEST_PASSWORD

pytestmark = pytest.mark.asyncio


async def make_user(
    client: AsyncClient, db: AsyncSession, email: str
) -> tuple[User, dict[str, str]]:
    user = User(
        email=email,
        hashed_password=hash_password(TEST_PASSWORD),
        full_name=email.split("@")[0].title(),
        global_role=GlobalRole.USER,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    response = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": TEST_PASSWORD}
    )
    assert response.status_code == 200
    return user, {"Authorization": f"Bearer {response.json()['access_token']}"}


async def add_member(
    db: AsyncSession, user: User, organization: Organization, role: OrgRole
) -> None:
    db.add(OrganizationMember(user_id=user.id, organization_id=organization.id, role_in_org=role))
    await db.commit()


async def make_event(
    db: AsyncSession,
    organization: Organization,
    creator: User,
    *,
    status: EventStatus = EventStatus.PUBLISHED,
    starts_in: timedelta = timedelta(days=1),
    duration: timedelta = timedelta(hours=2),
    capacity: int = 10,
    registration_deadline: datetime | None = None,
) -> Event:
    start = datetime.now(timezone.utc) + starts_in
    event = Event(
        title="Attendance Test Event",
        location="UBB Main Building",
        start_time=start,
        end_time=start + duration,
        capacity=capacity,
        status=status,
        organization_id=organization.id,
        created_by_id=creator.id,
        registration_deadline=registration_deadline,
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event


async def register(client: AsyncClient, event: Event, headers: dict[str, str]):
    return await client.post(f"/api/v1/events/{event.id}/register", headers=headers)


async def ticket_token(client: AsyncClient, ticket_id: str, headers: dict[str, str]) -> str:
    response = await client.get(f"/api/v1/me/tickets/{ticket_id}", headers=headers)
    assert response.status_code == 200
    return response.json()["qr_token"]


# --- Registration rules -------------------------------------------------------


@pytest.mark.parametrize("status", [EventStatus.DRAFT, EventStatus.SUBMITTED, EventStatus.CANCELLED])
async def test_cannot_register_for_unpublished_event(
    async_client, db_session, user_headers, test_admin, test_organization, status
):
    event = await make_event(db_session, test_organization, test_admin, status=status)
    response = await register(async_client, event, user_headers)
    assert response.status_code == 409


async def test_cannot_register_after_deadline(
    async_client, db_session, user_headers, test_admin, test_organization
):
    event = await make_event(
        db_session,
        test_organization,
        test_admin,
        registration_deadline=datetime.now(timezone.utc) - timedelta(minutes=1),
    )
    response = await register(async_client, event, user_headers)
    assert response.status_code == 409
    assert "closed" in response.json()["detail"]


async def test_cannot_register_after_event_started(
    async_client, db_session, user_headers, test_admin, test_organization
):
    event = await make_event(
        db_session, test_organization, test_admin, starts_in=timedelta(minutes=-10)
    )
    response = await register(async_client, event, user_headers)
    assert response.status_code == 409


async def test_create_event_rejects_deadline_after_start(
    async_client, user_headers, test_organization, organizer_membership
):
    start = datetime.now(timezone.utc) + timedelta(days=2)
    response = await async_client.post(
        "/api/v1/events",
        headers=user_headers,
        json={
            "title": "Deadline",
            "location": "UBB",
            "start_time": start.isoformat(),
            "end_time": (start + timedelta(hours=1)).isoformat(),
            "capacity": 5,
            "organization_id": str(test_organization.id),
            "category": "WORKSHOP",
            "registration_deadline": (start + timedelta(minutes=1)).isoformat(),
        },
    )
    assert response.status_code == 422


# --- Tickets ------------------------------------------------------------------


async def test_ticket_lifecycle_with_waitlist(
    async_client, db_session, user_headers, test_user, test_admin, test_organization
):
    event = await make_event(db_session, test_organization, test_admin, capacity=1)
    other, other_headers = await make_user(async_client, db_session, "maria@ubbcluj.ro")

    first = await register(async_client, event, user_headers)
    assert first.status_code == 201
    assert first.json()["status"] == EventRegistrationStatus.CONFIRMED.value
    first_ticket_id = first.json()["ticket_id"]
    assert first_ticket_id is not None

    second = await register(async_client, event, other_headers)
    assert second.json()["status"] == EventRegistrationStatus.WAITLIST.value
    assert second.json()["ticket_id"] is None

    # Cancelling revokes the ticket and promotes the waitlisted student, who gets a ticket.
    cancel = await async_client.delete(f"/api/v1/events/{event.id}/register", headers=user_headers)
    assert cancel.status_code == 200
    assert cancel.json()["ticket_id"] is None
    revoked = await async_client.get(f"/api/v1/me/tickets/{first_ticket_id}", headers=user_headers)
    assert revoked.json()["state"] == "REVOKED"
    assert revoked.json()["qr_token"] is None

    promoted = await async_client.get(f"/api/v1/events/{event.id}/register", headers=other_headers)
    assert promoted.json()["status"] == EventRegistrationStatus.CONFIRMED.value
    assert promoted.json()["ticket_id"] is not None


async def test_re_registering_issues_fresh_ticket_code(
    async_client, db_session, user_headers, test_admin, test_organization
):
    event = await make_event(db_session, test_organization, test_admin)
    ticket_id = (await register(async_client, event, user_headers)).json()["ticket_id"]
    old_token = await ticket_token(async_client, ticket_id, user_headers)

    await async_client.delete(f"/api/v1/events/{event.id}/register", headers=user_headers)
    again = await register(async_client, event, user_headers)
    assert again.json()["ticket_id"] == ticket_id
    assert await ticket_token(async_client, ticket_id, user_headers) != old_token


async def test_my_registrations_and_ticket_access(
    async_client, db_session, user_headers, test_admin, test_organization
):
    event = await make_event(db_session, test_organization, test_admin)
    ticket_id = (await register(async_client, event, user_headers)).json()["ticket_id"]

    schedule = await async_client.get("/api/v1/me/registrations", headers=user_headers)
    assert schedule.status_code == 200
    [entry] = schedule.json()
    assert entry["event"]["id"] == str(event.id)
    assert entry["ticket_id"] == ticket_id
    assert entry["ticket_state"] == "VALID"

    ticket = await async_client.get(f"/api/v1/me/tickets/{ticket_id}", headers=user_headers)
    assert ticket.status_code == 200
    assert ticket.json()["state"] == "VALID"
    assert ticket.json()["qr_token"]

    qr = await async_client.get(f"/api/v1/me/tickets/{ticket_id}/qr.svg", headers=user_headers)
    assert qr.status_code == 200
    assert qr.headers["content-type"].startswith("image/svg+xml")
    assert b"<svg" in qr.content

    _, stranger_headers = await make_user(async_client, db_session, "stranger@ubbcluj.ro")
    other = await async_client.get(f"/api/v1/me/tickets/{ticket_id}", headers=stranger_headers)
    assert other.status_code == 404


# --- Check-in -----------------------------------------------------------------


async def test_qr_check_in_flow(
    async_client, db_session, user_headers, test_user, test_admin, test_organization
):
    event = await make_event(db_session, test_organization, test_admin, starts_in=timedelta(minutes=30))
    organizer, organizer_headers = await make_user(async_client, db_session, "org@ubbcluj.ro")
    await add_member(db_session, organizer, test_organization, OrgRole.ORGANIZER)

    ticket_id = (await register(async_client, event, user_headers)).json()["ticket_id"]
    token = await ticket_token(async_client, ticket_id, user_headers)
    path = f"/api/v1/events/{event.id}/check-in"

    # A plain student cannot scan tickets.
    assert (await async_client.post(path, headers=user_headers, json={"token": token})).status_code == 403

    scan = await async_client.post(path, headers=organizer_headers, json={"token": token})
    assert scan.status_code == 200
    assert scan.json()["user_id"] == str(test_user.id)
    assert scan.json()["full_name"] == test_user.full_name
    assert scan.json()["checked_in_by_id"] == str(organizer.id)

    again = await async_client.post(path, headers=organizer_headers, json={"token": token})
    assert again.status_code == 409
    assert "already checked in" in again.json()["detail"]

    ticket = await async_client.get(f"/api/v1/me/tickets/{ticket_id}", headers=user_headers)
    assert ticket.json()["state"] == "USED"

    # Checked-in attendees cannot cancel; organizers can undo a mistaken scan.
    cancel = await async_client.delete(f"/api/v1/events/{event.id}/register", headers=user_headers)
    assert cancel.status_code == 409
    undo = await async_client.delete(f"{path}/{ticket_id}", headers=organizer_headers)
    assert undo.status_code == 204
    assert (await async_client.post(path, headers=organizer_headers, json={"token": token})).status_code == 200


async def test_check_in_rejects_bad_tokens(
    async_client, db_session, user_headers, admin_headers, test_admin, test_organization
):
    event = await make_event(db_session, test_organization, test_admin, starts_in=timedelta(minutes=5))
    other_event = await make_event(db_session, test_organization, test_admin, starts_in=timedelta(minutes=5))
    path = f"/api/v1/events/{event.id}/check-in"

    garbage = await async_client.post(path, headers=admin_headers, json={"token": "not-a-ticket"})
    assert garbage.status_code == 400

    other_ticket = (await register(async_client, other_event, user_headers)).json()["ticket_id"]
    other_token = await ticket_token(async_client, other_ticket, user_headers)
    wrong_event = await async_client.post(path, headers=admin_headers, json={"token": other_token})
    assert wrong_event.status_code == 400
    assert "different event" in wrong_event.json()["detail"]

    ticket_id = (await register(async_client, event, user_headers)).json()["ticket_id"]
    token = await ticket_token(async_client, ticket_id, user_headers)
    payload = jwt.decode(token, options={"verify_signature": False})
    forged = jwt.encode(payload, "attacker-secret-that-is-long-enough-for-hs256", algorithm="HS256")
    assert (await async_client.post(path, headers=admin_headers, json={"token": forged})).status_code == 400

    await async_client.delete(f"/api/v1/events/{event.id}/register", headers=user_headers)
    revoked = await async_client.post(path, headers=admin_headers, json={"token": token})
    assert revoked.status_code == 400
    assert "revoked" in revoked.json()["detail"]


async def test_check_in_window(
    async_client, db_session, user_headers, admin_headers, test_admin, test_organization
):
    event = await make_event(db_session, test_organization, test_admin, starts_in=timedelta(days=2))
    ticket_id = (await register(async_client, event, user_headers)).json()["ticket_id"]
    token = await ticket_token(async_client, ticket_id, user_headers)

    too_early = await async_client.post(
        f"/api/v1/events/{event.id}/check-in", headers=admin_headers, json={"token": token}
    )
    assert too_early.status_code == 409
    assert "opens at" in too_early.json()["detail"]


async def test_manual_check_in_and_attendance_stats(
    async_client, db_session, user_headers, admin_headers, test_user, test_admin, test_organization
):
    event = await make_event(
        db_session, test_organization, test_admin, starts_in=timedelta(minutes=10), capacity=2
    )
    await register(async_client, event, user_headers)
    _, h2 = await make_user(async_client, db_session, "b@ubbcluj.ro")
    _, h3 = await make_user(async_client, db_session, "c@ubbcluj.ro")
    await register(async_client, event, h2)
    await register(async_client, event, h3)  # waitlisted

    manual = await async_client.post(
        f"/api/v1/events/{event.id}/check-in/manual",
        headers=admin_headers,
        json={"user_id": str(test_user.id)},
    )
    assert manual.status_code == 200

    stats = await async_client.get(f"/api/v1/events/{event.id}/attendance", headers=admin_headers)
    assert stats.status_code == 200
    assert stats.json() == {
        "event_id": str(event.id),
        "capacity": 2,
        "confirmed": 2,
        "waitlisted": 1,
        "cancelled": 0,
        "checked_in": 1,
        "not_checked_in": 1,
        "attendance_rate": 0.5,
        "spots_left": 0,
    }

    attendees = await async_client.get(f"/api/v1/events/{event.id}/attendees", headers=admin_headers)
    checked = {a["user_id"]: a["checked_in_at"] for a in attendees.json()}
    assert checked[str(test_user.id)] is not None


# --- Lifecycle & event changes ------------------------------------------------


async def test_event_state_machine(
    async_client, db_session, user_headers, admin_headers, test_user, test_admin, test_organization
):
    await add_member(db_session, test_user, test_organization, OrgRole.ORGANIZER)
    event = await make_event(db_session, test_organization, test_admin, status=EventStatus.DRAFT)
    path = f"/api/v1/events/{event.id}/status"

    # Organizers submit for review but cannot publish.
    submitted = await async_client.patch(path, headers=user_headers, json={"status": "SUBMITTED"})
    assert submitted.status_code == 200
    assert (await async_client.patch(path, headers=user_headers, json={"status": "PUBLISHED"})).status_code == 403

    # Skipping states is not allowed.
    assert (await async_client.patch(path, headers=admin_headers, json={"status": "COMPLETED"})).status_code == 409

    for target in ("PUBLISHED", "IN_PROGRESS", "COMPLETED"):
        response = await async_client.patch(path, headers=admin_headers, json={"status": target})
        assert response.status_code == 200, response.text
        assert response.json()["status"] == target

    # Final states are final, and completed events can't be edited.
    assert (await async_client.patch(path, headers=admin_headers, json={"status": "PUBLISHED"})).status_code == 409
    assert (
        await async_client.put(f"/api/v1/events/{event.id}", headers=admin_headers, json={"title": "x"})
    ).status_code == 409


async def test_cancelling_event_revokes_all_tickets(
    async_client, db_session, user_headers, admin_headers, test_admin, test_organization
):
    event = await make_event(db_session, test_organization, test_admin)
    ticket_id = (await register(async_client, event, user_headers)).json()["ticket_id"]

    response = await async_client.patch(
        f"/api/v1/events/{event.id}/status", headers=admin_headers, json={"status": "CANCELLED"}
    )
    assert response.status_code == 200
    ticket = await db_session.scalar(select(Ticket).where(Ticket.id == UUID(ticket_id)))
    await db_session.refresh(ticket)
    assert ticket.revoked_at is not None


async def test_capacity_changes(
    async_client, db_session, user_headers, admin_headers, test_admin, test_organization
):
    event = await make_event(db_session, test_organization, test_admin, capacity=1)
    await register(async_client, event, user_headers)
    _, other_headers = await make_user(async_client, db_session, "wait@ubbcluj.ro")
    waitlisted = await register(async_client, event, other_headers)
    assert waitlisted.json()["status"] == "WAITLIST"

    path = f"/api/v1/events/{event.id}"
    assert (await async_client.put(path, headers=admin_headers, json={"capacity": 0})).status_code == 422

    # Raising capacity promotes from the waitlist and issues the ticket.
    assert (await async_client.put(path, headers=admin_headers, json={"capacity": 2})).status_code == 200
    promoted = await async_client.get(f"{path}/register", headers=other_headers)
    assert promoted.json()["status"] == "CONFIRMED"
    assert promoted.json()["ticket_id"] is not None

    # Lowering it below the confirmed count is refused.
    lowered = await async_client.put(path, headers=admin_headers, json={"capacity": 1})
    assert lowered.status_code == 409


async def test_unpublished_events_hidden_from_public(
    async_client, db_session, user_headers, admin_headers, test_admin, test_organization
):
    draft = await make_event(db_session, test_organization, test_admin, status=EventStatus.DRAFT)
    assert (await async_client.get(f"/api/v1/events/{draft.id}")).status_code == 404
    assert (await async_client.get(f"/api/v1/events/{draft.id}", headers=user_headers)).status_code == 404
    assert (await async_client.get(f"/api/v1/events/{draft.id}", headers=admin_headers)).status_code == 200


async def test_list_events_filters_by_category_and_date(
    async_client, db_session, test_admin, test_organization
):
    soon = await make_event(db_session, test_organization, test_admin, starts_in=timedelta(days=1))
    later = await make_event(db_session, test_organization, test_admin, starts_in=timedelta(days=10))
    later.category = EventCategory.WORKSHOP
    await db_session.commit()

    by_category = await async_client.get("/api/v1/events", params={"category": "WORKSHOP"})
    assert [e["id"] for e in by_category.json()["items"]] == [str(later.id)]

    cutoff = (datetime.now(timezone.utc) + timedelta(days=5)).isoformat()
    by_date = await async_client.get("/api/v1/events", params={"starts_before": cutoff})
    assert [e["id"] for e in by_date.json()["items"]] == [str(soon.id)]
