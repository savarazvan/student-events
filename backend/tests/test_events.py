import base64
from datetime import datetime, timedelta, timezone
from io import BytesIO
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException, UploadFile
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.datastructures import Headers

from app.core.image_utils import validate_image_upload
from app.models.models import (
    Event,
    EventRegistration,
    EventRegistrationStatus,
    EventStatus,
    Organization,
    OrganizationMember,
    OrgRole,
    User,
)


def event_payload(organization_id: str) -> dict[str, object]:
    start_time = datetime.now(timezone.utc) + timedelta(days=1)
    return {
        "title": "Student Tech Meetup",
        "description": "A meetup for student developers.",
        "location": "UBB Main Building",
        "start_time": start_time.isoformat(),
        "end_time": (start_time + timedelta(hours=2)).isoformat(),
        "capacity": 100,
        "organization_id": organization_id,
    }


async def persist_event(
    db_session: AsyncSession,
    organization: Organization,
    creator: User,
    event_status: EventStatus,
) -> Event:
    start_time = datetime.now(timezone.utc) + timedelta(days=1)
    event = Event(
        title=f"{event_status.value} Event",
        description="Event used for API tests.",
        location="UBB Main Building",
        start_time=start_time,
        end_time=start_time + timedelta(hours=2),
        capacity=100,
        status=event_status,
        organization_id=organization.id,
        created_by_id=creator.id,
    )
    db_session.add(event)
    await db_session.commit()
    await db_session.refresh(event)
    return event


@pytest.mark.asyncio
async def test_create_event_as_organizer_success(
    async_client: AsyncClient,
    db_session: AsyncSession,
    user_headers: dict[str, str],
    test_user: User,
    test_organization: Organization,
    organizer_membership: OrganizationMember,
) -> None:
    response = await async_client.post(
        "/api/v1/events",
        headers=user_headers,
        json=event_payload(str(test_organization.id)),
    )

    assert response.status_code == 201
    response_data = response.json()
    assert response_data["title"] == "Student Tech Meetup"
    assert response_data["status"] == EventStatus.DRAFT.value
    assert response_data["organization_id"] == str(test_organization.id)
    assert response_data["created_by_id"] == str(test_user.id)

    event = await db_session.scalar(
        select(Event).where(Event.id == UUID(response_data["id"]))
    )
    assert event is not None
    assert event.created_by_id == test_user.id
    assert event.status == EventStatus.DRAFT
    assert response_data["image_url"] is None


@pytest.mark.asyncio
async def test_create_event_with_valid_image_url(
    async_client: AsyncClient,
    user_headers: dict[str, str],
    test_organization: Organization,
    organizer_membership: OrganizationMember,
) -> None:
    payload = event_payload(str(test_organization.id))
    payload["image_url"] = "https://cdn.example.com/poster.JPEG"

    response = await async_client.post(
        "/api/v1/events",
        headers=user_headers,
        json=payload,
    )

    assert response.status_code == 201
    assert response.json()["image_url"] == payload["image_url"]


