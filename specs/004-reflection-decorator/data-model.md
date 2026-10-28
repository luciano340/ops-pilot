# Data Model: Reflection Decorator

The feature adds no persisted records. The entities below are transient values exchanged during one strategy invocation; the returned `StrategyResult` remains the public result shape.

## CritiqueOutput

Represents the evaluator's validated decision about one strategy answer.

| Field | Type | Constraints |
|---|---|---|
| `approved` | Boolean | Required; `true` ends the reflection cycle. |
| `feedback` | String | Required; supplied to the next correction attempt when rejected. |

Unexpected evaluator fields are rejected. Invalid structured output is an explicit evaluation failure, not an implicit approval.

## Reflection attempt

One strategy run and the evaluation of its answer.

| Value | Meaning |
|---|---|
| Original request | User request, retained for every evaluation and correction. |
| Strategy input | Original request, with the most recent rejection feedback appended for correction attempts. |
| Strategy result | Candidate answer, attempt trace, and attempt metrics. |
| Evidence | Contents of the attempt's trace events whose type is `observation`. |
| Critique | The corresponding `CritiqueOutput`. |
| Correction index | Zero for the initial attempt; subsequent values count corrections and may not exceed `max_reflections`. |

State transitions:

1. Run the base strategy for the original request.
2. Evaluate the candidate.
3. If approved, finish.
4. If rejected and the correction limit has not been reached, append feedback to the original request and run the base strategy again.
5. If rejected at the limit, finish with the latest strategy result and its critique.

## StrategyResult (aggregate)

The existing result contract is preserved.

| Field | Aggregate behavior |
|---|---|
| `answer` | Answer from the final strategy attempt, whether or not its last critique approved it. |
| `trace` | All attempt traces in chronological order, with one `critique` event appended immediately after each evaluated attempt. |
| `metrics.llm_calls` | Sum of all base-strategy model calls and evaluator chat-model starts. |
| `metrics.latency_ms` | Sum of all base-strategy reported latency and measured evaluator invocation latency. |

## Validation and bounds

- `max_reflections` is a non-negative integer; default is two correction attempts.
- The initial answer is always evaluated, including when `max_reflections` is zero.
- No correction follows an approval or exceeds the configured correction limit.
- Only `observation` events are supplied as evidence to the evaluator.
- The arena rejects duplicate selections as it does for existing strategies; reflected and base selectors are distinct choices.
