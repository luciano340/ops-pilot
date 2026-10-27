import pytest
from pydantic import ValidationError

from agents.types import ExecutionMetrics, StrategyResult, TraceEvent


def test_trace_event_accepts_known_type_and_action_arguments() -> None:
    event = TraceEvent(
        type="action",
        content="List active alerts",
        tool="list_alerts",
        args={"status": "firing"},
    )

    assert event.type == "action"
    assert event.tool == "list_alerts"
    assert event.args == {"status": "firing"}


@pytest.mark.parametrize(
    "payload",
    [
        {"type": "unknown", "content": "not allowed"},
        {"type": "action", "content": "missing tool", "args": {}},
        {"type": "action", "content": "missing args", "tool": "list_alerts"},
        {"type": "answer", "content": "unexpected tool", "tool": "list_alerts"},
    ],
)
def test_trace_event_rejects_invalid_shapes(payload: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        TraceEvent.model_validate(payload)


@pytest.mark.parametrize(
    ("llm_calls", "latency_ms"),
    [(-1, 0.0), (0, -0.1)],
)
def test_execution_metrics_reject_negative_values(
    llm_calls: int,
    latency_ms: float,
) -> None:
    with pytest.raises(ValidationError):
        ExecutionMetrics(llm_calls=llm_calls, latency_ms=latency_ms)


def test_strategy_result_contains_trace_and_metrics() -> None:
    result = StrategyResult(
        answer="There are no firing alerts.",
        trace=[TraceEvent(type="answer", content="There are no firing alerts.")],
        metrics=ExecutionMetrics(llm_calls=1, latency_ms=12.5),
    )

    assert result.answer == "There are no firing alerts."
    assert result.metrics.llm_calls == 1
