import json
import networkx as nx
from collections import defaultdict
from datetime import datetime

def build_graph(services_json_path: str) -> nx.DiGraph:
    g = nx.DiGraph()
    with open(services_json_path) as f:
        data = json.loads(f.read())
    for svc in data['services']:
        g.add_node(svc['name'], **{k: v for k, v in svc.items() if k != 'name'})
    for store in data['stores']:
        g.add_node(store['name'], **{k: v for k, v in store.items() if k != 'name'})
    for edge in data['edges']:
        g.add_edge(edge['from'], edge['to'], type=edge['type'])
    return g

def fingerprint(alert: dict) -> str:
    return f"{alert['service']}|{alert['metric']}|{alert['severity']}"

def session_groups(alerts: list[dict], gap_sec: int = 120) -> list[list[dict]]:
    if not alerts:
        return []
    sorted_alerts = sorted(alerts, key=lambda a: a['ts'])
    groups = [[sorted_alerts[0]]]
    for alert in sorted_alerts[1:]:
        ts = datetime.fromisoformat(alert['ts'].replace('Z', '+00:00'))
        last_ts = datetime.fromisoformat(groups[-1][-1]['ts'].replace('Z', '+00:00'))
        if (ts - last_ts).total_seconds() <= gap_sec:
            groups[-1].append(alert)
        else:
            groups.append([alert])
    return groups

def topology_group(alerts: list[dict], graph: nx.DiGraph, max_hop: int = 2) -> list[list[dict]]:
    if not alerts:
        return []
    undirected = graph.to_undirected()
    by_service = defaultdict(list)
    for a in alerts:
        by_service[a['service']].append(a)
    services_with_alerts = list(by_service.keys())
    
    parent = {s: s for s in services_with_alerts}
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    def union(x, y):
        parent[find(x)] = find(y)
        
    for i, s1 in enumerate(services_with_alerts):
        for s2 in services_with_alerts[i+1:]:
            try:
                if s1 in undirected and s2 in undirected:
                    dist = nx.shortest_path_length(undirected, s1, s2)
                    if dist <= max_hop:
                        union(s1, s2)
            except (nx.NetworkXNoPath, nx.NodeNotFound):
                continue
                
    groups_dict = defaultdict(list)
    for s in services_with_alerts:
        groups_dict[find(s)].extend(by_service[s])
    return list(groups_dict.values())

def get_max_severity(severities: list[str]) -> str:
    severity_order = {'info': 1, 'warn': 2, 'crit': 3, 'critical': 3}
    return max(severities, key=lambda s: severity_order.get(s.lower(), 0))

def correlate(alerts: list[dict], graph: nx.DiGraph, gap_sec: int = 120, max_hop: int = 2) -> list[dict]:
    sessions = session_groups(alerts, gap_sec=gap_sec)
    all_clusters = []
    for session_idx, session_alerts in enumerate(sessions):
        topo_groups = topology_group(session_alerts, graph, max_hop=max_hop)
        for group_idx, group in enumerate(topo_groups):
            all_clusters.append({
                'cluster_id': f'c-{session_idx:03d}-{group_idx:03d}',
                'alert_count': len(group),
                'services': sorted(set(a['service'] for a in group)),
                'alert_ids': [a['id'] for a in group],
                'time_range': [min(a['ts'] for a in group), max(a['ts'] for a in group)],
                'max_severity': get_max_severity([a['severity'] for a in group]),
                'fingerprints': sorted(list(set(fingerprint(a) for a in group)))
            })
    return all_clusters