@pytest.mark.asyncio
async def test_create_event_rejects_invalid_image_extension(
    async_client: AsyncClient,
    user_headers: dict[str, str],
    test_organization: Organization,
    organizer_membership: OrganizationMember,
) -> None:
    payload = event_payload(str(test_organization.id))
    payload["image_url"] = "https://cdn.example.com/poster.pdf"

    response = await async_client.post(
        "/api/v1/events",
        headers=user_headers,
        json=payload,
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_create_event_rejects_image_over_5mb(
    async_client: AsyncClient,
    user_headers: dict[str, str],
    test_organization: Organization,
    organizer_membership: OrganizationMember,
) -> None:
    content = b"\x89PNG\r\n\x1a\n" + b"x" * (5 * 1024 * 1024)
    encoded = base64.b64encode(content).decode("ascii")
    payload = event_payload(str(test_organization.id))
    payload["image_url"] = f"data:image/png;base64,{encoded}"

    response = await async_client.post(
        "/api/v1/events",
        headers=user_headers,
        json=payload,
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_image_upload_validator_rejects_mime_extension_mismatch() -> None:
    upload = UploadFile(
        filename="poster.png",
        file=BytesIO(b"\x89PNG\r\n\x1a\n"),
        headers=Headers({"content-type": "application/pdf"}),
    )

    with pytest.raises(HTTPException) as exception_info:
        await validate_image_upload(upload)

    assert exception_info.value.status_code == 400


@pytest.mark.asyncio
async def test_create_event_unauthorized_user_forbidden(
    async_client: AsyncClient,
    user_headers: dict[str, str],
    test_organization: Organization,
) -> None:
    response = await async_client.post(
        "/api/v1/events",
        headers=user_headers,
        json=event_payload(str(test_organization.id)),
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_list_events_public_only_published(
    async_client: AsyncClient,
    db_session: AsyncSession,
    user_headers: dict[str, str],
    test_user: User,
    test_organization: Organization,
) -> None:
    published = await persist_event(
        db_session, test_organization, test_user, EventStatus.PUBLISHED
    )
    await persist_event(db_session, test_organization, test_user, EventStatus.DRAFT)
    await persist_event(db_session, test_organization, test_user, EventStatus.CANCELLED)

    response = await async_client.get(
        "/api/v1/events",
        headers=user_headers,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["page"] == 1
    assert payload["size"] == 20
    assert [item["id"] for item in payload["items"]] == [str(published.id)]
    assert all(
        item["status"] == EventStatus.PUBLISHED.value for item in payload["items"]
    )


@pytest.mark.asyncio
async def test_list_events_supports_search_and_pagination(
    async_client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    test_organization: Organization,
) -> None:
    first = await persist_event(
        db_session, test_organization, test_user, EventStatus.PUBLISHED
    )
    first.title = "Robotics Workshop"
    await db_session.commit()
    second = await persist_event(
        db_session, test_organization, test_user, EventStatus.PUBLISHED
    )
    second.title = "Robotics Open Lab"
    await db_session.commit()
    await persist_event(db_session, test_organization, test_user, EventStatus.PUBLISHED)

    response = await async_client.get(
        "/api/v1/events",
        params={"search": "Robotics", "page": 2, "size": 1},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 2
    assert payload["page"] == 2
    assert payload["size"] == 1
    assert len(payload["items"]) == 1
    assert payload["items"][0]["id"] == str(second.id)


@pytest.mark.asyncio
async def test_update_event_status_as_org_admin(
    async_client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    test_organization: Organization,
) -> None:
    db_session.add(
        OrganizationMember(
            user_id=test_user.id,
            organization_id=test_organization.id,
            role_in_org=OrgRole.ADMIN,
        )
    )
    await db_session.commit()
    draft_event = await persist_event(
        db_session, test_organization, test_user, EventStatus.DRAFT
    )

    login_response = await async_client.post(
        "/api/v1/auth/login",
        json={"email": test_user.email, "password": "test-password-123"},
    )
    assert login_response.status_code == 200
    headers = {
        "Authorization": f"Bearer {login_response.json()['access_token']}"
    }

    response = await async_client.patch(
        f"/api/v1/events/{draft_event.id}/status",
        headers=headers,
        json={"status": EventStatus.PUBLISHED.value},
    )

    assert response.status_code == 200
    assert response.json()["status"] == EventStatus.PUBLISHED.value
    await db_session.refresh(draft_event)
    assert draft_event.status == EventStatus.PUBLISHED


@pytest.mark.asyncio
async def test_get_event_by_id_not_found(
    async_client: AsyncClient,
) -> None:
    response = await async_client.get(f"/api/v1/events/{uuid4()}")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_registration_capacity_and_waitlist_promotion(
    async_client: AsyncClient,
    db_session: AsyncSession,
    user_headers: dict[str, str],
    admin_headers: dict[str, str],
    test_user: User,
    test_admin: User,
    test_organization: Organization,
) -> None:
    event = await persist_event(
        db_session, test_organization, test_user, EventStatus.PUBLISHED
    )
    event.capacity = 1
    await db_session.commit()
    registration_path = f"/api/v1/events/{event.id}/register"

    first_response = await async_client.post(
        registration_path,
        headers=user_headers,
    )
    second_response = await async_client.post(
        registration_path,
        headers=admin_headers,
    )

    assert first_response.status_code == 201
    assert first_response.json()["status"] == EventRegistrationStatus.CONFIRMED.value
    assert second_response.status_code == 201
    assert second_response.json()["status"] == EventRegistrationStatus.WAITLIST.value

    registrations = list(
        (
            await db_session.scalars(
                select(EventRegistration).where(EventRegistration.event_id == event.id)
            )
        ).all()
    )
    assert len(registrations) == 2
    waitlisted_user_id = UUID(second_response.json()["user_id"])

    cancel_response = await async_client.delete(
        registration_path,
        headers=user_headers,
    )
    assert cancel_response.status_code == 200
    assert cancel_response.json()["status"] == EventRegistrationStatus.CANCELLED.value

    promoted = await db_session.scalar(
        select(EventRegistration).where(
            EventRegistration.event_id == event.id,
            EventRegistration.user_id == waitlisted_user_id,
        )
    )
    assert promoted is not None
    assert promoted.status == EventRegistrationStatus.CONFIRMED


@pytest.mark.asyncio
async def test_list_event_attendees_for_organization_organizer(
    async_client: AsyncClient,
    db_session: AsyncSession,
    user_headers: dict[str, str],
    test_user: User,
    test_organization: Organization,
    organizer_membership: OrganizationMember,
) -> None:
    event = await persist_event(
        db_session, test_organization, test_user, EventStatus.PUBLISHED
    )
    await async_client.post(
        f"/api/v1/events/{event.id}/register",
        headers=user_headers,
    )

    response = await async_client.get(
        f"/api/v1/events/{event.id}/attendees",
        headers=user_headers,
    )

    assert response.status_code == 200
    attendees = response.json()
    assert len(attendees) == 1
    assert attendees[0]["user_id"] == str(test_user.id)
    assert attendees[0]["full_name"] == test_user.full_name
    assert attendees[0]["email"] == test_user.email
    assert attendees[0]["registered_at"]
    assert attendees[0]["status"] == EventRegistrationStatus.CONFIRMED.value
