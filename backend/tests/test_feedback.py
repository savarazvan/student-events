"""Post-event feedback rules and the organizer's event report."""

from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from app.models.models import Event, EventStatus, Ticket
from tests.test_attendance import make_event, make_user, register

pytestmark = pytest.mark.asyncio


async def check_in(db_session, event: Event, user_id) -> None:
    ticket = await db_session.scalar(
        select(Ticket).where(Ticket.event_id == event.id, Ticket.user_id == user_id)
    )
    ticket.checked_in_at = datetime.now(timezone.utc)
    await db_session.commit()


async def set_status(db_session, event: Event, status: EventStatus) -> None:
    event.status = status
    await db_session.commit()


async def test_feedback_only_from_checked_in_attendees_after_completion(
    async_client, db_session, test_admin, test_organization
):
    event = await make_event(db_session, test_organization, test_admin)
    ana_user, ana = await make_user(async_client, db_session, "ana@example.com")
    _, bob = await make_user(async_client, db_session, "bob@example.com")
    await register(async_client, event, ana)
    await register(async_client, event, bob)
    url = f"/api/v1/events/{event.id}/feedback"

    response = await async_client.put(url, json={"rating": 5}, headers=ana)
    assert response.status_code == 409  # event not completed yet

    await check_in(db_session, event, ana_user.id)
    await set_status(db_session, event, EventStatus.COMPLETED)

    response = await async_client.put(url, json={"rating": 4}, headers=bob)
    assert response.status_code == 403  # registered but never showed up

    response = await async_client.put(
        url, json={"rating": 4, "comment": "  Great talk  "}, headers=ana
    )
    assert response.status_code == 200
    assert response.json()["comment"] == "Great talk"

    # Submitting again updates the same feedback.
    response = await async_client.put(url, json={"rating": 5, "comment": ""}, headers=ana)
    assert response.status_code == 200
    assert response.json()["rating"] == 5 and response.json()["comment"] is None

    response = await async_client.get(f"{url}/me", headers=ana)
    assert response.status_code == 200 and response.json()["rating"] == 5
    response = await async_client.get(f"{url}/me", headers=bob)
    assert response.status_code == 404


@pytest.mark.parametrize("rating", [0, 6])
async def test_rating_must_be_between_1_and_5(
    async_client, db_session, test_admin, test_organization, rating
):
    event = await make_event(db_session, test_organization, test_admin)
    _, ana = await make_user(async_client, db_session, "ana@example.com")
    response = await async_client.put(
        f"/api/v1/events/{event.id}/feedback", json={"rating": rating}, headers=ana
    )
    assert response.status_code == 422


async def test_completing_event_requests_feedback_from_attendees(
    async_client, db_session, test_admin, admin_headers, test_organization
):
    event = await make_event(db_session, test_organization, test_admin)
    ana_user, ana = await make_user(async_client, db_session, "ana@example.com")
    _, bob = await make_user(async_client, db_session, "bob@example.com")
    await register(async_client, event, ana)
    await register(async_client, event, bob)
    await check_in(db_session, event, ana_user.id)
    await set_status(db_session, event, EventStatus.IN_PROGRESS)

    response = await async_client.patch(
        f"/api/v1/events/{event.id}/status", json={"status": "COMPLETED"}, headers=admin_headers
    )
    assert response.status_code == 200

    ana_types = [
        n["type"]
        for n in (await async_client.get("/api/v1/me/notifications", headers=ana)).json()["items"]
    ]
    bob_types = [
        n["type"]
        for n in (await async_client.get("/api/v1/me/notifications", headers=bob)).json()["items"]
    ]
    assert ana_types[0] == "FEEDBACK_REQUESTED"
    assert "FEEDBACK_REQUESTED" not in bob_types


async def test_event_report(
    async_client, db_session, test_admin, admin_headers, test_organization
):
    event = await make_event(db_session, test_organization, test_admin)
    attendees = []
    for name in ("ana", "bob", "cat"):
        user, headers = await make_user(async_client, db_session, f"{name}@example.com")
        await register(async_client, event, headers)
        attendees.append((user, headers))
    _, no_show = await make_user(async_client, db_session, "dan@example.com")
    await register(async_client, event, no_show)
    for user, _ in attendees:
        await check_in(db_session, event, user.id)
    await set_status(db_session, event, EventStatus.COMPLETED)

    url = f"/api/v1/events/{event.id}/feedback"
    for (_, headers), rating, comment in zip(attendees, (5, 4, 4), ("Loved it", None, "Too long")):
        response = await async_client.put(
            url, json={"rating": rating, "comment": comment}, headers=headers
        )
        assert response.status_code == 200

    response = await async_client.get(f"/api/v1/events/{event.id}/report", headers=admin_headers)
    assert response.status_code == 200
    report = response.json()
    assert report["attendance"]["confirmed"] == 4
    assert report["attendance"]["checked_in"] == 3
    assert report["feedback_count"] == 3
    assert report["average_rating"] == 4.33
    assert report["rating_distribution"] == {"1": 0, "2": 0, "3": 0, "4": 2, "5": 1}
    assert report["feedback_response_rate"] == 1.0
    assert sorted(c["comment"] for c in report["comments"]) == ["Loved it", "Too long"]
    assert all("user_id" not in c for c in report["comments"])  # anonymous

    response = await async_client.get(f"/api/v1/events/{event.id}/report", headers=no_show)
    assert response.status_code == 403
