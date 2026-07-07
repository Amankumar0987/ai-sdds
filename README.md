# AI-SDDS — Core Detection Engine

Phase 1 of the AI-Powered Sensitive Document Detection System.
यह engine किसी भी इमेज/PDF में आधार नंबर, PAN, IFSC कोड, क्रेडिट/डेबिट
कार्ड नंबर और पासवर्ड-जैसी जानकारी को **AI सिस्टम में जाने से पहले**
पहचानता है।

## सेटअप (Setup)

```bash
# System dependencies (Linux/Mac)
sudo apt-get install tesseract-ocr tesseract-ocr-hin libmagic1

# Python dependencies
pip install -r requirements.txt
```

### Windows पर सेटअप

1. Tesseract OCR install करें: [UB-Mannheim installer](https://github.com/UB-Mannheim/tesseract/wiki) — installer में Hindi (`hin`) language pack ज़रूर चुनें।
2. `.env.example` को `.env` में कॉपी करें, और अगर installer ने tesseract को PATH में नहीं जोड़ा (ज़्यादातर डिफ़ॉल्ट इंस्टॉल में नहीं जुड़ता), तो `.env` में यह लाइन जोड़ें:
   ```
   AI_SDDS_TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
   ```
3. `pip install -r requirements.txt` (इसमें `python-dotenv` शामिल है जो `.env` को अपने-आप load करता है)।

अगर Tesseract बिल्कुल न मिले, तो अब scan crash नहीं होता — साफ़ `REJECTED` verdict के साथ ठीक यही ऊपर वाला instruction Hindi में दिखता है (देखें `core/ocr_engine.py::OCRUnavailable`)।

## चलाना (Run)

```bash
python main.py path/to/document.jpg
python main.py path/to/document.pdf
```

## टेस्ट चलाना (Run tests)

```bash
python -m pytest tests/ -v
```

56 tests cover: checksum validators (Verhoeff/Luhn), pattern matching,
adversarial-evasion defenses, file-security validation, API auth/rate-
limiting/metrics, federated-learning privacy properties, and real
end-to-end OCR pipeline tests (including graceful handling when
Tesseract itself is missing).

## आर्किटेक्चर (Architecture)

```
                 file_bytes
                     │
              security.validate_file
            (magic-byte MIME check,
             size limit, reject early)
                     │
        ┌────────────┴────────────┐
        │                         │
   ocr_engine.py              pdf_engine.py
   (dual-pass:                (text layer OR
    eng for digits,            per-page OCR
    hin+eng for text)          fallback)
        │                         │
        └────────────┬────────────┘
                     │  extracted text
                     │  (held in memory only)
                     ▼
              patterns.scan_text
        (regex candidate → checksum
         validator → confidence score)
                     │
                     ▼
              detector._decide_verdict
           BLOCK / WARN / ALLOW
                     │
                     ▼
          security.log_scan_event
        (metadata only — file hash,
         mime type, finding TYPES,
         verdict. Never raw values.)
```

## क्यों checksum validators ज़रूरी हैं

12 अंकों का कोई भी नंबर "आधार जैसा" दिखता है, लेकिन UIDAI असली आधार
नंबरों के लिए **Verhoeff checksum** algorithm का उपयोग करता है। बिना
validator के, हर invoice number, हर phone number sequence, हर random
ID को गलती से ब्लॉक कर दिया जाएगा (बहुत ज़्यादा false positives)।

इसलिए हर pattern दो स्तरों पर जाँचा जाता है:
1. **Regex shape match** → कम confidence (candidate)
2. **Checksum/structural validation pass** → उच्च confidence (confirmed)

यही तरीका PAN (4th अक्षर holder-type), IFSC (5th अक्षर सदा '0'), और
कार्ड नंबर (Luhn algorithm) पर भी लागू होता है।

## Security डिज़ाइन के मुख्य सिद्धांत

| जोखिम | समाधान | फ़ाइल |
|---|---|---|
| Fake file extension (.jpg जो असल में .exe है) | Magic-byte MIME sniffing, extension पर भरोसा नहीं | `security.py` |
| Decompression bomb / बहुत बड़ी इमेज | `Image.MAX_IMAGE_PIXELS` cap, file size cap | `security.py` |
| 10,000-page hostile PDF (DoS) | `MAX_PDF_PAGES` cap | `pdf_engine.py` |
| OCR हैंग होना (malformed इमेज) | थ्रेड-आधारित hard timeout | `security.py` |
| Log/console में असली आधार नंबर लीक होना | `mask_value()` — केवल पहले/आखिरी 2 अक्षर दिखते हैं, raw text कभी return/log नहीं होता | `security.py`, `detector.py` |
| Random 12-digit नंबर को गलती से ब्लॉक करना | Checksum validators (false-positive कम करते हैं) | `validators.py` |
| OCR में Hindi मॉडल के कारण अंक (digits) गलत पढ़ना | Dual-pass OCR: digits के लिए 'eng', टेक्स्ट के लिए 'hin+eng' | `ocr_engine.py` |

## Phase 2 — Computer Vision Layer (दृश्य संरचना पहचान)

OCR टेक्स्ट से कुछ न मिले तब भी (धुंधली फ़ोटो, glare, भारी compression)
ID-कार्ड को पहचानने के लिए दो स्वतंत्र layers:

### 1. Classical CV (आज ही काम करता है, कोई training/network नहीं चाहिए)
- **Face detection** (Haar cascade, opencv के अंदर bundled) — ज़्यादातर भारतीय
  ID दस्तावेज़ों में passport-स्टाइल फ़ोटो होती है।
- **QR code detection** (OpenCV का built-in detector) — आधार, बैंक दस्तावेज़,
  नए PAN सभी में QR कोड होता है।

दोनों `core/vision_engine.py` में हैं और हर scan में `detector.py` से
स्वचालित रूप से चलते हैं — सिर्फ़ image फ़ाइलों पर (PDF रेंडरिंग अभी
Phase में नहीं है, README के "ज्ञात सीमाएँ" में नोट है)।

```bash
# उदाहरण: सिर्फ़ QR code वाली इमेज, कोई OCR टेक्स्ट नहीं — फिर भी WARN मिलता है
python main.py sample_data/no_text_id_mock.png
```

### 2. YOLOv8 Layout Model (वैकल्पिक — ज़्यादा बारीक classes: photo/qr_code/logo)

```bash
python cv/generate_synthetic_dataset.py   # synthetic dataset बनाता है
python cv/train.py --epochs 10
export AI_SDDS_YOLO_WEIGHTS=cv/runs/id_layout/weights/best.pt
```

**⚠️ ईमानदार खुलासा (इसी sandbox की एक सीमा, आपके सिस्टम की नहीं):**
इस sandbox का network egress proxy `release-assets.githubusercontent.com`
को block करता है — यही जगह है जहाँ से YOLOv8 के असली pretrained (COCO)
weights डाउनलोड होते हैं। तो यहाँ training **architecture-only**
(`yolov8n.yaml`, random initialization) से हुई — training results.csv
में mAP पूरे समय 0 रहा (60 तस्वीरें + 6 epochs + कोई pretrained
features नहीं = कुछ खास नहीं सीखा)। **यह सिर्फ़ pipeline को प्रमाणित
करता है** (data → training → weights file → inference बिना crash के
चलता है), accuracy को नहीं।

**आपके सिस्टम पर** (सामान्य internet के साथ), `cv/train.py` में सिर्फ़
environment variable बदलें:
```bash
export AI_SDDS_PRETRAINED_AVAILABLE=true   # yolov8n.pt डाउनलोड होगा (COCO pretrained)
python cv/train.py --epochs 10
```
इससे transfer learning मिलेगी — कम images में भी काफ़ी बेहतर सटीकता।

## ज्ञात सीमाएँ (Known limitations — आगे के phases में ठीक होंगी)

- पासपोर्ट नंबर का कोई official checksum public नहीं है → अभी केवल structural pattern (कम confidence)।
- हाथ से लिखी (handwritten) जानकारी पर OCR सटीकता कम होगी।
- अभी कोई NER मॉडल नहीं है (नाम/पता को टेक्स्ट से अलग पहचानने के लिए) — यह अगला तार्किक कदम है।
- Visual CV scan अभी सिर्फ़ images पर चलता है, PDF pages पर नहीं (PDF को image में render करके चलाया जा सकता है — भविष्य का विस्तार)।
- YOLOv8 layout model असली labeled dataset और pretrained weights के बिना production-ready नहीं है (ऊपर देखें)।

## Phase 4 (आंशिक) — API सेवा

Core Engine अब एक secure FastAPI सेवा के पीछे है, जिसे Browser Extension या Mobile App कॉल कर सकते हैं।

```bash
cp .env.example .env        # और AI_SDDS_API_KEYS में अपनी असली key डालें
export $(cat .env | xargs)
uvicorn api.app:app --host 0.0.0.0 --port 8000

# या Docker से:
docker build -t ai-sdds-api .
docker run -p 8000:8000 --env-file .env ai-sdds-api
```

```bash
curl -X POST http://localhost:8000/v1/scan \
  -H "X-API-Key: <आपकी key>" \
  -F "file=@document.jpg"
```

### API सुरक्षा परतें

| परत | क्या करती है |
|---|---|
| Upload-size guard | `Content-Length` हेडर से बड़ी फ़ाइलें body पढ़े बिना ही 413 के साथ रिजेक्ट |
| CORS | खाली `AI_SDDS_ALLOWED_ORIGINS` से डिफ़ॉल्ट रूप से कोई भी cross-origin कॉल नहीं चलती |
| API key auth (`X-API-Key`) | key सेट न होने पर सर्वर खुद एक temporary key बनाकर startup log में दिखाता है — कभी "wide open" नहीं रहता |
| Rate limiting | `slowapi` से per-IP सीमा (डिफ़ॉल्ट 30/minute), 429 लौटाता है |
| Generic error handler | कोई भी unhandled exception caller को stack trace नहीं दिखाता |
| Non-root Docker user | container के अंदर भी root से नहीं चलता |

## आगे क्या (Next — Phase 2)

Computer Vision module (YOLOv8) जो टेक्स्ट के बिना भी ID कार्ड की
दृश्य संरचना (फोटो, QR कोड, सरकारी लोगो का स्थान) पहचान सके — ख़ासकर
तब ज़रूरी जब OCR टेक्स्ट पूरी तरह fail हो जाए।
