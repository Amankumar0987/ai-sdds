"""
test_detector_integration.py
=============================
This is the real end-to-end test: it renders a synthetic image (plain
text on a white background — not a copy of any real ID design),
runs it through actual Tesseract OCR, then through the full detector
pipeline, and checks that the final verdict is correct.
"""
import io
from PIL import Image, ImageDraw
from core import detector


def _render_text_image(lines: list[str]) -> bytes:
    img = Image.new("RGB", (700, 50 * (len(lines) + 1)), color="white")
    draw = ImageDraw.Draw(img)
    for i, line in enumerate(lines):
        draw.text((20, 20 + i * 50), line, fill="black")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_synthetic_sensitive_document_gets_blocked():
    image_bytes = _render_text_image([
        "Name: Demo User",
        "Aadhaar Number: 2345 6789 0124",
        "Address: Test Lane, Patna",
    ])
    result = detector.scan(image_bytes, filename="test_aadhaar.png")
    assert result.verdict in ("BLOCK", "WARN")
    types_found = {f["type"] for f in result.findings}
    assert "AADHAAR" in types_found


def test_synthetic_safe_document_gets_allowed():
    image_bytes = _render_text_image([
        "Name: Demo User",
        "Skills: Python React SQL",
        "Experience: 3 years",
    ])
    result = detector.scan(image_bytes, filename="test_resume.png")
    high_conf = [f for f in result.findings if f["confidence"] >= 0.85]
    assert high_conf == []
    assert result.verdict in ("ALLOW",)


def test_rejected_file_type_never_reaches_ocr():
    fake = b"not a real image file at all"
    result = detector.scan(fake, filename="fake.png")
    assert result.verdict == "REJECTED"
    assert result.findings == []


def test_missing_tesseract_degrades_gracefully_instead_of_crashing():
    """Found via a real run on a Windows machine without Tesseract on
    PATH: pytesseract.TesseractNotFoundError used to bubble up as an
    unhandled exception, surfacing to API callers as an opaque HTTP
    500. Simulated here (rather than requiring an actual machine
    without Tesseract installed) by patching pytesseract directly."""
    from unittest.mock import patch
    import pytesseract

    image_bytes = _render_text_image(["irrelevant — OCR call itself is mocked to fail"])
    with patch("pytesseract.image_to_string", side_effect=pytesseract.TesseractNotFoundError()):
        result = detector.scan(image_bytes, filename="test.png")

    assert result.verdict == "REJECTED"
    assert "Tesseract" in result.reason
    assert "AI_SDDS_TESSERACT_CMD" in result.reason  # actionable, not just "error occurred"
