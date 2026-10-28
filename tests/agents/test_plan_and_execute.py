import asyncio
from collections.abc import Sequence
from typing import Any

import pytest
from langchain_core.language_models import LanguageModelInput
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage
from langchain_core.runnables import Runnable, RunnableLambda
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, ValidationError

from agents.errors import StructuredOutputError
from agents.plan_and_execute import (
    Plan,
    PlanAndExecuteStrategy,
    PlanReview,
    PlanStep,
)


class PlanFakeModel(FakeMessagesListChatModel):
    structured_responses: list[BaseModel | Exception]
    structured_inputs: list[Any]
    tool_responses: list[AIMessage]

    def __init__(
        self,
        *,
        structured_responses: Sequence[BaseModel | Exception],
        tool_responses: Sequence[AIMessage],
        responses: Sequence[AIMessage] = (),
    ) -> None:
        super().__init__(
            responses=list(responses),
            structured_responses=list(structured_responses),
            structured_inputs=[],
            tool_responses=list(tool_responses),
        )

    def with_structured_output(
        self,
        schema: dict[str, Any] | type,
        *,
        include_raw: bool = False,
        **kwargs: Any,
    ) -> Runnable[Any, Any]:
        def invoke(input: Any) -> Any:
            self.structured_inputs.append(input)
            response = self.structured_responses.pop(0)
            if isinstance(response, Exception):
                raise response
            return response

        return RunnableLambda(invoke)

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


async def _fake_open_incident(
    title: str,
    service: str,
    severity: str,
) -> str:
    return f"created incident: {title} ({service}, {severity})"


def _tool() -> StructuredTool:
    return StructuredTool.from_function(
        coroutine=_fake_list_alerts,
        name="list_alerts",
        description="List alerts.",
    )


