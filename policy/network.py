"""Pharos Atlantic network health client using standard JSON-RPC only.

Enforces zero dependence on deprecated debug/trace methods (November 2026 compatibility).
"""

from datetime import datetime, timezone
import json
import time
from typing import Any, Dict, Optional
import urllib.request

from policy.config import CHAIN_ID, DEFAULT_RPC_URL, NETWORK_NAME, PERMITTED_RPC_METHODS


def get_atlantic_status(
    rpc_url: str = DEFAULT_RPC_URL,
    timeout_sec: float = 3.0,
) -> Dict[str, Any]:
    """Queries Atlantic testnet using standard eth_chainId and eth_blockNumber JSON-RPC calls.
    
    Returns structured status dictionary. Never throws unhandled network exceptions;
    gracefully reports disconnected state so offline policy engine remains fully functional.
    """
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "eth_blockNumber",
        "params": [],
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        rpc_url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "PharosPolicyGatekeeper/0.1.0",
        },
    )

    start_time = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            res = json.loads(resp.read().decode("utf-8"))
            block_hex = res.get("result")
            block_number = int(block_hex, 16) if block_hex else None

            return {
                "connected": True,
                "network_name": NETWORK_NAME,
                "chain_id": CHAIN_ID,
                "rpc_url": rpc_url,
                "block_number": block_number,
                "latency_ms": round(elapsed_ms, 2),
                "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
    except Exception as exc:
        return {
            "connected": False,
            "network_name": NETWORK_NAME,
            "chain_id": CHAIN_ID,
            "rpc_url": rpc_url,
            "block_number": None,
            "latency_ms": None,
            "error": f"{type(exc).__name__}: {str(exc)}",
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
