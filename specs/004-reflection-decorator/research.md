# Research: Reflection Decorator

**Date**: 2026-10-28

## Structured critique evaluation

- **Decision**: Build the evaluator from the shared configured chat model with LangChain structured output and a Pydantic `CritiqueOutput`; await its asynchronous invocation and inject the evaluator runnable into the decorator for tests.
- **Rationale**: LangChain documents Pydantic schemas as validated structured-output results and asynchronous model invocations. Reusing the shared model preserves the configured provider and model without a second configuration path. An injected runnable lets tests supply known critique results without credentials or network access.
- **Alternatives considered**: Parse free-form model text into JSON manually; use an additional model configuration; exercise the real provider from tests. These alternatives add parsing and configuration failure modes or break deterministic/offline test requirements.
- **Sources**: [LangChain structured output](https://docs.langchain.com/oss/python/langchain/structured-output); [LangChain ChatOpenAI integration](https://docs.langchain.com/oss/python/integrations/chat/openai); [LangChain unit testing](https://docs.langchain.com/oss/python/langchain/test/unit-testing).

## Model-call accounting

- **Decision**: Use chat-model callback events for evaluator model-call counts and measure evaluator elapsed time around its awaited invocation; add those metrics to each base attempt's metrics.
- **Rationale**: LangChain's chat model start callback observes actual model runs, including multiple calls made within a runnable, and is the existing ReAct strategy's counting approach. Runnable invocation configuration carries callbacks. This keeps reported totals tied to model runs rather than only strategy/evaluator wrapper calls.
- **Alternatives considered**: Count every evaluator runnable invocation as exactly one model call. This can undercount if the runnable executes multiple model calls or retries.
- **Sources**: [BaseCallbackHandler `on_chat_model_start`](https://reference.langchain.com/python/langchain-core/callbacks/base/BaseCallbackHandler/on_chat_model_start); [LangChain model invocation and callbacks](https://docs.langchain.com/oss/python/langchain/models).

## Pydantic critique schema

- **Decision**: Define a Pydantic v2 model with explicit `approved: bool` and `feedback: str` fields and forbid unexpected fields, following the agent package's existing schema conventions.
- **Rationale**: Pydantic validates typed values at runtime and supports model-level configuration such as `extra="forbid"`. Validation errors must remain failures and must not silently become approvals.
- **Alternatives considered**: Accept an unvalidated dictionary or parse strings manually. Both weaken the structured contract and can turn malformed evaluator output into ambiguous behavior.
- **Sources**: [Pydantic model configuration](https://docs.pydantic.dev/latest/concepts/config/); [Pydantic schema validation](https://docs.pydantic.dev/latest/why/).

## Retry and feedback behavior

- **Decision**: Preserve the original request and append the latest critique feedback as a distinct correction instruction for each subsequent strategy run. Count corrections separately from the initial attempt and evaluate the initial answer even when the correction limit is zero.
- **Rationale**: This honors the existing single-string strategy interface, keeps the request available to the strategy on every iteration, and makes the configured maximum unambiguous and bounded.
- **Alternatives considered**: Change the strategy protocol to accept separate feedback/context parameters or pass only feedback on retries. Changing the protocol expands the feature surface and risks breaking existing implementations; omitting the request loses essential context.

## Trace composition and evaluator evidence

- **Decision**: Evaluate only trace events marked as observations, include the original request and current answer, and append one critique trace event immediately after each attempt's trace.
- **Rationale**: The specification requires evaluation against observations, while event filtering avoids presenting internal thoughts or attempted actions as confirmed facts. Interleaving each critique after its attempt preserves chronological explainability.
- **Alternatives considered**: Pass the full trace; append all critiques after all attempts; discard intermediate attempt traces. These options either expose irrelevant reasoning as evidence or weaken execution traceability.

## Arena selection

- **Decision**: Extend the existing validated strategy-name choices with the two explicit selectors `reflect:react` and `reflect:plan_and_execute`; give wrappers matching distinct output names.
- **Rationale**: The names are specified by the feature request and allow the result map and formatted arena output to distinguish a decorated strategy from its undecorated base.
- **Alternatives considered**: Change existing selectors to implicitly reflect or use a separate reflection flag. Implicit behavior breaks existing expectations; a separate flag is outside the requested composed `--strategies` syntax.
