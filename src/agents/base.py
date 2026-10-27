from abc import ABC, abstractmethod

from agents.types import StrategyResult


class ReasoningStrategy(ABC):
    name: str

    @abstractmethod
    async def run(self, input: str) -> StrategyResult:
        raise NotImplementedError
