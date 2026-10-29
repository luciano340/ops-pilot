import asyncio
import json
from collections.abc import Callable, Sequence
from typing import Any, cast

import pytest
from django.http import HttpResponse
from django.test import AsyncClient
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool

from agents.base import ReasoningStrategy
from agents.chat_schemas import ChatRequest
from agents.chat_service import ChatService
from agents.reflection import CritiqueEvaluator, CritiqueOutput
from agents.types import ExecutionMetrics, StrategyResult, TraceEvent


class _FakeChatService:
    def __init__(self) -> None:
        self.requests: list[ChatRequest] = []

    async def execute(self, request: ChatRequest) -> StrategyResult:
        self.requests.append(request)
        return StrategyResult(
            answer=f"Handled by {request.strategy}",
            trace=[
                TraceEvent(
                    type="action",
                    content="Call list_alerts",
                    tool="list_alerts",
                    args={"status": "firing"},
                ),
                TraceEvent(type="answer", content=f"Handled by {request.strategy}"),
            ],
            metrics=ExecutionMetrics(llm_calls=2, latency_ms=12.5),
        )


class _SequenceStrategy(ReasoningStrategy):
    name = "react"

    def __init__(self) -> None:
        self.inputs: list[str] = []

    async def run(self, input: str) -> StrategyResult:
        self.inputs.append(input)
        return StrategyResult(
            answer="Operational answer",
            trace=[TraceEvent(type="answer", content="Operational answer")],
            metrics=ExecutionMetrics(llm_calls=1, latency_ms=4.0),
        )


class _ApprovedEvaluator:
    def __init__(self) -> None:
        self.calls = 0

    async def ainvoke(
        self,
        input: str,
        config: RunnableConfig | None = None,
    ) -> CritiqueOutput:
        self.calls += 1
        return CritiqueOutput(approved=True, feedback="")


class _SlowOrFailingStrategy(ReasoningStrategy):
    name = "react"

    def __init__(
        self,
        *,
        delay: float = 0.0,
        error: Exception | None = None,
    ) -> None:
        self.delay = delay
        self.error = error

    async def run(self, input: str) -> StrategyResult:
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.error is not None:
            raise self.error
        return StrategyResult(
            answer="Done",
            trace=[TraceEvent(type="answer", content="Done")],
            metrics=ExecutionMetrics(llm_calls=1, latency_ms=1.0),
        )


def _post(client: AsyncClient, body: object) -> HttpResponse:
    return cast(
        HttpResponse,
        asyncio.run(
            client.post(
                "/chat",
                data=json.dumps(body),
                content_type="application/json",
            )
        ),
    )


def _post_raw(client: AsyncClient, body: str) -> HttpResponse:
    return cast(
        HttpResponse,
        asyncio.run(
            client.post(
                "/chat",
                data=body,
                content_type="application/json",
            )
        ),
    )


def _response_json(response: HttpResponse) -> Any:
    return json.loads(response.content)


def _service_for(
    strategy: ReasoningStrategy,
    model: BaseChatModel,
    *,
    timeout_seconds: float = 180.0,
) -> ChatService:
    def build_strategy(
        _model: BaseChatModel,
        _tools: Sequence[BaseTool],
    ) -> ReasoningStrategy:
        return strategy

    return ChatService(
        registry={"react": build_strategy},
        model_factory=lambda: model,
        tools_factory=lambda: [],
        timeout_seconds=timeout_seconds,
    )


@pytest.mark.django_db
def test_chat_endpoint_uses_default_strategy_and_serializes_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from agents import views

    service = _FakeChatService()
    monkeypatch.setattr(views, "get_chat_service", lambda: service)

    response = _post(AsyncClient(), {"message": "List firing alerts"})

    assert response.status_code == 200
    assert _response_json(response) == {
        "answer": "Handled by react",
        "trace": [
            {
                "type": "action",
                "content": "Call list_alerts",
                "tool": "list_alerts",
                "args": {"status": "firing"},
            },
            {"type": "answer", "content": "Handled by react"},
        ],
        "metrics": {"llm_calls": 2, "latency_ms": 12.5},
    }
    assert len(service.requests) == 1
    assert service.requests[0].strategy == "react"
    assert service.requests[0].reflect is False


@pytest.mark.django_db
def test_chat_endpoint_accepts_explicit_strategy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from agents import views

    service = _FakeChatService()
    monkeypatch.setattr(views, "get_chat_service", lambda: service)

    response = _post(
        AsyncClient(),
        {"message": "Summarize incidents", "strategy": "plan_and_execute"},
    )

    assert response.status_code == 200
    assert _response_json(response)["answer"] == "Handled by plan_and_execute"
    assert service.requests[0].strategy == "plan_and_execute"


@pytest.mark.django_db
def test_chat_endpoint_rejects_non_post_methods_without_execution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from agents import views

    service = _FakeChatService()
    monkeypatch.setattr(views, "get_chat_service", lambda: service)

    response = asyncio.run(AsyncClient().get("/chat"))

    assert response.status_code == 405
    assert response.headers["Allow"] == "POST"
    assert service.requests == []


