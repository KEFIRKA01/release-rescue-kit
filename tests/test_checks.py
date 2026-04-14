from pathlib import Path

from kit.checks import (
    CheckResult,
    Target,
    build_playbook,
    build_release_report,
    load_targets,
    maintenance_window_risk,
    owner_workload,
    run_targets,
    summarize,
)


def test_summary_marks_system_unstable_on_critical_failure() -> None:
    report = summarize(
        [
            CheckResult(name="api", ok=False, severity="critical", note="500", response_ms=1500),
            CheckResult(name="landing", ok=True, severity="critical", note="ok", response_ms=120),
        ]
    )
    assert report["status"] == "unstable"
    assert report["critical_count"] == 1


def test_summary_stays_stable_when_all_pass() -> None:
    report = summarize([CheckResult(name="ok", ok=True, severity="critical", note="ok", response_ms=100)])
    assert report["status"] == "stable"
    assert report["score"] == 100


def test_load_targets_and_build_release_report() -> None:
    targets_path = Path(__file__).resolve().parents[1] / "seed" / "demo_targets.json"
    results = run_targets(load_targets(targets_path))
    report = build_release_report(results)
    assert report["summary"]["warning_count"] == 1
    assert report["recommendation"] == "Ship carefully with focused monitoring."
    assert report["playbook"]


def test_maintenance_window_and_owner_workload_cover_unusual_rescue_cases() -> None:
    targets = [
        Target(name="legacy_crm", critical=True, owner="integrations", expected_ms=700, simulated_ms=1200, available=True),
        Target(name="white_label_portal", critical=True, owner="frontend", expected_ms=900, simulated_ms=300, available=False),
    ]
    assert maintenance_window_risk(targets, window_minutes=10) == "unsafe"
    workload = owner_workload(run_targets(targets))
    assert workload["integrations"]["issues"] == 1
    playbook = build_playbook(run_targets(targets))
    assert len(playbook) == 2
