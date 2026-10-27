import pytest
from django.core.management import call_command

from operations.models import Alert, Service


@pytest.mark.django_db
def test_seed_db_is_repeatable_with_expected_fixture_counts() -> None:
    call_command("seed_db")
    call_command("seed_db")

    assert Service.objects.count() == 5
    assert Alert.objects.count() == 6
    assert Alert.objects.filter(status=Alert.Status.FIRING).count() == 3
    assert Alert.objects.filter(status=Alert.Status.RESOLVED).count() == 3


@pytest.mark.django_db
def test_seed_db_preserves_records_outside_its_fixture() -> None:
    external_service = Service.objects.create(name="external-service")
    external_alert = Alert.objects.create(
        service=external_service,
        name="external-alert",
        status=Alert.Status.FIRING,
    )

    call_command("seed_db")

    assert Service.objects.filter(pk=external_service.pk).exists()
    assert Alert.objects.filter(pk=external_alert.pk).exists()
    assert Service.objects.count() == 6
    assert Alert.objects.count() == 7
