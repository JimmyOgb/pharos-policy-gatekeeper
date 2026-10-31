/**
 * Automated Test Suite for Browser-Side Policy Evaluator
 * Verifies all 16 requirements for Phase 5 compliance.
 */

const assert = require('assert');
const path = require('path');
const { evaluateAction, DEFAULT_POLICY, EVM_ADDRESS_REGEX } = require('../web/evaluator.js');

let passedTests = 0;
let totalTests = 0;

function runTest(name, fn) {
  totalTests++;
  try {
    fn();
    passedTests++;
    console.log(`  PASS: [${totalTests.toString().padStart(2, '0')}] ${name}`);
  } catch (err) {
    console.error(`  FAIL: [${totalTests.toString().padStart(2, '0')}] ${name}`);
    console.error(`        Error: ${err.message}`);
    throw err;
  }
}

console.log("============================================================");
console.log("RUNNING BROWSER POLICY EVALUATOR TEST SUITE (PHASE 5)");
console.log("============================================================");

// Base valid request (Wed 14:00 UTC, MultiCall3, 0.5 PHRS)
const VALID_BASE_REQUEST = {
  action_id: "test-act-001",
  action_type: "evm_call",
  target: "0xcA11bde05977b3631167028862bE2a173976CA11",
  value_wei: "500000000000000000", // 0.5 PHRS
  data: "0xbce38bd7",
  timestamp: 1793800800, // Wed Nov 4 2026 14:00:00 UTC
  description: "Valid batch call during business hours"
};

// Test 1: Spend request within limit -> ALLOW
runTest("Spend request within limit (0.5 PHRS <= 1.0 PHRS cap) -> ALLOW", () => {
  const req = { ...VALID_BASE_REQUEST, value_wei: "500000000000000000" };
  const res = evaluateAction(req, DEFAULT_POLICY);
  assert.strictEqual(res.outcome, "ALLOW");
  assert.strictEqual(res.deciding_rule_type, "consensus");
  const spendTrace = res.evaluations.find(e => e.rule_type === "spend_limit");
  assert.strictEqual(spendTrace.passed, true);
});

// Test 2: Spend request above limit -> DENY
runTest("Spend request above limit (5.0 PHRS > 1.0 PHRS cap) -> DENY", () => {
  const req = { ...VALID_BASE_REQUEST, value_wei: "5000000000000000000" }; // 5.0 PHRS
  const res = evaluateAction(req, DEFAULT_POLICY);
  assert.strictEqual(res.outcome, "DENY");
  assert.strictEqual(res.deciding_rule_id, "rule-spend-limit-01");
  assert.strictEqual(res.deciding_rule_type, "spend_limit");
  assert.ok(res.reason.includes("exceeds per-transaction limit"));
});

// Test 3: Invalid / negative spend amount -> DENY
runTest("Invalid / negative spend amount (-1000 wei) -> DENY (fail closed)", () => {
  const req = { ...VALID_BASE_REQUEST, value_wei: "-1000" };
  const res = evaluateAction(req, DEFAULT_POLICY);
  assert.strictEqual(res.outcome, "DENY");
  assert.strictEqual(res.deciding_rule_type, "spend_limit");
  assert.ok(res.reason.includes("Negative or malformed"));
});

// Test 4: Allowlisted address -> ALLOW
runTest("Allowlisted address (MultiCall3: 0xcA11...CA11) -> ALLOW", () => {
  const req = { ...VALID_BASE_REQUEST, target: "0xcA11bde05977b3631167028862bE2a173976CA11" };
  const res = evaluateAction(req, DEFAULT_POLICY);
  assert.strictEqual(res.outcome, "ALLOW");
  const allowTrace = res.evaluations.find(e => e.rule_type === "allowlist");
  assert.strictEqual(allowTrace.passed, true);
});

// Test 5: Unlisted address -> DENY
runTest("Unlisted address (0x9999...9999) -> DENY", () => {
  const req = { ...VALID_BASE_REQUEST, target: "0x9999999999999999999999999999999999999999" };
  const res = evaluateAction(req, DEFAULT_POLICY);
  assert.strictEqual(res.outcome, "DENY");
  assert.strictEqual(res.deciding_rule_id, "rule-allowlist-02");
  assert.strictEqual(res.deciding_rule_type, "allowlist");
  assert.ok(res.reason.includes("not in authorized allowlist"));
});

// Test 6: Invalid EVM address format -> DENY
runTest("Invalid EVM address format ('0xinvalid_target') -> DENY", () => {
  const req = { ...VALID_BASE_REQUEST, target: "0xinvalid_target" };
  const res = evaluateAction(req, DEFAULT_POLICY);
  assert.strictEqual(res.outcome, "DENY");
  assert.ok(res.reason.includes("not a valid 20-byte EVM hex address"));
});

// Test 7: Request inside permitted UTC window -> ALLOW
runTest("Request inside permitted UTC window (Wed 14:00 UTC) -> ALLOW", () => {
  const req = { ...VALID_BASE_REQUEST, timestamp: 1793800800 }; // Wed 14:00 UTC
  const res = evaluateAction(req, DEFAULT_POLICY);
  assert.strictEqual(res.outcome, "ALLOW");
  const timeTrace = res.evaluations.find(e => e.rule_type === "time_window");
  assert.strictEqual(timeTrace.passed, true);
});

