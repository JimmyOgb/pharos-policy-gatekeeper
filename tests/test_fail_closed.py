"""Offline security tests for Fail-Closed Execution and Boundary Isolation."""

import os
from datetime import datetime, timezone
import pytest

from policy.evaluator import PolicyEvaluator
from policy.gatekeeper import Gatekeeper, PolicyViolationError
from policy.rules.base import BaseRule
from policy.schema import ActionRequest, Outcome, RuleEvaluationResult, RuleType

MULTICALL3 = "0xcA11bde05977b3631167028862bE2a173976CA11"
ONE_PHRS = 1000000000000000000
POLICY_YAML = os.path.join(os.path.dirname(os.path.dirname(__file__)), "examples", "policy.yaml")


class FailingExceptionRule(BaseRule):
    """Rule deliberately raising an unexpected internal exception to test fail-closed handling."""

    def __init__(self):
        super().__init__(
            rule_id="rule-exploding",
            name="Exploding Rule",
            rule_type=RuleType.FAIL_CLOSED_DEFAULT,
        )

    def _evaluate(self, request, context=None):
        raise RuntimeError("Simulated internal evaluator crash!")


class MockExecutionAdapter:
    """Instrumented test adapter recording every call dispatched to the execution layer."""

    def __init__(self):
        self.call_count = 0
        self.executed_requests = []

    def execute(self, request: ActionRequest):
        self.call_count += 1
        self.executed_requests.append(request)
        return {"status": "success", "tx_hash": "0xsimulated_hash"}


@pytest.fixture
def policy_evaluator():
    return PolicyEvaluator.from_yaml_file(POLICY_YAML)


def test_fail_closed_on_unknown_action_type(policy_evaluator):
    """Unknown action type: strictly DENY."""
    req = ActionRequest(
        action_id="act-unknown-type",
        target=MULTICALL3,
        action_type="arbitrary_system_command",  # Not in {'evm_call', 'evm_transfer'}
        timestamp=int(datetime(2026, 11, 4, 12, 0, 0, tzinfo=timezone.utc).timestamp()),
    )
    decision = policy_evaluator.evaluate(req)
    assert decision.outcome == Outcome.DENY
    assert decision.deciding_rule_type == RuleType.FAIL_CLOSED_DEFAULT
    assert "Unknown or unauthorized action_type" in decision.reason


def test_fail_closed_on_missing_action_id(policy_evaluator):
    """Missing action_id: strictly DENY."""
    req = ActionRequest(
        action_id="",  # Empty action_id
        target=MULTICALL3,
        timestamp=int(datetime(2026, 11, 4, 12, 0, 0, tzinfo=timezone.utc).timestamp()),
    )
    decision = policy_evaluator.evaluate(req)
    assert decision.outcome == Outcome.DENY
    assert decision.deciding_rule_type == RuleType.SCHEMA_VALIDATION
    assert "missing mandatory 'action_id'" in decision.reason


def test_fail_closed_on_missing_target(policy_evaluator):
    """Missing target address: strictly DENY."""
    req = ActionRequest(
        action_id="act-missing-target",
        target="",  # Empty target
        timestamp=int(datetime(2026, 11, 4, 12, 0, 0, tzinfo=timezone.utc).timestamp()),
    )
    decision = policy_evaluator.evaluate(req)
    assert decision.outcome == Outcome.DENY
    assert decision.deciding_rule_type == RuleType.SCHEMA_VALIDATION
    assert "missing mandatory 'target'" in decision.reason


def test_fail_closed_on_malformed_policy_config():
    """Missing mandatory rules in policy config: raises ValueError."""
    bad_config = {
        "policy_id": "bad-policy",
        "version": "1.0.0",
        "rules": [
            {"id": "r1", "type": "spend_limit", "parameters": {}},
            # Missing allowlist and time_window
        ],
    }
    with pytest.raises(ValueError, match="Policy configuration must contain at least 3 rules"):
        PolicyEvaluator.from_dict(bad_config)


def test_fail_closed_on_internal_rule_exception():
    """Internal rule exception is caught and fails closed to DENY."""
    exploding_rule = FailingExceptionRule()
    evaluator = PolicyEvaluator(
        policy_id="exploding-policy",
        version="1.0.0",
        rules=[exploding_rule],
    )
    req = ActionRequest(
        action_id="act-explode",
        target=MULTICALL3,
        timestamp=int(datetime(2026, 11, 4, 12, 0, 0, tzinfo=timezone.utc).timestamp()),
    )
    decision = evaluator.evaluate(req)
    assert decision.outcome == Outcome.DENY
    assert decision.deciding_rule_id == "rule-exploding"
    assert "Internal rule evaluation exception" in decision.reason


def test_fail_closed_multiple_simultaneous_rule_failures(policy_evaluator):
    """Action failing multiple rules (spend + target + time) deterministically returns first failing rule."""
    # Bad spend (5.0 PHRS), bad target (0x9999...9999), bad time (03:00 UTC)
    bad_ts = int(datetime(2026, 11, 4, 3, 0, 0, tzinfo=timezone.utc).timestamp())
    req = ActionRequest(
        action_id="act-triple-fail",
        target="0x9999999999999999999999999999999999999999",
        value_wei=5 * ONE_PHRS,
        timestamp=bad_ts,
    )
    decision = policy_evaluator.evaluate(req)
    assert decision.outcome == Outcome.DENY
    # Spend limit rule is evaluated first
    assert decision.deciding_rule_id == "rule-spend-limit-01"
    assert "exceeds per-transaction limit" in decision.reason
    # Evaluations trace includes all checks
    assert len(decision.evaluations) == 3


def test_gatekeeper_physical_execution_isolation(policy_evaluator):
    """Execution adapter is NEVER called for denied requests, called exactly once for allowed requests."""
    gatekeeper = Gatekeeper(evaluator=policy_evaluator)
    adapter = MockExecutionAdapter()

    # 1. Test DENIED request (spend exceeded)
    denied_req = ActionRequest(
        action_id="act-deny-isolation",
        target=MULTICALL3,
        value_wei=5 * ONE_PHRS,
        timestamp=int(datetime(2026, 11, 4, 12, 0, 0, tzinfo=timezone.utc).timestamp()),
    )

    with pytest.raises(PolicyViolationError) as exc_info:
        gatekeeper.execute_safely(denied_req, execution_adapter=adapter.execute)

    assert "Execution Denied" in str(exc_info.value)
    # Critical invariant: adapter must NOT have been called
    assert adapter.call_count == 0
    assert len(adapter.executed_requests) == 0

    # 2. Test ALLOWED request
    allowed_req = ActionRequest(
        action_id="act-allow-isolation",
        target=MULTICALL3,
        value_wei=ONE_PHRS // 2,
        data="0xbce38bd700000000",
        timestamp=int(datetime(2026, 11, 4, 12, 0, 0, tzinfo=timezone.utc).timestamp()),
    )

    result = gatekeeper.execute_safely(allowed_req, execution_adapter=adapter.execute)
    assert result["status"] == "success"
    # Critical invariant: adapter called exactly once
    assert adapter.call_count == 1
    assert adapter.executed_requests[0].action_id == "act-allow-isolation"
