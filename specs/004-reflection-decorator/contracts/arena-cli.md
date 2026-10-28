# Arena CLI Contract

## Purpose

Select an undecorated or reflection-decorated reasoning strategy through the existing Django management command.

## Invocation

```text
python manage.py arena "<request>" --strategies <comma-separated-names>
```

The command retains its existing default strategies and `--max-iterations` option.

## Accepted strategy names

| Name | Behavior | Result name |
|---|---|---|
| `react` | Run ReAct without reflection. | `react` |
| `plan_and_execute` | Run Plan-and-Execute without reflection. | `plan_and_execute` |
| `reflect:react` | Run ReAct with reflection. | `reflect:react` |
| `reflect:plan_and_execute` | Run Plan-and-Execute with reflection. | `reflect:plan_and_execute` |

Names are comma-separated; duplicate names are invalid. The two reflected selectors are opt-in and do not replace the existing choices.

## Output

Each selected strategy produces one result section in the existing arena format. A reflected result includes the final answer, all attempt and critique trace events in chronological order, and aggregate `llm_calls` and `latency_ms`.

## Errors

Invalid or duplicate strategy selectors are rejected during command-input validation and surfaced as a CLI error. Invalid evaluator output and model configuration failures are not converted into successful answers.
