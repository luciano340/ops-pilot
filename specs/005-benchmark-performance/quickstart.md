# Quickstart: Benchmark de Desempenho

## Prerequisites

- Python 3.14, repository dependencies, and the project's virtual environment.
- Apply database migrations before running the benchmark.
- A database configured for OpsPilot. The command seeds sample services and alerts but does not clear incidents or other records.
- OpenRouter credentials and model configuration for live model execution.

## Run focused scenarios

```powershell
python manage.py bench --scenario c1 --strategies react
python manage.py bench -s c2 --strategies plan_and_execute
python manage.py bench --scenario c3 --strategies react,plan_and_execute --no-replanner
```

## Run the full matrix

```powershell
python manage.py bench
```

Expected behavior:

- The seed runs before every scenario-strategy pair.
- Each run captures a baseline and validates response text plus persisted ORM effects without deleting preexisting records.
- C3 exposes alert creation timestamps to the strategies and directs them to request firing alerts in `oldest` order; the first result is the deterministic target, with ID as the tie-break.
- The full matrix prints six rows, one per scenario and strategy, containing pass/fail, LLM calls, and latency.
- Exit code is zero only if all selected combinations pass; otherwise it is one.

## Deterministic validation

```powershell
pytest tests/operations/test_seed_db.py tests/operations/test_services.py tests/operations/test_store.py
pytest tests/agents/test_plan_and_execute.py tests/agents/test_bench_command.py
mypy .
```

Use fake or injected models in tests. No test should call OpenRouter or another external service.

See the [CLI contract](./contracts/bench-cli.md) and [data model](./data-model.md) for matrix, state-delta, severity, and validation rules.
