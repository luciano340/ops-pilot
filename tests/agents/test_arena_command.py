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
from agents.types import StrategyResult


def test_arena_command_rejects_invalid_strategy_before_creating_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_model_creation() -> None:
        pytest.fail("The model must not be constructed for invalid arguments")

    monkeypatch.setattr(arena_command, "create_model", fail_model_creation)

    with pytest.raises(CommandError, match="react|plan_and_execute"):
        call_command("arena", "check alerts", strategies="unknown")


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
