from uuid import UUID

from django.utils import timezone

from operations.domain import (
    AlertDTO,
    AlertPageDTO,
    IncidentAlreadyResolvedError,
    IncidentDTO,
    IncidentNotFoundError,
    ListAlertsDTO,
    OpenIncidentDTO,
    ResolveIncidentDTO,
    ServiceNotFoundError,
)
from operations.models import Alert, Incident, Service


class OperationsStore:
    async def list_alerts(self, query: ListAlertsDTO) -> AlertPageDTO:
        ordering = (
            ("created_at", "id")
            if query.order == "oldest"
            else ("-created_at", "id")
        )
        queryset = Alert.objects.select_related("service").order_by(*ordering)
        if query.status is not None:
            queryset = queryset.filter(status=query.status)
        if query.severity is not None:
            queryset = queryset.filter(severity=query.severity)

        async def collect_page() -> list[AlertDTO]:
            items: list[AlertDTO] = []
            rows = queryset.values(
                "id",
                "service__name",
                "name",
                "message",
                "status",
                "severity",
                "created_at",
            )[query.offset : query.offset + query.limit]
            async for row in rows:
                items.append(
                    AlertDTO(
                        id=row["id"],
                        service=row["service__name"],
                        name=row["name"],
                        message=row["message"],
                        status=row["status"],
                        severity=row["severity"],
                        created_at=row["created_at"],
                    )
                )
            return items

        total = await queryset.acount()
        items = await collect_page()
        return AlertPageDTO(items=items, total=total)

    async def open_incident(self, payload: OpenIncidentDTO) -> IncidentDTO:
        service_id = await Service.objects.filter(name=payload.service).values_list(
            "id", flat=True
        ).afirst()
        if service_id is None:
            raise ServiceNotFoundError(f"Service '{payload.service}' was not found")

        incident = await Incident.objects.acreate(
            title=payload.title,
            service_id=service_id,
            severity=payload.severity,
        )
        return IncidentDTO(
            id=incident.id,
            title=incident.title,
            service=payload.service,
            severity=incident.severity,
            status=incident.status,
            resolved_at=incident.resolved_at,
        )

    async def resolve_incident(self, payload: ResolveIncidentDTO) -> IncidentDTO:
        now = timezone.now()
        updated = await Incident.objects.filter(
            id=payload.id,
            status=Incident.Status.OPEN,
        ).aupdate(
            status=Incident.Status.RESOLVED,
            resolved_at=now,
            updated_at=now,
        )
        if updated == 0:
            existing = await Incident.objects.filter(id=payload.id).values(
                "id",
                "title",
                "service__name",
                "severity",
                "status",
                "resolved_at",
            ).afirst()
            if existing is None:
                raise IncidentNotFoundError(
                    f"Incident '{payload.id}' was not found"
                )
            raise IncidentAlreadyResolvedError(
                f"Incident '{payload.id}' is already resolved"
            )

        row = await Incident.objects.filter(id=payload.id).values(
            "id",
            "title",
            "service__name",
            "severity",
            "status",
            "resolved_at",
        ).aget()
        return IncidentDTO(
            id=row["id"],
            title=row["title"],
            service=row["service__name"],
            severity=row["severity"],
            status=row["status"],
            resolved_at=row["resolved_at"],
        )

    async def get_service_id(self, name: str) -> UUID:
        service = await Service.objects.filter(name=name).only("id").afirst()
        if service is None:
            raise ServiceNotFoundError(f"Service '{name}' was not found")
        return service.id
