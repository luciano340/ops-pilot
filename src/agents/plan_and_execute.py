import json
import operator
from collections.abc import Sequence
from time import perf_counter
from typing import Annotated, Any, Literal, TypedDict

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.runnables import Runnable
from langchain_core.tools import BaseTool
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from pydantic.v1 import BaseModel as PydanticV1BaseModel

from agents.base import ReasoningStrategy
from agents.errors import StructuredOutputError
from agents.types import ExecutionMetrics, StrategyResult, TraceEvent

MAX_ITERATIONS = 8


def _tool_args_schema(tool: BaseTool) -> dict[str, Any]:
    schema = tool.get_input_schema()
    if issubclass(schema, BaseModel):
        return schema.model_json_schema()
    if issubclass(schema, PydanticV1BaseModel):
        return schema.schema()
    raise TypeError(f"Unsupported argument schema for tool '{tool.name}'")


class PlanStep(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    description: str = Field(min_length=1)


class Plan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    steps: list[PlanStep]
    answer: str | None = None


class PlanReview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    steps: list[PlanStep]
    answer: str | None = None
    critique: str = ""


class PlanState(TypedDict):
    request: str
    steps: list[PlanStep]
    observations: list[str]
    trace: Annotated[list[TraceEvent], operator.add]
    iterations: int
    llm_calls: int
    max_iterations: int
    no_replanner: bool
    answer: str


class PlanAndExecuteStrategy(ReasoningStrategy):
    name = "plan_and_execute"

    def __init__(
        self,
        model: BaseChatModel,
        tools: Sequence[BaseTool],
        *,
        max_iterations: int = MAX_ITERATIONS,
        no_replanner: bool = False,
    ) -> None:
        if not 1 <= max_iterations <= MAX_ITERATIONS:
            raise ValueError(f"max_iterations must be between 1 and {MAX_ITERATIONS}")
        self._planner: Runnable[Any, Any] = model.with_structured_output(Plan)
        self._replanner: Runnable[Any, Any] = model.with_structured_output(PlanReview)
        self._finalizer = model
        self._executor: Runnable[Any, Any] = model.bind_tools(list(tools))
        self._tools = {tool.name: tool for tool in tools}
        self._tool_catalog = [
            {
                "name": tool.name,
                "description": tool.description,
                "args_schema": _tool_args_schema(tool),
            }
            for tool in tools
        ]
        self._max_iterations = max_iterations
        self._no_replanner = no_replanner

        builder = StateGraph(PlanState)
        builder.add_node("planner", self._plan)
        builder.add_node("executor", self._execute)
        builder.add_node("replanner", self._replan)
        builder.add_node("finalizer", self._finalize)
        builder.add_edge(START, "planner")
        builder.add_conditional_edges("planner", self._route_after_plan)
        builder.add_conditional_edges("executor", self._route_after_execute)
        builder.add_conditional_edges("replanner", self._route_after_replan)
        builder.add_edge("finalizer", END)
        self._graph = builder.compile()

    async def run(self, input: str) -> StrategyResult:
        if not input.strip():
            raise ValueError("Input must not be empty")

        started = perf_counter()
        state = await self._graph.ainvoke(
            {
                "request": input,
                "steps": [],
                "observations": [],
                "trace": [],
                "iterations": 0,
                "llm_calls": 0,
                "max_iterations": self._max_iterations,
                "no_replanner": self._no_replanner,
                "answer": "",
            }
        )
        answer = state["answer"].strip()
        if not answer:
            answer = "The plan ended without a final answer."
        trace = list(state["trace"])
        if not trace or trace[-1].type != "answer":
            trace.append(TraceEvent(type="answer", content=answer))

        return StrategyResult(
            answer=answer,
            trace=trace,
            metrics=ExecutionMetrics(
                llm_calls=state["llm_calls"],
                latency_ms=(perf_counter() - started) * 1000,
            ),
        )

    async def _plan(self, state: PlanState) -> dict[str, Any]:
        try:
            plan = await self._planner.ainvoke(
                [
                    SystemMessage(
                        content=(
                            "You are an operations planner. The available tools and "
                            "their argument schemas are provided in the request context. "
                            "When the user asks for an operation supported by an "
                            "available tool, create actionable steps for the executor; "
                            "when an operation depends on selected alert data, include "
                            "a read step followed by the requested write step. For the "
                            "oldest alert, call list_alerts with order='oldest' and "
                            "use the first result's created_at and service. "
                            "do not claim you lack access to an operation whose tool is "
                            "listed. Never invent required arguments or operational "
                            "facts. If required information is missing, use an available "
                            "read tool to find it when possible; otherwise return no "
                            "steps and ask the user a concise clarification question. "
                            "For operations with no available tool, explain that the "
                            "capability is unsupported and do not claim it was done. "
                            "For requests needing no action, return no steps and a "
                            "direct answer."
                        )
                    ),
                    HumanMessage(
                        content=json.dumps(
                            {
                                "request": state["request"],
                                "available_tools": self._tool_catalog,
                            },
                            ensure_ascii=False,
                        )
                    ),
                ]
            )
            validated = Plan.model_validate(plan)
        except ValidationError as exc:
            raise StructuredOutputError() from exc
        trace = [
            TraceEvent(
                type="plan",
                content=json.dumps(
                    [step.description for step in validated.steps],
                    ensure_ascii=False,
                ),
            )
        ]
        answer = validated.answer or ""
        if not validated.steps and not answer:
            answer = "No actions are required to complete the request."
        if not validated.steps:
            trace.append(TraceEvent(type="answer", content=answer))
        return {
            "steps": validated.steps,
            "trace": trace,
            "answer": answer,
            "llm_calls": state["llm_calls"] + 1,
        }

    async def _execute(self, state: PlanState) -> dict[str, Any]:
        step = state["steps"][0]
        message = await self._executor.ainvoke(
            [
                SystemMessage(
                    content=(
                        "Execute only the current plan step. Call at most one "
                        "operational tool. Do not execute later steps."
                    )
                ),
                HumanMessage(
                    content=json.dumps(
                        {
                            "request": state["request"],
                            "step": step.description,
                            "observations": state["observations"],
                        },
                        ensure_ascii=False,
                    )
                ),
            ]
        )
        if not isinstance(message, AIMessage):
            raise RuntimeError("Plan executor returned an invalid model response")
        if len(message.tool_calls) > 1:
            raise RuntimeError("Plan executor attempted more than one tool action")

        trace: list[TraceEvent] = []
        if message.tool_calls:
            call = message.tool_calls[0]
            tool = self._tools.get(call["name"])
            if tool is None:
                raise RuntimeError(f"Plan executor selected unknown tool '{call['name']}'")
            args = call["args"]
            trace.append(
                TraceEvent(
                    type="action",
                    content=f"Execute plan step: {step.description}",
                    tool=call["name"],
                    args=args,
                )
            )
            observation = await tool.ainvoke(args)
            observation_text = str(observation)
        else:
            observation_text = str(message.content).strip()
            if not observation_text:
                raise RuntimeError("Plan executor returned neither a tool call nor content")

        trace.append(TraceEvent(type="observation", content=observation_text))
        return {
            "steps": state["steps"][1:],
            "observations": state["observations"] + [observation_text],
            "trace": trace,
            "iterations": state["iterations"] + 1,
            "llm_calls": state["llm_calls"] + 1,
        }

    async def _replan(self, state: PlanState) -> dict[str, Any]:
        try:
            review = await self._replanner.ainvoke(
                [
                    SystemMessage(
                        content=(
                            "Review execution observations using the available tools "
                            "and their argument schemas in the request context. Return "
                            "only the remaining actionable steps and a final answer "
                            "when complete. Never invent required arguments or claim "
                            "an action succeeded without a confirming observation. If "
                            "required information is missing and cannot be found with "
                            "an available read tool, ask the user a concise clarification "
                            "question. Explain unsupported operations without claiming "
                            "they were done."
                        )
                    ),
                    HumanMessage(
                        content=json.dumps(
                            {
                                "request": state["request"],
                                "remaining_steps": [
                                    step.description for step in state["steps"]
                                ],
                                "observations": state["observations"],
                                "available_tools": self._tool_catalog,
                            },
                            ensure_ascii=False,
                        )
                    ),
                ]
            )
            validated = PlanReview.model_validate(review)
        except ValidationError as exc:
            raise StructuredOutputError() from exc
        steps = validated.steps
        answer = validated.answer or ""
        trace = [
            TraceEvent(
                type="critique",
                content=validated.critique
                or "Reviewed the remaining plan after the latest observation.",
            ),
            TraceEvent(
                type="plan",
                content=json.dumps(
                    [step.description for step in steps],
                    ensure_ascii=False,
                ),
            ),
        ]
        if not steps:
            if not answer:
                answer = "All planned steps are complete."
            trace.append(TraceEvent(type="answer", content=answer))
        elif state["iterations"] >= state["max_iterations"]:
            remaining = "; ".join(step.description for step in steps)
            answer = (
                f"Stopped at the iteration limit "
                f"({state['max_iterations']}). Remaining steps: {remaining}"
            )
            trace.append(TraceEvent(type="critique", content=answer))
            trace.append(TraceEvent(type="answer", content=answer))
        return {
            "steps": steps,
            "trace": trace,
            "answer": answer,
            "llm_calls": state["llm_calls"] + 1,
        }

    async def _finalize(self, state: PlanState) -> dict[str, Any]:
        message = await self._finalizer.ainvoke(
            [
                SystemMessage(
                    content=(
                        "Answer the original request using the execution observations. "
                        "Do not claim an action succeeded unless an observation confirms "
                        "it. If planned steps remain unexecuted, state that clearly."
                    )
                ),
                HumanMessage(
                    content=json.dumps(
                        {
                            "request": state["request"],
                            "observations": state["observations"],
                            "unexecuted_steps": [
                                step.description for step in state["steps"]
                            ],
                        },
                        ensure_ascii=False,
                    )
                ),
            ]
        )
        if not isinstance(message, AIMessage):
            raise RuntimeError("Plan finalizer returned an invalid model response")
        answer = str(message.content).strip()
        if not answer:
            raise RuntimeError("Plan finalizer returned an empty answer")
        return {
            "answer": answer,
            "trace": [TraceEvent(type="answer", content=answer)],
            "llm_calls": state["llm_calls"] + 1,
        }

    @staticmethod
    def _route_after_plan(state: PlanState) -> Literal["executor", "__end__"]:
        return "executor" if state["steps"] else "__end__"

    @staticmethod
    def _route_after_execute(
        state: PlanState,
    ) -> Literal["executor", "replanner", "finalizer"]:
        if not state["no_replanner"]:
            return "replanner"
        if state["steps"] and state["iterations"] < state["max_iterations"]:
            return "executor"
        return "finalizer"

    @staticmethod
    def _route_after_replan(state: PlanState) -> Literal["executor", "__end__"]:
        if not state["steps"] or state["iterations"] >= state["max_iterations"]:
            return "__end__"
        return "executor"
