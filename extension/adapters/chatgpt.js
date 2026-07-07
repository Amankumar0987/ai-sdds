/**
 * adapters/chatgpt.js
 *
 * ChatGPT adapter for AI-SDDS
 * - Detects ChatGPT pages
 * - Watches for dynamically added file inputs
 * - Hands discovered inputs to the UploadEngine
 */

class ChatGPTAdapter {
  constructor(uploadEngine) {
    this.engine = uploadEngine;
    this.started = false;
    this.observer = null;
  }

  isSupported() {
    return (
      location.hostname === "chatgpt.com" ||
      location.hostname === "chat.openai.com"
    );
  }

  start() {
    if (!this.isSupported() || this.started) return;

    this.started = true;

    // Attach the engine to the current document.
    this.engine.attach(document);

    // Watch for dynamically added DOM nodes so the extension
    // continues to work when ChatGPT updates its interface.
    this.observer = new MutationObserver(() => {
      // Future enhancement:
      // refresh UI bindings, update overlays, etc.
    });

    this.observer.observe(document.documentElement, {
      childList: true,
      subtree: true,
    });

    console.log("🛡 AI-SDDS ChatGPT adapter active");
  }

  stop() {
    this.observer?.disconnect();
    this.started = false;
  }
}

window.ChatGPTAdapter = ChatGPTAdapter;