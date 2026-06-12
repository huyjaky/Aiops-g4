# FINDINGS.md — System Analysis & Proof of Concept (POC) Plan

This document contains the detailed answers to the 5 architectural reflection questions regarding the GeekShop observability stack redesign and presents the Proof of Concept (POC) plan under Section 2.

---

## 1. Architectural Reflection Questions

### Question 1: Which capability turned out hardest to replace, and why? What did you compromise on?
*   **Hardest capability to replace**: **Long-tail log search and storage** (replacing Splunk Cloud).
*   **Why**: Splunk provides high-speed full-text indexing, complex compliance reports, and has deep historical search capability. Our security and audit teams had pre-built dashboards and scripts dependent on Splunk's SPL query language.
*   **Compromises**: We moved to **Grafana Loki**, which indexes metadata labels only, rather than full-text content. This means raw text queries over broad time ranges (e.g. searching for a random string in 30 days of raw logs without label filters) are slower than in Splunk, as Loki must perform parallel brute-force regex scanning on S3. We compromised on raw query speed for long-tail search in exchange for a 95% cost reduction (saving $15,000/month). To mitigate this, we enforce structured JSON logging and train engineers to always use static labels (`service`, `level`) in Loki.

### Question 2: Where did your design trade resilience for cost? Quantify the trade-off.
We made two primary resilience-for-cost trade-offs:
1.  **Metric-to-Trace Exemplar Loss during Outages (Observability Redundancy)**:
    *   *Trade-off*: We utilize a single-region Grafana Cloud SaaS deployment rather than running a redundant active-active multi-region metrics/alerting cluster.
    *   *Quantification*: **Saves ~$12,000 / month** in licensing and cross-region traffic fees. The cost is **~30 extra minutes of MTTR** during a complete Grafana Cloud regional outage, as our on-call engineers would have to fallback to logging in via SSH/CLI to query container statistics and raw log files directly on hosts.
2.  **Trace Sampling Limit (APM Visibility)**:
    *   *Trade-off*: We implement tail-based sampling, keeping 100% of errors/anomalies and 0.1% of successful traces, dropping 99.9% of normal transaction spans.
    *   *Quantification*: **Saves ~$11,950 / month** compared to Datadog's APM billing. The cost is **~15 extra minutes of MTTR** in rare "silent failure" scenarios (e.g., a performance bottleneck that slowly degrades latency but does not throw an HTTP 500 error or exceed p95 response time thresholds). In this case, trace history will be missing, and engineers must rely on raw system metrics to isolate the bug.

### Question 3: If the budget cut requirement were 60% instead of 40%, which decisions would change and which would not? What does that tell you about the structure of cost in this stack?
*   **Decisions that would remain unchanged**: Replacing Datadog Agent with **Grafana Alloy** and migrating logs to **Grafana Loki**. These represent the highest savings points ($15,700/mo on logs and $12,400/mo on APM). Our proposed design already achieves an **88.4% cost cut** ($4,883/mo), which comfortably exceeds a 60% requirement ($16,800 budget limit).
*   **Decisions that would change**: If forced to cut costs even further (e.g. 90% cost reduction, budget limit of $4,200), we would switch from **Managed Grafana Cloud (SaaS)** to a **Self-Hosted OSS Model** running Mimir, Loki, and Tempo directly on our existing AWS EKS nodes using cheap S3 storage.
*   **Structure of cost**: This tells us that the cost structure of this stack is dominated by **proprietary agent host-based licensing (Datadog's $58/host model)** and **full-text index processing fees (Splunk)**. Once we replace these with OpenTelemetry standards and metadata-indexed Loki chunks, costs drop exponentially. The choice between SaaS and OSS then becomes a trade-off between **cash layout** and **engineering time (headcount)** to maintain the monitoring stack.

### Question 4: Identify one pattern in your design that you copied from a real-world system you know. Name the system, the pattern, and what you changed.
*   **Real-world system**: Uber's **M3DB and OTel Collector Pipeline** architecture.
*   **Pattern copied**: **Local Telemetry Collector Processing & Gateway Routing**. In Uber's architecture, local host agents (M3 Coordinator) scrape and process metrics locally on each host to drop redundant tags and enforce cardinality rules before forwarding data to a centralized storage cluster.
*   **Changes made**: Instead of building and maintaining a custom M3DB cluster and dedicated Collector Gateways (which requires dedicated SRE headcount), we simplified this by using **Grafana Alloy** as a unified host agent (handling metrics, logs, and traces via a single River configuration file) and routed the preprocessed data directly to **Grafana Cloud managed backends**. This replicates Uber's high-efficiency pre-filtering benefits without the massive operational overhead.

### Question 5: What is the biggest unknown in your plan — something that could derail the migration at week N?
*   **Biggest unknown**: The CPU and memory impact of running **Grafana Alloy's Tail-Based Sampling processor** on high-throughput nodes (such as `edge-lb` and `checkout-svc`) in Week 3.
*   **The Risk**: Tail-sampling requires Alloy to hold trace spans in memory for 5 seconds to evaluate the request outcome. Under peak traffic spikes, this buffering could cause Alloy process memory to explode, triggering Linux Out of Memory (OOM) kills and destabilizing the application host.
*   **De-risking plan**: Execute a Proof of Concept load test in Week 1 to validate memory consumption under peak simulated load (detailed below).

---

## 2. A7. Proof of Concept (POC) Plan

We identify **Grafana Alloy's Tail-Based Sampling memory usage under load** as the single most uncertain component in our target design.

**Core Assumption to Validate**: *"Enforcing tail-based tracing sampling (holding spans in memory for 5 seconds) under a peak production load of 10,000 requests/second will not cause Grafana Alloy memory to exceed 150MB or consume more than 0.2 CPU cores per host node."*

**Validation Methodology & Measurement**:
In Week 1, we will set up a local POC in the Staging environment. We will deploy Grafana Alloy on a staging node matching production host specs. Using **k6**, we will generate a load ramping from 1,000 to 10,000 req/s targeting a mock API service. We will configure Alloy to capture OTel spans, buffer them for 5 seconds, keep 100% of errors/slow traces, and sample 0.1% of normal requests.
We will monitor the following metrics over a 24-hour test period:
1.  `container_memory_working_set_bytes` for the Grafana Alloy container.
2.  `container_cpu_usage_seconds_total` for the Grafana Alloy container.

*   **Confirming the assumption**: If Alloy process memory remains under 150MB and CPU usage is under 0.2 cores at peak 10,000 req/s load, the assumption is confirmed, and we proceed with production rollout in Week 3.
*   **Denying the assumption**: If memory usage exceeds 200MB or CPU usage spikes above 0.5 cores, the assumption is denied. We will change our design: instead of tail-sampling directly on application hosts, we will transition to a **Collector Gateway Pattern** (Alloy on hosts will forward raw traces immediately to a dedicated, auto-scaling pool of Alloy Collector Gateways inside Kubernetes to offload memory buffering from the primary app servers).
