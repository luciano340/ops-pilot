import os

from langchain_openai import ChatOpenAI
from pydantic import SecretStr


class ModelConfigurationError(ValueError):
    pass


def create_model(*, temperature: float = 0.0) -> ChatOpenAI:
    api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    model = os.environ.get("OPENROUTER_MODEL", "").strip()
    if not api_key:
        raise ModelConfigurationError("OPENROUTER_API_KEY is required")
    if not model:
        raise ModelConfigurationError("OPENROUTER_MODEL is required")
    return ChatOpenAI(
        model=model,
        api_key=SecretStr(api_key),
        base_url="https://openrouter.ai/api/v1",
        temperature=temperature,
    )
