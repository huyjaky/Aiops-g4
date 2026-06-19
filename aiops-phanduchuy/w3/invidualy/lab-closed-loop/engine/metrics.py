"""
engine/metrics.py — Prometheus metrics for the closed-loop orchestrator.

Exposes an HTTP server on port 9100 (scraped by Prometheus as job=closed-loop).
All metrics use label cardinality that matches the 5-service Ronki topology.
"""

from prometheus_client import Counter, Gauge, start_http_server

# ── Counters ──────────────────────────────────────────────────────────────────

action_counter = Counter(
    "closed_loop_actions_total",
    "Total closed-loop actions executed",
    ["service", "runbook", "outcome"],  # outcome: success | rollback | fail | dry_run
)

# ── Gauges ────────────────────────────────────────────────────────────────────

circuit_breaker_gauge = Gauge(
    "closed_loop_circuit_breaker_state",
    "Circuit-breaker state per service (0=closed 1=open)",
    ["service"],
)

blast_radius_gauge = Gauge(
    "closed_loop_blast_radius_remaining",
    "Remaining actions allowed in the current blast-radius window",
    ["service"],
)

mutex_gauge = Gauge(
    "closed_loop_mutex_locked",
    "Per-service mutex state (0=free 1=locked)",
    ["service"],
)

verify_status_gauge = Gauge(
    "closed_loop_verify_status",
    "Last verify result per service+runbook (0=fail 1=pass 2=in_progress)",
    ["service", "runbook"],
)

# ── Server ────────────────────────────────────────────────────────────────────

_METRICS_PORT = 9100
_started = False


def start_metrics_server(port: int = _METRICS_PORT) -> None:
    """Start the Prometheus HTTP server. Safe to call multiple times (idempotent)."""
    global _started
    if _started:
        return
    start_http_server(port)
    _started = True
