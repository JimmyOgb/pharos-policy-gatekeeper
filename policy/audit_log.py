"""Structured, append-only audit logger with SHA-256 cryptographic hash chaining.

Maintains an immutable record of all policy evaluation decisions and provides
tamper-evident verification across sequential decision entries.

Note on Limitations:
A locally stored hash chain is tamper-evident: modifying, reordering, deleting,
or inserting records without breaking the chain requires recomputing all downstream
hashes. However, it cannot prevent an attacker with root/write filesystem permissions
from rewriting the entire ledger and recalculating the chain from scratch.
"""

from datetime import datetime, timezone
import hashlib
import json
import os
from typing import Any, Dict, List, Optional, Tuple

from policy.schema import AuditIntegrity, AuditLogEntry, Decision, Outcome, RuleType

GENESIS_PREVIOUS_HASH = "0" * 64


class AuditLogger:
    """Manages an append-only JSON Lines audit ledger with SHA-256 hash chaining."""

    def __init__(self, log_path: str = "audit.jsonl"):
        self.log_path = log_path
        self._ensure_log_file()

    def _ensure_log_file(self) -> None:
        """Ensures the directory for the log file exists."""
        dirname = os.path.dirname(self.log_path)
        if dirname:
            os.makedirs(dirname, exist_ok=True)

    def get_last_entry(self) -> Optional[AuditLogEntry]:
        """Reads the last entry from the audit log, if any exists."""
        if not os.path.exists(self.log_path) or os.path.getsize(self.log_path) == 0:
            return None

        last_line = ""
        with open(self.log_path, "r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if stripped:
                    last_line = stripped

        if not last_line:
            return None

        try:
            d = json.loads(last_line)
            integ_dict = d.get("integrity", {})
            return AuditLogEntry(
                sequence_number=d["sequence_number"],
                decision_id=d["decision_id"],
                timestamp=d["timestamp"],
                policy_id=d["policy_id"],
                policy_version=d["policy_version"],
                action_request=d["action_request"],
                outcome=Outcome(d["outcome"]),
                deciding_rule_id=d["deciding_rule_id"],
                deciding_rule_type=RuleType(d["deciding_rule_type"]),
                reason=d["reason"],
                evaluations=d["evaluations"],
                integrity=AuditIntegrity(
                    algorithm=integ_dict.get("algorithm", "sha256"),
                    previous_hash=integ_dict.get("previous_hash", ""),
                    entry_hash=integ_dict.get("entry_hash", ""),
                ),
            )
        except Exception:
            return None

    def record(self, decision: Decision) -> AuditLogEntry:
        """Appends a new decision record to the audit ledger with SHA-256 hash chaining."""
        last_entry = self.get_last_entry()
        if last_entry is None:
            sequence_number = 0
            previous_hash = GENESIS_PREVIOUS_HASH
        else:
            sequence_number = last_entry.sequence_number + 1
            previous_hash = last_entry.integrity.entry_hash

        # Extract serializable action request
        action_dict = (
            decision.action_request.to_dict()
            if decision.action_request is not None
            else {}
        )
        evaluations_dict = [e.to_dict() for e in decision.evaluations]

        # Prepare unhashed entry structure
        entry_without_hash = AuditLogEntry(
            sequence_number=sequence_number,
            decision_id=decision.decision_id,
            timestamp=decision.timestamp,
            policy_id=decision.policy_id,
            policy_version=decision.policy_version,
            action_request=action_dict,
            outcome=decision.outcome,
            deciding_rule_id=decision.deciding_rule_id,
            deciding_rule_type=decision.deciding_rule_type,
            reason=decision.reason,
            evaluations=evaluations_dict,
            integrity=AuditIntegrity(
                algorithm="sha256",
                previous_hash=previous_hash,
                entry_hash="",  # Placeholder prior to computation
            ),
        )

        # Compute deterministic entry hash
        payload_bytes = entry_without_hash.canonical_payload_bytes()
        hash_seed = previous_hash.encode("utf-8") + payload_bytes
        entry_hash = hashlib.sha256(hash_seed).hexdigest()

        entry_without_hash.integrity.entry_hash = entry_hash

        # Append to log file
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry_without_hash.to_dict()) + "\n")

        return entry_without_hash

    def verify_integrity(self) -> Tuple[bool, str, int]:
        """Validates the unbroken cryptographic hash chain of the ledger.
        
        Returns:
            Tuple of (is_valid: bool, message: str, entry_count: int)
        """
        if not os.path.exists(self.log_path) or os.path.getsize(self.log_path) == 0:
            return (True, "Ledger is empty (0 entries).", 0)

        expected_seq = 0
        expected_prev_hash = GENESIS_PREVIOUS_HASH
        entry_count = 0

        with open(self.log_path, "r", encoding="utf-8") as f:
            for line_idx, line in enumerate(f, start=1):
                stripped = line.strip()
                if not stripped:
                    continue

                try:
                    data = json.loads(stripped)
                except json.JSONDecodeError as e:
                    return (False, f"Malformed JSON on line {line_idx}: {str(e)}", entry_count)

                seq = data.get("sequence_number")
                if seq != expected_seq:
                    return (
                        False,
                        f"Sequence number mismatch on line {line_idx}: expected {expected_seq}, found {seq}.",
                        entry_count,
                    )

                integ = data.get("integrity", {})
                prev_hash = integ.get("previous_hash")
                stored_hash = integ.get("entry_hash")

                if prev_hash != expected_prev_hash:
                    return (
                        False,
                        f"Hash chain broken on line {line_idx} (sequence {seq}): "
                        f"stored previous_hash '{prev_hash}' does not match expected '{expected_prev_hash}'.",
                        entry_count,
                    )

                # Recompute canonical payload and entry hash
                try:
                    entry_obj = AuditLogEntry(
                        sequence_number=data["sequence_number"],
                        decision_id=data["decision_id"],
                        timestamp=data["timestamp"],
                        policy_id=data["policy_id"],
                        policy_version=data["policy_version"],
                        action_request=data["action_request"],
                        outcome=Outcome(data["outcome"]),
                        deciding_rule_id=data["deciding_rule_id"],
                        deciding_rule_type=RuleType(data["deciding_rule_type"]),
                        reason=data["reason"],
                        evaluations=data["evaluations"],
                        integrity=AuditIntegrity(
                            algorithm=integ.get("algorithm", "sha256"),
                            previous_hash=prev_hash,
                            entry_hash="",
                        ),
                    )
                except Exception as ex:
                    return (
                        False,
                        f"Invalid entry schema on line {line_idx} (sequence {seq}): {str(ex)}",
                        entry_count,
                    )

                payload_bytes = entry_obj.canonical_payload_bytes()
                computed_hash = hashlib.sha256(expected_prev_hash.encode("utf-8") + payload_bytes).hexdigest()

                if computed_hash != stored_hash:
                    return (
                        False,
                        f"Payload tampering detected on line {line_idx} (sequence {seq}): "
                        f"recomputed hash '{computed_hash}' does not match stored '{stored_hash}'.",
                        entry_count,
                    )

                # Advance chain
                expected_seq += 1
                expected_prev_hash = stored_hash
                entry_count += 1

        return (True, f"Ledger integrity verified successfully ({entry_count} entries).", entry_count)
