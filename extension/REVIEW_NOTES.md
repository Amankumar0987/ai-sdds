# Browser Extension — Review Notes (इस पास में क्या ठीक हुआ)

Aman के भेजे गए बदलावों की समीक्षा के बाद ये fixes लगाए गए — हर एक को
असली browser (Playwright + Chromium) से end-to-end वेरीफाई किया गया,
सिर्फ़ कोड पढ़कर अंदाज़ा नहीं लगाया।

## 🔴 Critical fixes
1. **Hardcoded API key (`GSBHDFHDRGC457`) हटाई** — यह `config.py`,
   `background.js`, `tests/test_api.py`, और `.env.example` चार जगह
   default value के रूप में फैल गई थी। चूँकि यह zip में existing थी,
   इसे leaked माना जाना चाहिए — **अपने production deployment में
   एक नई, असली random key generate करें**, इसे कहीं reuse न करें।
2. **Secret-logging हटाया** — `api/app.py` में `print(API_KEYS)` और
   `background.js` में `console.log(apiKey)` दोनों हटाए। API key अब
   कभी server logs या browser devtools में plaintext नहीं दिखती।
3. **Windows hardcoded tesseract path हटाया** — अब
   `AI_SDDS_TESSERACT_CMD` env var से (वैकल्पिक) — Linux/Mac/Docker पर
   खाली छोड़ने पर अपने-आप PATH से मिल जाता है।

## 🟠 High fixes
4. **Async-listener race condition ठीक की** (`engine/upload-engine.js`)
   — `preventDefault()`/`stopImmediatePropagation()` अब `await` से
   **पहले**, synchronously call होते हैं। jsdom से प्रूव किया गया था कि
   पुराना pattern साइट के handler को रोकने में पूरी तरह विफल था।
5. **popup.html/popup.js sync किए** — popup.js नए
   backend-status/history/stats elements इस्तेमाल कर रहा था जो
   popup.html में मौजूद ही नहीं थे। दोनों फ़ाइलें अब मेल खाती हैं,
   और एक डुप्लिकेट `load()` function था जिसे merge किया।
6. **`RiskEngine` और `ScanHistory` को असल में wire किया** —
   पहले ये classes सिर्फ़ define थीं, कहीं instantiate नहीं हो रही थीं।
   अब `content-script.js` हर scan पर दोनों इस्तेमाल करता है — popup के
   जोखिम-स्कोर बैनर और scan-history दोनों अब असल डेटा से भरते हैं
   (Playwright से वेरीफाई: BLOCK पर "जोखिम स्कोर: 100/100 (HIGH)",
   WARN पर "60/100 (MEDIUM)" सही दिखा)।

## 🟡 Medium fixes
7. `python-dotenv` को `requirements.txt` में जोड़ा (कोड में इस्तेमाल हो
   रहा था, पर dependency list में missing था)।
8. CORS की malformed entry (`http://localhost:8000/scan` — origin में
   कभी path नहीं होता) हटाई।
9. `background.js` में `getSettings()` का duplicate call हटाया।

## ⚠️ अभी भी अधूरा/पार्किंग में (जानबूझकर छुआ नहीं)
- `engine/scanner.js`, `engine/upload-engine.js`, `adapters/chatgpt.js`
  अभी **manifest.json में load नहीं हैं** — ये एक parallel,
  per-site-adapter-friendly architecture का शुरुआती हिस्सा लगते हैं।
  सक्रिय, टेस्टेड path अभी भी `content/interceptor.js` है। दोनों को
  एक साथ load करना double-scanning/conflicting-resume का खतरा रखता है
  — इसलिए जानबूझकर अलग रखा। अगर आप `UploadEngine`-आधारित
  per-site-adapter approach पर माइग्रेट करना चाहें (`ChatGPTAdapter`
  जैसे adapters का मतलब यही लगता है), बताइए — मैं उसे ठीक से,
  टेस्ट करके migrate कर सकता हूँ, पर अभी दोनों सिस्टम साथ रखना खतरनाक है।
- `cryptography==46.0.7` में एक Moderate CVE है, patch (`48.0.1`)
  `flwr`(Phase 3) के अपने pin से ब्लॉक है — स्कोप सीमित है FL simulation
  tooling तक, production API प्रभावित नहीं। देखें `SECURITY_CHECKLIST.md`।

## वेरिफिकेशन का तरीका
हर दावे को इनमें से किसी एक तरीके से वास्तव में चलाकर साबित किया गया:
- `python -m pytest tests/` — 51 passed
- `npm test` (extension) — 4 passed
- Playwright से असली Chromium में extension load करके — BLOCK, WARN
  (फिर "फिर भी अपलोड करें" क्लिक करके resume), और ALLOW तीनों verdicts
  असली local API सर्वर के साथ end-to-end चलाकर देखे गए।
