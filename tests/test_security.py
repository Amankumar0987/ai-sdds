import io
from PIL import Image
from core import security


def _png_bytes(w=100, h=100):
    buf = io.BytesIO()
    Image.new("RGB", (w, h), color="white").save(buf, format="PNG")
    return buf.getvalue()


def test_validate_file_accepts_real_png():
    result = security.validate_file(_png_bytes())
    assert result.ok is True
    assert result.mime_type == "image/png"


def test_validate_file_rejects_fake_extension_attack():
    # A .jpg-named file that is actually a plain text file: magic-byte
    # sniffing must catch this even though a naive ext check would not.
    fake_bytes = b"this is not actually an image, just text pretending to be one"
    result = security.validate_file(fake_bytes)
    assert result.ok is False


def test_validate_file_rejects_oversized_file():
    big = b"0" * (security.MAX_FILE_SIZE_BYTES + 1)
    result = security.validate_file(big)
    assert result.ok is False
    assert "आकार" in result.reason


def test_validate_file_rejects_empty_file():
    result = security.validate_file(b"")
    assert result.ok is False


def test_mask_value_never_returns_raw_value():
    raw = "234567890124"
    masked = security.mask_value(raw)
    assert raw not in masked
    assert masked.startswith("23")
    assert masked.endswith("24")
    assert "*" in masked


def test_mask_value_fully_masks_short_strings():
    assert security.mask_value("abc") == "***"


def test_hash_filename_is_deterministic_and_not_reversible_lookalike():
    h1 = security.hash_filename("aadhaar.jpg")
    h2 = security.hash_filename("aadhaar.jpg")
    assert h1 == h2
    assert h1 != "aadhaar.jpg"
