import asyncio
import logging
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_maker, engine
from app.core.migrations import run_migrations
from app.core.security import get_password_hash
from app.models.models import (
    GlobalRole,
    Organization,
    OrganizationMember,
    OrgRole,
    User,
)

logger = logging.getLogger(__name__)
INITIAL_ORGANIZATIONS = ("OSUBB", "BEST Cluj-Napoca")


async def seed_data() -> None:
    async with async_session_maker() as session:
        try:
            admin = await session.scalar(
                select(User).where(User.email == "admin@ubbcluj.ro")
            )
            if admin is None:
                admin = User(
                    email="admin@ubbcluj.ro",
                    full_name="Super Administrator UBB",
                    hashed_password=get_password_hash("Admin123456!"),
                    global_role=GlobalRole.SUPER_ADMIN,
                    is_active=True,
                )
                session.add(admin)
                await session.flush()
                logger.info("Created super admin account.")
            else:
                admin.full_name = "Super Administrator UBB"
                admin.global_role = GlobalRole.SUPER_ADMIN
                admin.is_active = True
                logger.info("Super admin account already exists.")

            for organization_name in INITIAL_ORGANIZATIONS:
                organization = await session.scalar(
                    select(Organization).where(Organization.name == organization_name)
                )
                if organization is None:
                    organization = Organization(name=organization_name)
                    session.add(organization)
                    await session.flush()
                    logger.info("Created organization %s.", organization_name)

                membership = await session.scalar(
                    select(OrganizationMember).where(
                        OrganizationMember.user_id == admin.id,
                        OrganizationMember.organization_id == organization.id,
                    )
                )
                if membership is None:
                    session.add(
                        OrganizationMember(
                            user_id=admin.id,
                            organization_id=organization.id,
                            role_in_org=OrgRole.ADMIN,
                        )
                    )
                elif membership.role_in_org != OrgRole.ADMIN:
                    membership.role_in_org = OrgRole.ADMIN

            await session.commit()
            logger.info("Seed data committed successfully.")
        except Exception:
            await session.rollback()
            logger.exception("Failed to seed application data.")
            raise


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    run_migrations()

    async def run() -> None:
        await seed_data()
        await engine.dispose()

    asyncio.run(run())


if __name__ == "__main__":
    main()
