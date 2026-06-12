# GeekShop Observability & AIOps Stack Redesign — Submission

This directory contains the complete architectural redesign of GeekShop's observability and incident response stack. The proposed design achieves a **88.4% monthly cost reduction** (reducing monthly spend from $42,000 to **$4,883 / month**) and cuts median Time-To-Root-Cause (MTTR) by **over 30%** by consolidating 5 fragmented SaaS vendors into a unified **Grafana Cloud (LGTM Stack)** ecosystem.

---

## How to Read the Submission (Table of Contents)

For an optimal review of the design, we recommend starting with the architectural reflection and proof of concept details in [FINDINGS.md](file:///home/duckq1ulaptop/Desktop/aiops-g4/main2/geekshop-redesign/FINDINGS.md) to understand core design trade-offs, and then inspecting components as indexed below:

### 1. Required Deliverables (A1 - A7)

*   **A1. Target-state Architecture Diagram**: [architecture-target.mmd](file:///home/duckq1ulaptop/Desktop/aiops-g4/main2/geekshop-redesign/architecture-target.mmd)  
    *Mermaid configuration mapping ingestion streams (metrics, logs, traces), storage layers, alerting pathways, and unified query interfaces colored by SaaS/OSS/In-house boundaries.*
*   **A2. Component-Decision Table**: [components.md](file:///home/duckq1ulaptop/Desktop/aiops-g4/main2/geekshop-redesign/components.md)  
    *Detailed justifications for each chosen component and migration change consequences.*
*   **A3. Cost Model**: [cost-model.md](file:///home/duckq1ulaptop/Desktop/aiops-g4/main2/geekshop-redesign/cost-model.md)  
    *Before/after line-item comparisons, Grafana Cloud list price formulas, and metrics cardinality sensitivity analysis.*
*   **A4. Architecture Decision Records (ADRs)**:
    *   [ADR 001 - Grafana Alloy Unified Agent](file:///home/duckq1ulaptop/Desktop/aiops-g4/main2/geekshop-redesign/adr/adr-001-grafana-alloy.md): *Deciding to deploy Grafana Alloy as a unified agent to handle cardinality filtering and tail-based sampling.*
    *   [ADR 002 - Grafana Loki Log Engine](file:///home/duckq1ulaptop/Desktop/aiops-g4/main2/geekshop-redesign/adr/adr-002-grafana-loki.md): *Deciding to replace Splunk Cloud with Grafana Loki and analyzing S3 storage integration.*
*   **A5. Eight-week Migration Plan**: [migration-plan.md](file:///home/duckq1ulaptop/Desktop/aiops-g4/main2/geekshop-redesign/migration-plan.md)  
    *Week-by-week implementation schedule, dual-ingestion transition gates, no-blackout guarantees, and under-30-minute rollback paths.*
*   **A6. Risk Register**: [risks.md](file:///home/duckq1ulaptop/Desktop/aiops-g4/main2/geekshop-redesign/risks.md)  
    *The six highest technical/financial risks, owners, and specific actionable mitigations.*
*   **A7. Findings & Proof of Concept (POC) Plan**: [FINDINGS.md](file:///home/duckq1ulaptop/Desktop/aiops-g4/main2/geekshop-redesign/FINDINGS.md)  
    *Answers to the five architectural reflection questions and a staging POC load-testing plan to validate Alloy's memory during tail-sampling.*

---

### 2. Bonus Deliverables (B - E)

All four optional deep-dives have been fully completed to ensure a comprehensive production-ready transition plan:

*   **Bonus B. 12-Month Capacity Projection**: [capacity-model.md](file:///home/duckq1ulaptop/Desktop/aiops-g4/main2/geekshop-redesign/capacity-model.md)  
    *Telemetry volume and billing forecasts across three growth scenarios (Slow - 10%, Expected - 25%, Fast - 60%).*
*   **Bonus C. Vendor Exit-Clause Analysis**: [vendor-exit-analysis.md](file:///home/duckq1ulaptop/Desktop/aiops-g4/main2/geekshop-redesign/vendor-exit-analysis.md)  
    *Exit notice management for Splunk Cloud, Datadog, PagerDuty, and contractual safeguards for the new Grafana Cloud agreement.*
*   **Bonus D. Skills-Gap & Transition Plan**: [skills-gap-plan.md](file:///home/duckq1ulaptop/Desktop/aiops-g4/main2/geekshop-redesign/skills-gap-plan.md)  
    *Training curricula, free certifications, 8-week team upskilling timeline, and a $5,000 professional training budget.*
*   **Bonus E. Disaster Recovery & DR Posture**: [dr-posture.md](file:///home/duckq1ulaptop/Desktop/aiops-g4/main2/geekshop-redesign/dr-posture.md)  
    *Disaster recovery failover workflows, S3 cross-region replication (CRR), and RTO/RPO targets per signal.*
