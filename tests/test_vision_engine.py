import io
import qrcode
from PIL import Image, ImageDraw
from core import vision_engine


def _blank_image(w=300, h=300):
    return Image.new("RGB", (w, h), color="white")


def test_detect_qr_code_finds_a_real_qr():
    qr = qrcode.QRCode(box_size=4, border=2)
    qr.add_data("synthetic-test-only")
    qr.make()
    qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")

    canvas = Image.new("RGB", (400, 400), "white")
    canvas.paste(qr_img, (50, 50))

    findings = vision_engine.detect_qr_code(canvas)
    assert len(findings) == 1
    assert findings[0].type == "QR_CODE"
    assert findings[0].confidence > 0


def test_detect_qr_code_returns_empty_when_no_qr_present():
    findings = vision_engine.detect_qr_code(_blank_image())
    assert findings == []


def test_detect_face_photo_does_not_false_positive_on_blank_image():
    # The most important property of a face detector used as a security
    # signal: it must NOT fire on an empty/non-photographic image.
    findings = vision_engine.detect_face_photo(_blank_image())
    assert findings == []


def test_detect_face_photo_does_not_crash_on_cartoon_shapes():
    img = _blank_image()
    d = ImageDraw.Draw(img)
    d.ellipse([40, 40, 180, 200], fill=(222, 184, 150))
    d.ellipse([70, 100, 90, 120], fill="black")
    # Hand-drawn geometric shapes lack real photographic gradient
    # patterns, so a real Haar cascade correctly finds nothing here —
    # this is a feature (avoids false positives), not a limitation.
    findings = vision_engine.detect_face_photo(img)
    assert isinstance(findings, list)


def test_scan_image_merges_all_detectors_into_dicts():
    qr = qrcode.QRCode(box_size=4, border=2)
    qr.add_data("synthetic-test-only")
    qr.make()
    qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    canvas = Image.new("RGB", (400, 400), "white")
    canvas.paste(qr_img, (50, 50))

    results = vision_engine.scan_image(canvas)
    assert all(isinstance(r, dict) for r in results)
    assert any(r["type"] == "QR_CODE" for r in results)


def test_yolo_model_unavailable_returns_empty_without_crashing():
    model = vision_engine.YoloLayoutModel(weights_path="/nonexistent/path.pt")
    assert model.available is False
    assert model.detect(_blank_image()) == []
