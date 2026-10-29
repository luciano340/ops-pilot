import asyncio
from collections.abc import Callable, Mapping

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.tools import BaseTool

from agents.base import ReasoningStrategy
from agents.chat_errors import StrategyTimeoutError, UnknownStrategyError
from agents.chat_schemas import ChatRequest
from agents.factory import create_model
from agents.reflection import CritiqueEvaluator, CritiqueOutput, ReflectionStrategy
from agents.registry import StrategyBuilder, get_strategy_registry
from agents.tools import get_agent_tools
from agents.types import StrategyResult


class ChatService:
    def __init__(
        self,
        *,
        registry: Mapping[str, StrategyBuilder] | None = None,
        model_factory: Callable[[], BaseChatModel] | None = None,
        tools_factory: Callable[[], list[BaseTool]] | None = None,
        evaluator_factory: (
            Callable[[BaseChatModel], CritiqueEvaluator] | None
        ) = None,
        timeout_seconds: float = 180.0,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be greater than zero")

        self._registry = (
            registry if registry is not None else get_strategy_registry()
        )
        self._model_factory = (
            model_factory if model_factory is not None else create_model
        )
        self._tools_factory = (
            tools_factory if tools_factory is not None else get_agent_tools
        )
        self._evaluator_factory = evaluator_factory
        self._timeout_seconds = timeout_seconds

    async def execute(self, request: ChatRequest) -> StrategyResult:
        try:
            builder = self._registry[request.strategy]
        except KeyError as exc:
            raise UnknownStrategyError(request.strategy) from exc

        model = self._model_factory()
        strategy: ReasoningStrategy = builder(model, self._tools_factory())
        if request.reflect:
            evaluator = (
                self._evaluator_factory(model)
                if self._evaluator_factory is not None
                else model.with_structured_output(CritiqueOutput)
            )
            strategy = ReflectionStrategy(strategy, evaluator)

        deadline = asyncio.timeout(self._timeout_seconds)
        try:
            async with deadline:
                return await strategy.run(request.message)
        except TimeoutError as exc:
            if not deadline.expired():
                raise
            raise StrategyTimeoutError(
                "The strategy execution exceeded the time limit."
            ) from exc


def get_chat_service() -> ChatService:
    return ChatService()
