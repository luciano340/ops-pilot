import json
from dataclasses import asdict
from typing import Any

from langchain_core.tools import StructuredTool

from operations.domain import ListAlertsDTO, OpenIncidentDTO
from operations.schemas import (
    ListAlertsInput,
    OpenIncidentInput,
    ResolveIncidentInput,
)
from operations.services import OperationsService
from operations.store import OperationsStore


def _service() -> OperationsService:
    return OperationsService(OperationsStore())


def _to_json(value: object) -> str:
    return json.dumps(value, default=str, ensure_ascii=False, sort_keys=True)


async def list_alerts(
    status: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> str:
    payload = ListAlertsInput.model_validate(
        {"status": status, "limit": limit, "offset": offset}
    )
    page = await _service().list_alerts(
        ListAlertsDTO(
            status=payload.status,
            limit=payload.limit,
            offset=payload.offset,
        )
    )
    return _to_json(
        {
            "items": [asdict(alert) for alert in page.items],
            "total": page.total,
        }
    )


async def open_incident(title: str, service: str, severity: str) -> str:
    payload = OpenIncidentInput.model_validate(
        {"title": title, "service": service, "severity": severity}
    )
    incident = await _service().open_incident(
        OpenIncidentDTO(
            title=payload.title,
            service=payload.service,
            severity=payload.severity,
        )
    )
    return _to_json(asdict(incident))


async def resolve_incident(id: str) -> str:
    payload = ResolveIncidentInput.model_validate({"id": id})
    incident = await _service().resolve_incident(payload.id)
    return _to_json(asdict(incident))


def get_agent_tools() -> list[StructuredTool]:
    return [
        StructuredTool.from_function(
            coroutine=list_alerts,
            name="list_alerts",
            description="List operational alerts, optionally filtered by status.",
            args_schema=ListAlertsInput,
        ),
        StructuredTool.from_function(
            coroutine=open_incident,
            name="open_incident",
            description="Open an incident for an existing service.",
            args_schema=OpenIncidentInput,
        ),
        StructuredTool.from_function(
            coroutine=resolve_incident,
            name="resolve_incident",
            description="Resolve an existing incident by UUID.",
            args_schema=ResolveIncidentInput,
        ),
    ]
