"""
test_api.py
===========
These env vars MUST be set before `api.app` is imported, since
config.py reads them once at import time.
"""
import os
os.environ["AI_SDDS_REQUIRE_API_KEY"] = "true"
os.environ["AI_SDDS_API_KEYS"] = "test-key-123"
os.environ["AI_SDDS_RATE_LIMIT"] = "3/minute"

import io
import pytest
from PIL import Image
from fastapi.testclient import TestClient
from api.app import app, limiter

client = TestClient(app)
HEADERS = {"X-API-Key": "test-key-123"}


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """Without this, tests are order-dependent: test_rate_limit_blocks_
    excess_requests deliberately exhausts the 3/minute limit, and every
    later test in this module would then get 429'd by slowapi (whose
    storage persists for the lifetime of the `limiter` object, not per
    test). Resetting before each test makes every test independent of
    what ran before it — found via a real pytest run where this exact
    pollution made test_metrics_endpoint_tracks_scan_counts fail."""
    limiter.reset()
    yield


def _png_bytes(w=50, h=50):
    buf = io.BytesIO()
    Image.new("RGB", (w, h), color="white").save(buf, format="PNG")
    return buf.getvalue()


def test_health_does_not_require_auth():
    resp = client.get("/v1/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_scan_without_api_key_is_rejected():
    files = {"file": ("test.png", _png_bytes(), "image/png")}
    resp = client.post("/v1/scan", files=files)
    assert resp.status_code == 401


def test_scan_with_wrong_api_key_is_rejected():
    files = {"file": ("test.png", _png_bytes(), "image/png")}
    resp = client.post("/v1/scan", files=files, headers={"X-API-Key": "wrong-key"})
    assert resp.status_code == 401


def test_scan_with_valid_key_succeeds():
    files = {"file": ("test.png", _png_bytes(), "image/png")}
    resp = client.post("/v1/scan", files=files, headers=HEADERS)
    assert resp.status_code == 200
    body = resp.json()
    assert "verdict" in body and "findings" in body


def test_scan_rejects_fake_file_type():
    files = {"file": ("test.png", b"not actually a png", "image/png")}
    resp = client.post("/v1/scan", files=files, headers=HEADERS)
    assert resp.status_code == 200
    assert resp.json()["verdict"] == "REJECTED"


def test_oversized_upload_rejected_via_content_length():
    big_payload = b"0" * (15 * 1024 * 1024 + 10_000)  # > 15MB cap
    files = {"file": ("big.png", big_payload, "image/png")}
    resp = client.post("/v1/scan", files=files, headers=HEADERS)
    assert resp.status_code == 413


def test_rate_limit_blocks_excess_requests():
    files = {"file": ("test.png", _png_bytes(), "image/png")}
    statuses = []
    for _ in range(5):  # limit is set to 3/minute above
        resp = client.post("/v1/scan", files=files, headers=HEADERS)
        statuses.append(resp.status_code)
    assert 429 in statuses


def test_metrics_endpoint_tracks_scan_counts():
    files = {"file": ("test.png", _png_bytes(), "image/png")}
    before = client.get("/v1/metrics").text

    client.post("/v1/scan", files=files, headers=HEADERS)

    after_resp = client.get("/v1/metrics")
    assert after_resp.status_code == 200
    assert "text/plain" in after_resp.headers["content-type"]
    after = after_resp.text
    assert "ai_sdds_scans_total" in after
    assert "ai_sdds_scan_duration_seconds" in after
    # the counter for at least one verdict must have gone up
    assert after != before


def test_metrics_endpoint_never_leaks_file_content():
    files = {"file": ("secret_doc.png", _png_bytes(), "image/png")}
    client.post("/v1/scan", files=files, headers=HEADERS)
    body = client.get("/v1/metrics").text
    assert "secret_doc" not in body
