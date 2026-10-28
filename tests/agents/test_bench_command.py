import asyncio
from collections.abc import Sequence
from io import StringIO
import re
from typing import Any
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from django.core.management import CommandError, call_command
from django.utils import timezone

from agents.base import ReasoningStrategy
from agents.management.commands import bench as bench_command
from agents.types import ExecutionMetrics, StrategyResult
from operations.models import Alert, Incident, Service


class _BenchmarkStrategy(ReasoningStrategy):
    def __init__(self, name: str) -> None:
        self.name = name
        self.requests: list[str] = []
        self.event_loops: list[asyncio.AbstractEventLoop] = []

    async def run(self, input: str) -> StrategyResult:
        self.requests.append(input)
        self.event_loops.append(asyncio.get_running_loop())
        if input.startswith("Quantos alertas críticos"):
            answer = "Há 3 alertas críticos disparando."
        elif input.startswith("Abra três incidentes"):
            for service_name in ("checkout", "worker", "api"):
                service = await Service.objects.aget(name=service_name)
                incident = await Incident.objects.acreate(
                    id=uuid4(),
                    title=f"SEV2 incident for {service_name}",
                    service=service,
                    severity="SEV2",
                )
                if service_name == "checkout":
                    now = timezone.now()
                    await Incident.objects.filter(pk=incident.pk).aupdate(
                        status=Incident.Status.RESOLVED,
                        resolved_at=now,
                        updated_at=now,
                    )
            answer = (
                "Opened SEV2 incidents for checkout, worker, and api in order; "
                "checkout was resolved."
            )
        else:
            target = await Alert.objects.filter(
                status=Alert.Status.FIRING
            ).select_related("service").order_by("created_at", "id").afirst()
            assert target is not None
            await Incident.objects.acreate(
                id=uuid4(),
                title=f"Incident for {target.service.name}",
                service_id=target.service_id,
                severity="SEV2",
            )
            answer = "2 alertas firing sobraram."
        return StrategyResult(
            answer=answer,
            trace=[],
            metrics=ExecutionMetrics(llm_calls=2, latency_ms=1.5),
        )


