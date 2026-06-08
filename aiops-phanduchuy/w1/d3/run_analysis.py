import json
import math
import os
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from statsmodels.tsa.seasonal import STL

# 1. Load Data
# Using relative paths from the prompt
csv_path = "../raw_data/realKnownCause/ambient_temperature_system_failure.csv"
labels_path = "../raw_data/realKnownCause/combined_labels.json"

if not os.path.exists(csv_path) or not os.path.exists(labels_path):
    print(f"Warning: Data or labels not found at paths:\n  CSV: {csv_path}\n  Labels: {labels_path}")
    print("Please ensure these paths are correct relative to your execution directory.")
    # Exit gracefully if files are missing in this environment
    exit(1)

df = pd.read_csv(csv_path)
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

# 2. Feature Engineering
df['rolling_mean'] = df['value'].rolling(window=24).mean()
df['rolling_std'] = df['value'].rolling(window=24).std()
df['hour'] = df['timestamp'].dt.hour
df['dayofweek'] = df['timestamp'].dt.dayofweek
df['lag_1'] = df['value'].shift(1)
df['diff_1'] = df['value'].diff(1)

# Handle NaNs created by rolling and shift operations
df_features = df[['value', 'rolling_mean', 'rolling_std', 'hour', 'dayofweek', 'lag_1', 'diff_1']].bfill().fillna(0)

# Load ground truth labels
with open(labels_path, 'r') as f:
    labels_data = json.load(f)

# Load ground truth/label anomaly centers
anomaly_key = "realKnownCause/ambient_temperature_system_failure.csv"
anomaly_centers = labels_data[anomaly_key]

# Map anomaly windows of 360 hours centered around each anomaly timestamp (180 hours on each side)
HOURS = 180
df['label'] = 0
window_delta = pd.Timedelta(hours=HOURS)
for center in anomaly_centers:
    center_dt = pd.to_datetime(center)
    start_dt = center_dt - window_delta
    end_dt = center_dt + window_delta
    df.loc[(df['timestamp'] >= start_dt) & (df['timestamp'] <= end_dt), 'label'] = 1


# 3. Detector 1: Statistical Method (STL + 3-sigma)
# Hourly granularity -> 24 points per day for STL seasonal period
print("Running STL decomposition...")
stl = STL(df['value'], period=24, robust=True)
stl_result = stl.fit()
resid = stl_result.resid

mean_resid = resid.mean()
std_resid = resid.std()
# Flag values deviating by more than 3 standard deviations
preds_1 = ((resid - mean_resid).abs() > 3 * std_resid).astype(int)


# 4. Detector 2: Machine Learning Method (Isolation Forest)
print("Running Isolation Forest...")
best_cont = 0.012  # Estimated anomaly rate
clf = IsolationForest(contamination=best_cont, random_state=42)
# Fit and predict (-1 for anomaly, 1 for normal)
preds_raw = clf.fit_predict(df_features)
preds_2 = (preds_raw == -1).astype(int)


# 5. Plotting Function
def plot_metric_acf(
    timestamps_1,
    values_1,
    preds_1,  # Data for the top plot (STL)
    timestamps_2,
    values_2,
    preds_2,  # Data for the bottom plot (Isolation Forest)
    anomaly_centers,
    best_cont,
    metric_label="Ambient Temperature",
    window_hours=HOURS,
):
    fig, axes = plt.subplots(2, 1, figsize=(16, 12), sharex=True)

    t1, v1, p1 = np.array(timestamps_1), np.array(values_1), np.array(preds_1)
    t2, v2, p2 = np.array(timestamps_2), np.array(values_2), np.array(preds_2)

    mask_1 = p1 == 1
    anom_time_1, anom_val_1 = t1[mask_1], v1[mask_1]

    mask_2 = p2 == 1
    anom_time_2, anom_val_2 = t2[mask_2], v2[mask_2]

    window_delta = pd.Timedelta(hours=window_hours)

    # 1. Subplot 1: Detector 1 (STL + 3sigma)
    axes[0].plot(t1, v1, color="royalblue", alpha=0.5, label=metric_label)

    axes[0].scatter(
        anom_time_1,
        anom_val_1,
        color="red",
        s=20,
        zorder=5,
        label="Predicted Anomalies (STL + 3σ)",
    )

    # Overlay yellow ground truth windows
    first_window = True
    for center in anomaly_centers:
        center_dt = pd.to_datetime(center)
        axes[0].axvspan(
            center_dt - window_delta,
            center_dt + window_delta,
            color="yellow",
            alpha=0.25,
            label="NAB Ground Truth Window" if first_window else "",
        )
        first_window = False

    axes[0].set_title(
        "Detector 1: Statistical Method (STL + 3σ)", fontsize=13, fontweight="bold"
    )
    axes[0].set_ylabel("Value")
    axes[0].legend(loc="upper right")
    axes[0].grid(True, linestyle="--", alpha=0.5)

    # 2. Subplot 2: Detector 2 (Isolation Forest)
    axes[1].plot(t2, v2, color="royalblue", alpha=0.5, label=metric_label)

    axes[1].scatter(
        anom_time_2,
        anom_val_2,
        color="darkorange",
        s=20,
        zorder=5,
        label="Predicted Anomalies (Isolation Forest)",
    )

    # Overlay yellow ground truth windows
    first_window = True
    for center in anomaly_centers:
        center_dt = pd.to_datetime(center)
        axes[1].axvspan(
            center_dt - window_delta,
            center_dt + window_delta,
            color="yellow",
            alpha=0.25,
            label="NAB Ground Truth Window" if first_window else "",
        )
        first_window = False

    axes[1].set_title(
        f"Detector 2: Machine Learning Method (Isolation Forest, Contamination={best_cont})",
        fontsize=13,
        fontweight="bold",
    )
    axes[1].set_ylabel("Value")
    axes[1].set_xlabel("Timestamp")
    axes[1].legend(loc="upper right")
    axes[1].grid(True, linestyle="--", alpha=0.5)

    plt.tight_layout()
    plt.show()


# 6. Execute Plotting
print("Generating visualization...")
plot_metric_acf(
    timestamps_1=df['timestamp'],
    values_1=df['value'],
    preds_1=preds_1,
    timestamps_2=df['timestamp'],
    values_2=df['value'],
    preds_2=preds_2,
    anomaly_centers=anomaly_centers,
    best_cont=best_cont,
    metric_label="Ambient Temperature"
)
