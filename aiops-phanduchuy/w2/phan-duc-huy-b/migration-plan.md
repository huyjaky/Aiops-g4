# A5. Eight-Week Migration Plan

This document details the week-by-week migration plan from the current fragmented observability stack to the target Grafana-centric stack, guaranteeing zero observability blackouts and providing under-30-minute rollback paths for every transition phase.

---

## 1. Core Migration Principles

> [!IMPORTANT]
> **No-Observability-Blackout Guarantee:**
> *   **Dual-Ingestion**: During all transition phases, both the legacy stack (Datadog/Splunk) and the new stack (Grafana Cloud) will run in parallel. The legacy stack will only be decommissioned after the new stack runs stably for at least 7 consecutive days and passes all Go/No-Go gates.
> *   **Rolling Update**: Grafana Alloy deployment across the 300 hosts will use a Kubernetes DaemonSet rolling update strategy with `maxUnavailable = 10%`. This ensures at least 90% of nodes report telemetry continuously at any microsecond.
> *   **Low-Traffic Switchovers**: All alerting cuts and legacy system shutdowns will occur during low-traffic windows (Tuesdays between 02:00 and 04:00 AM UTC+7).

---

## 2. Week-by-Week Implementation Schedule

### Week 1: Infrastructure Setup & Alloy Staging Pilot
*   **Tasks**:
    *   Initialize Grafana Cloud Enterprise account and establish AWS VPC Private Link connections.
    *   Deploy Grafana Alloy to the Staging cluster. Configure infrastructure scraping and raw container log collection.
    *   Instrument mock applications in Staging with the OpenTelemetry SDK.
*   **Go/No-Go Gate 1**:
    *   100% of Staging hosts/containers successfully report telemetry to Grafana Cloud.
    *   Grafana Alloy CPU/memory footprint remains under 1.5% of total node capacity in Staging.
*   **Rollback Path**:
    *   Since Staging is a sandbox and runs in parallel, simply uninstall the Alloy DaemonSet via Helm (`helm uninstall alloy`). The legacy staging monitors remain unaffected. Execution time: **5 minutes**.

### Week 2: Production Metrics Dual-Ingestion & Cardinality Controls
*   **Tasks**:
    *   Deploy Grafana Alloy DaemonSet across all 300 Production hosts.
    *   Configure dual-ingestion: push system and app metrics to both Datadog and Grafana Mimir.
    *   Apply first-line cardinality drop rules in Alloy (drop `customer_id` from custom metrics).
*   **Go/No-Go Gate 2**:
    *   Active series count mismatch between Datadog and Grafana Mimir is < 2% (representing planned cardinality drops).
    *   Zero ingestion errors reported on the Grafana Cloud Billing Dashboard.
*   **Rollback Path**:
    *   If Alloy causes memory exhaustion or nodes crash, rollback the DaemonSet deployment using Kubernetes (`kubectl rollout undo daemonset/alloy`). Legacy Datadog agents are running independently, preventing data blackouts. Execution time: **3 minutes**.

### Week 3: Distributed Tracing & Tail-Based Sampling Deployment
*   **Tasks**:
    *   Deploy OpenTelemetry SDK-instrumented application code to Production via rolling update.
    *   Configure Grafana Alloy tail-based sampling: hold spans in memory for 5 seconds; keep 100% of errors and slow requests (> p95 latency), sample 0.1% of successful traces. Route to Grafana Tempo.
*   **Go/No-Go Gate 3**:
    *   Ingested trace volume stabilizes around ~10 GB/day as projected, preventing billing overages.
    *   Verify that Alloy successfully captures 100% of simulated HTTP 500 errors injected into Staging.
*   **Rollback Path**:
    *   If trace memory buffering causes Alloy OOM errors on nodes, hot-reload Alloy configuration via ConfigMap update to fall back to standard head-based 1% sampling. Execution time: **5 minutes**.

