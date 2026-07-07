"""
validators.py
=============
Checksum-based validators. A regex match alone produces too many false
positives (any random 12-digit number "looks like" an Aadhaar number).
These validators apply the *real* checksum algorithms used by the
issuing authorities, so we only flag numbers that are structurally
plausible, not just digit-shaped.

Security note: these functions accept and return only booleans/strings
derived from the input. They never write the input to disk, logs, or
any external service.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Aadhaar — Verhoeff checksum algorithm
# UIDAI uses the Verhoeff algorithm (ISO/IEC 7064) for the 12th check digit.
# ---------------------------------------------------------------------------

_VERHOEFF_D = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
    [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
    [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
    [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
    [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
    [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
    [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
    [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
    [9, 8, 7, 6, 5, 4, 3, 2, 1, 0],
]
_VERHOEFF_P = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
    [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
    [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
    [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
    [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
    [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
    [7, 0, 4, 6, 9, 1, 3, 2, 5, 8],
]
_VERHOEFF_INV = [0, 4, 3, 2, 1, 5, 6, 7, 8, 9]


def verhoeff_checksum_valid(number: str) -> bool:
    """Return True if `number` (digits only, last digit is the check digit)
    passes the Verhoeff checksum used by UIDAI for Aadhaar numbers."""
    digits = [int(d) for d in number if d.isdigit()]
    if len(digits) != 12:
        return False
    c = 0
    for i, item in enumerate(reversed(digits)):
        c = _VERHOEFF_D[c][_VERHOEFF_P[i % 8][item]]
    return c == 0


def aadhaar_structure_valid(number: str) -> bool:
    """UIDAI never issues Aadhaar numbers starting with 0 or 1."""
    digits = "".join(ch for ch in number if ch.isdigit())
    if len(digits) != 12:
        return False
    if digits[0] in ("0", "1"):
        return False
    return verhoeff_checksum_valid(digits)


# ---------------------------------------------------------------------------
# Credit / Debit card — Luhn algorithm (ISO/IEC 7812)
# ---------------------------------------------------------------------------

def luhn_checksum_valid(card_number: str) -> bool:
    digits = [int(d) for d in card_number if d.isdigit()]
    if not (13 <= len(digits) <= 19):
        return False
    total = 0
    reverse_digits = digits[::-1]
    for i, d in enumerate(reverse_digits):
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


# ---------------------------------------------------------------------------
# PAN — structural validation (4th character encodes holder type)
# ---------------------------------------------------------------------------

_PAN_HOLDER_TYPES = set("PCHFATBLJG")  # Individual, Company, HUF, Firm, AOP, Trust, BOI, Local, Govt, AOP(Govt)


def pan_structure_valid(pan: str) -> bool:
    pan = pan.strip().upper()
    if len(pan) != 10:
        return False
    if not (pan[0:5].isalpha() and pan[5:9].isdigit() and pan[9].isalpha()):
        return False
    return pan[3] in _PAN_HOLDER_TYPES


# ---------------------------------------------------------------------------
# IFSC — structural validation (5th character is always '0', reserved for future use)
# ---------------------------------------------------------------------------

def ifsc_structure_valid(ifsc: str) -> bool:
    ifsc = ifsc.strip().upper()
    if len(ifsc) != 11:
        return False
    return ifsc[:4].isalpha() and ifsc[4] == "0" and ifsc[5:].isalnum()
