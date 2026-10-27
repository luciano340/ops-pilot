import json
from collections.abc import Sequence

from agents.base import ReasoningStrategy
from agents.types import StrategyResult


async def run_strategies(
    input: str,
    strategies: Sequence[ReasoningStrategy],
) -> dict[str, StrategyResult]:
    if not input.strip():
        raise ValueError("Request must not be empty")
    if not strategies:
        raise ValueError("At least one strategy must be selected")

    names = [strategy.name for strategy in strategies]
    if any(not name.strip() for name in names):
        raise ValueError("Strategy names must not be empty")
    if len(names) != len(set(names)):
        raise ValueError("Strategy names must be unique")

    results: dict[str, StrategyResult] = {}
    for strategy in strategies:
        results[strategy.name] = await strategy.run(input)
    return results


def format_results(results: dict[str, StrategyResult]) -> str:
    if not results:
        raise ValueError("At least one strategy result is required")

    sections: list[str] = []
    for name, result in results.items():
        lines = [f"=== {name} ===", "Answer:", result.answer, "Trace:"]
        for index, event in enumerate(result.trace, start=1):
            event_text = f"{index}. [{event.type}] {event.content}"
            if event.type == "action":
                args = json.dumps(event.args, ensure_ascii=False, sort_keys=True)
                event_text += f" tool={event.tool} args={args}"
            lines.append(event_text)
        lines.extend(
            [
                f"llm_calls: {result.metrics.llm_calls}",
                f"latency_ms: {result.metrics.latency_ms}",
            ]
        )
        sections.append("\n".join(lines))
    return "\n\n".join(sections)
