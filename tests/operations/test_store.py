import asyncio
from uuid import UUID

import pytest

from operations.domain import (
    IncidentAlreadyResolvedError,
    IncidentNotFoundError,
    ListAlertsDTO,
    OpenIncidentDTO,
    ResolveIncidentDTO,
    ServiceNotFoundError,
)
from operations.models import Alert, Incident, Service
from operations.store import OperationsStore


@pytest.mark.django_db(transaction=True)
def test_store_lists_filtered_alerts_with_total_and_page_limit() -> None:
    service = Service.objects.create(name="checkout")
    Alert.objects.create(
        service=service,
        name="latency",
        status=Alert.Status.FIRING,
        severity=Alert.Severity.CRITICAL,
    )
    Alert.objects.create(
        service=service,
        name="errors",
        status=Alert.Status.RESOLVED,
        severity=Alert.Severity.INFO,
    )

    page = asyncio.run(
        OperationsStore().list_alerts(
            ListAlertsDTO(status="firing", severity="critical", limit=1)
        )
    )

    assert len(page.items) == 1
    assert page.total == 1
    assert page.items[0].service == "checkout"
    assert page.items[0].status == "firing"
    assert page.items[0].severity == "critical"


@pytest.mark.django_db(transaction=True)
def test_store_opens_and_resolves_incident_and_rejects_repeat_resolution() -> None:
    service = Service.objects.create(name="checkout")
    store = OperationsStore()

    incident = asyncio.run(
        store.open_incident(
            OpenIncidentDTO(
                title="Elevated errors",
                service="checkout",
                severity="high",
            )
        )
    )
    resolved = asyncio.run(store.resolve_incident(ResolveIncidentDTO(incident.id)))

    assert resolved.status == Incident.Status.RESOLVED
    assert resolved.resolved_at is not None
    with pytest.raises(IncidentAlreadyResolvedError):
        asyncio.run(store.resolve_incident(ResolveIncidentDTO(incident.id)))


@pytest.mark.django_db(transaction=True)
def test_store_reports_missing_service_and_incident() -> None:
    store = OperationsStore()

    with pytest.raises(ServiceNotFoundError):
        asyncio.run(
            store.open_incident(
                OpenIncidentDTO(
                    title="Unavailable service",
                    service="missing",
                    severity="high",
                )
            )
        )
    with pytest.raises(IncidentNotFoundError):
        asyncio.run(
            store.resolve_incident(
                ResolveIncidentDTO(UUID("00000000-0000-0000-0000-000000000000"))
            )
        )
