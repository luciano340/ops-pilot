import asyncio
import json

import pytest
from pydantic import ValidationError

from agents.tools import list_alerts, open_incident, resolve_incident
from operations.models import Alert, Service


@pytest.mark.django_db(transaction=True)
def test_list_alerts_tool_rejects_unsupported_status() -> None:
    with pytest.raises(ValidationError):
        asyncio.run(list_alerts(status="unknown"))


@pytest.mark.django_db(transaction=True)
def test_open_and_resolve_incident_tools_use_persistent_service() -> None:
    Service.objects.create(name="checkout")
    created = asyncio.run(
        open_incident(
            title="Elevated errors",
            service="checkout",
            severity="high",
        )
    )

    assert json.loads(created)["status"] == "open"
    resolved = asyncio.run(resolve_incident(id=json.loads(created)["id"]))
    assert json.loads(resolved)["status"] == "resolved"


@pytest.mark.django_db(transaction=True)
def test_list_alerts_tool_returns_json_and_optional_status_filter() -> None:
    service = Service.objects.create(name="checkout")
    Alert.objects.create(service=service, name="latency", status=Alert.Status.FIRING)

    result = asyncio.run(list_alerts(status="firing"))

    assert json.loads(result)["items"][0]["status"] == "firing"
