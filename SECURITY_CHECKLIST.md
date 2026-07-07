# Penetration-Testing Checklist — AI-SDDS

OWASP API Security Top 10 (2023) के हिसाब से structured। हर item पर
स्थिति: ✅ कोड में cover है (फ़ाइल/टेस्ट के साथ) | 🔲 launch से पहले
manual verification चाहिए | ➖ इस फ़ेज़ में लागू नहीं।

## API1: Broken Object Level Authorization
- ➖ कोई per-object access control नहीं है (कोई "documents" स्टोर नहीं होते, इसलिए कोई object ownership model नहीं)।

## API2: Broken Authentication
- ✅ `X-API-Key` हर `/v1/scan` कॉल पर ज़रूरी — `api/auth.py`, टेस्ट: `test_scan_without_api_key_is_rejected`
- ✅ Key न होने पर server secure-by-default (auto-generated, कभी "wide open" नहीं) — `api/app.py::lifespan`
- 🔲 असली production में shared-secret key के बजाय OAuth2/JWT पर माइग्रेट करें (multi-tenant उपयोग के लिए)
- 🔲 API key rotation policy दस्तावेज़ित करें और लागू करें

## API3: Broken Object Property Level Authorization
- ➖ लागू नहीं (कोई partial-field response/update endpoint नहीं)

## API4: Unrestricted Resource Consumption
- ✅ फ़ाइल आकार सीमा (15MB) — request body पढ़ने से पहले `Content-Length` हेडर पर ही चेक — `api/app.py::limit_upload_size`, टेस्ट: `test_oversized_upload_rejected_via_content_length`
- ✅ Image pixel-count cap (decompression bomb से बचाव) — `security.py::MAX_IMAGE_PIXELS`
- ✅ PDF page-count cap — `pdf_engine.py::MAX_PDF_PAGES`
- ✅ OCR hard timeout (हैंग होने से बचाव) — `security.py::run_with_timeout`
- ✅ Per-IP rate limiting — `slowapi`, टेस्ट: `test_rate_limit_blocks_excess_requests`
- 🔲 Load test करें: 100+ concurrent बड़ी फ़ाइलें — memory/CPU सीमा पर वास्तविक व्यवहार जाँचें

## API5: Broken Function Level Authorization
- ➖ अभी सिर्फ़ एक endpoint role है (scan) — भविष्य में admin endpoints जोड़ें तो अलग role चाहिए होगा

## API6: Unrestricted Access to Sensitive Business Flows
- ✅ Rate limiting अप्रत्यक्ष रूप से automation/scraping को धीमा करता है
- 🔲 असामान्य उपयोग pattern (एक ही key से अचानक 1000x ट्रैफ़िक) पर अलर्ट जोड़ें

## API7: Server-Side Request Forgery (SSRF)
- ✅ यह API कोई भी उपयोगकर्ता-दी गई URL कभी fetch नहीं करती (सिर्फ़ uploaded bytes लेती है) — SSRF का यह सबसे सामान्य रास्ता structurally बंद है
- 🔲 अगर भविष्य में "URL से दस्तावेज़ scan करें" फ़ीचर जोड़ें, तो तुरंत यह पूरा सेक्शन फिर से करें (private-IP/localhost block-list ज़रूरी होगी)

