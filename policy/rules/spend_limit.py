"""Spend limit policy rule implementation for Pharos Policy Gatekeeper.

Enforces per-transaction value caps and ERC20 token transfer limits
using pure integer arithmetic to prevent floating-point inaccuracies.
"""

from decimal import Decimal
from typing import Any, Dict, List, Optional

from policy.rules.base import BaseRule
from policy.schema import ActionRequest, RuleEvaluationResult, RuleType

# Standard ERC20 function selectors
TRANSFER_SELECTOR = "0xa9059cbb"  # transfer(address,uint256)
APPROVE_SELECTOR = "0x095ea7b3"   # approve(address,uint256)


class SpendLimitRule(BaseRule):
    """Evaluates whether an action exceeds native wei limits or ERC20 token transfer limits."""

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
            rule_type=RuleType.SPEND_LIMIT,
            enabled=enabled,
            parameters=parameters,
        )
        params = self.parameters or {}

        # Max native limit in wei (e.g., 1000000000000000000 wei = 1.0 PHRS)
        raw_native_max = params.get("max_native_wei", "1000000000000000000")
        self.max_native_wei: int = int(raw_native_max)

        # Optional cumulative native limit in wei
        raw_cumulative = params.get("max_cumulative_native_wei")
        self.max_cumulative_native_wei: Optional[int] = (
            int(raw_cumulative) if raw_cumulative is not None else None
        )

        # Registered ERC20 token limits
        self.token_limits: Dict[str, Dict[str, Any]] = {}
        for token_cfg in params.get("tokens", []):
            contract = str(token_cfg.get("contract", "")).strip().lower()
            if contract:
                self.token_limits[contract] = {
                    "symbol": token_cfg.get("symbol", "TOKEN"),
                    "decimals": int(token_cfg.get("decimals", 18)),
                    "max_amount_raw": int(token_cfg.get("max_amount_raw", 0)),
                }

    def _evaluate(
        self, request: ActionRequest, context: Optional[Dict[str, Any]] = None
    ) -> RuleEvaluationResult:
        # 1. Native Value Check
        if request.value_wei < 0:
            return RuleEvaluationResult(
                rule_id=self.rule_id,
                rule_type=self.rule_type,
                passed=False,
                message=f"Invalid or negative native value_wei ({request.value_wei}).",
            )

        if request.value_wei > self.max_native_wei:
            excess_wei = request.value_wei - self.max_native_wei
            phrs_val = Decimal(request.value_wei) / Decimal(10**18)
            phrs_max = Decimal(self.max_native_wei) / Decimal(10**18)
            return RuleEvaluationResult(
                rule_id=self.rule_id,
                rule_type=self.rule_type,
                passed=False,
                message=(
                    f"Native spend of {request.value_wei} wei ({phrs_val:.4f} PHRS) "
                    f"exceeds per-transaction limit of {self.max_native_wei} wei ({phrs_max:.4f} PHRS) "
                    f"by {excess_wei} wei."
                ),
            )

        # 2. Cumulative Native Spend Check
        if self.max_cumulative_native_wei is not None and context:
            prior_cumulative = int(context.get("cumulative_native_wei", 0))
            projected = prior_cumulative + request.value_wei
            if projected > self.max_cumulative_native_wei:
                return RuleEvaluationResult(
                    rule_id=self.rule_id,
                    rule_type=self.rule_type,
                    passed=False,
                    message=(
                        f"Cumulative native spend of {projected} wei exceeds rolling cap of "
                        f"{self.max_cumulative_native_wei} wei."
                    ),
                )

        # 3. ERC20 Token Spend Check
        target_normalized = request.target.lower()
        if target_normalized in self.token_limits:
            token_cfg = self.token_limits[target_normalized]
            symbol = token_cfg["symbol"]
            decimals = token_cfg["decimals"]
            max_amount_raw = token_cfg["max_amount_raw"]

            # Inspect calldata for ERC20 transfer or approve
            data = request.data
            if len(data) >= 10:
                selector = data[:10].lower()
                if selector in (TRANSFER_SELECTOR, APPROVE_SELECTOR):
                    # Calldata must be at least 10 (selector) + 64 (address) + 64 (uint256) chars
                    if len(data) < 138:
                        return RuleEvaluationResult(
                            rule_id=self.rule_id,
                            rule_type=self.rule_type,
                            passed=False,
                            message=f"Malformed ERC20 {symbol} calldata (length {len(data)} < 138).",
                        )

                    amount_hex = data[74:138]
                    try:
                        amount_raw = int(amount_hex, 16)
                    except ValueError:
                        return RuleEvaluationResult(
                            rule_id=self.rule_id,
                            rule_type=self.rule_type,
                            passed=False,
                            message=f"Invalid hexadecimal integer in ERC20 {symbol} calldata.",
                        )

                    if amount_raw > max_amount_raw:
                        human_amt = Decimal(amount_raw) / Decimal(10**decimals)
                        human_max = Decimal(max_amount_raw) / Decimal(10**decimals)
                        action_name = "transfer" if selector == TRANSFER_SELECTOR else "approve"
                        return RuleEvaluationResult(
                            rule_id=self.rule_id,
                            rule_type=self.rule_type,
                            passed=False,
                            message=(
                                f"ERC20 {symbol} {action_name} amount of {amount_raw} units "
                                f"({human_amt:.4f} {symbol}) exceeds limit of {max_amount_raw} units "
                                f"({human_max:.4f} {symbol})."
                            ),
                        )

        # All spend checks passed
        return RuleEvaluationResult(
            rule_id=self.rule_id,
            rule_type=self.rule_type,
            passed=True,
            message=f"Spend limit check passed: value {request.value_wei} wei <= {self.max_native_wei} wei.",
        )
