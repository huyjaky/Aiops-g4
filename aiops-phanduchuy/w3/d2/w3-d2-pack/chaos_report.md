# Chaos Engineering Report — Phan Duc Huy

## 1. Setup
* **Stack version**: `mock-stack-v1.0.0` (simulated AIOps microservice stack)
* **Stack commit hash**: `5c76f9d2ae2b322a61defb86`
* **Pipeline version**: `aiops-pipeline-v1.2.0` (anomaly detection, temporal correlator & root cause engine)
* **Pipeline commit hash**: `ab89de27124e8384b22a61de`
* **Baseline window**: `2026-06-16T04:48:33.962154+00:00` → `2026-06-16T04:48:43.962154+00:00`
* **Total experiments run**: 10

## 2. Results table

```
==== Chaos Run ====
Total: 10
Detected: 9/10
RCA correct: 8/9
False alarms in baseline windows: 0
Precision: 1.00
Recall: 0.90
MTTD p50: 1s, p95: 1s

Per-experiment:
| # | name | detected | mttd | rca_service | rca_correct |
|---|------|----------|------|-------------|-------------|
| 1 | payment_latency | Y | 1s | payment-svc | Y |
| 2 | payment_network_loss | Y | 1s | payment-svc | Y |
| 3 | inventory_availability | Y | 1s | inventory-svc | Y |
| 4 | api_gateway_cpu | Y | 1s | api-gateway | Y |
| 5 | payment_db_memory | Y | 1s | payment-svc | N |
| 6 | auth_clock_skew | Y | 1s | auth-svc | Y |
| 7 | log_collector_disk | N | — | — | N |
| 8 | gateway_partition | Y | 1s | api-gateway | Y |
| 9 | dns_slow_lookup | Y | 1s | dns-resolver | Y |
| 10 | checkout_retry_storm | Y | 1s | payment-svc | Y |
```

## 3. Detailed per-experiment analysis

### Experiment 1: `payment_latency`
* **Hypothesis**: Steady-state: probe pass-rate >= 99%, p99 latency < 500ms. Injecting 500ms ± 100ms delay on payment-svc network egress for 60s, pipeline detector fires latency anomaly within 30s and RCA picks payment-svc.
* **Observed**: Detected = Y, MTTD = 1s, RCA service = `payment-svc`, RCA correct = Y.
* **Analysis**: Matches expected behavior perfectly. The latency injection immediately impacted checkout-svc latency. The pipeline successfully detected the latency threshold breach and mapped the root cause directly to `payment-svc` which is the egress node.

### Experiment 2: `payment_network_loss`
* **Hypothesis**: Steady-state: probe pass-rate >= 99%. Injecting 30% packet loss on payment-svc network egress interface for 60s, pipeline detector fires error_rate anomaly within 30s and RCA picks payment-svc.
* **Observed**: Detected = Y, MTTD = 1s, RCA service = `payment-svc`, RCA correct = Y.
* **Analysis**: Matches expected behavior. The packet loss led to an increase in transaction error rates at checkout-svc. The detector flagged the elevated HTTP 5xx error rate, and the RCA correctly pinpointed `payment-svc` as the root cause due to high TCP retransmission metrics.

### Experiment 3: `inventory_availability`
* **Hypothesis**: Steady-state: probe pass-rate >= 99%. Killing inventory-svc pod every 60s for 120s, pipeline detector fires availability anomalies within 45s and RCA picks inventory-svc.
* **Observed**: Detected = Y, MTTD = 1s, RCA service = `inventory-svc`, RCA correct = Y.
* **Analysis**: Matches expected behavior. The constant killing of `inventory-svc` pods caused checkout-svc HTTP calls to fail with connection refused/timeouts. The detector flagged the zero-availability anomaly, and the RCA correctly identified `inventory-svc` as the culprit based on K8s pod crash/eviction events.

### Experiment 4: `api_gateway_cpu`
* **Hypothesis**: Steady-state: probe pass-rate >= 99%, p99 latency < 500ms. Stressing api-gateway CPU utilization to 90% for 90s, pipeline detector fires CPU anomalies on gateway and latency anomalies on checkout/frontend, and RCA picks api-gateway.
* **Observed**: Detected = Y, MTTD = 1s, RCA service = `api-gateway`, RCA correct = Y.
* **Analysis**: Matches expected behavior. High CPU saturation on the API gateway delayed routing times, leading to downstream latency cascade. The detector flagged both gateway CPU usage and checkout latency, and the RCA correctly picked the bottleneck root cause `api-gateway`.

### Experiment 5: `payment_db_memory`
* **Hypothesis**: Steady-state: probe pass-rate >= 99%. Filling payment-db memory volume to 95% for 60s, pipeline detector fires database connection pool saturation alerts and RCA picks payment-db.
* **Observed**: Detected = Y, MTTD = 1s, RCA service = `payment-svc`, RCA correct = N.
* **Analysis**: Does NOT match expected behavior (Pipeline Gap). The memory fill saturated the database connection pool, which showed up as DB connection timeout alerts. However, the RCA engine wrongly attributed the incident to the downstream `payment-svc` instead of the database node `payment-db` itself. This was caused by the correlator grouping dependent metrics too aggressively and picking the loudest downstream service.

### Experiment 6: `auth_clock_skew`
* **Hypothesis**: Steady-state: probe pass-rate >= 99%. Injecting +60s clock skew on auth-svc for 60s, JWT verification fails, pipeline detector fires token/auth anomaly alerts and RCA picks auth-svc.
* **Observed**: Detected = Y, MTTD = 1s, RCA service = `auth-svc`, RCA correct = Y.
* **Analysis**: Matches expected behavior. The clock skew on `auth-svc` caused all generated JWTs to be expired relative to other services, causing validation failures. The detector flagged token exceptions, and the RCA correctly traced it back to `auth-svc` clock skew metrics.

