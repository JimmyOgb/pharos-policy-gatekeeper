"""Offline unit tests for SpendLimitRule in Pharos Policy Gatekeeper."""

from decimal import Decimal
import pytest

from policy.rules.spend_limit import SpendLimitRule
from policy.schema import ActionRequest, RuleType

# 1.0 PHRS = 10^18 wei
ONE_PHRS_WEI = 1000000000000000000
USDC_CONTRACT = "0xcfC8330f4BCAB529c625D12781b1C19466A9Fc8B"
TRANSFER_SELECTOR = "0xa9059cbb"


@pytest.fixture
def spend_rule():
    return SpendLimitRule(
        rule_id="rule-spend-test",
        name="Spend Test Rule",
        parameters={
            "max_native_wei": str(ONE_PHRS_WEI),  # 1.0 PHRS
            "max_cumulative_native_wei": str(5 * ONE_PHRS_WEI),  # 5.0 PHRS
            "tokens": [
                {
                    "symbol": "USDC",
                    "contract": USDC_CONTRACT,
                    "decimals": 6,
                    "max_amount_raw": "100000000",  # 100.0 USDC (6 decimals)
                }
            ],
        },
    )


def test_spend_limit_below_cap(spend_rule):
    """Below limit: ALLOW."""
    req = ActionRequest(
        action_id="act-spend-below",
        target="0xcA11bde05977b3631167028862bE2a173976CA11",
        value_wei=ONE_PHRS_WEI // 2,  # 0.5 PHRS
    )
    res = spend_rule.evaluate(req)
    assert res.passed is True
    assert "Spend limit check passed" in res.message


def test_spend_limit_at_cap(spend_rule):
    """At limit: ALLOW (inclusive boundary)."""
    req = ActionRequest(
        action_id="act-spend-exact",
        target="0xcA11bde05977b3631167028862bE2a173976CA11",
        value_wei=ONE_PHRS_WEI,  # exactly 1.0 PHRS
    )
    res = spend_rule.evaluate(req)
    assert res.passed is True
    assert "Spend limit check passed" in res.message


def test_spend_limit_above_cap(spend_rule):
    """Above limit: DENY."""
    req = ActionRequest(
        action_id="act-spend-above",
        target="0xcA11bde05977b3631167028862bE2a173976CA11",
        value_wei=ONE_PHRS_WEI + 1,  # 1.0 PHRS + 1 wei
    )
    res = spend_rule.evaluate(req)
    assert res.passed is False
    assert "exceeds per-transaction limit" in res.message


def test_spend_limit_negative_value_denied(spend_rule):
    """Negative native value: DENY."""
    req = ActionRequest(
        action_id="act-spend-neg",
        target="0xcA11bde05977b3631167028862bE2a173976CA11",
        value_wei=-100,
    )
    res = spend_rule.evaluate(req)
    assert res.passed is False
    assert "Invalid or negative native value_wei" in res.message


def test_spend_limit_erc20_transfer_allow(spend_rule):
    """ERC20 transfer of 50.0 USDC (below 100.0 limit): ALLOW."""
    # calldata: selector (0xa9059cbb) + recipient (32 bytes) + amount (50,000,000 raw uint256)
    recipient = "0000000000000000000000001111111254fb6c44bac0bed2854e76f90643097d"
    amount_hex = f"{50000000:064x}"  # 50.000000 USDC
    calldata = f"{TRANSFER_SELECTOR}{recipient}{amount_hex}"

    req = ActionRequest(
        action_id="act-erc20-allow",
        target=USDC_CONTRACT,
        value_wei=0,
        data=calldata,
    )
    res = spend_rule.evaluate(req)
    assert res.passed is True


def test_spend_limit_erc20_transfer_deny(spend_rule):
    """ERC20 transfer of 250.0 USDC (above 100.0 limit): DENY."""
    recipient = "0000000000000000000000001111111254fb6c44bac0bed2854e76f90643097d"
    amount_hex = f"{250000000:064x}"  # 250.000000 USDC
    calldata = f"{TRANSFER_SELECTOR}{recipient}{amount_hex}"

    req = ActionRequest(
        action_id="act-erc20-deny",
        target=USDC_CONTRACT.lower(),
        value_wei=0,
        data=calldata,
    )
    res = spend_rule.evaluate(req)
    assert res.passed is False
    assert "ERC20 USDC transfer amount of 250000000 units (250.0000 USDC) exceeds limit" in res.message


def test_spend_limit_erc20_malformed_calldata(spend_rule):
    """Malformed ERC20 calldata: DENY."""
    req = ActionRequest(
        action_id="act-erc20-malformed",
        target=USDC_CONTRACT,
        value_wei=0,
        data=TRANSFER_SELECTOR + "1234",  # truncated calldata
    )
    res = spend_rule.evaluate(req)
    assert res.passed is False
    assert "Malformed ERC20 USDC calldata" in res.message


def test_spend_limit_cumulative_cap_exceeded(spend_rule):
    """Cumulative spend exceeding 5.0 PHRS: DENY."""
    req = ActionRequest(
        action_id="act-cum-spend",
        target="0xcA11bde05977b3631167028862bE2a173976CA11",
        value_wei=ONE_PHRS_WEI,  # 1.0 PHRS (passes single tx limit)
    )
    # Context indicates 4.5 PHRS already spent
    context = {"cumulative_native_wei": 4500000000000000000}
    res = spend_rule.evaluate(req, context=context)
    assert res.passed is False
    assert "Cumulative native spend of 5500000000000000000 wei exceeds rolling cap" in res.message
