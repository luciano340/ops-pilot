# Research: Benchmark de Desempenho

**Date**: 2026-10-28

## Django management command structure

- **Decision**: Implement `bench` as a synchronous Django management command that validates arguments, prepares each pair, runs the asynchronous strategy at the command boundary, and reports consolidated results. Keep scenario specifications and pure answer/state validators in a separate benchmark module.
- **Rationale**: This follows Django's management-command lifecycle and the existing arena command's synchronous boundary around asynchronous agent execution. It keeps CLI errors at the boundary and makes validation independently testable.
- **Alternatives considered**: Run all benchmark logic in a model/service layer; create a standalone executable. Those alternatives bypass the established CLI wiring and blur command-level errors with domain responsibilities.
- **Sources**: [Django custom management commands](https://docs.djangoproject.com/en/6.1/howto/custom-management-commands/); [Django `call_command` testing](https://docs.djangoproject.com/en/6.1/topics/testing/tools/#django.core.management.call_command).

## Scenario isolation and database assertions

- **Decision**: Run the existing idempotent seed before every scenario-strategy pair, snapshot relevant persisted state after seeding, and compare the post-run state with that baseline. Run cases sequentially, and never delete or recreate operational records.
- **Rationale**: The seed upserts stable fixture identifiers and preserves unrelated records; snapshot deltas avoid contamination from preexisting incidents while satisfying the required clean fixture baseline. Synchronous ORM snapshotting outside async strategy execution avoids sync ORM use inside event-loop code.
- **Alternatives considered**: Delete all incidents or reset the database before each run; use total database counts as the expected effect. These can destroy or misattribute unrelated records.
- **Sources**: [Django custom management commands](https://docs.djangoproject.com/en/6.1/howto/custom-management-commands/); [Django async ORM queries](https://docs.djangoproject.com/en/6.1/topics/async/#queries-the-orm); [Django transactions in async code](https://docs.djangoproject.com/en/6.1/topics/async/#transactions).

## Alert severity and migration

- **Decision**: Add a constrained alert severity classification (`critical`, `warning`, `info`) and expose it through the alert query schema, DTO, store projection/filter, tool response, deterministic seed, and a data migration. Use historical models in the migration and a safe `info` fallback for legacy rows; explicitly mark the three currently firing seed alerts as critical and resolved seed alerts as info.
- **Rationale**: C1 cannot be accurately evaluated without persisted alert severity. Explicit fixture values and seed conflict updates keep repeated seeds deterministic; the migration makes existing databases compatible without requiring deletion.
- **Alternatives considered**: Infer severity from alert names at query time or hard-code C1's expected count without adding alert severity. These approaches do not provide a reliable classification to strategies or other consumers.
- **Sources**: [Django data migrations](https://docs.djangoproject.com/en/6.1/topics/migrations/#data-migrations); [Django historical models](https://docs.djangoproject.com/en/6.1/topics/migrations/#historical-models); [Django `RunPython`](https://docs.djangoproject.com/en/6.1/ref/migration-operations/#runpython).

## Plan-and-Execute without replanning

- **Decision**: Add an explicit mode that follows the original plan through its steps without invoking the replanner, then performs one final model call using the original request and accumulated observations to produce the answer; count that final model call in metrics.
- **Rationale**: Simply skipping the replanner would leave the current graph without its existing answer-finalization behavior. A separate finalization path enables a meaningful latency/call-count comparison while honoring the selected no-replanning behavior.
- **Alternatives considered**: Skip both replanning and answer synthesis; ask the model to revise steps in a final call. The former yields incomplete user-facing results; the latter still performs replanning under another name.

## Deterministic textual validation

- **Decision**: Use scenario-specific, deterministic validators that parse required integers and normalize required service/severity/status terms; always pair text checks with direct ORM state checks.
- **Rationale**: The benchmark should report repeatable pass/fail and avoid relying on another model to grade the evaluated model. State checks catch unexecuted or incorrect side effects even when prose claims success.
- **Alternatives considered**: Compare the response to an exact sentence or use a second LLM judge. Exact sentence matching is brittle; LLM judging adds nondeterminism, cost, and model calls that pollute benchmark metrics.

## Test strategy

- **Decision**: Test management command orchestration with Django `call_command` and a test database, pure scenario validators with fixed inputs, seed repeatability/preservation with ORM assertions, and strategies with fake or injected models.
- **Rationale**: Django provides command-testing utilities; repository seed tests already verify idempotence and preservation of records outside fixtures. Injected models keep tests deterministic and offline.
- **Alternatives considered**: Run the live benchmark against a remote model in CI or use a production database. These are nondeterministic, credential-dependent, and unsafe.
- **Sources**: [Django testing tools](https://docs.djangoproject.com/en/6.1/topics/testing/tools/); [Django test databases](https://docs.djangoproject.com/en/6.1/topics/testing/overview/).
