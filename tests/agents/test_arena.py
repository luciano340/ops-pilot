import asyncio

import pytest

from agents.base import ReasoningStrategy
from agents.types import ExecutionMetrics, StrategyResult, TraceEvent
from arena import run_strategies


class FakeStrategy(ReasoningStrategy):
    def __init__(self, name: str) -> None:
        self.name = name
        self.received: list[str] = []

    async def run(self, input: str) -> StrategyResult:
        self.received.append(input)
        return StrategyResult(
            answer=f"{self.name}: {input}",
            trace=[TraceEvent(type="answer", content=input)],
            metrics=ExecutionMetrics(llm_calls=1, latency_ms=1.0),
        )


def test_run_strategies_gives_each_the_same_input_and_keeps_order() -> None:
    first = FakeStrategy("first")
    second = FakeStrategy("second")

    results = asyncio.run(run_strategies("inspect alerts", [first, second]))

    assert list(results) == ["first", "second"]
    assert first.received == ["inspect alerts"]
    assert second.received == ["inspect alerts"]


@pytest.mark.parametrize(
    ("request_text", "strategies"),
    [
        (" ", [FakeStrategy("first")]),
        ("valid request", []),
        ("valid request", [FakeStrategy("same"), FakeStrategy("same")]),
    ],
)
def test_run_strategies_rejects_invalid_input_before_running(
    request_text: str,
    strategies: list[FakeStrategy],
) -> None:
    with pytest.raises(ValueError):
        asyncio.run(run_strategies(request_text, strategies))

    assert all(not strategy.received for strategy in strategies)
