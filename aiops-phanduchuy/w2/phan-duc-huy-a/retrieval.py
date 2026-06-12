import math
import os
from dotenv import load_dotenv

load_dotenv()
TRACE_ERROR_THRESHOLD = float(os.getenv("TRACE_ERROR_THRESHOLD", "0.05"))
TRACE_DEVIATION_THRESHOLD = float(os.getenv("TRACE_DEVIATION_THRESHOLD", "1.5"))

WEIGHT_SVC = float(os.getenv("WEIGHT_SVC", "0.2"))
WEIGHT_LOG = float(os.getenv("WEIGHT_LOG", "0.3"))
WEIGHT_TRACE = float(os.getenv("WEIGHT_TRACE", "0.3"))
WEIGHT_METRIC = float(os.getenv("WEIGHT_METRIC", "0.2"))

TOP_K = int(os.getenv("TOP_K", "3"))
OOD_THRESHOLD = float(os.getenv("OOD_THRESHOLD", "0.35"))
VOTING_SIM_THRESHOLD = float(os.getenv("VOTING_SIM_THRESHOLD", "0.35"))

def jaccard(set_a, set_b):
    if not set_a and not set_b:
        return 1.0
    return len(set_a & set_b) / len(set_a | set_b)

def parse_metric_delta(s: str) -> tuple[float, float]:
    parts = s.replace("->", "|").split("|")
    if len(parts) != 2:
        raise ValueError(f"unexpected delta format: {s!r}")
    return float(parts[0].strip()), float(parts[1].strip())

def compute_similarity(live: dict, hist: dict) -> float:
    # 1. Affected services similarity
    set_live_svc = set(live.get("affected_services", []))
    set_hist_svc = set(hist.get("affected_services", []))
    s_svc = jaccard(set_live_svc, set_hist_svc)
    
    # 2. Log signatures similarity
    set_live_logs = set(live.get("log_signatures", []))
    set_hist_logs = set(hist.get("log_signatures", []))
    s_log = jaccard(set_live_logs, set_hist_logs)
    
    # 3. Trace signatures similarity
    hist_traces = hist.get("trace_signatures", [])
    live_traces = { (t["from"], t["to"]): t for t in live.get("trace_signatures", []) }
    
    s_trace = 1.0
    if hist_traces:
        trace_scores = []
        for h_tr in hist_traces:
            edge = (h_tr["from"], h_tr["to"])
            if edge in live_traces:
                l_tr = live_traces[edge]
                dev_l = l_tr["p99_deviation_ratio"]
                dev_h = h_tr["p99_deviation_ratio"]
                sim_dev = 1.0 - abs(dev_l - dev_h) / max(dev_l, dev_h, 1.0)
                sim_dev = max(0.0, sim_dev)
                
                err_l = l_tr["error_rate"]
                err_h = h_tr["error_rate"]
                sim_err = 1.0 - abs(err_l - err_h)
                sim_err = max(0.0, sim_err)
                
                trace_scores.append(0.5 * sim_dev + 0.5 * sim_err)
            else:
                trace_scores.append(0.0)
        s_trace = sum(trace_scores) / len(trace_scores)
    else:
        has_live_trace_anom = any(t["p99_deviation_ratio"] > TRACE_DEVIATION_THRESHOLD or t["error_rate"] > TRACE_ERROR_THRESHOLD for t in live.get("trace_signatures", []))
        s_trace = 1.0 if not has_live_trace_anom else 0.5
        
    # 4. Metric signatures similarity
    hist_metrics = hist.get("metric_signatures", [])
    live_metrics = { (m["service"], m["metric"]): m for m in live.get("metric_signatures", []) }
    
    s_metric = 1.0
    if hist_metrics:
        metric_scores = []
        for h_m in hist_metrics:
            key = (h_m["service"], h_m["metric"])
            if key in live_metrics:
                try:
                    before_h, after_h = parse_metric_delta(h_m["delta"])
                    ratio_h = after_h / before_h if before_h > 0 else 1.0
                except Exception:
                    ratio_h = 1.0
                    
                l_m = live_metrics[key]
                before_l = l_m["before"]
                after_l = l_m["after"]
                ratio_l = after_l / before_l if before_l > 0 else 1.0
                
                sim_m = 1.0 - abs(ratio_l - ratio_h) / max(ratio_l, ratio_h, 1.0)
                sim_m = max(0.0, sim_m)
                metric_scores.append(sim_m)
            else:
                metric_scores.append(0.0)
        s_metric = sum(metric_scores) / len(metric_scores)
    else:
        has_live_metric_anom = any(m["after"]/m["before"] > float(os.getenv("METRIC_UPPER_THRESHOLD", "1.5")) or m["after"]/m["before"] < float(os.getenv("METRIC_LOWER_THRESHOLD", "0.5")) for m in live.get("metric_signatures", []) if m["before"] > 0)
        s_metric = 1.0 if not has_live_metric_anom else 0.5
        
    w_svc = WEIGHT_SVC
    w_log = WEIGHT_LOG
    w_trace = WEIGHT_TRACE
    w_metric = WEIGHT_METRIC
    
    total_weight = w_svc
    score = w_svc * s_svc
    
    if hist.get("log_signatures"):
        total_weight += w_log
        score += w_log * s_log
    if hist.get("trace_signatures"):
        total_weight += w_trace
        score += w_trace * s_trace
    if hist.get("metric_signatures"):
        total_weight += w_metric
        score += w_metric * s_metric
        
    return score / total_weight if total_weight > 0 else 0.0

