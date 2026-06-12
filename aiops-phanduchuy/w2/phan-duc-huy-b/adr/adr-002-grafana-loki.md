# ADR 002: Using Grafana Loki as the Unified Log Engine Replacing Splunk Cloud and Datadog Logs

*   **Status**: Approved
*   **Author**: Platform Architect Team
*   **Date**: 2026-06-12

---

## 1. Context
GeekShop's current logging infrastructure is highly fragmented and expensive, costing **$15,700 / month** (representing 37% of our total monthly observability bill):
1.  **Duplicate Ingestion**: Application logs are sent simultaneously to Datadog Logs ($1,800/month, 15 days hot retention) for engineering troubleshooting, and to Splunk Cloud ($13,900/month, 30 days retention) for security auditing and compliance reporting.
2.  **High Search Latency (Pain Point 1)**: Splunk Cloud's indexer falls behind during the daily 14:00 traffic peak, causing queries crossing a 7-day window to exceed 25 seconds. This delays SRE response times.
3.  **Blacked-out Dashboards (Pain Point 6)**: Once a quarter, Splunk performs index rotations which cause saved searches and dashboards to return empty results for 5–15 minutes, causing false escalations.
4.  **Contractual Risks (Pain Point 10)**: Splunk Cloud requires a 90-day cancellation notice before auto-renewing, a window we have missed in the past, creating high lock-in risks.

We need a unified log management system that operates at a fraction of the cost, provides reliable long-term storage, is immune to indexing-rotation blackouts, and integrates natively with tracing to accelerate troubleshooting.

---

## 2. Decision
We decide to replace both Splunk Cloud and Datadog Logs with **Grafana Loki** (Managed Grafana Cloud Logs) as the single unified log storage and query engine for GeekShop.

Grafana Loki will:
*   Ingest all application and system logs as structured JSON formatted logs via Grafana Alloy.
*   Enforce a tiered retention schedule: 15 days hot retention in Grafana Cloud for active debugging, and auto-archive logs to our customer-owned **AWS S3** bucket for 90 days cold storage to satisfy compliance requirements.
*   Enable metadata label correlation to link Loki log lines directly to Tempo trace spans using Trace IDs in the Grafana UI.

---

## 3. Alternatives Considered & Rejected

### Alternative A: Self-hosted ClickHouse for Logs
*   *Why Rejected*: ClickHouse is a fast columnar database that provides excellent compression and raw query performance. However, deploying ClickHouse requires the Platform team to design schemas, manage data partitioning, install and configure Grafana plugins, and maintain an active-active ClickHouse database cluster. This introduces significant operational overhead for a small platform team.

### Alternative B: Deploy OpenSearch / Elasticsearch (SaaS or Self-hosted)
*   *Why Rejected*: OpenSearch builds full-text inverted indexes of every word in log lines. This indexing model is extremely resource-intensive, requiring high CPU, large JVM memory heaps, and expensive SSD storage (AWS EBS gp3). Running OpenSearch for 52 GB/day with 30-day hot retention would cost between $2,500 and $3,500/month, and self-hosting would add high maintenance overhead. It also maintains data fragmentation outside the Grafana ecosystem.

---

## 4. Consequences

### Positive
*   **95% Cost Reduction**: Log management costs drop from $15,700/mo to **$780 / month** due to Loki's metadata-only indexing model and cheap raw storage on AWS S3.
*   **No Dashboard Blackouts**: Loki stores logs as compressed chunks in object storage and does not use index-rotation mechanisms, eliminating the 5-15 minute dashboard blackouts (**Pain Point 6**).
*   **Unified UI Correlation**: Resolves context-switching by enabling 1-click transitions from Loki logs to Tempo traces directly in Grafana.

### Negative
*   **Slower Raw Text Queries Over Long Ranges**: Because Loki only indexes labels and performs parallel brute-force regex scanning on raw log content, querying for arbitrary text across large windows (e.g. searching for a random word in 30 days of logs without label filters) is slower than in Splunk.
*   *Mitigations*:
    1. We configure Grafana Alloy to automatically apply static metadata labels (`service`, `env`, `level`, `container`) to all ingested logs.
    2. We train engineers to always write queries utilizing labels first (e.g., `{service="payment-svc", level="error"}`) before searching for raw text.
    3. We enforce structured JSON logging across all microservices, allowing Loki to parse fields dynamically (`| json`) to accelerate filtering.
