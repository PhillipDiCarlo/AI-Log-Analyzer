import pandas as pd
from datetime import datetime, timedelta
from src.anomaly_detector import aggregate_counts_by_minute, detect_anomalies

def test_aggregate_counts_by_minute():
    times = [
        datetime(2025,1,1,0,0,1),
        datetime(2025,1,1,0,0,30),
        datetime(2025,1,1,0,1,0)
    ]
    df = aggregate_counts_by_minute(times)
    # two in minute 0, one in minute 1
    assert set(df['count']) == {2,1}
    assert len(df) == 2

def test_detect_anomalies_constant():
    # constant series => no anomalies if contamination low
    minutes = [datetime(2025,1,1,0,i,0) for i in range(10)]
    counts = pd.DataFrame({
        'minute': minutes,
        'count': [5]*10
    })
    anoms, flagged = detect_anomalies(counts, contamination=0.1)
    assert anoms.empty
    # flagged should label all as normal (1)
    assert set(flagged['anomaly_flag']) == {1}
