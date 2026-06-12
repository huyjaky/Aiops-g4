import json
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
TRACE_ERROR_THRESHOLD = float(os.getenv("TRACE_ERROR_THRESHOLD", "0.05"))
TRACE_DEVIATION_THRESHOLD = float(os.getenv("TRACE_DEVIATION_THRESHOLD", "1.5"))
METRIC_UPPER_THRESHOLD = float(os.getenv("METRIC_UPPER_THRESHOLD", "1.5"))
METRIC_LOWER_THRESHOLD = float(os.getenv("METRIC_LOWER_THRESHOLD", "0.5"))

def parse_ts(ts_str):
    try:
        return datetime.strptime(ts_str, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        try:
            return datetime.strptime(ts_str, "%Y-%m-%dT%H:%M:%S.%fZ")
        except ValueError:
            return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))

def extract_features(incident: dict, history: list[dict]) -> dict:
    """
    Layer 1: Pull log + trace + metric features into a comparable dict representation.
    """
    detected_at_str = incident.get("detected_at")
    detected_at = parse_ts(detected_at_str)
    
    # 1. Extract matched log signatures from history
    all_log_sigs = set()
    for hist in history:
        for sig in hist.get("log_signatures", []):
            all_log_sigs.add(sig)
    
    matched_log_sigs = []
    # Concatenate all log lines to search in one pass
    all_logs_text = "\n".join([log.get("msg", "") for log in incident.get("logs", [])])
    for sig in sorted(list(all_log_sigs)):
        if sig in all_logs_text:
            matched_log_sigs.append(sig)
            
    # 2. Process traces to compute p99_deviation_ratio and error_rate for all active edges
    traces = incident.get("traces", [])
    edge_data = {}
    
    for t in traces:
        edge = (t["from"], t["to"])
        if edge not in edge_data:
            edge_data[edge] = {"baseline": [], "active": []}
        
        t_ts = parse_ts(t["ts"])
        if t_ts < detected_at:
            edge_data[edge]["baseline"].append(t)
        else:
            edge_data[edge]["active"].append(t)
            
    computed_traces = []
    for edge, periods in edge_data.items():
        base_records = periods["baseline"]
        act_records = periods["active"]
        
        base_count = sum(r.get("count", 0) for r in base_records)
        base_errors = sum(r.get("error_count", 0) for r in base_records)
        base_p99_sum = sum(r.get("p99_ms", 0.0) * r.get("count", 1) for r in base_records)
        avg_p99_base = (base_p99_sum / base_count) if base_count > 0 else 0.0
        
        act_count = sum(r.get("count", 0) for r in act_records)
        act_errors = sum(r.get("error_count", 0) for r in act_records)
        act_p99_sum = sum(r.get("p99_ms", 0.0) * r.get("count", 1) for r in act_records)
        avg_p99_act = (act_p99_sum / act_count) if act_count > 0 else 0.0
        
        error_rate = (act_errors / act_count) if act_count > 0 else 0.0
        
        if avg_p99_base > 0:
            p99_deviation_ratio = avg_p99_act / avg_p99_base
        else:
            p99_deviation_ratio = 1.0 if avg_p99_act == 0 else 2.0
            
        computed_traces.append({
            "from": edge[0],
            "to": edge[1],
            "p99_deviation_ratio": p99_deviation_ratio,
            "error_rate": error_rate,
            "avg_p99_base": avg_p99_base,
            "avg_p99_act": avg_p99_act
        })
        
    # 3. Process metrics to find baseline vs active deltas
    metrics = incident.get("metrics_window", {})
    samples = metrics.get("samples", {})
    computed_metrics = []
    
    for metric_name, sample_points in samples.items():
        parts = metric_name.split(".", 1)
        if len(parts) == 2:
            service, m_name = parts
        else:
            service = parts[0]
            m_name = "unknown"
            
        baseline_vals = []
        active_vals = []
        
        for pt in sample_points:
            pt_ts = parse_ts(pt[0])
            val = pt[1]
            if pt_ts < detected_at:
                baseline_vals.append(val)
            else:
                active_vals.append(val)
                
        avg_base = sum(baseline_vals) / len(baseline_vals) if baseline_vals else 0.0
        avg_act = sum(active_vals) / len(active_vals) if active_vals else 0.0
        
        computed_metrics.append({
            "service": service,
            "metric": m_name,
            "before": avg_base,
            "after": avg_act
        })
        
    # 4. Determine affected services
    affected = set()
    trigger = incident.get("trigger_alert", {})
    if trigger.get("service"):
        affected.add(trigger["service"])
        
    for log in incident.get("logs", []):
        if log.get("level") in ("ERROR", "CRITICAL", "SEVERE", "FATAL"):
            if log.get("svc"):
                affected.add(log["svc"])
                
    for ct in computed_traces:
        if ct["error_rate"] > TRACE_ERROR_THRESHOLD or ct["p99_deviation_ratio"] > TRACE_DEVIATION_THRESHOLD:
            affected.add(ct["from"])
            affected.add(ct["to"])
            
    for cm in computed_metrics:
        ratio = (cm["after"] / cm["before"]) if cm["before"] > 0 else 1.0
        if ratio > METRIC_UPPER_THRESHOLD or ratio < METRIC_LOWER_THRESHOLD:
            affected.add(cm["service"])
            
    return {
        "incident_id": incident.get("incident_id"),
        "trigger_alert": trigger,
        "affected_services": sorted(list(affected)),
        "log_signatures": matched_log_sigs,
        "trace_signatures": computed_traces,
        "metric_signatures": computed_metrics,
        "logs": incident.get("logs", [])
    }
