from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.models import GlobalRole, OrgRole


class OrganizationCreate(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=255)]
    description: str | None = None
    contact_email: Annotated[str, Field(min_length=3, max_length=320)]

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Organization name cannot be blank.")
        return normalized

    @field_validator("contact_email")
    @classmethod
    def normalize_contact_email(cls, value: str) -> str:
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
            raise ValueError("A valid contact email address is required.")
        return normalized


class OrganizationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    contact_email: str | None


class AssignOrgMember(BaseModel):
    user_id: UUID
    role: OrgRole


class OrganizationMemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    organization_id: UUID
    role_in_org: OrgRole


class UpdateGlobalRole(BaseModel):
    global_role: GlobalRole


class AdminUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    full_name: str
    global_role: GlobalRole
    is_active: bool
