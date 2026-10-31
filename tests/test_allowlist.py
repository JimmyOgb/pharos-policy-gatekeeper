"""Offline unit tests for AllowlistRule in Pharos Policy Gatekeeper."""

import pytest

from policy.rules.allowlist import AllowlistRule
from policy.schema import ActionRequest

MULTICALL3 = "0xcA11bde05977b3631167028862bE2a173976CA11"
USDC = "0xcfC8330f4BCAB529c625D12781b1C19466A9Fc8B"
WPHRS = "0x76A4De34D608AEf6003117565868E079d20c57F9"
TRY_AGGREGATE = "0xbce38bd7"


@pytest.fixture
def allowlist_rule():
    return AllowlistRule(
        rule_id="rule-allowlist-test",
        name="Allowlist Test Rule",
        parameters={
            "allow_unknown_targets": False,
            "allowed_addresses": [
                {"address": MULTICALL3, "name": "MultiCall3"},
                {"address": USDC, "name": "Atlantic USDC"},
                {"address": WPHRS, "name": "Atlantic WPHRS"},
            ],
            "allowed_function_selectors": [
                {"selector": TRY_AGGREGATE, "name": "tryAggregate"},
                {"selector": "0xa9059cbb", "name": "transfer"},
            ],
            "strict_selectors": False,
        },
    )


def test_allowlist_known_contract_allow(allowlist_rule):
    """Listed target: ALLOW."""
    req = ActionRequest(
        action_id="act-allow-known",
        target=MULTICALL3,
        data=f"{TRY_AGGREGATE}00000000",
    )
    res = allowlist_rule.evaluate(req)
    assert res.passed is True
    assert "MultiCall3" in res.message


def test_allowlist_case_insensitive_allow(allowlist_rule):
    """Case-insensitive address normalization: ALLOW."""
    # Pass lowercase version of MultiCall3 address
    req = ActionRequest(
        action_id="act-allow-lower",
        target=MULTICALL3.lower(),
        data="0x",
    )
    res = allowlist_rule.evaluate(req)
    assert res.passed is True


def test_allowlist_unlisted_target_deny(allowlist_rule):
    """Unlisted target: DENY."""
    unlisted_addr = "0x9999999999999999999999999999999999999999"
    req = ActionRequest(
        action_id="act-deny-unlisted",
        target=unlisted_addr,
        data="0x",
    )
    res = allowlist_rule.evaluate(req)
    assert res.passed is False
    assert f"Target address '{unlisted_addr}' is not in authorized allowlist" in res.message


def test_allowlist_invalid_address_format_deny(allowlist_rule):
    """Invalid target format: DENY."""
    for invalid_target in ["not-an-address", "0x1234", "0xZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ", ""]:
        req = ActionRequest(
            action_id="act-deny-invalid-addr",
            target=invalid_target,
            data="0x",
        )
        res = allowlist_rule.evaluate(req)
        assert res.passed is False
        assert "Invalid or malformed target address format" in res.message


def test_allowlist_disallowed_function_selector_deny(allowlist_rule):
    """Disallowed function selector: DENY."""
    disallowed_sel = "0xdeadbeef"
    req = ActionRequest(
        action_id="act-deny-selector",
        target=MULTICALL3,
        data=f"{disallowed_sel}00000000",
    )
    res = allowlist_rule.evaluate(req)
    assert res.passed is False
    assert f"Function selector '{disallowed_sel}' is not authorized" in res.message


def test_allowlist_empty_data_allowed_when_strict_false(allowlist_rule):
    """Pure native transfers (empty calldata) permitted when strict_selectors=False."""
    req = ActionRequest(
        action_id="act-allow-pure-transfer",
        target=WPHRS,
        data="0x",
    )
    res = allowlist_rule.evaluate(req)
    assert res.passed is True
