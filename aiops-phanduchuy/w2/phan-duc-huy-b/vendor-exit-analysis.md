# C. Vendor Exit-Clause Analysis

This document details the contract exit analysis for current SaaS vendors (Splunk, Datadog, PagerDuty), presents the negotiation and migration workflow, and establishes target contractual safeguards for the new **Grafana Cloud** contract to prevent future vendor lock-in.

---

## 1. Exit Strategies for Current Vendor Contracts

### Vendor 1: Splunk Cloud (Current cost: $13,900 / month)
*   **Contract Terms**: 12-month commitment ending in **7 months**, requiring a **90-day cancellation notice** to prevent auto-renewal. Bulk export is contractually capped at **100 GB / day** during transition.
*   **Migration & Exit Plan**:
    1.  *Day 1 Formal Notice*: Submit a formal non-renewal notice to Splunk on Day 1 of the migration project. Doing this 7 months early ensures we do not trigger the 90-day auto-renew window (**Pain Point 10**).
    2.  *Extracting Data*: Our current logging rate is 52 GB/day, which is well below the 100 GB/day export limit. We will deploy a daily cronjob to export the previous 24 hours of raw logs in compressed JSON format and archive them to our AWS S3 bucket.
    3.  *Read-only Transition Option*: Since the contract remains paid for 7 months, we will request Splunk account management to disable active ingestion (ingest rate = 0) and convert our workspace to a search-only tier. This allows on-call engineers to query historical logs via `oncall-runbook.sh` without incurring ingestion overages.
    4.  *Escape Clause Trigger*: If Splunk refuses to support transition archiving, we will assert rights to cancel for material breach based on Splunk Cloud's p99 query latency regularly exceeding 25 seconds during traffic peaks (SLA breach of **Pain Point 1**).

### Vendor 2: Datadog Pro (Current cost: $22,960 / month)
*   **Contract Terms**: Monthly pay-as-you-go rolling contract, no long-term commitment. Ingest data export via API is permitted, but no bulk export tool is provided.
*   **Migration & Exit Plan**:
    1.  *30-day Notice*: Submit cancellation notice in Week 4 of the migration plan, terminating services at the end of the billing month.
    2.  *Configuration Export*: Since Datadog lacks bulk export tools, we will use Terraform Datadog Provider to export our active monitor configurations as code, then translate the logic into Grafana Alerting rules.
    3.  *Handling Historical Metrics*: Because raw Datadog metrics cannot be exported in bulk, we will run dual-ingestion (Week 2-4) to accumulate a 30-day historical metrics buffer in Grafana Mimir before shutting down Datadog.
    4.  *Data Rights at Termination*: Enforce our contractual right to request Datadog to purge all telemetry data and customer PII from their servers within 30 days of termination (GDPR/CCPA compliance).

### Vendor 3: PagerDuty Business (Current cost: $3,900 / month)
*   **Contract Terms**: Monthly billing, 30-day notice. User data export is available via API; incident history export requires support tickets.
*   **Migration & Exit Plan**:
    1.  *30-day Notice*: Submit termination notice in Week 5.
    2.  *API-based Export*: Run an API script to export all 65 users, phone numbers, and escalation routing rules into a JSON file, which will be imported into Grafana OnCall.
    3.  *Audit Trail Export*: Open a support ticket requesting a complete CSV dump of all historical paging and incident audit logs for the last 6 months to maintain compliance records before closing the account.

---

## 2. Contractual Safeguards for the New Grafana Cloud Enterprise Contract

To ensure GeekShop does not repeat the vendor lock-in cycle, we will negotiate the following protective clauses in our new **Grafana Cloud Enterprise** contract:

1.  **30-day Exit Notice Clause**:
    *   The contract will commit to a 12-month term, but after the initial term, it must transition to a month-to-month rolling contract with a 30-day notice period for termination (avoiding Splunk's 90-day auto-renew trap).
2.  **Telemetry Data Portability Clause**:
    *   Grafana Labs must agree to support standard bulk exports of metrics (Prometheus block formats) and logs/traces (OTLP/JSON) to our AWS S3 bucket upon request at termination, without charging data egress penalties.
3.  **Intellectual Property Rights for Configuration**:
    *   All dashboard definitions (JSON format), alerting rules (PromQL/LogQL queries), and Alloy configuration files (River scripts) are the exclusive intellectual property of GeekShop. Grafana Labs must not encrypt or prevent the extraction of these configurations.
4.  **Open-Source Escape Hatch (Ultimate Protection)**:
    *   Because Grafana Cloud is built entirely on open-source standards (Mimir, Loki, Tempo, Pyroscope, Grafana OSS, Alloy), GeekShop retains the right to transition the entire stack to a self-hosted environment on our own EKS cluster at any time. We can reuse our PromQL/LogQL queries, dashboards, and Alloy River configurations with zero application code changes.
