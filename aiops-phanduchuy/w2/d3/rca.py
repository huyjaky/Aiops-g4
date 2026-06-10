import os
import json
import networkx as nx
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

def rca_pagerank(cluster_services: list[str], graph: nx.DiGraph, alpha: float = 0.85) -> dict[str, float]:
    sub = graph.subgraph(cluster_services).copy()
    if len(sub) == 0:
        return {}
    if len(sub.edges()) == 0:
        return {node: 1.0 / len(sub.nodes()) for node in sub.nodes()}
    try:
        scores = nx.pagerank(sub, alpha=alpha)
    except Exception:
        scores = {node: 1.0 / len(sub.nodes()) for node in sub.nodes()}
    return scores

def rca_combined(cluster: dict, alerts: list[dict], graph: nx.DiGraph) -> list[tuple[str, float]]:
    cluster_services = cluster['services']
    pr_scores = rca_pagerank(cluster_services, graph)
    
    sub = graph.subgraph(cluster_services)
    topo_diffs = {}
    for node in cluster_services:
        in_deg = sub.in_degree(node) if node in sub else 0
        out_deg = sub.out_degree(node) if node in sub else 0
        topo_diffs[node] = in_deg - out_deg
        
    if topo_diffs:
        max_topo = max(topo_diffs.values())
        min_topo = min(topo_diffs.values())
        range_topo = max_topo - min_topo
        if range_topo > 0:
            topo_scores = {svc: (val - min_topo) / range_topo for svc, val in topo_diffs.items()}
        else:
            topo_scores = {svc: 0.5 for svc in cluster_services}
    else:
        topo_scores = {svc: 0.5 for svc in cluster_services}
        
    cluster_alerts = [a for a in alerts if a['id'] in cluster['alert_ids']]
    
    earliest_by_svc = {}
    severity_by_svc = {}
    for a in cluster_alerts:
        svc = a['service']
        ts = a['ts']
        sev = a['severity']
        if svc not in earliest_by_svc or ts < earliest_by_svc[svc]:
            earliest_by_svc[svc] = ts
        if svc not in severity_by_svc or sev == 'crit':
            severity_by_svc[svc] = sev
            
    if not earliest_by_svc:
        return [(s, pr_scores.get(s, 0)) for s in cluster_services]
        
    sorted_by_time = sorted(earliest_by_svc.items(), key=lambda x: x[1])
    n = len(sorted_by_time)
    if n > 1:
        timestamp_score = {svc: 1.0 - i / (n - 1) for i, (svc, _) in enumerate(sorted_by_time)}
    else:
        timestamp_score = {svc: 1.0 for svc, _ in sorted_by_time}
        
    pr_max = max(pr_scores.values()) if pr_scores else 1.0
    combined = []
    for svc in cluster_services:
        pr = pr_scores.get(svc, 0) / pr_max if pr_max > 0 else 0
        topo = topo_scores.get(svc, 0.5)
        graph_score = 0.5 * pr + 0.5 * topo
        
        ts = timestamp_score.get(svc, 0)
        
        sev = severity_by_svc.get(svc, 'warn')
        sev_score = 1.0 if sev == 'crit' else 0.0
        
        score = 0.4 * graph_score + 0.2 * ts + 0.4 * sev_score
        combined.append((svc, score))
        
    combined.sort(key=lambda x: -x[1])
    return combined

def incident_similarity(cluster: dict, history_item: dict) -> float:
    score = 0.0
    if history_item['root_cause_service'] in cluster['services']:
        score += 0.4
    overlap = set(cluster['services']) & set(history_item['services_involved'])
    score += min(0.4, 0.2 * len(overlap))
    if cluster.get('max_severity') == history_item.get('severity'):
        score += 0.2
    return min(score, 1.0)

def top_k_similar(cluster: dict, history: list[dict], k: int = 3) -> list[dict]:
    scored = [(item, incident_similarity(cluster, item)) for item in history]
    scored.sort(key=lambda x: -x[1])
    return [{**item, '_similarity': s} for item, s in scored[:k] if s > 0.2]

