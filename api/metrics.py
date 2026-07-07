"""
metrics.py
==========
Phase 7 — production observability. Exposes counters/histograms in the
standard Prometheus text-exposition format at GET /v1/metrics.

Deliberately tracks ONLY non-sensitive, aggregate numbers — verdict
counts and latency. Never anything from a file's content (consistent
with the zero-retention principle that runs through the whole codebase).
"""

from prometheus_client import Counter, Histogram, CONTENT_TYPE_LATEST, generate_latest

SCANS_TOTAL = Counter(
    "ai_sdds_scans_total",
    "कुल scan requests, verdict के अनुसार विभाजित",
    ["verdict"],
)

SCAN_DURATION_SECONDS = Histogram(
    "ai_sdds_scan_duration_seconds",
    "एक scan request को पूरा होने में लगा समय (सेकंड)",
    buckets=(0.1, 0.25, 0.5, 1, 2, 5, 10, 15),
)

DEGRADED_MODE_EVENTS = Counter(
    "ai_sdds_degraded_mode_events_total",
    "वे मौके जब scanner त्रुटि के कारण fail-open हुआ",
)


def record_scan(verdict: str, duration_seconds: float, degraded: bool = False) -> None:
    SCANS_TOTAL.labels(verdict=verdict).inc()
    SCAN_DURATION_SECONDS.observe(duration_seconds)
    if degraded:
        DEGRADED_MODE_EVENTS.inc()


def render_latest() -> tuple[bytes, str]:
    return generate_latest(), CONTENT_TYPE_LATEST