@pytest.mark.django_db
def test_chat_endpoint_applies_reflection_only_when_requested(
    monkeypatch: pytest.MonkeyPatch,
    fake_tool_calling_model: Callable[[Sequence[AIMessage]], BaseChatModel],
) -> None:
    from agents import views

    strategy = _SequenceStrategy()
    evaluator = _ApprovedEvaluator()

    def build_strategy(
        model: BaseChatModel,
        tools: Sequence[BaseTool],
    ) -> ReasoningStrategy:
        return strategy

    model = fake_tool_calling_model([AIMessage(content="not used")])
    service = ChatService(
        registry={"react": build_strategy},
        model_factory=lambda: model,
        tools_factory=lambda: [],
        evaluator_factory=lambda _model: evaluator,
    )
    monkeypatch.setattr(views, "get_chat_service", lambda: service)
    client = AsyncClient()

    without_reflection = _post(client, {"message": "Check status"})
    with_reflection = _post(
        client,
        {"message": "Check status", "reflect": True},
    )

    assert without_reflection.status_code == 200
    assert [
        event["type"] for event in _response_json(without_reflection)["trace"]
    ] == [
        "answer"
    ]
    assert with_reflection.status_code == 200
    assert [event["type"] for event in _response_json(with_reflection)["trace"]] == [
        "answer",
        "critique",
    ]
    assert set(_response_json(with_reflection)) == {"answer", "trace", "metrics"}
    assert evaluator.calls == 1
    assert strategy.inputs == ["Check status", "Check status"]


@pytest.mark.parametrize(
    "body",
    [
        "{not-json",
        "[]",
        "{}",
        '{"message":"   "}',
        '{"message":"check","reflect":"true"}',
        '{"message":"check","private":"sentinel-value"}',
    ],
)
@pytest.mark.django_db
def test_chat_endpoint_returns_safe_validation_issues_without_execution(
    body: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from agents import views

    service = _FakeChatService()
    monkeypatch.setattr(views, "get_chat_service", lambda: service)

    response = _post_raw(AsyncClient(), body)

    assert response.status_code == 400
    issues = _response_json(response)["issues"]
    assert issues
    assert all(set(issue) == {"loc", "code", "message"} for issue in issues)
    assert "sentinel-value" not in response.content.decode()
    assert service.requests == []


@pytest.mark.django_db
def test_chat_endpoint_returns_unknown_strategy_before_model_creation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from agents import views

    def unexpected_model_factory() -> BaseChatModel:
        raise AssertionError("Model factory must not run for unknown strategy")

    service = ChatService(
        registry={},
        model_factory=unexpected_model_factory,
        tools_factory=lambda: [],
    )
    monkeypatch.setattr(views, "get_chat_service", lambda: service)

    response = _post(
        AsyncClient(),
        {"message": "Check status", "strategy": "missing"},
    )

    assert response.status_code == 422
    assert _response_json(response)["error"]["code"] == "unknown_strategy"


@pytest.mark.django_db
def test_chat_endpoint_returns_timeout_and_generic_operational_error(
    monkeypatch: pytest.MonkeyPatch,
    fake_tool_calling_model: Callable[[Sequence[AIMessage]], BaseChatModel],
) -> None:
    from agents import views

    model = fake_tool_calling_model([AIMessage(content="not used")])
    timeout_service = _service_for(
        _SlowOrFailingStrategy(delay=0.1),
        model,
        timeout_seconds=0.001,
    )
    monkeypatch.setattr(
        views,
        "get_chat_service",
        lambda: timeout_service,
    )

    timeout_response = _post(AsyncClient(), {"message": "Wait"})

    assert timeout_response.status_code == 504
    assert _response_json(timeout_response)["error"]["code"] == "strategy_timeout"

    failing_service = _service_for(
        _SlowOrFailingStrategy(
            error=RuntimeError("private provider details"),
        ),
        model,
    )
    monkeypatch.setattr(
        views,
        "get_chat_service",
        lambda: failing_service,
    )

    failure_response = _post(AsyncClient(), {"message": "Fail"})

    assert failure_response.status_code == 500
    assert _response_json(failure_response)["error"]["code"] == "internal_error"
    assert "private provider details" not in failure_response.content.decode()


@pytest.mark.django_db
def test_chat_endpoint_processes_an_independent_request_while_one_waits(
    monkeypatch: pytest.MonkeyPatch,
    fake_tool_calling_model: Callable[[Sequence[AIMessage]], BaseChatModel],
) -> None:
    from agents import views

    async def exercise_requests() -> None:
        model = fake_tool_calling_model([AIMessage(content="not used")])
        started = asyncio.Event()
        release_slow = asyncio.Event()

        class _ConcurrentStrategy(ReasoningStrategy):
            name = "react"

            async def run(self, input: str) -> StrategyResult:
                if input == "slow":
                    started.set()
                    await release_slow.wait()
                elif input == "fast":
                    release_slow.set()
                return StrategyResult(
                    answer=input,
                    trace=[TraceEvent(type="answer", content=input)],
                    metrics=ExecutionMetrics(llm_calls=1, latency_ms=1.0),
                )

        service = _service_for(_ConcurrentStrategy(), model)
        monkeypatch.setattr(views, "get_chat_service", lambda: service)
        client = AsyncClient()
        slow_request = asyncio.create_task(
            client.post(
                "/chat",
                data=json.dumps({"message": "slow"}),
                content_type="application/json",
            )
        )
        await started.wait()
        fast_response = await client.post(
            "/chat",
            data=json.dumps({"message": "fast"}),
            content_type="application/json",
        )
        assert fast_response.status_code == 200
        assert _response_json(cast(HttpResponse, fast_response))["answer"] == "fast"
        assert not slow_request.done()
        release_slow.set()
        slow_response = await slow_request
        assert slow_response.status_code == 200
        assert _response_json(cast(HttpResponse, slow_response))["answer"] == "slow"

    asyncio.run(exercise_requests())