def map_service_name(h_service: str, H: dict, query: dict) -> str:
    query_services = {n["id"] for n in query.get("topology", {}).get("nodes", [])}
    query_affected = set(query.get("affected_services", []))
    
    if h_service in query_services and h_service in query_affected:
        return h_service
        
    matched_sigs = [sig for sig in H.get("log_signatures", []) if sig in query.get("log_signatures", [])]
    if matched_sigs:
        for log in query.get("logs", []):
            for sig in matched_sigs:
                if sig in log.get("msg", ""):
                    svc = log.get("svc")
                    if svc:
                        return svc
                        
    anomalous_services = []
    for tr in query.get("trace_signatures", []):
        if tr["error_rate"] > TRACE_ERROR_THRESHOLD or tr["p99_deviation_ratio"] > TRACE_DEVIATION_THRESHOLD:
            anomalous_services.append((tr["from"], tr["error_rate"]))
            anomalous_services.append((tr["to"], tr["error_rate"]))
    if anomalous_services:
        anomalous_services.sort(key=lambda x: -x[1])
        return anomalous_services[0][0]
        
    if h_service in query_services:
        return h_service
        
    trigger_svc = query.get("trigger_alert", {}).get("service")
    if trigger_svc:
        return trigger_svc
        
    return h_service

def translate_action(action_str: str, H: dict, query: dict, actions_catalog: list[dict]) -> dict:
    parts = action_str.split(":")
    act_name = parts[0]
    act_args = parts[1:]
    
    catalog_entry = next((a for a in actions_catalog if a["name"] == act_name), None)
    if not catalog_entry:
        return {"name": act_name, "params": {}}
        
    param_names = catalog_entry.get("params", [])
    params = {}
    for idx, name in enumerate(param_names):
        if idx < len(act_args):
            val = act_args[idx]
            if name == "service":
                val = map_service_name(val, H, query)
            params[name] = val
            
    if act_name == "rollback_service" and "target_version" in params:
        params["target_version"] = "previous"
        
    return {"name": act_name, "params": params}

def retrieve_and_vote(query: dict, history: list[dict], actions_catalog: list[dict], top_k: int = TOP_K, ood_threshold: float = OOD_THRESHOLD) -> dict:
    scored_neighbors = []
    for hist in history:
        sim = compute_similarity(query, hist)
        scored_neighbors.append((hist, sim))
        
    scored_neighbors.sort(key=lambda x: -x[1])
    top_neighbors = scored_neighbors[:top_k]
    
    max_similarity = scored_neighbors[0][1] if scored_neighbors else 0.0
    is_ood = max_similarity < ood_threshold
    
    outcome_weights = {
        "success": 1.0,
        "partial": 0.5,
        "failed": 0.0
    }
    
    action_votes = {}
    
    for hist, sim in top_neighbors:
        if sim < VOTING_SIM_THRESHOLD:
            continue
        outcome = hist.get("outcome", "success")
        w_outcome = outcome_weights.get(outcome, 1.0)
        
        actions = hist.get("actions_taken", [])
        for act_str in actions:
            norm_act = translate_action(act_str, hist, query, actions_catalog)
            param_key = tuple(sorted(norm_act["params"].items()))
            key = (norm_act["name"], param_key)
            
            if key not in action_votes:
                action_votes[key] = {
                    "name": norm_act["name"],
                    "params": norm_act["params"],
                    "vote_score": 0.0,
                    "voters": []
                }
            vote = sim * w_outcome
            action_votes[key]["vote_score"] += vote
            action_votes[key]["voters"].append((hist["id"], sim, outcome))
            
    candidates = list(action_votes.values())
    candidates.sort(key=lambda x: -x["vote_score"])
    
    consensus_score = 0.0
    if candidates and top_neighbors:
        top_cand = candidates[0]
        voter_ids = {v[0] for v in top_cand["voters"]}
        voting_sim = sum(sim for hist, sim in top_neighbors if hist["id"] in voter_ids)
        total_sim = sum(sim for hist, sim in top_neighbors)
        consensus_score = (voting_sim / total_sim) if total_sim > 0 else 0.0
        
    return {
        "is_ood": is_ood,
        "max_similarity": max_similarity,
        "top_3_neighbors": [
            {"id": h["id"], "similarity": round(sim, 3), "root_cause_class": h.get("root_cause_class")}
            for h, sim in top_neighbors
        ],
        "consensus_score": round(consensus_score, 3),
        "candidates": candidates
    }
