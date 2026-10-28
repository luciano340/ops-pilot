from datetime import datetime, timezone
from uuid import UUID

from bench import (
    AlertSnapshot,
    BenchmarkSnapshot,
    IncidentSnapshot,
    count_uncovered_firing_alerts,
    oldest_firing_alert,
    validate_answer,
    validate_state,
)


def _alert(
    alert_id: str,
    service: str,
    *,
    created_at: datetime | None = None,
    status: str = "firing",
    severity: str = "critical",
) -> AlertSnapshot:
    return AlertSnapshot(
        id=UUID(alert_id),
        service=service,
        name=f"{service} alert",
        message="observed",
        status=status,
        severity=severity,
        created_at=created_at or datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


def _incident(
    incident_id: str,
    service: str,
    severity: str,
    status: str,
) -> IncidentSnapshot:
    return IncidentSnapshot(
        id=UUID(incident_id),
        title=f"{service} issue",
        service=service,
        severity=severity,
        status=status,
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        resolved_at=(
            datetime(2026, 1, 1, tzinfo=timezone.utc)
            if status == "resolved"
            else None
        ),
    )


def _snapshot(
    alerts: tuple[AlertSnapshot, ...] = (),
    incidents: tuple[IncidentSnapshot, ...] = (),
) -> BenchmarkSnapshot:
    return BenchmarkSnapshot(alerts=alerts, incidents=incidents)


def test_c1_answer_matches_exact_critical_firing_count() -> None:
    baseline = _snapshot(
        alerts=(
            _alert("00000000-0000-0000-0000-000000000001", "api"),
            _alert("00000000-0000-0000-0000-000000000002", "checkout"),
            _alert("00000000-0000-0000-0000-000000000003", "worker"),
            _alert(
                "00000000-0000-0000-0000-000000000004",
                "web",
                status="resolved",
            ),
        )
    )

    assert validate_answer("c1", "Há três alertas críticos disparando.", baseline) == []
    assert validate_answer("c1", "Há 4 alertas críticos disparando.", baseline)


def test_c1_rejects_any_change_to_alerts_or_incidents() -> None:
    alert = _alert("00000000-0000-0000-0000-000000000001", "api")
    baseline = _snapshot(alerts=(alert,))
    changed = _snapshot(
        alerts=(alert,),
        incidents=(
            _incident(
                "10000000-0000-0000-0000-000000000001",
                "api",
                "SEV2",
                "open",
            ),
        ),
    )

    assert validate_state("c1", baseline, baseline) == []
    assert validate_state("c1", baseline, changed)


def test_c2_requires_three_new_sev2_incidents_and_requested_statuses() -> None:
    baseline = _snapshot()
    after = _snapshot(
        incidents=(
            _incident(
                "10000000-0000-0000-0000-000000000001",
                "checkout",
                "SEV2",
                "resolved",
            ),
            _incident(
                "10000000-0000-0000-0000-000000000002",
                "worker",
                "SEV2",
                "open",
            ),
            _incident(
                "10000000-0000-0000-0000-000000000003",
                "api",
                "SEV2",
                "open",
            ),
        )
    )

    assert validate_answer(
        "c2",
        "Opened SEV2 incidents for checkout, worker, and api in order; "
        "checkout was resolved.",
        baseline,
    ) == []
    assert validate_state("c2", baseline, after) == []


def test_c2_rejects_incorrect_incident_effects() -> None:
    baseline = _snapshot()
    after = _snapshot(
        incidents=(
            _incident(
                "10000000-0000-0000-0000-000000000001",
                "checkout",
                "SEV1",
                "open",
            ),
        )
    )

    assert validate_state("c2", baseline, after)
    assert validate_answer("c2", "Created incidents for checkout and worker.", baseline)
    assert validate_answer(
        "c2",
        "Opened SEV2 incidents for checkout, worker, and api, "
        "but checkout não foi resolvido.",
        baseline,
    )


def test_c3_selects_oldest_alert_with_id_tie_break_and_counts_uncovered_services() -> None:
    first = _alert(
        "00000000-0000-0000-0000-000000000001",
        "checkout",
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    tied_later_id = _alert(
        "00000000-0000-0000-0000-000000000002",
        "worker",
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    newer = _alert(
        "00000000-0000-0000-0000-000000000003",
        "api",
        created_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
    )
    baseline = _snapshot(alerts=(newer, tied_later_id, first))
    after = _snapshot(
        alerts=(newer, tied_later_id, first),
        incidents=(
            _incident(
                "10000000-0000-0000-0000-000000000001",
                "checkout",
                "SEV2",
                "open",
            ),
        ),
    )

    assert oldest_firing_alert(baseline) == first
    assert count_uncovered_firing_alerts(baseline, {"checkout"}) == 2
    assert validate_answer("c3", "Dois alertas firing sobraram.", baseline) == []
    assert validate_state("c3", baseline, after) == []


def test_c3_without_firing_alerts_is_a_scenario_failure() -> None:
    baseline = _snapshot(
        alerts=(
            _alert(
                "00000000-0000-0000-0000-000000000001",
                "api",
                status="resolved",
            ),
        )
    )

    assert validate_answer("c3", "Nenhum alerta sobrou.", baseline)
    assert validate_state("c3", baseline, baseline)
