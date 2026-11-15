"""Notifications for registration changes, announcements, reminders and e-mail outbox."""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.models.models import EventStatus, Notification, OrgRole
from app.services.notifications import deliver_pending_emails, send_due_reminders
from tests.test_attendance import add_member, make_event, make_user, register

pytestmark = pytest.mark.asyncio


async def notification_types(client, headers) -> list[str]:
    response = await client.get("/api/v1/me/notifications", headers=headers)
    assert response.status_code == 200
    return [n["type"] for n in response.json()["items"]]


async def test_registration_waitlist_and_promotion_notifications(
    async_client, db_session, test_admin, test_organization
):
    event = await make_event(db_session, test_organization, test_admin, capacity=1)
    _, ana = await make_user(async_client, db_session, "ana@example.com")
    _, bob = await make_user(async_client, db_session, "bob@example.com")

    assert (await register(async_client, event, ana)).json()["status"] == "CONFIRMED"
    assert (await register(async_client, event, bob)).json()["status"] == "WAITLIST"
    assert await notification_types(async_client, ana) == ["REGISTRATION_CONFIRMED"]
    assert await notification_types(async_client, bob) == ["REGISTRATION_WAITLISTED"]

    response = await async_client.delete(f"/api/v1/events/{event.id}/register", headers=ana)
    assert response.status_code == 200
    assert await notification_types(async_client, bob) == [
        "WAITLIST_PROMOTED",
        "REGISTRATION_WAITLISTED",
    ]


async def test_logistics_change_notifies_registrants(
    async_client, db_session, test_admin, admin_headers, test_organization
):
    event = await make_event(db_session, test_organization, test_admin)
    _, ana = await make_user(async_client, db_session, "ana@example.com")
    await register(async_client, event, ana)

    # A title change is not critical: no notification.
    response = await async_client.put(
        f"/api/v1/events/{event.id}", json={"title": "Renamed"}, headers=admin_headers
    )
    assert response.status_code == 200
    assert await notification_types(async_client, ana) == ["REGISTRATION_CONFIRMED"]

    response = await async_client.put(
        f"/api/v1/events/{event.id}", json={"location": "Room 2"}, headers=admin_headers
    )
    assert response.status_code == 200
    response = await async_client.get("/api/v1/me/notifications", headers=ana)
    latest = response.json()["items"][0]
    assert latest["type"] == "EVENT_UPDATED"
    assert "location" in latest["message"] and "Room 2" in latest["message"]


async def test_cancelling_event_notifies_registrants(
    async_client, db_session, test_admin, admin_headers, test_organization
):
    event = await make_event(db_session, test_organization, test_admin)
    _, ana = await make_user(async_client, db_session, "ana@example.com")
    await register(async_client, event, ana)
    response = await async_client.patch(
        f"/api/v1/events/{event.id}/status", json={"status": "CANCELLED"}, headers=admin_headers
    )
    assert response.status_code == 200
    assert (await notification_types(async_client, ana))[0] == "EVENT_CANCELLED"


async def test_announcements(async_client, db_session, test_admin, admin_headers, test_organization):
    event = await make_event(db_session, test_organization, test_admin, capacity=1)
    _, ana = await make_user(async_client, db_session, "ana@example.com")
    _, bob = await make_user(async_client, db_session, "bob@example.com")
    await register(async_client, event, ana)
    await register(async_client, event, bob)  # waitlisted, still informed
    url = f"/api/v1/events/{event.id}/announcements"

    response = await async_client.post(
        url, json={"title": "Room change", "message": "We moved to Aula Magna."}, headers=ana
    )
    assert response.status_code == 403

    response = await async_client.post(
        url,
        json={"title": " Room change ", "message": "We moved to Aula Magna."},
        headers=admin_headers,
    )
    assert response.status_code == 201
    assert response.json()["recipients"] == 2
    assert response.json()["title"] == "Room change"

    for headers in (ana, bob):
        assert (await notification_types(async_client, headers))[0] == "EVENT_ANNOUNCEMENT"

    response = await async_client.get(url)  # public for published events
    assert response.status_code == 200
    assert [(a["title"], a["author_name"]) for a in response.json()] == [
        ("Room change", "Test Administrator")
    ]


async def test_announcement_requires_published_event(
    async_client, db_session, test_admin, admin_headers, test_organization
):
    event = await make_event(db_session, test_organization, test_admin, status=EventStatus.DRAFT)
    response = await async_client.post(
        f"/api/v1/events/{event.id}/announcements",
        json={"title": "Hi", "message": "Hello"},
        headers=admin_headers,
    )
    assert response.status_code == 409


