"""Offline unit and security tests for AuditLogger with SHA-256 Hash Chaining."""

import json
import os
import pytest

from policy.audit_log import AuditLogger, GENESIS_PREVIOUS_HASH
from policy.schema import ActionRequest, Decision, Outcome, RuleType


@pytest.fixture
def temp_audit_log(tmp_path):
    log_file = tmp_path / "test_audit.jsonl"
    return str(log_file)


def create_sample_decision(decision_id: str, outcome: Outcome, value_wei: int = 100) -> Decision:
    req = ActionRequest(
        action_id=f"act-{decision_id}",
        target="0xcA11bde05977b3631167028862bE2a173976CA11",
        value_wei=value_wei,
    )
    return Decision(
        decision_id=decision_id,
        outcome=outcome,
        deciding_rule_id="rule-test",
        deciding_rule_type=RuleType.SPEND_LIMIT,
        reason=f"Evaluation test for {decision_id}",
        policy_id="test-policy-v1",
        policy_version="1.0.0",
        timestamp="2026-11-04T12:00:00Z",
        evaluations=[],
        action_request=req,
    )


def test_audit_log_hash_chain_creation(temp_audit_log):
    """Verifies sequence numbers and continuous SHA-256 hash chaining across entries."""
    logger = AuditLogger(temp_audit_log)

    dec1 = create_sample_decision("dec-001", Outcome.ALLOW, 100)
    dec2 = create_sample_decision("dec-002", Outcome.DENY, 500)
    dec3 = create_sample_decision("dec-003", Outcome.ALLOW, 200)

    e1 = logger.record(dec1)
    e2 = logger.record(dec2)
    e3 = logger.record(dec3)

    assert e1.sequence_number == 0
    assert e1.integrity.previous_hash == GENESIS_PREVIOUS_HASH
    assert len(e1.integrity.entry_hash) == 64

    assert e2.sequence_number == 1
    assert e2.integrity.previous_hash == e1.integrity.entry_hash
    assert len(e2.integrity.entry_hash) == 64

    assert e3.sequence_number == 2
    assert e3.integrity.previous_hash == e2.integrity.entry_hash
    assert len(e3.integrity.entry_hash) == 64

    # Verify overall ledger integrity
    is_valid, msg, count = logger.verify_integrity()
    assert is_valid is True
    assert count == 3
    assert "verified successfully" in msg


def test_audit_log_tamper_detection_modified_payload(temp_audit_log):
    """Tampering with a past payload (e.g. changing DENY to ALLOW) is immediately detected."""
    logger = AuditLogger(temp_audit_log)
    logger.record(create_sample_decision("dec-001", Outcome.ALLOW))
    logger.record(create_sample_decision("dec-002", Outcome.DENY))
    logger.record(create_sample_decision("dec-003", Outcome.ALLOW))

    # Tamper with entry 1: change outcome from DENY to ALLOW in file
    with open(temp_audit_log, "r", encoding="utf-8") as f:
        lines = [json.loads(line) for line in f]

    lines[1]["outcome"] = "ALLOW"  # Fraudulent change

    with open(temp_audit_log, "w", encoding="utf-8") as f:
        for item in lines:
            f.write(json.dumps(item) + "\n")

    is_valid, msg, count = logger.verify_integrity()
    assert is_valid is False
    assert "Payload tampering detected on line 2" in msg


def test_audit_log_tamper_detection_deleted_entry(temp_audit_log):
    """Deleting an entry from the ledger is detected via sequence number mismatch."""
    logger = AuditLogger(temp_audit_log)
    logger.record(create_sample_decision("dec-001", Outcome.ALLOW))
    logger.record(create_sample_decision("dec-002", Outcome.DENY))
    logger.record(create_sample_decision("dec-003", Outcome.ALLOW))

    # Delete entry 1 (sequence 1)
    with open(temp_audit_log, "r", encoding="utf-8") as f:
        lines = [json.loads(line) for line in f]

    del lines[1]

    with open(temp_audit_log, "w", encoding="utf-8") as f:
        for item in lines:
            f.write(json.dumps(item) + "\n")

    is_valid, msg, count = logger.verify_integrity()
    assert is_valid is False
    assert "Sequence number mismatch on line 2" in msg


def test_audit_log_tamper_detection_reordered_entries(temp_audit_log):
    """Reordering entries is detected immediately."""
    logger = AuditLogger(temp_audit_log)
    logger.record(create_sample_decision("dec-001", Outcome.ALLOW))
    logger.record(create_sample_decision("dec-002", Outcome.DENY))

    with open(temp_audit_log, "r", encoding="utf-8") as f:
        lines = [json.loads(line) for line in f]

    # Swap entries 0 and 1
    lines[0], lines[1] = lines[1], lines[0]

    with open(temp_audit_log, "w", encoding="utf-8") as f:
        for item in lines:
            f.write(json.dumps(item) + "\n")

    is_valid, msg, count = logger.verify_integrity()
    assert is_valid is False
    assert "Sequence number mismatch on line 1" in msg or "Hash chain broken" in msg


def test_audit_log_tamper_detection_inserted_entry(temp_audit_log):
    """Inserting a fraudulent entry into the ledger is detected."""
    logger = AuditLogger(temp_audit_log)
    logger.record(create_sample_decision("dec-001", Outcome.ALLOW))
    logger.record(create_sample_decision("dec-002", Outcome.DENY))

    with open(temp_audit_log, "r", encoding="utf-8") as f:
        lines = [json.loads(line) for line in f]

    # Insert fake record with forged sequence 1
    fake_record = dict(lines[1])
    fake_record["decision_id"] = "dec-fake"
    lines.insert(1, fake_record)

    with open(temp_audit_log, "w", encoding="utf-8") as f:
        for item in lines:
            f.write(json.dumps(item) + "\n")

    is_valid, msg, count = logger.verify_integrity()
    assert is_valid is False
    assert any(phrase in msg for phrase in ["Sequence number mismatch", "Hash chain broken", "Payload tampering detected"])


def test_audit_log_tamper_detection_broken_previous_hash(temp_audit_log):
    """Breaking the previous_hash link is detected."""
    logger = AuditLogger(temp_audit_log)
    logger.record(create_sample_decision("dec-001", Outcome.ALLOW))
    logger.record(create_sample_decision("dec-002", Outcome.DENY))

    with open(temp_audit_log, "r", encoding="utf-8") as f:
        lines = [json.loads(line) for line in f]

    lines[1]["integrity"]["previous_hash"] = "f" * 64

    with open(temp_audit_log, "w", encoding="utf-8") as f:
        for item in lines:
            f.write(json.dumps(item) + "\n")

    is_valid, msg, count = logger.verify_integrity()
    assert is_valid is False
    assert "Hash chain broken on line 2" in msg
