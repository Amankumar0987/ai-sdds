"""
model.py
========
A deliberately tiny CNN — this FL demo exists to prove the federated
ARCHITECTURE is correct (privacy property + weight aggregation), not
to build a state-of-the-art classifier. A bigger model would only make
the simulation slower without making the privacy proof any stronger.
"""

from __future__ import annotations
import os
from collections import OrderedDict

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
from PIL import Image

CLASSES = ["photo", "qr_code", "logo", "background"]
TILE_SIZE = 32


class TinyClassifier(nn.Module):
    def __init__(self, num_classes: int = 4):
        super().__init__()
        self.conv1 = nn.Conv2d(3, 8, kernel_size=3, padding=1)
        self.conv2 = nn.Conv2d(8, 16, kernel_size=3, padding=1)
        self.pool = nn.MaxPool2d(2, 2)
        self.fc1 = nn.Linear(16 * 8 * 8, 32)
        self.fc2 = nn.Linear(32, num_classes)

    def forward(self, x):
        x = self.pool(F.relu(self.conv1(x)))   # 32x32 -> 16x16
        x = self.pool(F.relu(self.conv2(x)))   # 16x16 -> 8x8
        x = x.view(x.size(0), -1)
        x = F.relu(self.fc1(x))
        return self.fc2(x)


class TileDataset(Dataset):
    """Loads images from disk paths and labels — used identically by
    every client, each pointed only at its OWN partition directory."""

    def __init__(self, root_dir: str):
        self.samples: list[tuple[str, int]] = []
        for idx, cls in enumerate(CLASSES):
            cls_dir = os.path.join(root_dir, cls)
            if not os.path.isdir(cls_dir):
                continue
            for fname in sorted(os.listdir(cls_dir)):
                self.samples.append((os.path.join(cls_dir, fname), idx))

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        path, label = self.samples[idx]
        img = Image.open(path).convert("RGB")
        arr = np.asarray(img, dtype=np.float32).transpose(2, 0, 1) / 255.0
        return torch.from_numpy(arr), label


def load_dataloader(root_dir: str, batch_size: int = 16, shuffle: bool = True) -> DataLoader:
    return DataLoader(TileDataset(root_dir), batch_size=batch_size, shuffle=shuffle)


# --- Helpers for converting between PyTorch state_dict and the plain
# numpy-array lists that Flower's NumPyClient interface requires. This
# is the ONLY thing that ever crosses the client<->server boundary. ---

def get_parameters(model: nn.Module) -> list[np.ndarray]:
    return [val.cpu().numpy() for val in model.state_dict().values()]


def set_parameters(model: nn.Module, parameters: list[np.ndarray]) -> None:
    params_dict = zip(model.state_dict().keys(), parameters)
    state_dict = OrderedDict({k: torch.tensor(v) for k, v in params_dict})
    model.load_state_dict(state_dict, strict=True)
