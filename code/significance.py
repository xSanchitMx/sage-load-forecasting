"""
Significance of accuracy differences between two forecasters on the same hours.

dm_test: Diebold-Mariano (1995) test of equal predictive accuracy for one series, on the
loss differential d_t = |e1_t|^p - |e2_t|^p (p = 1: absolute, p = 2: squared error;
"ape": absolute percentage error). The
variance of mean(d) uses a Newey-West (Bartlett) estimator with `lag` hours (default 24)
to allow for the strong autocorrelation of hourly errors; the Harvey, Leybourne & Newbold
(1997) small-sample correction is applied. Negative statistic = forecaster 1 is better.

compare: runs dm_test for every (client, scenario) pair of two methods, and adds an
across-series summary: how many series favour method 1, how many are significant at 5%
each way, and a two-sided Wilcoxon signed-rank test on the per-series relative loss
differences (mean d / mean loss of method 2), which treats each series as one unit.
"""
from __future__ import annotations
import math
import numpy as np


def _norm_sf(z):
    return 0.5 * math.erfc(z / math.sqrt(2))


def dm_test(y, f1, f2, power=2, lag: int = 24):
    """power 1 / 2: absolute / squared error; "ape": absolute percentage error |e|/y on
    hours with y > 0 (the loss MAPE averages)."""
    y, f1, f2 = (np.asarray(a, float) for a in (y, f1, f2))
    if power == "ape":
        m = y > 1e-6
        y, f1, f2 = np.ones(m.sum()), f1[m] / y[m], f2[m] / y[m]
        power = 1
    d = np.abs(y - f1) ** power - np.abs(y - f2) ** power
    T = len(d)
    dm = d - d.mean()
    gamma0 = dm @ dm / T
    var = gamma0
    for k in range(1, min(lag, T - 1) + 1):
        var += 2 * (1 - k / (lag + 1)) * (dm[k:] @ dm[:-k]) / T
    var = max(var, 1e-12)
    stat = d.mean() / math.sqrt(var / T)
    stat *= math.sqrt((T + 1 - 2 + 0) / T)          # HLN correction for 1-step forecasts
    p = 2 * _norm_sf(abs(stat))
    rel = d.mean() / max(1e-12, float(np.mean(np.abs(y - f2) ** power)))
    return {"stat": float(stat), "p": float(p), "rel_diff": float(rel), "n": T}


def wilcoxon_signed_rank(x):
    """Two-sided Wilcoxon signed-rank test (normal approximation with tie correction)."""
    x = np.asarray([v for v in x if v != 0], float)
    n = len(x)
    if n == 0:
        return {"W": 0.0, "p": 1.0, "n": 0}
    ranks = np.argsort(np.argsort(np.abs(x))) + 1.0
    # average ranks for ties
    a = np.abs(x)
    for v in np.unique(a):
        m = a == v
        if m.sum() > 1:
            ranks[m] = ranks[m].mean()
    w_plus = ranks[x > 0].sum()
    mu = n * (n + 1) / 4
    _, counts = np.unique(a, return_counts=True)
    sd = math.sqrt(n * (n + 1) * (2 * n + 1) / 24 - (counts ** 3 - counts).sum() / 48)
    z = (w_plus - mu) / sd if sd > 0 else 0.0
    return {"W": float(w_plus), "z": float(z), "p": float(2 * _norm_sf(abs(z))), "n": n}


def compare(series, power: int = 2, lag: int = 24, alpha: float = 0.05):
    """series: dict key -> (y, f1, f2). Returns per-series DM results and a summary."""
    per = {k: dm_test(y, f1, f2, power, lag) for k, (y, f1, f2) in series.items()}
    rel = [r["rel_diff"] for r in per.values()]
    summ = {
        "n_series": len(per),
        "favour_1": int(sum(r["stat"] < 0 for r in per.values())),
        "sig_better_1": int(sum(r["stat"] < 0 and r["p"] < alpha for r in per.values())),
        "sig_worse_1": int(sum(r["stat"] > 0 and r["p"] < alpha for r in per.values())),
        "mean_rel_diff": float(np.mean(rel)),
        "wilcoxon": wilcoxon_signed_rank(rel),
    }
    return per, summ
