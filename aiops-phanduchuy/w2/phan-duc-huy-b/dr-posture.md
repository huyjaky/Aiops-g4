# E. Disaster Recovery & DR Posture

GeekShop's current observability infrastructure is entirely single-region and lacks disaster recovery procedures during regional outages.

This document details the multi-region disaster recovery (DR) architecture for the target state, specifying **Recovery Time Objective (RTO)** and **Recovery Point Objective (RPO)** targets for each component, along with their technical justifications.

---

## 1. RTO & RPO Targets per Component

The table below details recovery metrics for each observability component:

| Observability Component | DR Strategy | Target RTO (Max recovery time) | Target RPO (Max data loss) | Technical Justification |
| :--- | :--- | :--- | :--- | :--- |
| **Grafana Alloy (Agent)** | Deployed as a self-healing Kubernetes DaemonSet. Configured to buffer telemetry to host disk write-ahead log buffers if upstream connection is lost. | **1 minute** | **30 seconds** | The agent is stateless. RTO is bounded by Kubernetes rescheduling time. RPO is secured by Alloy's disk write-ahead log cache, which preserves data during network blips. |
| **AWS S3 Object Storage (Unified Storage)** | **S3 Cross-Region Replication (CRR)**: Automatically replicate raw compressed logs, traces, and metrics from the primary S3 bucket (`us-east-1`) to a secondary bucket (`us-west-2`). | **5 minutes** | **15 minutes** | S3 holds the source of truth for long-tail compliance audits. AWS S3 CRR typically syncs changes in under 15 minutes (RPO). RTO represents SRE time to update query datasource variables to point to the backup S3 bucket. |
| **Grafana Mimir (Metrics & Alerting)** | **Active-Active Replication**: Grafana Alloy is configured to dual-write (remote write) metrics simultaneously to two separate Grafana Cloud zones (primary and secondary). | **0 minutes** (Instant) | **0 minutes** (Zero Loss) | Alerting and SLO metrics are real-time. Any data drop can cause missed critical pages or false alarms. Active-active writing guarantees zero metrics loss and immediate query failover. |
| **Grafana Loki (Logs Store)** | S3 CRR + **Cold Failover**: During a primary region outage, Alloy routes new log writes to the secondary Loki endpoint. Query historical logs via the S3 CRR backup bucket. | **15 minutes** | **15 minutes** | Logs are large. Active-active dual-writing logs would double egress bandwidth costs. Accepting a 15-minute loss (RPO) and 15-minute failover (RTO) optimizes infrastructure costs. |
| **Grafana Tempo (Traces Store)** | **Cold Failover**: Traces are transient (14-day retention). During a disaster, redirect new traces to the secondary region. Historical traces are not replicated. | **30 minutes** | **2 hours** | Traces are debugging aids. Losing a few hours of traces during a major regional disaster does not affect operational capability and saves thousands of dollars in egress replication fees. |
| **Grafana OnCall (Paging & Routing)** | **SaaS Multi-zone HA** with fallback SMS/Call gateway routing utilizing independent Twilio APIs configured across multiple regions. | **5 minutes** | **0 minutes** | Escalation is the most critical element. If paging is down, SREs cannot respond to outages. RTO of 5 minutes enables direct Twilio fallback paging. RPO is zero as alert triggers are real-time events, not historical logs. |

---

## 2. Disaster Recovery Workflow

When the primary AWS region (`us-east-1`) experiences a total outage:

1.  **Detection**: Grafana Synthetic Monitoring probes located outside the affected region detect that GeekShop services in `us-east-1` are down, immediately triggering a P1 incident via Grafana OnCall.
2.  **Infrastructure Standby**: SREs trigger Terraform scripts to boot the GeekShop application standby cluster in the backup region (`us-west-2`).
3.  **DNS Failover**: Update Route 53 DNS records to route 100% of production traffic to `us-west-2`.
4.  **Observability Transition**:
    *   Grafana Alloy agents running in `us-west-2` begin forwarding system metrics and container logs to the backup Grafana Cloud zones.
    *   Grafana Dashboards automatically switch queries to the backup S3 bucket in `us-west-2` (which contains historical logs and metrics synchronized via S3 CRR up to the point of failure).
    *   Grafana Alerting rule evaluation resumes against Mimir and Loki backends in the backup zone.
