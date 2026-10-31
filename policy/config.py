"""Network and system configuration constants for Pharos Policy Gatekeeper.

Enforces zero-dependence on deprecated debug/trace RPC methods (November 2026 compatibility).
"""

from typing import Final, Set

# Pharos Atlantic Testnet Constants
CHAIN_ID: Final[int] = 688689
NETWORK_NAME: Final[str] = "Pharos Atlantic Testnet"
DEFAULT_RPC_URL: Final[str] = "https://atlantic.dplabs-internal.com"

# Verified Infrastructure Contracts on Atlantic Testnet
MULTICALL3_ADDRESS: Final[str] = "0xcA11bde05977b3631167028862bE2a173976CA11"
USDC_ADDRESS: Final[str] = "0xcfC8330f4BCAB529c625D12781b1C19466A9Fc8B"
WPHRS_ADDRESS: Final[str] = "0x76A4De34D608AEf6003117565868E079d20c57F9"

# Prohibited Debug & Trace RPC Methods (Deprecating November 2026)
# Public RPC endpoints on Pharos will reject these calls.
PROHIBITED_RPC_METHODS: Final[Set[str]] = {
    "debug_traceTransaction",
    "debug_traceBlockByNumber",
    "debug_traceBlockByHash",
    "debug_traceCall",
    "trace_filter",
}

# Permitted Standard JSON-RPC Methods for optional block-time or state checks
PERMITTED_RPC_METHODS: Final[Set[str]] = {
    "eth_chainId",
    "eth_blockNumber",
    "eth_getBlockByNumber",
    "eth_call",
}
