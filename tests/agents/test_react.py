import asyncio
from collections.abc import Callable, Sequence

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.tools import StructuredTool

from agents.react import ReactStrategy


async def _lookup_alerts(status: str) -> str:
    return f'{{"status": "{status}", "total": 0}}'


def test_react_strategy_returns_final_answer_and_counts_model_calls(
    fake_tool_calling_model: Callable[[Sequence[AIMessage]], BaseChatModel],
) -> None:
    model = fake_tool_calling_model(
        [AIMessage(content="No active alerts were found.")]
    )

    result = asyncio.run(ReactStrategy(model, []).run("List firing alerts"))

    assert result.answer == "No active alerts were found."
    assert result.metrics.llm_calls == 1
    assert [event.type for event in result.trace] == ["answer"]


def test_react_strategy_records_tool_action_and_observation(
    fake_tool_calling_model: Callable[[Sequence[AIMessage]], BaseChatModel],
) -> None:
    tool = StructuredTool.from_function(
        coroutine=_lookup_alerts,
        name="list_alerts",
        description="List alerts by status.",
    )
    model = fake_tool_calling_model(
        [
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "list_alerts",
                        "args": {"status": "firing"},
                        "id": "call-1",
                    }
                ],
            ),
            AIMessage(content="There are no firing alerts."),
        ]
    )

    result = asyncio.run(
        ReactStrategy(model, [tool]).run("List firing alerts")
    )

    assert result.answer == "There are no firing alerts."
    assert result.metrics.llm_calls == 2
    assert [event.type for event in result.trace] == [
        "action",
        "observation",
        "answer",
    ]
    assert result.trace[0].tool == "list_alerts"
    assert result.trace[0].args == {"status": "firing"}
