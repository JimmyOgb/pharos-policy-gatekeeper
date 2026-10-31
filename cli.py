"""Command-line interface for Pharos Policy Gatekeeper.

Provides commands for evaluating actions against policies, inspecting audit logs,
and verifying cryptographic hash-chain integrity.
"""

import argparse
from datetime import datetime, timezone
import json
import os
import sys

from policy.audit_log import AuditLogger
from policy.evaluator import PolicyEvaluator
from policy.gatekeeper import Gatekeeper, PolicyViolationError
from policy.schema import ActionRequest, Outcome


def cmd_check(args: argparse.Namespace) -> int:
    """Evaluates an action request against a policy file."""
    if not os.path.exists(args.request):
        print(f"Error: Action request file not found: {args.request}", file=sys.stderr)
        return 1

    if not os.path.exists(args.policy):
        print(f"Error: Policy configuration file not found: {args.policy}", file=sys.stderr)
        return 1

    with open(args.request, "r", encoding="utf-8") as f:
        req_data = json.load(f)

    request = ActionRequest.from_dict(req_data)
    evaluator = PolicyEvaluator.from_yaml_file(args.policy)
    audit_logger = AuditLogger(args.log) if args.log else None
    gatekeeper = Gatekeeper(evaluator=evaluator, audit_logger=audit_logger)

    decision = gatekeeper.check(request)

    print("=" * 60)
    print("PHAROS POLICY GATEKEEPER — EVALUATION REPORT")
    print("=" * 60)
    print(f"Decision ID:    {decision.decision_id}")
    print(f"Timestamp:      {decision.timestamp}")
    print(f"Policy:         {decision.policy_id} (v{decision.policy_version})")
    print(f"Action ID:      {request.action_id}")
    print(f"Target:         {request.target}")
    print(f"Value:          {request.value_wei} wei")
    print(f"Outcome:        {decision.outcome.value}")
    print(f"Deciding Rule:  {decision.deciding_rule_id} ({decision.deciding_rule_type.value})")
    print(f"Reason:         {decision.reason}")
    print("-" * 60)
    print("Rule Traces:")
    for eval_trace in decision.evaluations:
        status_sym = "[PASS]" if eval_trace.passed else "[FAIL]"
        print(f"  {status_sym} {eval_trace.rule_id} ({eval_trace.rule_type.value}): {eval_trace.message}")
    print("=" * 60)

    if args.json:
        print("\nJSON Output:")
        print(json.dumps(decision.to_dict(), indent=2))

    return 0 if decision.outcome == Outcome.ALLOW else 2


def cmd_audit(args: argparse.Namespace) -> int:
    """Performs audit log inspections and cryptographic integrity verifications."""
    logger = AuditLogger(args.log)

    if args.action == "verify":
        is_valid, msg, count = logger.verify_integrity()
        print("=" * 60)
        print("AUDIT LEDGER INTEGRITY VERIFICATION")
        print("=" * 60)
        print(f"Ledger File:  {args.log}")
        print(f"Total Records:{count}")
        print(f"Status:       {'VALID' if is_valid else 'TAMPERED / INVALID'}")
        print(f"Details:      {msg}")
        print("=" * 60)
        return 0 if is_valid else 1

    elif args.action in ("list", "tail"):
        if not os.path.exists(args.log) or os.path.getsize(args.log) == 0:
            print(f"Audit log '{args.log}' is empty or does not exist.")
            return 0

        entries = []
        with open(args.log, "r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if stripped:
                    try:
                        entries.append(json.loads(stripped))
                    except Exception:
                        pass

        if args.action == "tail":
            entries = entries[-10:]

        print("=" * 70)
        print(f"AUDIT LOG RECORDS ({len(entries)} displayed)")
        print("=" * 70)
        for e in entries:
            seq = e.get("sequence_number")
            dec_id = e.get("decision_id")
            ts = e.get("timestamp")
            out = e.get("outcome")
            rule = e.get("deciding_rule_id")
            prev_h = e.get("integrity", {}).get("previous_hash", "")[:8]
            curr_h = e.get("integrity", {}).get("entry_hash", "")[:8]
            print(f"[{seq:04d}] {ts} | {out:5s} | Rule: {rule} | Hash: {prev_h}... -> {curr_h}...")
        print("=" * 70)
        return 0

    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    """Launches the FastAPI backend and interactive web dashboard."""
    import uvicorn
    print("=" * 60)
    print("PHAROS POLICY GATEKEEPER — DASHBOARD SERVER")
    print("=" * 60)
    print(f"Hosting on:    http://{args.host}:{args.port}")
    print(f"Policy file:   examples/policy.yaml")
    print(f"Audit log:     audit.jsonl")
    print("=" * 60)
    uvicorn.run("policy.server:app", host=args.host, port=args.port, reload=False)
    return 0


def parse_args():
    parser = argparse.ArgumentParser(
        prog="pharos-policy-gatekeeper",
        description="Deterministic, fail-closed policy enforcement engine for Pharos agents.",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # check subcommand
    check_parser = subparsers.add_parser("check", help="Evaluate an action request against a policy")
    check_parser.add_argument("request", help="Path to action request JSON")
    check_parser.add_argument("--policy", default="examples/policy.yaml", help="Path to policy YAML/JSON")
    check_parser.add_argument("--log", default="audit.jsonl", help="Path to append audit ledger")
    check_parser.add_argument("--json", action="store_true", help="Print raw JSON decision")

    # audit subcommand
    audit_parser = subparsers.add_parser("audit", help="Inspect or verify the decision audit log")
    audit_parser.add_argument("action", choices=["verify", "list", "tail"], help="Audit action to perform")
    audit_parser.add_argument("--log", default="audit.jsonl", help="Path to audit log file")

    # serve subcommand
    serve_parser = subparsers.add_parser("serve", help="Launch FastAPI server and dashboard")
    serve_parser.add_argument("--host", default="127.0.0.1", help="Host interface to bind")
    serve_parser.add_argument("--port", type=int, default=8899, help="Port to listen on")

    return parser.parse_args()


def main():
    args = parse_args()
    if not args.command:
        print("Pharos Policy Gatekeeper CLI (v0.1.0)")
        print("Use --help to view available commands: 'check', 'audit', 'serve'.")
        sys.exit(0)

    if args.command == "check":
        sys.exit(cmd_check(args))
    elif args.command == "audit":
        sys.exit(cmd_audit(args))
    elif args.command == "serve":
        sys.exit(cmd_serve(args))


if __name__ == "__main__":
    main()
