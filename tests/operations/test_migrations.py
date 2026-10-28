import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

from operations.models import Alert


@pytest.mark.django_db(transaction=True)
def test_alert_severity_migration_backfills_fixture_and_legacy_rows() -> None:
    migration_executor = MigrationExecutor(connection)
    migration_executor.migrate([("operations", "0001_initial")])
    old_apps = migration_executor.loader.project_state(
        [("operations", "0001_initial")]
    ).apps
    old_service = old_apps.get_model("operations", "Service")
    old_alert = old_apps.get_model("operations", "Alert")

    api = old_service.objects.create(name="api")
    checkout = old_service.objects.create(name="checkout")
    database = old_service.objects.create(name="database")
    old_alert.objects.create(
        service=api,
        name="Elevated 5xx responses",
        message="5xx responses",
        status="firing",
    )
    old_alert.objects.create(
        service=checkout,
        name="Checkout error rate recovered",
        message="recovered",
        status="resolved",
    )
    old_alert.objects.create(
        service=database,
        name="Legacy alert",
        message="legacy",
        status="firing",
    )

    migration_executor = MigrationExecutor(connection)
    migration_executor.migrate([("operations", "0002_alert_severity")])

    assert Alert.objects.get(name="Elevated 5xx responses").severity == "critical"
    assert (
        Alert.objects.get(name="Checkout error rate recovered").severity == "info"
    )
    assert Alert.objects.get(name="Legacy alert").severity == "info"

    migration_executor = MigrationExecutor(connection)
    migration_executor.migrate(migration_executor.loader.graph.leaf_nodes())
