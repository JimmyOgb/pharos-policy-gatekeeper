---
name: pharos-policy-gatekeeper
description: >
  Deterministic, fail-closed policy enforcement engine and tamper-evident audit ledger
  for autonomous Pharos agents. Sits directly between agent decision logic and execution
  adapters, evaluating proposed actions against configurable spend limits, contract allowlists,
  and authorized UTC time windows. Enforces strict zero-execution on DENY decisions.
version: 0.1.0
requires:
  anyBins:
  - python3
  - python
---

# Pharos Policy Gatekeeper

A SkillEngine-compatible security firewall and decision audit ledger for autonomous agents on the Pharos blockchain (`Chain ID: 688689`). It sits directly in front of an agent's execution adapters, intercepting all proposed transactions or contract calls, evaluating them deterministically against multi-condition security policies, returning explicit `ALLOW` or `DENY` verdicts with the deciding rule attributed, and maintaining a structured, append-only, SHA-256 hash-chained audit log.

## Capability Index

| Capability | Command / Endpoint | Description |
|---|---|---|
| **Evaluate Action Request** | `python cli.py check <request.json> [--policy <policy.yaml>]` | Deterministically evaluates an action against loaded policy rules and returns explicit verdict. |
| **Verify Audit Integrity** | `python cli.py audit verify [--log <audit.jsonl>]` | Validates the unbroken SHA-256 cryptographic hash chain of the append-only audit ledger. |
| **Inspect Audit Log** | `python cli.py audit list [--log <audit.jsonl>]` | Lists historical policy evaluation verdicts with deciding rules, timestamps, and action IDs. |
| **Start Web Dashboard** | `python cli.py serve [--port 8899]` | Launches the interactive visualizer and real-time policy test harness. |
| **Status / Health API** | `GET /api/status` | Reports policy version, active rules, network configuration, and RPC health. |
| **Gate Check API** | `POST /api/check` | REST endpoint accepting an `ActionRequest` and returning a deterministic `Decision`. |
| **Audit Ledger API** | `GET /api/audit` | REST endpoint streaming paginated audit log entries with integrity hashes. |

## Agent Guidelines Block

When an autonomous agent intends to dispatch a transaction or call an on-chain contract on Pharos Atlantic:

1. **Mandatory Pre-Execution Interception**:
   - The agent MUST pass the proposed action to `PolicyGatekeeper.check(request)` or `POST /api/check` before signing, broadcasting, or submitting calldata.
2. **Explicit Verdict Inspection**:
   - If `outcome == "ALLOW"`: The proposed action meets all security constraints. Proceed to execution.
   - If `outcome == "DENY"`: The proposed action violates policy. **ABORT IMMEDIATELY.** Never attempt to circumvent or re-dispatch denied actions.
3. **Fail-Closed Principle**:
   - If the policy file is missing, corrupt, or unparseable, or if an unexpected exception occurs during evaluation, the gatekeeper automatically defaults to `DENY`.
   - Denied actions are **physically prevented** from reaching the execution adapter.
4. **Audit Trail**:
   - Every evaluation creates an immutable, SHA-256 hash-chained entry in the audit ledger recording the decision ID, timestamp, deciding rule, and justification.

## Rule Type Specifications

The engine supports three mandatory rule categories:

### 1. Spend Limit (`spend_limit`)
- **Native PHRS Transfers**: Restricts single-transaction wei values (`max_native_wei`) and cumulative rolling spend (`max_cumulative_native_wei`).
- **ERC20 Token Transfers**: Parses standard `transfer(address,uint256)` and `approve(address,uint256)` calldata for verified tokens (e.g. Atlantic USDC `0xcfC8330f4BCAB529c625D12781b1C19466A9Fc8B`), validating raw amount against token decimals.

### 2. Contract & Address Allowlist (`allowlist`)
- **Target Verification**: Evaluates recipient/contract addresses against an approved whitelist. Unlisted targets are immediately denied (`allow_unknown_targets: false`).
- **Function Selector Restrictions**: Optionally restricts permissible 4-byte EVM function selectors (e.g., `0xbce38bd7` for MultiCall3 `tryAggregate`, `0xa9059cbb` for ERC20 `transfer`).

### 3. Execution Time Window (`time_window`)
- **UTC Time of Day**: Restricts execution to authorized operating hours (e.g., `08:00:00` to `20:00:00` UTC).
- **Authorized Weekdays**: Restricts operations to designated days (e.g., `MONDAY` through `FRIDAY`).
- **Clock Source**: Evaluates timestamp from request metadata or verifies against current Atlantic block timestamp via standard `eth_getBlockByNumber`.

## Pharos RPC Compatibility Statement (November 2026)

Pharos announced that debug and trace methods (`debug_traceTransaction`, `debug_traceBlockByNumber`, `debug_traceBlockByHash`, `debug_traceCall`, `trace_filter`) will be disabled on public RPC endpoints before November 2, 2026.

**Policy Gatekeeper Compatibility:**
- **Zero Dependence on Debug/Trace:** Core policy evaluation is 100% deterministic and offline-first. It does not require RPC access to evaluate spend caps, allowlists, or time windows.
- **Standard JSON-RPC Only:** When live blockchain context is requested (e.g. current block timestamp), the engine strictly uses standard methods: `eth_chainId`, `eth_blockNumber`, `eth_getBlockByNumber`, and `eth_call`.
- **Prohibited Method Rejection:** The engine explicitly blacklists debug and trace RPC methods in `policy/config.py` to prevent accidental calls.
