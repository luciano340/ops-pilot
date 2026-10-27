from uuid import UUID

from operations.domain import (
    AlertPageDTO,
    IncidentDTO,
    ListAlertsDTO,
    OpenIncidentDTO,
    ResolveIncidentDTO,
)
from operations.store import OperationsStore


class OperationsService:
    def __init__(self, store: OperationsStore) -> None:
        self._store = store

    async def list_alerts(self, query: ListAlertsDTO) -> AlertPageDTO:
        if not 1 <= query.limit <= 100:
            raise ValueError("Alert page size must be between 1 and 100")
        if query.offset < 0:
            raise ValueError("Alert page offset must not be negative")
        if query.status not in (None, "firing", "resolved"):
            raise ValueError(f"Unsupported alert status: {query.status}")
        return await self._store.list_alerts(query)

    async def open_incident(self, payload: OpenIncidentDTO) -> IncidentDTO:
        if not payload.title.strip():
            raise ValueError("Incident title must not be empty")
        if not payload.service.strip():
            raise ValueError("Incident service must not be empty")
        if not payload.severity.strip():
            raise ValueError("Incident severity must not be empty")
        return await self._store.open_incident(payload)

    async def resolve_incident(self, incident_id: UUID) -> IncidentDTO:
        return await self._store.resolve_incident(
            ResolveIncidentDTO(id=incident_id)
        )
