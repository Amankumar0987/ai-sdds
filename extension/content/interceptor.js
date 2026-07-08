/**
 * interceptor.js
 * ==============
 * The hard problem this file solves: a browser will NOT let a content
 * script silently swap out a file the user picked — that's a deliberate
 * security boundary (you can't have a webpage secretly substitute the
 * file a user selected). So we can't "intercept and replace" — we can
 * only PAUSE the native event, scan the file out-of-band, and then
 * either:
 *   - re-dispatch a synthetic event carrying the SAME File object (ALLOW), or
 *   - clear the input / drop the event entirely (BLOCK).
 *
 * This module is deliberately dependency-free (no chrome.* APIs) so it
 * can run both inside a real content script AND inside a plain Node +
 * jsdom test, with `scanFile` and `ui` injected from the outside.
 *
 * Contract for the injected `scanFile(file)`:
 *   returns a Promise<{ verdict: "BLOCK" | "WARN" | "ALLOW", reason, ... }>
 *
 * Contract for the injected `ui`:
 *   showBlocked(file, verdict)         -> void
 *   showWarn(file, verdict)            -> Promise<boolean>  (true = proceed anyway)
 *   showAllowedBriefly(file)           -> void
 */
console.log("🛡 AI-SDDS Interceptor Loaded");
(function (root, factory) {
  if (typeof module !== "undefined" && module.exports) {
    module.exports = factory();
  } else {
    root.AISDDSInterceptor = factory();
  }
})(typeof window !== "undefined" ? window : globalThis, function () {

  function isFileInput(el) {
    return !!el && el.tagName === "INPUT" && el.type === "file";
  }

  function createInterceptor({ scanFile, ui }) {
    // Guards against re-intercepting the synthetic event we dispatch
    // ourselves when resuming an ALLOW/WARN-approved upload.
    let bypass = false;

    async function handleFiles(files, target) {
      for (const file of files) {
        let verdict;
        try {
          verdict = await scanFile(file);
        } catch (err) {
          // FIX: was fail-open to ALLOW, which meant a scanner outage
          // silently let every upload through with zero protection —
          // exactly the "blocking doesn't work" bug. We still don't
          // want to permanently jam uploads on every site, so we
          // fail-closed to WARN instead: the user sees a clear prompt
          // and must explicitly choose to proceed, rather than the
          // check silently disappearing. Surfaced to the user via the
          // popup's degraded-mode banner too (see background.js).
          verdict = { verdict: "WARN", reason: "स्कैनर अनुपलब्ध — जाँच नहीं हो पाई, सावधानी से आगे बढ़ें", degraded: true };
        }

        if (verdict.verdict === "BLOCK") {
          ui.showBlocked(file, verdict);
          if (isFileInput(target)) target.value = "";
          return false;
        }

        if (verdict.verdict === "WARN") {
          const proceed = await ui.showWarn(file, verdict);
          if (!proceed) {
            if (isFileInput(target)) target.value = "";
            return false;
          }
        } else {
          ui.showAllowedBriefly(file);
        }
      }
      resume(target, files);
      return true;
    }

    function resume(target, files) {
      const dt = new DataTransfer();
      for (const f of files) dt.items.add(f);

      bypass = true;
      try {
        if (isFileInput(target)) {
          target.files = dt.files;
          target.dispatchEvent(new Event("change", { bubbles: true }));
        } else {
          target.dispatchEvent(
            new DragEvent("drop", { bubbles: true, cancelable: true, dataTransfer: dt })
          );
        }
      } finally {
        bypass = false;
      }
    }

    function onChange(e) {
      if (bypass) return;
      const target = e.target;
      if (!isFileInput(target) || !target.files || target.files.length === 0) return;
      e.preventDefault();
      e.stopImmediatePropagation();
      handleFiles(Array.from(target.files), target);
    }

    function onDrop(e) {
      if (bypass) return;
      if (!e.dataTransfer || !e.dataTransfer.files || e.dataTransfer.files.length === 0) return;
      e.preventDefault();
      e.stopImmediatePropagation();
      handleFiles(Array.from(e.dataTransfer.files), e.target);
    }

    function onDragOver(e) {
      if (!bypass) e.preventDefault();
    }

    function attach(doc) {
      const d = doc || document;
      d.addEventListener("change", onChange, true);
      d.addEventListener("drop", onDrop, true);
      d.addEventListener("dragover", onDragOver, true);
    }

    function detach(doc) {
      const d = doc || document;
      d.removeEventListener("change", onChange, true);
      d.removeEventListener("drop", onDrop, true);
      d.removeEventListener("dragover", onDragOver, true);
    }

    return { attach, detach, _handleFiles: handleFiles };
  }

  return { createInterceptor };
});
