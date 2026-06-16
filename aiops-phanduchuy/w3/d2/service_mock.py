import os
import sys
import time
import json
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Shared state file path
STATE_FILE = os.getenv("STATE_FILE", "/app/shared/state.json")

def get_state():
    if not os.path.exists(STATE_FILE):
        return {"name": None, "t0": 0}
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {"name": None, "t0": 0}

def save_state(name, t0):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump({"name": name, "t0": t0}, f)

# Initialize the mock applications
pipeline_app = FastAPI(title="Mock AIOps Pipeline")
checkout_app = FastAPI(title="Mock Checkout Service")
prometheus_app = FastAPI(title="Mock Prometheus")

class ExperimentPayload(BaseModel):
    name: str

@pipeline_app.post("/inject")
def inject_experiment(payload: ExperimentPayload):
    t0 = int(time.time())
    save_state(payload.name, t0)
    print(f"[Mock Pipeline] Injected experiment: {payload.name}")
    return {"status": "success", "active_experiment": payload.name}

@pipeline_app.post("/rollback")
def rollback_experiment():
    state = get_state()
    print(f"[Mock Pipeline] Rollback active experiment: {state['name']}")
    save_state(None, 0)
    return {"status": "success"}

# GET /alerts?since=<ts>
@pipeline_app.get("/alerts")
def get_alerts(since: int = 0):
    state = get_state()
    exp_name = state["name"]
    t0 = state["t0"]
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
        "log_collector_disk": [],  # Simulated gap: Missed Detection
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
    state = get_state()
    exp_name = state["name"]
    if not exp_name:
        return {"root_service": "unknown", "confidence": 0.0, "evidence": "No active incident detected"}
    
    # Map experiment to expected root cause service
    rca_map = {
        "payment_latency": {"root_service": "payment-svc", "confidence": 0.95, "evidence": "Direct netem latency injected on payment-svc egress interface"},
        "payment_network_loss": {"root_service": "payment-svc", "confidence": 0.92, "evidence": "Egress packet loss (30%) on payment-svc interface"},
        "inventory_availability": {"root_service": "inventory-svc", "confidence": 0.88, "evidence": "Availability dropped to 0 due to inventory-svc pod delete"},
        "api_gateway_cpu": {"root_service": "api-gateway", "confidence": 0.91, "evidence": "api-gateway CPU spiked to 92%, causing downstream latency cascade"},
        "payment_db_memory": {"root_service": "payment-svc", "confidence": 0.85, "evidence": "DB connection pool saturated (98%) due to payment-db memory pressure but correlator attributed it to downstream dependency payment-svc"}, # Simulated gap: Wrong RCA
        "auth_clock_skew": {"root_service": "auth-svc", "confidence": 0.89, "evidence": "JWT validation failures surged due to auth-svc clock skew (+60s)"},
        "log_collector_disk": {"root_service": "log-collector", "confidence": 0.78, "evidence": "Log ingestion lag spiked because log-collector disk is 95% full"},
        "gateway_partition": {"root_service": "api-gateway", "confidence": 0.87, "evidence": "Network partition between frontend and api-gateway"},
        "dns_slow_lookup": {"root_service": "dns-resolver", "confidence": 0.82, "evidence": "Intermittent lookup failures matching dns-resolver latency spike"},
        "checkout_retry_storm": {"root_service": "payment-svc", "confidence": 0.81, "evidence": "Payment-svc overloaded by checkout retry storm"},
    }
    
    return rca_map.get(exp_name, {"root_service": "unknown", "confidence": 0.0, "evidence": "Unrecognized active experiment"})


# Checkout health mock
@checkout_app.get("/checkout/health")
def get_checkout_health():
    state = get_state()
    exp_name = state["name"]
    
    if not exp_name:
        return {"status": "ok"}
    
    # Simulate health degradation based on experiment
    if exp_name == "payment_latency":
        time.sleep(0.55)  # 550ms latency
        return {"status": "ok", "detail": "payment slow"}
    
    elif exp_name == "payment_network_loss":
        import random
        if random.random() < 0.3:
            return {"status": "error", "detail": "internal server error"}
        return {"status": "ok"}
        
    elif exp_name == "inventory_availability":
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


def main():
    if len(sys.argv) < 2:
        print("Usage: python service_mock.py <role>")
        sys.exit(1)
        
    role = sys.argv[1]
    print(f"[Service Mock] Starting role: {role}")
    
    pipeline_port = int(os.getenv("PIPELINE_PORT", "8000"))
    checkout_port = int(os.getenv("CHECKOUT_PORT", "8080"))
    prometheus_port = int(os.getenv("PROMETHEUS_PORT", "9090"))
    
    if role == "pipeline":
        uvicorn.run(pipeline_app, host="0.0.0.0", port=pipeline_port)
    elif role == "checkout-svc":
        uvicorn.run(checkout_app, host="0.0.0.0", port=checkout_port)
    elif role == "prometheus":
        uvicorn.run(prometheus_app, host="0.0.0.0", port=prometheus_port)
    else:
        # Idle microservices (frontend, api-gateway, payment-svc, inventory-svc, etc.)
        try:
            while True:
                time.sleep(3600)
        except KeyboardInterrupt:
            print(f"[Service Mock] Stopping role: {role}")

if __name__ == "__main__":
    main()