async def test_mark_read_and_unread_count(async_client, db_session, test_admin, test_organization):
    first = await make_event(db_session, test_organization, test_admin)
    second = await make_event(db_session, test_organization, test_admin)
    _, ana = await make_user(async_client, db_session, "ana@example.com")
    _, bob = await make_user(async_client, db_session, "bob@example.com")
    for event in (first, second):
        await register(async_client, event, ana)

    body = (await async_client.get("/api/v1/me/notifications", headers=ana)).json()
    assert body["unread_count"] == 2
    first_id = body["items"][0]["id"]

    response = await async_client.post(f"/api/v1/me/notifications/{first_id}/read", headers=bob)
    assert response.status_code == 404  # not Bob's notification

    response = await async_client.post(f"/api/v1/me/notifications/{first_id}/read", headers=ana)
    assert response.status_code == 200 and response.json()["read_at"] is not None
    body = (
        await async_client.get("/api/v1/me/notifications?unread_only=true", headers=ana)
    ).json()
    assert body["unread_count"] == 1 and len(body["items"]) == 1

    response = await async_client.post("/api/v1/me/notifications/read-all", headers=ana)
    assert response.json() == {"updated": 1}
    body = (await async_client.get("/api/v1/me/notifications", headers=ana)).json()
    assert body["unread_count"] == 0


async def test_reminders_are_sent_once_to_confirmed_attendees(
    async_client, db_session, test_admin, test_organization
):
    tomorrow = await make_event(
        db_session, test_organization, test_admin, starts_in=timedelta(hours=20), capacity=1
    )
    soon = await make_event(
        db_session, test_organization, test_admin, starts_in=timedelta(minutes=90)
    )
    later = await make_event(db_session, test_organization, test_admin, starts_in=timedelta(days=3))
    ana_user, ana = await make_user(async_client, db_session, "ana@example.com")
    _, bob = await make_user(async_client, db_session, "bob@example.com")
    for event in (tomorrow, soon, later):
        await register(async_client, event, ana)
    await register(async_client, tomorrow, bob)  # waitlisted: no reminder

    assert await send_due_reminders(db_session) == 2
    assert await send_due_reminders(db_session) == 0  # idempotent

    reminders = (
        await db_session.scalars(
            select(Notification).where(Notification.type == "EVENT_REMINDER")
        )
    ).all()
    assert {(n.event_id, n.user_id, n.dedup_key.split(":")[1]) for n in reminders} == {
        (tomorrow.id, ana_user.id, "24h"),
        (soon.id, ana_user.id, "2h"),
    }

    # Once the event gets within 2 hours, the 24h-reminded attendee gets the 2h one too.
    in_19h = datetime.now(timezone.utc) + timedelta(hours=19)
    assert await send_due_reminders(db_session, now=in_19h) == 1


async def test_email_outbox_delivery(async_client, db_session, test_admin, test_organization):
    event = await make_event(db_session, test_organization, test_admin)
    _, ana = await make_user(async_client, db_session, "ana@example.com")
    await register(async_client, event, ana)

    sent: list[tuple[str, str]] = []
    assert await deliver_pending_emails(db_session, lambda to, s, b: sent.append((to, s))) == 1
    assert sent == [("ana@example.com", "You're registered: Attendance Test Event")]
    assert await deliver_pending_emails(db_session, lambda *a: sent.append(a)) == 0


async def test_email_failure_keeps_notification_pending(
    async_client, db_session, test_admin, test_organization
):
    event = await make_event(db_session, test_organization, test_admin)
    _, ana = await make_user(async_client, db_session, "ana@example.com")
    await register(async_client, event, ana)

    def broken(*_args):
        raise OSError("SMTP down")

    assert await deliver_pending_emails(db_session, broken) == 0
    assert await deliver_pending_emails(db_session, lambda *a: None) == 1


async def test_org_member_role_cannot_send_announcements(
    async_client, db_session, test_admin, test_organization
):
    member, headers = await make_user(async_client, db_session, "member@example.com")
    await add_member(db_session, member, test_organization, OrgRole.MEMBER)
    event = await make_event(db_session, test_organization, test_admin)
    response = await async_client.post(
        f"/api/v1/events/{event.id}/announcements",
        json={"title": "Hi", "message": "Hello"},
        headers=headers,
    )
    assert response.status_code == 403
