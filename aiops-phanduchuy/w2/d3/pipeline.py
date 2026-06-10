import json
from pathlib import Path
from correlate import correlate, build_graph
from rca import run_rca, top_k_similar

# Load once at module level (cached)
dataset_dir = Path(__file__).parent / "dataset"
GRAPH = build_graph(str(dataset_dir / "services.json"))
HISTORY = json.loads((dataset_dir / "incidents_history.json").read_text())['incidents']

def process_batch(alerts: list[dict]) -> dict:
    """
    Full pipeline. Trả về dict matching IncidentResponse schema.
    """
    # L1: Correlate
    # Note: we use gap_sec=120 and max_hop=2 as defaults
    clusters = correlate(alerts, GRAPH, gap_sec=120, max_hop=2)
    if not clusters:
        return {
            'clusters': [],
            'root_cause': {
                'service': 'unknown',
                'confidence': 0.0,
                'reasoning': 'No clusters found'
            },
            'recommended_actions': [],
            'similar_incidents': [],
        }
    
    # Pick largest cluster as "primary incident"
    primary = max(clusters, key=lambda c: c['alert_count'])
    
    # L2 + L3: RCA + LLM enrichment cho primary cluster
    rca_result = run_rca(primary, alerts, GRAPH, HISTORY)
    
    # Retrieve similar incidents with full details
    similar_details = []
    similar_incidents_list = rca_result.get('similar_incidents', [])
    for inc_id in similar_incidents_list[:3]:
        # Find in HISTORY
        hist_item = next((item for item in HISTORY if item['id'] == inc_id), None)
        if hist_item:
            # Recalculate similarity if needed, or use a default
            # Since rca_result doesn't carry the similarity scores directly for similar_incidents,
            # we can look up the top similar ones again.
            similar_retrieved = top_k_similar(primary, HISTORY, k=5)
            match = next((item for item in similar_retrieved if item['id'] == inc_id), None)
            sim_score = match['_similarity'] if match else 0.7
            summary_text = hist_item.get('summary', 'No summary available')
        else:
            sim_score = 0.7
            summary_text = 'No summary available'
            
        similar_details.append({
            'id': inc_id,
            'similarity': float(sim_score),
            'summary': summary_text
        })

    return {
        'clusters': [
            {
                'cluster_id': c['cluster_id'],
                'alert_count': c['alert_count'],
                'services': c['services'],
                'time_range': c['time_range'],
            } for c in clusters
        ],
        'root_cause': {
            'service': rca_result.get('root_cause') or 'unknown',
            'confidence': float(rca_result.get('confidence', 0.0)),
            'reasoning': rca_result.get('reasoning', ''),
        },
        'recommended_actions': rca_result.get('actions', []),
        'similar_incidents': similar_details,
    }