def _install_fake_strategies(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[Mock, _BenchmarkStrategy, _BenchmarkStrategy]:
    react = _BenchmarkStrategy("react")
    plan_and_execute = _BenchmarkStrategy("plan_and_execute")
    model = Mock()
    model.root_async_client.close = AsyncMock()
    monkeypatch.setattr(bench_command, "create_model", lambda: model)
    monkeypatch.setattr(bench_command, "get_agent_tools", lambda: [])
    monkeypatch.setattr(bench_command, "ReactStrategy", lambda model, tools: react)
    monkeypatch.setattr(
        bench_command,
        "PlanAndExecuteStrategy",
        lambda model, tools, *, max_iterations, no_replanner: plan_and_execute,
    )
    return model, react, plan_and_execute


@pytest.mark.django_db(transaction=True)
def test_bench_runs_default_matrix_and_preserves_existing_incidents(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model, react, plan_and_execute = _install_fake_strategies(monkeypatch)
    call_command("seed_db")
    checkout = Service.objects.get(name="checkout")
    existing = Incident.objects.create(
        title="Preexisting checkout incident",
        service=checkout,
        severity="SEV3",
    )
    output = StringIO()

    call_command("bench", stdout=output)

    assert len(react.requests) == 3
    assert len(plan_and_execute.requests) == 3
    result_rows = output.getvalue().splitlines()[2:]
    assert sum(bool(re.search(r"\|\s+react\s+\|", row)) for row in result_rows) == 3
    assert sum(
        bool(re.search(r"\|\s+plan_and_execute\s+\|", row))
        for row in result_rows
    ) == 3
    assert "Cenário" in output.getvalue()
    assert "Chamadas LLM" in output.getvalue()
    assert Incident.objects.filter(pk=existing.pk).exists()
    assert Incident.objects.count() == 9
    assert model.root_async_client.close.await_count == 1
    loops = react.event_loops + plan_and_execute.event_loops
    assert len({id(loop) for loop in loops}) == 1


@pytest.mark.django_db(transaction=True)
def test_bench_accepts_scenario_alias_and_strategy_filter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model, react, plan_and_execute = _install_fake_strategies(monkeypatch)
    output = StringIO()

    call_command(
        "bench",
        scenario="c1",
        strategies="react",
        stdout=output,
    )

    assert len(react.requests) == 1
    assert plan_and_execute.requests == []
    model.root_async_client.close.assert_awaited_once()
    assert output.getvalue().count("c1") == 1
    assert "PASS" in output.getvalue()


def test_bench_rejects_invalid_selectors_before_seed_or_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail() -> None:
        pytest.fail("Seed and model creation must not run for invalid selectors")

    monkeypatch.setattr(bench_command, "create_model", fail)
    monkeypatch.setattr(bench_command, "call_command", fail)

    with pytest.raises(CommandError):
        call_command("bench", scenario="unknown", strategies="react")
    with pytest.raises(CommandError):
        call_command("bench", scenario="c1", strategies="")
    with pytest.raises(CommandError):
        call_command("bench", scenario="c1", strategies="react,unknown")


def test_bench_parser_accepts_short_scenario_flag() -> None:
    parser = bench_command.Command().create_parser("manage.py", "bench")

    options = parser.parse_args(["-s", "c2", "--strategies", "react"])

    assert options.scenario == "c2"
    assert options.strategies == "react"


@pytest.mark.django_db(transaction=True)
def test_bench_reports_failed_validation_and_raises_command_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class IncorrectAnswer(_BenchmarkStrategy):
        async def run(self, input: str) -> StrategyResult:
            return StrategyResult(
                answer="There are 30 critical alerts.",
                trace=[],
                metrics=ExecutionMetrics(llm_calls=1, latency_ms=1),
            )

    strategy = IncorrectAnswer("react")
    model = Mock()
    model.root_async_client.close = AsyncMock()
    monkeypatch.setattr(bench_command, "create_model", lambda: model)
    monkeypatch.setattr(bench_command, "get_agent_tools", lambda: [])
    monkeypatch.setattr(bench_command, "ReactStrategy", lambda model, tools: strategy)
    output = StringIO()

    with pytest.raises(CommandError, match="benchmark case"):
        call_command(
            "bench",
            scenario="all",
            strategies="react",
            stdout=output,
        )

    assert "FAIL" in output.getvalue()
    assert output.getvalue().count("| react") == 3
    assert "expected critical firing alert count" in output.getvalue()
    assert model.root_async_client.close.await_count == 1


@pytest.mark.django_db(transaction=True)
def test_bench_passes_no_replanner_flag_only_to_plan_and_execute(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    strategy = _BenchmarkStrategy("plan_and_execute")
    received: list[dict[str, Any]] = []
    model = Mock()
    model.root_async_client.close = AsyncMock()
    monkeypatch.setattr(bench_command, "create_model", lambda: model)
    monkeypatch.setattr(bench_command, "get_agent_tools", lambda: [])
    monkeypatch.setattr(bench_command, "ReactStrategy", lambda model, tools: None)

    def build_plan_strategy(
        model: object,
        tools: Sequence[object],
        *,
        max_iterations: int,
        no_replanner: bool,
    ) -> _BenchmarkStrategy:
        received.append(
            {"max_iterations": max_iterations, "no_replanner": no_replanner}
        )
        return strategy

    monkeypatch.setattr(
        bench_command,
        "PlanAndExecuteStrategy",
        build_plan_strategy,
    )

    call_command(
        "bench",
        scenario="c1",
        strategies="plan_and_execute",
        no_replanner=True,
        stdout=StringIO(),
    )

    assert received == [{"max_iterations": 8, "no_replanner": True}]
