# Quickstart: Reflection Decorator Validation

## Prerequisites

- Python 3.14 and the repository virtual environment are available.
- Install the project and development dependencies according to the repository setup.
- Unit tests do not require `OPENROUTER_API_KEY`, model credentials, or network access.

## Deterministic unit tests

Run the focused reflection and arena command tests:

```powershell
pytest tests/agents/test_reflection.py tests/agents/test_arena_command.py
```

Expected outcomes:

- The initial answer is returned without correction when the critique approves.
- A rejection triggers a retry that includes feedback and retains the original request; a later approval ends the cycle.
- Rejections stop at the configured correction limit, and the final attempt is returned.
- Critique events follow their corresponding attempt traces; aggregate metrics include every strategy and evaluator invocation.
- Both reflected selectors are accepted by the CLI input boundary; invalid and duplicate names are rejected.
- Tests use injected strategies and evaluator responses and do not perform external model calls.

## Type and regression validation

```powershell
mypy .
pytest tests/agents/
```

Expected outcomes: strict typing passes, focused behavior tests pass, and existing strategy/arena behavior remains unchanged for undecorated selectors.

## Live arena smoke test (optional)

After supplying the configured OpenRouter environment variables, run a request with either selector:

```powershell
python manage.py arena "Summarize the current operational status" --strategies reflect:react
python manage.py arena "Summarize the current operational status" --strategies reflect:plan_and_execute
```

Expected outcome: one result section for the selected reflected strategy, with critique events and accumulated model metrics. This check is optional and is not part of deterministic test validation.

See the [arena CLI contract](./contracts/arena-cli.md) and [data model](./data-model.md) for output and retry semantics.
