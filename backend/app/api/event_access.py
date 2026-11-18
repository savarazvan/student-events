"""Shared permission checks for event-scoped endpoints."""

from collections.abc import Sequence
from uuid import UUID

from fastapi import HTTPException, status as http_status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Event, EventStatus, GlobalRole, OrganizationMember, OrgRole, User
from app.services.registrations import EVENT_NOT_FOUND_DETAIL

EVENT_MANAGER_ROLES: tuple[OrgRole, ...] = (OrgRole.ADMIN, OrgRole.ORGANIZER)
ORG_MEMBER_ROLES: tuple[OrgRole, ...] = (OrgRole.ADMIN, OrgRole.ORGANIZER, OrgRole.MEMBER)
# Statuses anyone may see; DRAFT/SUBMITTED are visible to the organization's managers only.
PUBLIC_STATUSES: tuple[EventStatus, ...] = (
    EventStatus.PUBLISHED,
    EventStatus.IN_PROGRESS,
    EventStatus.COMPLETED,
    EventStatus.CANCELLED,
)


async def get_event_or_404(db: AsyncSession, event_id: UUID) -> Event:
    event = await db.get(Event, event_id)
    if event is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND, detail=EVENT_NOT_FOUND_DETAIL
        )
    return event


async def has_org_role(
    db: AsyncSession,
    user: User | None,
    organization_id: UUID,
    allowed_roles: Sequence[OrgRole],
) -> bool:
    if user is None:
        return False
    if user.global_role == GlobalRole.SUPER_ADMIN:
        return True
    membership_exists = await db.scalar(
        select(OrganizationMember.id).where(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.user_id == user.id,
            OrganizationMember.role_in_org.in_(allowed_roles),
        )
    )
    return membership_exists is not None


async def is_event_manager(
    db: AsyncSession,
    user: User | None,
    event: Event,
    allowed_roles: Sequence[OrgRole] = EVENT_MANAGER_ROLES,
) -> bool:
    return await has_org_role(db, user, event.organization_id, allowed_roles)


async def require_event_manager(
    db: AsyncSession,
    user: User,
    event: Event,
    allowed_roles: Sequence[OrgRole] = EVENT_MANAGER_ROLES,
) -> None:
    if not await is_event_manager(db, user, event, allowed_roles):
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions for this event.",
        )


async def get_visible_event(db: AsyncSession, event_id: UUID, user: User | None) -> Event:
    """The event, or 404 when it does not exist or is unpublished and the user is no manager."""
    event = await get_event_or_404(db, event_id)
    if event.status not in PUBLIC_STATUSES and not await is_event_manager(db, user, event):
        # Do not reveal that unpublished events exist.
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND, detail=EVENT_NOT_FOUND_DETAIL
        )
    return event