### Week 4: Production Log Dual-Ingestion (Splunk to Loki)
*   **Tasks**:
    *   Configure Grafana Alloy log collector to scrape `stdout/stderr` files on all 300 hosts and forward them to Loki.
    *   Keep Splunk Universal Forwarders fully active, writing logs to Splunk Cloud.
    *   Configure Loki cold-tier archiving rules to push logs to our S3 bucket after 15 days.
*   **Go/No-Go Gate 4**:
    *   Daily ingestion rate in Loki reaches ~52 GB/day, matching Splunk Cloud statistics within a 1% margin.
    *   Verify p99 Loki query latency for a 7-day window is under 2.0 seconds.
*   **Rollback Path**:
    *   Since Splunk Forwarders run independently, if Loki ingestion fails, temporarily disable Loki write pipelines in Grafana Alloy configurations. History remains intact on Splunk. Execution time: **2 minutes**.

### Week 5: Alert Rules & Dashboard Migration
*   **Tasks**:
    *   Manually translate all Datadog monitors and Splunk alerts into **Grafana Alerting** PromQL/LogQL alert rules.
    *   Recreate executive and engineering dashboards in Grafana, removing Datadog-specific API queries.
*   **Go/No-Go Gate 5**:
    *   Successfully replicate and test at least 95% of historical alert rules in Grafana.
    *   Dashboards display real-time data matching legacy platforms within a 2% margin.
*   **Rollback Path**:
    *   No changes are made to active alerting pathways yet. No rollback required.

### Week 6: On-Call Training & Incident Routing Cut-Over (PagerDuty to Grafana OnCall)
*   **Tasks**:
    *   Train all 65 engineers on Grafana Explore, LogQL/PromQL basics, and Grafana OnCall app configurations.
    *   Replicate PagerDuty escalation pathways and rotation shifts inside Grafana OnCall.
    *   Run a simulated chaos drill: trigger a database pool leak in Staging; verify that Grafana OnCall groups the cascading alerts into a single incident.
*   **Go/No-Go Gate 6**:
    *   On-call engineers successfully triage and locate the root cause of a simulated incident in Staging using only Grafana and OnCall in under 5 minutes.
    *   Verify that alert grouping suppresses duplicate paging storms.
*   **Rollback Path (Within 5 minutes)**:
    *   If Grafana OnCall fails to trigger SMS/phone paging during a real incident:
        1. Unmute PagerDuty alerting configurations.
        2. Update Grafana Alerting webhooks to route directly back to the PagerDuty API endpoint.

### Week 7: Log Ingestion Cut-Over & Splunk Decommissioning
*   **Tasks**:
    *   Remove Splunk Universal Forwarder DaemonSet from all hosts.
    *   Stop active ingestion to Splunk Cloud. Downgrade Splunk subscription to a read-only tier for the remaining 7 months of the contract to access historical archives.
*   **Go/No-Go Gate 7**:
    *   Grafana Loki runs stably as the sole log engine for 7 consecutive days with no data loss or query delays.
*   **Rollback Path (Within 10 minutes)**:
    *   If security audits reveal a critical log formatting issue in Loki:
        1. Redeploy Splunk Universal Forwarder DaemonSet via Helm.
        2. Resume ingestion into Splunk Cloud (since the contract remains paid for).

### Week 8: Datadog Shutdown & Project Sign-off
*   **Tasks**:
    *   Remove Datadog Agent DaemonSet from all 300 hosts.
    *   Decommission Datadog subscription.
    *   Audit Grafana Cloud's first monthly invoice to verify it aligns with the projected $4,883 cost.
*   **Go/No-Go Gate 8**:
    *   Total actual monthly bill does not deviate from the target projection by more than 10%.
    *   Median MTTR for production incidents drops by over 30% compared to pre-migration baseline.
*   **Rollback Path (Within 10 minutes)**:
    *   If a major operational emergency requires Datadog tools:
        1. Redeploy Datadog Agent DaemonSet via Helm.
        2. Re-enable the Datadog monthly billing subscription.
