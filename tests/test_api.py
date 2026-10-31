"""Integration tests for Pharos Policy Gatekeeper FastAPI backend and REST endpoints."""

import os
import pytest
from fastapi.testclient import TestClient

from policy.server import app
from policy.config import CHAIN_ID, MULTICALL3_ADDRESS, USDC_ADDRESS, WPHRS_ADDRESS

client = TestClient(app)

MULTICALL3 = "0xcA11bde05977b3631167028862bE2a173976CA11"
WED_14_UTC = 1793800800  # Wednesday 14:00 UTC
WED_03_UTC = 1793761200  # Wednesday 03:00 UTC (outside 08:00-20:00)


def test_api_status_endpoint():
    """GET /api/status returns healthy backend, policy metadata, and separate network status."""
    response = client.get("/api/status?check_network=false")
    assert response.status_code == 200
    data = response.json()

    assert data["backend_status"] == "healthy"
    assert data["service"] == "Pharos Policy Gatekeeper"
    assert data["policy"]["policy_id"] == "pharos-atlantic-guardian-v1"
    assert data["policy"]["rule_count"] >= 3
    assert "audit_ledger" in data
    assert data["contracts"]["multicall3"] == MULTICALL3_ADDRESS


def test_api_check_allow_scenario():
    """POST /api/check evaluates valid request and returns ALLOW decision."""
    payload = {
        "action_id": "api-allow-001",
        "action_type": "evm_call",
        "target": MULTICALL3,
        "value_wei": 0,
        "data": "0xbce38bd700000000",
        "timestamp": WED_14_UTC,
        "description": "MultiCall3 read-only call during Wednesday business hours",
    }
    response = client.post("/api/check", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["outcome"] == "ALLOW"
    assert data["deciding_rule_id"] == "all_rules_passed"
    assert data["execution_status"] == "NOT EXECUTED"
    assert "No real blockchain transactions were broadcast" in data["execution_note"]
    assert len(data["evaluations"]) == 3
    assert all(e["passed"] is True for e in data["evaluations"])


def test_api_check_deny_spend_scenario():
    """POST /api/check returns DENY when spend limit is exceeded."""
    payload = {
        "action_id": "api-deny-spend-002",
        "action_type": "evm_call",
        "target": WPHRS_ADDRESS,
        "value_wei": 5000000000000000000,  # 5.0 PHRS (exceeds 1.0 limit)
        "data": "0xd0e30db0",
        "timestamp": WED_14_UTC,
        "description": "Deposit exceeding per-transaction spend limit",
    }
    response = client.post("/api/check", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["outcome"] == "DENY"
    assert data["deciding_rule_id"] == "rule-spend-limit-01"
    assert data["deciding_rule_type"] == "spend_limit"
    assert "exceeds per-transaction limit" in data["reason"]
    assert data["execution_status"] == "NOT EXECUTED"


def test_api_check_deny_allowlist_scenario():
    """POST /api/check returns DENY when target is not allowlisted."""
    payload = {
        "action_id": "api-deny-allowlist-003",
        "action_type": "evm_call",
        "target": "0x9999999999999999999999999999999999999999",
        "value_wei": 0,
        "data": "0x",
        "timestamp": WED_14_UTC,
        "description": "Call to unverified target",
    }
    response = client.post("/api/check", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["outcome"] == "DENY"
    assert data["deciding_rule_id"] == "rule-allowlist-02"
    assert data["deciding_rule_type"] == "allowlist"
    assert "not in authorized allowlist" in data["reason"]
    assert data["execution_status"] == "NOT EXECUTED"


def test_api_check_deny_timewindow_scenario():
    """POST /api/check returns DENY when execution time is outside authorized window."""
    payload = {
        "action_id": "api-deny-time-004",
        "action_type": "evm_call",
        "target": MULTICALL3,
        "value_wei": 0,
        "data": "0xbce38bd7",
        "timestamp": WED_03_UTC,  # 03:00 UTC (outside 08:00-20:00)
        "description": "Call outside business hours",
    }
    response = client.post("/api/check", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["outcome"] == "DENY"
    assert data["deciding_rule_id"] == "rule-time-window-03"
    assert data["deciding_rule_type"] == "time_window"
    assert "outside authorized operating window" in data["reason"]
    assert data["execution_status"] == "NOT EXECUTED"


def test_api_check_malformed_input_rejected():
    """POST /api/check validates required fields and rejects invalid types."""
    # 1. Missing target
    bad_payload_1 = {
        "action_id": "bad-01",
        "value_wei": 0,
    }
    resp1 = client.post("/api/check", json=bad_payload_1)
    assert resp1.status_code == 422

    # 2. Negative value_wei
    bad_payload_2 = {
        "action_id": "bad-02",
        "target": MULTICALL3,
        "value_wei": -50,
    }
    resp2 = client.post("/api/check", json=bad_payload_2)
    assert resp2.status_code == 422


def test_api_audit_records_endpoint():
    """GET /api/audit retrieves structured records from the append-only ledger."""
    response = client.get("/api/audit?limit=10&tail=true")
    assert response.status_code == 200
    data = response.json()

    assert "total" in data
    assert "entries" in data
    assert isinstance(data["entries"], list)
    if data["total"] > 0:
        entry = data["entries"][-1]
        assert "sequence_number" in entry
        assert "integrity" in entry
        assert "entry_hash" in entry["integrity"]


def test_api_verify_integrity_endpoint():
    """GET /api/verify performs cryptographic SHA-256 hash-chain verification."""
    response = client.get("/api/verify")
    assert response.status_code == 200
    data = response.json()

    assert "is_valid" in data
    assert data["is_valid"] is True
    assert data["status"] == "VALID"
    assert data["algorithm"] == "sha256"
    assert "total_records" in data


def test_static_dashboard_served():
    """GET / returns the HTML5 dashboard interface."""
    response = client.get("/")
    assert response.status_code == 200
    assert "Pharos Policy Gatekeeper" in response.text
    assert "action-form" in response.text