def _incident_tool() -> StructuredTool:
    return StructuredTool.from_function(
        coroutine=_fake_open_incident,
        name="open_incident",
        description="Open an incident for an existing service.",
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


def _incident_tool_call() -> AIMessage:
    return AIMessage(
        content="",
        tool_calls=[
            {
                "name": "open_incident",
                "args": {
                    "title": "Checkout errors",
                    "service": "checkout",
                    "severity": "2",
                },
                "id": "call-open-incident",
            }
        ],
    )


def _validation_error() -> ValidationError:
    try:
        Plan.model_validate(
            {"steps": [{}], "sensitive": "must not appear in the user message"}
        )
    except ValidationError as exc:
        return exc
    raise AssertionError("Expected invalid plan data to raise ValidationError")


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


def test_plan_and_execute_without_replanner_synthesizes_one_final_answer() -> None:
    model = PlanFakeModel(
        structured_responses=[
            Plan(steps=[PlanStep(description="List firing alerts")]),
        ],
        tool_responses=[_tool_call()],
        responses=[AIMessage(content="There are no firing alerts.")],
    )
    strategy = PlanAndExecuteStrategy(model, [_tool()], no_replanner=True)

    result = asyncio.run(strategy.run("Check firing alerts"))

    assert result.answer == "There are no firing alerts."
    assert result.metrics.llm_calls == 3
    assert len(model.structured_inputs) == 1
    assert [event.type for event in result.trace] == [
        "plan",
        "action",
        "observation",
        "answer",
    ]


def test_plan_and_execute_without_replanner_runs_all_initial_steps_in_order() -> None:
    model = PlanFakeModel(
        structured_responses=[
            Plan(
                steps=[
                    PlanStep(description="List firing alerts"),
                    PlanStep(description="Summarize alert status"),
                ]
            ),
        ],
        tool_responses=[_tool_call(), _tool_call()],
        responses=[AIMessage(content="Both planned steps are complete.")],
    )
    strategy = PlanAndExecuteStrategy(model, [_tool()], no_replanner=True)

    result = asyncio.run(strategy.run("Review firing alerts"))

    assert result.answer == "Both planned steps are complete."
    assert result.metrics.llm_calls == 4
    assert len(model.structured_inputs) == 1
    assert [event.type for event in result.trace] == [
        "plan",
        "action",
        "observation",
        "action",
        "observation",
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


def test_planner_receives_available_tool_catalog_and_guidance() -> None:
    model = PlanFakeModel(
        structured_responses=[
            Plan(
                steps=[
                    PlanStep(
                        description="List firing alerts to identify the checkout service."
                    )
                ]
            ),
            PlanReview(
                steps=[],
                answer="Please provide the incident severity.",
            ),
        ],
        tool_responses=[_tool_call()],
    )
    strategy = PlanAndExecuteStrategy(model, [_tool(), _incident_tool()])

    result = asyncio.run(
        strategy.run("Open an incident for checkout alerts that are firing")
    )

    planner_messages = model.structured_inputs[0]
    system_prompt = str(planner_messages[0].content)
    planner_context = str(planner_messages[1].content)
    assert "open_incident" in planner_context
    assert "existing service" in planner_context
    assert "required" in planner_context
    assert "severity" in planner_context
    assert "order='oldest'" in system_prompt
    assert "title" in planner_context
    assert "service" in planner_context
    assert "list_alerts" in planner_context
    assert "available tools" in system_prompt.lower()
    assert "never invent" in system_prompt.lower()
    assert "unsupported" in system_prompt.lower()
    assert result.answer == "Please provide the incident severity."
    assert [event.tool for event in result.trace if event.type == "action"] == [
        "list_alerts"
    ]


def test_planner_catalog_contains_only_tools_bound_to_the_strategy() -> None:
    model = PlanFakeModel(
        structured_responses=[Plan(steps=[], answer="No action is needed.")],
        tool_responses=[],
    )
    strategy = PlanAndExecuteStrategy(model, [_tool()])

    asyncio.run(strategy.run("What can you do?"))

    planner_context = str(model.structured_inputs[0][1].content)
    assert "list_alerts" in planner_context
    assert "open_incident" not in planner_context


def test_plan_and_execute_executes_open_incident_from_actionable_plan() -> None:
    model = PlanFakeModel(
        structured_responses=[
            Plan(steps=[PlanStep(description="Open an incident for checkout.")]),
            PlanReview(
                steps=[],
                answer="The checkout incident was created.",
            ),
        ],
        tool_responses=[_incident_tool_call()],
    )
    strategy = PlanAndExecuteStrategy(model, [_incident_tool()])

    result = asyncio.run(strategy.run("Open a severity 2 checkout incident"))

    assert result.answer == "The checkout incident was created."
    replanner_system_prompt = str(model.structured_inputs[1][0].content)
    replanner_context = str(model.structured_inputs[1][1].content)
    assert "available tools" in replanner_system_prompt.lower()
    assert "never invent" in replanner_system_prompt.lower()
    assert "available_tools" in replanner_context
    assert "open_incident" in replanner_context
    assert [event.type for event in result.trace] == [
        "plan",
        "action",
        "observation",
        "critique",
        "plan",
        "answer",
    ]
    action = next(event for event in result.trace if event.type == "action")
    observation = next(
        event for event in result.trace if event.type == "observation"
    )
    assert action.tool == "open_incident"
    assert observation.content == (
        "created incident: Checkout errors (checkout, 2)"
    )


def test_plan_and_execute_does_not_execute_unsupported_operation() -> None:
    model = PlanFakeModel(
        structured_responses=[
            Plan(steps=[], answer="There is no alert-closing tool available.")
        ],
        tool_responses=[],
    )
    strategy = PlanAndExecuteStrategy(model, [])

    result = asyncio.run(strategy.run("Close the firing alerts"))

    assert result.answer == "There is no alert-closing tool available."
    assert [event.type for event in result.trace] == ["plan", "answer"]
    assert result.trace[0].content == "[]"


def test_plan_and_execute_keeps_informational_requests_without_steps() -> None:
    model = PlanFakeModel(
        structured_responses=[
            Plan(steps=[], answer="I can answer this without operational tools.")
        ],
        tool_responses=[],
    )
    strategy = PlanAndExecuteStrategy(model, [_tool()])

    result = asyncio.run(strategy.run("What can you help me with?"))

    assert result.answer == "I can answer this without operational tools."
    assert [event.type for event in result.trace] == ["plan", "answer"]
    assert result.trace[0].content == "[]"


def test_plan_and_execute_wraps_invalid_planner_response() -> None:
    model = PlanFakeModel(
        structured_responses=[_validation_error()],
        tool_responses=[],
    )
    strategy = PlanAndExecuteStrategy(model, [_tool()])

    with pytest.raises(StructuredOutputError) as exc_info:
        asyncio.run(strategy.run("Check firing alerts"))

    assert str(exc_info.value) == (
        "The model returned an invalid structured response. Please retry or "
        "choose a model that supports structured outputs."
    )
    assert isinstance(exc_info.value.__cause__, ValidationError)
    assert "must not appear in the user message" not in str(exc_info.value)


def test_plan_and_execute_wraps_invalid_replanner_response() -> None:
    model = PlanFakeModel(
        structured_responses=[
            Plan(steps=[PlanStep(description="List firing alerts")]),
            _validation_error(),
        ],
        tool_responses=[_tool_call()],
    )
    strategy = PlanAndExecuteStrategy(model, [_tool()])

    with pytest.raises(StructuredOutputError) as exc_info:
        asyncio.run(strategy.run("Check firing alerts"))

    assert str(exc_info.value) == (
        "The model returned an invalid structured response. Please retry or "
        "choose a model that supports structured outputs."
    )
    assert isinstance(exc_info.value.__cause__, ValidationError)


def test_plan_and_execute_does_not_wrap_unrelated_structured_call_errors() -> None:
    model = PlanFakeModel(
        structured_responses=[RuntimeError("provider unavailable")],
        tool_responses=[],
    )
    strategy = PlanAndExecuteStrategy(model, [_tool()])

    with pytest.raises(RuntimeError, match="provider unavailable") as exc_info:
        asyncio.run(strategy.run("Check firing alerts"))

    assert not isinstance(exc_info.value, StructuredOutputError)
