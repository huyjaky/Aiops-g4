# SPEC: HuyPD AIOps Mini-Platform

## 1. Platform overview
The HuyPD AIOps Mini-Platform is an end-to-end intelligent observability and operations platform designed to monitor a 10-service e-commerce microservice stack. 

### Data Layer Architecture (from W1)
* **Collection:** OpenTelemetry (OTel) Collector gathers metrics (error rates, latencies) and system traces from the microservices.
* **Transport:** Apache Kafka acts as a message broker buffer, protecting downstream components from backpressure during high traffic spikes.
* **Processing:** Apache Flink handles stream processing and rolling aggregation of telemetry data in real-time.
* **Storage:** VictoriaMetrics handles hot/warm time-series storage, and Elasticsearch stores log lines and raw traces.
* **Query & ML:** Grafana serves as the visualization portal, and Python AI Services run machine learning detectors (3σ, Isolation Forest, etc.) to trigger anomalies.

The platform's scope includes real-time anomaly detection, temporal-topology alert correlation, and root cause analysis (RCA). Its non-scope is automated self-healing and service restarts, remaining an advisory tool for SREs and on-call engineers.

## 2. SLO definition (from W3-D1)
The platform monitors three core services with the following SLO configurations defined in `slo_spec.yaml`:

- **API Gateway (`api`):**
  - **Target SLO:** 99.9% availability over a 30-day window.
  - **SLI:** Count of HTTP responses returning 2xx/3xx/4xx (excluding 429) with latency < 500ms divided by total requests.
  - **Error budget:** 20,737 allowed failures per month (equivalent to 43 minutes of downtime).
  
- **Database Subsystem (`db`):**
  - **Target SLO:** 99.95% availability over a 30-day window.
  - **SLI:** Count of successful queries with duration < 100ms divided by total queries.
  - **Error budget:** 863 allowed failures per month (equivalent to 22 minutes of downtime).

- **Frontend Subsystem (`frontend`):**
  - **Target SLO:** 99.0% availability over a 30-day window.
  - **SLI:** RUM-reported page loads where DOM is ready < 3000ms with no JS errors or network errors.
  - **Error budget:** 51,840 allowed failures per month (equivalent to 432 minutes of downtime).

- **Burn-rate Alert Tiers (from `burn_rate_alerts.yaml`):**
  - **Tier 1 (Critical):** Burn rate >= 14.4x (evaluated over 1h and 5m windows). Actions: PagerDuty alert (SRE paged).
  - **Tier 2 (Warning):** Burn rate >= 6x (evaluated over 6h and 30m windows). Actions: PagerDuty alert.
  - **Tier 3 (Info/Ticket):** Burn rate >= 1x (evaluated over 3d and 6h windows). Actions: Ticket created in Jira backlog.

## 3. Detection + Correlation + RCA stack (from W1+W2)
- **Detector:** 3-sigma (3σ) dynamic anomaly detector on Prometheus HTTP/DB rate, error, and latency metrics. It outputs boolean anomaly flags with timestamps.
- **Correlator:** Temporal-Topology correlator. It groups active alerts into logical incident clusters using a sliding window of 120 seconds and a maximum topology distance of 2 hops (BFS on service dependency graph).
- **RCA:** Granger Causality temporal lag checking combined with Upstream Topology Bias. It references the service dependency graph to identify the earliest drifting node, outputting the root service name and confidence level.
- **Decision Records:**
  - *ADR-001 (W1-D3):* Integrated Apache Kafka as the transport layer between OTel Collector and VictoriaMetrics/Elasticsearch to prevent metric/log loss under high-load peaks (up to 50M events/sec).
  - *ADR-007 (W2-D3):* Replaced count-based alert ranking with topology-aware temporal lag analysis (Granger Causality) to handle cascading retry storms.
  - *ADR-008 (W3-D3):* Integrated SSH audit logs (`auditd`) and Docker/Kubernetes container events into the correlation engine to detect operator-induced outages (resolving Gap 1 of the postmortem).

## 4. Reliability validation (from W3-D2)
- **Chaos run cadence:** Weekly automated execution of chaos experiments.
- **Detected/total ratio target:** 90% detection recall target (historically achieved 90% / 9/10 experiments detected in validation runs).
- **Steady-state signal:** Dual validation (synthetic HTTP ping probe + internal Prometheus SLO metrics).
- **Top 3 Gaps Identified in Chaos Report:**
  1. *Wrong RCA on Database Memory:* DB connection timeouts were attributed to the downstream `payment-svc` instead of `payment-db` because of tight topology correlation.
  2. *False Negative on Log Collector Disk:* 95% disk fill on `log-collector` went undetected because the high noise floor of the log ingestion metric buried the write latency anomalies.
  3. *Sidecar & DNS Resolution Gaps:* DNS resolvers and clock skews on Auth sidecars had lower RCA confidence scores due to missing lateral dependency links in the static topology map.

## 5. Operational pattern (from W3-D3)
- **Postmortem template:** [postmortem.md] (follows Google SRE blameless incident report format).
- **On-call rotation:** Tier-based escalations. L1 on-call engineer is paged first on Tier 1/2 alerts. If not acknowledged within 15 minutes, the alert escalates to L2 SREs.
- **ADR repository:** References [ADR.md] and [ADR-001.md].

## 6. Cost model (from W3-D3)
- **Monthly cost:** $20,000 USD (Includes $1,000 for compute and storage, and $19,000 for 0.25 FTE SRE support at $12,500/month loaded loaded cost + on-call opportunities).
- **Break-even avoided incidents/month:** 1.0 incidents avoided per month (assuming a downtime cost of $50,000/hour for a medium-large e-commerce platform and 40% MTTR reduction).
- **Calculator implementation:** See [cost_model.py].

## 7. Open risks
- **Risk 1 (High Severity):** Anomaly detector silence during slow disk capacity exhaustion on noisy I/O nodes. *Mitigation:* Transition to percentile-based (p99) disk write latency metrics and absolute disk space alerts.
- **Risk 2 (Medium Severity):** Topology map omission of sidecars and helper dependencies (DNS resolution, Auth clock skews). *Mitigation:* Move to dynamic topology mapping by parsing mesh controller configuration data.
- **Risk 3 (Medium Severity):** Potential audit log bloat and privacy leakage under high-frequency operator commands. *Mitigation:* Implement client-side regex scrubbing of commands before ingestion into AIOps pipelines.
