import asyncio

import pytest
from pydantic import ValidationError

from operations.domain import (
    IncidentAlreadyResolvedError,
    ListAlertsDTO,
    OpenIncidentDTO,
    ResolveIncidentDTO,
)
from operations.models import Alert, Service
from operations.schemas import ListAlertsInput, OpenIncidentInput, ResolveIncidentInput
from operations.services import OperationsService
from operations.store import OperationsStore


def test_tool_schemas_validate_status_nonempty_values_and_uuid() -> None:
    assert ListAlertsInput(status="firing").status == "firing"
    with pytest.raises(ValidationError):
        ListAlertsInput(status="unknown")
    with pytest.raises(ValidationError):
        OpenIncidentInput(title=" ", service="checkout", severity="high")
    with pytest.raises(ValidationError):
        ResolveIncidentInput(id="not-a-uuid")


@pytest.mark.django_db(transaction=True)
def test_services_list_and_create_incidents() -> None:
    service = Service.objects.create(name="checkout")
    Alert.objects.create(service=service, name="latency", status=Alert.Status.FIRING)

    async def invoke() -> tuple[int, str]:
        business = OperationsService(OperationsStore())
        page = await business.list_alerts(ListAlertsDTO(status=None))
        incident = await business.open_incident(
            OpenIncidentDTO("Elevated errors", "checkout", "high")
        )
        return page.total, incident.status

    total, status = asyncio.run(invoke())
    assert total == 1
    assert status == "open"


@pytest.mark.django_db(transaction=True)
def test_service_rejects_resolving_an_already_resolved_incident() -> None:
    service = Service.objects.create(name="checkout")

    async def invoke() -> None:
        store = OperationsStore()
        incident = await store.open_incident(
            OpenIncidentDTO("Elevated errors", "checkout", "high")
        )
        await store.resolve_incident(
            ResolveIncidentDTO(incident.id)
        )
        await OperationsService(store).resolve_incident(incident.id)

    with pytest.raises(IncidentAlreadyResolvedError):
        asyncio.run(invoke())
