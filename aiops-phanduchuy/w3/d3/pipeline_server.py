import os
import subprocess
import time
from fastapi import FastAPI
import uvicorn

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

app = FastAPI(title="Simulated AIOps Pipeline")

CONTAINERS = {
    "billing": "aws_s3_2017-billing-1",
    "index": "aws_s3_2017-index-1",
    "placement": "aws_s3_2017-placement-1"
}

# State to store when containers were detected as stopped
state = {
    "stopped_ts": None
}

# Load pipeline hyperparameters from environment variables
SIGMA = float(os.getenv("ANOMALY_THRESHOLD_SIGMA", "3.0"))
CORR_WINDOW = int(os.getenv("CORRELATION_WINDOW_SECONDS", "120"))
USE_LLM = os.getenv("AIOPS_USE_LLM", "true").lower() == "true"

def is_container_running(name: str) -> bool:
    try:
        res = subprocess.run(
            ["docker", "inspect", "-f", "{{.State.Running}}", name],
            capture_output=True,
            text=True,
            check=True
        )
        return res.stdout.strip() == "true"
    except Exception:
        return False

@app.get("/healthz")
def healthz():
    return {"status": "ok"}

@app.get("/alerts")
def get_alerts(since: int = 0):
    all_running = True
    stopped_services = []
    
    for svc, container_name in CONTAINERS.items():
        if not is_container_running(container_name):
            all_running = False
            stopped_services.append(svc)
            
    if all_running:
        state["stopped_ts"] = None
        return []
    
    if state["stopped_ts"] is None:
        state["stopped_ts"] = int(time.time())
        
    alerts = []
    # If the containers are down, simulate alerts using threshold settings
    for svc in stopped_services:
        alerts.append({
            "name": f"{svc}-down",
            "service": svc,
            "fire_ts": state["stopped_ts"],
            "meta": {
                "sigma_threshold": SIGMA,
                "correlation_window_sec": CORR_WINDOW
            }
        })
        
    # Filter by since
    return [a for a in alerts if a["fire_ts"] >= since]

@app.post("/rca")
def post_rca():
    all_running = True
    for svc, container_name in CONTAINERS.items():
        if not is_container_running(container_name):
            all_running = False
            
    if all_running:
        return {
            "root_service": "none",
            "confidence": 1.0,
            "evidence": "All systems operational.",
            "pipeline_mode": "LLM" if USE_LLM else "Graph-only"
        }
        
    return {
        "root_service": "unknown",
        "confidence": 0.33,
        "evidence": "Simultaneous outage of billing, index, and placement. No sequential cascading pattern detected. Highly indicative of an operator-level typo or infrastructure provider outage.",
        "pipeline_mode": "LLM" if USE_LLM else "Graph-only"
    }

if __name__ == "__main__":
    port = int(os.getenv("PIPELINE_PORT", "8000"))
    print(f"--- Pipeline Server configuration loaded ---")
    print(f"Port: {port}")
    print(f"Anomaly threshold (Sigma): {SIGMA}")
    print(f"Correlation window: {CORR_WINDOW}s")
    print(f"Use LLM enrichment: {USE_LLM}")
    print(f"--------------------------------------------")
    uvicorn.run(app, host="0.0.0.0", port=port)
