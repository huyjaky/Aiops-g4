# Postmortem: AWS S3 us-east-1 Disruption (2017-02-28)

## Summary
On 2017-02-28, a routine billing subsystem maintenance command was executed with incorrect parameters, causing the unintended removal of a larger set of servers than planned. This set included critical servers from the S3 index and placement subsystems, which are responsible for metadata storage and routing. The removal of these subsystems disabled all S3 API operations in the us-east-1 region for 4 hours and 11 minutes.

## Impact
- **Users affected:** ~100% of S3 API operations in us-east-1, impacting thousands of downstream applications, websites, and cloud dependencies.
- **Services affected:** S3 Billing, S3 Index, and S3 Placement subsystems.
- **Revenue/SLA impact:** Extensive SLA breaches and credit requests from enterprise customers.
- **Duration:** 2017-02-28 17:37:00 UTC → 2017-02-28 21:48:00 UTC (4 hours and 11 minutes).

## Timeline (UTC)
Timeline events mapped from the simulated reproduction container events (`timeline.json`) and the original incident timeline:

| UTC | Event |
|-----|-------|
| 2017-02-28 17:37:00 | Maintenance window starts; operator begins execution of billing server replacement script. |
| 2017-02-28 17:37:38 | Script is invoked, but incorrect parameters bypass scope boundaries and target all subsystems in the compose context. |
| 2017-02-28 17:38:00 | Script executes destructive action, triggering `kill` signal on container `aws_s3_2017-placement-1`. |
| 2017-02-28 17:38:05 | Script triggers `kill` signal on container `aws_s3_2017-index-1`. |
| 2017-02-28 17:38:10 | Script triggers `kill` signal on container `aws_s3_2017-billing-1`. |
| 2017-02-28 17:38:15 | Container `aws_s3_2017-placement-1` is stopped (disconnect and stop events). |
| 2017-02-28 17:38:20 | Container `aws_s3_2017-index-1` is stopped (disconnect and stop events). |
| 2017-02-28 17:38:25 | Container `aws_s3_2017-billing-1` is stopped (disconnect and stop events). |
| 2017-02-28 17:38:30 | Downstream health checks on S3 Gateway begin failing with HTTP 500 errors. |
| 2017-02-28 17:38:57 | AIOps pipeline receives status change events and registers `billing-down`, `index-down`, and `placement-down` alerts. |
| 2017-02-28 17:39:15 | On-call engineer receives alerts and begins investigating. |
| 2017-02-28 19:40:00 | Root cause is identified; manual startup of index and placement subsystems is initiated. |
| 2017-02-28 21:00:00 | Index and placement subsystems complete cold-start data validation. S3 APIs begin to accept requests. |
| 2017-02-28 21:48:00 | S3 Gateway services return to normal latencies. Incident resolved. |

## Root Cause
The billing maintenance scripts lacked parameter verification and safety guardrails, permitting a command meant to stop a subset of billing servers to propagate globally across all services defined in the orchestration context, stopping the critical S3 index and placement subsystems.

## Contributing Factors
1. **Lack of Blast-Radius Boundaries:** The administrative tooling was not containerized or restricted to query only its local subsystem; it had authorization to stop critical systems.
2. **Cold-Start Metadata Validation Delay:** The S3 index and placement subsystems had not undergone a full cold restart in years. The verification processes on startup took significantly longer than expected (over 2 hours).
3. **No Dry-Run Mode:** Destructive commands did not support a dry-run confirmation showing which resource IDs would be removed before execution.

## Detection
- **How was it detected?** Pipeline alerts registered container termination, while external gateways flagged high HTTP 500 error rates.
- **MTTD:** 79 seconds (from script execution at 17:37:38 to pipeline alerts at 17:38:57).
- **Pipeline gaps observed during reproduction:**
  - **Gap 1: Missing Operational Context Ingestion.** The pipeline was unable to differentiate between an infrastructure crash and an intentional manual operator action because it does not ingest audit logs, bash history, or Ansible/Terraform executions.
  - **Gap 2: Inability to Resolve Flat Cascades.** Because all three subsystems went down at the exact same second, the pipeline correlator returned `unknown` for the root cause. Without sequential lag (cause preceding effect), the pipeline cannot infer causality on flat topology.

## Response
- **First responder action:** Checked container orchestration status and verified that the billing replacement script had removed placement and index servers.
- **Time to mitigate:** 3 hours and 22 minutes (to get placement and index back online).
- **Time to fully resolve:** 4 hours and 11 minutes.

## Action Items
| # | Action | Owner | Type | ETA |
|---|--------|-------|------|-----|
| 1 | Add input argument validation and confirmation prompts to billing scripts. | DevOps Team | preventive | 2017-03-05 |
| 2 | Restructure compose/configuration contexts to isolate placement and index subsystems from billing. | Tech Lead | preventive | 2017-03-10 |
| 3 | Integrate shell command auditing and pipeline deployment logs into AIOps pipeline. | AIOps Team | detective | 2017-03-12 |
| 4 | Conduct routine failure tests of index and placement cold starts to optimize recovery time. | SRE Team | mitigation | 2017-04-01 |
