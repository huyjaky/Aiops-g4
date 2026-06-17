# ADR-008: Integrate Shell Auditing and Deploy Log Ingestion for Operation-Aware RCA

## Status
Accepted

## Context
When an operator runs a maintenance command, configuration push, or automated deploy script that triggers an outage, traditional monitoring registers container termination or HTTP 500 alerts, but lacks context of the human actions that initiated them. 

In our AWS S3 2017 outage reproduction, the simultaneous termination of `billing`, `index`, and `placement` caused the AIOps pipeline to report an `unknown` root cause with low confidence (0.33) because the topology was flat and the failures occurred at the exact same timestamp. Without access to operations history (such as SSH audit trails or Ansible/Docker execution logs), the correlator cannot distinguish between a catastrophic infrastructure collapse and an operator typo. This lack of operational logs is a major gap in the current RCA stack.

## Decision
We will integrate host-level shell command audit logs (via `auditd` and SSH logs) and orchestration event logs (Docker events, Kubernetes API events, and CI/CD deploy logs) as first-class input signals into the AIOps pipeline's correlation engine.

## Alternatives considered
1. **Manual Incident Reporting (Self-declaration):**
   * *Why rejected:* Relying on operators manually reporting their commands on Slack or Jira is unreliable. Under the stress of an active incident, operators often forget to self-declare, and this model cannot capture unauthorized CLI actions or rogue automated cron jobs.
2. **Rule-Based Deployment Coincidence Heuristics:**
   * *Why rejected:* Simply assuming any outage within 5 minutes of a deployment commit is a "deployment failure" generates a high rate of false positives and fails to catch ad-hoc operator commands executed directly on production virtual machines.
3. **Graph-only Dependency Mapping:**
   * *Why rejected:* Standard topology graphs map structural dependencies but cannot capture the *temporal intent* of a command run by a user.

## Consequences
- **Positive:**
  * **Accurate Operator Attribution:** The correlation engine can link the sudden disappearance of services to the exact command executed (e.g., `docker compose stop` or `terraform destroy`), raising RCA confidence to >90%.
  * **Actionable Recovery Suggestions:** Instead of telling the on-call engineer that three services are down, the pipeline can report: *"Subsystems stopped by operator command. Run rollback script immediately."*
- **Negative:**
  * **Security and Compliance Overhead:** Operational audit logs can contain sensitive arguments (like API keys or passwords). We must implement client-side redaction before ingestion.
  * **Operational Complexity:** Requires deploying logging agents (`auditd` daemon configurations) across all host machines.
- **Risks introduced:**
  * High-volume CI/CD pipeline runs could flood the correlator with noise, requiring strict filtering rules to ignore non-production environments.
- **What gets locked in:**
  * The AIOps pipeline schema will mandate a unified `OperationEvent` stream alongside Prometheus metrics and alerts.
