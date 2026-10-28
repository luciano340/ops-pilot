import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID

from operations.models import Alert, Incident

ScenarioKey = Literal["c1", "c2", "c3"]
StrategyName = Literal["react", "plan_and_execute"]

C1_REQUEST = "Quantos alertas críticos estão disparando?"
C2_REQUEST = (
    "Abra três incidentes SEV2 para checkout, worker e api nessa ordem, "
    "e resolva o primeiro."
)
C3_REQUEST = (
    "Dos alertas disparando, abra um incidente para o mais antigo "
    "e diga quantos sobraram."
)


@dataclass(frozen=True, slots=True)
class BenchmarkScenario:
    key: ScenarioKey
    request: str


SCENARIOS: dict[ScenarioKey, BenchmarkScenario] = {
    "c1": BenchmarkScenario(key="c1", request=C1_REQUEST),
    "c2": BenchmarkScenario(key="c2", request=C2_REQUEST),
    "c3": BenchmarkScenario(key="c3", request=C3_REQUEST),
}


@dataclass(frozen=True, slots=True)
class AlertSnapshot:
    id: UUID
    service: str
    name: str
    message: str
    status: str
    severity: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class IncidentSnapshot:
    id: UUID
    title: str
    service: str
    severity: str
    status: str
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None


@dataclass(frozen=True, slots=True)
class BenchmarkSnapshot:
    alerts: tuple[AlertSnapshot, ...]
    incidents: tuple[IncidentSnapshot, ...]


@dataclass(frozen=True, slots=True)
class BenchmarkResult:
    scenario: ScenarioKey
    strategy: StrategyName
    passed: bool
    llm_calls: int
    latency_ms: float
    details: str = ""


_NUMBER_WORDS: dict[int, tuple[str, ...]] = {
    0: ("zero",),
    1: ("um", "uma", "one"),
    2: ("dois", "duas", "two"),
    3: ("tres", "three"),
    4: ("quatro", "four"),
    5: ("cinco", "five"),
    6: ("seis", "six"),
    7: ("sete", "seven"),
    8: ("oito", "eight"),
    9: ("nove", "nine"),
    10: ("dez", "ten"),
    11: ("onze", "eleven"),
    12: ("doze", "twelve"),
    13: ("treze", "thirteen"),
    14: ("quatorze", "catorze", "fourteen"),
    15: ("quinze", "fifteen"),
    16: ("dezesseis", "sixteen"),
    17: ("dezessete", "seventeen"),
    18: ("dezoito", "eighteen"),
    19: ("dezenove", "nineteen"),
    20: ("vinte", "twenty"),
}


def capture_snapshot() -> BenchmarkSnapshot:
    alerts = tuple(
        AlertSnapshot(
            id=alert.id,
            service=alert.service.name,
            name=alert.name,
            message=alert.message,
            status=alert.status,
            severity=alert.severity,
            created_at=alert.created_at,
            updated_at=alert.updated_at,
        )
        for alert in Alert.objects.select_related("service")
        .only(
            "id",
            "service__name",
            "name",
            "message",
            "status",
            "severity",
            "created_at",
            "updated_at",
        )
        .order_by("id")
    )
    incidents = tuple(
        IncidentSnapshot(
            id=incident.id,
            title=incident.title,
            service=incident.service.name,
            severity=incident.severity,
            status=incident.status,
            created_at=incident.created_at,
            updated_at=incident.updated_at,
            resolved_at=incident.resolved_at,
        )
        for incident in Incident.objects.select_related("service")
        .only(
            "id",
            "title",
            "service__name",
            "severity",
            "status",
            "created_at",
            "updated_at",
            "resolved_at",
        )
        .order_by("id")
    )
    return BenchmarkSnapshot(alerts=alerts, incidents=incidents)


def oldest_firing_alert(snapshot: BenchmarkSnapshot) -> AlertSnapshot | None:
    firing = [
        alert for alert in snapshot.alerts if alert.status == Alert.Status.FIRING
    ]
    return min(firing, key=lambda alert: (alert.created_at, alert.id), default=None)


def count_uncovered_firing_alerts(
    snapshot: BenchmarkSnapshot,
    covered_services: set[str],
) -> int:
    return sum(
        alert.status == Alert.Status.FIRING and alert.service not in covered_services
        for alert in snapshot.alerts
    )


def _normalized_text(value: str) -> str:
    decomposed = unicodedata.normalize("NFD", value.casefold())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def _contains_number(value: str, expected: int) -> bool:
    normalized = _normalized_text(value)
    if re.search(rf"(?<!\w){expected}(?!\w)", normalized):
        return True
    return any(
        re.search(rf"\b{re.escape(word)}\b", normalized)
        for word in _NUMBER_WORDS.get(expected, ())
    )


