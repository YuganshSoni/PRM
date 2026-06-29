from server.models.enums import HealthStatus
from server.services.scheduler_results import (
    ComplianceRunResult,
    HealthComputationResult,
    HealthFlagResult,
    HealthPersistResult,
    MissedMarkResult,
    RecomputeResult,
    RiskFlagDraft,
    SchedulerRunResult,
)


def test_recompute_result_fields():
    result = RecomputeResult(bench_count=3, allocated_count=7)
    assert result.bench_count == 3
    assert result.allocated_count == 7


def test_missed_mark_result_fields():
    result = MissedMarkResult(created=1, updated=2, skipped=3)
    assert (result.created, result.updated, result.skipped) == (1, 2, 3)


def test_risk_flag_draft_and_health_computation():
    flag = RiskFlagDraft(flag_text="Delay", is_positive=False, sort_order=1)
    result = HealthComputationResult(
        health_status=HealthStatus.AT_RISK,
        risk_flags=[flag],
    )
    assert result.health_status == HealthStatus.AT_RISK
    assert result.risk_flags[0].flag_text == "Delay"
    assert result.risk_flags[0].is_positive is False


def test_health_persist_result():
    health = object()
    result = HealthPersistResult(health=health, transitioned_to_at_risk=True)
    assert result.health is health
    assert result.transitioned_to_at_risk is True


def test_health_flag_result():
    result = HealthFlagResult(
        projects_processed=10,
        on_track_count=5,
        attention_count=3,
        at_risk_count=2,
        at_risk_transitions=[1, 9],
    )
    assert result.projects_processed == 10
    assert result.at_risk_transitions == [1, 9]


def test_compliance_and_scheduler_run_result_defaults():
    compliance = ComplianceRunResult(reminders_sent=4, freezes_applied=1)
    result = SchedulerRunResult(
        recompute=RecomputeResult(1, 2),
        missed=MissedMarkResult(0, 0, 1),
        health=HealthFlagResult(1, 1, 0, 0, []),
        compliance=compliance,
    )
    assert result.compliance is compliance
    assert result.at_risk_emails_sent == 0

    with_emails = SchedulerRunResult(
        recompute=result.recompute,
        missed=result.missed,
        health=result.health,
        at_risk_emails_sent=2,
    )
    assert with_emails.compliance is None
    assert with_emails.at_risk_emails_sent == 2


def test_scheduler_results_are_frozen():
    import pytest

    result = RecomputeResult(1, 2)
    with pytest.raises(Exception):
        result.bench_count = 99  # type: ignore[misc]