## API8: Security Misconfiguration
- ✅ CORS डिफ़ॉल्ट रूप से बंद (`AI_SDDS_ALLOWED_ORIGINS` खाली = कोई cross-origin नहीं) — `api/app.py`
- ✅ Generic error handler — कोई stack trace caller को नहीं दिखता — `api/app.py::generic_exception_handler`
- ✅ Docker non-root user — `Dockerfile`
- ✅ Dependency scanning automated — `pip-audit`/`npm audit`, CI में wired (`.github/workflows/ci.yml`)
- ✅ Secret scanning pre-commit hook — `.pre-commit-config.yaml`, बेसलाइन: `.secrets.baseline`
- 🔲 **अनसुलझा known issue**: `flwr` (Phase 3, सिर्फ़ FL simulation में) `cryptography<47.0.0` pin करता है, जो `GHSA-537c-gmf6-5ccf` (CVE-2026-34180, Moderate, bundled OpenSSL में out-of-bounds read/DoS) के patched version (48.0.1) को रोकता है। **दायरा सीमित है** — यह transitive dependency सिर्फ़ `fl/` simulation tooling के रास्ते आता है, production API (`api/`, `core/`) इस पर निर्भर नहीं करता। जब upstream `flwr` अपना pin अपडेट करे, तुरंत अपग्रेड करें — तब तक `fl/` को production नेटवर्क पर expose न करें।
- 🔲 TLS termination सेटअप करें (इस repo में सिर्फ़ plain HTTP है — production में nginx/Caddy/cloud LB से TLS लगाएँ)
- 🔲 Security headers (HSTS, X-Content-Type-Options, CSP) reverse-proxy स्तर पर जोड़ें

## API9: Improper Inventory Management
- 🔲 API versioning स्ट्रैटेजी दस्तावेज़ित करें (अभी `/v1/` prefix है, पर deprecation policy नहीं लिखी)
- 🔲 कौन-कौन से environments (staging/prod) चल रहे हैं, उसकी inventory रखें

## API10: Unsafe Consumption of APIs
- ➖ यह सेवा खुद किसी तीसरे-पक्ष API को कॉल नहीं करती

---

## अतिरिक्त — File-Upload-विशिष्ट हमले (OWASP से अलग, पर इस प्रोजेक्ट के लिए ज़रूरी)

- ✅ Magic-byte MIME sniffing (फ़ाइल extension पर भरोसा नहीं) — टेस्ट: `test_validate_file_rejects_fake_extension_attack`
- ✅ Polyglot/zip-bomb से बचाव — pixel cap + size cap + PDF page cap
- ✅ Adversarial text evasion (zero-width characters, dot separators, RTL overrides, Cyrillic homoglyphs) — टेस्ट: `tests/test_redteam.py`, `tests/test_patterns.py`
- 🔲 Base64-encoded sensitive data embedded in text is not decoded/re-scanned — documented gap, टेस्ट: `test_KNOWN_GAP_base64_encoded_number_is_not_decoded` (out of scope for image/PDF-focused product; revisit if a "paste text" input is ever added)
- 🔲 Polyglot PDF (PDF के अंदर embedded JavaScript/launch actions) — अभी सिर्फ़ टेक्स्ट/इमेज एक्सट्रैक्ट होता है, JS कभी execute नहीं होता (pdfplumber JS नहीं चलाता), पर explicitly एक टेस्ट केस के साथ पुष्टि करें
- 🔲 EXIF metadata में छुपी जानकारी (GPS coordinates आदि) — अभी सिर्फ़ visible pixel content scan होता है, EXIF स्कैन नहीं होता

## Browser Extension–विशिष्ट

- ✅ Fail-open डिज़ाइन (scanner डाउन होने पर uploads हमेशा के लिए जाम नहीं होते) — टेस्ट: `test_zero_width...` नहीं, बल्कि `interceptor.test.js::scanner failure fails open`
- ✅ Shadow DOM isolation (host page का CSS/JS हमारी UI को छेड़ नहीं सकता)
- 🔲 Content Security Policy की समीक्षा करें अगर किसी AI साइट का अपना strict CSP हमारे injected UI को block करे
- 🔲 Manifest `host_permissions` को नियमित रूप से ऑडिट करें — सिर्फ़ ज़रूरी domains जोड़ें (least privilege)

---

## इसे कैसे इस्तेमाल करें

लॉन्च से पहले हर 🔲 item को या तो:
1. ठीक करें और ✅ में बदलें, या
2. एक स्वीकृत जोखिम के रूप में दस्तावेज़ित करें (कौन approve किया, कब, क्यों)।

यह checklist एक living document है — हर नए feature के साथ इसे फिर से देखें।
