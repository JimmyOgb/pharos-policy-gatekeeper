"""FastAPI backend server for Pharos Policy Gatekeeper.

Provides REST endpoints for deterministic policy checking, audit log inspection,
cryptographic ledger verification, and separate Atlantic network status reporting.
"""

from datetime import datetime, timezone
import json
import os
from typing import Any, Dict, List, Optional

from fastapi import Body, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from policy.audit_log import AuditLogger
from policy.config import CHAIN_ID, DEFAULT_RPC_URL, MULTICALL3_ADDRESS, NETWORK_NAME, USDC_ADDRESS, WPHRS_ADDRESS
from policy.evaluator import PolicyEvaluator
from policy.gatekeeper import Gatekeeper
from policy.network import get_atlantic_status
from policy.schema import ActionRequest, Decision, Outcome

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DEFAULT_POLICY_PATH = os.path.join(BASE_DIR, "examples", "policy.yaml")
DEFAULT_LOG_PATH = os.path.join(BASE_DIR, "audit.jsonl")
STATIC_DIR = os.path.join(BASE_DIR, "web")

# Shared singletons
evaluator = PolicyEvaluator.from_yaml_file(DEFAULT_POLICY_PATH)
audit_logger = AuditLogger(DEFAULT_LOG_PATH)
gatekeeper = Gatekeeper(evaluator=evaluator, audit_logger=audit_logger)

app = FastAPI(
    title="Pharos Policy Gatekeeper API",
    description="Deterministic fail-closed agent security firewall and audit ledger on Pharos Atlantic",
    version="0.1.0",
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic schemas for request validation
class ActionRequestDTO(BaseModel):
    action_id: str = Field(..., description="Unique identifier for the action request")
    target: str = Field(..., description="EVM target address (20 bytes hex)")
    action_type: str = Field(default="evm_call", description="Action type ('evm_call' or 'evm_transfer')")
    sender: Optional[str] = Field(default=None, description="Initiator address")
    value_wei: int = Field(default=0, ge=0, description="Native token value in wei")
    data: str = Field(default="0x", description="Hex-encoded calldata")
    timestamp: Optional[int] = Field(default=None, description="Unix epoch seconds timestamp")
    description: str = Field(default="", description="Human-readable description of action intent")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary execution context metadata")


@app.get("/api/status")
async def get_status(check_network: bool = Query(default=True)) -> Dict[str, Any]:
    """Reports backend health, active policy metadata, and Atlantic network status separately."""
    rules_summary = [
        {
            "id": r.rule_id,
            "name": r.name,
            "type": r.rule_type.value,
            "enabled": r.enabled,
        }
        for r in evaluator.rules
    ]

    # Audit summary
    last_entry = audit_logger.get_last_entry()
    total_records = last_entry.sequence_number + 1 if last_entry else 0
    last_hash = last_entry.integrity.entry_hash if last_entry else None

    # Optional network status check
    network_info = get_atlantic_status() if check_network else {"connected": False, "skipped": True}

    return {
        "backend_status": "healthy",
        "service": "Pharos Policy Gatekeeper",
        "version": "0.1.0",
        "policy": {
            "policy_id": evaluator.policy_id,
            "version": evaluator.version,
            "name": evaluator.name,
            "rule_count": len(evaluator.rules),
            "rules": rules_summary,
        },
        "audit_ledger": {
            "log_file": os.path.basename(DEFAULT_LOG_PATH),
            "total_records": total_records,
            "last_entry_hash": last_hash,
        },
        "network": network_info,
        "contracts": {
            "multicall3": MULTICALL3_ADDRESS,
            "usdc": USDC_ADDRESS,
            "wphrs": WPHRS_ADDRESS,
        },
        "server_time_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


@app.post("/api/check")
async def check_action(request_dto: ActionRequestDTO) -> Dict[str, Any]:
    """Deterministically evaluates an ActionRequest against the active policy.
    
    Returns ALLOW or DENY with deciding rule attribution and records decision in audit log.
    Never broadcasts or executes real transactions (honest execution boundary).
    """
    request = ActionRequest(
        action_id=request_dto.action_id,
        target=request_dto.target,
        action_type=request_dto.action_type,
        sender=request_dto.sender,
        value_wei=request_dto.value_wei,
        data=request_dto.data,
        timestamp=request_dto.timestamp,
        description=request_dto.description,
        metadata=request_dto.metadata,
    )

    decision = gatekeeper.check(request)

    response_data = decision.to_dict()
    # Explicit honest boundary metadata
    response_data["execution_status"] = "NOT EXECUTED"
    response_data["execution_note"] = (
        "Policy Gatekeeper is an evaluation and boundary enforcement firewall. "
        "No real blockchain transactions were broadcast."
    )

    return response_data


@app.get("/api/audit")
async def get_audit_records(
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    tail: bool = Query(default=False),
) -> Dict[str, Any]:
    """Retrieves structured entries from the append-only audit ledger."""
    if not os.path.exists(DEFAULT_LOG_PATH) or os.path.getsize(DEFAULT_LOG_PATH) == 0:
        return {"total": 0, "entries": [], "limit": limit, "offset": offset}

    all_entries: List[Dict[str, Any]] = []
    with open(DEFAULT_LOG_PATH, "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if stripped:
                try:
                    all_entries.append(json.loads(stripped))
                except Exception:
                    pass

    total = len(all_entries)

    if tail:
        sliced = all_entries[-limit:]
    else:
        sliced = all_entries[offset : offset + limit]

    return {
        "total": total,
        "count": len(sliced),
        "limit": limit,
        "offset": offset,
        "entries": sliced,
    }


@app.get("/api/verify")
async def verify_audit_ledger() -> Dict[str, Any]:
    """Runs cryptographic SHA-256 hash-chain verification across all audit records."""
    is_valid, msg, count = audit_logger.verify_integrity()
    return {
        "is_valid": is_valid,
        "status": "VALID" if is_valid else "TAMPERED",
        "message": msg,
        "total_records": count,
        "algorithm": "sha256",
        "verified_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


# Mount static dashboard frontend
if os.path.exists(STATIC_DIR):
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
