"""
main.py
=======
CLI demo for AI-SDDS Core Detection Engine.

Usage:
    python main.py path/to/document.jpg
    python main.py path/to/document.pdf
"""

from __future__ import annotations
import sys
import json
from core import detector


def main() -> int:
    if len(sys.argv) != 2:
        print("उपयोग: python main.py <file_path>")
        return 1

    path = sys.argv[1]
    with open(path, "rb") as fh:
        file_bytes = fh.read()

    result = detector.scan(file_bytes, filename=path)

    print(f"\nफ़ाइल: {path}")
    print(f"प्रकार: {result.mime_type}  |  आकार: {result.size_bytes} bytes")
    print(f"फैसला: {result.verdict}")
    print(f"कारण: {result.reason}\n")

    if result.findings:
        print("मिले हुए संवेदनशील क्षेत्र:")
        for f in result.findings:
            tag = "✓ validated" if f["validated"] else "  unvalidated"
            print(f"  - [{f['type']:<16}] {f['label']:<28} {f['masked_value']:<20} "
                  f"confidence={f['confidence']:.2f} ({tag})")
    print()
    return 0 if result.verdict != "REJECTED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
