"""
train.py
========
Trains a YOLOv8 model on the ID-card-layout dataset.

⚠️ IMPORTANT — read this before running in your own environment:

In THIS sandbox, pretrained COCO weights (yolov8n.pt) cannot be
downloaded — the egress proxy here blocks `release-assets.githubusercontent.com`,
which is where ultralytics fetches them from. So this script trains
from a random-initialized architecture (`yolov8n.yaml`) instead of
fine-tuning pretrained weights. That makes the resulting model purely
a pipeline proof — don't expect strong real-world accuracy from it.

ON YOUR OWN MACHINE (normal internet access), change ONE line:

    model = YOLO("yolov8n.yaml")      # this sandbox (no internet to GitHub releases)
    model = YOLO("yolov8n.pt")        # <-- your machine: auto-downloads COCO-pretrained
                                       #     weights and fine-tunes them (transfer learning).
                                       #     This converges faster and far more accurately,
                                       #     especially with a small dataset like this one.

Usage:
    python cv/train.py --epochs 10 --imgsz 256
"""

from __future__ import annotations
import argparse
import os
from ultralytics import YOLO

DATASET_YAML = os.path.join(os.path.dirname(__file__), "dataset", "data.yaml")
PRETRAINED_AVAILABLE = os.getenv("AI_SDDS_PRETRAINED_AVAILABLE", "false").lower() == "true"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--imgsz", type=int, default=256)
    parser.add_argument("--batch", type=int, default=8)
    parser.add_argument("--out", default="id_layout")
    args = parser.parse_args()

    base = "yolov8n.pt" if PRETRAINED_AVAILABLE else "yolov8n.yaml"
    print(f"आधार मॉडल: {base}  (pretrained={PRETRAINED_AVAILABLE})")
    model = YOLO(base)

    model.train(
        data=DATASET_YAML,
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        device="cpu",
        project=os.path.join(os.path.dirname(__file__), "runs"),
        name=args.out,
        plots=False,   # avoids an extra Arial.ttf download attempt in restricted sandboxes
        verbose=False,
    )

    best_weights = os.path.join(os.path.dirname(__file__), "runs", args.out, "weights", "best.pt")
    print(f"\nप्रशिक्षण पूरा। weights यहाँ हैं: {best_weights}")
    print(f"उपयोग के लिए: export AI_SDDS_YOLO_WEIGHTS={best_weights}")


if __name__ == "__main__":
    main()
