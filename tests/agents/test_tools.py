import asyncio
import json
from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from agents.tools import get_agent_tools, list_alerts, open_incident, resolve_incident
from operations.models import Alert, Service
from operations.schemas import ListAlertsInput


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
    Alert.objects.create(
        service=service,
        name="latency",
        status=Alert.Status.FIRING,
        severity=Alert.Severity.CRITICAL,
    )

    result = asyncio.run(list_alerts(status="firing", severity="critical"))

    assert json.loads(result)["items"][0]["status"] == "firing"
    assert json.loads(result)["items"][0]["severity"] == "critical"


@pytest.mark.django_db(transaction=True)
def test_list_alerts_tool_exposes_timestamps_and_oldest_order() -> None:
    service = Service.objects.create(name="checkout")
    first = Alert.objects.create(
        service=service,
        name="first",
        status=Alert.Status.FIRING,
    )
    second = Alert.objects.create(
        service=service,
        name="second",
        status=Alert.Status.FIRING,
    )
    first_created = datetime(2026, 1, 1, tzinfo=timezone.utc)
    second_created = first_created + timedelta(days=1)
    Alert.objects.filter(pk=first.pk).update(created_at=first_created)
    Alert.objects.filter(pk=second.pk).update(created_at=second_created)

    result = json.loads(asyncio.run(list_alerts(status="firing", order="oldest")))

    assert [alert["name"] for alert in result["items"]] == ["first", "second"]
    assert result["items"][0]["created_at"] == first_created.isoformat()


def test_list_alerts_tool_documents_oldest_order_and_timestamps() -> None:
    tool = get_agent_tools()[0]

    assert "'oldest'" in tool.description
    assert "created_at" in tool.description
    assert ListAlertsInput.model_json_schema()["properties"]["order"]["enum"] == [
        "oldest",
        "newest",
    ]
