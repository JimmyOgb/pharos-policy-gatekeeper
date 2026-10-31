"""Deterministic policy evaluation engine for Pharos Policy Gatekeeper.

Parses policy definitions, validates incoming ActionRequests, evaluates rules
sequentially, and produces explicit, deterministic Decision objects.
"""

from datetime import datetime, timezone
import hashlib
import json
import os
from typing import Any, Dict, List, Optional, Set, Union
import uuid

import yaml

from policy.rules.allowlist import AllowlistRule
from policy.rules.base import BaseRule
from policy.rules.spend_limit import SpendLimitRule
from policy.rules.time_window import TimeWindowRule
from policy.schema import ActionRequest, Decision, Outcome, RuleEvaluationResult, RuleType

# Permitted action types for agent operations
ALLOWED_ACTION_TYPES: Set[str] = {"evm_call", "evm_transfer"}


class PolicyEvaluator:
    """Evaluates ActionRequests deterministically against a loaded policy configuration."""

    def __init__(
        self,
        policy_id: str,
        version: str,
        rules: List[BaseRule],
        name: str = "",
        description: str = "",
        network: Optional[Dict[str, Any]] = None,
        default_action: str = "DENY",
    ):
        self.policy_id = policy_id
        self.version = version
        self.rules = rules
        self.name = name
        self.description = description
        self.network = network or {}
        self.default_action = default_action

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PolicyEvaluator":
        """Instantiates an evaluator from a policy dictionary."""
        if not isinstance(data, dict):
            raise ValueError(f"Policy configuration must be a dictionary, got {type(data)}.")

        policy_id = str(data.get("policy_id", "")).strip()
        version = str(data.get("version", "")).strip()
        if not policy_id:
            raise ValueError("Policy configuration is missing required 'policy_id'.")
        if not version:
            raise ValueError("Policy configuration is missing required 'version'.")

        name = str(data.get("name", ""))
        description = str(data.get("description", ""))
        network = data.get("network", {})
        default_action = data.get("default_action", "DENY")

        raw_rules = data.get("rules", [])
        if not isinstance(raw_rules, list) or len(raw_rules) < 3:
            raise ValueError(
                f"Policy configuration must contain at least 3 rules (spend_limit, allowlist, time_window), "
                f"found {len(raw_rules) if isinstance(raw_rules, list) else 0}."
            )

        rules: List[BaseRule] = []
        rule_types_found: Set[str] = set()

        for idx, r_data in enumerate(raw_rules):
            if not isinstance(r_data, dict):
                raise ValueError(f"Rule at index {idx} must be a dictionary.")

            r_id = str(r_data.get("id", f"rule-{idx}")).strip()
            r_type_str = str(r_data.get("type", "")).strip()
            r_name = str(r_data.get("name", r_id))
            r_enabled = bool(r_data.get("enabled", True))
            r_params = r_data.get("parameters", {})

            rule_types_found.add(r_type_str)

            if r_type_str == RuleType.SPEND_LIMIT.value:
                rules.append(SpendLimitRule(rule_id=r_id, name=r_name, enabled=r_enabled, parameters=r_params))
            elif r_type_str == RuleType.ALLOWLIST.value:
                rules.append(AllowlistRule(rule_id=r_id, name=r_name, enabled=r_enabled, parameters=r_params))
            elif r_type_str == RuleType.TIME_WINDOW.value:
                rules.append(TimeWindowRule(rule_id=r_id, name=r_name, enabled=r_enabled, parameters=r_params))
            else:
                raise ValueError(f"Unknown or unsupported rule type '{r_type_str}' in rule '{r_id}'.")

        required_types = {RuleType.SPEND_LIMIT.value, RuleType.ALLOWLIST.value, RuleType.TIME_WINDOW.value}
        missing = required_types - rule_types_found
        if missing:
            raise ValueError(f"Policy is missing mandatory rule type(s): {missing}.")

        return cls(
            policy_id=policy_id,
            version=version,
            rules=rules,
            name=name,
            description=description,
            network=network,
            default_action=default_action,
        )

    @classmethod
    def from_yaml_file(cls, path: str) -> "PolicyEvaluator":
        """Loads and parses a policy from a YAML or JSON file."""
        if not os.path.exists(path):
            raise FileNotFoundError(f"Policy file not found: {path}")
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return cls.from_dict(data)

    @classmethod
    def from_yaml_str(cls, content: str) -> "PolicyEvaluator":
        """Loads and parses a policy from a YAML or JSON string."""
        data = yaml.safe_load(content)
        return cls.from_dict(data)

    def evaluate(
        self,
        request: ActionRequest,
        evaluation_time: Optional[datetime] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Decision:
        """Evaluates an ActionRequest against all policy rules deterministically.
        
        Guarantees fail-closed behavior:
        - Missing or invalid request fields -> DENY
        - Unknown action types -> DENY
        - Any failing rule -> DENY with deciding rule ID & reason
        - Rule exceptions -> DENY with exception details
        """
        eval_ctx = dict(context or {})
        if evaluation_time is not None:
            eval_ctx["evaluation_time"] = evaluation_time

        # Determine evaluation timestamp string
        if evaluation_time is not None:
            ts_dt = evaluation_time.astimezone(timezone.utc)
        elif request.timestamp is not None and isinstance(request.timestamp, (int, float)) and request.timestamp >= 0:
            try:
                ts_dt = datetime.fromtimestamp(request.timestamp, tz=timezone.utc)
            except Exception:
                ts_dt = datetime.now(timezone.utc)
        else:
            ts_dt = datetime.now(timezone.utc)

        ts_str = ts_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

        # Deterministic decision ID derived from policy_id, action_id, and timestamp
        raw_hash_seed = f"{self.policy_id}:{request.action_id}:{request.target}:{request.value_wei}:{ts_str}"
        short_hash = hashlib.sha256(raw_hash_seed.encode("utf-8")).hexdigest()[:12]
        decision_id = f"dec-{self.policy_id}-{request.action_id}-{short_hash}"

        # 1. Action Request Integrity Check (Fail-closed)
        if not request.action_id:
            return Decision(
                decision_id=decision_id,
                outcome=Outcome.DENY,
                deciding_rule_id="schema_validation",
                deciding_rule_type=RuleType.SCHEMA_VALIDATION,
                reason="ActionRequest is missing mandatory 'action_id'.",
                policy_id=self.policy_id,
                policy_version=self.version,
                timestamp=ts_str,
                evaluations=[],
                action_request=request,
            )

        if not request.target:
            return Decision(
                decision_id=decision_id,
                outcome=Outcome.DENY,
                deciding_rule_id="schema_validation",
                deciding_rule_type=RuleType.SCHEMA_VALIDATION,
                reason="ActionRequest is missing mandatory 'target' address.",
                policy_id=self.policy_id,
                policy_version=self.version,
                timestamp=ts_str,
                evaluations=[],
                action_request=request,
            )

        # 2. Action Type Check (Fail-closed)
        if request.action_type not in ALLOWED_ACTION_TYPES:
            return Decision(
                decision_id=decision_id,
                outcome=Outcome.DENY,
                deciding_rule_id="fail_closed_action_type",
                deciding_rule_type=RuleType.FAIL_CLOSED_DEFAULT,
                reason=(
                    f"Unknown or unauthorized action_type '{request.action_type}'. "
                    f"Permitted types: {sorted(list(ALLOWED_ACTION_TYPES))}."
                ),
                policy_id=self.policy_id,
                policy_version=self.version,
                timestamp=ts_str,
                evaluations=[],
                action_request=request,
            )

        # 3. Sequential Rule Evaluation
        evaluations: List[RuleEvaluationResult] = []
        first_failure: Optional[RuleEvaluationResult] = None

        for rule in self.rules:
            res = rule.evaluate(request, eval_ctx)
            evaluations.append(res)
            if not res.passed and first_failure is None:
                first_failure = res

        # 4. Synthesize Deterministic Verdict
        if first_failure is not None:
            return Decision(
                decision_id=decision_id,
                outcome=Outcome.DENY,
                deciding_rule_id=first_failure.rule_id,
                deciding_rule_type=first_failure.rule_type,
                reason=first_failure.message,
                policy_id=self.policy_id,
                policy_version=self.version,
                timestamp=ts_str,
                evaluations=evaluations,
                action_request=request,
            )

        # All rules passed
        return Decision(
            decision_id=decision_id,
            outcome=Outcome.ALLOW,
            deciding_rule_id="all_rules_passed",
            deciding_rule_type=RuleType.FAIL_CLOSED_DEFAULT,
            reason="All policy security rules satisfied.",
            policy_id=self.policy_id,
            policy_version=self.version,
            timestamp=ts_str,
            evaluations=evaluations,
            action_request=request,
        )
