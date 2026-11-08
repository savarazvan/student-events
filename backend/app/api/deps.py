from collections.abc import Sequence
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.models import GlobalRole, Organization, OrganizationMember, OrgRole, User

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing authentication credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise unauthorized

    try:
        payload = decode_access_token(credentials.credentials)
        user_id = UUID(str(payload["sub"]))
    except (InvalidTokenError, KeyError, TypeError, ValueError):
        raise unauthorized from None

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise unauthorized
    return user


def require_global_role(role: GlobalRole):
    def role_dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.global_role != role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient global permissions.",
            )
        return current_user

    return role_dependency


def require_org_role(org_id_param: str, allowed_roles: Sequence[OrgRole]):
    async def role_dependency(
        request: Request,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        raw_org_id = request.path_params.get(org_id_param)
        try:
            organization_id = UUID(str(raw_org_id))
        except (TypeError, ValueError):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found.",
            ) from None

        organization_exists = await db.scalar(
            select(Organization.id).where(Organization.id == organization_id)
        )
        if organization_exists is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found.",
            )

        if current_user.global_role == GlobalRole.SUPER_ADMIN:
            return current_user

        membership_exists = await db.scalar(
            select(OrganizationMember.id).where(
                OrganizationMember.user_id == current_user.id,
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.role_in_org.in_(allowed_roles),
            )
        )
        if membership_exists is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions for this organization.",
            )
        return current_user

    return role_dependency