def call_llm_rca(cluster: dict, candidates: list, history: list[dict], graph_summary: str) -> dict:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not set.")

    from openai import OpenAI
    base_url = os.environ.get("OPENAI_BASE_URL") or os.environ.get("OPENAI_API_BASE")
    client = OpenAI(api_key=api_key, base_url=base_url)
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    
    similar = top_k_similar(cluster, history, k=3)
    similar_block = '\n'.join(
        f"- {i['id']}: root_cause={i['root_cause_service']} ({i['root_cause_class']}) | "
        f"{i['summary']} | remediation: {i['remediation']}"
        for i in similar
    ) or "(no similar incidents found)"
    
    ranked_block = '\n'.join(
        f"  {idx+1}. {svc}  (score: {score:.2f})"
        for idx, (svc, score) in enumerate(candidates[:5])
    )
    
    RCA_PROMPT_TEMPLATE = """\
You are a senior SRE diagnosing a production incident at GeekShop e-commerce platform.

# Cluster information

Cluster ID: {cluster_id}
Time range: {time_range}
Services with alerts: {services}
Top root-cause candidates (from graph RCA, ranked):
{ranked_candidates}

# Similar past incidents (for reference, retrieved by similarity)

{similar_incidents_block}

# Service graph context

{topology_block}

# Task

Based on the cluster, the ranked candidates, and the similar incidents:

1. Pick the single most likely root_cause service (string from cluster.services)
2. Classify the root_cause_class (one of: connection_pool_exhaustion, slow_query, \
memory_leak, rebalance_storm, deadlock, network_partition, bad_deploy, \
config_push, tls_expiry, ddos, other)
3. Provide confidence (0.0-1.0)
4. Suggest 1-3 actions, ordered by recommended sequence
5. Brief reasoning (2-3 sentences) — why this candidate over others?

Respond in JSON ONLY:
{{
  "root_cause": "...",
  "class": "...",
  "confidence": 0.0,
  "actions": ["...", "..."],
  "reasoning": "...",
  "similar_incidents": ["INC-...", "INC-..."]
}}
"""
    prompt = RCA_PROMPT_TEMPLATE.format(
        cluster_id=cluster['cluster_id'],
        time_range=' to '.join(cluster['time_range']),
        services=', '.join(cluster['services']),
        ranked_candidates=ranked_block,
        similar_incidents_block=similar_block,
        topology_block=graph_summary,
    )
    
    response = client.chat.completions.create(
        model=model,
        messages=[
            {'role': 'system', 'content': 'You are a senior SRE. Respond only in valid JSON.'},
            {'role': 'user', 'content': prompt},
        ],
        temperature=0.2,
        response_format={'type': 'json_object'},
    )
    raw = response.choices[0].message.content
    return json.loads(raw)

def validate_llm_output(parsed: dict, cluster: dict, allowed_classes: set) -> tuple[bool, list[str]]:
    errors = []
    if parsed.get('root_cause') not in cluster['services']:
        errors.append(f"root_cause '{parsed.get('root_cause')}' not in cluster services")
    if parsed.get('class') not in allowed_classes:
        errors.append(f"class '{parsed.get('class')}' not in allowed enum")
    conf = parsed.get('confidence', 0)
    if not isinstance(conf, (int, float)) or not (0 <= conf <= 1):
        errors.append(f"confidence '{conf}' not in [0, 1]")
    actions = parsed.get('actions', [])
    if not isinstance(actions, list) or len(actions) == 0:
        errors.append("actions empty or wrong type")
    return (len(errors) == 0, errors)

