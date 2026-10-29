from collections.abc import Callable, Sequence

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.tools import BaseTool

from agents.base import ReasoningStrategy
from agents.plan_and_execute import PlanAndExecuteStrategy
from agents.react import ReactStrategy

StrategyBuilder = Callable[
    [BaseChatModel, Sequence[BaseTool]],
    ReasoningStrategy,
]


def _build_react(
    model: BaseChatModel,
    tools: Sequence[BaseTool],
) -> ReasoningStrategy:
    return ReactStrategy(model, tools)


def _build_plan_and_execute(
    model: BaseChatModel,
    tools: Sequence[BaseTool],
) -> ReasoningStrategy:
    return PlanAndExecuteStrategy(model, tools)


def get_strategy_registry() -> dict[str, StrategyBuilder]:
    return {
        "react": _build_react,
        "plan_and_execute": _build_plan_and_execute,
    }
