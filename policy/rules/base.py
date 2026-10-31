"""Abstract base rule interface for deterministic policy evaluation."""

from abc import ABC, abstractmethod
import time
from typing import Any, Dict, Optional

from policy.schema import ActionRequest, RuleEvaluationResult, RuleType


class BaseRule(ABC):
    """Abstract base class that all policy rules must implement."""

    def __init__(
        self,
        rule_id: str,
        name: str,
        rule_type: RuleType,
        enabled: bool = True,
        parameters: Optional[Dict[str, Any]] = None,
    ):
        self.rule_id = rule_id
        self.name = name
        self.rule_type = rule_type
        self.enabled = enabled
        self.parameters = parameters or {}

    def evaluate(self, request: ActionRequest, context: Optional[Dict[str, Any]] = None) -> RuleEvaluationResult:
        """Evaluates an action request against this rule.
        
        Enforces fail-closed safety: if any unexpected exception is raised
        during evaluation, it catches the error and returns passed=False.
        """
        if not self.enabled:
            return RuleEvaluationResult(
                rule_id=self.rule_id,
                rule_type=self.rule_type,
                passed=True,
                message=f"Rule '{self.name}' is disabled; skipping evaluation.",
                execution_time_ms=0.0,
            )

        start_time = time.perf_counter()
        try:
            result = self._evaluate(request, context)
            result.execution_time_ms = (time.perf_counter() - start_time) * 1000.0
            return result
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            # Fail-closed guarantee: any exception inside rule logic returns passed=False
            return RuleEvaluationResult(
                rule_id=self.rule_id,
                rule_type=self.rule_type,
                passed=False,
                message=f"Internal rule evaluation exception in '{self.name}': {type(exc).__name__}: {str(exc)}",
                execution_time_ms=elapsed_ms,
            )

    @abstractmethod
    def _evaluate(self, request: ActionRequest, context: Optional[Dict[str, Any]] = None) -> RuleEvaluationResult:
        """Concrete rule implementation logic. Subclasses must implement this."""
        raise NotImplementedError("Subclasses must implement _evaluate()")
