"""
ocr_engine.py
=============
Thin, security-conscious wrapper around pytesseract.

- Operates entirely in memory (PIL.Image from bytes in, str out).
- Never writes the image or extracted text to disk.
- Wrapped by security.run_with_timeout by the caller to bound worst-case
  processing time (a hostile, specially-crafted image can otherwise make
  Tesseract run for a very long time).
"""

from __future__ import annotations
from PIL import Image
import os
import pytesseract
from dotenv import load_dotenv

# Loaded here too (not just in config.py) so this module behaves
# correctly no matter which file gets imported first — relying on
# config.py having already run was a real, found bug: in a fresh
# process where core.ocr_engine is imported before config.py (e.g. a
# test file that imports `from core import detector` directly), the
# .env file would silently never load, and AI_SDDS_TESSERACT_CMD would
# be ignored even if set. load_dotenv() is idempotent — calling it
# twice across the app is harmless.
load_dotenv()

# Most systems (Linux, Mac, Docker, CI) find tesseract automatically on
# PATH. Windows installs are the one common exception — pytesseract
# can't find it without an explicit path. Instead of hardcoding ONE
# machine's install path (which breaks for everyone else), this reads
# an optional environment variable. Windows users set it once in their
# own .env, nothing else changes:
#   AI_SDDS_TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
_tesseract_cmd_override = os.getenv("AI_SDDS_TESSERACT_CMD")
if _tesseract_cmd_override:
    pytesseract.pytesseract.tesseract_cmd = _tesseract_cmd_override


class OCRUnavailable(Exception):
    """Raised when the Tesseract OCR *engine itself* is missing or
    misconfigured on this machine — a system-level setup problem, not
    a bad file. Without this, pytesseract.TesseractNotFoundError would
    bubble up as an unhandled exception and surface to API callers as
    an opaque, unexplained HTTP 500 (this is exactly what happened in
    a real run on a Windows machine without Tesseract on PATH and
    without AI_SDDS_TESSERACT_CMD set)."""


# Hindi + English by default. Add more language codes as needed, e.g.
# "hin+eng+ben" once additional tesseract-ocr-<lang> packs are installed.
DEFAULT_LANGS = "hin+eng"
TESSERACT_CONFIG = "--oem 3 --psm 6"

# Tesseract's LSTM engine can drop thin glyphs (most often the digit "1")
# on small or low-DPI renders. Upscaling before OCR consistently fixes
# this in practice — it is the single highest-leverage preprocessing
# step for scanned IDs and phone-camera photos alike.
MIN_UPSCALE_DIMENSION = 1200


def _preprocess(image: Image.Image) -> Image.Image:
    image = image.convert("L")  # grayscale: removes color noise, speeds up OCR
    longest_side = max(image.size)
    if longest_side < MIN_UPSCALE_DIMENSION:
        scale = MIN_UPSCALE_DIMENSION / longest_side
        new_size = (int(image.width * scale), int(image.height * scale))
        image = image.resize(new_size, Image.LANCZOS)
    return image


def extract_text(image: Image.Image, langs: str = DEFAULT_LANGS) -> str:
    """Run OCR on a Pillow Image already loaded in memory.

    Dual-pass strategy: the bundled Hindi ('hin') traineddata model is
    measurably less accurate on Latin digits than the English model —
    in testing it regularly dropped the digit "1" inside 12-digit
    Aadhaar numbers and IFSC codes. Since all of our regulated-ID
    patterns (Aadhaar/PAN/IFSC/card numbers) are always written in
    Latin digits even on Hindi-language documents, we run a dedicated
    'eng' pass for accurate pattern matching, and a separate hin+eng
    pass to also capture Devanagari text (names/addresses) for the NER
    stage. Both texts are concatenated before pattern scanning.
    """
    image = _preprocess(image)
    try:
        digits_pass = pytesseract.image_to_string(image, lang="eng", config=TESSERACT_CONFIG)
        multilingual_pass = pytesseract.image_to_string(image, lang=langs, config=TESSERACT_CONFIG)
    except pytesseract.TesseractNotFoundError as exc:
        raise OCRUnavailable(
            "Tesseract OCR इंजन नहीं मिला। इसे install करें: "
            "https://github.com/UB-Mannheim/tesseract/wiki (Windows) "
            "या 'apt-get install tesseract-ocr' (Linux). अगर install है पर "
            "PATH में नहीं, तो .env में AI_SDDS_TESSERACT_CMD सेट करें — "
            "देखें .env.example।"
        ) from exc
    return digits_pass + "\n" + multilingual_pass


def extract_text_from_bytes(image_bytes: bytes, langs: str = DEFAULT_LANGS) -> str:
    from . import security
    img = security.safe_open_image(image_bytes)
    return extract_text(img, langs=langs)
