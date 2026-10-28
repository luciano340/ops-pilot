# Tasks: Reflection Decorator

**Input**: Design documents from `/specs/004-reflection-decorator/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/arena-cli.md, quickstart.md

**Tests**: Included because the specification explicitly requires deterministic unit tests without external network calls.

**Organization**: Tasks are grouped by user story; User Story 2 depends on the reflection decorator delivered by User Story 1.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: The task can proceed in parallel with other marked tasks because it edits separate files and has no unmet dependencies.
- **[Story]**: User-story label corresponding to the approved specification.
- Each task includes the exact implementation or test file path.

## Phase 1: Setup

**Purpose**: No project initialization or dependency changes are needed; the application, test layout, and required dependencies already exist.

No tasks.

## Phase 2: Foundational

**Purpose**: No cross-story infrastructure is needed. The decorator and evaluator schema belong to User Story 1; arena selection belongs to User Story 2.

No tasks.

## Phase 3: User Story 1 - Revisar e corrigir uma resposta operacional (Priority: P1) 🎯 MVP

**Goal**: Evaluate each answer against the original request and trace observations, retry with critique feedback within the configured correction limit, and return the final result with its complete trace and aggregate metrics.

**Independent Test**: Run `pytest tests/agents/test_reflection.py`; approval on the first attempt causes no retry, rejection followed by approval causes one correction with the original request and feedback preserved, and continuous rejection stops at the configured limit. All cases use injected doubles and no network.

### Tests for User Story 1

- [X] T001 [US1] Add deterministic tests for first-attempt approval, rejection followed by approval, default and custom correction limits, zero corrections, observation-only evaluator evidence, chronological critique traces, aggregate metrics, and invalid evaluator output in `tests/agents/test_reflection.py`

### Implementation for User Story 1

- [X] T002 [US1] Define the Pydantic `CritiqueOutput` schema and typed injectable evaluator contract, rejecting extra fields and preserving invalid structured output as an explicit failure, in `src/agents/reflection.py`
- [X] T003 [US1] Implement the async reflection loop in `src/agents/reflection.py`: validate a non-negative `max_reflections` defaulting to two, evaluate the initial answer, pass only observation events with the original request and answer, append rejection feedback without dropping the original request on corrections, and stop on approval or the limit
- [X] T004 [US1] Aggregate each base attempt's answer, trace, and metrics with one chronological `critique` event per evaluation, including evaluator chat-model call counts and elapsed time, in `src/agents/reflection.py`

**Checkpoint**: User Story 1 is independently testable with a base strategy and evaluator stub; it returns the last attempt and critique even when the correction limit is reached.

## Phase 4: User Story 2 - Escolher uma estratégia com reflexão e inspecionar sua execução (Priority: P2)

**Goal**: Expose reflection as an opt-in wrapper for both supported strategies while retaining existing selectors and result formatting.

**Independent Test**: Run `pytest tests/agents/test_arena_command.py`; both reflected selectors construct the matching wrapped strategy with the shared configured model, and existing undecorated selectors remain valid.

### Tests for User Story 2

- [X] T005 [US2] Add command-boundary tests for accepting `reflect:react` and `reflect:plan_and_execute`, rejecting unknown or duplicate selectors, constructing each matching decorator, and preserving undecorated strategy selection in `tests/agents/test_arena_command.py`

### Implementation for User Story 2

- [X] T006 [P] [US2] Extend the validated strategy-name choices to accept `reflect:react` and `reflect:plan_and_execute` while preserving existing choices and duplicate rejection in `src/agents/schemas.py`
- [X] T007 [P] [US2] Compose each selected reflected strategy with its existing base strategy and a structured-output evaluator built from the same configured model, preserving existing undecorated construction and reflected result names, in `src/agents/management/commands/arena.py`

**Checkpoint**: Both reflected modes are selectable and remain distinguishable in arena output; existing modes continue to work without reflection.

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Verify the full agent test suite and the project's strict type checks.

- [X] T008 Run `pytest tests/agents/` and `mypy .` from the repository root, covering the implementation in `src/agents/` and tests in `tests/agents/`; resolve any regressions before marking the feature complete

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No tasks; no project initialization is needed.
- **Foundational (Phase 2)**: No tasks; no shared blocking infrastructure is needed.
- **User Story 1 (Phase 3)**: Independent; delivers the MVP decorator and deterministic tests.
- **User Story 2 (Phase 4)**: Depends on User Story 1's decorator interface so the arena can construct it.
- **Polish (Phase 5)**: Depends on the desired user stories being implemented.

### User Story Dependencies

- **User Story 1 (P1)**: No dependencies on other stories.
- **User Story 2 (P2)**: Depends on User Story 1 (T002-T004) for the decorator and evaluator interface.

### Within Each User Story

- Write and run the deterministic story tests before implementation.
- Complete the critique schema and evaluator contract before implementing the reflection loop and aggregate result.
- In User Story 2, the schema and arena command tasks edit separate files and may proceed in parallel after the command tests are defined and User Story 1 is complete.
- Run the focused independent test for each story before moving to the next story.

### Dependency Graph

```text
T001 -> T002 -> T003 -> T004 -> T005 -> (T006 || T007) -> T008
```

### Parallel Opportunities

- In User Story 2, T006 (`src/agents/schemas.py`) and T007 (`src/agents/management/commands/arena.py`) can be implemented in parallel after T005 is defined and User Story 1 is complete; they edit separate files and both follow the accepted CLI contract.
- No setup or foundational tasks are required, so there is no artificial project-wide blocking phase.

## Parallel Example: User Story 2

```text
After T005 and User Story 1 (T002-T004) are complete:
Task: T006 - Extend accepted strategy names in src/agents/schemas.py
Task: T007 - Compose reflected strategies in src/agents/management/commands/arena.py
```

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete T001-T004.
2. Run `pytest tests/agents/test_reflection.py`.
3. Confirm the decorator remains usable directly without arena changes.

### Incremental Delivery

1. Deliver and independently validate User Story 1 as the MVP.
2. Complete T005-T007 to add the two reflected arena selectors.
3. Run `pytest tests/agents/test_arena_command.py`.
4. Complete T008 to verify all agent tests and strict typing.
