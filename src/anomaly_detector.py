# src/anomaly_detector.py
import pandas as pd
from sklearn.ensemble import IsolationForest
from datetime import datetime
from typing import List, Tuple

def aggregate_counts_by_minute(timestamps: List[datetime]) -> pd.DataFrame:
    """
    Given a list of datetimes, bucket them by minute and count occurrences.
    Returns a DataFrame with columns [“minute” (datetime), “count” (int)].
    """
    df = pd.DataFrame({"timestamp": timestamps})
    df["minute"] = df["timestamp"].dt.floor("min")
    counts = df.groupby("minute").size().rename("count").reset_index()
    return counts

def detect_anomalies(counts_df: pd.DataFrame,
                     contamination: float = 0.1
                    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Fit an IsolationForest on the count series.
    Returns (anomalies_df, full_counts_df_with_flags).
    An anomaly is where model.predict == -1.
    """
    model = IsolationForest(contamination=contamination, random_state=42)
    counts_df = counts_df.copy()
    counts_df["anomaly_flag"] = model.fit_predict(counts_df[["count"]])
    anomalies = counts_df[counts_df["anomaly_flag"] == -1]
    return anomalies, counts_df
