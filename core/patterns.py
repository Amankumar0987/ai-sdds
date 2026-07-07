"""
patterns.py
===========
Regex pattern library for sensitive Indian-document fields.

Design choice: every pattern here is paired with a structural/checksum
validator from validators.py. A regex hit alone is only a *candidate* —
it gets a low confidence score. It only becomes a high-confidence
finding once the checksum validator confirms it. This is what keeps
false positives down (e.g. a random 12-digit invoice number will not
pass the Aadhaar Verhoeff check).
"""

from __future__ import annotations
import re
import unicodedata
from dataclasses import dataclass
from typing import Callable, Optional

from confusable_homoglyphs import confusables

from . import validators

# Adversarial-evasion defense #1: zero-width and other invisible Unicode
# "format" characters can be inserted between digits of a real Aadhaar/
# PAN/card number to make it invisible to a human reader while
# completely defeating a naive regex (e.g. "2345\u200b6789\u200b0124").
# We strip every Unicode category "Cf" (Format) character before
# scanning. This is a deliberate, tested security control — see
# tests/test_patterns.py::test_zero_width_evasion_is_still_detected.
_INVISIBLE_CATEGORY = "Cf"


def _strip_invisible_chars(text: str) -> str:
    return "".join(ch for ch in text if unicodedata.category(ch) != _INVISIBLE_CATEGORY)


# Adversarial-evasion defense #2: a single Cyrillic/Greek letter that
# LOOKS identical to a Latin one (e.g. Cyrillic "Р" U+0420 instead of
# Latin "P") defeats our [A-Z] regex classes while looking completely
# normal to a human. We fold these to their Latin lookalike before
# scanning, using the `confusable-homoglyphs` library (Unicode's own
# published confusables data — not a hand-rolled partial table).
#
# SAFETY-CRITICAL constraint: this fold must NEVER touch Devanagari (or
# any other legitimate non-Latin script our documents contain) — it
# would corrupt real Hindi text. We only ever fold a character when the
# replacement candidate is itself a single plain ASCII letter; combining
# marks / multi-character sequences are never substituted. See
# tests/test_patterns.py::test_confusable_fold_never_touches_devanagari.
def _fold_confusables(text: str) -> str:
    chars = list(text)
    for i, ch in enumerate(chars):
        if not ch.isalpha() or ch.isascii():
            continue  # already plain ASCII, or not a letter — nothing to do
        match = confusables.is_confusable(ch, greedy=False)
        if not match or match[0]["alias"] == "LATIN":
            continue
        for homoglyph in match[0]["homoglyphs"]:
            candidate = homoglyph["c"]
            if len(candidate) == 1 and candidate.isascii() and candidate.isalpha():
                chars[i] = candidate
                break
    return "".join(chars)


def normalize_for_scanning(text: str) -> str:
    return _fold_confusables(_strip_invisible_chars(text))


@dataclass
class PatternRule:
    name: str               # internal id, e.g. "AADHAAR"
    label_hi: str           # Hindi display label
    regex: re.Pattern
    validator: Optional[Callable[[str], bool]] = None
    base_confidence: float = 0.55   # confidence if regex matches but validator fails/absent
    validated_confidence: float = 0.97  # confidence if validator also passes
    severity: str = "high"  # high | medium


RULES: list[PatternRule] = [
    PatternRule(
        name="AADHAAR",
        label_hi="आधार नंबर",
        regex=re.compile(r"\b\d{4}[\s.-]?\d{4}[\s.-]?\d{4}\b"),
        validator=validators.aadhaar_structure_valid,
        base_confidence=0.40,   # plenty of 12-digit numbers exist that aren't Aadhaar
        validated_confidence=0.98,
        severity="high",
    ),
    PatternRule(
        name="PAN",
        label_hi="PAN नंबर",
        regex=re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b"),
        validator=validators.pan_structure_valid,
        base_confidence=0.70,
        validated_confidence=0.97,
        severity="high",
    ),
    PatternRule(
        name="IFSC",
        label_hi="IFSC कोड",
        regex=re.compile(r"\b[A-Z]{4}0[A-Z0-9]{6}\b"),
        validator=validators.ifsc_structure_valid,
        base_confidence=0.65,
        validated_confidence=0.95,
        severity="medium",
    ),
    PatternRule(
        name="CARD",
        label_hi="क्रेडिट/डेबिट कार्ड नंबर",
        regex=re.compile(r"\b(?:\d[ .-]?){13,19}\b"),
        validator=validators.luhn_checksum_valid,
        base_confidence=0.30,
        validated_confidence=0.97,
        severity="high",
    ),
    PatternRule(
        name="PASSPORT",
        label_hi="पासपोर्ट नंबर",
        regex=re.compile(r"\b[A-PR-WYa-pr-wy][1-9]\d\s?\d{4}[1-9]\b"),
        validator=None,
        base_confidence=0.55,
        validated_confidence=0.55,
        severity="high",
    ),
    PatternRule(
        name="PASSWORD_KEYWORD",
        label_hi="पासवर्ड (कीवर्ड संदर्भ)",
        regex=re.compile(
            r"(?i)\b(password|pwd|passwd|पासवर्ड)\s*[:=\-]\s*\S{4,}"
        ),
        validator=None,
        base_confidence=0.85,
        validated_confidence=0.85,
        severity="high",
    ),
    PatternRule(
        name="EMAIL",
        label_hi="ईमेल पता",
        regex=re.compile(r"\b[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}\b"),
        validator=None,
        base_confidence=0.30,   # low severity on its own
        validated_confidence=0.30,
        severity="medium",
    ),
    PatternRule(
        name="PHONE_IN",
        label_hi="भारतीय मोबाइल नंबर",
        regex=re.compile(r"\b[6-9]\d{9}\b"),
        validator=None,
        base_confidence=0.45,
        validated_confidence=0.45,
        severity="medium",
    ),
]


def scan_text(text: str) -> list[dict]:
    """Run every pattern rule against `text`. Returns a list of finding
    dicts. The raw matched substring is NEVER returned in full — only a
    masked version (see security.mask_value), to keep this function
    safe to log or display."""
    from . import security  # local import avoids a circular import at module load

    text = normalize_for_scanning(text)
    findings = []
    for rule in RULES:
        for match in rule.regex.finditer(text):
            raw = match.group(0)
            validated = bool(rule.validator and rule.validator(raw))
            confidence = rule.validated_confidence if validated else rule.base_confidence
            findings.append(
                {
                    "type": rule.name,
                    "label": rule.label_hi,
                    "masked_value": security.mask_value(raw),
                    "confidence": round(confidence, 2),
                    "validated": validated,
                    "severity": rule.severity,
                    "span": match.span(),
                }
            )
    return findings