def run_rca(cluster: dict, alerts: list[dict], graph: nx.DiGraph, history: list[dict]) -> dict:
    candidates = rca_combined(cluster, alerts, graph)
    if not candidates:
        return {'root_cause': 'unknown', 'confidence': 0.0, 'method': 'no-candidates', 'class': 'other', 'actions': ['Investigate manually'], 'reasoning': 'No candidates generated', 'similar_incidents': []}
        
    top_candidate = candidates[0][0]
    similar = top_k_similar(cluster, history, k=3)
    
    use_llm = os.environ.get("AIOPS_USE_LLM", "true").lower() == "true"
    api_key = os.environ.get("OPENAI_API_KEY")
    
    if api_key and use_llm:
        sub = graph.subgraph(cluster['services'])
        edges_str = '\n'.join(f"  {u} -> {v}" for u, v in sub.edges())
        graph_summary = f"Service dependencies in cluster:\n{edges_str}"
        
        try:
            llm_out = call_llm_rca(cluster, candidates, history, graph_summary)
            valid, errors = validate_llm_output(llm_out, cluster, allowed_classes={
                'connection_pool_exhaustion', 'slow_query', 'memory_leak', 'rebalance_storm',
                'deadlock', 'network_partition', 'bad_deploy', 'config_push', 'tls_expiry',
                'ddos', 'other'
            })
            if not valid:
                return {
                    'cluster_id': cluster['cluster_id'],
                    'graph_top3': [[c[0], float(c[1])] for c in candidates[:3]],
                    'root_cause': top_candidate,
                    'class': 'other',
                    'confidence': float(candidates[0][1]),
                    'actions': ['Investigate manually'],
                    'reasoning': f'LLM output invalid: {errors}',
                    'similar_incidents': [],
                    'method': 'graph-only-fallback'
                }
            
            return {
                'cluster_id': cluster['cluster_id'],
                'graph_top3': [[c[0], float(c[1])] for c in candidates[:3]],
                'root_cause': llm_out['root_cause'],
                'class': llm_out['class'],
                'confidence': float(llm_out['confidence']),
                'actions': llm_out['actions'],
                'reasoning': llm_out['reasoning'],
                'similar_incidents': llm_out.get('similar_incidents', []),
                'method': 'graph+llm'
            }
        except Exception as e:
            return {
                'cluster_id': cluster['cluster_id'],
                'graph_top3': [[c[0], float(c[1])] for c in candidates[:3]],
                'root_cause': top_candidate,
                'class': 'other',
                'confidence': float(candidates[0][1] * 0.5),
                'actions': ['LLM unavailable — investigate manually'],
                'reasoning': f'LLM call failed: {e}',
                'similar_incidents': [],
                'method': 'graph-only-llm-failed'
            }
    else:
        if similar:
            best_match = similar[0]
            rca_class = best_match['root_cause_class']
            remediation_actions = [
                f"Apply remediation from {best_match['id']}: {best_match['remediation']}"
            ]
            
            if best_match['_similarity'] >= 0.8 and best_match['root_cause_service'] in cluster['services']:
                final_root_cause = best_match['root_cause_service']
                reasoning = (
                    f"Determined via graph+retrieval. A highly similar historical incident "
                    f"{best_match['id']} (similarity: {best_match['_similarity']:.2f}) was found. "
                    f"Overriding graph top candidate ({top_candidate}) with historical culprit "
                    f"({final_root_cause}) to avoid terminal noise / victim identification."
                )
            else:
                final_root_cause = top_candidate
                reasoning = (
                    f"Determined via graph traversal (top candidate: {top_candidate} with score {candidates[0][1]:.2f}) "
                    f"and historical incident retrieval. Match found with {best_match['id']} (similarity: {best_match['_similarity']:.2f}) "
                    f"which had root cause {best_match['root_cause_service']} ({rca_class})."
                )
            
            confidence = float(0.6 * candidates[0][1] + 0.4 * best_match['_similarity'])
            similar_ids = [item['id'] for item in similar]
        else:
            final_root_cause = top_candidate
            rca_class = "other"
            remediation_actions = ["Investigate manually"]
            reasoning = f"Determined via graph traversal. Top candidate is {top_candidate} with score {candidates[0][1]:.2f}. No similar incidents found in history."
            confidence = float(candidates[0][1] * 0.5)
            similar_ids = []
            
        return {
            'cluster_id': cluster['cluster_id'],
            'graph_top3': [[c[0], float(c[1])] for c in candidates[:3]],
            'root_cause': final_root_cause,
            'class': rca_class,
            'confidence': confidence,
            'actions': remediation_actions,
            'reasoning': reasoning,
            'similar_incidents': similar_ids,
            'method': 'graph+retrieval'
        }
