import asyncio
from collections.abc import Sequence
from typing import Any
from uuid import uuid4

import pytest
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.runnables import RunnableConfig

from agents.base import ReasoningStrategy
from agents.errors import StructuredOutputError
from agents.reflection import CritiqueOutput, ReflectionStrategy
from agents.types import ExecutionMetrics, StrategyResult, TraceEvent


@pytest.fixture
def deterministic_clock(monkeypatch: pytest.MonkeyPatch) -> None:
    ticks = iter(float(tick) for tick in range(20))
    monkeypatch.setattr("agents.reflection.perf_counter", lambda: next(ticks))


class _SequenceStrategy(ReasoningStrategy):
    name = "sequence"

    def __init__(self, results: Sequence[StrategyResult]) -> None:
        self.results = list(results)
        self.inputs: list[str] = []

    async def run(self, input: str) -> StrategyResult:
        self.inputs.append(input)
        return self.results.pop(0)


class _SequenceEvaluator:
    def __init__(self, outputs: Sequence[CritiqueOutput | dict[str, object]]) -> None:
        self.outputs = list(outputs)
        self.prompts: list[str] = []

    async def ainvoke(
        self,
        input: str,
        config: RunnableConfig | None = None,
    ) -> CritiqueOutput | dict[str, object]:
        self.prompts.append(input)
        callbacks = config.get("callbacks") if config else None
        if isinstance(callbacks, list):
            for callback in callbacks:
                if isinstance(callback, BaseCallbackHandler):
                    callback.on_chat_model_start(
                        {},
                        [[]],
                        run_id=uuid4(),
                    )
        return self.outputs.pop(0)


def _result(answer: str, *, llm_calls: int, latency_ms: float) -> StrategyResult:
    return StrategyResult(
        answer=answer,
        trace=[
            TraceEvent(type="thought", content="internal reasoning"),
            TraceEvent(type="observation", content=f"observed for {answer}"),
            TraceEvent(type="answer", content=answer),
        ],
        metrics=ExecutionMetrics(
            llm_calls=llm_calls,
            latency_ms=latency_ms,
        ),
    )


def test_reflection_returns_first_approved_answer_without_retry(
    deterministic_clock: None,
) -> None:
    strategy = _SequenceStrategy(
        [_result("Healthy", llm_calls=2, latency_ms=12.0)]
    )
    evaluator = _SequenceEvaluator(
        [CritiqueOutput(approved=True, feedback="")]
    )

    result = asyncio.run(
        ReflectionStrategy(strategy, evaluator).run("Check status")
    )

    assert result.answer == "Healthy"
    assert strategy.inputs == ["Check status"]
    assert len(evaluator.prompts) == 1
    assert "Check status" in evaluator.prompts[0]
    assert "Healthy" in evaluator.prompts[0]
    assert "observed for Healthy" in evaluator.prompts[0]
    assert "internal reasoning" not in evaluator.prompts[0]
    assert [event.type for event in result.trace] == [
        "thought",
        "observation",
        "answer",
        "critique",
    ]
    assert result.trace[-1].content == "approved: True\nfeedback: "
    assert result.metrics.llm_calls == 3
    assert result.metrics.latency_ms == 1012.0


def test_reflection_retries_with_feedback_and_stops_when_approved(
    deterministic_clock: None,
) -> None:
    strategy = _SequenceStrategy(
        [
            _result("Incomplete", llm_calls=1, latency_ms=5.0),
            _result("Complete", llm_calls=2, latency_ms=7.0),
        ]
    )
    evaluator = _SequenceEvaluator(
        [
            CritiqueOutput(approved=False, feedback="Include the observed cause."),
            CritiqueOutput(approved=True, feedback=""),
        ]
    )

    result = asyncio.run(
        ReflectionStrategy(strategy, evaluator).run("Explain the incident")
    )

    assert result.answer == "Complete"
    assert strategy.inputs[0] == "Explain the incident"
    assert "Explain the incident" in strategy.inputs[1]
    assert "Include the observed cause." in strategy.inputs[1]
    assert len(evaluator.prompts) == 2
    assert [event.type for event in result.trace].count("critique") == 2
    assert [event.type for event in result.trace] == [
        "thought",
        "observation",
        "answer",
        "critique",
        "thought",
        "observation",
        "answer",
        "critique",
    ]
    assert result.metrics.llm_calls == 5
    assert result.metrics.latency_ms == 2012.0


