# AI-SDDS — Mobile App (Flutter)

## ⚠️ सबसे पहले यह पढ़ें — ईमानदार खुलासा

**यह कोड इस sandbox में कभी `flutter run`/`flutter test`/`dart analyze`
से नहीं चलाया गया** — यहाँ Flutter SDK install नहीं हो सकता (न तो यह
पहले से है, न network की allowlist में Flutter के डाउनलोड-सर्वर हैं)।

जो मैंने यहाँ वास्तव में किया:
- ✅ `pubspec.yaml` को असली YAML parser से validate किया
- ✅ हर `.dart` फ़ाइल में braces/parens का स्थूल balance-check किया
- ❌ **असली Dart compiler/analyzer से कभी नहीं चलाया गया** — यानी type
  errors, गलत import, या API mismatch (जैसे किसी package का गलत
  version इस्तेमाल करना) अभी भी संभव है

**आपको पहला असली काम यह करना है:**
```bash
flutter create ai_sdds_mobile
cd ai_sdds_mobile
# इस फ़ोल्डर का pubspec.yaml की dependencies सेक्शन कॉपी करें, फिर:
flutter pub get
# इस फ़ोल्डर का पूरा lib/ कॉपी करें (अपने नए प्रोजेक्ट के lib/ को overwrite करते हुए)
flutter analyze        # ← यहीं पर असली syntax/type errors दिखेंगे
flutter test           # अभी कोई टेस्ट फ़ाइल शामिल नहीं है (नीचे देखें)
flutter run
```

## आर्किटेक्चरल फ़ैसला: Mobile, Browser Extension जैसा "intercept" नहीं कर सकता

Browser extension एक वेबपेज के अंदर JavaScript event को capture कर
सकता है। **Mobile OS पर ऐसा संभव नहीं** — कोई भी app किसी दूसरे app
(जैसे ChatGPT app) के अंदर हो रहे file-picker को रोक नहीं सकता; यह
जानबूझकर एक OS-level सुरक्षा सीमा है (iOS और Android दोनों पर)।

इसलिए design अलग है — दो तरीके:

1. **Manual मोड**: सीधे यह app खोलें, फ़ाइल/फ़ोटो चुनें, फैसला देखें।
2. **Share-target मोड** (असली mobile-native pattern): किसी भी app में
   "Share" दबाएँ → "AI-SDDS से जाँचें" चुनें (हमारा app Android के
   Share Sheet में रजिस्टर होता है) → स्कैन होता है → सुरक्षित होने पर
   आगे शेयर जारी रहता है।

## ⚠️ अधूरा हिस्सा (जानबूझकर, स्पष्ट रूप से चिह्नित)

`home_screen.dart` में `_proceedAnyway()` के पास एक comment है: WARN
के बाद "फिर भी जारी रखें" दबाने पर फ़ाइल को **असली originally-चुने गए
app तक वापस भेजना** अभी implement नहीं है। इसके लिए `share_plus`
package और प्लेटफ़ॉर्म-specific Intent handling चाहिए — बिना टेस्ट किए
इसे लिखना risky था, तो मैंने इसे साफ़ तौर पर एक placeholder के रूप में
छोड़ा है, अनुमान लगाकर "लगता है काम करेगा" जैसा कोड नहीं लिखा।

## iOS पर Share Extension

ऊपर वाला Android Intent-filter pattern है। iOS पर असली Share Extension
चाहिए — यह Flutter से सीधे नहीं होता, एक अलग Xcode target बनाना पड़ता
है (`flutter create` के बाद Xcode खोलकर "File → New → Target → Share
Extension")। यह repo में शामिल नहीं है क्योंकि Xcode/macOS के बिना
इसे लिखना सिर्फ़ अनुमान होता — आपके Mac पर सही तरीका होगा।

## फ़ाइलें

| फ़ाइल | काम | Extension में बराबर |
|---|---|---|
| `lib/services/api_client.dart` | `/v1/scan` कॉल, fail-open | `background.js` |
| `lib/services/settings_store.dart` | API key — Keystore/Keychain में (extension से ज़्यादा सुरक्षित) | `popup.js` के storage हिस्से |
| `lib/screens/home_screen.dart` | मुख्य UI + share-intent receiver | `content-script.js` + `test-page.html` |
| `lib/widgets/verdict_card.dart` | रंग-कोडित फैसला कार्ड | Shadow DOM banner |
| `android_manifest_snippet/` | Share Sheet में दिखने के लिए ज़रूरी XML | manifest.json की `content_scripts` |

## अगला कदम (आपके Mac/Linux मशीन पर)
1. ऊपर दिए गए `flutter create` स्टेप्स पूरे करें
2. `flutter analyze` से सभी असली compile errors ठीक करें
3. एक widget test लिखें (`test/verdict_card_test.dart`) — यहाँ शामिल
   नहीं किया गया क्योंकि बिना चलाए लिखी गई टेस्ट सिर्फ़ false confidence
   देती, असली validation नहीं
4. iOS Share Extension अलग से Xcode में बनाएँ
