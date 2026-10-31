// Pharos Policy Gatekeeper — Web Dashboard Client Application

document.addEventListener("DOMContentLoaded", () => {
  // Elements
  const badgeNetwork = document.getElementById("badge-network");
  const networkText = document.getElementById("network-text");
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

  function setActivePreset(activeBtn) {
    allPresets.forEach(btn => btn.classList.remove("active"));
    if (activeBtn) activeBtn.classList.add("active");
  }

  // Presets definition
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
    inputValueWei.value = "5000000000000000000"; // 5.0 PHRS (exceeds 1.0)
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
        inputTimestamp.value = "1793444400"; // Saturday 11:00 UTC
      }
      setActivePreset(null);
    });
  });

  // Fetch Status & Network
  async function loadStatus() {
    try {
      const resp = await fetch("/api/status");
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();

      // Network badge
      if (data.network && data.network.connected) {
        badgeNetwork.className = "status-badge badge-success";
        networkText.textContent = `Atlantic Testnet (#${data.network.block_number.toLocaleString()}, ${data.network.latency_ms}ms)`;
      } else {
        badgeNetwork.className = "status-badge badge-warning";
        networkText.textContent = "Atlantic RPC: Offline (Policy Engine Active)";
      }
    } catch (e) {
      badgeNetwork.className = "status-badge badge-warning";
      networkText.textContent = "Atlantic RPC: Offline (Policy Engine Active)";
    }
  }

  // Load Audit Records
  async function loadAuditRecords() {
    try {
      const resp = await fetch("/api/audit?limit=50&tail=true");
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();

      auditTableBody.innerHTML = "";
      if (!data.entries || data.entries.length === 0) {
        auditTableBody.innerHTML = `<tr><td colspan="5" class="table-empty">Ledger is empty (0 records).</td></tr>`;
        return;
      }

      // Render rows (most recent first)
      const reversed = [...data.entries].reverse();
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
    } catch (e) {
      auditTableBody.innerHTML = `<tr><td colspan="5" class="table-empty text-warning">Failed to load audit records: ${e.message}</td></tr>`;
    }
  }

  // Verify Audit Integrity
  btnVerifyAudit.addEventListener("click", async () => {
    btnVerifyAudit.disabled = true;
    btnVerifyAudit.innerHTML = "<span>⏳</span> Verifying...";

    try {
      const resp = await fetch("/api/verify");
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const res = await resp.json();

      integrityBanner.classList.remove("hidden");
      if (res.is_valid) {
        integrityBanner.style.background = "var(--status-allow-bg)";
        integrityBanner.style.borderColor = "var(--status-allow-border)";
        integrityIcon.textContent = "✅";
        integrityTitle.textContent = `SHA-256 Chain Verified (${res.total_records} records)`;
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
  });

  btnRefreshAudit.addEventListener("click", () => {
    loadAuditRecords();
  });

  // Form Submit: Evaluate Policy Gate
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    btnSubmit.disabled = true;
    btnSubmit.innerHTML = "<span>⏳</span> Evaluating Deterministic Policy...";

    const payload = {
      action_id: inputActionId.value.trim(),
      action_type: inputActionType.value,
      target: inputTarget.value.trim(),
      value_wei: parseInt(inputValueWei.value || "0", 10),
      data: inputCalldata.value.trim() || "0x",
      timestamp: inputTimestamp.value ? parseInt(inputTimestamp.value, 10) : null,
      description: inputDescription.value.trim(),
      metadata: { source: "web_dashboard" }
    };

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

      // Refresh audit ledger automatically after check
      loadAuditRecords();
    } catch (err) {
      alert(`Evaluation request error: ${err.message}`);
    } finally {
      btnSubmit.disabled = false;
      btnSubmit.innerHTML = '<span class="btn-icon">🛡️</span> Evaluate Policy Gate';
    }
  });

  function renderDecision(decision) {
    const isAllow = decision.outcome === "ALLOW";

    // Update Verdict Pill
    verdictPill.className = `verdict-pill ${isAllow ? "allow" : "deny"}`;
    verdictPill.textContent = decision.outcome;

    // Update Verdict Banner
    verdictBanner.className = `verdict-banner ${isAllow ? "allow" : "deny"}`;
    verdictTitle.textContent = isAllow ? "Action Authorized by Policy" : "Action Blocked by Gatekeeper";
    verdictReason.textContent = decision.reason;

    // Update Meta Items
    metaDecidingRule.textContent = decision.deciding_rule_id;
    metaRuleType.textContent = decision.deciding_rule_type;
    metaDecisionId.textContent = decision.decision_id;

    // Render Rule Traces
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
      ruleTracesList.innerHTML = `<div class="empty-state">No individual rule traces returned.</div>`;
    }
  }

  // Initial Load
  loadStatus();
  loadAuditRecords();
});
