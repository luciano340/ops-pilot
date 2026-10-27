from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

TraceType = Literal["thought", "action", "observation", "plan", "critique", "answer"]


class TraceEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    type: TraceType
    content: str
    tool: str | None = None
    args: dict[str, object] | None = None

    @model_validator(mode="after")
    def validate_action_fields(self) -> "TraceEvent":
        if self.type == "action":
            if not self.tool or self.args is None:
                raise ValueError("Action events require a tool name and args")
        elif self.tool is not None or self.args is not None:
            raise ValueError("Only action events may contain tool and args")
        return self


class ExecutionMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    llm_calls: int = Field(ge=0)
    latency_ms: float = Field(ge=0)


class StrategyResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    answer: str
    trace: list[TraceEvent]
    metrics: ExecutionMetrics
