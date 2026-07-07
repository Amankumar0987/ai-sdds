/**
 * engine/upload-engine.js
 *
 * ⚠️ NOT CURRENTLY ACTIVE. content/interceptor.js is the tested,
 * wired-up interception engine (see manifest.json + content-script.js).
 * This file is kept as an alternate, per-site-adapter-friendly
 * implementation for future use — do not `attach()` this at the same
 * time as interceptor.js; running both on the same document would
 * double-scan every file and risk conflicting resume logic.
 *
 * IMPORTANT FIX (found during review): a capture-phase event listener
 * that is declared `async` cannot block the event by calling
 * preventDefault()/stopImmediatePropagation() AFTER an `await` — by
 * the time the awaited Promise resolves, the browser has already
 * finished dispatching the event to every other listener (including
 * the site's own upload handler). The fix is the same pattern used in
 * interceptor.js: synchronously call preventDefault/stopImmediatePropagation
 * FIRST, then do the async scan-and-resume work separately.
 */
class UploadEngine {
    constructor(scanCallback, ui) {
        this.scan = scanCallback;
        this.ui = ui;
    }

    async processFiles(files, source) {
        const list = Array.from(files);

        for (const file of list) {
            const result = await this.scan(file);

            switch (result.verdict) {

                case "BLOCK":
                    this.ui.showBlocked(file, result);
                    return false;

                case "WARN": {
                    const allow = await this.ui.showWarn(file, result);
                    if (!allow) return false;
                    break;
                }

                case "ALLOW":
                default:
                    this.ui.showAllowedBriefly(file);
            }
        }

        return true;
    }

    /** Re-dispatches the same File objects via a fresh DataTransfer —
     * the only way to legitimately resume an upload after pausing it
     * (see content/interceptor.js's resume() for the original pattern
     * this mirrors). */
    resume(target, files, eventType) {
        const dt = new DataTransfer();
        for (const f of files) dt.items.add(f);

        if (target instanceof HTMLInputElement) {
            target.files = dt.files;
            target.dispatchEvent(new Event("change", { bubbles: true }));
        } else {
            target.dispatchEvent(new DragEvent("drop", { bubbles: true, cancelable: true, dataTransfer: dt }));
        }
    }

    attach(root = document) {
        let bypass = false;

        // File picker
        root.addEventListener(
            "change",
            (e) => {
                if (bypass) return;
                const input = e.target;
                if (!(input instanceof HTMLInputElement) || input.type !== "file") return;
                if (!input.files || input.files.length === 0) return;

                // CRITICAL: stop the event SYNCHRONOUSLY, before any await.
                e.preventDefault();
                e.stopPropagation();
                e.stopImmediatePropagation();
                const files = Array.from(input.files);
                input.value = ""; // clear immediately; we'll resume() it if approved

                this.processFiles(files, "picker").then((ok) => {
                    if (ok) {
                        bypass = true;
                        try { this.resume(input, files); } finally { bypass = false; }
                    }
                });
            },
            true
        );

        // Drag & Drop
        root.addEventListener(
            "drop",
            (e) => {
                if (bypass) return;
                if (!e.dataTransfer || !e.dataTransfer.files || e.dataTransfer.files.length === 0) return;

                e.preventDefault();
                e.stopPropagation();
                e.stopImmediatePropagation();
                const files = Array.from(e.dataTransfer.files);
                const target = e.target;

                this.processFiles(files, "drop").then((ok) => {
                    if (ok) {
                        bypass = true;
                        try { this.resume(target, files); } finally { bypass = false; }
                    }
                });
            },
            true
        );

        // Paste — kept as block-only (no resume attempted: re-synthesizing
        // a paste event is unreliable across browsers, so on ALLOW we just
        // let the user paste again; this is documented, not a silent gap).
        root.addEventListener(
            "paste",
            (e) => {
                if (bypass) return;
                if (!e.clipboardData) return;

                const files = [];
                for (const item of e.clipboardData.items) {
                    if (item.kind === "file") {
                        const file = item.getAsFile();
                        if (file) files.push(file);
                    }
                }
                if (!files.length) return;

                e.preventDefault();
                e.stopPropagation();
                e.stopImmediatePropagation();

                this.processFiles(files, "paste");
                // No resume on ALLOW for paste — see comment above.
            },
            true
        );
    }
}

window.UploadEngine = UploadEngine;