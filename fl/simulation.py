"""
simulation.py
=============
Runs the federated simulation: N clients, each training only on its
own local partition, with a central FedAvg strategy aggregating their
weight updates round by round. Evaluation against the held-out
global_test set happens centrally — using a SEPARATE benchmark
dataset, never any client's own data — and is reported per round so
you can see the global model actually improving.

Run: python -m fl.simulation
"""

from __future__ import annotations
import os
from typing import List, Tuple, Dict

import flwr as fl
from flwr.common import Metrics
import torch
import torch.nn as nn

from .client import FlowerClient
from .model import TinyClassifier, get_parameters, set_parameters, load_dataloader

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
N_CLIENTS = 4


def client_fn(context: fl.common.Context) -> fl.client.Client:
    client_id = context.node_config.get("partition-id", 0)
    data_dir = os.path.join(DATA_DIR, f"client_{client_id}")
    return FlowerClient(client_id=str(client_id), data_dir=data_dir).to_client()


def weighted_average(metrics: List[Tuple[int, Metrics]]) -> Metrics:
    accuracies = [num_examples * m["accuracy"] for num_examples, m in metrics]
    total_examples = sum(num_examples for num_examples, _ in metrics)
    return {"accuracy": sum(accuracies) / total_examples}


def evaluate_global_model(server_round: int, parameters, config) -> Tuple[float, Dict]:
    """Centralized evaluation on the held-out benchmark set — this is
    the ONLY place test data is used, and it was never any client's
    training data (see generate_crops_dataset.py)."""
    model = TinyClassifier()
    set_parameters(model, parameters)
    loader = load_dataloader(os.path.join(DATA_DIR, "global_test"), batch_size=32, shuffle=False)

    criterion = nn.CrossEntropyLoss()
    model.eval()
    total_loss, correct, total = 0.0, 0, 0
    with torch.no_grad():
        for x, y in loader:
            out = model(x)
            loss = criterion(out, y)
            total_loss += loss.item() * len(y)
            correct += (out.argmax(dim=1) == y).sum().item()
            total += len(y)

    accuracy = correct / max(total, 1)
    print(f"  [round {server_round}] global_test accuracy = {accuracy:.2%}")
    return total_loss / max(total, 1), {"global_accuracy": accuracy}


def run_simulation(n_rounds: int = 5, n_clients: int = N_CLIENTS):
    initial_model = TinyClassifier()

    strategy = fl.server.strategy.FedAvg(
        fraction_fit=1.0,
        fraction_evaluate=1.0,
        min_fit_clients=n_clients,
        min_evaluate_clients=n_clients,
        min_available_clients=n_clients,
        evaluate_metrics_aggregation_fn=weighted_average,
        evaluate_fn=evaluate_global_model,
        initial_parameters=fl.common.ndarrays_to_parameters(get_parameters(initial_model)),
    )

    history = fl.simulation.start_simulation(
        client_fn=client_fn,
        num_clients=n_clients,
        config=fl.server.ServerConfig(num_rounds=n_rounds),
        strategy=strategy,
        client_resources={"num_cpus": 1},
        ray_init_args={"include_dashboard": False, "log_to_driver": False},
    )
    return history


if __name__ == "__main__":
    print(f"शुरू: {N_CLIENTS} clients, FedAvg aggregation\n")
    run_simulation()
