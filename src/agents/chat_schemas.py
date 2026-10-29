from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        strict=True,
        str_strip_whitespace=True,
    )

    message: str = Field(min_length=1)
    strategy: str = Field(default="react", min_length=1)
    reflect: bool = False
