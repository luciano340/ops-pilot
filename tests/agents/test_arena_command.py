from collections.abc import Sequence
from io import StringIO
from unittest.mock import Mock

import pytest
from django.core.management import CommandError, call_command
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage

from agents.base import ReasoningStrategy
from agents.errors import StructuredOutputError
from agents.management.commands import arena as arena_command
from agents.reflection import CritiqueOutput, ReflectionStrategy
from agents.types import ExecutionMetrics, StrategyResult


class _NamedStrategy(ReasoningStrategy):
    def __init__(self, name: str) -> None:
        self.name = name

    async def run(self, input: str) -> StrategyResult:
        return StrategyResult(
            answer="answer",
            trace=[],
            metrics=ExecutionMetrics(llm_calls=0, latency_ms=0),
        )


def test_arena_command_rejects_invalid_strategy_before_creating_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_model_creation() -> None:
        pytest.fail("The model must not be constructed for invalid arguments")

    monkeypatch.setattr(arena_command, "create_model", fail_model_creation)

    with pytest.raises(CommandError, match="react|plan_and_execute"):
        call_command("arena", "check alerts", strategies="unknown")


def test_arena_command_rejects_duplicate_strategy_before_creating_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_model_creation() -> None:
        pytest.fail("The model must not be constructed for invalid arguments")

    monkeypatch.setattr(arena_command, "create_model", fail_model_creation)

    with pytest.raises(CommandError, match="duplicates"):
        call_command("arena", "check alerts", strategies="react,react")


@pytest.mark.parametrize(
    ("selector", "base_name"),
    [
        ("reflect:react", "react"),
        ("reflect:plan_and_execute", "plan_and_execute"),
    ],
)
def test_arena_command_builds_selected_reflection_wrapper(
    selector: str,
    base_name: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model = Mock()
    evaluator = Mock()
    model.with_structured_output.return_value = evaluator
    base_strategy = _NamedStrategy(base_name)
    selected_strategies: list[ReasoningStrategy] = []

    async def fake_run_strategies(
        request: str,
        strategies: Sequence[ReasoningStrategy],
    ) -> dict[str, StrategyResult]:
        selected_strategies.extend(strategies)
        return {
            strategy.name: StrategyResult(
                answer="answer",
                trace=[],
                metrics=ExecutionMetrics(
                    llm_calls=0,
                    latency_ms=0,
                ),
            )
            for strategy in strategies
        }

    monkeypatch.setattr(arena_command, "create_model", lambda: model)
    monkeypatch.setattr(arena_command, "get_agent_tools", lambda: [])
    monkeypatch.setattr(arena_command, "run_strategies", fake_run_strategies)
    monkeypatch.setattr(
        arena_command,
        "ReactStrategy",
        lambda model, tools: base_strategy,
    )
    monkeypatch.setattr(
        arena_command,
        "PlanAndExecuteStrategy",
        lambda model, tools, *, max_iterations: base_strategy,
    )

    call_command(
        "arena",
        "Check active alerts",
        strategies=selector,
        stdout=StringIO(),
    )

    assert len(selected_strategies) == 1
    reflected = selected_strategies[0]
    assert isinstance(reflected, ReflectionStrategy)
    assert reflected.name == selector
    assert reflected._strategy is base_strategy
    assert reflected._evaluator is evaluator
    model.with_structured_output.assert_called_once_with(CritiqueOutput)


def test_arena_command_runs_selected_strategy_with_injected_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model = FakeMessagesListChatModel(
        responses=[AIMessage(content="There are no active alerts.")]
    )
    output = StringIO()
    monkeypatch.setattr(arena_command, "create_model", lambda: model)
    monkeypatch.setattr(arena_command, "get_agent_tools", lambda: [])

    call_command(
        "arena",
        "Check active alerts",
        strategies="react",
        stdout=output,
    )

    assert "There are no active alerts." in output.getvalue()
    assert "llm_calls: 1" in output.getvalue()


def test_arena_command_presents_structured_output_error_without_traceback(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    async def fail_run_strategies(
        request: str,
        strategies: Sequence[ReasoningStrategy],
    ) -> dict[str, StrategyResult]:
        raise StructuredOutputError()

    monkeypatch.setattr(arena_command, "create_model", Mock)
    monkeypatch.setattr(arena_command, "get_agent_tools", lambda: [])
    monkeypatch.setattr(arena_command, "run_strategies", fail_run_strategies)

    with pytest.raises(SystemExit) as exc_info:
        arena_command.Command().run_from_argv(
            [
                "manage.py",
                "arena",
                "Check active alerts",
                "--strategies",
                "plan_and_execute",
            ]
        )

    captured = capsys.readouterr()
    assert exc_info.value.code == 1
    assert "The model returned an invalid structured response." in captured.err
    assert "Traceback" not in captured.err
