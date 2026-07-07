"""
detector.py
===========
The single public entry point: `scan(file_bytes, filename)`.

Pipeline:
  1. security.validate_file   -> reject anything that isn't a real
                                  image/PDF, or is oversized.
  2. extract text              -> OCR (images) or pdf_engine (PDFs),
                                  always wrapped in a hard timeout.
  3. patterns.scan_text        -> regex + checksum validation.
  4. aggregate verdict         -> BLOCK / WARN / ALLOW.
  5. security.log_scan_event   -> metadata-only audit log.

No function in this module ever returns, stores, or logs the raw
extracted text or the raw matched substrings — only masked findings.
"""

from __future__ import annotations
from dataclasses import dataclass, field

from . import security
from . import ocr_engine
from . import pdf_engine
from . import patterns
from . import vision_engine

BLOCK_CONFIDENCE_THRESHOLD = 0.85   # findings at/above this => BLOCK
WARN_CONFIDENCE_THRESHOLD = 0.40    # findings at/above this (but below BLOCK) => WARN

# A face photo AND a QR code together, with no corroborating text match
# at all, is the classic "OCR completely failed on a real ID" case this
# phase exists to catch (blurry phone photo, glare, heavy compression).
VISUAL_ID_LAYOUT_TYPES = {"FACE_PHOTO", "QR_CODE"}


@dataclass
class ScanResult:
    verdict: str                       # "BLOCK" | "WARN" | "ALLOW" | "REJECTED"
    findings: list[dict] = field(default_factory=list)
    reason: str = ""
    mime_type: str = ""
    size_bytes: int = 0

    def to_dict(self) -> dict:
        return {
            "verdict": self.verdict,
            "findings": self.findings,
            "reason": self.reason,
            "mime_type": self.mime_type,
            "size_bytes": self.size_bytes,
        }


def _extract_text(file_bytes: bytes, mime_type: str) -> str:
    if mime_type == "application/pdf":
        return security.run_with_timeout(pdf_engine.extract_text, args=(file_bytes,))
    return security.run_with_timeout(ocr_engine.extract_text_from_bytes, args=(file_bytes,))


_VISUAL_LABELS_HI = {
    "FACE_PHOTO": "चेहरे की फ़ोटो (ID-जैसी)",
    "QR_CODE": "QR कोड",
}

_yolo_model = None  # lazily constructed singleton — loading a model on every call would be wasteful


def _get_yolo_model() -> vision_engine.YoloLayoutModel:
    global _yolo_model
    if _yolo_model is None:
        _yolo_model = vision_engine.YoloLayoutModel()
    return _yolo_model


def _scan_visual_structure(file_bytes: bytes, mime_type: str) -> list[dict]:
    """Only runs for image uploads — PDF page-rendering + vision is a
    possible future extension, not yet implemented (see README)."""
    if mime_type == "application/pdf":
        return []
    try:
        image = security.run_with_timeout(security.safe_open_image, args=(file_bytes,))
    except (security.OCRTimeout, security.FileRejected):
        return []

    raw = vision_engine.scan_image(image, yolo_model=_get_yolo_model())
    findings = []
    for f in raw:
        findings.append({
            "type": f["type"],
            "label": _VISUAL_LABELS_HI.get(f["type"], f["type"]),
            "masked_value": "[दृश्य संरचना — कोई टेक्स्ट नहीं]",
            "confidence": f["confidence"],
            "validated": False,
            "severity": "medium",
        })

    visual_types = {f["type"] for f in findings}
    if VISUAL_ID_LAYOUT_TYPES.issubset(visual_types):
        findings.append({
            "type": "ID_LAYOUT_COMBO",
            "label": "ID-कार्ड जैसी संरचना (फ़ोटो + QR एक साथ)",
            "masked_value": "[दृश्य संरचना — कोई टेक्स्ट नहीं]",
            "confidence": 0.75,
            "validated": False,
            "severity": "medium",
        })
    return findings


def scan(file_bytes: bytes, filename: str = "upload") -> ScanResult:
    validation = security.validate_file(file_bytes)
    if not validation.ok:
        result = ScanResult(
            verdict="REJECTED",
            reason=validation.reason,
            mime_type=validation.mime_type,
            size_bytes=validation.size_bytes,
        )
        security.log_scan_event(security.hash_filename(filename), validation.mime_type, [], result.verdict)
        return result

    try:
        text = _extract_text(file_bytes, validation.mime_type)
    except ocr_engine.OCRUnavailable as exc:
        # System-level misconfiguration (Tesseract missing), not a bad
        # file — kept as its own branch so the reason string is
        # actionable instead of looking like "this file is bad".
        result = ScanResult(
            verdict="REJECTED",
            reason=str(exc),
            mime_type=validation.mime_type,
            size_bytes=validation.size_bytes,
        )
        security.log_scan_event(security.hash_filename(filename), validation.mime_type, [], "OCR_UNAVAILABLE")
        return result
    except (security.OCRTimeout, security.FileRejected) as exc:
        result = ScanResult(
            verdict="REJECTED",
            reason=str(exc),
            mime_type=validation.mime_type,
            size_bytes=validation.size_bytes,
        )
        security.log_scan_event(security.hash_filename(filename), validation.mime_type, [], result.verdict)
        return result

    findings = patterns.scan_text(text)
    del text  # explicitly drop the raw extracted text as soon as we're done with it

    findings += _scan_visual_structure(file_bytes, validation.mime_type)

    verdict, reason = _decide_verdict(findings)
    result = ScanResult(
        verdict=verdict,
        findings=findings,
        reason=reason,
        mime_type=validation.mime_type,
        size_bytes=validation.size_bytes,
    )
    security.log_scan_event(
        security.hash_filename(filename),
        validation.mime_type,
        [f["type"] for f in findings],
        verdict,
    )
    return result


def _decide_verdict(findings: list[dict]) -> tuple[str, str]:
    if not findings:
        return "ALLOW", "कोई संवेदनशील जानकारी नहीं मिली"

    high = [f for f in findings if f["confidence"] >= BLOCK_CONFIDENCE_THRESHOLD]
    if high:
        types = ", ".join(sorted({f["label"] for f in high}))
        return "BLOCK", f"उच्च-विश्वास संवेदनशील जानकारी मिली: {types}"

    medium = [f for f in findings if f["confidence"] >= WARN_CONFIDENCE_THRESHOLD]
    if medium:
        types = ", ".join(sorted({f["label"] for f in medium}))
        return "WARN", f"संभावित संवेदनशील जानकारी मिली, कृपया जाँच लें: {types}"

    return "ALLOW", "कोई महत्वपूर्ण संवेदनशील जानकारी नहीं मिली"
