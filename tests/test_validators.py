"""
test_validators.py
Tests use SYNTHETIC numbers constructed to satisfy/fail the checksum
math itself — none of these are real people's documents.
"""
from core import validators


def test_luhn_valid_known_test_number():
    # 4111111111111111 is the universally-used Luhn-valid VISA TEST number
    # (published by payment networks specifically for testing).
    assert validators.luhn_checksum_valid("4111111111111111") is True


def test_luhn_invalid_random_digits():
    assert validators.luhn_checksum_valid("1234567890123456") is False


def test_pan_structure_valid_individual():
    assert validators.pan_structure_valid("ABCPE1234F") is True  # 4th char 'P' = individual


def test_pan_structure_invalid_bad_holder_type():
    assert validators.pan_structure_valid("ABCZE1234F") is False  # 'Z' is not a valid holder type


def test_pan_structure_invalid_length():
    assert validators.pan_structure_valid("ABC123") is False


def test_ifsc_structure_valid():
    assert validators.ifsc_structure_valid("SBIN0001234") is True


def test_ifsc_structure_invalid_fifth_char():
    assert validators.ifsc_structure_valid("SBIN1001234") is False  # 5th char must be '0'


def test_aadhaar_rejects_leading_zero_or_one():
    # Even if the remaining 11 digits happened to checksum correctly,
    # UIDAI never issues numbers starting with 0 or 1.
    assert validators.aadhaar_structure_valid("012345678901") is False


def test_aadhaar_accepts_synthetic_checksum_valid_number():
    # 234567890124 is a SYNTHETIC number generated purely to satisfy the
    # Verhoeff math for this test — it is not, and does not correspond
    # to, any real person's Aadhaar number.
    assert validators.aadhaar_structure_valid("234567890124") is True


def test_aadhaar_rejects_wrong_length():
    assert validators.aadhaar_structure_valid("12345") is False
