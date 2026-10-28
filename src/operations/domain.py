from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


class DomainError(Exception):
    pass


class ServiceNotFoundError(DomainError):
    pass


class IncidentNotFoundError(DomainError):
    pass


class IncidentAlreadyResolvedError(DomainError):
    pass


@dataclass(frozen=True, slots=True)
class ServiceDTO:
    id: UUID
    name: str
    description: str


@dataclass(frozen=True, slots=True)
class AlertDTO:
    id: UUID
    service: str
    name: str
    message: str
    status: str
    severity: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class IncidentDTO:
    id: UUID
    title: str
    service: str
    severity: str
    status: str
    resolved_at: datetime | None


@dataclass(frozen=True, slots=True)
class AlertPageDTO:
    items: list[AlertDTO]
    total: int


@dataclass(frozen=True, slots=True)
class ListAlertsDTO:
    status: str | None = None
    severity: str | None = None
    order: str = "newest"
    limit: int = 100
    offset: int = 0


@dataclass(frozen=True, slots=True)
class OpenIncidentDTO:
    title: str
    service: str
    severity: str


@dataclass(frozen=True, slots=True)
class ResolveIncidentDTO:
    id: UUID
