import pytest
from correlate import fingerprint, session_groups

def test_fingerprint_excludes_timestamp():
    a = {'service': 'payment-svc', 'metric': 'latency', 'severity': 'crit', 'ts': '2026-06-12T09:42:01Z', 'value': 1840}
    b = {'service': 'payment-svc', 'metric': 'latency', 'severity': 'crit', 'ts': '2026-06-12T09:42:30Z', 'value': 1900}
    assert fingerprint(a) == fingerprint(b)

def test_session_split_on_gap():
    alerts = [
        {'id': '1', 'ts': '2026-06-12T09:42:00Z', 'service': 'a', 'metric': 'm', 'severity': 'warn', 'value': 1, 'threshold': 0},
        {'id': '2', 'ts': '2026-06-12T09:42:30Z', 'service': 'a', 'metric': 'm', 'severity': 'warn', 'value': 1, 'threshold': 0},
        {'id': '3', 'ts': '2026-06-12T09:50:00Z', 'service': 'a', 'metric': 'm', 'severity': 'warn', 'value': 1, 'threshold': 0},
    ]
    groups = session_groups(alerts, gap_sec=120)
    assert len(groups) == 2  # 1 + 2 split by 7.5 min gap
