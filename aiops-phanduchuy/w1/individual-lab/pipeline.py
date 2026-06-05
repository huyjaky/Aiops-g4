from fastapi import FastAPI, Request
import json
import uvicorn
import collections

app = FastAPI()
ALERTS_FILE = "alerts.jsonl"

history = collections.deque(maxlen=5)
alerted_types = set()

def check_anomaly():
    if len(history) < 3:
        return None, None, None
        
    avg_upstream = sum(m["upstream_timeout_rate"] for m in history) / len(history)
    avg_rps = sum(m["http_requests_per_sec"] for m in history) / len(history)
    avg_mem = sum(m["memory_usage_bytes"] for m in history) / len(history)
    
    if avg_upstream > 3.0:
        return "dependency_timeout", "critical", f"Upstream timeout rate averaged {avg_upstream:.1f}% over recent ticks"
    
    if avg_rps > 250:
        return "traffic_spike", "critical", f"Traffic spiked to {avg_rps:.1f} req/s over recent ticks"
        
    if avg_mem > 900_000_000:
        return "memory_leak", "critical", f"Memory usage is abnormally high, averaging {avg_mem/1e6:.1f}MB"
        
    return None, None, None

@app.post("/ingest")
async def ingest(request: Request):
    payload = await request.json()
    metrics = payload["metrics"]
    logs = payload["logs"]
    timestamp = payload["timestamp"]

    print(f"[PIPELINE] Nhận data: RAM = {metrics['memory_usage_bytes'] / 1e6:.1f} MB")
    
    history.append(metrics)
    
    fault_type, severity, message = check_anomaly()
    
    if fault_type and fault_type not in alerted_types:
        alert = {
            "timestamp": timestamp, 
            "type": fault_type, 
            "severity": severity, 
            "message": message
        }
        with open(ALERTS_FILE, "a") as f:
            f.write(json.dumps(alert) + "\n")
        alerted_types.add(fault_type)
        print(f"[ALERT] {fault_type}: {message}")

    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
