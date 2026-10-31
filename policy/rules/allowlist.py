"""Address and selector allowlist policy rule implementation for Pharos Policy Gatekeeper.

Enforces target contract/address whitelisting and optional function selector restrictions
with fail-closed validation on malformed addresses.
"""

import re
from typing import Any, Dict, List, Optional, Set, Union

from policy.rules.base import BaseRule
from policy.schema import ActionRequest, RuleEvaluationResult, RuleType

# Regular expression for standard EVM 20-byte address format
ADDRESS_REGEX = re.compile(r"^0x[a-fA-F0-9]{40}$")


class AllowlistRule(BaseRule):
    """Evaluates whether an action's target address and call data match allowed lists."""

    def __init__(
        self,
        rule_id: str,
        name: str,
        enabled: bool = True,
        parameters: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            rule_id=rule_id,
            name=name,
            rule_type=RuleType.ALLOWLIST,
            enabled=enabled,
            parameters=parameters,
        )
        params = self.parameters or {}

        self.allow_unknown_targets: bool = bool(params.get("allow_unknown_targets", False))
        self.strict_selectors: bool = bool(params.get("strict_selectors", False))

        # Build normalized target address set
        self.allowed_addresses: Set[str] = set()
        self.address_names: Dict[str, str] = {}
        for item in params.get("allowed_addresses", []):
            if isinstance(item, dict):
                addr = str(item.get("address", "")).strip().lower()
                name_str = item.get("name", addr)
            else:
                addr = str(item).strip().lower()
                name_str = addr
            if addr:
                self.allowed_addresses.add(addr)
                self.address_names[addr] = name_str

        # Build normalized allowed function selector set
        self.allowed_selectors: Set[str] = set()
        self.selector_names: Dict[str, str] = {}
        for item in params.get("allowed_function_selectors", []):
            if isinstance(item, dict):
                sel = str(item.get("selector", "")).strip().lower()
                sel_name = item.get("name", sel)
            else:
                sel = str(item).strip().lower()
                sel_name = sel
            if sel:
                # Ensure 0x prefix and lowercase
                if not sel.startswith("0x"):
                    sel = "0x" + sel
                self.allowed_selectors.add(sel)
                self.selector_names[sel] = sel_name

    def _evaluate(
        self, request: ActionRequest, context: Optional[Dict[str, Any]] = None
    ) -> RuleEvaluationResult:
        target = request.target

        # 1. Address Format Validation
        if not target or not isinstance(target, str) or not ADDRESS_REGEX.match(target):
            return RuleEvaluationResult(
                rule_id=self.rule_id,
                rule_type=self.rule_type,
                passed=False,
                message=f"Invalid or malformed target address format: '{target}'.",
            )

        target_normalized = target.lower()

        # 2. Whitelist Check
        if target_normalized not in self.allowed_addresses:
            if not self.allow_unknown_targets:
                return RuleEvaluationResult(
                    rule_id=self.rule_id,
                    rule_type=self.rule_type,
                    passed=False,
                    message=f"Target address '{target}' is not in authorized allowlist.",
                )

        # 3. Function Selector Check
        if self.allowed_selectors:
            data = request.data
            if len(data) >= 10:
                selector = data[:10].lower()
                if selector not in self.allowed_selectors:
                    return RuleEvaluationResult(
                        rule_id=self.rule_id,
                        rule_type=self.rule_type,
                        passed=False,
                        message=(
                            f"Function selector '{selector}' is not authorized. "
                            f"Permitted selectors: {sorted(list(self.allowed_selectors))}."
                        ),
                    )
            else:
                # Data is empty or less than 4 bytes (e.g. 0x)
                if self.strict_selectors:
                    return RuleEvaluationResult(
                        rule_id=self.rule_id,
                        rule_type=self.rule_type,
                        passed=False,
                        message="Empty or short calldata is not permitted under strict selector policy.",
                    )

        target_label = self.address_names.get(target_normalized, target)
        return RuleEvaluationResult(
            rule_id=self.rule_id,
            rule_type=self.rule_type,
            passed=True,
            message=f"Target '{target_label}' is authorized by allowlist.",
        )
