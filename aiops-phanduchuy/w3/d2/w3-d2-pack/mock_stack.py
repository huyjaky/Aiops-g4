import os
import time
import uvicorn
from fastapi import FastAPI, Request
from pydantic import BaseModel

# Initialize the mock applications
pipeline_app = FastAPI(title="Mock AIOps Pipeline")
checkout_app = FastAPI(title="Mock Checkout Service")
prometheus_app = FastAPI(title="Mock Prometheus")

# State to store the active experiment name
# Default is None (steady state)
active_experiment = {"name": None, "t0": 0}

class ExperimentPayload(BaseModel):
    name: str

@pipeline_app.post("/inject")
def inject_experiment(payload: ExperimentPayload):
    active_experiment["name"] = payload.name
    active_experiment["t0"] = int(time.time())
    print(f"[Mock Pipeline] Injected experiment: {payload.name}")
    return {"status": "success", "active_experiment": payload.name}

@pipeline_app.post("/rollback")
def rollback_experiment():
    print(f"[Mock Pipeline] Rollback active experiment: {active_experiment['name']}")
    active_experiment["name"] = None
    active_experiment["t0"] = 0
    return {"status": "success"}

# Section 8.1 / 8.5 endpoints
# GET /alerts?since=<ts>
@pipeline_app.get("/alerts")
def get_alerts(since: int = 0):
    exp_name = active_experiment["name"]
    t0 = active_experiment["t0"]
    now = int(time.time())
    
    # If no experiment is active, return no alerts
    if not exp_name:
        return []
    
    # Generate mock alerts based on the experiment
    alert_time = t0 + 1  # fires 1 second after injection
    
    # Map experiment name to alerts
    alerts_map = {
        "payment_latency": [
            {"id": "alert-1", "fire_ts": alert_time, "service": "payment-svc", "metric": "latency", "severity": "critical", "value": 550.0, "threshold": 500.0}
        ],
        "payment_network_loss": [
            {"id": "alert-2", "fire_ts": alert_time, "service": "payment-svc", "metric": "error_rate", "severity": "critical", "value": 0.32, "threshold": 0.05}
        ],
        "inventory_availability": [
            {"id": "alert-3", "fire_ts": alert_time, "service": "inventory-svc", "metric": "availability", "severity": "critical", "value": 0.0, "threshold": 0.99}
        ],
        "api_gateway_cpu": [
            {"id": "alert-4", "fire_ts": alert_time, "service": "api-gateway", "metric": "cpu_usage", "severity": "warning", "value": 0.92, "threshold": 0.90},
            {"id": "alert-4-downstream", "fire_ts": alert_time + 5, "service": "checkout-svc", "metric": "latency", "severity": "critical", "value": 1200.0, "threshold": 500.0}
        ],
        "payment_db_memory": [
            {"id": "alert-5", "fire_ts": alert_time, "service": "payment-db", "metric": "connection_pool_saturation", "severity": "critical", "value": 0.98, "threshold": 0.85}
        ],
        "auth_clock_skew": [
            {"id": "alert-6", "fire_ts": alert_time, "service": "auth-svc", "metric": "jwt_validation_failures", "severity": "critical", "value": 15.0, "threshold": 2.0}
        ],
        "log_collector_disk": [],
        "gateway_partition": [
            {"id": "alert-8", "fire_ts": alert_time, "service": "api-gateway", "metric": "all_downstream_timeout", "severity": "critical", "value": 1.0, "threshold": 0.5}
        ],
        "dns_slow_lookup": [
            {"id": "alert-9", "fire_ts": alert_time, "service": "dns-resolver", "metric": "lookup_latency_seconds", "severity": "critical", "value": 2.2, "threshold": 0.5}
        ],
        "checkout_retry_storm": [
            {"id": "alert-10", "fire_ts": alert_time, "service": "checkout-svc", "metric": "http_500_rate", "severity": "critical", "value": 0.20, "threshold": 0.05},
            {"id": "alert-10-retry", "fire_ts": alert_time + 5, "service": "payment-svc", "metric": "request_count", "severity": "warning", "value": 250.0, "threshold": 100.0}
        ],
    }
    
    raw_alerts = alerts_map.get(exp_name, [])
    # Filter alerts by since timestamp
    return [a for a in raw_alerts if a["fire_ts"] >= since]

