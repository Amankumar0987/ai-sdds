from core import patterns


def test_detects_validated_pan():
    text = "मेरा PAN नंबर ABCPE1234F है"
    findings = patterns.scan_text(text)
    pan_findings = [f for f in findings if f["type"] == "PAN"]
    assert len(pan_findings) == 1
    assert pan_findings[0]["validated"] is True
    assert pan_findings[0]["confidence"] >= 0.85
    # raw value must never appear in full in the finding
    assert "ABCPE1234F" not in pan_findings[0]["masked_value"]


def test_detects_password_keyword():
    text = "Gmail password: Rahul@1990#"
    findings = patterns.scan_text(text)
    pw_findings = [f for f in findings if f["type"] == "PASSWORD_KEYWORD"]
    assert len(pw_findings) == 1


def test_aadhaar_format_without_checksum_gets_low_confidence():
    # A random 12-digit number that matches the *shape* but fails Verhoeff
    text = "Invoice number: 1111 2222 3333"
    findings = patterns.scan_text(text)
    aadhaar_findings = [f for f in findings if f["type"] == "AADHAAR"]
    assert len(aadhaar_findings) == 1
    assert aadhaar_findings[0]["validated"] is False
    assert aadhaar_findings[0]["confidence"] < 0.85  # should not trigger a BLOCK alone


def test_resume_like_text_produces_no_high_confidence_findings():
    text = "नाम: अंकिता सिंह\nकौशल: Python, React, SQL\nअनुभव: 3 वर्ष - TCS\nईमेल: ankita@email.com"
    findings = patterns.scan_text(text)
    high_conf = [f for f in findings if f["confidence"] >= 0.85]
    assert high_conf == []


def test_zero_width_evasion_is_still_detected():
    # An attacker (or a bypass attempt) can insert invisible Unicode
    # "format" characters between digits to defeat a naive regex while
    # the text still LOOKS identical to a human. Found during a
    # security-hardening pass — see patterns.normalize_for_scanning.
    evasive = "Aadhaar Number: 2345\u200b6789\u200b0124"  # zero-width spaces between groups
    findings = patterns.scan_text(evasive)
    aadhaar = [f for f in findings if f["type"] == "AADHAAR"]
    assert len(aadhaar) == 1
    assert aadhaar[0]["validated"] is True
    assert aadhaar[0]["confidence"] >= 0.85


def test_zero_width_joiner_and_bom_are_also_stripped():
    evasive = "PAN: ABC\u200cPE\u200d1234\ufeffF"
    findings = patterns.scan_text(evasive)
    pan = [f for f in findings if f["type"] == "PAN"]
    assert len(pan) == 1
    assert pan[0]["validated"] is True


def test_dot_separated_aadhaar_is_detected():
    # Red-team finding: a dot-separated Aadhaar (common OCR/typing
    # variant) previously evaded the regex entirely (the separator
    # class only allowed whitespace/hyphen).
    findings = patterns.scan_text("Aadhaar: 2345.6789.0124")
    aadhaar = [f for f in findings if f["type"] == "AADHAAR"]
    assert len(aadhaar) == 1
    assert aadhaar[0]["validated"] is True


def test_cyrillic_homoglyph_pan_is_detected():
    # Red-team finding: replacing a single Latin letter with a
    # visually-identical Cyrillic one (U+0420 "Р" instead of "P")
    # previously defeated the [A-Z] regex class entirely while looking
    # completely normal to a human reader.
    evasive = "PAN: ABC\u0420E1234F"  # Cyrillic А/Р look identical to Latin A/P
    findings = patterns.scan_text(evasive)
    pan = [f for f in findings if f["type"] == "PAN"]
    assert len(pan) == 1
    assert pan[0]["validated"] is True


def test_confusable_fold_never_touches_devanagari():
    # SAFETY-CRITICAL: the confusable-folding defense must never
    # corrupt real Hindi text. This is checked on every run, not just
    # during initial development — a future library upgrade or
    # confusables-data change could silently break this.
    text = "नाम: अंकिता सिंह, पता: साहरसा बिहार"
    findings = patterns.scan_text(text)
    assert findings == []
    # Also confirm the normalization step itself is lossless for this text
    assert patterns.normalize_for_scanning(text) == text
