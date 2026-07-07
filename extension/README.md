# AI-SDDS — Browser Extension (Manifest V3)

API (Phase 4 का backend हिस्सा) पर बना यह extension किसी भी AI चैट
साइट पर फ़ाइल अपलोड को इंटरसेप्ट करता है, स्कैन करता है, और संवेदनशील
पाए जाने पर रोकता है।

## क्यों यह मुश्किल है (और हमने कैसे हल किया)

ब्राउज़र की सुरक्षा नीति किसी वेबसाइट या एक्सटेंशन को **चुपके से** किसी
file input की फ़ाइल को बदलने नहीं देती — यह जानबूझकर एक सुरक्षा सीमा है।
तो "रोको और बदलो" संभव नहीं; जो संभव है वह है **"रोको, स्कैन करो, फिर
वही असली फ़ाइल आगे भेजो (resume)"**:

1. हम capture-phase में `change`/`drop` event को सबसे पहले पकड़ते हैं
   (साइट के अपने JS से पहले) और `stopImmediatePropagation()` से उसे रोक देते हैं।
2. फ़ाइल को background service worker के ज़रिए API पर स्कैन भेजते हैं।
3. **BLOCK** → input खाली कर देते हैं, साइट को फ़ाइल कभी नहीं दिखती।
4. **ALLOW/WARN-स्वीकृत** → एक नया `DataTransfer` बनाकर उसी File object
   के साथ एक synthetic event फिर से dispatch करते हैं — अब साइट का अपना
   handler सामान्य रूप से चलता है, जैसे कुछ हुआ ही न हो।

यह तर्क पूरी तरह **`content/interceptor.js`** में है और chrome.* API पर
निर्भर नहीं करता — इसलिए इसे बिना browser के jsdom से टेस्ट किया जा सकता है:

```bash
cd extension
npm install
npm test
```

(jsdom असली Drag-and-Drop API को implement नहीं करता — टेस्ट फ़ाइल में
एक छोटा सा documented shim है। असली Chrome में native API पूरी तरह काम
करता है।)

## Chrome में लोड करना

1. `chrome://extensions` खोलें, "Developer mode" चालू करें
2. "Load unpacked" → इस `extension/` फ़ोल्डर को चुनें
3. एक्सटेंशन आइकन पर क्लिक करें → API सर्वर पता और API key भरें
   (अगर आपने पहले Core API को `uvicorn` से चलाया है, default
   `http://localhost:8000` ठीक रहेगा)

## बिना असली AI साइट खोले टेस्ट करना

`extension/test-page.html` को Chrome में खोलें (या extension को
`file:///*` पर भी match किया गया है)। यह पेज एक नकली "साइट हैंडलर"
चलाता है ताकि आप देख सकें कि:
- संवेदनशील फ़ाइल पर साइट का अपना handler **कभी नहीं चलता**
- सुरक्षित फ़ाइल पर वह **सामान्य रूप से चलता है**

## Fail-open डिज़ाइन (ज़रूरी सुरक्षा निर्णय)

अगर API सर्वर बंद है या नेटवर्क fail हो जाए, तो extension उस फ़ाइल को
**अनुमति दे देता है** (ब्लॉक नहीं करता) — एक स्कैनर का आउटेज उपयोगकर्ता
के काम को हमेशा के लिए नहीं रोक सकता। लेकिन यह *चुपचाप* नहीं होता:
popup में एक "⚠ degraded mode" चेतावनी तुरंत दिखती है जब तक सर्वर ठीक न
हो जाए। (देखें `background.js` → `flagDegradedMode`)

## फ़ाइलें

| फ़ाइल | काम |
|---|---|
| `content/interceptor.js` | Core intercept→scan→resume लॉजिक, framework-agnostic, यूनिट-टेस्टेड |
| `content/content-script.js` | असली पेज पर चलता है, Shadow DOM UI दिखाता है |
| `background.js` | API को असली network कॉल, fail-open लॉजिक |
| `popup/` | सेटिंग्स (API पता, key, on/off, degraded-mode चेतावनी) |
| `test-page.html` | असली AI साइट खोले बिना मैनुअल टेस्टिंग |

## ज्ञात सीमाएँ

- अभी केवल 4 प्रमुख AI साइट्स + localhost पर सक्रिय (manifest में
  `host_permissions`/`matches`) — नई साइट जोड़ने के लिए manifest.json
  में domain जोड़ें।
- File→ArrayBuffer→वापस File का conversion बड़ी फ़ाइलों (>10MB) पर थोड़ा
  धीमा हो सकता है; Phase 5 में streaming उपयोग पर विचार करें।
- Icons अभी placeholder हैं — असली ब्रांडिंग से बदलें।
