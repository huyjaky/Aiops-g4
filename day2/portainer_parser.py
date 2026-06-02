import os
from drain3 import TemplateMiner
from drain3.template_miner_config import TemplateMinerConfig
from drain3.masking import MaskingInstruction

def parse_portainer_log():
    log_file = "_portainer_logs.txt"
    if not os.path.exists(log_file):
        print(f"File {log_file} not found!")
        return

    config = TemplateMinerConfig()
    config.profiling_enabled = False
    
    # Custom masking rules for Portainer logs
    config.masking_instructions = [
        MaskingInstruction(r"endpoint_id=\d+", "*"),
        MaskingInstruction(r"bind_address=:\d+", "*"),
        MaskingInstruction(r"tcp \d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d+->\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d+", "*"),
        MaskingInstruction(r"Fingerprint [A-Za-z0-9+/=]+", "*"),
        MaskingInstruction(r"error=\".*?\"", "*"),
        MaskingInstruction(r"build_number=\d+", "*"),
        MaskingInstruction(r"go_version=go[\d.]+", "*"),
        MaskingInstruction(r"image_tag=[\w.-]+", "*"),
        MaskingInstruction(r"nodejs_version=v[\d.]+", "*"),
        MaskingInstruction(r"pnpm_version=[\d.]+", "*"),
        MaskingInstruction(r"version=[\d.]+", "*"),
        MaskingInstruction(r"webpack_version=[\d.]+", "*")
    ]
    
    miner = TemplateMiner(config=config)
    
    print("Mining templates for Portainer logs...")
    with open(log_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            # Extract the actual log message (payload)
            # Based on 2 main patterns in _portainer_logs.txt:
            # 1. 2026/05/26 17:15:35 server: <payload>
            # 2. 2026/05/26 05:15PM INF .../file.go:141 > <payload>
            if " > " in line:
                payload = line.split(" > ", 1)[1]
            elif " server: " in line:
                payload = line.split(" server: ", 1)[1]
            else:
                # If it doesn't match any pattern, take the whole line (ignoring datetime if present)
                parts = line.split(maxsplit=2)
                payload = parts[2] if len(parts) > 2 else line
                
            miner.add_log_message(payload)
            
    print(f"\\n--- LOG PARSING RESULTS ---")
    print(f"Total templates found: {len(miner.drain.clusters)}")
    print("\\nTemplate List:")
    
    # Sort clusters by size descending
    sorted_clusters = sorted(miner.drain.clusters, key=lambda it: it.size, reverse=True)
    for cluster in sorted_clusters:
        print(f"[{cluster.size:2} times] {cluster.get_template()}")

if __name__ == "__main__":
    parse_portainer_log()
