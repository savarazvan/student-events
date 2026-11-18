from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.models import OrgRole
from app.schemas.admin import OrganizationCreate


class OrganizationUpdate(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=255)] | None = None
    description: str | None = None
    contact_email: Annotated[str, Field(min_length=3, max_length=320)] | None = None

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str | None) -> str | None:
        return None if value is None else OrganizationCreate.normalize_name(value)

    @field_validator("contact_email")
    @classmethod
    def normalize_contact_email(cls, value: str | None) -> str | None:
        return None if value is None else OrganizationCreate.normalize_contact_email(value)

    @model_validator(mode="after")
    def validate_non_nullable_fields(self) -> "OrganizationUpdate":
        if "name" in self.model_fields_set and self.name is None:
            raise ValueError("name cannot be null.")
        return self


class OrganizationMemberDetail(BaseModel):
    user_id: UUID
    full_name: str
    email: str
    role: OrgRole


class OrganizationMemberAdd(BaseModel):
    email: Annotated[str, Field(min_length=3, max_length=320)]
    role: OrgRole = OrgRole.MEMBER

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class OrganizationMemberRoleUpdate(BaseModel):
    role: OrgRole
