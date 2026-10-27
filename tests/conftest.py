from collections.abc import Callable, Sequence

import pytest
from langchain_core.language_models import BaseChatModel, LanguageModelInput
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage
from langchain_core.runnables import Runnable


class OfflineToolCallingModel(FakeMessagesListChatModel):
    def bind_tools(
        self,
        tools: Sequence[object],
        *,
        tool_choice: str | None = None,
        **kwargs: object,
    ) -> Runnable[LanguageModelInput, AIMessage]:
        return self


@pytest.fixture
def offline_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_MODEL", raising=False)


@pytest.fixture
def fake_tool_calling_model() -> Callable[[Sequence[AIMessage]], BaseChatModel]:
    def create_model(responses: Sequence[AIMessage]) -> BaseChatModel:
        return OfflineToolCallingModel(responses=list(responses))

    return create_model