def test_reflection_stops_after_default_maximum_and_returns_last_answer(
    deterministic_clock: None,
) -> None:
    strategy = _SequenceStrategy(
        [
            _result("Attempt 1", llm_calls=1, latency_ms=2.0),
            _result("Attempt 2", llm_calls=1, latency_ms=3.0),
            _result("Attempt 3", llm_calls=1, latency_ms=4.0),
        ]
    )
    evaluator = _SequenceEvaluator(
        [
            CritiqueOutput(approved=False, feedback="Revise 1"),
            CritiqueOutput(approved=False, feedback="Revise 2"),
            CritiqueOutput(approved=False, feedback="Revise 3"),
        ]
    )

    result = asyncio.run(
        ReflectionStrategy(strategy, evaluator).run("Investigate issue")
    )

    assert result.answer == "Attempt 3"
    assert len(strategy.inputs) == 3
    assert len(evaluator.prompts) == 3
    assert [event.type for event in result.trace].count("critique") == 3
    assert result.trace[-1].content == "approved: False\nfeedback: Revise 3"
    assert result.metrics.llm_calls == 6
    assert result.metrics.latency_ms == 3009.0


def test_reflection_respects_custom_limit_and_evaluates_with_zero_limit(
    deterministic_clock: None,
) -> None:
    strategy = _SequenceStrategy(
        [
            _result("First", llm_calls=1, latency_ms=2.0),
            _result("Second", llm_calls=1, latency_ms=3.0),
        ]
    )
    evaluator = _SequenceEvaluator(
        [
            CritiqueOutput(approved=False, feedback="One correction"),
            CritiqueOutput(approved=False, feedback="Limit reached"),
        ]
    )

    result = asyncio.run(
        ReflectionStrategy(
            strategy,
            evaluator,
            max_reflections=1,
        ).run("Check")
    )

    assert result.answer == "Second"
    assert len(strategy.inputs) == 2
    assert len(evaluator.prompts) == 2
    assert result.metrics.latency_ms == 2005.0

    zero_limit_strategy = _SequenceStrategy(
        [_result("Unchanged", llm_calls=1, latency_ms=1.0)]
    )
    zero_limit_evaluator = _SequenceEvaluator(
        [CritiqueOutput(approved=False, feedback="No retry allowed")]
    )
    zero_limit_result = asyncio.run(
        ReflectionStrategy(
            zero_limit_strategy,
            zero_limit_evaluator,
            max_reflections=0,
        ).run("Check")
    )

    assert zero_limit_result.answer == "Unchanged"
    assert len(zero_limit_strategy.inputs) == 1
    assert len(zero_limit_evaluator.prompts) == 1
    assert zero_limit_result.trace[-1].type == "critique"
    assert zero_limit_result.metrics.latency_ms == 1001.0


@pytest.mark.parametrize("max_reflections", [-1, 1.5, True])
def test_reflection_rejects_invalid_max_reflections(
    max_reflections: int,
) -> None:
    strategy = _SequenceStrategy([])
    evaluator = _SequenceEvaluator([])

    with pytest.raises(ValueError, match="max_reflections"):
        ReflectionStrategy(
            strategy,
            evaluator,
            max_reflections=max_reflections,
        )


def test_reflection_evaluates_answer_without_observations(
    deterministic_clock: None,
) -> None:
    strategy = _SequenceStrategy(
        [
            StrategyResult(
                answer="No trace evidence",
                trace=[],
                metrics=ExecutionMetrics(llm_calls=1, latency_ms=1.0),
            )
        ]
    )
    evaluator = _SequenceEvaluator(
        [CritiqueOutput(approved=True, feedback="")]
    )

    result = asyncio.run(
        ReflectionStrategy(strategy, evaluator).run("Answer the question")
    )

    assert "Observed facts:\n[]" in evaluator.prompts[0]
    assert result.answer == "No trace evidence"
    assert result.metrics.latency_ms == 1001.0


@pytest.mark.parametrize(
    "output",
    [
        {"approved": "indeterminate", "feedback": ""},
        {"approved": True, "feedback": "", "unexpected": True},
    ],
)
def test_reflection_rejects_invalid_critique_output(
    output: dict[str, object],
) -> None:
    strategy = _SequenceStrategy(
        [_result("Answer", llm_calls=1, latency_ms=1.0)]
    )
    evaluator = _SequenceEvaluator([output])

    with pytest.raises(StructuredOutputError):
        asyncio.run(ReflectionStrategy(strategy, evaluator).run("Check"))
