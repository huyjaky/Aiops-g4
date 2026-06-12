import argparse
import json
import yaml
import os
from pathlib import Path
from dotenv import load_dotenv

from features import extract_features
from retrieval import retrieve_and_vote
from decision import select_action

# Load dotenv to read DATA_DIR
load_dotenv()
DATA_DIR = os.getenv("DATA_DIR", ".")

def resolve_path(path_str: str) -> Path:
    p = Path(path_str)
    if p.is_absolute():
        return p
    # Resolve relative to DATA_DIR
    return Path(DATA_DIR) / p

def decide(incident_path: Path, history_path: Path, actions_path: Path) -> dict:
    # Resolve relative paths
    real_incident_path = resolve_path(str(incident_path))
    real_history_path = resolve_path(str(history_path))
    real_actions_path = resolve_path(str(actions_path))
    
    incident = json.loads(real_incident_path.read_text())
    history = json.loads(real_history_path.read_text())
    actions_catalog = yaml.safe_load(real_actions_path.read_text())
    
    # Layer 1: Feature Extraction
    features = extract_features(incident, history)
    
    # Layer 2: Retrieval and Voting
    retrieval_results = retrieve_and_vote(features, history, actions_catalog)
    
    # Layer 3: Decision Making
    decision = select_action(retrieval_results, actions_catalog, features)
    
    # Ensure incident_id matches basename without extension
    decision["incident_id"] = incident_path.stem
    
    return decision

def main() -> int:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd")
    d = sub.add_parser("decide")
    d.add_argument("--incident", required=True)
    d.add_argument("--history", default="incidents_history.json")
    d.add_argument("--actions", default="actions.yaml")
    args = p.parse_args()
    
    if args.cmd == "decide":
        out = decide(Path(args.incident), Path(args.history), Path(args.actions))
        print(json.dumps(out, indent=2))
        
        # Resolve audit.jsonl path relative to DATA_DIR
        audit_path = resolve_path("audit.jsonl")
        
        # Write to audit.jsonl
        with open(audit_path, "a") as f:
            f.write(json.dumps(out) + "\n")
        return 0
        
    p.print_help()
    return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())
