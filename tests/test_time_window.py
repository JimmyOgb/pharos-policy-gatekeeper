"""Offline unit tests for TimeWindowRule in Pharos Policy Gatekeeper."""

from datetime import datetime, timezone
import pytest

from policy.rules.time_window import TimeWindowRule
from policy.schema import ActionRequest


@pytest.fixture
def time_rule():
    return TimeWindowRule(
        rule_id="rule-time-test",
        name="Time Window Test Rule",
        parameters={
            "allowed_start_utc": "08:00:00",
            "allowed_end_utc": "20:00:00",
            "allowed_days_of_week": ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY"],
        },
    )


def test_time_window_inside_window_allow(time_rule):
    """Inside permitted UTC window on weekday: ALLOW."""
    # Wednesday 2026-11-04 14:30:00 UTC
    dt = datetime(2026, 11, 4, 14, 30, 0, tzinfo=timezone.utc)
    req = ActionRequest(
        action_id="act-time-allow",
        target="0xcA11bde05977b3631167028862bE2a173976CA11",
        timestamp=int(dt.timestamp()),
    )
    res = time_rule.evaluate(req)
    assert res.passed is True
    assert "is within authorized window" in res.message


def test_time_window_outside_window_early_deny(time_rule):
    """Outside window (too early at 03:00 UTC): DENY."""
    # Wednesday 2026-11-04 03:00:00 UTC
    dt = datetime(2026, 11, 4, 3, 0, 0, tzinfo=timezone.utc)
    req = ActionRequest(
        action_id="act-time-early",
        target="0xcA11bde05977b3631167028862bE2a173976CA11",
        timestamp=int(dt.timestamp()),
    )
    res = time_rule.evaluate(req)
    assert res.passed is False
    assert "Current time 03:00:00 UTC is outside authorized operating window" in res.message


def test_time_window_outside_window_late_deny(time_rule):
    """Outside window (too late at 22:15 UTC): DENY."""
    # Wednesday 2026-11-04 22:15:00 UTC
    dt = datetime(2026, 11, 4, 22, 15, 0, tzinfo=timezone.utc)
    req = ActionRequest(
        action_id="act-time-late",
        target="0xcA11bde05977b3631167028862bE2a173976CA11",
        timestamp=int(dt.timestamp()),
    )
    res = time_rule.evaluate(req)
    assert res.passed is False
    assert "outside authorized operating window" in res.message


def test_time_window_exact_boundary_start_allow(time_rule):
    """Exact start boundary 08:00:00 UTC: ALLOW."""
    dt = datetime(2026, 11, 4, 8, 0, 0, tzinfo=timezone.utc)
    req = ActionRequest(
        action_id="act-boundary-start",
        target="0xcA11bde05977b3631167028862bE2a173976CA11",
        timestamp=int(dt.timestamp()),
    )
    res = time_rule.evaluate(req)
    assert res.passed is True


def test_time_window_exact_boundary_end_allow(time_rule):
    """Exact end boundary 20:00:00 UTC: ALLOW."""
    dt = datetime(2026, 11, 4, 20, 0, 0, tzinfo=timezone.utc)
    req = ActionRequest(
        action_id="act-boundary-end",
        target="0xcA11bde05977b3631167028862bE2a173976CA11",
        timestamp=int(dt.timestamp()),
    )
    res = time_rule.evaluate(req)
    assert res.passed is True


def test_time_window_disallowed_weekend_deny(time_rule):
    """Disallowed day of week (Sunday): DENY."""
    # Sunday 2026-11-08 12:00:00 UTC
    dt = datetime(2026, 11, 8, 12, 0, 0, tzinfo=timezone.utc)
    req = ActionRequest(
        action_id="act-time-sunday",
        target="0xcA11bde05977b3631167028862bE2a173976CA11",
        timestamp=int(dt.timestamp()),
    )
    res = time_rule.evaluate(req)
    assert res.passed is False
    assert "Execution on SUNDAY is not permitted" in res.message


def test_time_window_clock_dependency_injection(time_rule):
    """Evaluation time injected via context overrides missing request timestamp: ALLOW."""
    req = ActionRequest(
        action_id="act-injected-time",
        target="0xcA11bde05977b3631167028862bE2a173976CA11",
        timestamp=None,  # No timestamp in request
    )
    injected_dt = datetime(2026, 11, 5, 11, 0, 0, tzinfo=timezone.utc)  # Thursday 11:00 UTC
    res = time_rule.evaluate(req, context={"evaluation_time": injected_dt})
    assert res.passed is True
    assert "THURSDAY 11:00:00 UTC is within authorized window" in res.message


def test_time_window_missing_and_invalid_timestamp_deny(time_rule):
    """Missing or invalid/negative timestamp: DENY."""
    # 1. Missing both request timestamp and context
    req_missing = ActionRequest(
        action_id="act-missing-ts",
        target="0xcA11bde05977b3631167028862bE2a173976CA11",
        timestamp=None,
    )
    res1 = time_rule.evaluate(req_missing)
    assert res1.passed is False
    assert "Missing timestamp" in res1.message

    # 2. Negative timestamp
    req_neg = ActionRequest(
        action_id="act-neg-ts",
        target="0xcA11bde05977b3631167028862bE2a173976CA11",
        timestamp=-9999,
    )
    res2 = time_rule.evaluate(req_neg)
    assert res2.passed is False
    assert "Invalid or negative timestamp" in res2.message
