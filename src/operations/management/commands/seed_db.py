import uuid
from typing import Any

from django.core.management import BaseCommand

from operations.models import Alert, Service

SERVICE_FIXTURE = (
    ("api", "Public API and request routing."),
    ("checkout", "Checkout and payment workflow."),
    ("database", "Primary relational datastore."),
    ("worker", "Asynchronous background processing."),
    ("web", "Customer-facing web application."),
)

ALERT_FIXTURE = (
    ("api", "Elevated 5xx responses", Alert.Status.FIRING, Alert.Severity.CRITICAL),
    (
        "checkout",
        "Payment authorization latency",
        Alert.Status.FIRING,
        Alert.Severity.CRITICAL,
    ),
    (
        "worker",
        "Queue backlog above threshold",
        Alert.Status.FIRING,
        Alert.Severity.CRITICAL,
    ),
    (
        "database",
        "Replica lag returned to normal",
        Alert.Status.RESOLVED,
        Alert.Severity.INFO,
    ),
    (
        "web",
        "Homepage availability recovered",
        Alert.Status.RESOLVED,
        Alert.Severity.INFO,
    ),
    (
        "checkout",
        "Checkout error rate recovered",
        Alert.Status.RESOLVED,
        Alert.Severity.INFO,
    ),
)

SEED_NAMESPACE = uuid.UUID("0ffea316-2752-4c70-9dba-30b73b081c57")


def _stable_id(kind: str, name: str) -> uuid.UUID:
    return uuid.uuid5(SEED_NAMESPACE, f"{kind}:{name}")


class Command(BaseCommand):
    help = "Create or refresh the OpsPilot sample services and alerts."

    def handle(self, *args: Any, **options: Any) -> None:
        services = [
            Service(
                id=_stable_id("service", name),
                name=name,
                description=description,
            )
            for name, description in SERVICE_FIXTURE
        ]
        Service.objects.bulk_create(
            services,
            update_conflicts=True,
            update_fields=["description"],
            unique_fields=["name"],
        )
        service_names = [name for name, _ in SERVICE_FIXTURE]
        services_by_name = {
            service.name: service
            for service in Service.objects.filter(name__in=service_names)
        }
        alerts = [
            Alert(
                id=_stable_id("alert", f"{service_name}:{name}"),
                service=services_by_name[service_name],
                name=name,
                message=name,
                status=status,
                severity=severity,
            )
            for service_name, name, status, severity in ALERT_FIXTURE
        ]
        Alert.objects.bulk_create(
            alerts,
            update_conflicts=True,
            update_fields=["message", "status", "severity"],
            unique_fields=["service", "name"],
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {len(services)} services and {len(alerts)} alerts."
            )
        )
