# Data Model: Benchmark de Desempenho

The benchmark does not persist run records. It operates on the existing alert, service, and incident records and uses transient snapshots to validate each run.

## Alert severity

`Alert` gains an explicit severity classification.

| Value | Meaning |
|---|---|
| `critical` | Highest urgency; assigned to all three firing alerts in the current sample seed. |
| `warning` | Elevated but non-critical urgency; available for other alerts and fixtures. |
| `info` | Informational classification; assigned to the three resolved alerts in the current sample seed and used as a safe migration default. |

Validation rules:

- Every alert has exactly one supported severity.
- Seed fixture severity is deterministic and updated when a fixture alert already exists.
- Alert list input may filter by severity; alert DTOs and tool outputs include it.
- The migration uses a safe default for existing rows and backfills the specified seed fixture rows to their intended values.

## Benchmark scenario

| Field | Meaning |
|---|---|
| Scenario key | One of `c1`, `c2`, or `c3`. |
| Request | Fixed operational prompt executed by the strategy. |
| Baseline expectations | Counts, target alert, or intended operations derived after seed. |
| Text validator | Deterministic checks over the returned strategy answer. |
| State validator | Direct ORM checks comparing persisted state with the post-seed baseline. |

### C1

- Expected critical firing alert count is derived from the post-seed rows; it is three for the current seed.
- The answer must contain the exact expected integer.
- The run must not create incidents or modify operational alert/incident state.

### C2

- Requested service order: `checkout`, `worker`, `api`.
- Expected new incidents: exactly three, all `SEV2`, with one per service.
- Expected statuses: checkout resolved, worker open, api open.
- Text validation requires the answer to mention the three services, `SEV2`, and that checkout was resolved.

### C3

- Target alert: firing alert ordered first by `(created_at, id)` ascending in the baseline.
- Expected new incident: one incident for the target alert's service.
- Remaining count: number of baseline firing alerts whose service has no incident created during this execution.
- The answer must contain the exact remaining count.

## Baseline snapshot

Transient read-only record sets captured after seeding and before the strategy invocation.

| Snapshot | Values |
|---|---|
| Alerts | Alert IDs, status, severity, service ID, and other fields relevant to detecting scenario changes. |
| Incidents | Incident IDs and relevant service, severity, status, and resolution fields. |

Post-run comparison uses ID differences for new incidents and field comparisons for baseline records. No snapshot is written to storage; no baseline record is deleted or modified by benchmark preparation.

## Benchmark result

One result per scenario-strategy pair.

| Field | Type/meaning |
|---|---|
| Scenario | `c1`, `c2`, or `c3`. |
| Strategy | `react` or `plan_and_execute`. |
| Passed | True only when both textual and persisted-state validation pass. |
| LLM calls | Total model calls made by the strategy for this run, including finalization if no-replanner mode is active. |
| Latency (ms) | Strategy execution duration; excludes seed, baseline queries, and output formatting. |
| Failure details | Human-readable mismatch details shown for failed cases, not a success-shaped fallback. |

The command exit status is zero only when all selected results pass; any failed validation yields exit status one.
