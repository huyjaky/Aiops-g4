import sys
import os
import pandas as pd
from datetime import datetime
from drain3 import TemplateMiner
from drain3.template_miner_config import TemplateMinerConfig

def parse_line(line, dataset_type):
    parts = line.strip().split()
    if not parts:
        return None, None
    try:
        if dataset_type == "BGL":
            # BGL format: Label Timestamp Date Node Time Node Type Component Level Payload
            # - 1117838570 ...
            timestamp = datetime.fromtimestamp(int(parts[1]))
            payload = " ".join(parts[9:])
            return timestamp, payload
        elif dataset_type == "HDFS":
            # HDFS format: Date Time Pid Level Component Payload
            # 081109 203615 ...
            date_time_str = parts[0] + " " + parts[1]
            timestamp = datetime.strptime(date_time_str, "%y%m%d %H%M%S")
            payload = " ".join(parts[5:])
            return timestamp, payload
    except Exception as e:
        pass
    return None, None

def analyze_log(filepath):
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return

    dataset_type = "BGL" if "BGL" in filepath else "HDFS" if "HDFS" in filepath else None
    if not dataset_type:
        print("Cannot determine dataset type from filename (must contain 'BGL' or 'HDFS').")
        return

    print(f"=== Log Analyzer ===")
    print(f"File: {filepath} | Type: {dataset_type}")
    print("Mining templates...")
    
    config = TemplateMinerConfig()
    config.load("drain3.ini") if os.path.exists("drain3.ini") else None
    config.profiling_enabled = False
    miner = TemplateMiner(config=config)
    
    data = []
    total_lines = 0
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            total_lines += 1
            timestamp, payload = parse_line(line, dataset_type)
            if timestamp and payload:
                result = miner.add_log_message(payload)
                data.append({
                    "Timestamp": timestamp,
                    "EventTemplate": result["template_mined"]
                })
                
    df = pd.DataFrame(data)
    df.set_index("Timestamp", inplace=True)
    df.sort_index(inplace=True)
    
    unique_templates = len(miner.drain.clusters)
    print(f"\\n[1] General Statistics:")
    print(f"Total lines: {total_lines}")
    print(f"Unique templates: {unique_templates}")
    
    # Top-5 template
    template_counts = df["EventTemplate"].value_counts()
    print(f"\\n[2] Top-5 Templates:")
    for t, count in template_counts.head(5).items():
        pct = (count / total_lines) * 100
        print(f"  - [{count} times | {pct:.1f}%] {t}")
        
    # Anomaly in the last hour
    print(f"\\n[3] Anomaly Detection (Last 1 hour):")
    # Resample by 1 Hour
    df_1h = df.groupby([pd.Grouper(freq='1h'), 'EventTemplate']).size().unstack(fill_value=0)
    
    if len(df_1h) < 2:
        print("  Not enough data to compare the last hour with the past (requires > 1 hour).")
    else:
        # Last hour
        last_hour = df_1h.index[-1]
        last_hour_data = df_1h.loc[last_hour]
        
        # Past data
        past_data = df_1h.loc[:df_1h.index[-2]]
        
        # Calculate Mean and Std of past data
        past_mean = past_data.mean()
        past_std = past_data.std().fillna(0)
        
        # Spike threshold: > Mean + 3 * Std
        threshold = past_mean + 3 * past_std
        
        spikes = []
        new_templates = []
        
        for template in df_1h.columns:
            current_count = last_hour_data[template]
            
            # Check new template (never seen before)
            if past_data[template].sum() == 0 and current_count > 0:
                new_templates.append((template, current_count))
            # Check spike
            elif current_count > threshold[template] and current_count > past_mean[template] * 2: 
                # Condition > mean * 2 added to avoid noise when mean = 0, std = 0
                spikes.append((template, current_count, past_mean[template]))
                
        print(f"  Time frame evaluated (Last hour): {last_hour}")
        print(f"  * Spiked templates (> Mean + 3 Std):")
        if not spikes:
            print("    None.")
        for t, c, m in spikes:
            print(f"    - {t} (Count: {c}, Avg: {m:.1f})")
            
        print(f"  * New Templates (Never seen before):")
        if not new_templates:
            print("    None.")
        for t, c in new_templates:
            print(f"    - {t} (Count: {c})")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python log_analyzer.py <logfile>")
        sys.exit(1)
    analyze_log(sys.argv[1])
