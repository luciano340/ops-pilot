# Implementation Plan: Benchmark de Desempenho

**Branch**: `005-benchmark-performance` | **Date**: 2026-10-28 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/005-benchmark-performance/spec.md`

## Summary

Add a Django management command that runs the selected scenario/strategy matrix sequentially. For each pair, it runs the existing seed, captures a non-destructive baseline, runs the configured strategy, validates both response text and persisted state deltas, and reports pass/fail plus model-call and latency metrics. Add explicit alert severity across the model, migration, seed, DTO/schema/store/tool read path. Add an optional Plan-and-Execute path that executes the initial plan without replanning and uses exactly one final model call to synthesize the response.

## Technical Context

**Language/Version**: Python 3.14

**Primary Dependencies**: Django 6.1, Pydantic v2, LangChain, LangChain Core, LangChain OpenAI, LangGraph, pytest and pytest-django.

**Storage**: Existing configured SQLite database for development and PostgreSQL for Compose; one schema migration adds alert severity. The benchmark stores no additional results or snapshots persistently.

**Testing**: Pytest with Django's isolated test database, `call_command` for management commands, controlled/fake chat models for strategy behavior, and strict `mypy .`.

**Target Platform**: Existing OpsPilot Python application and Django management CLI.

**Project Type**: Python application with Django management commands, async agent strategies, and ORM-backed operations.

**Performance Goals**: Produce a result for each selected scenario-strategy pair; report the strategy's model-call count and elapsed latency while excluding seed and ORM snapshot time. `--no-replanner` must not invoke replanning and must make one final language-model call after initial-plan execution to produce the answer.

**Constraints**: Seed before each pair, then capture baseline; never delete existing incidents or other operational data. Keep ORM snapshots and seed in synchronous command context and run async strategies via the existing event-loop boundary. All result metrics include model invocations from planning, tools/executor, replanning where enabled, and finalization where used. No network calls are made in unit tests.

**Scale/Scope**: Three fixed scenarios (`c1`, `c2`, `c3`), two fixed strategies (`react`, `plan_and_execute`), up to six sequential combinations per default run. No repeated statistical sampling or result persistence in v1.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Layering and domain purity — PASS**: Alert severity flows through existing Model → Store → Service/DTO → agent-tool boundaries. The benchmark is a CLI orchestration/validation concern and does not move I/O into the domain.
- **II. Validated boundaries and explicit contracts — PASS**: CLI selectors are validated before DB/model work; alert severity is constrained to named values; existing tool schemas remain the input boundary.
- **III. Type safety and quality — PASS**: New command, scenario validators, migration-adjacent code, and tests will be typed and verified by pytest and strict mypy.
- **IV. Async access and resource efficiency — PASS**: The synchronous management command performs seed and ORM snapshots outside async strategy execution. Existing async operations remain awaited; no sync ORM access is introduced inside async code.
- **V. Security by default — PASS**: The benchmark never clears or resets operational tables. It captures state and compares effects using identifiers and relevant pre-run fields. Model credentials continue to come from existing configuration.
- **Spec-first governance — PASS**: This design follows the approved specification. Implementation is deferred to `/speckit-implement`.

No constitution violations or exceptions are required.

## Project Structure

### Documentation (this feature)

```text
specs/005-benchmark-performance/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── bench-cli.md
└── tasks.md
```

### Source Code (repository root)

```text
src/operations/
├── models.py
├── schemas.py
├── domain.py
├── services.py
├── store.py
├── migrations/
│   └── 0002_alert_severity.py
└── management/commands/
    └── seed_db.py

src/agents/
├── tools.py
└── plan_and_execute.py

src/
├── bench.py
└── agents/management/commands/
    └── bench.py

tests/
├── operations/
│   ├── test_seed_db.py
│   ├── test_services.py
│   └── test_store.py
└── agents/
    ├── test_plan_and_execute.py
    └── test_bench_command.py
```

**Structure Decision**: Keep the Django management command at `src/agents/management/commands/bench.py`, matching the existing arena command and making it discoverable as `python manage.py bench`. Keep scenario data, snapshots, deterministic answer checks, and result formatting as typed pure helpers in `src/bench.py`. Extend the existing operations alert read path and seed, add one migration, and update Plan-and-Execute graph routing for the selected no-replanner mode.

## Design Decisions

- **One run per pair, in sequence**: For each selected scenario and strategy, call the idempotent seed, capture a baseline, run the strategy, and capture post-run state. Sequential execution avoids cross-case contamination from shared state and follows the requested seed-before-each-run behavior.
- **Non-destructive isolation**: Snapshot incident identifiers and the relevant incident fields after the seed. Compare identifiers and fields after execution. For read-only C1, require no new incidents and no changes to alert/incident operational state. Never truncate tables, delete records, or recreate the database.
- **Seed reuse**: Extract or reuse the seed's idempotent upsert operation so the command can invoke the same seed behavior without duplicating fixture data. Update fixture conflicts for severity. A seed failure aborts the run with an explicit command error.
- **Alert severity**: Add `Alert.Severity` with `critical`, `warning`, and `info` values. Assign the three current firing fixtures `critical`, and the three resolved fixtures `info`; retain `warning` as a supported classification. Add a migration that provides a safe default for legacy rows and deterministically backfills the three specified firing fixture rows using historical models. Expose severity in alert DTOs, filters, selected ORM values, and `list_alerts` tool responses.
- **C1 answer check**: Count critical firing alerts in the post-seed baseline and require the answer to include the exact integer; require zero changes in persistent operational state. With the current seed, the expected answer count is three.
- **C2 answer and state check**: Use fixed requested service order `checkout`, `worker`, `api`. Parse/normalize the response for all three service names, `SEV2`, and a positive resolution statement for checkout. Independently validate exactly three new incidents, one per expected service, each severity `SEV2`, with checkout resolved and worker/api open. Existing incidents are ignored for the new-record check.
- **C3 answer and state check**: Select the baseline firing alert with stable `(created_at, id)` ascending order. Validate exactly one new incident for its service. Calculate “remaining” as firing alerts whose service has no new incident in this run; require the answer to contain that exact integer.
- **Pass/fail behavior**: A case passes only if its text and ORM state checks both pass. An ordinary assertion mismatch creates a failed result row and processing continues through the remaining matrix; setup, seed, DB, or model configuration/execution exceptions are surfaced and return command failure without success-shaped fallback.
- **Metrics and timing**: Time the strategy invocation only, excluding seed, snapshots, and display. ReAct callback/model metrics and Plan-and-Execute graph metrics supply model-call totals; the no-replanner finalization call is counted. Store the duration in milliseconds per case.
- **No-replanner path**: When disabled, execute the initial planned steps in order without calling the replanner. Once steps are complete, make one final model call with the original request and observations to synthesize a user-facing answer; do not generate or modify additional steps. Normal mode retains the existing replanning graph and behavior. ReAct ignores this setting.
- **CLI validation and output**: Validate scenario and strategy names before seed/model calls; default to all scenarios and both strategies. Print a deterministic plain-text table with scenario, strategy, pass/fail, LLM calls, and latency. Return exit status 1 if any case validation fails, 0 only if all selected cases pass.
- **Testing seam**: Inject or patch model creation, seed invocation, strategies, and DB state helpers in command tests. Test scenario checks as pure functions with controlled state; test schema/seed/read-path behavior in operations tests. No test calls OpenRouter or another external service.

## Complexity Tracking

No additional projects, persistence layers, or architectural exceptions are introduced.
