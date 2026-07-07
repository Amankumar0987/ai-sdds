/**
 * content-script.js
 * =================
 * Runs on the actual AI platform page. Wires interceptor.js (already
 * loaded by manifest.json before this file) to:
 *   - a Shadow DOM UI (so our banner's CSS can never clash with, or be
 *     clashed by, the host page's CSS — and the host page's JS cannot
 *     reach into our DOM either)
 *   - background.js, which performs the actual network call to the
 *     scanning API (content scripts run in an isolated world but
 *     CSP on some sites still blocks their fetch() calls; the
 *     background service worker is not subject to page CSP)
 */
(function () {
  const HOST_ID = "ai-sdds-ui-host";

  function getShadowRoot() {
    let host = document.getElementById(HOST_ID);
    if (!host) {
      host = document.createElement("div");
      host.id = HOST_ID;
      host.style.position = "fixed";
      host.style.top = "16px";
      host.style.right = "16px";
      host.style.zIndex = "2147483647"; // above virtually anything the host page uses
      document.documentElement.appendChild(host);
      host.attachShadow({ mode: "open" });
      const style = document.createElement("style");
      style.textContent = `
        .card { font-family: system-ui, sans-serif; font-size: 13px; line-height: 1.4;
                max-width: 320px; border-radius: 8px; padding: 12px 14px; margin-bottom: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,.25); color: #fff; }
        .block { background: #a32d2d; }
        .warn  { background: #854f0b; }
        .allow { background: #27500a; }
        .title { font-weight: 600; margin-bottom: 4px; }
        .risk { font-size: 11px; opacity: 0.85; margin-top: 4px; }
        .row { display: flex; gap: 8px; margin-top: 8px; }
        button { cursor: pointer; border: none; border-radius: 4px; padding: 6px 10px; font-size: 12px; }
        .proceed { background: #fff; color: #a32d2d; }
        .cancel  { background: rgba(255,255,255,.15); color: #fff; }
      `;
      host.shadowRoot.appendChild(style);
    }
    return host.shadowRoot;
  }

  function showBlocked(file, verdict) {
    const root = getShadowRoot();
    const card = document.createElement("div");
    card.className = "card block";
    const riskLine = verdict.risk ? `<div class="risk">जोखिम स्कोर: ${verdict.risk.score}/100 (${verdict.risk.level})</div>` : "";
    card.innerHTML = `<div class="title">अपलोड ब्लॉक किया गया</div>
      <div>${file.name}: ${verdict.reason || "संवेदनशील जानकारी मिली"}</div>
      ${riskLine}`;
    root.appendChild(card);
    setTimeout(() => card.remove(), 6000);
  }

  function showAllowedBriefly(file) {
    const root = getShadowRoot();
    const card = document.createElement("div");
    card.className = "card allow";
    card.innerHTML = `<div class="title">सुरक्षित ✓</div><div>${file.name}</div>`;
    root.appendChild(card);
    setTimeout(() => card.remove(), 1500);
  }

  function showWarn(file, verdict) {
    return new Promise((resolve) => {
      const root = getShadowRoot();
      const card = document.createElement("div");
      card.className = "card warn";
      const riskLine = verdict.risk ? `<div class="risk">जोखिम स्कोर: ${verdict.risk.score}/100 (${verdict.risk.level})</div>` : "";
      card.innerHTML = `<div class="title">संभावित संवेदनशील जानकारी</div>
        <div>${file.name}: ${verdict.reason || ""}</div>
        ${riskLine}
        <div class="row">
          <button class="proceed">फिर भी अपलोड करें</button>
          <button class="cancel">रद्द करें</button>
        </div>`;
      root.appendChild(card);
      card.querySelector(".proceed").addEventListener("click", () => { card.remove(); resolve(true); });
      card.querySelector(".cancel").addEventListener("click", () => { card.remove(); resolve(false); });
    });
  }

  async function scanFileViaExtension(file) {
    const buffer = await file.arrayBuffer();
    const result = await chrome.runtime.sendMessage({
      type: "AI_SDDS_SCAN_FILE",
      payload: { name: file.name, mimeType: file.type, buffer: Array.from(new Uint8Array(buffer)) },
    });

    // RiskEngine (engine/risk-engine.js) turns a verdict into a 0-100
    // score for display; ScanHistory (engine/history.js) persists a
    // record so the popup's "स्कैन/ब्लॉक/चेतावनी" counters and recent-
    // history list have real data. Both are optional — if either
    // script failed to load for any reason, scanning still works.
    if (window.RiskEngine) {
      result.risk = new window.RiskEngine().calculate(result);
    }
    if (window.ScanHistory) {
      try {
        await new window.ScanHistory().add({
          fileName: file.name,
          verdict: result.verdict,
          findings: result.findings || [],
        });
      } catch (err) {
        // History is a convenience feature — never let a storage error
        // block the actual scan verdict from being honored.
        console.error("AI-SDDS: scan history को सेव नहीं किया जा सका", err);
      }
    }

    return result;
  }

  const ui = { showBlocked, showWarn, showAllowedBriefly };

  const interceptor = window.AISDDSInterceptor.createInterceptor({ scanFile: scanFileViaExtension, ui });
  interceptor.attach(document);
})();
