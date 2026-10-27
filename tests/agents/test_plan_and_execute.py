import asyncio
from collections.abc import Sequence
from typing import Any

from langchain_core.language_models import LanguageModelInput
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage
from langchain_core.runnables import Runnable, RunnableLambda
from langchain_core.tools import StructuredTool
from pydantic import BaseModel

from agents.plan_and_execute import (
    Plan,
    PlanAndExecuteStrategy,
    PlanReview,
    PlanStep,
)


class PlanFakeModel(FakeMessagesListChatModel):
    structured_responses: list[BaseModel]
    tool_responses: list[AIMessage]

    def __init__(
        self,
        *,
        structured_responses: Sequence[BaseModel],
        tool_responses: Sequence[AIMessage],
    ) -> None:
        super().__init__(
            responses=[],
            structured_responses=list(structured_responses),
            tool_responses=list(tool_responses),
        )

    def with_structured_output(
        self,
        schema: dict[str, Any] | type,
        *,
        include_raw: bool = False,
        **kwargs: Any,
    ) -> Runnable[Any, Any]:
        return RunnableLambda(lambda input: self.structured_responses.pop(0))

    def bind_tools(
        self,
        tools: Sequence[Any],
        *,
        tool_choice: str | None = None,
        **kwargs: Any,
    ) -> Runnable[LanguageModelInput, AIMessage]:
        return RunnableLambda(lambda input: self.tool_responses.pop(0))


async def _fake_list_alerts(status: str) -> str:
    return f"alerts filtered by {status}"


def _tool() -> StructuredTool:
    return StructuredTool.from_function(
        coroutine=_fake_list_alerts,
        name="list_alerts",
        description="List alerts.",
    )


def _tool_call() -> AIMessage:
    return AIMessage(
        content="",
        tool_calls=[
            {
                "name": "list_alerts",
                "args": {"status": "firing"},
                "id": "call-1",
            }
        ],
    )


def test_plan_and_execute_runs_one_tool_then_replans_to_completion() -> None:
    model = PlanFakeModel(
        structured_responses=[
            Plan(steps=[PlanStep(description="List firing alerts")]),
            PlanReview(steps=[], answer="There are no firing alerts."),
        ],
        tool_responses=[_tool_call()],
    )
    strategy = PlanAndExecuteStrategy(model, [_tool()])

    result = asyncio.run(strategy.run("Check firing alerts"))

    assert result.answer == "There are no firing alerts."
    assert result.metrics.llm_calls == 3
    assert [event.type for event in result.trace] == [
        "plan",
        "action",
        "observation",
        "critique",
        "plan",
        "answer",
    ]


def test_plan_and_execute_stops_at_iteration_limit_with_steps_remaining() -> None:
    model = PlanFakeModel(
        structured_responses=[
            Plan(
                steps=[
                    PlanStep(description="List firing alerts"),
                    PlanStep(description="Summarize alert owners"),
                ]
            ),
            PlanReview(
                steps=[PlanStep(description="Summarize alert owners")],
                answer=None,
            ),
        ],
        tool_responses=[_tool_call()],
    )
    strategy = PlanAndExecuteStrategy(model, [_tool()], max_iterations=1)

    result = asyncio.run(strategy.run("Review alerts"))

    assert "limit" in result.answer.lower()
    assert "Summarize alert owners" in result.answer
    assert result.metrics.llm_calls == 3
    assert sum(event.type == "action" for event in result.trace) == 1
