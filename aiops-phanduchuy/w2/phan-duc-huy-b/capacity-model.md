# B. 12-Month Capacity & Cost Projection (Capacity Model)

This document forecasts telemetry data growth and monthly costs for GeekShop over the next 12 months under three different business scenarios, defending the technical assumptions behind each scenario.

---

## 1. Analysis Baseline & Growth Assumptions

Based on the 30 historical incidents recorded in [incidents_history.json](file:///home/duckq1ulaptop/Desktop/aiops-g4/main2/data-pack/incidents_history.json) over the past year (averaging ~2.5 incidents per month), we observe that:
*   Critical outages (such as connection pool exhaustion or CPU spikes) frequently trigger auto-scaling expansion of 10% to 30% to absorb transient loads, temporarily inflating metric active series counts and container logs.
*   GeekShop currently runs **10 microservices** on **300 hosts**. On average, each host generates 1,000 active series metrics, and container logs ingest **52 GB logs/day** under normal operations.

We project growth over the next 12 months using the following three scenarios:

---

## 2. Three Growth Scenarios

### Scenario 1: Slow Growth (Conservative - 10% Annual Growth)
*   **Assumptions**:
    *   Business volume stabilizes. GeekShop launches no new microservices (keeps 10 services).
    *   Host count scales up by 10% (to **330 hosts**) to handle natural traffic growth.
    *   Active series metrics are kept at **385,000 active series** via OTel cardinality filters.
    *   Log volume increases to **57 GB/day** (1,710 GB/month).
    *   Trace volume increases to **330 GB/month**.
    *   On-call team size remains flat (65 users).

### Scenario 2: Expected Growth (Baseline - 25% Annual Growth)
*   **Assumptions**:
    *   GeekShop launches 2 new microservices (total **12 services**).
    *   Host count increases by 25% (to **375 hosts**) to support the new services.
    *   Metrics grow to **437,500 active series**.
    *   Log volume increases to **65 GB/day** (1,950 GB/month).
    *   Trace volume increases to **375 GB/month**.
    *   Engineering team expands, increasing on-call rotation users to **70 users** (5 added seats).

### Scenario 3: Fast Growth (Hyper-growth - 60% Annual Growth)
*   **Assumptions**:
    *   GeekShop expands rapidly, adding 5 new microservices (total **15 services**).
    *   Production host count grows to **480 hosts** (60% increase).
    *   Metrics grow to **560,000 active series**.
    *   Log volume increases to **83 GB/day** (2,490 GB/month).
    *   Trace volume increases to **480 GB/month**.
    *   On-call rotation scales up to **80 users** (15 added seats).

---

## 3. Cost Projections under Scenarios (USD / Month)

| Telemetry Component | Grafana List Price | Current Target State | Scenario 1 (Slow - 10%) | Scenario 2 (Expected - 25%) | Scenario 3 (Fast - 60%) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Infrastructure Metrics** | $8 / 1k active series | $2,400 (300k series) | $3,080 (385k series) | $3,500 (437.5k series) | $4,480 (560k series) |
| **Custom Metrics** | $8 / 1k active series | $400 (50k series) | $440 (55k series) | $500 (62.5k series) | $640 (80k series) |
| **Logs Volume** | $0.50 / GB | $780 (1,560 GB) | $855 (1,710 GB) | $975 (1,950 GB) | $1,245 (2,490 GB) |
| **Traces Volume** | $0.50 / GB | $150 (300 GB) | $165 (330 GB) | $188 (375 GB) | $240 (480 GB) |
| **User Seats** | Editor $29, Viewer $8 | $183 (18 users) | $183 (18 users) | $183 (18 users) | $215 (20 users) |
| **Grafana OnCall** | $15 / user (3 free) | $930 (65 users) | $930 (65 users) | $1,005 (70 users) | $1,155 (80 users) |
| **Synthetics / Status** | Check runs / OSS S3 | $40 | $40 | $50 | $70 |
| **TOTAL COST / MONTH** | | **$4,883** | **$5,693** | **$6,401** | **$8,045** |
| **Savings vs. Old Bill** | Compared to $42,000 | **-88.4%** | **-86.4%** | **-84.7%** | **-80.8%** |

---

## 4. Cost-Resilience Defense

The capacity projection demonstrates the **financial resilience of our target design** under high growth pressure (Scenario 3):

1.  **Resilience against Host-scaling (Datadog Comparison)**:
    *   Under Scenario 3 (480 hosts), if we remained on Datadog, host-based APM + Infra pricing would climb to: `480 hosts * $58 = $27,840/month`.
    *   With the new stack, metrics billing is based on active series, not hosts. Even with 480 hosts, metrics cost only increases to **$4,480/month** (representing a $23,360 monthly savings relative to Datadog).
2.  **Resilience against Log Ingestion Spikes (Splunk Comparison)**:
    *   Ingesting 83 GB/day of logs under Scenario 3 would push us into expensive custom Splunk Cloud licensing tiers, likely exceeding **$20,000/month**.
    *   In Grafana Loki, because we store data as raw chunks in object storage, the cost increases linearly to just **$1,245/month**, absorbing the growth easily.
3.  **Controlled Trace Storage Growth**:
    *   While transactions grow by 60%, our tail-based sampling rules filter out 99.9% of normal traces. Consequently, Tempo trace volume scales very slowly (increasing trace cost from $150 to just $240/month), avoiding billing surprises.
