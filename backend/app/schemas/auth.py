from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.models import GlobalRole, OrgRole


def _normalize_email(value: str) -> str:
    normalized = value.strip().lower()
    local_part, separator, domain = normalized.partition("@")
    if (
        not separator
        or not local_part
        or not domain
        or "@" in domain
        or "." not in domain
        or any(character.isspace() for character in normalized)
        or domain.startswith(".")
        or domain.endswith(".")
        or ".." in domain
    ):
        raise ValueError("A valid email address is required.")
    return normalized


class UserRegister(BaseModel):
    email: Annotated[str, Field(min_length=3, max_length=320)]
    password: Annotated[str, Field(min_length=8, max_length=72)]
    full_name: Annotated[str, Field(min_length=1, max_length=255)]

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return _normalize_email(value)

    @field_validator("password")
    @classmethod
    def limit_password_bytes(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Password must be no more than 72 UTF-8 bytes.")
        return value

    @field_validator("full_name")
    @classmethod
    def normalize_full_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Full name cannot be blank.")
        return normalized


class UserLogin(BaseModel):
    email: Annotated[str, Field(min_length=3, max_length=320)]
    password: Annotated[str, Field(min_length=1, max_length=72)]

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return _normalize_email(value)

    @field_validator("password")
    @classmethod
    def limit_password_bytes(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Password must be no more than 72 UTF-8 bytes.")
        return value


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class OrganizationMembershipResponse(BaseModel):
    organization_id: UUID
    organization_name: str
    role: OrgRole


class UserProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    full_name: str
    global_role: GlobalRole
    is_active: bool
    organization_memberships: list[OrganizationMembershipResponse]
