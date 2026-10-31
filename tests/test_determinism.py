"""Offline tests for Determinism and Repeatability in Policy Gatekeeper."""

import os
from datetime import datetime, timezone
import pytest

from policy.evaluator import PolicyEvaluator
from policy.schema import ActionRequest, Outcome

MULTICALL3 = "0xcA11bde05977b3631167028862bE2a173976CA11"
ONE_PHRS = 1000000000000000000
POLICY_YAML = os.path.join(os.path.dirname(os.path.dirname(__file__)), "examples", "policy.yaml")


@pytest.fixture
def policy_evaluator():
    return PolicyEvaluator.from_yaml_file(POLICY_YAML)


def test_evaluation_determinism_repeated_runs(policy_evaluator):
    """Identical input, policy, and injected evaluation time produce identical decisions across 50 runs."""
    injected_time = datetime(2026, 11, 4, 14, 0, 0, tzinfo=timezone.utc)
    req = ActionRequest(
        action_id="act-determ-01",
        target=MULTICALL3,
        value_wei=ONE_PHRS // 2,
        data="0xbce38bd700000000",
        timestamp=int(injected_time.timestamp()),
    )

    baseline = policy_evaluator.evaluate(req, evaluation_time=injected_time)

    for _ in range(50):
        decision = policy_evaluator.evaluate(req, evaluation_time=injected_time)
        assert decision.outcome == baseline.outcome
        assert decision.decision_id == baseline.decision_id
        assert decision.deciding_rule_id == baseline.deciding_rule_id
        assert decision.deciding_rule_type == baseline.deciding_rule_type
        assert decision.reason == baseline.reason
        assert decision.policy_id == baseline.policy_id
        assert decision.policy_version == baseline.policy_version
        assert decision.timestamp == baseline.timestamp
        assert len(decision.evaluations) == len(baseline.evaluations)
        for e1, e2 in zip(decision.evaluations, baseline.evaluations):
            assert e1.rule_id == e2.rule_id
            assert e1.passed == e2.passed
            assert e1.message == e2.message


def test_deny_determinism_repeated_runs(policy_evaluator):
    """Denied requests produce identical explanations and rule attribution across repeated runs."""
    injected_time = datetime(2026, 11, 4, 14, 0, 0, tzinfo=timezone.utc)
    req = ActionRequest(
        action_id="act-determ-deny",
        target=MULTICALL3,
        value_wei=5 * ONE_PHRS,  # Exceeds 1.0 PHRS limit
        timestamp=int(injected_time.timestamp()),
    )

    baseline = policy_evaluator.evaluate(req, evaluation_time=injected_time)
    assert baseline.outcome == Outcome.DENY

    for _ in range(50):
        decision = policy_evaluator.evaluate(req, evaluation_time=injected_time)
        assert decision.outcome == Outcome.DENY
        assert decision.decision_id == baseline.decision_id
        assert decision.deciding_rule_id == "rule-spend-limit-01"
        assert decision.reason == baseline.reason
