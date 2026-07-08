/**
 * background.js (MV3 service worker)
 * ===================================
 * The only part of the extension that talks to the network. Content
 * scripts run inside the page's isolated world and can be blocked by
 * page CSP; this service worker is not.
 */

const DEFAULT_SETTINGS = {
  apiBaseUrl: "http://localhost:8000",
  apiKey: "",
  enabled: true,
};

async function getSettings() {
  const stored = await chrome.storage.sync.get(DEFAULT_SETTINGS);
  return { ...DEFAULT_SETTINGS, ...stored };
}

async function scanFile(file) {
  const settings = await getSettings();
  if (!settings.enabled) {
    return { verdict: "ALLOW", reason: "एक्सटेंशन अभी बंद है" };
  }

  const formData = new FormData();
  formData.append("file", file, file.name);

  let response;
  try {
    response = await fetch(`${settings.apiBaseUrl}/v1/scan`, {
      method: "POST",
      headers: { "X-API-Key": settings.apiKey },
      body: formData,
    });
  } catch (networkErr) {
    await flagDegradedMode(`API से कनेक्ट नहीं हो सका: ${networkErr.message}`);
    // FIX: was "ALLOW" (fail-open) — any network/CORS problem silently
    // let every upload through with no blocking at all. Now fails
    // CLOSED to "WARN" so the user gets an explicit prompt instead.
    return { verdict: "WARN", reason: "स्कैनर अनुपलब्ध — जाँच नहीं हो पाई, सावधानी से आगे बढ़ें", degraded: true };
  }

  if (!response.ok) {
    await flagDegradedMode(`स्कैनर ने HTTP ${response.status} लौटाया`);
    return { verdict: "WARN", reason: `स्कैनर त्रुटि (HTTP ${response.status}) — जाँच नहीं हो पाई, सावधानी से आगे बढ़ें`, degraded: true };
  }

  return response.json();
}

async function flagDegradedMode(message) {
  // Surfaced in the popup so the user is never silently unprotected —
  // a fail-open design must be visible, not invisible.
  await chrome.storage.local.set({ degraded: true, degradedMessage: message, degradedAt: Date.now() });
}

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message.type !== "AI_SDDS_SCAN_FILE") return;

  const { name, mimeType, buffer } = message.payload;
  const blob = new Blob([new Uint8Array(buffer)], { type: mimeType });
  const file = new File([blob], name, { type: mimeType });
  
  scanFile(file)
    .then(sendResponse)
    .catch((err) => sendResponse({ verdict: "WARN", reason: `स्कैनर त्रुटि: ${String(err)} — सावधानी से आगे बढ़ें`, degraded: true }));
  return true; // keep the message channel open for the async response
});
