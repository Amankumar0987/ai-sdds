/**
 * interceptor.test.js
 * ===================
 * NOTE on the shims below: jsdom does not implement the native
 * DataTransfer / DragEvent APIs (this is a known, documented jsdom gap,
 * not a bug in interceptor.js). Real Chrome/Firefox/Edge implement
 * both fully. The shims here provide just enough behavior
 * (`items.add()`, `.files`) for interceptor.js's resume() logic to run
 * the same code path it would in a real browser.
 */
const test = require("node:test");
const assert = require("node:assert/strict");
const { JSDOM } = require("jsdom");
const { createInterceptor } = require("./interceptor.js");

function makeDom() {
  const dom = new JSDOM(
    `<!doctype html><body>
       <input type="file" id="fileInput" />
       <div id="dropZone"></div>
     </body>`,
    { url: "http://localhost/test-page.html" }
  );
  const { window } = dom;

  class FakeDataTransfer {
    constructor() { this._files = []; }
    get items() {
      const self = this;
      return { add(file) { self._files.push(file); } };
    }
    get files() {
      const arr = this._files.slice();
      arr.item = (i) => arr[i] ?? null;
      return arr;
    }
  }

  class FakeDragEvent extends window.Event {
    constructor(type, init = {}) {
      super(type, init);
      this.dataTransfer = init.dataTransfer || null;
    }
  }

  global.window = window;
  global.document = window.document;
  global.Event = window.Event;
  global.File = window.File;
  global.DataTransfer = FakeDataTransfer;
  global.DragEvent = FakeDragEvent;

  return window;
}

function makeFile(name, content, type) {
  return new global.File([content], name, { type });
}

test("BLOCK: site's own change handler never fires, input is cleared", async () => {
  const window = makeDom();
  const input = window.document.getElementById("fileInput");

  let siteHandlerFired = false;
  input.addEventListener("change", () => { siteHandlerFired = true; });

  const ui = {
    showBlocked: () => {},
    showWarn: async () => true,
    showAllowedBriefly: () => {},
  };
  const scanFile = async () => ({ verdict: "BLOCK", reason: "test" });

  const interceptor = createInterceptor({ scanFile, ui });
  interceptor.attach(window.document);

  const file = makeFile("aadhaar.png", "fake-bytes", "image/png");
  const dt = new global.DataTransfer();
  dt.items.add(file);
  Object.defineProperty(input, "files", { value: dt.files, configurable: true });

  input.dispatchEvent(new window.Event("change", { bubbles: true }));
  await new Promise((r) => setTimeout(r, 10)); // let the async handler resolve

  assert.equal(siteHandlerFired, false, "site handler must NOT see a blocked file");
  assert.equal(input.value, "");
});

test("ALLOW: site's own change handler DOES fire, receives the same file", async () => {
  const window = makeDom();
  const input = window.document.getElementById("fileInput");

  let receivedFileName = null;
  input.addEventListener("change", (e) => {
    receivedFileName = e.target.files[0] && e.target.files[0].name;
  });

  const ui = {
    showBlocked: () => {},
    showWarn: async () => true,
    showAllowedBriefly: () => {},
  };
  const scanFile = async () => ({ verdict: "ALLOW", reason: "safe" });

  const interceptor = createInterceptor({ scanFile, ui });
  interceptor.attach(window.document);

  const file = makeFile("resume.pdf", "fake-bytes", "application/pdf");
  const dt = new global.DataTransfer();
  dt.items.add(file);
  Object.defineProperty(input, "files", { value: dt.files, configurable: true });

  input.dispatchEvent(new window.Event("change", { bubbles: true }));
  await new Promise((r) => setTimeout(r, 10));

  assert.equal(receivedFileName, "resume.pdf", "site handler must receive the allowed file");
});

test("WARN + user cancels: site handler never fires", async () => {
  const window = makeDom();
  const input = window.document.getElementById("fileInput");

  let siteHandlerFired = false;
  input.addEventListener("change", () => { siteHandlerFired = true; });

  const ui = {
    showBlocked: () => {},
    showWarn: async () => false, // user clicks "Cancel"
    showAllowedBriefly: () => {},
  };
  const scanFile = async () => ({ verdict: "WARN", reason: "possible PII" });

  const interceptor = createInterceptor({ scanFile, ui });
  interceptor.attach(window.document);

  const file = makeFile("maybe-sensitive.jpg", "fake-bytes", "image/jpeg");
  const dt = new global.DataTransfer();
  dt.items.add(file);
  Object.defineProperty(input, "files", { value: dt.files, configurable: true });

  input.dispatchEvent(new window.Event("change", { bubbles: true }));
  await new Promise((r) => setTimeout(r, 10));

  assert.equal(siteHandlerFired, false);
});

test("scanner failure fails CLOSED to a WARN prompt (not silent ALLOW) and does not permanently jam uploads when user proceeds", async () => {
  const window = makeDom();
  const input = window.document.getElementById("fileInput");

  let siteHandlerFired = false;
  input.addEventListener("change", () => { siteHandlerFired = true; });

  let warnedWith = null;
  const ui = {
    showBlocked: () => {},
    showWarn: async (file, verdict) => { warnedWith = verdict; return true; },
    showAllowedBriefly: () => {},
  };
  const scanFile = async () => { throw new Error("network down"); };

  const interceptor = createInterceptor({ scanFile, ui });
  interceptor.attach(window.document);

  const file = makeFile("doc.png", "fake-bytes", "image/png");
  const dt = new global.DataTransfer();
  dt.items.add(file);
  Object.defineProperty(input, "files", { value: dt.files, configurable: true });

  input.dispatchEvent(new window.Event("change", { bubbles: true }));
  await new Promise((r) => setTimeout(r, 10));

  assert.equal(warnedWith?.verdict, "WARN", "a scanner outage must surface a WARN prompt, not silently ALLOW");
  assert.equal(siteHandlerFired, true, "once the user explicitly confirms, the upload should still go through — not be jammed forever");
});

test("scanner failure fails CLOSED: if the user declines the WARN prompt, the upload does NOT proceed", async () => {
  const window = makeDom();
  const input = window.document.getElementById("fileInput");

  let siteHandlerFired = false;
  input.addEventListener("change", () => { siteHandlerFired = true; });

  const ui = { showBlocked: () => {}, showWarn: async () => false, showAllowedBriefly: () => {} };
  const scanFile = async () => { throw new Error("network down"); };

  const interceptor = createInterceptor({ scanFile, ui });
  interceptor.attach(window.document);

  const file = makeFile("doc.png", "fake-bytes", "image/png");
  const dt = new global.DataTransfer();
  dt.items.add(file);
  Object.defineProperty(input, "files", { value: dt.files, configurable: true });

  input.dispatchEvent(new window.Event("change", { bubbles: true }));
  await new Promise((r) => setTimeout(r, 10));

  assert.equal(siteHandlerFired, false, "declining the warn prompt on a scanner outage must NOT let the upload through");
});
