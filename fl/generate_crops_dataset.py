"""
generate_crops_dataset.py
==========================
Phase 3 — Federated Learning. Generates a small image-CLASSIFICATION
dataset (not object detection — kept deliberately lightweight so the
FL simulation runs in seconds on CPU, since the point here is to prove
the FEDERATED ARCHITECTURE works correctly, not to win an accuracy
benchmark).

4 classes: photo, qr_code, logo, background — same visual vocabulary
as cv/generate_synthetic_dataset.py from Phase 2, just cropped to
32x32 single-class tiles.

CRITICAL DESIGN POINT: this script partitions the data into N
non-overlapping client folders (data/client_0/, data/client_1/, ...).
In a real deployment, each of these folders would physically live on
a DIFFERENT device/organization's server and would NEVER be copied
anywhere else. The FL client code (client.py) only ever reads from its
OWN partition — this script existing in one place is purely a
simulation convenience for this sandbox demo.
"""

from __future__ import annotations
import os
import random
from PIL import Image, ImageDraw

CLASSES = ["photo", "qr_code", "logo", "background"]
TILE_SIZE = 32
OUT_DIR = os.path.join(os.path.dirname(__file__), "data")


def _make_photo_tile() -> Image.Image:
    img = Image.new("RGB", (TILE_SIZE, TILE_SIZE), (180, 180, 190))
    d = ImageDraw.Draw(img)
    d.ellipse([6, 4, 26, 28], fill=(150, 120, 100))
    return img


def _make_qr_tile() -> Image.Image:
    img = Image.new("RGB", (TILE_SIZE, TILE_SIZE), "white")
    d = ImageDraw.Draw(img)
    cell = 4
    for y in range(0, TILE_SIZE, cell):
        for x in range(0, TILE_SIZE, cell):
            if random.random() > 0.5:
                d.rectangle([x, y, x + cell, y + cell], fill="black")
    return img


def _make_logo_tile() -> Image.Image:
    img = Image.new("RGB", (TILE_SIZE, TILE_SIZE), (245, 245, 240))
    d = ImageDraw.Draw(img)
    color = random.choice([(31, 56, 100), (160, 30, 30), (30, 120, 70)])
    d.ellipse([4, 4, TILE_SIZE - 4, TILE_SIZE - 4], fill=color)
    return img


def _make_background_tile() -> Image.Image:
    shade = random.randint(200, 250)
    img = Image.new("RGB", (TILE_SIZE, TILE_SIZE), (shade, shade, shade - 5))
    d = ImageDraw.Draw(img)
    if random.random() > 0.5:
        y = random.randint(4, TILE_SIZE - 8)
        d.rectangle([4, y, TILE_SIZE - 4, y + 3], fill=(210, 210, 210))
    return img


_GENERATORS = {
    "photo": _make_photo_tile,
    "qr_code": _make_qr_tile,
    "logo": _make_logo_tile,
    "background": _make_background_tile,
}


def generate_partitioned_dataset(n_clients: int = 4, samples_per_class_per_client: int = 25, seed: int = 7):
    random.seed(seed)
    for client_id in range(n_clients):
        client_dir = os.path.join(OUT_DIR, f"client_{client_id}")
        for cls in CLASSES:
            cls_dir = os.path.join(client_dir, cls)
            os.makedirs(cls_dir, exist_ok=True)
            for i in range(samples_per_class_per_client):
                img = _GENERATORS[cls]()
                img.save(os.path.join(cls_dir, f"{cls}_{i:03d}.png"))

    # A held-out GLOBAL test set — generated separately, used only for
    # reporting how the aggregated global model performs. This is
    # standard ML practice (a benchmark set), not "centralized client
    # data" — no client's images are copied into it.
    test_dir = os.path.join(OUT_DIR, "global_test")
    for cls in CLASSES:
        cls_dir = os.path.join(test_dir, cls)
        os.makedirs(cls_dir, exist_ok=True)
        for i in range(15):
            img = _GENERATORS[cls]()
            img.save(os.path.join(cls_dir, f"{cls}_{i:03d}.png"))

    print(f"बनाया गया: {n_clients} client partitions, हर एक में {samples_per_class_per_client * len(CLASSES)} images")
    print(f"global_test: {15 * len(CLASSES)} images (सिर्फ़ benchmark के लिए, किसी client का डेटा नहीं)")


if __name__ == "__main__":
    generate_partitioned_dataset()
