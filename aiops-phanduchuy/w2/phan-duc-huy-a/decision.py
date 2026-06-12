import os
from dotenv import load_dotenv

load_dotenv()
TRACE_ERROR_THRESHOLD = float(os.getenv("TRACE_ERROR_THRESHOLD", "0.05"))
TRACE_DEVIATION_THRESHOLD = float(os.getenv("TRACE_DEVIATION_THRESHOLD", "1.5"))
COST_PAGE = float(os.getenv("COST_PAGE", "35.0"))
BLAST_RADIUS_LIMIT = int(os.getenv("BLAST_RADIUS_LIMIT", "3"))
BLAST_RADIUS_CONF_THRESHOLD = float(os.getenv("BLAST_RADIUS_CONF_THRESHOLD", "0.70"))

def select_action(retrieval_results: dict, actions_catalog: list[dict], query_incident: dict) -> dict:
    """
    Layer 3: Cost-aware expected utility (EV) + blast-radius safety gate.
    """
    is_ood = retrieval_results.get("is_ood", False)
    candidates = retrieval_results.get("candidates", [])
    top_3_neighbors = retrieval_results.get("top_3_neighbors", [])
    consensus_score = retrieval_results.get("consensus_score", 0.0)
    max_similarity = retrieval_results.get("max_similarity", 0.0)
    
    page_action = {
        "selected_action": "page_oncall",
        "params": {"team": "platform-team"},
        "confidence": round(max(0.5, max_similarity), 3),
        "top_3_neighbors": top_3_neighbors,
        "consensus_score": consensus_score,
        "blast_radius_check": "passed",
        "evidence": {
            "reason": "Escalating to platform team.",
            "is_ood": is_ood,
            "max_similarity": max_similarity
        }
    }
    
    if is_ood or not candidates:
        page_action["confidence"] = 1.0 if is_ood else round(max(0.5, max_similarity), 3)
        page_action["evidence"]["reason"] = "Incident is Out-of-Distribution or no historical matches found."
        return page_action
        
    catalog_meta = { a["name"]: a for a in actions_catalog }
    
    total_votes = sum(c["vote_score"] for c in candidates)
    if total_votes > 0:
        for c in candidates:
            c["prob"] = (c["vote_score"] / total_votes) * max_similarity
    else:
        for c in candidates:
            c["prob"] = 0.0
            
    candidates.sort(key=lambda x: -x["prob"])
    
    trace_anomalous_services = set()
    for tr in query_incident.get("trace_signatures", []):
        if tr["error_rate"] > TRACE_ERROR_THRESHOLD or tr["p99_deviation_ratio"] > TRACE_DEVIATION_THRESHOLD:
            trace_anomalous_services.add(tr["from"])
            trace_anomalous_services.add(tr["to"])
            
    trigger_svc = query_incident.get("trigger_alert", {}).get("service")
    if trigger_svc:
        trace_anomalous_services.add(trigger_svc)
        
    valid_candidates = []
    for c in candidates:
        name = c["name"]
        params = c["params"]
        
        if name == "increase_pool_size":
            is_deadlock = any("deadlock" in sig.lower() or "lock" in sig.lower() for sig in query_incident.get("log_signatures", []))
            if is_deadlock:
                continue
                
        if name in ("rollback_service", "restart_pod", "increase_pool_size"):
            target_svc = params.get("service")
            if target_svc and target_svc not in trace_anomalous_services:
                continue
        valid_candidates.append(c)
        
    if not valid_candidates:
        page_action["evidence"]["reason"] = "All candidate auto-actions failed the trace anomaly guardrail."
        return page_action
        
    cost_page = COST_PAGE
    
    best_action = None
    min_expected_cost = cost_page
    
    for c in valid_candidates:
        name = c["name"]
        params = c["params"]
        prob = c["prob"]
        
        meta = catalog_meta.get(name)
        if not meta or name == "page_oncall":
            continue
            
        cost_min = meta.get("cost_min", 0)
        downtime_min = meta.get("downtime_min", 0)
        
        cost_action = cost_min + 2 * downtime_min
        
        expected_cost = cost_action + (1.0 - prob) * cost_page
        
        c["expected_cost"] = expected_cost
        c["cost_action"] = cost_action
        
        if expected_cost < min_expected_cost:
            min_expected_cost = expected_cost
            best_action = c
            
    if not best_action:
        page_action["evidence"]["reason"] = "Paging oncall has lower expected cost than any auto-action."
        page_action["evidence"]["candidate_costs"] = [
            {"name": c["name"], "params": c["params"], "prob": round(c["prob"], 3)}
            for c in valid_candidates[:3]
        ]
        return page_action
        
    meta = catalog_meta.get(best_action["name"])
    blast_radius = meta.get("blast_radius_services", 0)
    confidence = best_action["prob"]
    
    blast_radius_check = "passed"
    if blast_radius >= BLAST_RADIUS_LIMIT and confidence < BLAST_RADIUS_CONF_THRESHOLD:
        blast_radius_check = f"failed (blast_radius={blast_radius}, confidence={round(confidence, 3)} < 0.70)"
        page_action["evidence"]["reason"] = f"Action '{best_action['name']}' failed blast-radius gate: {blast_radius_check}."
        page_action["evidence"]["best_action_rejected"] = {
            "name": best_action["name"],
            "params": best_action["params"],
            "confidence": round(confidence, 3)
        }
        return page_action
        
    selected_action_meta = {
        "blast_radius_services": blast_radius,
        "cost_min": meta.get("cost_min", 0),
        "downtime_min": meta.get("downtime_min", 0)
    }
    
    return {
        "incident_id": query_incident.get("incident_id").split("-")[0],
        "selected_action": best_action["name"],
        "params": best_action["params"],
        "confidence": round(confidence, 3),
        "top_3_neighbors": top_3_neighbors,
        "consensus_score": consensus_score,
        "blast_radius_check": blast_radius_check,
        "selected_action_meta": selected_action_meta,
        "evidence": {
            "reason": f"Expected cost of '{best_action['name']}' ({round(min_expected_cost, 2)}) is lower than paging ({cost_page}).",
            "blast_radius": blast_radius,
            "max_similarity": max_similarity,
            "expected_cost": round(min_expected_cost, 2),
            "prob": round(confidence, 3)
        }
    }
