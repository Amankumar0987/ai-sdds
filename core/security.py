"""
security.py
===========
This module is the security backbone of AI-SDDS. Every rule here maps
directly to a row in the "Phase 5 — Full Security Hardening" plan.

Principles enforced in this file:
  1. ZERO RETENTION   — sensitive bytes/text are never written to disk
                         or to any persistent log. Only masked values
                         and metadata leave this module.
  2. FILE-TYPE TRUST   — never trust a file extension; verify the real
                         MIME type from the file's magic bytes.
  3. RESOURCE LIMITS   — hard caps on file size / image pixel count to
                         stop decompression-bomb / DoS attacks.
  4. SAFE LOGGING      — a dedicated logger that physically cannot emit
                         a raw matched value, only masked ones.
"""

from __future__ import annotations
import io
import logging
import time
from dataclasses import dataclass

try:
    import magic  # python-magic, wraps libmagic
except ImportError:  # pragma: no cover
    magic = None

from PIL import Image

# ---------------------------------------------------------------------------
# 1. Resource limits (anti-DoS / anti decompression-bomb)
# ---------------------------------------------------------------------------

MAX_FILE_SIZE_BYTES = 15 * 1024 * 1024       # 15 MB upload cap
MAX_IMAGE_PIXELS = 40_000_000                # ~40 MP cap (blocks pixel-flood bombs)
MAX_PDF_PAGES = 30                           # cap pages scanned per document
OCR_TIMEOUT_SECONDS = 10                     # per-page OCR timeout

Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS    # enforce at the Pillow level too

ALLOWED_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "application/pdf",
}


class FileRejected(Exception):
    """Raised when a file fails a security check, before any OCR/NLP runs."""


@dataclass
class ValidationResult:
    ok: bool
    mime_type: str
    size_bytes: int
    reason: str = ""


def validate_file(file_bytes: bytes) -> ValidationResult:
    """Validate a file purely from its bytes — never from a filename or
    a user-supplied extension, both of which are trivially spoofable."""
    size = len(file_bytes)
    if size == 0:
        return ValidationResult(False, "unknown", size, "खाली फ़ाइल")
    if size > MAX_FILE_SIZE_BYTES:
        return ValidationResult(False, "unknown", size, "फ़ाइल आकार सीमा से अधिक")

    if magic is not None:
        mime = magic.from_buffer(file_bytes, mime=True)
    else:  # pragma: no cover - fallback if libmagic unavailable in an environment
        mime = _sniff_mime_fallback(file_bytes)

    if mime not in ALLOWED_MIME_TYPES:
        return ValidationResult(False, mime, size, f"असमर्थित फ़ाइल प्रकार: {mime}")

    return ValidationResult(True, mime, size, "ठीक है")


def _sniff_mime_fallback(b: bytes) -> str:
    if b[:4] == b"%PDF":
        return "application/pdf"
    if b[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if b[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    return "application/octet-stream"


def safe_open_image(file_bytes: bytes) -> Image.Image:
    """Open an image fully in-memory. Raises FileRejected on anything
    that looks like a decompression-bomb or a corrupt/malicious payload."""
    try:
        img = Image.open(io.BytesIO(file_bytes))
        img.load()  # force full decode now, inside our pixel-count guard
    except Exception as exc:
        raise FileRejected(f"छवि सुरक्षित रूप से नहीं खोली जा सकी: {exc}") from exc
    return img


# ---------------------------------------------------------------------------
# 2. Masking — the only form in which a matched value may leave core/
# ---------------------------------------------------------------------------

def mask_value(value: str) -> str:
    """Keep the first 2 and last 2 characters, mask the rest. Short
    values are masked entirely. This is what gets logged/displayed —
    never the raw value."""
    cleaned = value.strip()
    if len(cleaned) <= 4:
        return "*" * len(cleaned)
    return cleaned[:2] + "*" * (len(cleaned) - 4) + cleaned[-2:]


# ---------------------------------------------------------------------------
# 3. Safe logging — structurally cannot leak a raw sensitive value
# ---------------------------------------------------------------------------

logger = logging.getLogger("ai_sdds")
logger.setLevel(logging.INFO)
if not logger.handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(_h)


def log_scan_event(filename_hash: str, mime_type: str, finding_types: list[str], verdict: str) -> None:
    """Log only non-sensitive metadata: a hash of the filename (not the
    content), the mime type, which *types* of sensitive data were found
    (e.g. "AADHAAR"), and the final verdict. Never the matched text."""
    logger.info(
        "scan file_hash=%s mime=%s findings=%s verdict=%s",
        filename_hash, mime_type, ",".join(finding_types) or "none", verdict,
    )


def hash_filename(filename: str) -> str:
    import hashlib
    return hashlib.sha256(filename.encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------------------
# 4. Simple timeout guard for OCR calls (anti hung-process DoS)
# ---------------------------------------------------------------------------

class OCRTimeout(Exception):
    pass


def run_with_timeout(func, args=(), timeout=OCR_TIMEOUT_SECONDS):
    """Run `func` in a worker thread with a hard wall-clock timeout.
    Thread-based (not signal-based) so it stays safe inside async/web
    server contexts where SIGALRM is unreliable."""
    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(func, *args)
        try:
            return future.result(timeout=timeout)
        except concurrent.futures.TimeoutError as exc:
            raise OCRTimeout(f"{timeout} सेकंड में प्रसंस्करण पूरा नहीं हुआ") from exc
