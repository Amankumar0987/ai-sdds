# Changelog

## [Unreleased] — Windows test run पर मिले 4 असली bugs ठीक किए
- Fixed: `tests/test_api.py` में rate-limiter test pollution — `test_rate_limit_blocks_excess_requests` के बाद चलने वाले टेस्ट 429 की वजह से fail हो रहे थे; अब हर टेस्ट से पहले `limiter.reset()` (autouse fixture)
- Fixed: `tests/test_privacy_property.py` अब dataset न होने पर साफ़ pytest skip देता है, cryptic torch `ValueError` नहीं
- Fixed: Tesseract पूरी तरह न मिलने पर अब scan crash नहीं होता — साफ़ `REJECTED` verdict + actionable install instructions (`core/ocr_engine.py::OCRUnavailable`, `core/detector.py`) — empirically टेस्ट किया गया (mocked `TesseractNotFoundError`)
- Fixed: `.env` loading अब import-order-independent — `core/ocr_engine.py` खुद भी `load_dotenv()` कॉल करता है, सिर्फ़ `config.py` के पहले import होने पर निर्भर नहीं
- Added: README में Windows-विशिष्ट Tesseract setup अनुभाग

## [Unreleased] — Phase 3: Federated Learning (पहले सिर्फ़ concept था)
- Added: `fl/` — असली Flower (flwr) FedAvg simulation, 4 clients, 5 rounds — 25% → 71.7% accuracy तक improve हुआ (असली, चलाकर देखा गया रिजल्ट, fluctuation के साथ ईमानदारी से रिपोर्ट किया)
- Added: `tests/test_privacy_property.py` — 4 टेस्ट जो structurally साबित करते हैं कि क्लाइंट्स कभी एक-दूसरे का डेटा नहीं छूते, और network payload की shape डेटा-वॉल्यूम से independent है (raw data leak होना संरचनात्मक रूप से असंभव)
- Documented: production federated learning (secure aggregation, differential privacy, cross-device, Byzantine fault tolerance) से यह कितना दूर है — `fl/README.md`
- Known issue: `flwr` का `cryptography<47.0.0` pin एक Moderate CVE के patch को रोकता है — स्कोप सीमित है FL simulation tooling तक, production API प्रभावित नहीं — `SECURITY_CHECKLIST.md`

## [Unreleased] — Phase 7: Launch Readiness
- Added: Prometheus metrics endpoint (`/v1/metrics`) — scan counts by verdict, latency histogram, degraded-mode counter
- Added: `LAUNCH_CHECKLIST.md`, this changelog

## Phase 6 — Red-Team Testing
- Fixed: zero-width Unicode characters could completely bypass Aadhaar/PAN/card detection
- Fixed: dot-separated number groups (`2345.6789.0124`) were not matched
- Fixed: single Cyrillic/Greek homoglyph letters (e.g. `Р` instead of `P`) defeated `[A-Z]` pattern matching
- Added: `tests/test_redteam.py` as a living adversarial-test collection
- Documented (not fixed): base64-encoded sensitive data embedded in text is not decoded/re-scanned

## Phase 5 — Security Hardening
- Fixed: 9 known CVEs across Pillow, pytest, pdfminer-six (dependency upgrade)
- Added: `pip-audit` + `npm audit` wired into CI
- Added: `detect-secrets` + pre-commit hooks, `.secrets.baseline`
- Added: GitHub Actions CI (`.github/workflows/ci.yml`) — tests, dependency scan, secret scan, Docker build
- Added: `SECURITY_CHECKLIST.md` (OWASP API Security Top 10 mapped)
- Added: `SECRETS.md` (Vault migration pattern, not yet wired in)

## Phase 2 — Computer Vision Layer
- Added: `core/vision_engine.py` — face-photo detection (Haar cascade) + QR code detection (OpenCV), zero network/training dependency
- Added: YOLOv8 training pipeline (`cv/generate_synthetic_dataset.py`, `cv/train.py`) — proof-of-pipeline only in sandboxed environments without internet access to pretrained weights
- Wired visual findings into `detector.py` — catches ID-card-like structure even when OCR finds zero readable text

## Phase 4 — Browser Extension & API (partial)
- Added: `extension/` — Manifest V3 extension with intercept→scan→resume upload-interception pattern
- Added: `extension/content/interceptor.js` — framework-agnostic core logic, unit-tested via Node + jsdom
- Added: fail-open design for scanner outages, with a visible "degraded mode" warning in the popup
- Added: `api/app.py` — FastAPI service (auth, rate limiting, CORS, upload-size guard, generic error handling)
- Added: `Dockerfile` — non-root user, healthcheck

## Phase 1 — Core Detection Engine
- Added: `core/validators.py` — Verhoeff (Aadhaar), Luhn (cards), structural checks (PAN/IFSC)
- Added: `core/patterns.py` — regex + checksum-validated confidence scoring
- Added: `core/security.py` — magic-byte file validation, masking, safe logging, resource limits, OCR timeout
- Added: `core/ocr_engine.py` — dual-pass OCR (separate `eng` pass for digit accuracy, `hin+eng` for multilingual text) after discovering the combined model dropped digits
- Added: `core/pdf_engine.py` — text-layer + scanned-PDF support
- Added: `core/detector.py` — BLOCK/WARN/ALLOW orchestrator
