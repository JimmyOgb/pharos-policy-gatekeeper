/**
 * Pharos Policy Gatekeeper — Deterministic Browser-Side Policy Engine
 * Evaluates action requests against configured rules: Spend Limit, Allowlist, Time Window.
 * 
 * FAIL-CLOSED INVARIANT:
 * Any invalid input, unknown rule, or unexpected error strictly returns DENY.
 * Every decision returns execution_status: "NOT EXECUTED".
 */

(function (root, factory) {
  if (typeof module === 'object' && module.exports) {
    module.exports = factory();
  } else {
    root.PolicyEvaluator = factory();
  }
}(typeof self !== 'undefined' ? self : this, function () {

  const DEFAULT_POLICY = {
    version: "1.0.0",
    policy_id: "pharos-atlantic-guardian-v1",
    name: "Pharos Atlantic Testnet Standard Protection Policy",
    default_action: "DENY",
    rules: [
      {
        id: "rule-spend-limit-01",
        type: "spend_limit",
        name: "Maximum Single Transaction and ERC20 Spend Cap",
        enabled: true,
        parameters: {
          max_native_wei: "1000000000000000000", // 1.0 PHRS
          max_cumulative_native_wei: "5000000000000000000", // 5.0 PHRS
          tokens: [
            {
              symbol: "USDC",
              contract: "0xcfC8330f4BCAB529c625D12781b1C19466A9Fc8B",
              decimals: 6,
              max_amount_raw: "100000000" // 100.00 USDC
            }
          ]
        }
      },
      {
        id: "rule-allowlist-02",
        type: "allowlist",
        name: "Verified Atlantic Contract Whitelist",
        enabled: true,
        parameters: {
          allow_unknown_targets: false,
          allowed_addresses: [
            { address: "0xcA11bde05977b3631167028862bE2a173976CA11", name: "MultiCall3" },
            { address: "0xcfC8330f4BCAB529c625D12781b1C19466A9Fc8B", name: "Atlantic USDC" },
            { address: "0x76A4De34D608AEf6003117565868E079d20c57F9", name: "Atlantic WPHRS" },
            { address: "0x1111111254fb6c44bac0bed2854e76f90643097d", name: "Operations Safe" }
          ],
          allowed_function_selectors: [
            { selector: "0x095ea7b3", name: "approve(address,uint256)" },
            { selector: "0xa9059cbb", name: "transfer(address,uint256)" },
            { selector: "0xd0e30db0", name: "deposit()" },
            { selector: "0x2e1a7d4d", name: "withdraw(uint256)" },
            { selector: "0xbce38bd7", name: "tryAggregate(bool,(address,bytes)[])" }
          ]
        }
      },
      {
        id: "rule-time-window-03",
        type: "time_window",
        name: "Authorized Business Hours Window",
        enabled: true,
        parameters: {
          timezone: "UTC",
          allowed_start_utc: "08:00:00",
          allowed_end_utc: "20:00:00",
          allowed_days_of_week: ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY"]
        }
      }
    ]
  };

  const EVM_ADDRESS_REGEX = /^0x[0-9a-fA-F]{40}$/;

  /**
   * Evaluates an ActionRequest against a security Policy.
   * Deterministic, fail-closed.
   */
  function evaluateAction(request, policy, clockOverride) {
    const t0 = (typeof performance !== 'undefined' && performance.now) ? performance.now() : Date.now();
    policy = policy || DEFAULT_POLICY;

    // Fail-closed validation of request object
    if (!request || typeof request !== 'object') {
      return buildDeny("fail_closed_invalid_request", "system", "Action request payload is null or not an object.", [], t0);
    }
    if (!request.action_id || typeof request.action_id !== 'string') {
      return buildDeny("fail_closed_missing_id", "system", "Action request missing valid action_id string.", [], t0);
    }
    if (!request.action_type || !['evm_call', 'evm_transfer'].includes(request.action_type)) {
      return buildDeny("fail_closed_invalid_type", "system", `Unsupported or invalid action_type: '${request.action_type}'. Must be evm_call or evm_transfer.`, [], t0);
    }
    if (!request.target || typeof request.target !== 'string' || !EVM_ADDRESS_REGEX.test(request.target.trim())) {
      return buildDeny("fail_closed_invalid_address", "system", `Target address '${request.target}' is not a valid 20-byte EVM hex address.`, [], t0);
    }

    // Fail-closed validation of policy
    if (!policy || !Array.isArray(policy.rules) || policy.rules.length === 0) {
      return buildDeny("fail_closed_no_policy", "system", "No valid policy rules configured; fail-closed.", [], t0);
    }

    const evaluations = [];
    const normalizedTarget = request.target.trim().toLowerCase();

    // Evaluate Rule 1: Spend Limit
    const spendRule = policy.rules.find(r => r.type === "spend_limit" && r.enabled);
    if (spendRule) {
      const startRule = (typeof performance !== 'undefined' && performance.now) ? performance.now() : Date.now();
      let passed = true;
      let msg = "";

      try {
        let valueWei;
        try {
          valueWei = BigInt(request.value_wei != null ? String(request.value_wei) : "0");
        } catch (e) {
          valueWei = -1n;
        }

        if (valueWei < 0n) {
          passed = false;
          msg = `Negative or malformed native spend value (${request.value_wei}) is strictly rejected.`;
        } else {
          const maxWei = BigInt(spendRule.parameters.max_native_wei || "0");
          if (valueWei > maxWei) {
            passed = false;
            const ethVal = (Number(valueWei) / 1e18).toFixed(4);
            const maxEth = (Number(maxWei) / 1e18).toFixed(4);
            msg = `Native spend of ${valueWei} wei (${ethVal} PHRS) exceeds per-transaction limit of ${maxWei} wei (${maxEth} PHRS).`;
          } else {
            // Check ERC-20 tokens if target is token and data is transfer
            const tokenConfig = (spendRule.parameters.tokens || []).find(t => t.contract.toLowerCase() === normalizedTarget);
            if (tokenConfig && request.data && request.data.startsWith("0xa9059cbb") && request.data.length >= 74) {
              const rawAmountHex = "0x" + request.data.slice(74, 138);
              const erc20Amount = BigInt(rawAmountHex);
              const maxTokenRaw = BigInt(tokenConfig.max_amount_raw || "0");
              if (erc20Amount > maxTokenRaw) {
                passed = false;
                msg = `ERC-20 ${tokenConfig.symbol} spend of ${erc20Amount} raw units exceeds per-transaction limit of ${maxTokenRaw} raw units.`;
              }
            }
          }
        }

        if (passed) {
          msg = `Spend limit check passed: value ${request.value_wei || 0} wei <= ${spendRule.parameters.max_native_wei} wei.`;
        }
      } catch (err) {
        passed = false;
        msg = `Exception during spend limit evaluation: ${err.message}`;
      }

      const elapsed = Math.max(0.01, (((typeof performance !== 'undefined' && performance.now) ? performance.now() : Date.now()) - startRule));
      evaluations.push({
        rule_id: spendRule.id,
        rule_type: "spend_limit",
        passed: passed,
        message: msg,
        execution_time_ms: parseFloat(elapsed.toFixed(3))
      });

      if (!passed) {
        return buildDecision("DENY", spendRule.id, "spend_limit", msg, evaluations, request, policy, t0);
      }
    }

    // Evaluate Rule 2: Allowlist
    const allowRule = policy.rules.find(r => r.type === "allowlist" && r.enabled);
    if (allowRule) {
      const startRule = (typeof performance !== 'undefined' && performance.now) ? performance.now() : Date.now();
      let passed = true;
      let msg = "";

      try {
        const allowedTargets = (allowRule.parameters.allowed_addresses || []).map(a => a.address.toLowerCase());
        const targetObj = (allowRule.parameters.allowed_addresses || []).find(a => a.address.toLowerCase() === normalizedTarget);

        if (!allowedTargets.includes(normalizedTarget)) {
          passed = false;
          msg = `Target address '${request.target}' is not in authorized allowlist.`;
        } else {
          // Check function selector whitelist if calldata provided
          if (request.data && request.data.length >= 10 && allowRule.parameters.allowed_function_selectors) {
            const selector = request.data.slice(0, 10).toLowerCase();
            const allowedSelectors = (allowRule.parameters.allowed_function_selectors || []).map(s => s.selector.toLowerCase());
            if (!allowedSelectors.includes(selector)) {
              passed = false;
              msg = `Function selector '${selector}' on target '${targetObj ? targetObj.name : normalizedTarget}' is not in authorized selector list.`;
            }
          }
        }

        if (passed) {
          msg = `Target '${targetObj ? targetObj.name : request.target}' is authorized by allowlist.`;
        }
      } catch (err) {
        passed = false;
        msg = `Exception during allowlist evaluation: ${err.message}`;
      }

      const elapsed = Math.max(0.01, (((typeof performance !== 'undefined' && performance.now) ? performance.now() : Date.now()) - startRule));
      evaluations.push({
        rule_id: allowRule.id,
        rule_type: "allowlist",
        passed: passed,
        message: msg,
        execution_time_ms: parseFloat(elapsed.toFixed(3))
      });

      if (!passed) {
        return buildDecision("DENY", allowRule.id, "allowlist", msg, evaluations, request, policy, t0);
      }
    }

    // Evaluate Rule 3: Time Window
    const timeRule = policy.rules.find(r => r.type === "time_window" && r.enabled);
    if (timeRule) {
      const startRule = (typeof performance !== 'undefined' && performance.now) ? performance.now() : Date.now();
      let passed = true;
      let msg = "";

      try {
        let evalTimestamp = request.timestamp != null ? Number(request.timestamp) : (clockOverride != null ? clockOverride : Math.floor(Date.now() / 1000));
        if (isNaN(evalTimestamp) || evalTimestamp <= 0) {
          passed = false;
          msg = `Invalid timestamp provided for time window check: '${request.timestamp}'.`;
        } else {
          const evalDate = new Date(evalTimestamp * 1000);
          const DAYS = ["SUNDAY", "MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY"];
          const dayOfWeek = DAYS[evalDate.getUTCDay()];

          const allowedDays = (timeRule.parameters.allowed_days_of_week || []).map(d => d.toUpperCase());
          if (!allowedDays.includes(dayOfWeek)) {
            passed = false;
            msg = `Execution day ${dayOfWeek} is outside authorized days of week (${allowedDays.join(', ')}).`;
          } else {
            // Check time of day (seconds from midnight UTC)
            const curSec = evalDate.getUTCHours() * 3600 + evalDate.getUTCMinutes() * 60 + evalDate.getUTCSeconds();
            const startParts = (timeRule.parameters.allowed_start_utc || "08:00:00").split(":").map(Number);
            const endParts = (timeRule.parameters.allowed_end_utc || "20:00:00").split(":").map(Number);
            const startSec = startParts[0] * 3600 + (startParts[1] || 0) * 60 + (startParts[2] || 0);
            const endSec = endParts[0] * 3600 + (endParts[1] || 0) * 60 + (endParts[2] || 0);

            if (curSec < startSec || curSec > endSec) {
              passed = false;
              const curTimeStr = evalDate.toISOString().substring(11, 19);
              msg = `Current time ${curTimeStr} UTC is outside authorized operating window (${timeRule.parameters.allowed_start_utc} to ${timeRule.parameters.allowed_end_utc} UTC).`;
            } else {
              const curTimeStr = evalDate.toISOString().substring(11, 19);
              msg = `Execution at ${dayOfWeek} ${curTimeStr} UTC is within authorized window (${timeRule.parameters.allowed_start_utc} to ${timeRule.parameters.allowed_end_utc} UTC).`;
            }
          }
        }
      } catch (err) {
        passed = false;
        msg = `Exception during time window evaluation: ${err.message}`;
      }

      const elapsed = Math.max(0.01, (((typeof performance !== 'undefined' && performance.now) ? performance.now() : Date.now()) - startRule));
      evaluations.push({
        rule_id: timeRule.id,
        rule_type: "time_window",
        passed: passed,
        message: msg,
        execution_time_ms: parseFloat(elapsed.toFixed(3))
      });

      if (!passed) {
        return buildDecision("DENY", timeRule.id, "time_window", msg, evaluations, request, policy, t0);
      }
    }

    // Check if unknown rules exist that were not evaluated
    const knownTypes = ["spend_limit", "allowlist", "time_window"];
    for (const r of policy.rules) {
      if (r.enabled && !knownTypes.includes(r.type)) {
        const failMsg = `Unknown rule type '${r.type}' in policy; fail closed.`;
        evaluations.push({
          rule_id: r.id,
          rule_type: r.type,
          passed: false,
          message: failMsg,
          execution_time_ms: 0.01
        });
        return buildDecision("DENY", r.id, r.type, failMsg, evaluations, request, policy, t0);
      }
    }

    // Consensus ALLOW
    return buildDecision(
      "ALLOW",
      "consensus",
      "consensus",
      "Action complies with all active policy rules (spend_limit, allowlist, time_window).",
      evaluations,
      request,
      policy,
      t0
    );
  }

  function buildDecision(outcome, decidingRuleId, decidingRuleType, reason, evaluations, request, policy, t0) {
    const elapsedTotal = Math.max(0.05, (((typeof performance !== 'undefined' && performance.now) ? performance.now() : Date.now()) - t0));
    const randomHex = Math.random().toString(16).substring(2, 10);
    const decisionId = `dec-${policy ? policy.policy_id : "demo"}-${request ? request.action_id : "act"}-${randomHex}`;

    return {
      decision_id: decisionId,
      timestamp: new Date().toISOString(),
      policy_id: policy ? policy.policy_id : "pharos-atlantic-guardian-v1",
      policy_version: policy ? policy.version : "1.0.0",
      action_request: request || {},
      outcome: outcome,
      deciding_rule_id: decidingRuleId,
      deciding_rule_type: decidingRuleType,
      reason: reason,
      evaluations: evaluations,
      total_evaluation_time_ms: parseFloat(elapsedTotal.toFixed(3)),
      execution_status: "NOT EXECUTED",
      mode: "DEMO_BROWSER_EVALUATION"
    };
  }

  function buildDeny(ruleId, ruleType, reason, evaluations, t0) {
    return buildDecision("DENY", ruleId, ruleType, reason, evaluations, { action_id: "invalid-request" }, DEFAULT_POLICY, t0);
  }

  return {
    DEFAULT_POLICY: DEFAULT_POLICY,
    evaluateAction: evaluateAction,
    EVM_ADDRESS_REGEX: EVM_ADDRESS_REGEX
  };
}));
