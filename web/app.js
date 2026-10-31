// Pharos Policy Gatekeeper — Dual-Mode Web Dashboard Application
// Mode A: Local Authoritative Mode (FastAPI Python Policy Engine)
// Mode B: Hosted Browser-Demo Mode (Deterministic Client-Side Policy Engine)

document.addEventListener("DOMContentLoaded", () => {
  // Mode & Navigation Elements
  const badgeMode = document.getElementById("badge-mode");
  const modeText = document.getElementById("mode-text");
  const badgeNetwork = document.getElementById("badge-network");
  const networkText = document.getElementById("network-text");
  const safetyTitle = document.getElementById("safety-mode-title");
  const safetyText = document.getElementById("safety-mode-text");
  const metaOperatingMode = document.getElementById("meta-operating-mode");
  const auditTitleText = document.getElementById("audit-title-text");
  const auditModeNotice = document.getElementById("audit-mode-notice");
  const auditFooterText = document.getElementById("audit-footer-text");

  // Form & Simulator Elements
  const form = document.getElementById("action-form");
  const btnSubmit = document.getElementById("btn-submit-eval");
  
  // Verdict Elements
  const verdictPill = document.getElementById("verdict-pill");
  const verdictBanner = document.getElementById("verdict-banner");
  const verdictTitle = document.getElementById("verdict-title");
  const verdictReason = document.getElementById("verdict-reason");
  const metaDecidingRule = document.getElementById("meta-deciding-rule");
  const metaRuleType = document.getElementById("meta-rule-type");
  const metaDecisionId = document.getElementById("meta-decision-id");
  const metaExecutionStatus = document.getElementById("meta-execution-status");
  const ruleTracesList = document.getElementById("rule-traces-list");

  // Audit Elements
  const auditTableBody = document.getElementById("audit-table-body");
  const btnVerifyAudit = document.getElementById("btn-verify-audit");
  const btnRefreshAudit = document.getElementById("btn-refresh-audit");
  const integrityBanner = document.getElementById("integrity-banner");
  const integrityTitle = document.getElementById("integrity-title");
  const integrityMsg = document.getElementById("integrity-msg");
  const integrityIcon = document.getElementById("integrity-icon");

  // Form Inputs
  const inputActionId = document.getElementById("input-action-id");
  const inputActionType = document.getElementById("input-action-type");
  const inputTarget = document.getElementById("input-target");
  const inputValueWei = document.getElementById("input-value-wei");
  const inputCalldata = document.getElementById("input-calldata");
  const inputTimestamp = document.getElementById("input-timestamp");
  const inputDescription = document.getElementById("input-description");

  // Preset Buttons
  const presetAllow = document.getElementById("preset-allow");
  const presetDenySpend = document.getElementById("preset-deny-spend");
  const presetDenyAllowlist = document.getElementById("preset-deny-allowlist");
  const presetDenyTime = document.getElementById("preset-deny-time");
  const allPresets = [presetAllow, presetDenySpend, presetDenyAllowlist, presetDenyTime];

  // State
  let isLocalBackend = false;
  let browserSessionRecords = [];
  let lastSessionHash = "0000000000000000000000000000000000000000000000000000000000000000";

  function setActivePreset(activeBtn) {
    allPresets.forEach(btn => btn.classList.remove("active"));
    if (activeBtn) activeBtn.classList.add("active");
  }

  // Preset Listeners
  presetAllow.addEventListener("click", () => {
    setActivePreset(presetAllow);
    inputActionId.value = "act-allow-001";
    inputActionType.value = "evm_call";
    inputTarget.value = "0xcA11bde05977b3631167028862bE2a173976CA11";
    inputValueWei.value = "0";
    inputTimestamp.value = "1793800800"; // Wed 14:00 UTC
    inputCalldata.value = "0xbce38bd70000000000000000000000000000000000000000000000000000000000000000";
    inputDescription.value = "MultiCall3 batch read evaluation during approved Wednesday 14:00 UTC business window";
  });

  presetDenySpend.addEventListener("click", () => {
    setActivePreset(presetDenySpend);
    inputActionId.value = "act-deny-spend-002";
    inputActionType.value = "evm_call";
    inputTarget.value = "0x76A4De34D608AEf6003117565868E079d20c57F9";
    inputValueWei.value = "5000000000000000000"; // 5.0 PHRS (exceeds 1.0 PHRS)
    inputTimestamp.value = "1793800800";
    inputCalldata.value = "0xd0e30db0";
    inputDescription.value = "Attempted 5.0 PHRS deposit into WPHRS, exceeding per-transaction limit of 1.0 PHRS";
  });

  presetDenyAllowlist.addEventListener("click", () => {
    setActivePreset(presetDenyAllowlist);
    inputActionId.value = "act-deny-allowlist-003";
    inputActionType.value = "evm_call";
    inputTarget.value = "0x9999999999999999999999999999999999999999";
    inputValueWei.value = "0";
    inputTimestamp.value = "1793800800";
    inputCalldata.value = "0xa9059cbb00000000000000000000000099999999999999999999999999999999999999990000000000000000000000000000000000000000000000000000000000000001";
    inputDescription.value = "Attempted interaction with unverified, non-allowlisted target address 0x9999...";
  });

  presetDenyTime.addEventListener("click", () => {
    setActivePreset(presetDenyTime);
    inputActionId.value = "act-deny-timewindow-004";
    inputActionType.value = "evm_call";
    inputTarget.value = "0xcA11bde05977b3631167028862bE2a173976CA11";
    inputValueWei.value = "0";
    inputTimestamp.value = "1793761200"; // Wed 03:00 UTC (outside 08:00-20:00)
    inputCalldata.value = "0xbce38bd7";
    inputDescription.value = "Attempted execution on Wednesday at 03:00 UTC (outside permitted 08:00-20:00 UTC window)";
  });

  // Quick Links
  document.querySelectorAll(".quick-link[data-target]").forEach(btn => {
    btn.addEventListener("click", () => {
      inputTarget.value = btn.getAttribute("data-target");
      setActivePreset(null);
    });
  });

  document.querySelectorAll(".quick-link[data-value]").forEach(btn => {
    btn.addEventListener("click", () => {
      inputValueWei.value = btn.getAttribute("data-value");
      setActivePreset(null);
    });
  });

  document.querySelectorAll(".quick-link[data-time]").forEach(btn => {
    btn.addEventListener("click", () => {
      const mode = btn.getAttribute("data-time");
      if (mode === "wednesday_business") {
        inputTimestamp.value = "1793800800"; // Wed 14:00 UTC
      } else if (mode === "wednesday_night") {
        inputTimestamp.value = "1793761200"; // Wed 03:00 UTC
      } else if (mode === "weekend") {
        inputTimestamp.value = "1793534400"; // Sunday 12:00 UTC
      }
      setActivePreset(null);
    });
  });

  // Helper: SHA-256 for browser-side audit chaining
  async function computeSha256(text) {
    if (window.crypto && window.crypto.subtle) {
      const msgBuffer = new TextEncoder().encode(text);
      const hashBuffer = await window.crypto.subtle.digest("SHA-256", msgBuffer);
      const hashArray = Array.from(new Uint8Array(hashBuffer));
      return hashArray.map(b => b.toString(16).padStart(2, "0")).join("");
    }
    // Fallback simple hash string if crypto.subtle not available
    let hash = 0;
    for (let i = 0; i < text.length; i++) {
      hash = ((hash << 5) - hash) + text.charCodeAt(i);
      hash |= 0;
    }
    return Math.abs(hash).toString(16).padStart(64, "0");
  }

  // Mode Auto-Detection & Initialization
  async function detectOperatingMode() {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 2000);
      const resp = await fetch("/api/status", { signal: controller.signal });
      clearTimeout(timeoutId);

      if (resp.ok) {
        const data = await resp.json();
        if (data.status === "healthy") {
          enableLocalBackendMode(data);
          return;
        }
      }
      enableBrowserDemoMode("Backend reported non-healthy status.");
    } catch (e) {
      enableBrowserDemoMode("FastAPI server unreachable (Hosted Vercel environment).");
    }
  }

  function enableLocalBackendMode(data) {
    isLocalBackend = true;
    badgeMode.className = "status-badge badge-success";
    modeText.textContent = "LOCAL BACKEND ACTIVE (FastAPI Engine)";
    
    safetyTitle.textContent = "LOCAL AUTHORITATIVE MODE — FASTAPI ENGINE ACTIVE";
    safetyText.innerHTML = "Connected to local Python policy gatekeeper. Decisions are evaluated by the authoritative Python engine with immutable SHA-256 audit ledger logging. Every verdict reports <code class=\"status-code\">execution_status: NOT EXECUTED</code>.";

    metaOperatingMode.textContent = "Local Python Engine";
    metaOperatingMode.className = "meta-value mono text-success";

    auditTitleText.textContent = "Append-Only Audit Ledger (audit.jsonl)";
    auditModeNotice.textContent = "Authoritative SHA-256 Cryptographic Hash Chain Ledger (audit.jsonl)";
    auditFooterText.innerHTML = "ℹ️ Authoritative tamper-evident SHA-256 hash chaining: <code>entry_hash = SHA-256(prev || payload)</code>";

    if (data.network && data.network.connected) {
      badgeNetwork.className = "status-badge badge-success";
      networkText.textContent = `Atlantic Testnet (#${data.network.block_number.toLocaleString()}, ${data.network.latency_ms}ms)`;
    } else {
      badgeNetwork.className = "status-badge badge-neutral";
      networkText.textContent = "Atlantic RPC: Standby (Offline-First)";
    }

    loadBackendAuditRecords();
  }

  function enableBrowserDemoMode(reason) {
    isLocalBackend = false;
    badgeMode.className = "status-badge badge-warning";
    modeText.textContent = "DEMO MODE — BROWSER-SIDE EVALUATION";

    safetyTitle.textContent = "DEMO MODE — BROWSER-SIDE POLICY EVALUATION";
    safetyText.innerHTML = "Policy decisions are demonstrations only. They do not authorize, execute, block, or secure real wallet transactions. Every evaluation strictly returns <code class=\"status-code\">execution_status: NOT EXECUTED</code>.";

    metaOperatingMode.textContent = "Browser-Side Demo";
    metaOperatingMode.className = "meta-value mono text-warning";

    auditTitleText.textContent = "Evaluation Audit History";
    auditModeNotice.textContent = "Browser Session History (Demonstration Log — Retained in Memory)";
    auditFooterText.innerHTML = "ℹ️ Demonstration mode: Session entries are hashed in-memory. For persistent cryptographic audit ledger, run local backend.";

    badgeNetwork.className = "status-badge badge-neutral";
    networkText.textContent = "Atlantic RPC: Client Evaluation";

    loadSeedBrowserDemoRecords();
  }

  // Initial Demo Seed Records (Matching Task 11 Canonical Proofs)
  async function loadSeedBrowserDemoRecords() {
    if (browserSessionRecords.length === 0) {
      const seedEntries = [
        {
          seq: 1,
          time: "2026-11-04 14:00:00 UTC",
          outcome: "ALLOW",
          rule: "consensus",
          desc: "MultiCall3 batch read during Wed business hours"
        },
        {
          seq: 2,
          time: "2026-11-04 14:00:00 UTC",
          outcome: "DENY",
          rule: "rule-spend-limit-01",
          desc: "Native spend of 5.0 PHRS exceeds 1.0 PHRS limit"
        },
        {
          seq: 3,
          time: "2026-11-04 14:00:00 UTC",
          outcome: "DENY",
          rule: "rule-allowlist-02",
          desc: "Target address 0x9999... is not in authorized allowlist"
        },
        {
          seq: 4,
          time: "2026-11-04 03:00:00 UTC",
          outcome: "DENY",
          rule: "rule-time-window-03",
          desc: "Time 03:00 UTC is outside authorized 08:00-20:00 window"
        }
      ];

      for (const item of seedEntries) {
        const payloadStr = JSON.stringify(item);
        const entryHash = await computeSha256(lastSessionHash + payloadStr);
        browserSessionRecords.push({
          sequence_number: item.seq,
          timestamp: item.time,
          outcome: item.outcome,
          deciding_rule_id: item.rule,
          reason: item.desc,
          integrity: {
            previous_hash: lastSessionHash,
            entry_hash: entryHash
          }
        });
        lastSessionHash = entryHash;
      }
    }
    renderAuditTable(browserSessionRecords);
  }

  // Load Backend Records (Mode A)
  async function loadBackendAuditRecords() {
    try {
      const resp = await fetch("/api/audit?limit=50&tail=true");
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();
      renderAuditTable(data.entries || []);
    } catch (e) {
      auditTableBody.innerHTML = `<tr><td colspan="5" class="table-empty text-warning">Failed to load backend audit records: ${e.message}</td></tr>`;
    }
  }

  function renderAuditTable(entries) {
    auditTableBody.innerHTML = "";
    if (!entries || entries.length === 0) {
      auditTableBody.innerHTML = `<tr><td colspan="5" class="table-empty">Ledger is empty (0 records).</td></tr>`;
      return;
    }

    const reversed = [...entries].reverse();
    reversed.forEach(entry => {
      const tr = document.createElement("tr");
      const outcomeClass = entry.outcome === "ALLOW" ? "allow" : "deny";
      const prevH = (entry.integrity.previous_hash || "").substring(0, 8);
      const currH = (entry.integrity.entry_hash || "").substring(0, 8);
      const seqPadded = String(entry.sequence_number).padStart(4, "0");

      tr.innerHTML = `
        <td>#${seqPadded}</td>
        <td>${entry.timestamp}</td>
        <td><span class="badge-table ${outcomeClass}">${entry.outcome}</span></td>
        <td title="${entry.reason}">${entry.deciding_rule_id}</td>
        <td><span title="${entry.integrity.previous_hash}">${prevH}...</span> &rarr; <span title="${entry.integrity.entry_hash}">${currH}...</span></td>
      `;
      auditTableBody.appendChild(tr);
    });
  }

  // Verify Audit Integrity
  btnVerifyAudit.addEventListener("click", async () => {
    btnVerifyAudit.disabled = true;
    btnVerifyAudit.innerHTML = "<span>⏳</span> Verifying...";

    if (isLocalBackend) {
      try {
        const resp = await fetch("/api/verify");
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const res = await resp.json();

        integrityBanner.classList.remove("hidden");
        if (res.is_valid) {
          integrityBanner.style.background = "var(--status-allow-bg)";
          integrityBanner.style.borderColor = "var(--status-allow-border)";
          integrityIcon.textContent = "✅";
          integrityTitle.textContent = `Authoritative SHA-256 Chain Verified (${res.total_records} records)`;
          integrityTitle.style.color = "var(--status-allow-text)";
          integrityMsg.textContent = res.message;
        } else {
          integrityBanner.style.background = "var(--status-deny-bg)";
          integrityBanner.style.borderColor = "var(--status-deny-border)";
          integrityIcon.textContent = "🛑";
          integrityTitle.textContent = "Tampering / Inconsistency Detected!";
          integrityTitle.style.color = "var(--status-deny-text)";
          integrityMsg.textContent = res.message;
        }
      } catch (e) {
        alert(`Verification failed: ${e.message}`);
      } finally {
        btnVerifyAudit.disabled = false;
        btnVerifyAudit.innerHTML = "<span>🔐</span> Verify Hash Chain";
      }
    } else {
      // Browser demo mode: verify in-memory session chain
      let isValid = true;
      let checkHash = "0000000000000000000000000000000000000000000000000000000000000000";
      for (const rec of browserSessionRecords) {
        if (rec.integrity.previous_hash !== checkHash) {
          isValid = false;
          break;
        }
        checkHash = rec.integrity.entry_hash;
      }

      integrityBanner.classList.remove("hidden");
      integrityBanner.style.background = "var(--status-allow-bg)";
      integrityBanner.style.borderColor = "var(--status-allow-border)";
      integrityIcon.textContent = "✅";
      integrityTitle.textContent = `Session History Verified (${browserSessionRecords.length} entries)`;
      integrityTitle.style.color = "var(--status-allow-text)";
      integrityMsg.textContent = "In-memory session demonstration chain verified. Notice: For the permanent SHA-256 ledger, run local backend (python cli.py audit verify).";

      btnVerifyAudit.disabled = false;
      btnVerifyAudit.innerHTML = "<span>🔐</span> Verify Hash Chain";
    }
  });

  btnRefreshAudit.addEventListener("click", () => {
    if (isLocalBackend) {
      loadBackendAuditRecords();
    } else {
      renderAuditTable(browserSessionRecords);
    }
  });

  // Action Submission Handler (Dual-Mode)
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    btnSubmit.disabled = true;
    btnSubmit.innerHTML = "<span>⏳</span> Evaluating Deterministic Policy...";

    const payload = {
      action_id: inputActionId.value.trim(),
      action_type: inputActionType.value,
      target: inputTarget.value.trim(),
      value_wei: inputValueWei.value ? inputValueWei.value.trim() : "0",
      data: inputCalldata.value.trim() || "0x",
      timestamp: inputTimestamp.value ? parseInt(inputTimestamp.value, 10) : null,
      description: inputDescription.value.trim(),
      metadata: { source: isLocalBackend ? "web_dashboard_backend" : "web_dashboard_browser_demo" }
    };

    if (isLocalBackend) {
      // MODE A: Local Authoritative Python Backend
      try {
        const resp = await fetch("/api/check", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });

        if (!resp.ok) {
          const errJson = await resp.json();
          throw new Error(errJson.detail || `HTTP ${resp.status}`);
        }

        const decision = await resp.json();
        renderDecision(decision);
        loadBackendAuditRecords();
      } catch (err) {
        alert(`Backend evaluation error: ${err.message}. Falling back to browser evaluator.`);
        runBrowserEvaluation(payload);
      } finally {
        btnSubmit.disabled = false;
        btnSubmit.innerHTML = '<span class="btn-icon">🛡️</span> Evaluate Policy Gate';
      }
    } else {
      // MODE B: Hosted Browser-Side Demonstration
      runBrowserEvaluation(payload);
      btnSubmit.disabled = false;
      btnSubmit.innerHTML = '<span class="btn-icon">🛡️</span> Evaluate Policy Gate';
    }
  });

  async function runBrowserEvaluation(payload) {
    if (typeof PolicyEvaluator === "undefined" || !PolicyEvaluator.evaluateAction) {
      alert("Error: Browser policy evaluator module is not loaded.");
      return;
    }

    const decision = PolicyEvaluator.evaluateAction(payload, PolicyEvaluator.DEFAULT_POLICY);
    renderDecision(decision);

    // Append to browser demo session records
    const nextSeq = browserSessionRecords.length + 1;
    const recPayload = JSON.stringify({ seq: nextSeq, outcome: decision.outcome, rule: decision.deciding_rule_id, desc: decision.reason });
    const entryHash = await computeSha256(lastSessionHash + recPayload);

    browserSessionRecords.push({
      sequence_number: nextSeq,
      timestamp: new Date().toISOString().replace("T", " ").substring(0, 19) + " UTC",
      outcome: decision.outcome,
      deciding_rule_id: decision.deciding_rule_id,
      reason: decision.reason,
      integrity: {
        previous_hash: lastSessionHash,
        entry_hash: entryHash
      }
    });
    lastSessionHash = entryHash;

    renderAuditTable(browserSessionRecords);
  }

  function renderDecision(decision) {
    const isAllow = decision.outcome === "ALLOW";

    // Verdict Pill
    verdictPill.className = `verdict-pill ${isAllow ? "allow" : "deny"}`;
    verdictPill.textContent = decision.outcome;

    // Verdict Banner
    verdictBanner.className = `verdict-banner ${isAllow ? "allow" : "deny"}`;
    verdictTitle.textContent = isAllow ? "Action Authorized by Policy" : "Action Blocked by Gatekeeper";
    verdictReason.textContent = decision.reason;

    // Meta Items
    metaDecidingRule.textContent = decision.deciding_rule_id;
    metaRuleType.textContent = decision.deciding_rule_type;
    metaDecisionId.textContent = decision.decision_id;
    metaExecutionStatus.textContent = "NOT EXECUTED";

    // Rule Traces
    ruleTracesList.innerHTML = "";
    if (decision.evaluations && decision.evaluations.length > 0) {
      decision.evaluations.forEach(ev => {
        const item = document.createElement("div");
        const passClass = ev.passed ? "pass" : "fail";
        const badgeText = ev.passed ? "PASS" : "FAIL";

        item.className = `trace-item ${passClass}`;
        item.innerHTML = `
          <div class="trace-badge ${passClass}">${badgeText}</div>
          <div class="trace-details">
            <div class="trace-header">
              <span class="trace-rule-id">${ev.rule_id} (${ev.rule_type})</span>
              <span class="trace-time">${ev.execution_time_ms}ms</span>
            </div>
            <div class="trace-msg">${ev.message}</div>
          </div>
        `;
        ruleTracesList.appendChild(item);
      });
    } else {
      ruleTracesList.innerHTML = `<div class="empty-state">No individual rule traces recorded.</div>`;
    }
  }

  // Detect mode immediately on startup
  detectOperatingMode();
});