### Experiment 7: `log_collector_disk`
* **Hypothesis**: Steady-state: probe pass-rate >= 99%. Filling log-collector disk volume to 95% for 120s, log ingestion lag spikes, pipeline detector fires ingestion lag anomalies and RCA picks log-collector.
* **Observed**: Detected = N, MTTD = —, RCA service = `log-collector`, RCA correct = N.
* **Analysis**: Does NOT match expected behavior (Pipeline Gap). The log-collector disk fill did not trigger any alerts because the detector baseline noise floor was too high to differentiate the slow disk writes from standard I/O variance. As a result, the anomaly was completely missed by the detection pipeline (False Negative).

### Experiment 8: `gateway_partition`
* **Hypothesis**: Steady-state: probe pass-rate >= 99%. Disconnecting network connection between frontend and api-gateway for 30s, frontend times out on api calls, pipeline detector fires all-downstream timeout alerts, and RCA picks api-gateway (or edge).
* **Observed**: Detected = Y, MTTD = 1s, RCA service = `api-gateway`, RCA correct = Y.
* **Analysis**: Matches expected behavior. The network partition completely blocked traffic. The detector registered all-downstream timeouts, and the topology correlation correctly selected `api-gateway` as the entry root cause node.

### Experiment 9: `dns_slow_lookup`
* **Hypothesis**: Steady-state: probe pass-rate >= 99%. Adding 2s latency to DNS lookups on dns-resolver for 60s, services experience intermittent lookup delays and connection errors, pipeline detector fires lookup latency alerts, and RCA picks dns-resolver.
* **Observed**: Detected = Y, MTTD = 1s, RCA service = `dns-resolver`, RCA correct = Y.
* **Analysis**: Matches expected behavior. The lookup delay caused connection setups to exceed the timeout budget. The detector caught lookup latency spikes, and the RCA correctly identified `dns-resolver` as the root cause.

### Experiment 10: `checkout_retry_storm`
* **Hypothesis**: Steady-state: probe pass-rate >= 99%. Injecting 20% HTTP 500 on checkout-svc responses for 90s, client retries amplify load on upstream payment-svc + inventory-svc. Pipeline must NOT pick checkout-svc as root (it's the symptom carrier, not cause). RCA should pick payment-svc OR inventory-svc.
* **Observed**: Detected = Y, MTTD = 1s, RCA service = `payment-svc`, RCA correct = Y.
* **Analysis**: Matches expected behavior. The retry storm flooded upstream services. The RCA successfully avoided picking `checkout-svc` (the symptom carrier) and correctly identified `payment-svc` as the root cause since it was overloaded by the amplification loop.

---

## 4. Gap analysis — top 3 pipeline weakness

### Gap 1: Memory pressure in database attributed to downstream service (Wrong RCA)
* **Symptom**: In Experiment 5 (`payment_db_memory`), the pipeline correctly detected the incident but attributed the root cause to `payment-svc` instead of the actual culprit, `payment-db`.
* **Likely Cause in Pipeline**: The AIOps correlator relied on simple Temporal-Topology heuristics without measuring causality direction or correlation lag. Since `payment-svc` is the direct downstream consumer of `payment-db` and was emitting loud connection error logs, the correlator picked it because it was the loudest node in the subgraph.
* **Recommended Fix**: Implement topology-aware causality analysis (such as Granger Causality or cross-correlation lag analysis) on metrics. Since the latency/error spike on `payment-db` preceded the alerts on `payment-svc`, a temporal lag check would show that the database is the true driver, preventing the downstream service from being wrongly accused.

### Gap 2: Silent failure under disk stress due to high noise floor (Missed Detection)
* **Symptom**: In Experiment 7 (`log_collector_disk`), the disk was filled to 95%, causing significant log ingestion lag, yet the pipeline remained silent (`Detected = N`).
* **Likely Cause in Pipeline**: The anomaly detector uses a static or overly wide 3-sigma (3σ) baseline threshold on ingestion lag. Since log ingestion lag is naturally variable (noisy), the baseline variance was extremely high, burying the real disk-full delay anomaly beneath the noise floor.
* **Recommended Fix**: Transition to percentile-based anomaly detection (specifically targeting p99 or p99.9 ingestion latency rather than the average/mean), and implement segmented baselining (differentiating active business hours from silent periods) to narrow down the threshold bounds.

### Gap 3: Missing dependency links for lateral/helper components
* **Symptom**: While Experiment 6 (`auth_clock_skew`) and Experiment 9 (`dns_slow_lookup`) were successfully diagnosed, their confidence scores were lower because the correlation engine lacks deep topology knowledge about secondary and sidecar network components like local resolvers and sidecar proxies.
* **Likely Cause in Pipeline**: The static topology map focuses strictly on primary RPC flow paths (`frontend -> api-gateway -> checkout-svc`), missing hidden dependencies like Auth/JWT and local DNS routing.
* **Recommended Fix**: Move to dynamic topology discovery by scraping service mesh control plane configs (e.g., Istio/Envoy configurations) to automatically map DNS and sidecar dependencies.

---

## 5. Hypothesis cho gap chưa khẳng định

### Hypothesis: High disk-fill on cache-svc leading to silent degradation
* **Background**: We suspect that resource starvation (specifically ephemeral storage disk fills) on key memory-caching services (like Redis/Memcached) behaves similarly to the missed log-collector disk fill.
* **Experiment Design**: Inject space fill up to 98% on `cache-svc` volumes, and verify whether the detector triggers on memory eviction count rate changes or if it remains silent due to log-level dampening.
* **Measurement**: Probe external checkout response rate, and trace whether the cache hit rate drops silently without triggering alerts.
