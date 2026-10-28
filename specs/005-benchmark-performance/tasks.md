# Tasks: Benchmark de Desempenho

**Input**: Design documents from `/specs/005-benchmark-performance/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/bench-cli.md, quickstart.md

**Tests**: Included because the project constitution requires tests for new behavior and the feature requires deterministic validation without external model calls.

**Organization**: Tasks are grouped by user story. Shared alert severity and seed support are foundational because all benchmark scenarios depend on the prepared alert data.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: The task can proceed in parallel with another marked task because they affect separate files and have no unmet dependency.
- **[Story]**: User-story label corresponding to the approved specification.
- Each task names the exact source or test file paths to change or validate.

## Phase 1: Setup

**Purpose**: The Django project, migration framework, CLI package, and test environment already exist.

No tasks.

## Phase 2: Foundational

**Purpose**: Add alert severity consistently before implementing benchmark scenarios that query critical alerts.

- [X] T001 Add tests for alert severity migration defaults, severity filtering and serialization, deterministic seed severities on repeated runs, and preservation of records outside the seed fixture in `tests/operations/test_seed_db.py`, `tests/operations/test_services.py`, and `tests/operations/test_store.py`
- [X] T002 Add `Alert.Severity` with exactly `critical`, `warning`, and `info` choices and safe default `info` in `src/operations/models.py`; create `src/operations/migrations/0002_alert_severity.py` with historical-model backfill assigning `critical` to the three specified firing seed alerts and `info` to the three resolved seed alerts
- [X] T003 [P] Propagate alert severity through `ListAlertsInput`, `ListAlertsDTO`, and `AlertDTO`, supporting optional severity filtering in the service and store and including severity in returned alert data in `src/operations/schemas.py`, `src/operations/domain.py`, `src/operations/services.py`, `src/operations/store.py`, and `src/agents/tools.py`
- [X] T004 [P] Assign explicit deterministic severities to every `ALERT_FIXTURE` entry and include severity in conflict updates so repeated `seed_db` runs refresh it in `src/operations/management/commands/seed_db.py`

**Checkpoint**: Existing alerts migrate safely; repeated seed runs establish the same severities; the alert query/tool path exposes and filters severity.

## Phase 3: User Story 1 - Medir leitura e operações sequenciais (Priority: P1) 🎯 MVP

**Goal**: Validate C1 critical-alert reading and C2 sequential incident creation/resolution using both response text and persisted state deltas.

**Independent Test**: Run the C1/C2 scenario tests with fixed alert and incident baselines and injected strategies; verify exact critical count, no C1 writes, exactly three new SEV2 incidents for the requested services in C2, checkout resolved, worker/api open, and preservation of preexisting records.

### Tests for User Story 1

- [X] T005 [US1] Add offline scenario tests for C1 and C2 text parsing, baseline-derived expectations, new-incident deltas, incident statuses, and rejection when either text or persisted state is incorrect in `tests/test_bench.py`

### Implementation for User Story 1

- [X] T006 [US1] Define typed benchmark scenario/result records, the fixed C1 and C2 requests, and deterministic response-text validators for exact critical count and the ordered `checkout`, `worker`, `api` plus `SEV2`/resolution response requirements in `src/bench.py`
- [X] T007 [US1] Implement non-destructive baseline snapshots and ORM delta validators for C1 read-only state and C2's exactly-three-new-incident requirements in `src/bench.py`; compare incident IDs and relevant service, severity, status, and resolution fields without deleting records
- [X] T008 [US1] Implement the first `bench` management command flow for C1/C2 in `src/agents/management/commands/bench.py`: invoke the existing seed before each scenario-strategy pair, snapshot after seed, run one selected strategy, time only strategy execution, record model calls, validate text plus state, and surface setup/execution failures

**Checkpoint**: C1/C2 can be executed and independently evaluated against ORM state without clearing operational records.

## Phase 4: User Story 2 - Avaliar lógica dinâmica com alertas (Priority: P2)

**Goal**: Validate C3 target selection, incident creation for the oldest firing alert's service, and the remaining-alert count.

**Independent Test**: Use fixed firing alerts with timestamps and IDs plus preexisting incidents; verify stable `(created_at, id)` target selection, exactly one new incident for its service, and exact response count for uncovered firing-alert services.

### Tests for User Story 2

- [X] T009 [US2] Add deterministic C3 tests for earliest-alert selection with ID tie-break, one new incident for the target service, uncovered-alert count, preexisting-record exclusion, and mismatched answer/state failure in `tests/test_bench.py`

### Implementation for User Story 2

- [X] T010 [US2] Add the C3 request, stable `(created_at, id)` target selection, expected uncovered firing-alert calculation, and response/state validators in `src/bench.py`; treat no firing alerts as a clear non-executable scenario failure

**Checkpoint**: C3 passes only when the text count and new incident's service match the post-seed baseline calculations.

## Phase 5: User Story 3 - Selecionar, comparar e inspecionar execuções (Priority: P2)

**Goal**: Support the complete matrix and CLI filters, optional no-replanner mode, consolidated output, and correct process exit status.

**Independent Test**: Run command tests with patched seed, ORM snapshots, model creation, and strategy doubles; verify the default six combinations, each filter, validation before side effects, result table fields, no-replanner wiring, and exit status for all-pass versus any-failure results.

### Tests for User Story 3

- [X] T011 [P] [US3] Add command tests for default `all`/both-strategy matrix, `--scenario` and `-s` filters, comma-separated strategy filters, invalid or empty selectors before model/seed work, result columns, continuation after validation mismatch, and exit codes in `tests/agents/test_bench_command.py`
- [X] T012 [P] [US3] Add Plan-and-Execute tests asserting no replanner invocation when disabled, ordered execution of the initial plan, one final answer-synthesis model call, and correct LLM-call metrics while preserving default replanning behavior in `tests/agents/test_plan_and_execute.py`

### Implementation for User Story 3

- [X] T013 [P] [US3] Add validated `--scenario`/`-s`, `--strategies`, and `--no-replanner` arguments; execute the selected scenario-strategy matrix sequentially, print the required five-column table, and return failure for any failed result in `src/agents/management/commands/bench.py`
- [X] T014 [P] [US3] Add an opt-in no-replanner mode to `PlanAndExecuteStrategy` in `src/agents/plan_and_execute.py`: execute only initial planned steps, skip the replanner node, make exactly one final model call from the original request and observations, and count that call without changing default behavior

**Checkpoint**: Default invocation reports six cases; filters reduce the matrix as requested; no-replanner affects only Plan-and-Execute and is represented in its call metrics.

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Verify migrations, all feature-related tests, agent regressions, and strict typing.

- [X] T015 Run the full test suite with `.venv\Scripts\python.exe -m pytest`, verify `manage.py makemigrations --check --dry-run` and `manage.py check`, then run `.venv\Scripts\mypy.exe .`; resolve all feature regressions before completion

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No tasks; project infrastructure already exists.
- **Foundational (Phase 2)**: Required before C1 because critical severity must be persisted and queryable; T003 and T004 can proceed in parallel after T002.
- **User Story 1 (Phase 3)**: Depends on the foundational alert severity and seed work; delivers the MVP scenarios C1 and C2.
- **User Story 2 (Phase 4)**: Depends on the shared scenario result and baseline helpers from User Story 1.
- **User Story 3 (Phase 5)**: Depends on all three scenarios and the initial benchmark command; Plan-and-Execute no-replanner implementation can proceed in parallel with CLI filtering after its tests are defined.
- **Polish (Phase 6)**: Depends on all desired stories being complete.

### User Story Dependencies

- **User Story 1 (P1)**: Depends on Phase 2; no dependency on later stories.
- **User Story 2 (P2)**: Depends on User Story 1's benchmark scenario/result helpers in `src/bench.py`.
- **User Story 3 (P2)**: Depends on the C1-C3 matrix and initial command flow. Its Plan-and-Execute graph change is isolated from the command implementation.

### Within Each Phase

- T001 tests are written before alert model and migration implementation.
- T002 must precede T003 and T004 because both rely on the new severity field.
- T005 precedes C1/C2 helper and command implementation.
- T009 precedes C3 scenario implementation.
- T011 and T012 test different files and can proceed in parallel; T013 and T014 also edit separate source files and can proceed in parallel after their tests are established.

### Dependency Graph

```text
T001 -> T002 -> (T003 || T004) -> T005 -> T006 -> T007 -> T008
T008 -> (T009 -> T010) -> T013
T008 -> T011 -> T013
T008 -> T012 -> T014
T010 -> T015; T013 -> T015; T014 -> T015
```

### Parallel Opportunities

- After T002, T003 (operations read-path propagation) and T004 (seed fixture updates) touch separate files and may run in parallel.
- After User Story 1, C3 tests/implementation (T009-T010) may run in parallel with CLI/strategy tests (T011-T012), as they touch separate test and source modules; the command integration in T013 should wait for both T010 and T011.
- After T011/T012 and C3 helper completion, T013 (`src/agents/management/commands/bench.py`) and T014 (`src/agents/plan_and_execute.py`) may run in parallel.

## Parallel Example: User Story 3

```text
After T011 and T012 tests are defined and T010 is complete:
Task: T013 - Add CLI selection, matrix execution, output, and exit status in src/agents/management/commands/bench.py
Task: T014 - Add no-replanner execution and final synthesis in src/agents/plan_and_execute.py
```

## Implementation Strategy

### MVP First (User Story 1)

1. Complete T001-T008, including the foundational severity migration and seed changes.
2. Run focused operations, C1, and C2 tests.
3. Confirm C1/C2 validate both response content and persisted state without deleting existing records.

### Incremental Delivery

1. Add C3 with T009-T010 and verify dynamic target/count behavior independently.
2. Add full CLI filtering, comparison table, and no-replanner mode with T011-T014.
3. Run T015 for the feature-specific tests and strict project type check.
