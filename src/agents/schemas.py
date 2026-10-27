from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ArenaCommandInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    request: str = Field(min_length=1)
    strategies: list[Literal["react", "plan_and_execute"]] = Field(min_length=1)
    max_iterations: int = Field(default=8, ge=1, le=8)

    @field_validator("strategies")
    @classmethod
    def validate_unique_strategies(
        cls,
        strategies: list[Literal["react", "plan_and_execute"]],
    ) -> list[Literal["react", "plan_and_execute"]]:
        if len(strategies) != len(set(strategies)):
            raise ValueError("Strategies must not contain duplicates")
        return strategies
