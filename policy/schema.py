"""Core data models and type definitions for Pharos Policy Gatekeeper.

Deterministic data structures for action requests, policy definitions,
rule evaluation traces, decisions, and audit entries.
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
import json
from typing import Any, Dict, List, Optional, Union
import uuid


class Outcome(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"


class RuleType(str, Enum):
    SPEND_LIMIT = "spend_limit"
    ALLOWLIST = "allowlist"
    TIME_WINDOW = "time_window"
    FAIL_CLOSED_DEFAULT = "fail_closed_default"
    SCHEMA_VALIDATION = "schema_validation"


@dataclass
class ActionRequest:
    """Represents an agent action proposed for gatekeeping."""
    action_id: str
    target: str
    action_type: str = "evm_call"
    sender: Optional[str] = None
    value_wei: int = 0
    data: str = "0x"
    timestamp: Optional[int] = None
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        # Normalize target
        if self.target:
            self.target = str(self.target).strip()
        # Normalize value_wei to int
        if isinstance(self.value_wei, str):
            try:
                self.value_wei = int(self.value_wei)
            except ValueError:
                self.value_wei = -1  # Marks invalid value for fail-closed handling
        elif not isinstance(self.value_wei, int):
            self.value_wei = -1
        # Normalize data
        if not self.data:
            self.data = "0x"
        elif not self.data.startswith("0x"):
            self.data = "0x" + self.data

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_id": self.action_id,
            "target": self.target,
            "action_type": self.action_type,
            "sender": self.sender,
            "value_wei": self.value_wei,
            "data": self.data,
            "timestamp": self.timestamp,
            "description": self.description,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ActionRequest":
        return cls(
            action_id=data.get("action_id", ""),
            target=data.get("target", ""),
            action_type=data.get("action_type", "evm_call"),
            sender=data.get("sender"),
            value_wei=data.get("value_wei", 0),
            data=data.get("data", "0x"),
            timestamp=data.get("timestamp"),
            description=data.get("description", ""),
            metadata=data.get("metadata", {}),
        )


@dataclass
class RuleEvaluationResult:
    """Outcome of evaluating a single rule against an action request."""
    rule_id: str
    rule_type: RuleType
    passed: bool
    message: str
    execution_time_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "rule_type": self.rule_type.value if isinstance(self.rule_type, RuleType) else str(self.rule_type),
            "passed": self.passed,
            "message": self.message,
            "execution_time_ms": round(self.execution_time_ms, 3),
        }


@dataclass
class Decision:
    """Deterministic final verdict produced by the policy evaluator."""
    decision_id: str
    outcome: Outcome
    deciding_rule_id: str
    deciding_rule_type: RuleType
    reason: str
    policy_id: str
    policy_version: str
    timestamp: str  # ISO-8601 UTC string
    evaluations: List[RuleEvaluationResult] = field(default_factory=list)
    action_request: Optional[ActionRequest] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "outcome": self.outcome.value if isinstance(self.outcome, Outcome) else str(self.outcome),
            "deciding_rule_id": self.deciding_rule_id,
            "deciding_rule_type": self.deciding_rule_type.value if isinstance(self.deciding_rule_type, RuleType) else str(self.deciding_rule_type),
            "reason": self.reason,
            "policy_id": self.policy_id,
            "policy_version": self.policy_version,
            "timestamp": self.timestamp,
            "evaluations": [e.to_dict() for e in self.evaluations],
            "action_request": self.action_request.to_dict() if self.action_request else None,
        }


@dataclass
class AuditIntegrity:
    """Cryptographic hash-chaining verification metadata."""
    algorithm: str
    previous_hash: str
    entry_hash: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "algorithm": self.algorithm,
            "previous_hash": self.previous_hash,
            "entry_hash": self.entry_hash,
        }


@dataclass
class AuditLogEntry:
    """Structured, immutable audit record with SHA-256 hash chaining."""
    sequence_number: int
    decision_id: str
    timestamp: str
    policy_id: str
    policy_version: str
    action_request: Dict[str, Any]
    outcome: Outcome
    deciding_rule_id: str
    deciding_rule_type: RuleType
    reason: str
    evaluations: List[Dict[str, Any]]
    integrity: AuditIntegrity

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sequence_number": self.sequence_number,
            "decision_id": self.decision_id,
            "timestamp": self.timestamp,
            "policy_id": self.policy_id,
            "policy_version": self.policy_version,
            "action_request": self.action_request,
            "outcome": self.outcome.value if isinstance(self.outcome, Outcome) else str(self.outcome),
            "deciding_rule_id": self.deciding_rule_id,
            "deciding_rule_type": self.deciding_rule_type.value if isinstance(self.deciding_rule_type, RuleType) else str(self.deciding_rule_type),
            "reason": self.reason,
            "evaluations": self.evaluations,
            "integrity": self.integrity.to_dict(),
        }

    def canonical_payload_bytes(self) -> bytes:
        """Serializes the core record fields into a deterministic, canonical JSON representation."""
        payload = {
            "sequence_number": self.sequence_number,
            "decision_id": self.decision_id,
            "timestamp": self.timestamp,
            "policy_id": self.policy_id,
            "policy_version": self.policy_version,
            "action_request": self.action_request,
            "outcome": self.outcome.value if isinstance(self.outcome, Outcome) else str(self.outcome),
            "deciding_rule_id": self.deciding_rule_id,
            "deciding_rule_type": self.deciding_rule_type.value if isinstance(self.deciding_rule_type, RuleType) else str(self.deciding_rule_type),
            "reason": self.reason,
            "evaluations": self.evaluations,
        }
        # Sort keys and use compact separators to ensure deterministic serialization
        return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
