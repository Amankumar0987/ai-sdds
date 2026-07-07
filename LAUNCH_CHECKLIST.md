# Launch Checklist — AI-SDDS

`SECURITY_CHECKLIST.md` security से संबंधित है। यह checklist
**operational readiness** के बारे में है — क्या सिस्टम असली ट्रैफ़िक
के लिए चलाने लायक है।

## Monitoring & Alerting
- ✅ `/v1/metrics` (Prometheus format) — scan counts by verdict, latency histogram, degraded-mode events — `api/metrics.py`
- 🔲 Prometheus + Grafana (या समकक्ष) से dashboard बनाएँ
- 🔲 Alert rule: `ai_sdds_degraded_mode_events_total` अचानक बढ़े तो तुरंत अलर्ट (scanner outage का सीधा संकेत)
- 🔲 Alert rule: `BLOCK` verdict की दर सामान्य से बहुत ज़्यादा/कम बदले तो जाँचें (pattern बदलने या attack का संकेत हो सकता है)
- 🔲 `/v1/metrics` को सिर्फ़ internal network से सुलभ बनाएँ (reverse-proxy/firewall स्तर पर) — अभी unauthenticated है, standard Prometheus convention के अनुसार, पर public internet पर expose न करें

## Versioning & Releases
- ✅ API पहले से ही `/v1/` prefixed है — breaking changes के लिए `/v2/` का रास्ता साफ़ है
- 🔲 Semantic versioning अपनाएँ (`MAJOR.MINOR.PATCH`) हर component के लिए: Core Engine, API, Extension अलग-अलग version हो सकते हैं
- 🔲 हर release को git tag करें, CHANGELOG.md अपडेट करें (देखें नीचे)

## Rollback Plan
- 🔲 पुराना Docker image टैग रखें (कम से कम पिछले 3 releases) ताकि तुरंत rollback हो सके
- 🔲 Database/state migration नहीं है अभी (कोई persistent storage नहीं) — इससे rollback आसान है, इसे बनाए रखें

## Load Testing
- 🔲 असली traffic से पहले `locust`/`k6` से load test करें — विशेष रूप से OCR/YOLO latency के साथ concurrent requests
- 🔲 rate-limit values (`AI_SDDS_RATE_LIMIT`) को असली उपयोग पैटर्न देखकर tune करें — अभी 30/minute एक placeholder अनुमान है

## Compliance (भारत-विशिष्ट)
- 🔲 DPDPA 2023 के तहत data fiduciary registration की ज़रूरत है या नहीं — कानूनी सलाह लें
- 🔲 Privacy policy दस्तावेज़ बनाएँ (बताएँ कि कुछ भी persist नहीं होता — यह एक मार्केटिंग/trust बढ़ाने वाला बिंदु भी है)
- 🔲 अगर B2B SaaS के रूप में बेचा जाए, तो data-processing agreement (DPA) टेम्पलेट तैयार करें

## License (अभी कोई फ़ैसला नहीं लिया गया — जानबूझकर)
- 🔲 यह तय करना बाकी है: open-source (MIT/Apache-2.0) या proprietary/commercial?
  इससे `LICENSE` फ़ाइल का चुनाव होगा। **मैंने जानबूझकर कोई license नहीं चुनी** —
  research paper में जो business-opportunity वाला हिस्सा था, उससे लगा कि यह एक
  commercial product हो सकता है, इसलिए यह फ़ैसला आपका होना चाहिए।

## Support / On-call
- 🔲 कौन degraded-mode अलर्ट का जवाब देगा, यह तय करें
- 🔲 Incident response runbook बनाएँ (scanner डाउन होने पर क्या करना है — अभी fail-open है, पर मैन्युअल escalation path भी चाहिए)
