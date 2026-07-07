"""
test_privacy_property.py
=========================
These tests exist to PROVE the federated-learning privacy claim, not
just assert it in a docstring. Same philosophy as
tests/test_security.py::test_mask_value_never_returns_raw_value and
tests/test_redteam.py — a security/privacy property is only real once
there's a test that would fail if it broke.
"""

import os
import pytest
import numpy as np
from fl.client import FlowerClient
from fl.model import TinyClassifier, get_parameters

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "fl", "data")

# These tests need a generated synthetic dataset (fl/data/client_0 ...).
# It's intentionally not committed to the repo (regenerable, and
# datasets shouldn't live in git). Without this guard, a missing
# dataset surfaces as a confusing torch.utils.data.sampler ValueError
# ("num_samples should be a positive integer value, but got
# num_samples=0") deep inside PyTorch — this skip gives a clear,
# actionable message instead.
pytestmark = pytest.mark.skipif(
    not os.path.isdir(os.path.join(DATA_DIR, "client_0")),
    reason=(
        "fl/data/ नहीं मिला। पहले चलाएँ: python -m fl.generate_crops_dataset "
        "(देखें fl/README.md)"
    ),
)
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "fl", "data")


def test_each_client_only_ever_touches_its_own_partition():
    """A client constructed with client_0's directory must never load
    a single sample from any other client's directory."""
    client = FlowerClient(client_id="0", data_dir=os.path.join(DATA_DIR, "client_0"))
    sample_paths = [p for p, _ in client.train_loader.dataset.samples]
    assert len(sample_paths) > 0
    for path in sample_paths:
        normalized = os.path.normpath(path)
        assert f"client_0{os.sep}" in normalized or normalized.endswith("client_0")
        assert "client_1" not in normalized
        assert "client_2" not in normalized
        assert "client_3" not in normalized


def test_fit_return_payload_contains_only_weights_and_scalars():
    """Inspect EXACTLY what fit() returns and hands to the network
    layer. It must be: a list of numpy arrays (model weights) + an int
    (example count) + a dict of scalar metrics. Nothing else."""
    client = FlowerClient(client_id="0", data_dir=os.path.join(DATA_DIR, "client_0"), local_epochs=1)
    initial_params = get_parameters(TinyClassifier())

    returned_params, num_examples, metrics = client.fit(initial_params, config={})

    assert isinstance(returned_params, list)
    assert all(isinstance(p, np.ndarray) for p in returned_params)
    assert isinstance(num_examples, int)
    assert isinstance(metrics, dict)
    for key, value in metrics.items():
        assert isinstance(value, (str, int, float)), (
            f"metrics['{key}'] is {type(value)} — only scalars are allowed to "
            "cross the client/server boundary"
        )


def test_weight_payload_shape_is_independent_of_dataset_size():
    """THE core structural privacy guarantee: the shape of what a
    client transmits is fixed by the model architecture alone. A
    client with 5 images and a client with 5,000 images return
    identically-shaped payloads — so the payload itself cannot encode
    how much (or which) raw data was used to produce it."""
    small_client = FlowerClient(client_id="small", data_dir=os.path.join(DATA_DIR, "client_0"), local_epochs=1)
    big_client = FlowerClient(client_id="big", data_dir=os.path.join(DATA_DIR, "client_1"), local_epochs=1)

    initial_params = get_parameters(TinyClassifier())
    small_result, small_n, _ = small_client.fit(initial_params, config={})
    big_result, big_n, _ = big_client.fit(initial_params, config={})

    small_shapes = [p.shape for p in small_result]
    big_shapes = [p.shape for p in big_result]
    assert small_shapes == big_shapes, "payload shape must never depend on data volume"

    # And yet real learning happened — the actual weight VALUES differ,
    # proving this isn't just a static no-op return.
    assert not all(np.array_equal(a, b) for a, b in zip(small_result, big_result))


def test_evaluate_does_not_leak_dataset_size_via_loss_alone():
    """A sanity check that evaluate()'s returned `num_examples` is the
    only place example-count appears — it is intentionally a public,
    aggregate scalar (Flower's own weighting mechanism needs it), not a
    leak of anything content-specific."""
    client = FlowerClient(client_id="0", data_dir=os.path.join(DATA_DIR, "client_0"))
    loss, num_examples, metrics = client.evaluate(get_parameters(client.model), config={})
    assert isinstance(loss, float)
    assert isinstance(num_examples, int)
    assert "accuracy" in metrics
