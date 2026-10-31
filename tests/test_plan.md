# Pharos Policy Gatekeeper — Comprehensive Test Plan

**Document Version:** 1.0.0  
**Target:** Task 11 — Policy Gatekeeper  
**Network:** Pharos Atlantic Testnet (`Chain ID: 688689`)  

---

## 1. Test Philosophy & Invariants

The test suite enforces three fundamental invariants:
1. **Determinism:** Given identical policy configuration and identical action request, the engine MUST produce the exact same outcome, deciding rule, and reason every single time.
2. **Fail-Closed Execution:** Any missing, invalid, corrupt, or unhandled condition MUST resolve to `DENY`. Under no circumstances may an action proceed to an execution adapter upon evaluation error.
3. **Audit Immutability:** Every decision (both `ALLOW` and `DENY`) must be permanently recorded with unbroken cryptographic hash chaining (`previous_hash` -> `entry_hash`).

---

## 2. Test Matrix Overview

| Test Module | Coverage Scope | Target Invariant | Type |
|---|---|---|:---:|
| `test_spend_limit.py` | Native PHRS & ERC20 spend thresholds | Per-tx limits, cumulative caps, token decimals | Unit (Offline) |
| `test_allowlist.py` | Target addresses, contracts & function selectors | Whitelist checks, case-insensitive checksums | Unit (Offline) |
| `test_time_window.py` | Allowed UTC windows, days of week, epoch bounds | Time-of-day bounds, weekday enforcement | Unit (Offline) |
| `test_fail_closed.py` | Boundary interception, error handling, missing policies | Physical separation of eval and execution | Security (Offline) |
| `test_audit_log.py` | Append-only logging, SHA-256 hash chaining, tampering | Tamper detection, sequence integrity | Unit (Offline) |
| `test_live_rpc.py` | Atlantic node block timestamps & contract addresses | Read-only state checks (standard RPC only) | Integration (Live) |

---

## 3. Detailed Test Specifications

### Module A: Spend Limit (`test_spend_limit.py`)
- **TC-SPEND-01 (ALLOW):** Native PHRS value of 0.5 PHRS evaluated against 1.0 PHRS limit -> `ALLOW`.
- **TC-SPEND-02 (DENY):** Native PHRS value of 1.5 PHRS evaluated against 1.0 PHRS limit -> `DENY` (`rule-spend-limit-01`).
- **TC-SPEND-03 (ALLOW):** ERC20 USDC transfer of 50.0 USDC (50,000,000 units) against 100.0 limit -> `ALLOW`.
- **TC-SPEND-04 (DENY):** ERC20 USDC transfer of 250.0 USDC (250,000,000 units) against 100.0 limit -> `DENY`.
- **TC-SPEND-05 (DENY):** Cumulative spend across rolling 24h window exceeding 5.0 PHRS cap -> `DENY`.

### Module B: Target & Selector Allowlist (`test_allowlist.py`)
- **TC-ALLOW-01 (ALLOW):** Call to allowlisted MultiCall3 (`0xcA11bde05977b3631167028862bE2a173976CA11`) -> `ALLOW`.
- **TC-ALLOW-02 (DENY):** Call to non-allowlisted contract address (`0x9999...9999`) -> `DENY` (`rule-allowlist-02`).
- **TC-ALLOW-03 (ALLOW):** Allowed function selector `0xbce38bd7` (`tryAggregate`) on allowlisted contract -> `ALLOW`.
- **TC-ALLOW-04 (DENY):** Disallowed function selector (e.g. `0xdeadbeef`) on allowlisted contract -> `DENY`.
- **TC-ALLOW-05 (ALLOW):** EIP-55 mixed-case checksum normalization (lowercase input matches checksummed rule) -> `ALLOW`.

### Module C: Time Window (`test_time_window.py`)
- **TC-TIME-01 (ALLOW):** Action timestamped at 14:30 UTC on Wednesday (within 08:00-20:00 UTC window) -> `ALLOW`.
- **TC-TIME-02 (DENY):** Action timestamped at 03:15 UTC on Wednesday (outside window) -> `DENY` (`rule-time-window-03`).
- **TC-TIME-03 (DENY):** Action timestamped at 12:00 UTC on Sunday (weekend outside allowed weekdays) -> `DENY`.
- **TC-TIME-04 (ALLOW):** Boundary exact match at 08:00:00 UTC -> `ALLOW`.
- **TC-TIME-05 (ALLOW):** Boundary exact match at 20:00:00 UTC -> `ALLOW`.

### Module D: Fail-Closed & Boundary Security (`test_fail_closed.py`)
- **TC-FAIL-01 (DENY):** Evaluation with empty policy file or missing rule definitions -> `DENY`.
- **TC-FAIL-02 (DENY):** Evaluation with malformed/invalid JSON/YAML schema -> `DENY`.
- **TC-FAIL-03 (DENY):** Unknown action type (e.g., `"unknown_cloud_exec"`) -> `DENY`.
- **TC-FAIL-04 (DENY):** Simulated internal evaluator exception -> `DENY` (never raises unhandled exception to execution adapter).
- **TC-FAIL-05 (SECURITY):** Execution adapter mock called through `Gatekeeper.execute_safely`:
  - When `outcome == DENY`: execution callback is verified to have NEVER been called (`call_count == 0`).
  - When `outcome == ALLOW`: execution callback called exactly once (`call_count == 1`).

### Module E: Audit Log Integrity (`test_audit_log.py`)
- **TC-AUDIT-01 (INTEGRITY):** Log 10 consecutive decisions, verify genesis `previous_hash` (64 zeros) and continuous hash chain.
- **TC-AUDIT-02 (TAMPER):** Deliberately alter 1 character in a past log line, run `verify_integrity()`, assert tampering is immediately detected.
- **TC-AUDIT-03 (APPEND):** Verify file is strictly appended (new entries do not rewrite prior entries).
- **TC-AUDIT-04 (METADATA):** Verify all mandatory fields are present (decision_id, timestamp, rule_id, rule_type, reason).

### Module F: Multi-Rule Interaction (`test_multi_rule.py`)
- **TC-MULTI-01:** Request failing both Spend Limit and Allowlist -> returns first failing rule explicitly with detailed evaluation trace.
- **TC-MULTI-02:** Request passing Spend Limit and Allowlist but failing Time Window -> returns Time Window DENY.
