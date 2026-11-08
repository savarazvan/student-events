from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette.concurrency import run_in_threadpool

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.security import create_access_token, hash_password, verify_password
from app.models.models import OrganizationMember, User
from app.schemas.auth import (
    OrganizationMembershipResponse,
    TokenResponse,
    UserLogin,
    UserProfileResponse,
    UserRegister,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    payload: UserRegister,
    db: AsyncSession = Depends(get_db),
) -> UserProfileResponse:
    existing_user = await db.scalar(select(User.id).where(User.email == payload.email))
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists.",
        )

    user = User(
        email=payload.email,
        hashed_password=await run_in_threadpool(hash_password, payload.password),
        full_name=payload.full_name,
    )
    db.add(user)
    try:
        await db.commit()
        await db.refresh(user)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists.",
        ) from None

    return UserProfileResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        global_role=user.global_role,
        is_active=user.is_active,
        organization_memberships=[],
    )


@router.post("/login")
async def login(
    payload: UserLogin,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    user = await db.scalar(select(User).where(User.email == payload.email))
    password_matches = await run_in_threadpool(
        verify_password,
        payload.password,
        user.hashed_password if user is not None else "",
    )
    if user is None or not user.is_active or not password_matches:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return TokenResponse(access_token=create_access_token(user.id))


@router.get("/me")
async def read_current_user(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserProfileResponse:
    result = await db.execute(
        select(OrganizationMember)
        .options(selectinload(OrganizationMember.organization))
        .where(OrganizationMember.user_id == current_user.id)
    )
    memberships = result.scalars().all()

    return UserProfileResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        global_role=current_user.global_role,
        is_active=current_user.is_active,
        organization_memberships=[
            OrganizationMembershipResponse(
                organization_id=membership.organization_id,
                organization_name=membership.organization.name,
                role=membership.role_in_org,
            )
            for membership in memberships
        ],
    )
