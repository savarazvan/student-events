"""Public organization directory and self-service membership management.

Organization admins (``ORG_ADMIN``) manage their own organization's profile and
members here; super admins pass every check. Creating organizations stays a
super-admin operation (``/api/v1/admin/organizations``).
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status as http_status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_org_role
from app.core.database import get_db
from app.models.models import Event, EventTask, Organization, OrganizationMember, OrgRole, User
from app.schemas.admin import OrganizationResponse
from app.schemas.organization import (
    OrganizationMemberAdd,
    OrganizationMemberDetail,
    OrganizationMemberRoleUpdate,
    OrganizationUpdate,
)

router = APIRouter(prefix="/organizations", tags=["Organizations"])

ORG_NOT_FOUND_DETAIL = "Organization not found."
LAST_ADMIN_DETAIL = "An organization must keep at least one ORG_ADMIN."
ALL_ORG_ROLES = (OrgRole.ADMIN, OrgRole.ORGANIZER, OrgRole.MEMBER)


async def _get_organization_or_404(db: AsyncSession, org_id: UUID) -> Organization:
    organization = await db.get(Organization, org_id)
    if organization is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail=ORG_NOT_FOUND_DETAIL)
    return organization


async def _get_membership_or_404(
    db: AsyncSession, org_id: UUID, user_id: UUID
) -> OrganizationMember:
    membership = await db.scalar(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.user_id == user_id,
        )
    )
    if membership is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND, detail="Membership not found."
        )
    return membership


async def _ensure_not_last_admin(db: AsyncSession, membership: OrganizationMember) -> None:
    if membership.role_in_org != OrgRole.ADMIN:
        return
    admin_count = await db.scalar(
        select(func.count())
        .select_from(OrganizationMember)
        .where(
            OrganizationMember.organization_id == membership.organization_id,
            OrganizationMember.role_in_org == OrgRole.ADMIN,
        )
    )
    if (admin_count or 0) <= 1:
        raise HTTPException(status_code=http_status.HTTP_409_CONFLICT, detail=LAST_ADMIN_DETAIL)


async def _member_detail(
    db: AsyncSession, membership: OrganizationMember
) -> OrganizationMemberDetail:
    user = await db.get(User, membership.user_id)
    return OrganizationMemberDetail(
        user_id=user.id, full_name=user.full_name, email=user.email, role=membership.role_in_org
    )


@router.get("", response_model=list[OrganizationResponse])
async def list_organizations(db: AsyncSession = Depends(get_db)) -> list[Organization]:
    """Public directory, used by event filters and to show organizer names."""
    return list((await db.scalars(select(Organization).order_by(Organization.name))).all())


@router.get("/{org_id}", response_model=OrganizationResponse)
async def get_organization(org_id: UUID, db: AsyncSession = Depends(get_db)) -> Organization:
    return await _get_organization_or_404(db, org_id)


@router.patch(
    "/{org_id}",
    response_model=OrganizationResponse,
    dependencies=[Depends(require_org_role("org_id", [OrgRole.ADMIN]))],
)
async def update_organization(
    org_id: UUID,
    payload: OrganizationUpdate,
    db: AsyncSession = Depends(get_db),
) -> Organization:
    organization = await _get_organization_or_404(db, org_id)
    updates = payload.model_dump(exclude_unset=True)
    new_name = updates.get("name")
    if new_name is not None and new_name != organization.name:
        clash = await db.scalar(
            select(Organization.id).where(Organization.name == new_name, Organization.id != org_id)
        )
        if clash is not None:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="An organization with this name already exists.",
            )
    for field, value in updates.items():
        setattr(organization, field, value)
    await db.commit()
    await db.refresh(organization)
    return organization


@router.get(
    "/{org_id}/members",
    response_model=list[OrganizationMemberDetail],
    dependencies=[Depends(require_org_role("org_id", ALL_ORG_ROLES))],
)
async def list_members(
    org_id: UUID, db: AsyncSession = Depends(get_db)
) -> list[OrganizationMemberDetail]:
    rows = (
        await db.execute(
            select(OrganizationMember, User)
            .join(User, User.id == OrganizationMember.user_id)
            .where(OrganizationMember.organization_id == org_id)
            .order_by(User.full_name, User.email)
        )
    ).all()
    return [
        OrganizationMemberDetail(
            user_id=user.id, full_name=user.full_name, email=user.email, role=membership.role_in_org
        )
        for membership, user in rows
    ]


@router.post(
    "/{org_id}/members",
    response_model=OrganizationMemberDetail,
    dependencies=[Depends(require_org_role("org_id", [OrgRole.ADMIN]))],
)
async def add_member(
    org_id: UUID,
    payload: OrganizationMemberAdd,
    db: AsyncSession = Depends(get_db),
) -> OrganizationMemberDetail:
    """Add a registered user by e-mail, or change the role of an existing member."""
    user = await db.scalar(select(User).where(User.email == payload.email))
    if user is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="No account with this e-mail. Ask the person to register first.",
        )
    membership = await db.scalar(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.user_id == user.id,
        )
    )
    if membership is None:
        membership = OrganizationMember(
            organization_id=org_id, user_id=user.id, role_in_org=payload.role
        )
        db.add(membership)
    elif membership.role_in_org != payload.role:
        if payload.role != OrgRole.ADMIN:
            await _ensure_not_last_admin(db, membership)
        membership.role_in_org = payload.role
    await db.commit()
    await db.refresh(membership)
    return await _member_detail(db, membership)


@router.patch(
    "/{org_id}/members/{user_id}",
    response_model=OrganizationMemberDetail,
    dependencies=[Depends(require_org_role("org_id", [OrgRole.ADMIN]))],
)
async def update_member_role(
    org_id: UUID,
    user_id: UUID,
    payload: OrganizationMemberRoleUpdate,
    db: AsyncSession = Depends(get_db),
) -> OrganizationMemberDetail:
    membership = await _get_membership_or_404(db, org_id, user_id)
    if payload.role != OrgRole.ADMIN:
        await _ensure_not_last_admin(db, membership)
    membership.role_in_org = payload.role
    await db.commit()
    await db.refresh(membership)
    return await _member_detail(db, membership)


@router.delete(
    "/{org_id}/members/{user_id}",
    status_code=http_status.HTTP_204_NO_CONTENT,
    response_class=Response,
    dependencies=[Depends(require_org_role("org_id", [OrgRole.ADMIN]))],
)
async def remove_member(
    org_id: UUID,
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Remove a member; their open tasks in this organization's events become unassigned."""
    membership = await _get_membership_or_404(db, org_id, user_id)
    await _ensure_not_last_admin(db, membership)
    await db.execute(
        update(EventTask)
        .where(
            EventTask.assignee_id == user_id,
            EventTask.event_id.in_(select(Event.id).where(Event.organization_id == org_id)),
        )
        .values(assignee_id=None)
        .execution_options(synchronize_session=False)
    )
    await db.delete(membership)
    await db.commit()
    return Response(status_code=http_status.HTTP_204_NO_CONTENT)
