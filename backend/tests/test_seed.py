from contextlib import asynccontextmanager

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import seed
from app.models.models import (
    GlobalRole,
    Organization,
    OrganizationMember,
    OrgRole,
    User,
)


@pytest.mark.asyncio
async def test_seed_data_is_idempotent(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    @asynccontextmanager
    async def session_context():
        yield db_session

    monkeypatch.setattr(seed, "async_session_maker", lambda: session_context())

    await seed.seed_data()
    await seed.seed_data()

    admin = await db_session.scalar(
        select(User).where(User.email == "admin@ubbcluj.ro")
    )
    assert admin is not None
    assert admin.full_name == "Super Administrator UBB"
    assert admin.global_role == GlobalRole.SUPER_ADMIN
    assert admin.is_active is True

    organizations = list((await db_session.scalars(select(Organization))).all())
    assert {organization.name for organization in organizations} == {
        "OSUBB",
        "BEST Cluj-Napoca",
    }

    memberships = list(
        (
            await db_session.scalars(
                select(OrganizationMember).where(
                    OrganizationMember.user_id == admin.id
                )
            )
        ).all()
    )
    assert len(memberships) == 2
    assert {membership.role_in_org for membership in memberships} == {OrgRole.ORG_ADMIN}
