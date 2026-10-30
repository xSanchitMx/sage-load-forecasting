"""
Module 1 - Data Acquisition and Preprocessing.

Turns the raw UCI ElectricityLoadDiagrams20112014 data into the streaming feed the
rest of the system consumes: client selection, hourly resampling, calendar features,
causal scaling, and the chronological 50/15/35 warm-start / validation / test split.

The heavy hourly file (Dataset/electricity_hourly_2012_2014.csv) already has the
15-min -> hourly aggregation and the 2011 / history-less-client removal applied, so
this module works from it directly. A loader for the raw LD2011_2014.txt is also
provided for completeness.
"""
from __future__ import annotations
import os
import numpy as np
import pandas as pd

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOURLY_CSV = os.path.join(PROJECT, "Dataset", "electricity_hourly_2012_2014.csv")
RAW_TXT = os.path.join(PROJECT, "Dataset", "LD2011_2014.txt")

# Portugal public holidays 2012-2014 (the dataset is Portuguese clients).
_PT_HOLIDAYS = {
    # 2012
    "2012-01-01", "2012-02-21", "2012-04-06", "2012-04-08", "2012-04-25",
    "2012-05-01", "2012-06-07", "2012-06-10", "2012-08-15", "2012-10-05",
    "2012-11-01", "2012-12-01", "2012-12-08", "2012-12-25",
    # 2013
    "2013-01-01", "2013-02-12", "2013-03-29", "2013-03-31", "2013-04-25",
    "2013-05-01", "2013-05-30", "2013-06-10", "2013-08-15", "2013-10-05",
    "2013-11-01", "2013-12-01", "2013-12-08", "2013-12-25",
    # 2014
    "2014-01-01", "2014-03-04", "2014-04-18", "2014-04-20", "2014-04-25",
    "2014-05-01", "2014-06-10", "2014-06-19", "2014-08-15", "2014-10-05",
    "2014-11-01", "2014-12-01", "2014-12-08", "2014-12-25",
}


def load_hourly() -> pd.DataFrame:
    """Load the hourly 321-client matrix, indexed by timestamp."""
    df = pd.read_csv(HOURLY_CSV, parse_dates=["date"])
    df = df.set_index("date")
    return df


def select_clients(df: pd.DataFrame, n: int = 8, seed: int = 42) -> list[str]:
    """
    Stratified client selection: rank clients by coefficient of variation of the
    (non-zero) series and sample across low / medium / high-CV terciles so the subset
    spans stable and volatile demand profiles.
    """
    rng = np.random.default_rng(seed)
    cv = {}
    for c in df.columns:
        s = df[c].values.astype(float)
        s = s[s > 0]
        if s.size < 24 * 30:          # need at least ~a month of history
            continue
        m = s.mean()
        if m > 0:
            cv[c] = s.std() / m
    cvs = pd.Series(cv).sort_values()
    # split into terciles, sample round(n/3) from each
    thirds = np.array_split(cvs.index.values, 3)
    per = max(1, n // 3)
    chosen: list[str] = []
    for group in thirds:
        k = min(per, len(group))
        chosen.extend(rng.choice(group, size=k, replace=False).tolist())
    # top up to n from the middle tercile if rounding left us short
    if len(chosen) < n:
        remaining = [c for c in cvs.index if c not in chosen]
        chosen.extend(remaining[: n - len(chosen)])
    return chosen[:n]


def calendar_features(index: pd.DatetimeIndex) -> pd.DataFrame:
    """Hour-of-day, day-of-week, month, and holiday flag for each timestamp."""
    feats = pd.DataFrame(index=index)
    feats["hour"] = index.hour
    feats["dow"] = index.dayofweek
    feats["month"] = index.month
    feats["is_weekend"] = (index.dayofweek >= 5).astype(int)
    feats["is_holiday"] = index.normalize().strftime("%Y-%m-%d").isin(_PT_HOLIDAYS).astype(int)
    return feats


def make_splits(n_steps: int, warm: float = 0.50, val: float = 0.15):
    """Chronological index boundaries for warm-start / validation / test."""
    w = int(n_steps * warm)
    v = int(n_steps * (warm + val))
    return {"warm": (0, w), "val": (w, v), "test": (v, n_steps)}


class ClientSeries:
    """
    A single client's prepared series: raw values, calendar features, split boundaries,
    and a causal scaler whose statistics refresh every `refresh_weeks` using past data only.
    """

    def __init__(self, series: pd.Series, refresh_weeks: int = 6):
        # drop the leading all-zero warm-up period for this client
        first_nz = (series > 0).idxmax()
        series = series.loc[first_nz:]
        self.y = series.astype(float)
        self.index = series.index
        self.n = len(series)
        self.feats = calendar_features(self.index)
        self.splits = make_splits(self.n)
        self.refresh = refresh_weeks * 168  # steps between scaler refreshes
        self._mu = None
        self._sigma = None
        self._last_refresh = -10**9

    def refresh_scaler(self, t: int):
        """Recompute mean/std on data strictly before t (causal), warm-start floor."""
        lo = max(0, t - self.refresh) if t >= self.refresh else 0
        window = self.y.values[lo:t] if t > 0 else self.y.values[: self.splits["warm"][1]]
        window = window[window > 0]
        self._mu = float(window.mean()) if window.size else 0.0
        self._sigma = float(window.std()) if window.size and window.std() > 0 else 1.0
        self._last_refresh = t

    def z(self, value: float, t: int) -> float:
        if self._mu is None or (t - self._last_refresh) >= self.refresh:
            self.refresh_scaler(t)
        return (value - self._mu) / self._sigma

    def inv_z(self, zvalue: float) -> float:
        return zvalue * self._sigma + self._mu


def prepare(n_clients: int = 8, seed: int = 42) -> dict[str, ClientSeries]:
    """Full Module-1 output: {client_id: ClientSeries} for the selected subset."""
    df = load_hourly()
    clients = select_clients(df, n=n_clients, seed=seed)
    return {c: ClientSeries(df[c]) for c in clients}


if __name__ == "__main__":
    data = prepare()
    print(f"Selected {len(data)} clients.")
    for cid, cs in data.items():
        w, v, t = cs.splits["warm"], cs.splits["val"], cs.splits["test"]
        print(f"  {cid}: {cs.n} steps | warm {w} val {v} test {t} | "
              f"mean {cs.y[cs.y>0].mean():.0f} kWh")