# POST /rca
@pipeline_app.post("/rca")
def post_rca(payload: dict):
    exp_name = active_experiment["name"]
    if not exp_name:
        return {"root_service": "unknown", "confidence": 0.0, "evidence": "No active incident detected"}
    
    # Map experiment to expected root cause service
    rca_map = {
        "payment_latency": {"root_service": "payment-svc", "confidence": 0.95, "evidence": "Direct netem latency injected on payment-svc egress interface"},
        "payment_network_loss": {"root_service": "payment-svc", "confidence": 0.92, "evidence": "Egress packet loss (30%) on payment-svc interface"},
        "inventory_availability": {"root_service": "inventory-svc", "confidence": 0.88, "evidence": "Availability dropped to 0 due to inventory-svc pod delete"},
        "api_gateway_cpu": {"root_service": "api-gateway", "confidence": 0.91, "evidence": "api-gateway CPU spiked to 92%, causing downstream latency cascade"},
        "payment_db_memory": {"root_service": "payment-svc", "confidence": 0.85, "evidence": "DB connection pool saturated (98%) due to payment-db memory pressure but correlator attributed it to downstream dependency payment-svc"},
        "auth_clock_skew": {"root_service": "auth-svc", "confidence": 0.89, "evidence": "JWT validation failures surged due to auth-svc clock skew (+60s)"},
        "log_collector_disk": {"root_service": "log-collector", "confidence": 0.78, "evidence": "Log ingestion lag spiked because log-collector disk is 95% full"},
        "gateway_partition": {"root_service": "api-gateway", "confidence": 0.87, "evidence": "Network partition between frontend and api-gateway"},
        "dns_slow_lookup": {"root_service": "dns-resolver", "confidence": 0.82, "evidence": "Intermittent lookup failures matching dns-resolver latency spike"},
        # For checkout_retry_storm, expected root service is NOT checkout-svc
        # The prompt says: "RCA must NOT pick checkout-svc... should pick payment-svc OR inventory-svc"
        "checkout_retry_storm": {"root_service": "payment-svc", "confidence": 0.81, "evidence": "Payment-svc overloaded by checkout retry storm"},
    }
    
    return rca_map.get(exp_name, {"root_service": "unknown", "confidence": 0.0, "evidence": "Unrecognized active experiment"})


# Checkout health mock
@checkout_app.get("/checkout/health")
def get_checkout_health():
    exp_name = active_experiment["name"]
    
    if not exp_name:
        # Healthy steady state
        return {"status": "ok"}
    
    # Simulate health degradation based on experiment
    if exp_name == "payment_latency":
        time.sleep(0.55)  # 550ms latency
        return {"status": "ok", "detail": "payment slow"}
    
    elif exp_name == "payment_network_loss":
        # Simulate 30% failure rate
        import random
        if random.random() < 0.3:
            return {"status": "error", "detail": "internal server error"}
        return {"status": "ok"}
        
    elif exp_name == "inventory_availability":
        # Down
        return {"status": "error", "detail": "inventory-svc down"}
        
    elif exp_name == "api_gateway_cpu":
        time.sleep(1.2)  # High latency cascade
        return {"status": "ok"}
        
    elif exp_name == "payment_db_memory":
        time.sleep(0.5)
        return {"status": "error", "detail": "payment db timeout"}
        
    elif exp_name == "auth_clock_skew":
        return {"status": "error", "detail": "unauthorized"}
        
    elif exp_name == "gateway_partition":
        # Partition checkout/gateway
        time.sleep(2.0)
        return {"status": "error", "detail": "gateway timeout"}
        
    elif exp_name == "dns_slow_lookup":
        time.sleep(2.2)  # DNS slow lookup
        return {"status": "ok"}
        
    elif exp_name == "checkout_retry_storm":
        import random
        if random.random() < 0.2:
            return {"status": "error", "detail": "retry storm 500"}
        return {"status": "ok"}
        
    # Default healthy
    return {"status": "ok"}


# Prometheus mock `/api/v1/query`
@prometheus_app.get("/api/v1/query")
def get_prometheus_query(query: str):
    import random
    value = 0.0
    if "rate(http_requests_total[1m])" in query:
        value = 100.0 + random.uniform(-5, 5)
    elif "histogram_quantile" in query:
        value = 0.12 + random.uniform(-0.02, 0.02)
    elif "status=~'5..'" in query:
        value = 0.01 + random.uniform(-0.005, 0.005)
    elif "container_memory_usage_bytes" in query:
        value = 1073741824.0 + random.uniform(-10000, 10000)
    elif "rate(container_cpu_usage_seconds_total[1m])" in query:
        value = 0.15 + random.uniform(-0.02, 0.02)
    
    return {
        "status": "success",
        "data": {
            "resultType": "vector",
            "result": [
                {
                    "metric": {},
                    "value": [int(time.time()), str(value)]
                }
            ]
        }
    }


def start_all():
    # We will run this script and it will spin up three threads/servers
    # Let's run uvicorn programmatically in threads
    import threading
    
    t1 = threading.Thread(target=lambda: uvicorn.run(pipeline_app, host="127.0.0.1", port=28000), daemon=True)
    t2 = threading.Thread(target=lambda: uvicorn.run(checkout_app, host="127.0.0.1", port=28080), daemon=True)
    t3 = threading.Thread(target=lambda: uvicorn.run(prometheus_app, host="127.0.0.1", port=29090), daemon=True)
    
    t1.start()
    t2.start()
    t3.start()
    
    print("[Mock Stack] Running services on ports 28000 (pipeline), 28080 (checkout), and 29090 (prometheus)...")
    
    # Keep main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("[Mock Stack] Shutting down...")

if __name__ == "__main__":
    start_all()
