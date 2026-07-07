"""
test_redteam.py
================
Phase 6 — a dedicated, growing collection of adversarial evasion
attempts. Each test documents WHY the technique might work against a
naive scanner, and confirms whether AI-SDDS catches it. New evasion
ideas should be added here first (as a failing test), then fixed in
patterns.py/security.py, mirroring how the zero-width and homoglyph
findings were handled.
"""
from core import patterns


def test_evasion_newline_inside_number_is_caught():
    findings = patterns.scan_text("Aadhaar: 2345\n6789\n0124")
    assert any(f["type"] == "AADHAAR" and f["validated"] for f in findings)


def test_evasion_ideographic_space_is_caught():
    findings = patterns.scan_text("Aadhaar: 2345\u30006789\u30000124")
    assert any(f["type"] == "AADHAAR" and f["validated"] for f in findings)


def test_evasion_rtl_override_control_char_is_caught():
    findings = patterns.scan_text("Aadhaar: 2345\u202e6789\u202c0124")
    assert any(f["type"] == "AADHAAR" and f["validated"] for f in findings)


def test_evasion_dot_separators_are_caught():
    findings = patterns.scan_text("Aadhaar: 2345.6789.0124")
    assert any(f["type"] == "AADHAAR" and f["validated"] for f in findings)


def test_evasion_single_cyrillic_letter_in_pan_is_caught():
    findings = patterns.scan_text("PAN: ABC\u0420E1234F")
    assert any(f["type"] == "PAN" and f["validated"] for f in findings)


def test_evasion_mixed_case_password_keyword_is_caught():
    findings = patterns.scan_text("PaSsWoRd: Secret@123")
    assert any(f["type"] == "PASSWORD_KEYWORD" for f in findings)


# --- Known remaining gaps (documented, NOT yet fixed) -----------------
# These are intentionally written as tests-that-confirm-the-gap-exists
# (not xfail) so the gap is visible in plain test output rather than
# hidden. Closing these is tracked in SECURITY_CHECKLIST.md.

def test_KNOWN_GAP_base64_encoded_number_is_not_decoded():
    """A base64-encoded Aadhaar number is never decoded/re-scanned.
    Relevant mainly for text-bearing PDFs, not photographed ID images.
    See SECURITY_CHECKLIST.md."""
    import base64
    encoded = base64.b64encode(b"234567890124").decode()
    findings = patterns.scan_text(f"data: {encoded}")
    assert findings == []  # documents the current (unfixed) behavior
