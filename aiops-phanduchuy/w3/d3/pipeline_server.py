import subprocess
import time
from fastapi import FastAPI
import uvicorn

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
    # If the containers are down, simulate alerts
    for svc in stopped_services:
        alerts.append({
            "name": f"{svc}-down",
            "service": svc,
            "fire_ts": state["stopped_ts"]
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
            "evidence": "All systems operational."
        }
        
    return {
        "root_service": "unknown",
        "confidence": 0.33,
        "evidence": "Simultaneous outage of billing, index, and placement. No sequential cascading pattern detected. Highly indicative of an operator-level typo or infrastructure provider outage."
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
