from agents.types import ExecutionMetrics, StrategyResult, TraceEvent
from arena import format_results


def test_format_results_includes_ordered_trace_actions_and_metrics() -> None:
    result = StrategyResult(
        answer="Incident opened.",
        trace=[
            TraceEvent(type="plan", content="Open an incident."),
            TraceEvent(
                type="action",
                content="Open incident",
                tool="open_incident",
                args={"title": "Elevated errors", "service": "checkout", "severity": "high"},
            ),
            TraceEvent(type="observation", content="Incident 123 created."),
            TraceEvent(type="answer", content="Incident opened."),
        ],
        metrics=ExecutionMetrics(llm_calls=2, latency_ms=18.0),
    )

    formatted = format_results({"plan_and_execute": result})

    assert formatted.index("plan") < formatted.index("action")
    assert formatted.index("action") < formatted.index("observation")
    assert formatted.index("observation") < formatted.index("answer")
    assert "open_incident" in formatted
    assert '"service": "checkout"' in formatted
    assert "llm_calls: 2" in formatted
    assert "latency_ms: 18.0" in formatted
