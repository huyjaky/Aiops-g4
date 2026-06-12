# D. Skills-Gap & Transition Plan

Transitioning from a "click-and-play" SaaS model (Datadog/Splunk UIs) to a flexible, open-standards platform (Grafana Cloud and OTel) requires a deliberate upskilling effort for the GeekShop engineering team.

This document identifies skills gaps across roles, details our training strategy (focusing on upskilling rather than hiring), specifies training curricula, outlines the 8-week timeline, and details the budget.

---

## 1. Role-Based Skills-Gap Analysis

Currently, our engineers are familiar with Datadog and Splunk interfaces. We must retrain the team to adopt the target architecture skills:

| Role | Size | Current Skills | Target Skills | Key Skills Gap |
| :--- | :--- | :--- | :--- | :--- |
| **Platform / SRE Team** | 3 engineers | Datadog Agent YAML configuration, Splunk Forwarders, on-call bash runbooks. | **Grafana Alloy (River syntax)**, OTel collector processors, Mimir/Loki rules. | River syntax, OTel pipeline specifications, and metrics cardinality management. |
| **Application Developers** | 60 engineers (9 teams) | Datadog SDK auto-instrumentation, Datadog APM query interface. | **OpenTelemetry SDK** code instrumentation, **PromQL** for service dashboards. | OpenTelemetry API standards, PromQL query syntax (replacing Datadog syntax). |
| **On-Call Responders** | ~20 rotating engineers | PD alerts, opening 4 separate vendor tabs during incident triage. | **Grafana OnCall**, unified **Explore** correlation pathways (1-click triage). | 1-click Log-to-Trace troubleshooting, OnCall notification configurations. |
| **Security & Audit Team** | 2 engineers | Splunk Search Processing Language (SPL) for compliance auditing. | **LogQL** on Grafana Loki to query long-tail audit logs archived in S3. | Translating Splunk SPL queries into Loki LogQL queries. |

---

## 2. Training Strategy: Upskilling vs. Hiring

To control operational overhead, **we will not hire new staff**. We will focus 100% of our resources on upskilling the existing team using free online materials supplemented by a single targeted expert workshop.

### Training Curricula:
1.  **For Platform / SRE Team**:
    *   *Courses*: Grafana University — "Grafana Alloy Configuration", "Loki / Mimir Administration" (Free).
    *   *Reference*: OpenTelemetry.io — "Collector Pipelines & Sampling Guide" (Free).
2.  **For Application Developers**:
    *   *Courses*: Grafana University — "Introduction to PromQL", "Grafana Explore Fundamentals" (Free).
    *   *Reference*: "Datadog to PromQL translation cheat sheet" (Compiled internally by the Platform Team).
3.  **For Security & Audit Team**:
    *   *Courses*: Grafana University — "LogQL Fundamentals" (Free).
    *   *Reference*: "Splunk SPL to LogQL translation cheat sheet".

---

## 3. Timeline & Training Schedule

Training is integrated directly into the 8-week migration plan:

*   **Week 1 - 2 (SRE Kick-off)**:
    *   The 3 SRE engineers complete Grafana University administrator courses and validate the Staging POC.
*   **Week 3 - 4 (SRE Documentation)**:
    *   Platform team compiles query translation cheatsheets and drafts OTel SDK guidelines for developers.
*   **Week 5 (Developer Upskilling)**:
    *   Conduct a **2-hour hands-on Developer Workshop**. Guide developers on OTel SDK integrations and basic PromQL. Record the session to onboard future hires (resolving **Pain Point 8**).
*   **Week 6 (On-Call Simulation)**:
    *   Conduct a 1-hour chaos drill session for the 20 rotating on-call engineers. Guide them on Grafana OnCall mobile app setup and demonstrate 1-click Log-to-Trace triage workflows.
*   **Week 7 (Security Session)**:
    *   Conduct a 2-hour 1-on-1 session between the Platform Team and Security Auditors to translate Splunk compliance reports to LogQL.

---

## 4. Cost of Transition (Training Budget)

*   **Self-study / Internal Training**: Estimated ~80 hours of SRE time and ~3 hours per developer (absorbed in existing salary pools, no cash cost).
*   **Professional Services Training**: Hire Grafana Labs Professional Services to conduct a 1-day dedicated performance-tuning workshop for Mimir and Loki: **$5,000** (one-time fee paid from project contingency funds).
*   **TOTAL CASH BUDGET**: **$5,000**.
