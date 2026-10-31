# Contributing to Pharos Policy Gatekeeper

Thank you for your interest in contributing to `pharos-policy-gatekeeper`!

## Code of Conduct & Core Invariants

1. **Deterministic Rule Evaluation**:
   - The policy engine must remain 100% deterministic and offline-first.
   - Monetary values must use integer/decimal arithmetic; floating-point comparisons are strictly prohibited.
2. **Fail-Closed Boundary Invariant**:
   - Any unhandled exception, missing policy, or corrupt configuration must fail closed to `DENY`.
   - Denied actions must never be passed to an execution adapter. No flags or AI recommendations can override a `DENY`.
3. **Cryptographic Audit Integrity**:
   - All decisions (both `ALLOW` and `DENY`) must be permanently recorded with unbroken SHA-256 hash chaining (`previous_hash` -> `entry_hash`).
   - Tamper-evident verification must detect any modification, deletion, reordering, or insertion.
4. **Pharos RPC Compatibility (November 2026)**:
   - Deprecated debug and trace RPC methods (`debug_traceTransaction`, `debug_traceBlockByNumber`, `debug_traceBlockByHash`, `debug_traceCall`, `trace_filter`) are strictly prohibited.
   - Only standard JSON-RPC methods (`eth_blockNumber`, `eth_chainId`) are permitted for optional network health checks.
5. **$0-First Policy**:
   - The engine must never require funded wallets, gas fees, or paid external APIs to evaluate policies or run tests.

## Development & Testing Workflow

1. Install dependencies:
   ```bash
   pip install pyyaml fastapi uvicorn pydantic pytest
   ```
2. Run test suite:
   ```bash
   python -m pytest tests/ -v
   ```
3. Run CLI:
   ```bash
   python cli.py check examples/requests_allow.json
   python cli.py audit verify
   ```
4. Run Web Dashboard:
   ```bash
   python cli.py serve --port 8899
   ```

## Pull Request Guidelines

- Ensure all 46 automated tests pass before submitting PRs.
- Preserve backward compatibility for existing policy schemas.
- Do not introduce dependencies on prohibited debug/trace RPC calls.
