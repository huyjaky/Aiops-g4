# /// script
# requires-python = ">=3.9"
# dependencies = [
#     "pandas",
#     "pyarrow",
# ]
# ///

import os
import queue
import threading
import time
import math
from collections import deque
import pandas as pd

# Path configuration
CSV_FILE = "./realKnownCause/machine_temperature_system_failure.csv"
OUTPUT_PARQUET = "features.parquet"

# Thread-safe Queue for Producer-Consumer communication
event_queue = queue.Queue(maxsize=1000)
# Sentinel object to signal the consumer that the stream is finished
SENTINEL = object()

def check_data_exists():
    """Verify that the dataset file exists at the specified path."""
    if not os.path.exists(CSV_FILE):
        raise FileNotFoundError(f"Dataset file not found at: {CSV_FILE}")
    print(f"Dataset verified at: {CSV_FILE}")

def producer_task(csv_path, q):
    """Producer Thread: Reads CSV and emits each row into the queue."""
    print("Producer: Initializing...")
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        print(f"Producer: Error reading CSV file: {e}")
        q.put(SENTINEL)
        return
        
    print(f"Producer: Loaded {len(df)} rows. Starting to push data to queue...")
    
    for idx, row in df.iterrows():
        q.put(row.to_dict())
        # Sleep briefly to simulate streaming
        time.sleep(0.00005)
        
    # Send end of stream signal
    q.put(SENTINEL)
    print("Producer: Finished pushing all data.")

def consumer_task(q, window_size=12):
    """Consumer Thread: Reads from queue, calculates rolling features and rate of change."""
    print("Consumer: Initializing...")
    window = deque(maxlen=window_size)
    processed_records = []
    prev_value = None
    count = 0
    
    while True:
        try:
            event = q.get(timeout=5)
        except queue.Empty:
            print("Consumer: Queue empty timeout. Stopping...")
            break
            
        if event is SENTINEL:
            break
            
        timestamp = event["timestamp"]
        value = float(event["value"])
        
        # Update rolling window
        window.append(value)
        
        # 1. Rolling Mean
        rolling_mean = sum(window) / len(window)
        
        # 2. Rolling Std
        n = len(window)
        if n >= 2:
            variance = sum((x - rolling_mean) ** 2 for x in window) / (n - 1)
            rolling_std = math.sqrt(variance)
        else:
            rolling_std = 0.0
            
        # 3. Rate of Change (percentage change from previous value)
        rate_of_change = 0.0
        if prev_value is not None and prev_value != 0:
            rate_of_change = (value - prev_value) / prev_value
            
        prev_value = value
        
        # Save output record
        processed_records.append({
            "timestamp": timestamp,
            "value": value,
            "rolling_mean": round(rolling_mean, 4),
            "rolling_std": round(rolling_std, 4),
            "rate_of_change": round(rate_of_change, 6)
        })
        
        count += 1
        if count % 3000 == 0:
            print(f"Consumer: Processed {count} records... (Latest: Time: {timestamp} | Value: {value} | Mean: {rolling_mean:.2f} | Std: {rolling_std:.2f})")
            
    print(f"Consumer: Completed processing. Total records: {count}")
    
    # Save features to parquet
    if processed_records:
        df_features = pd.DataFrame(processed_records)
        df_features.to_parquet(OUTPUT_PARQUET, index=False)
        print(f"Consumer: Features successfully saved to: {OUTPUT_PARQUET}")
    else:
        print("Consumer: No records processed to save.")

def main():
    try:
        check_data_exists()
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return

    # Create threads for parallel execution
    prod_thread = threading.Thread(target=producer_task, args=(CSV_FILE, event_queue))
    cons_thread = threading.Thread(target=consumer_task, args=(event_queue, 12))  # 12 points window (1 hour window)
    
    start_time = time.time()
    
    prod_thread.start()
    cons_thread.start()
    
    prod_thread.join()
    cons_thread.join()
    
    print(f"Pipeline completed in {time.time() - start_time:.2f} seconds.")

if __name__ == "__main__":
    main()