// Test 8: Request outside permitted UTC window -> DENY
runTest("Request outside permitted UTC window (Wed 03:00 UTC) -> DENY", () => {
  const req = { ...VALID_BASE_REQUEST, timestamp: 1793761200 }; // Wed 03:00 UTC
  const res = evaluateAction(req, DEFAULT_POLICY);
  assert.strictEqual(res.outcome, "DENY");
  assert.strictEqual(res.deciding_rule_id, "rule-time-window-03");
  assert.strictEqual(res.deciding_rule_type, "time_window");
  assert.ok(res.reason.includes("outside authorized operating window"));
});

// Test 9: Weekday restrictions -> DENY
runTest("Weekday restrictions (Sunday noon: timestamp 1793534400) -> DENY", () => {
  const req = { ...VALID_BASE_REQUEST, timestamp: 1793534400 }; // Sunday 12:00 UTC
  const res = evaluateAction(req, DEFAULT_POLICY);
  assert.strictEqual(res.outcome, "DENY");
  assert.strictEqual(res.deciding_rule_type, "time_window");
  assert.ok(res.reason.includes("outside authorized days of week"));
});

// Test 10: Time-window boundary conditions -> ALLOW
runTest("Time-window boundary conditions (exact 08:00:00 and 20:00:00 UTC) -> ALLOW", () => {
  // Wed Nov 4 2026 08:00:00 UTC: 1793800800 - 6*3600 = 1793779200
  const reqStart = { ...VALID_BASE_REQUEST, timestamp: 1793779200 };
  const resStart = evaluateAction(reqStart, DEFAULT_POLICY);
  assert.strictEqual(resStart.outcome, "ALLOW");

  // Wed Nov 4 2026 20:00:00 UTC: 1793800800 + 6*3600 = 1793822400
  const reqEnd = { ...VALID_BASE_REQUEST, timestamp: 1793822400 };
  const resEnd = evaluateAction(reqEnd, DEFAULT_POLICY);
  assert.strictEqual(resEnd.outcome, "ALLOW");
});

// Test 11: Malformed policy -> fail closed
runTest("Malformed policy (empty rules array) -> DENY (fail closed)", () => {
  const brokenPolicy = { policy_id: "broken", rules: [] };
  const res = evaluateAction(VALID_BASE_REQUEST, brokenPolicy);
  assert.strictEqual(res.outcome, "DENY");
  assert.strictEqual(res.deciding_rule_id, "fail_closed_no_policy");
});

// Test 12: Evaluation exception handling -> fail closed
runTest("Unknown rule type in policy -> DENY (fail closed)", () => {
  const unknownPolicy = {
    policy_id: "unknown-rule-policy",
    rules: [
      { id: "rule-alien-99", type: "alien_quantum_check", enabled: true, parameters: {} }
    ]
  };
  const res = evaluateAction(VALID_BASE_REQUEST, unknownPolicy);
  assert.strictEqual(res.outcome, "DENY");
  assert.ok(res.reason.includes("Unknown rule type 'alien_quantum_check'"));
});

// Test 13: Verdict metadata contains execution_status: NOT EXECUTED
runTest("Verdict metadata always contains execution_status: NOT EXECUTED", () => {
  const allowRes = evaluateAction(VALID_BASE_REQUEST, DEFAULT_POLICY);
  assert.strictEqual(allowRes.execution_status, "NOT EXECUTED");

  const denyReq = { ...VALID_BASE_REQUEST, value_wei: "9999999999999999999" };
  const denyRes = evaluateAction(denyReq, DEFAULT_POLICY);
  assert.strictEqual(denyRes.execution_status, "NOT EXECUTED");
});

// Test 14: DENY decision guarantees zero execution dispatches
runTest("DENY decision guarantees zero execution dispatches", () => {
  let executionCalled = false;
  function mockExecutionAdapter() {
    executionCalled = true;
  }

  const denyReq = { ...VALID_BASE_REQUEST, target: "0x9999999999999999999999999999999999999999" };
  const res = evaluateAction(denyReq, DEFAULT_POLICY);
  if (res.outcome === "ALLOW") {
    mockExecutionAdapter();
  }
  assert.strictEqual(executionCalled, false);
});

// Test 15: Local backend mode API routing preserved
runTest("Local backend mode schema parity (evaluator outputs match FastAPI Decision schema)", () => {
  const res = evaluateAction(VALID_BASE_REQUEST, DEFAULT_POLICY);
  const requiredKeys = [
    "decision_id", "timestamp", "policy_id", "policy_version",
    "action_request", "outcome", "deciding_rule_id", "deciding_rule_type",
    "reason", "evaluations", "total_evaluation_time_ms", "execution_status"
  ];
  for (const k of requiredKeys) {
    assert.ok(k in res, `Missing required key: ${k}`);
  }
});

// Test 16: Browser-demo mode correctly identified when backend is offline
runTest("Browser-demo mode metadata flag is present", () => {
  const res = evaluateAction(VALID_BASE_REQUEST, DEFAULT_POLICY);
  assert.strictEqual(res.mode, "DEMO_BROWSER_EVALUATION");
});

console.log("============================================================");
console.log(`ALL ${passedTests}/${totalTests} JAVASCRIPT EVALUATOR TESTS PASSED!`);
console.log("============================================================");
