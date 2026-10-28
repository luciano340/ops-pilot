# Benchmark CLI Contract

## Invocation

```text
python manage.py bench [--scenario {c1,c2,c3,all}] [--strategies react,plan_and_execute] [--no-replanner]
```

## Options

| Option | Default | Behavior |
|---|---|---|
| `--scenario`, `-s` | `all` | Run one scenario (`c1`, `c2`, or `c3`) or all three. |
| `--strategies` | `react,plan_and_execute` | Comma-separated selection of one or both supported strategies. Unknown and empty selections are errors. |
| `--no-replanner` | Disabled | For Plan-and-Execute only, execute the initial plan without replanning, then make one final model call to synthesize the answer. Does not change ReAct behavior. |

Argument errors are reported before the seed, database queries, or model configuration are invoked.

## Execution behavior

For each selected scenario-strategy pair, sequentially:

1. Run the existing idempotent seed to prepare the fixture state.
2. Capture the relevant state baseline after the seed.
3. Execute exactly one strategy run for the pair.
4. Capture persisted state and validate changes against the baseline.
5. Validate both the strategy response text and scenario state.

The command does not delete database tables or preexisting operational records. Seed, database, model configuration, and execution errors are surfaced explicitly.

## Scenario requests

| Key | Request |
|---|---|
| `c1` | `Quantos alertas críticos estão disparando?` |
| `c2` | `Abra três incidentes SEV2 para checkout, worker e api nessa ordem, e resolva o primeiro.` |
| `c3` | `Dos alertas disparando, abra um incidente para o mais antigo e diga quantos sobraram.` |

## Output

Print one row for each selected scenario-strategy pair with the columns:

| Cenário | Estratégia | Acerto | Chamadas LLM | Latência (ms) |
|---|---|---|---:|---:|

Failed validations are shown as failures and include a concise reason; remaining selected cases continue where execution infrastructure remains available.

## Exit status

- `0`: every selected scenario-strategy result passed both response-text and persisted-state validation.
- `1`: one or more validations failed, or seed, database, model configuration, or strategy execution failed.
