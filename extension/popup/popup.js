const DEFAULT_SETTINGS = { apiBaseUrl: "http://localhost:8000", apiKey: "", enabled: true };

async function load() {
  const settings = await chrome.storage.sync.get(DEFAULT_SETTINGS);
  document.getElementById("enabled").checked = settings.enabled;
  document.getElementById("apiBaseUrl").value = settings.apiBaseUrl;
  document.getElementById("apiKey").value = settings.apiKey;

  const { degraded, degradedMessage } = await chrome.storage.local.get(["degraded", "degradedMessage"]);
  const banner = document.getElementById("degradedBanner");
  if (degraded) {
    banner.textContent = `⚠ ${degradedMessage || "स्कैनर अनुपलब्ध"}`;
    banner.classList.remove("hidden");
  }

  await refreshBackendStatus(settings.apiBaseUrl);
  await refreshHistorySummary();
}

async function refreshBackendStatus(apiBaseUrl) {
  const statusText = document.getElementById("backendStatus");
  const dot = document.getElementById("statusDot");
  try {
    const res = await fetch(`${apiBaseUrl}/v1/health`);
    const ok = res.ok;
    statusText.textContent = ok ? "जुड़ा हुआ" : "ऑफ़लाइन";
    dot.style.background = ok ? "#22c55e" : "#dc2626";
  } catch {
    statusText.textContent = "ऑफ़लाइन";
    dot.style.background = "#dc2626";
  }
}

async function refreshHistorySummary() {
  const data = await chrome.storage.local.get("ai_sdds_history");
  const history = data.ai_sdds_history || [];

  let blocked = 0;
  let warned = 0;
  for (const entry of history) {
    if (entry.verdict === "BLOCK") blocked++;
    if (entry.verdict === "WARN") warned++;
  }

  document.getElementById("scanCount").textContent = history.length;
  document.getElementById("blockedCount").textContent = blocked;
  document.getElementById("warnCount").textContent = warned;

  const list = document.getElementById("history");
  list.innerHTML = "";
  for (const entry of history.slice(0, 5)) {
    const row = document.createElement("div");
    row.className = "history-row";
    row.innerHTML = `<b>${entry.file}</b><span class="verdict-${entry.verdict}">${entry.verdict}</span>`;
    list.appendChild(row);
  }
}

async function save() {
  await chrome.storage.sync.set({
    enabled: document.getElementById("enabled").checked,
    apiBaseUrl: document.getElementById("apiBaseUrl").value.trim() || DEFAULT_SETTINGS.apiBaseUrl,
    apiKey: document.getElementById("apiKey").value,
  });
  await chrome.storage.local.remove(["degraded", "degradedMessage"]);
  const status = document.getElementById("status");
  status.textContent = "सेव हो गया";
  setTimeout(() => { status.textContent = ""; }, 1500);
}

document.addEventListener("DOMContentLoaded", load);
document.getElementById("save").addEventListener("click", save);
