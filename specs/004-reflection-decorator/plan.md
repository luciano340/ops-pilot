# Implementation Plan: Reflection Decorator

**Branch**: `004-reflection-decorator` | **Date**: 2026-10-28 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/004-reflection-decorator/spec.md`

## Summary

Add an opt-in decorator that runs an existing reasoning strategy, evaluates each answer against the original request and that attempt's trace observations using the configured language model and a validated critique schema, and retries with the critique as context up to two corrections by default. Preserve all attempt traces, append one critique event per evaluation, and aggregate strategy and evaluator metrics. Expose both supported decorated strategies through the arena CLI while leaving existing strategy selections unchanged.

## Technical Context

**Language/Version**: Python 3.14

**Primary Dependencies**: LangChain, LangChain Core, LangChain OpenAI, LangGraph, Pydantic v2

**Storage**: None; reflection results are returned in the existing in-memory strategy result.

**Testing**: Pytest; deterministic unit tests with injected strategy/evaluator doubles and no external network calls.

**Target Platform**: Existing OpsPilot Python application and Django management CLI.

**Project Type**: Python application with reasoning library and command-line interface.

**Performance Goals**: Bound added model work by one evaluator call per attempt and no more than two correction attempts by default. Total latency is necessarily sequential and is reported as an aggregate.

**Constraints**: Keep the existing asynchronous `ReasoningStrategy.run(input: str) -> StrategyResult` contract; preserve the initial user request when adding feedback; do not make a correction after approval or after the configured limit; use the configured model and provider; do not add persistence or make network calls in unit tests.

**Scale/Scope**: One strategy invocation at a time per selected arena strategy; two existing base strategies; one initial answer plus a configurable number of corrections.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Layering and domain purity — PASS**: Reflection remains an agent strategy decorator beside the existing model-integrating strategies. No domain, persistence, or ORM behavior is introduced.
- **II. Validated boundaries and explicit contracts — PASS**: The arena continues to validate its input with Pydantic; critique output is a validated schema; the decorator preserves the existing strategy result contract.
- **III. Type safety and quality — PASS**: New interfaces will be typed, behavioral paths will have offline tests, and pytest plus strict mypy remain required.
- **IV. Async access and resource efficiency — PASS**: Strategy and evaluator calls are awaited; retries are sequential and bounded. No repository or database operations are added.
- **V. Security by default — PASS**: The evaluator uses the same configured model/provider as the wrapped strategy. No additional external service, persistence, credential handling, or operational tool execution is introduced.
- **Spec-first governance — PASS**: This design follows the approved feature specification; implementation remains for the subsequent task and implement phases.

No constitution violations or exceptions are required.

## Project Structure

### Documentation (this feature)

```text
specs/004-reflection-decorator/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── arena-cli.md
└── tasks.md
```

### Source Code (repository root)

```text
src/agents/
├── base.py
├── types.py
├── react.py
├── plan_and_execute.py
├── reflection.py                 # Decorator and critique schema
└── management/commands/arena.py  # Compose and expose reflected strategies

tests/agents/
├── test_reflection.py
└── test_arena_command.py
```

**Structure Decision**: Extend the existing single Python application. Place the decorator beside the reasoning strategies and update the existing arena command and command-input schema; put tests alongside the current agent tests. These paths reuse the established package and test layout.

## Design Decisions

- Construct the production evaluator from the same model instance already passed to the base strategy, using LangChain structured output with the Pydantic critique schema. Inject the evaluator runnable into the decorator so tests can return deterministic critiques without provider calls.
- Keep the wrapper's public `run(input: str)` signature unchanged. For corrections, append a clearly delimited previous-review feedback section to the original request passed to the base strategy; never replace the original request.
- Treat `max_reflections` as the maximum number of correction attempts after the initial answer. Evaluate the initial answer even when this value is zero.
- For each attempt, provide the original request, candidate answer, and only the trace events of type `observation` to the evaluator. Do not treat thoughts, actions, or prior critiques as evidence.
- Append the attempt trace, then the matching `critique` event, preserving chronological order across attempts. Return the final attempt's answer and all accumulated trace events.
- Sum strategy-reported metrics and evaluator model-call/elapsed-time metrics over all attempts. Use LangChain chat-model callbacks for model invocation counts, consistent with the existing ReAct strategy's approach.
- Give reflected strategy instances a distinct result name (`reflect:react` or `reflect:plan_and_execute`) so arena outputs remain unique and clearly identify the selected mode. Existing base strategy names remain unchanged.

## Complexity Tracking

No additional projects, persistence layers, or architectural exceptions are introduced.
