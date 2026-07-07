"""
client.py
=========
This is THE privacy-critical file. Read it carefully:

- `fit()` trains on `self.train_loader`, which is built from ONE
  client's own directory (see simulation.py) — never any other
  client's data, never the global test set.
- `fit()` returns `get_parameters(model)` — a list of numpy arrays
  whose SHAPE is fixed by the model architecture (see model.py) and
  is therefore completely independent of how much/which image data
  was used to train. This is the structural guarantee that no raw
  image data can leak through this return value — see
  tests/test_privacy_property.py for a test that proves this.
- Nothing in this file ever reads, returns, or logs a file path, a
  pixel array, or anything dataset-derived other than aggregate
  scalars (loss/accuracy) and the model weights themselves.
"""

from __future__ import annotations
import torch
import torch.nn as nn
import flwr as fl

from .model import TinyClassifier, get_parameters, set_parameters, load_dataloader


class FlowerClient(fl.client.NumPyClient):
    def __init__(self, client_id: str, data_dir: str, local_epochs: int = 1):
        self.client_id = client_id
        self.model = TinyClassifier()
        self.train_loader = load_dataloader(data_dir, batch_size=16, shuffle=True)
        self.local_epochs = local_epochs

    def get_parameters(self, config):
        return get_parameters(self.model)

    def fit(self, parameters, config):
        set_parameters(self.model, parameters)
        optimizer = torch.optim.Adam(self.model.parameters(), lr=0.01)
        criterion = nn.CrossEntropyLoss()

        self.model.train()
        total_loss, total_examples = 0.0, 0
        for _ in range(self.local_epochs):
            for x, y in self.train_loader:
                optimizer.zero_grad()
                out = self.model(x)
                loss = criterion(out, y)
                loss.backward()
                optimizer.step()
                total_loss += loss.item() * len(y)
                total_examples += len(y)

        avg_loss = total_loss / max(total_examples, 1)
        # Returned metrics are SCALARS ONLY (loss, example count) — no
        # dataset content of any kind.
        return get_parameters(self.model), total_examples, {"client_id": self.client_id, "train_loss": avg_loss}

    def evaluate(self, parameters, config):
        set_parameters(self.model, parameters)
        criterion = nn.CrossEntropyLoss()
        self.model.eval()

        total_loss, correct, total = 0.0, 0, 0
        with torch.no_grad():
            for x, y in self.train_loader:
                out = self.model(x)
                loss = criterion(out, y)
                total_loss += loss.item() * len(y)
                correct += (out.argmax(dim=1) == y).sum().item()
                total += len(y)

        accuracy = correct / max(total, 1)
        return total_loss / max(total, 1), total, {"accuracy": accuracy, "client_id": self.client_id}
