from django.db import migrations, models
from django.db.backends.base.schema import BaseDatabaseSchemaEditor
from django.db.migrations.state import StateApps


def backfill_alert_severity(
    apps: StateApps,
    schema_editor: BaseDatabaseSchemaEditor,
) -> None:
    Alert = apps.get_model("operations", "Alert")
    Alert.objects.filter(
        service__name="api",
        name="Elevated 5xx responses",
        status="firing",
    ).update(severity="critical")
    Alert.objects.filter(
        service__name="checkout",
        name="Payment authorization latency",
        status="firing",
    ).update(severity="critical")
    Alert.objects.filter(
        service__name="worker",
        name="Queue backlog above threshold",
        status="firing",
    ).update(severity="critical")


class Migration(migrations.Migration):
    dependencies = [
        ("operations", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="alert",
            name="severity",
            field=models.CharField(
                choices=[
                    ("critical", "Critical"),
                    ("warning", "Warning"),
                    ("info", "Info"),
                ],
                default="info",
                max_length=10,
            ),
        ),
        migrations.RunPython(backfill_alert_severity, migrations.RunPython.noop),
    ]
