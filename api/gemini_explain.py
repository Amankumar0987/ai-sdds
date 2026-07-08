"""
api/gemini_explain.py
======================
Turns a ScanResult into a short, plain-Hindi explanation for
non-technical users, using Gemini (gemini-2.0-flash).

SECURITY DESIGN (do not weaken this):
  - Raw file bytes are NEVER sent here and never touch this module —
    the PWA only sends the already-computed ScanResult JSON (verdict,
    reason, masked findings). Gemini never sees the uploaded file.
  - If GEMINI_API_KEY is unset, or the Gemini call fails/times out for
    any reason, we fall back to a canned Hindi explanation keyed off
    the verdict. The core verdict itself is never touched by this
    module — this is presentation-only, best-effort enrichment.
"""

from __future__ import annotations
import os
import logging

logger = logging.getLogger("ai_sdds.gemini_explain")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
_MODEL_NAME = "gemini-2.0-flash"

_FALLBACK_HI = {
    "BLOCK": "इस फ़ाइल में उच्च-विश्वास संवेदनशील जानकारी (जैसे आधार, PAN, या कार्ड नंबर) मिली है, इसलिए इसे अपलोड करने से रोका गया है। कृपया संवेदनशील हिस्सा हटाकर दोबारा कोशिश करें।",
    "WARN": "इस फ़ाइल में संभावित संवेदनशील जानकारी मिली है। आगे बढ़ने से पहले एक बार ध्यान से जाँच लें कि इसमें कोई निजी जानकारी तो नहीं है।",
    "ALLOW": "इस फ़ाइल में कोई महत्वपूर्ण संवेदनशील जानकारी नहीं मिली। इसे अपलोड करना सुरक्षित लग रहा है।",
    "REJECTED": "इस फ़ाइल को स्कैन नहीं किया जा सका (गलत फ़ॉर्मैट, आकार सीमा से बड़ी, या स्कैनर अस्थायी रूप से अनुपलब्ध)। कृपया फ़ाइल जाँचें और दोबारा कोशिश करें।",
}


def _fallback(scan_result: dict) -> str:
    verdict = scan_result.get("verdict", "REJECTED")
    return _FALLBACK_HI.get(verdict, _FALLBACK_HI["REJECTED"])


def explain(scan_result: dict) -> str:
    if not GEMINI_API_KEY:
        return _fallback(scan_result)

    try:
        import google.generativeai as genai

        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel(_MODEL_NAME)

        verdict = scan_result.get("verdict", "")
        reason = scan_result.get("reason", "")
        findings = scan_result.get("findings", []) or []
        # Only masked labels/types are forwarded — never masked_value's
        # surrounding raw context, and never the original file.
        finding_labels = ", ".join(sorted({f.get("label", f.get("type", "")) for f in findings})) or "कोई नहीं"

        prompt = (
            "तुम एक गैर-तकनीकी भारतीय उपयोगकर्ता को यह समझा रहे हो कि उनकी फ़ाइल "
            "अपलोड से पहले क्यों ब्लॉक/चेतावनी/अनुमति दी गई। सरल, 2-3 वाक्यों का "
            "हिंदी में जवाब दो, कोई तकनीकी शब्दजाल नहीं।\n\n"
            f"फैसला: {verdict}\n"
            f"कारण: {reason}\n"
            f"मिली संवेदनशील श्रेणियाँ: {finding_labels}\n"
        )

        response = model.generate_content(
            prompt,
            request_options={"timeout": 10},
        )
        text = (getattr(response, "text", "") or "").strip()
        return text or _fallback(scan_result)
    except Exception as exc:  # noqa: BLE001 — any Gemini failure must degrade safely
        logger.warning("Gemini explain failed, using fallback: %s", exc)
        return _fallback(scan_result)
