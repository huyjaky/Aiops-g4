# ADR 001: Using Grafana Alloy as Unified Telemetry Collection Agent

*   **Status**: Approved
*   **Author**: Platform Architect Team
*   **Date**: 2026-06-12

---

## 1. Context
Currently, the GeekShop observability infrastructure runs two proprietary agents in parallel on each of our 300 hosts: **Datadog Agent** (collecting system metrics, APM traces, logs) and **Splunk Universal Forwarder** (collecting `stdout/stderr` logs for the security and compliance team).

This multi-agent architecture introduces several critical pain points:
1.  **High Resource Footprint**: Running two concurrent agents consumes significant CPU and memory resources across all 300 application hosts.
2.  **Lack of Correlation at Source**: Metrics, logs, and traces are collected independently by different agents, making it impossible to unify labels or synchronize data paths at the collection layer.
3.  **Lack of Cost-Control Mechanisms**: Neither agent allows local, in-flight data processing (such as dynamic cardinality filtering or tail-based sampling for traces) before data leaves our network. This leads directly to custom metrics budget overages ($2,200/month) and forces us to limit tracing sampling to a flat 1% to prevent Datadog billing spikes.

We need a single, open-source, OpenTelemetry-compliant collection agent capable of running unified processing and filtering rules at the host level.

---

## 2. Decision
We decide to replace both Datadog Agent and Splunk Universal Forwarder with **Grafana Alloy** as the single unified telemetry collection agent across all 300 GeekShop hosts and Kubernetes clusters.

Grafana Alloy will perform the following functions:
*   Scrape system and infrastructure metrics (replacing Datadog Infra).
*   Ingest distributed traces from application code instrumented with the OpenTelemetry SDK (replacing Datadog APM).
*   Collect container logs from standard outputs (`stdout/stderr`) and system log files (replacing Splunk Universal Forwarder).
*   Apply local OTel processors to strip out dynamic, high-cardinality tags (such as `customer_id`) at the source to prevent metric cardinality budget explosions.
*   Enforce **Tail-Based Tracing Sampling**: Hold traces in local memory buffer for 5 seconds to evaluate their outcome; ingest 100% of error traces (HTTP 5xx) and slow traces (> 2s latency), while sampling only 0.1% of successful traces.

---

## 3. Alternatives Considered & Rejected

### Alternative A: Keep Datadog Agent + Splunk Universal Forwarder
*   *Why Rejected*: This alternative maintains vendor lock-in and fails to solve the 70% cost reduction requirement. Datadog's host-based pricing ($40/host for APM) is too expensive for our 300-host scale, and Splunk maintains high log-indexing fees without allowing S3-archive redirection at the collection tier.

### Alternative B: Deploy Standard OpenTelemetry Collector (Standard OTel Collector)
*   *Why Rejected*: The standard OTel Collector is a powerful tool but relies on static YAML configurations, making dynamic service discovery difficult in our auto-scaling environments. Additionally, it lacks native optimization components for writing directly to Grafana Mimir (via Prometheus remote write) and Grafana Loki compared to Grafana Alloy, which uses the dynamic "River" configuration language supporting hot-reloads without process restarts.

---

## 4. Consequences

### Positive
*   **Reduced Resource Footprint**: Consolidating two agents into a single agent reduces host CPU and memory consumption to under 2% per node.
*   **Standardization on OpenTelemetry**: Eliminates proprietary agent SDK dependencies, shifting application code to the open OpenTelemetry standard. This enables us to change backend stores in the future without code changes.
*   **Resolved Capability Gaps**: Solves the 1% trace sampling limit (capturing 100% of errors via tail-sampling) and blocks metric cardinality leaks before data leaves the local network.

### Negative
*   **Learning Curve (Skills Gap)**: The Platform and SRE teams must learn Grafana Alloy's new configuration language (**River**), which is modeled after Terraform's HCL rather than standard YAML.
*   **Migration Effort**: Requires rewriting configuration files and deploying a parallel daemonset configuration across 300 hosts during a controlled transition phase to prevent observability blackouts.
