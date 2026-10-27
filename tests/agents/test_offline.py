from collections.abc import Callable, Sequence

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage

import pytest

from agents.factory import ModelConfigurationError, create_model


def test_model_factory_requires_external_credentials_without_network(
    offline_environment: None,
) -> None:
    with pytest.raises(ModelConfigurationError, match="OPENROUTER_API_KEY"):
        create_model()


def test_fake_model_runs_without_network(
    fake_tool_calling_model: Callable[[Sequence[AIMessage]], BaseChatModel],
) -> None:
    model = fake_tool_calling_model([AIMessage(content="offline response")])

    response = model.invoke("offline request")

    assert response.content == "offline response"
