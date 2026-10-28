import json
from time import perf_counter
from typing import Any, Protocol

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import BaseMessage
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, ConfigDict, ValidationError

from agents.base import ReasoningStrategy
from agents.errors import StructuredOutputError
from agents.types import ExecutionMetrics, StrategyResult, TraceEvent


class CritiqueOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    approved: bool
    feedback: str


class CritiqueEvaluator(Protocol):
    async def ainvoke(
        self,
        input: str,
        config: RunnableConfig | None = None,
    ) -> Any: ...


class _CallCounter(BaseCallbackHandler):
    def __init__(self) -> None:
        self.calls = 0

    def on_chat_model_start(
        self,
        serialized: dict[str, Any],
        messages: list[list[BaseMessage]],
        **kwargs: Any,
    ) -> None:
        self.calls += 1


class ReflectionStrategy(ReasoningStrategy):
    name: str

    def __init__(
        self,
        strategy: ReasoningStrategy,
        evaluator: CritiqueEvaluator,
        *,
        max_reflections: int = 2,
    ) -> None:
        if type(max_reflections) is not int or max_reflections < 0:
            raise ValueError("max_reflections must be a non-negative integer")
        self._strategy = strategy
        self._evaluator = evaluator
        self._max_reflections = max_reflections
        self.name = f"reflect:{strategy.name}"

    async def run(self, input: str) -> StrategyResult:
        if not input.strip():
            raise ValueError("Input must not be empty")

        trace: list[TraceEvent] = []
        llm_calls = 0
        latency_ms = 0.0
        correction_count = 0
        feedback: str | None = None

        while True:
            strategy_input = input
            if feedback is not None:
                strategy_input = (
                    f"{input}\n\n"
                    "Reflection feedback to address in your next answer:\n"
                    f"{feedback}"
                )

            result = await self._strategy.run(strategy_input)
            trace.extend(result.trace)
            llm_calls += result.metrics.llm_calls
            latency_ms += result.metrics.latency_ms

            counter = _CallCounter()
            started = perf_counter()
            try:
                raw_critique = await self._evaluator.ainvoke(
                    self._build_prompt(input, result),
                    config={"callbacks": [counter]},
                )
                critique = CritiqueOutput.model_validate(raw_critique)
            except ValidationError as exc:
                raise StructuredOutputError() from exc
            latency_ms += (perf_counter() - started) * 1000
            llm_calls += counter.calls

            trace.append(
                TraceEvent(
                    type="critique",
                    content=(
                        f"approved: {critique.approved}\n"
                        f"feedback: {critique.feedback}"
                    ),
                )
            )

            if critique.approved or correction_count >= self._max_reflections:
                return StrategyResult(
                    answer=result.answer,
                    trace=trace,
                    metrics=ExecutionMetrics(
                        llm_calls=llm_calls,
                        latency_ms=latency_ms,
                    ),
                )

            correction_count += 1
            feedback = critique.feedback

    @staticmethod
    def _build_prompt(request: str, result: StrategyResult) -> str:
        observations = [
            event.content
            for event in result.trace
            if event.type == "observation"
        ]
        return (
            "Evaluate whether the candidate answer accurately addresses the "
            "request and is consistent with the observed facts. Treat only "
            "the listed observations as evidence. Approve only when both "
            "criteria are met. If not approved, give specific corrective "
            "feedback.\n\n"
            f"Request:\n{json.dumps(request, ensure_ascii=False)}\n\n"
            "Observed facts:\n"
            f"{json.dumps(observations, ensure_ascii=False)}\n\n"
            "Candidate answer:\n"
            f"{json.dumps(result.answer, ensure_ascii=False)}"
        )
