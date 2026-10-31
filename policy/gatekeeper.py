"""Fail-closed Policy Gatekeeper execution interceptor for Pharos agents.

Sits strictly between agent decision logic and execution adapters, ensuring
that denied actions are physically prevented from reaching the execution layer.
"""

from datetime import datetime
from typing import Any, Callable, Dict, Optional

from policy.audit_log import AuditLogger
from policy.evaluator import PolicyEvaluator
from policy.schema import ActionRequest, Decision, Outcome


class PolicyViolationError(Exception):
    """Raised when an action is denied by policy evaluation."""

    def __init__(self, decision: Decision):
        self.decision = decision
        target = decision.action_request.target if decision.action_request else "unknown"
        action_id = decision.action_request.action_id if decision.action_request else "unknown"
        super().__init__(
            f"Execution Denied for action '{action_id}' (target: {target}) by rule "
            f"'{decision.deciding_rule_id}': {decision.reason}"
        )


class Gatekeeper:
    """Fail-closed execution wrapper enforcing strict boundary isolation."""

    def __init__(
        self,
        evaluator: PolicyEvaluator,
        audit_logger: Optional[AuditLogger] = None,
    ):
        self.evaluator = evaluator
        self.audit_logger = audit_logger

    def check(
        self,
        request: ActionRequest,
        evaluation_time: Optional[datetime] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Decision:
        """Evaluates an action request and records the decision in the audit log.
        
        Does NOT trigger execution. Read-only gate check.
        """
        decision = self.evaluator.evaluate(
            request=request,
            evaluation_time=evaluation_time,
            context=context,
        )

        # Record in audit log if logger is attached
        if self.audit_logger is not None:
            self.audit_logger.record(decision)

        return decision

    def execute_safely(
        self,
        request: ActionRequest,
        execution_adapter: Callable[[ActionRequest], Any],
        evaluation_time: Optional[datetime] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Enforces fail-closed execution.
        
        Evaluates the action request against policy.
        - If outcome is ALLOW: invokes execution_adapter(request) and returns result.
        - If outcome is DENY: raises PolicyViolationError. The execution_adapter
          is NEVER called. No flags or AI recommendations can override this.
        """
        if not callable(execution_adapter):
            raise TypeError("execution_adapter must be a callable function or method.")

        decision = self.check(
            request=request,
            evaluation_time=evaluation_time,
            context=context,
        )

        if decision.outcome != Outcome.ALLOW:
            # Physical boundary: execution_adapter is never reached
            raise PolicyViolationError(decision)

        # Authorized: dispatch to execution adapter
        return execution_adapter(request)
