from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, List


@dataclass(slots=True)
class CheckResult:
    name: str
    ok: bool
    severity: str
    note: str
    response_ms: int | None = None
    owner: str | None = None


@dataclass(slots=True)
class Target:
    name: str
    critical: bool
    owner: str
    expected_ms: int
    simulated_ms: int
    available: bool = True


def evaluate_target(target: Target) -> CheckResult:
    severity = "critical" if target.critical else "warning"
    if not target.available:
        return CheckResult(
            name=target.name,
            ok=False,
            severity=severity,
            note="Service is unavailable",
            response_ms=target.simulated_ms,
            owner=target.owner,
        )
    if target.simulated_ms > target.expected_ms:
        return CheckResult(
            name=target.name,
            ok=False,
            severity="warning",
            note=f"Latency above threshold: {target.simulated_ms}ms > {target.expected_ms}ms",
            response_ms=target.simulated_ms,
            owner=target.owner,
        )
    return CheckResult(
        name=target.name,
        ok=True,
        severity=severity,
        note="Scenario is healthy",
        response_ms=target.simulated_ms,
        owner=target.owner,
    )


def categorize_incident(result: CheckResult) -> str:
    note = result.note.lower()
    if "latency" in note:
        return "performance"
    if "unavailable" in note:
        return "availability"
    return "functional"


def maintenance_window_risk(targets: Iterable[Target], window_minutes: int) -> str:
    critical_targets = [target for target in targets if target.critical]
    if any(not target.available for target in critical_targets):
        return "unsafe"
    if window_minutes < len(critical_targets) * 15:
        return "tight"
    return "safe"


def summarize(results: Iterable[CheckResult]) -> dict[str, object]:
    data = list(results)
    critical = [item for item in data if not item.ok and item.severity == "critical"]
    warnings = [item for item in data if not item.ok and item.severity == "warning"]
    passed = [item for item in data if item.ok]
    latencies = [item.response_ms for item in data if item.response_ms is not None]
    score = max(0, 100 - len(critical) * 35 - len(warnings) * 10)
    return {
        "score": score,
        "critical_count": len(critical),
        "warning_count": len(warnings),
        "passed_count": len(passed),
        "median_response_ms": sorted(latencies)[len(latencies) // 2] if latencies else 0,
        "status": "unstable" if critical else "attention" if warnings else "stable",
    }


def owner_workload(results: Iterable[CheckResult]) -> dict[str, dict[str, int]]:
    report: dict[str, dict[str, int]] = {}
    for item in results:
        owner = item.owner or "unknown"
        payload = report.setdefault(owner, {"issues": 0, "critical": 0})
        if not item.ok:
            payload["issues"] += 1
            if item.severity == "critical":
                payload["critical"] += 1
    return report


def build_playbook(results: Iterable[CheckResult]) -> List[str]:
    actions: List[str] = []
    for item in results:
        if item.ok:
            continue
        category = categorize_incident(item)
        if category == "performance":
            actions.append(f"{item.name}: проверить очереди, внешние API и таймауты")
        elif category == "availability":
            actions.append(f"{item.name}: поднять канал fallback и проверить доступность среды")
        else:
            actions.append(f"{item.name}: воспроизвести сценарий вручную и снять логи запроса")
    return actions


def load_targets(path: str | Path) -> List[Target]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return [Target(**item) for item in payload["targets"]]


def run_targets(targets: Iterable[Target]) -> List[CheckResult]:
    return [evaluate_target(target) for target in targets]


def smoke_catalog() -> List[CheckResult]:
    demo_targets = [
        Target(name="landing_form_submit", critical=True, owner="frontend", expected_ms=900, simulated_ms=420),
        Target(name="crm_webhook_delivery", critical=False, owner="integrations", expected_ms=600, simulated_ms=860),
        Target(name="payment_callback", critical=True, owner="backend", expected_ms=500, simulated_ms=380),
    ]
    return run_targets(demo_targets)


def build_release_report(results: Iterable[CheckResult]) -> dict[str, object]:
    data = list(results)
    summary = summarize(data)
    return {
        "summary": summary,
        "results": [asdict(item) for item in data],
        "playbook": build_playbook(data),
        "owners": owner_workload(data),
        "recommendation": (
            "Freeze release and fix critical scenarios first."
            if summary["critical_count"]
            else "Ship carefully with focused monitoring."
            if summary["warning_count"]
            else "Release looks healthy."
        ),
    }
