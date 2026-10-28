from uuid import UUID
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ListAlertsInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["firing", "resolved"] | None = None
    severity: Literal["critical", "warning", "info"] | None = None
    order: Literal["oldest", "newest"] = "newest"
    limit: int = Field(default=100, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class OpenIncidentInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str = Field(min_length=1)
    service: str = Field(min_length=1)
    severity: str = Field(min_length=1)


class ResolveIncidentInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
