import json
import random
from collections import deque
from datetime import datetime, timedelta

def generate_mock_data(num_records=50):
    """Generate a mock metric stream data simulating a message queue."""
    queue = []
    base_time = datetime.now()
    base_value = 100.0
    for i in range(num_records):
        # Simulate some random fluctuation in the metric
        base_value += random.uniform(-2.0, 2.0)
        record = {
            "timestamp": (base_time + timedelta(seconds=i)).isoformat(),
            "metric_value": round(base_value, 4)
        }
        queue.append(record)
    return queue

def process_stream(queue, window_size=5):
    """
    Consumer function that reads from the queue, 
    calculates rolling mean and rate of change,
    and returns the extracted features.
    """
    features = []
    window = deque(maxlen=window_size)
    prev_value = None
    
    # Mock consuming messages from a queue
    for item in queue:
        current_value = item["metric_value"]
        window.append(current_value)
        
        # Calculate Rolling Mean
        rolling_mean = sum(window) / len(window)
        
        # Calculate Rate of Change (pct change compared to the previous value)
        rate_of_change = 0.0
        if prev_value is not None and prev_value != 0:
            rate_of_change = (current_value - prev_value) / prev_value
            
        prev_value = current_value
        
        feature_record = {
            "timestamp": item["timestamp"],
            "metric_value": current_value,
            "rolling_mean_5s": round(rolling_mean, 4),
            "rate_of_change": round(rate_of_change, 6)
        }
        features.append(feature_record)
        print(f"[{item['timestamp']}] Value: {current_value:.4f} | Rolling Mean: {rolling_mean:.4f} | RoC: {rate_of_change:.6f}")
        
    return features

def main():
    
    mock_queue = generate_mock_data(150)
    print(f"Generated mock queue with {len(mock_queue)} records.\n")
    
    features = process_stream(mock_queue, window_size=5)
    
    # 3. Output features to features.json
    output_file = "features.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(features, f, indent=4)
        
    print(f"\nPipeline completed successfully. Extracted features saved to {output_file}")

if __name__ == "__main__":
    main()