def validate_answer(
    scenario: ScenarioKey,
    answer: str,
    baseline: BenchmarkSnapshot,
) -> list[str]:
    normalized = _normalized_text(answer)
    errors: list[str] = []
    if scenario == "c1":
        expected = sum(
            alert.status == Alert.Status.FIRING
            and alert.severity == Alert.Severity.CRITICAL
            for alert in baseline.alerts
        )
        if not _contains_number(answer, expected):
            errors.append(
                f"answer does not report the expected critical firing alert count "
                f"({expected})"
            )
    elif scenario == "c2":
        services = ("checkout", "worker", "api")
        positions = [normalized.find(service) for service in services]
        if any(position < 0 for position in positions):
            errors.append("answer must mention checkout, worker, and api")
        elif positions != sorted(positions):
            errors.append("answer must report checkout, worker, and api in order")
        if not re.search(r"\bsev[\s-]*2\b", normalized):
            errors.append("answer must mention SEV2")
        resolved = re.search(r"\bresolv(?:ed|ido|ida|er|eram|e|eu)\b", normalized)
        negated_resolution = re.search(
            r"\b(?:not|never|nao)\s+(?:(?:be|foi|esta|estava)\s+)?resolv",
            normalized,
        )
        if resolved is None or negated_resolution is not None:
            errors.append("answer must state that checkout was resolved")
    else:
        target = oldest_firing_alert(baseline)
        if target is None:
            errors.append("C3 cannot run because the baseline has no firing alerts")
        else:
            expected = count_uncovered_firing_alerts(baseline, {target.service})
            if not _contains_number(answer, expected):
                errors.append(
                    f"answer does not report the expected remaining alert count "
                    f"({expected})"
                )
    return errors


def validate_state(
    scenario: ScenarioKey,
    baseline: BenchmarkSnapshot,
    after: BenchmarkSnapshot,
) -> list[str]:
    errors: list[str] = []
    before_alerts = {alert.id: alert for alert in baseline.alerts}
    after_alerts = {alert.id: alert for alert in after.alerts}
    before_incidents = {incident.id: incident for incident in baseline.incidents}
    after_incidents = {incident.id: incident for incident in after.incidents}

    changed_alerts = [
        alert_id
        for alert_id, alert in before_alerts.items()
        if after_alerts.get(alert_id) != alert
    ]
    new_alerts = after_alerts.keys() - before_alerts.keys()
    if changed_alerts or new_alerts:
        errors.append("alerts were changed or added during the strategy run")

    changed_incidents = [
        incident_id
        for incident_id, incident in before_incidents.items()
        if after_incidents.get(incident_id) != incident
    ]
    if changed_incidents:
        errors.append("preexisting incidents were changed during the strategy run")

    new_incidents = [
        incident
        for incident_id, incident in after_incidents.items()
        if incident_id not in before_incidents
    ]
    if scenario == "c1":
        if new_incidents:
            errors.append("C1 must not create incidents")
        if after_incidents.keys() != before_incidents.keys():
            errors.append("C1 must not remove or add incidents")
    elif scenario == "c2":
        if len(new_incidents) != 3:
            errors.append(
                f"C2 must create exactly three incidents; found {len(new_incidents)}"
            )
        expected_statuses = {
            "checkout": Incident.Status.RESOLVED,
            "worker": Incident.Status.OPEN,
            "api": Incident.Status.OPEN,
        }
        by_service: dict[str, list[IncidentSnapshot]] = {}
        for incident in new_incidents:
            by_service.setdefault(incident.service, []).append(incident)
            if incident.severity.casefold() != "sev2":
                errors.append(
                    f"C2 incident for {incident.service} must have severity SEV2"
                )
        if set(by_service) != set(expected_statuses):
            errors.append("C2 incidents must cover checkout, worker, and api")
        for service, expected_status in expected_statuses.items():
            incidents = by_service.get(service, [])
            if len(incidents) != 1:
                errors.append(f"C2 must create exactly one incident for {service}")
            elif incidents[0].status != expected_status:
                errors.append(
                    f"C2 incident for {service} must be {expected_status}"
                )
            elif service == "checkout" and incidents[0].resolved_at is None:
                errors.append("C2 checkout incident must have a resolution timestamp")
    else:
        target = oldest_firing_alert(baseline)
        if target is None:
            errors.append("C3 cannot run because the baseline has no firing alerts")
        if len(new_incidents) != 1:
            errors.append(
                f"C3 must create exactly one incident; found {len(new_incidents)}"
            )
        elif target is not None:
            incident = new_incidents[0]
            if incident.service != target.service:
                errors.append(
                    f"C3 incident must target {target.service}, not {incident.service}"
                )
            if incident.status != Incident.Status.OPEN:
                errors.append("C3 incident must remain open")
    return errors
