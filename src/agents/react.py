from collections.abc import Sequence
from time import perf_counter
from typing import Any

from langchain.agents import create_agent
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langchain_core.runnables import Runnable

from agents.base import ReasoningStrategy
from agents.types import ExecutionMetrics, StrategyResult, TraceEvent


class _CallCounter(BaseCallbackHandler):
    def __init__(self) -> None:
        self.calls = 0

    def on_chat_model_start(
        self,
        serialized: dict[str, Any],
        messages: list[list[BaseMessage]],
        **kwargs: Any,
    ) -> None:
        self.calls += 1


def _message_text(content: str | list[str | dict[str, Any]]) -> str:
    if isinstance(content, str):
        return content
    text_parts = [
        block["text"]
        for block in content
        if isinstance(block, dict) and isinstance(block.get("text"), str)
    ]
    return "\n".join(text_parts)


class ReactStrategy(ReasoningStrategy):
    name = "react"

    def __init__(
        self,
        model: Runnable[Any, Any],
        tools: Sequence[Any],
    ) -> None:
        self._model = model
        self._tools = list(tools)

    async def run(self, input: str) -> StrategyResult:
        if not input.strip():
            raise ValueError("Input must not be empty")

        agent = create_agent(
            model=self._model,
            tools=self._tools,
            system_prompt=(
                "You are an operations assistant. Use the available tools to "
                "verify operational facts before answering. Never claim an "
                "action succeeded unless the tool confirms it. Complete every "
                "requested operational action; when a request requires choosing "
                "the oldest alert, request list_alerts with order='oldest' and "
                "base the action on the first result's created_at and service."
            ),
        )
        counter = _CallCounter()
        started = perf_counter()
        result = await agent.ainvoke(
            {"messages": [{"role": "user", "content": input}]},
            config={"callbacks": [counter]},
        )
        elapsed_ms = (perf_counter() - started) * 1000
        messages = result["messages"]
        trace: list[TraceEvent] = []
        answer = ""

        for message in messages:
            if isinstance(message, AIMessage):
                for tool_call in message.tool_calls:
                    trace.append(
                        TraceEvent(
                            type="action",
                            content=f"Call {tool_call['name']}",
                            tool=tool_call["name"],
                            args=tool_call["args"],
                        )
                    )
                text = _message_text(message.content)
                if text and not message.tool_calls:
                    answer = text
                    trace.append(TraceEvent(type="answer", content=text))
            elif isinstance(message, ToolMessage):
                trace.append(
                    TraceEvent(
                        type="observation",
                        content=_message_text(message.content),
                    )
                )

        if not answer:
            raise RuntimeError("ReAct agent completed without a textual answer")

        return StrategyResult(
            answer=answer,
            trace=trace,
            metrics=ExecutionMetrics(
                llm_calls=counter.calls,
                latency_ms=elapsed_ms,
            ),
        )
