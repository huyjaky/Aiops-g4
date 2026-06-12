# A3. Cost Model

The table below compares the current monthly observability cost (fragmented SaaS) with the target state (consolidated Grafana Cloud), based on the publicly available Grafana Labs List Pricing (Grafana Cloud Pro/Enterprise tiers).

## Monthly Bill Comparison

| Cost Line Item | Old Vendor | Old Monthly Cost | New Vendor | New Monthly Cost | New Cost Formula & Assumed Scale | Savings (%) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Infrastructure Metrics** | Datadog Pro | $5,400 | Grafana Cloud | **$2,400** | 300 hosts * 1,000 metrics/host = 300,000 active series. <br>Unit Price: $8 per 1,000 active series. <br>Formula: `(300,000 / 1,000) * $8` = $2,400. | -55.6% |
| **APM & Traces** | Datadog APM | $12,100 | Grafana Cloud | **$150** | Traces collected via Alloy (applying tail-sampling to reduce volume to ~10 GB/day = 300 GB/month). <br>Unit Price: $0.50 per GB traces ingested. <br>Formula: `300 * $0.50` = $150. | -98.8% |
| **Custom Metrics** | Datadog | $2,200 | Grafana Cloud | **$400** | Assuming we retain ~50,000 active series for custom metrics after filtering out high-cardinality dynamic tags (like `customer_id`). <br>Unit Price: $8 per 1,000 active series. <br>Formula: `(50,000 / 1,000) * $8` = $400. | -81.8% |
| **Logs (Hot + Cold)** | Splunk + DD Logs | $15,700 | Grafana Cloud | **$780** | Log volume: 52 GB/day * 30 days = 1,560 GB/month. <br>Unit Price: $0.50 per GB logs ingested (includes 30 days default hot retention). <br>Formula: `1,560 * $0.50` = $780. | -95.0% |
| **Paging & Routing** | PagerDuty | $3,900 | Grafana OnCall | **$930** | 65 users. Grafana Cloud Pro includes 3 users free, then bills $15/user/month for additional users. <br>Formula: `(65 - 3) * $15` = $930. | -76.2% |
| **User Licenses** | Grafana Cloud | $1,050 | Grafana Cloud | **$183** | Total of 18 users (6 Editors, 12 Viewers). 3 free users are allocated to Editors. <br>Unit Price: Additional Editor $29, Viewer $8. <br>Formula: `(3 * $29) + (12 * $8)` = $87 + $96 = $183. | -82.6% |
| **Synthetic Checks** | Datadog | $1,360 | Grafana Cloud | **$30** | 270 checks running every 1 minute from 2 geographic locations (US-East & AP-Southeast) = 23.6M checks/month. <br>Unit Price: $1.20 per 1 million API checks. <br>Formula: `23.6 * $1.20` = $28.32. | -97.8% |
| **Status Page** | Statuspage | $290 | Uptime Kuma | **$10** | Migrated to self-hosted Uptime Kuma (OSS). Infrastructure cost for S3 hosting and CDN distribution. | -96.5% |
| **TOTAL** | | **$42,000** | | **$4,883** | **Savings of $37,117 per month** | **-88.4%** |

---

## Sensitivity Analysis

> [!WARNING]
> **Scenario: Data Volume Grows 2x Faster Than Projected**
> 
> If the entire data volume of the system doubles, the cost adjustments will behave as follows:
> 
> 1.  **Logs Volume (2x)**: Increases from 1,560 GB to 3,120 GB/month. Loki cost increases from $780 to **$1,560 / month** (Increase of **$780**).
> 2.  **Traces Volume (2x)**: Increases from 300 GB to 600 GB/month. Tempo cost increases from $150 to **$300 / month** (Increase of **$150**).
> 3.  **Metrics Volume (2x)**: If the active series double (from 350k to 700k series due to cardinality leakage), Mimir cost doubles from $2,800 to **$5,600 / month** (Increase of **$2,800**).
> 
> **Component that breaks the budget first**: **Metrics Active Series**.
> While doubling logs and traces only adds $930 to the monthly bill, a 2x cardinality leak on metrics drains an extra $2,800. This is because metrics are billed per active time-series database record and are highly sensitive to developer-introduced dynamic labels.
> 
> **Mitigation**: Configure hard limits on active series in Grafana Alloy and write an alert to trigger when active series utilization exceeds 85% (400,000 series).

---

## Pricing Defense (List Price Verification)
*   **Grafana Cloud Metrics**: List price is $8 per 1,000 active series for pay-as-you-go Pro plans. We used this highest tier to ensure budget safety.
*   **Grafana Cloud Logs/Traces**: List price is $0.50 per GB ingested as officially published on the Grafana pricing page.
*   **Grafana Cloud Users**: Pro tier charges $29/month per additional Editor and $8/month per additional Viewer.
*   **Grafana Cloud OnCall**: Standard pricing of $15/user/month for team members included in escalation rotations.
