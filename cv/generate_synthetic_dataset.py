"""
generate_synthetic_dataset.py
==============================
Generates a small synthetic "ID-card-layout" dataset to prove the
YOLOv8 training pipeline end-to-end, WITHOUT using any real ID card
images or any real person's photo/data (both for privacy reasons and
because no such labeled dataset is available here).

Each synthetic image is a plain card-shaped rectangle containing:
  - class 0 "photo"   — a gray rectangle with a simple oval (face proxy)
  - class 1 "qr_code" — a black/white noise grid (QR-code proxy)
  - class 2 "logo"    — a small colored circle in a corner (emblem proxy)
at randomized positions/sizes, with YOLO-format bounding-box labels
written alongside each image.

This is NOT a substitute for a real labeled dataset of real ID layouts
— it exists purely to validate that data prep -> training -> inference
works end-to-end. Swap in a real (consented/synthetic-but-realistic)
dataset before relying on this for production accuracy.
"""

from __future__ import annotations
import os
import random
from PIL import Image, ImageDraw

CLASSES = ["photo", "qr_code", "logo"]
OUT_DIR = os.path.join(os.path.dirname(__file__), "dataset")
IMG_SIZE = 256


def _draw_photo(draw: ImageDraw.ImageDraw, box):
    x1, y1, x2, y2 = box
    draw.rectangle(box, fill=(180, 180, 190))
    cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
    w, h = (x2 - x1) * 0.7, (y2 - y1) * 0.8
    draw.ellipse([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2], fill=(150, 120, 100))


def _draw_qr(draw: ImageDraw.ImageDraw, box):
    x1, y1, x2, y2 = box
    cell = max(2, int((x2 - x1) / 10))
    for yy in range(int(y1), int(y2), cell):
        for xx in range(int(x1), int(x2), cell):
            if random.random() > 0.5:
                draw.rectangle([xx, yy, xx + cell, yy + cell], fill="black")
    draw.rectangle(box, outline="black", width=1)


def _draw_logo(draw: ImageDraw.ImageDraw, box):
    x1, y1, x2, y2 = box
    color = random.choice([(31, 56, 100), (160, 30, 30), (30, 120, 70)])
    draw.ellipse(box, fill=color)


_DRAWERS = {"photo": _draw_photo, "qr_code": _draw_qr, "logo": _draw_logo}


def _random_box(used_boxes, size_range=(35, 70)):
    for _ in range(20):
        w = random.randint(*size_range)
        h = random.randint(*size_range)
        x1 = random.randint(10, IMG_SIZE - w - 10)
        y1 = random.randint(10, IMG_SIZE - h - 10)
        box = (x1, y1, x1 + w, y1 + h)
        if not any(_overlaps(box, b) for b in used_boxes):
            return box
    return None


def _overlaps(a, b):
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    return ax1 < bx2 and ax2 > bx1 and ay1 < by2 and ay2 > by1


def _to_yolo_label(box, cls_index, img_size=IMG_SIZE):
    x1, y1, x2, y2 = box
    cx = (x1 + x2) / 2 / img_size
    cy = (y1 + y2) / 2 / img_size
    w = (x2 - x1) / img_size
    h = (y2 - y1) / img_size
    return f"{cls_index} {cx:.5f} {cy:.5f} {w:.5f} {h:.5f}"


def generate_one(idx: int, split: str):
    img = Image.new("RGB", (IMG_SIZE, IMG_SIZE), color=(245, 245, 240))
    draw = ImageDraw.Draw(img)
    # background "card" border so it's not just blank
    draw.rectangle([4, 4, IMG_SIZE - 4, IMG_SIZE - 4], outline=(200, 200, 200), width=2)
    # a few gray "text line" bars for clutter (not a labeled class)
    for _ in range(random.randint(2, 4)):
        y = random.randint(20, IMG_SIZE - 20)
        x1 = random.randint(15, 60)
        x2 = x1 + random.randint(60, 140)
        draw.rectangle([x1, y, x2, y + 6], fill=(210, 210, 210))

    used_boxes = []
    labels = []
    classes_present = random.sample(CLASSES, k=random.randint(2, 3))
    for cls in classes_present:
        size_range = (30, 55) if cls != "photo" else (45, 75)
        box = _random_box(used_boxes, size_range)
        if box is None:
            continue
        used_boxes.append(box)
        _DRAWERS[cls](draw, box)
        labels.append(_to_yolo_label(box, CLASSES.index(cls)))

    img_path = os.path.join(OUT_DIR, "images", split, f"synthetic_{idx:04d}.png")
    label_path = os.path.join(OUT_DIR, "labels", split, f"synthetic_{idx:04d}.txt")
    img.save(img_path)
    with open(label_path, "w") as fh:
        fh.write("\n".join(labels))


def main(n_train: int = 60, n_val: int = 15):
    for split in ("train", "val"):
        os.makedirs(os.path.join(OUT_DIR, "images", split), exist_ok=True)
        os.makedirs(os.path.join(OUT_DIR, "labels", split), exist_ok=True)

    random.seed(42)
    for i in range(n_train):
        generate_one(i, "train")
    for i in range(n_val):
        generate_one(1000 + i, "val")

    data_yaml = os.path.join(OUT_DIR, "data.yaml")
    with open(data_yaml, "w") as fh:
        fh.write(
            f"path: {OUT_DIR}\n"
            f"train: images/train\n"
            f"val: images/val\n"
            f"names:\n"
            + "\n".join(f"  {i}: {name}" for i, name in enumerate(CLASSES))
            + "\n"
        )
    print(f"बनाया गया: {n_train} train + {n_val} val images, classes={CLASSES}")
    print(f"data.yaml -> {data_yaml}")


if __name__ == "__main__":
    main()
