from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Enum as SqlEnum, ForeignKey, Integer, String, Text, Uuid, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

_DELETE_ORPHAN_CASCADE = "all, delete-orphan"


class GlobalRole(str, Enum):
    SUPER_ADMIN = "SUPER_ADMIN"
    USER = "USER"


class OrgRole(str, Enum):
    ORG_ADMIN = "ORG_ADMIN"
    ADMIN = "ORG_ADMIN"
    ORGANIZER = "ORGANIZER"
    MEMBER = "MEMBER"


class EventStatus(str, Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    PUBLISHED = "PUBLISHED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    full_name: Mapped[str] = mapped_column(String, nullable=False)
    global_role: Mapped[GlobalRole] = mapped_column(
        SqlEnum(GlobalRole, name="global_role"), default=GlobalRole.USER, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    organization_memberships: Mapped[list[OrganizationMember]] = relationship(
        back_populates="user", cascade=_DELETE_ORPHAN_CASCADE
    )
    registrations: Mapped[list[Registration]] = relationship(
        back_populates="user", cascade=_DELETE_ORPHAN_CASCADE
    )


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    memberships: Mapped[list[OrganizationMember]] = relationship(
        back_populates="organization", cascade=_DELETE_ORPHAN_CASCADE
    )
    events: Mapped[list[Event]] = relationship(back_populates="organization")


class OrganizationMember(Base):
    __tablename__ = "organization_members"
    __table_args__ = (
        UniqueConstraint("user_id", "organization_id", name="uq_organization_members_user_org"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    role_in_org: Mapped[OrgRole] = mapped_column(
        SqlEnum(OrgRole, name="org_role"), default=OrgRole.ORGANIZER, nullable=False
    )

    user: Mapped[User] = relationship(back_populates="organization_memberships")
    organization: Mapped[Organization] = relationship(back_populates="memberships")


class Event(Base):
    __tablename__ = "events"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String, nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    location: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[EventStatus] = mapped_column(
        SqlEnum(EventStatus, name="event_status"), default=EventStatus.DRAFT, nullable=False
    )
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)

    organization: Mapped[Organization] = relationship(back_populates="events")
    registrations: Mapped[list[Registration]] = relationship(
        back_populates="event", cascade=_DELETE_ORPHAN_CASCADE
    )


class Registration(Base):
    __tablename__ = "registrations"
    __table_args__ = (UniqueConstraint("user_id", "event_id", name="uq_registrations_user_event"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    event_id: Mapped[UUID] = mapped_column(ForeignKey("events.id"), nullable=False)
    registered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    status: Mapped[str] = mapped_column(String, default="CONFIRMED", nullable=False)
    qr_code_token: Mapped[str] = mapped_column(String, nullable=False)

    user: Mapped[User] = relationship(back_populates="registrations")
    event: Mapped[Event] = relationship(back_populates="registrations")
