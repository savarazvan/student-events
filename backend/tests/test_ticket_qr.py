"""Ticket QR codes link to the ticket-check page; verification and URL check-in."""

from datetime import timedelta
from urllib.parse import parse_qs, urlsplit

import pytest

from app.models.models import OrgRole
from tests.test_attendance import add_member, make_event, make_user, register

pytestmark = pytest.mark.asyncio


async def my_ticket(client, headers) -> dict:
    ticket_id = (await client.get("/api/v1/me/registrations", headers=headers)).json()[0][
        "ticket_id"
    ]
    return (await client.get(f"/api/v1/me/tickets/{ticket_id}", headers=headers)).json()


async def test_qr_encodes_ticket_check_url(
    async_client, db_session, test_admin, test_organization, monkeypatch
):
    monkeypatch.setenv("FRONTEND_URL", "https://events.example.ro/")
    event = await make_event(db_session, test_organization, test_admin)
    _, ana = await make_user(async_client, db_session, "ana@example.com")
    await register(async_client, event, ana)

    ticket = await my_ticket(async_client, ana)
    url = urlsplit(ticket["qr_url"])
    assert (url.scheme, url.netloc, url.path) == ("https", "events.example.ro", "/ticket-check")
    assert parse_qs(url.query)["token"] == [ticket["qr_token"]]


async def test_verify_ticket_as_public_holder_and_organizer(
    async_client, db_session, test_admin, test_organization
):
    event = await make_event(
        db_session, test_organization, test_admin, starts_in=timedelta(minutes=30)
    )
    organizer, organizer_headers = await make_user(async_client, db_session, "org@example.com")
    await add_member(db_session, organizer, test_organization, OrgRole.ORGANIZER)
    _, ana = await make_user(async_client, db_session, "ana@example.com")
    await register(async_client, event, ana)
    ticket = await my_ticket(async_client, ana)
    params = {"token": ticket["qr_url"]}  # the full scanned URL is accepted

    public = (await async_client.get("/api/v1/tickets/verify", params=params)).json()
    assert public["state"] == "VALID"
    assert public["event"]["id"] == str(event.id)
    assert public["attendee_name"] is None  # no personal data for strangers
    assert public["can_check_in"] is False

    holder = (
        await async_client.get("/api/v1/tickets/verify", params=params, headers=ana)
    ).json()
    assert holder["attendee_name"] == "Ana" and holder["can_check_in"] is False

    staff = (
        await async_client.get(
            "/api/v1/tickets/verify", params=params, headers=organizer_headers
        )
    ).json()
    assert staff["attendee_name"] == "Ana"
    assert staff["can_check_in"] is True and staff["check_in_unavailable_reason"] is None

    # Scanning the URL with the in-app scanner checks the attendee in.
    response = await async_client.post(
        f"/api/v1/events/{event.id}/check-in",
        json={"token": ticket["qr_url"]},
        headers=organizer_headers,
    )
    assert response.status_code == 200

    staff = (
        await async_client.get(
            "/api/v1/tickets/verify", params=params, headers=organizer_headers
        )
    ).json()
    assert staff["state"] == "USED" and staff["can_check_in"] is False
    assert staff["checked_in_at"] is not None


async def test_verify_reports_closed_check_in_window(
    async_client, db_session, test_admin, admin_headers, test_organization
):
    event = await make_event(db_session, test_organization, test_admin, starts_in=timedelta(days=2))
    _, ana = await make_user(async_client, db_session, "ana@example.com")
    await register(async_client, event, ana)
    ticket = await my_ticket(async_client, ana)

    body = (
        await async_client.get(
            "/api/v1/tickets/verify", params={"token": ticket["qr_token"]}, headers=admin_headers
        )
    ).json()
    assert body["can_check_in"] is False
    assert body["check_in_unavailable_reason"].startswith("Check-in opens at")


@pytest.mark.parametrize(
    "token",
    ["garbage", "https://events.example.ro/ticket-check?token=garbage", "https://x.ro/?a=1"],
)
async def test_verify_rejects_invalid_tokens(async_client, token):
    response = await async_client.get("/api/v1/tickets/verify", params={"token": token})
    assert response.status_code == 400
