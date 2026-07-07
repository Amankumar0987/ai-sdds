"""
vision_engine.py
=================
Phase 2: visual structure detection — finds ID-card-like signals even
when OCR finds NO readable text at all (blurry phone photo, glare,
heavily compressed image, etc).

Two independent layers, deliberately kept separate so one failing
never breaks the other:

  1. CLASSICAL CV (always available, zero network/model dependency)
     - Face detection (Haar cascade, bundled inside opencv-python)
       -> most government ID cards/passports carry a passport-style photo.
     - QR code detection (OpenCV's built-in QRCodeDetector)
       -> Aadhaar, many bank documents, and modern PANs carry a QR code.

  2. YOLOv8 LAYOUT MODEL (optional — only used if a trained weights
     file is present at the configured path). Detects finer-grained
     regions: photo box, QR box, government emblem/logo, signature
     strip. See cv/train.py for how to train this once you have a
     labeled dataset and (importantly) unrestricted internet access
     to pull COCO-pretrained YOLOv8 weights for transfer learning.
"""

from __future__ import annotations
import os
from dataclasses import dataclass

import cv2
print("cv2 =", cv2)
print("cv2 file =", getattr(cv2, "__file__", None))
print("has Cascade =", hasattr(cv2, "CascadeClassifier"))
import numpy as np
from PIL import Image

_FACE_CASCADE_PATH = os.path.join(cv2.data.haarcascades, "haarcascade_frontalface_alt2.xml")
_face_detector = cv2.CascadeClassifier(_FACE_CASCADE_PATH)
_qr_detector = cv2.QRCodeDetector()

YOLO_WEIGHTS_ENV_VAR = "AI_SDDS_YOLO_WEIGHTS"


@dataclass
class VisualFinding:
    type: str          # "FACE_PHOTO" | "QR_CODE" | "ID_LAYOUT_<class>"
    confidence: float
    bbox: tuple[int, int, int, int] | None = None  # x, y, w, h in pixels

    def to_dict(self) -> dict:
        return {"type": self.type, "confidence": round(self.confidence, 2), "bbox": self.bbox}


def _pil_to_cv2_gray(image: Image.Image) -> np.ndarray:
    arr = np.array(image.convert("RGB"))
    return cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)


def detect_face_photo(image: Image.Image) -> list[VisualFinding]:
    """Most Indian ID documents (Aadhaar, PAN, passport, driving licence)
    carry a small passport-style face photo. Detecting one is a strong
    structural signal even with zero readable OCR text."""
    gray = _pil_to_cv2_gray(image)
    faces = _face_detector.detectMultiScale(
        gray, scaleFactor=1.1, minNeighbors=6, minSize=(40, 40)
    )
    findings = []
    for (x, y, w, h) in faces:
        # Haar cascades don't output a real confidence score; we derive
        # a simple proxy from relative face size (tiny spurious detections
        # in noisy backgrounds tend to be small).
        rel_size = (w * h) / (gray.shape[0] * gray.shape[1])
        confidence = min(0.55 + rel_size * 4, 0.85)
        findings.append(VisualFinding("FACE_PHOTO", confidence, (int(x), int(y), int(w), int(h))))
    return findings


def detect_qr_code(image: Image.Image) -> list[VisualFinding]:
    arr = np.array(image.convert("RGB"))
    retval, points = _qr_detector.detect(arr)
    if not retval or points is None:
        return []
    x, y = points[0][:, 0].min(), points[0][:, 1].min()
    w = points[0][:, 0].max() - x
    h = points[0][:, 1].max() - y
    return [VisualFinding("QR_CODE", 0.80, (int(x), int(y), int(w), int(h)))]


class YoloLayoutModel:
    """Thin, optional wrapper. If no weights file is configured/found,
    every method returns an empty list — callers never need to branch
    on whether the model is available."""

    def __init__(self, weights_path: str | None = None):
        self.weights_path = weights_path or os.getenv(YOLO_WEIGHTS_ENV_VAR)
        self._model = None
        if self.weights_path and os.path.exists(self.weights_path):
            from ultralytics import YOLO  # imported lazily: heavy dependency, optional feature
            self._model = YOLO(self.weights_path)

    @property
    def available(self) -> bool:
        return self._model is not None

    def detect(self, image: Image.Image, conf: float = 0.4) -> list[VisualFinding]:
        if not self._model:
            return []
        results = self._model.predict(image, conf=conf, verbose=False)
        findings = []
        for r in results:
            for box in r.boxes:
                cls_name = r.names[int(box.cls[0])]
                x1, y1, x2, y2 = [int(v) for v in box.xyxy[0].tolist()]
                findings.append(
                    VisualFinding(f"ID_LAYOUT_{cls_name.upper()}", float(box.conf[0]), (x1, y1, x2 - x1, y2 - y1))
                )
        return findings


def scan_image(image: Image.Image, yolo_model: YoloLayoutModel | None = None) -> list[dict]:
    """Run every available visual detector and return a flat list of
    finding dicts, in the same shape patterns.scan_text() findings use,
    so detector.py can merge both lists uniformly."""
    findings: list[VisualFinding] = []
    findings += detect_face_photo(image)
    findings += detect_qr_code(image)
    if yolo_model and yolo_model.available:
        findings += yolo_model.detect(image)
    return [f.to_dict() for f in findings]
