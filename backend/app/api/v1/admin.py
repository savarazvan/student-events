from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_global_role
from app.core.database import get_db
from app.models.models import GlobalRole, Organization, OrganizationMember, User
from app.schemas.admin import (
    AdminUserResponse,
    AssignOrgMember,
    OrganizationCreate,
    OrganizationMemberResponse,
    OrganizationResponse,
    UpdateGlobalRole,
)

router = APIRouter(
    tags=["Admin"],
    dependencies=[Depends(require_global_role(GlobalRole.SUPER_ADMIN))],
)


@router.post(
    "/organizations",
    response_model=OrganizationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_organization(
    payload: OrganizationCreate,
    db: AsyncSession = Depends(get_db),
) -> Organization:
    existing = await db.scalar(
        select(Organization.id).where(Organization.name == payload.name)
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An organization with this name already exists.",
        )

    organization = Organization(
        name=payload.name,
        description=payload.description,
        contact_email=payload.contact_email,
    )
    db.add(organization)
    try:
        await db.commit()
        await db.refresh(organization)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An organization with this name already exists.",
        ) from None
    return organization


@router.get("/organizations", response_model=list[OrganizationResponse])
async def list_organizations(
    db: AsyncSession = Depends(get_db),
) -> list[Organization]:
    result = await db.scalars(select(Organization).order_by(Organization.name))
    return list(result.all())


@router.post(
    "/organizations/{org_id}/members",
    response_model=OrganizationMemberResponse,
)
async def assign_organization_member(
    org_id: UUID,
    payload: AssignOrgMember,
    db: AsyncSession = Depends(get_db),
) -> OrganizationMember:
    organization = await db.get(Organization, org_id)
    if organization is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found.",
        )

    user = await db.get(User, payload.user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    membership = await db.scalar(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.user_id == payload.user_id,
        )
    )
    if membership is None:
        membership = OrganizationMember(
            organization_id=org_id,
            user_id=payload.user_id,
            role_in_org=payload.role,
        )
        db.add(membership)
    else:
        membership.role_in_org = payload.role

    await db.commit()
    await db.refresh(membership)
    return membership


@router.patch(
    "/users/{user_id}/global-role",
    response_model=AdminUserResponse,
)
async def update_global_role(
    user_id: UUID,
    payload: UpdateGlobalRole,
    db: AsyncSession = Depends(get_db),
) -> User:
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    user.global_role = payload.global_role
    await db.commit()
    await db.refresh(user)
    return user
