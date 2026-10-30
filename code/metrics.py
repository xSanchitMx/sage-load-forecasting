"""
Module 5 metrics - accuracy, regret, and post-drift recovery time.
All operate on aligned numpy arrays of ground-truth and forecast over the test block.
"""
from __future__ import annotations
import numpy as np


def mae(y, yhat):
    return float(np.mean(np.abs(y - yhat)))


def rmse(y, yhat):
    return float(np.sqrt(np.mean((y - yhat) ** 2)))


def cv_rmse(y, yhat, eps=1e-6):
    """RMSE as a percentage of the mean load (ASHRAE Guideline 14 CV-RMSE).
    Scale-free, so it is comparable across clients of different magnitudes."""
    mean_y = np.mean(y)
    if abs(mean_y) < eps:
        return float("nan")
    return float(rmse(y, yhat) / mean_y * 100)


def mape(y, yhat, eps=1e-6):
    mask = np.abs(y) > eps
    return float(np.mean(np.abs((y[mask] - yhat[mask]) / y[mask])) * 100)


def directional_accuracy(y, yhat):
    """% of steps where the sign of the change y_t - y_{t-1} is predicted correctly."""
    if len(y) < 2:
        return float("nan")
    true_dir = np.sign(np.diff(y))
    pred_dir = np.sign(yhat[1:] - y[:-1])   # predicted change vs last observed
    valid = true_dir != 0
    if valid.sum() == 0:
        return float("nan")
    return float(np.mean(true_dir[valid] == pred_dir[valid]) * 100)


def cumulative_regret(y, yhat, per_model_yhat):
    """
    Regret vs the best single model in hindsight.
    per_model_yhat: dict name -> forecast array (same length as y).
    Returns total regret = sum |e_system| - sum |e_best_single|.
    """
    sys_loss = np.abs(y - yhat).sum()
    best_loss = min(np.abs(y - fc).sum() for fc in per_model_yhat.values())
    return float(sys_loss - best_loss)


def rolling_mae(err_abs, window=168):
    """Trailing rolling mean of absolute error."""
    s = np.cumsum(np.insert(err_abs, 0, 0.0))
    out = np.full(len(err_abs), np.nan)
    for t in range(len(err_abs)):
        lo = max(0, t - window + 1)
        out[t] = (s[t + 1] - s[lo]) / (t - lo + 1)
    return out


def recovery_times(y, yhat, drift_points, window=24, base_span=168, tol=0.10,
                   sustain=12, cap=168 * 4):
    """
    For each drift point t0, recovery time = first tau >= 0 from which the `window`-hour
    rolling MAE stays within tol of the pre-drift baseline for `sustain` consecutive hours.
    The baseline is the median rolling MAE over the `base_span` hours ending one window
    before t0, so the error build-up that triggered the detector is not part of it.
    A short window is used so the rolling MAE can actually move within hours.
    Returns (list_of_recovery_hours, non_recovery_count).
    """
    err = np.abs(y - yhat)
    rmae = rolling_mae(err, window)
    recoveries = []
    non_recovered = 0
    for t0 in drift_points:
        if t0 - base_span - window < 0 or t0 >= len(y):
            continue
        pre = np.nanmedian(rmae[t0 - base_span - window:t0 - window])
        if not np.isfinite(pre) or pre <= 0:
            continue
        thresh = pre * (1 + tol)
        run = 0
        rec = None
        for tau in range(0, min(cap, len(y) - t0)):
            if rmae[t0 + tau] <= thresh:
                run += 1
                if run >= sustain:
                    rec = tau - sustain + 1
                    break
            else:
                run = 0
        if rec is None:
            non_recovered += 1
        else:
            recoveries.append(rec)
    return recoveries, non_recovered


def summarize(y, yhat, per_model_yhat=None, drift_points=None):
    out = {
        "MAE": mae(y, yhat),
        "RMSE": rmse(y, yhat),
        "CV_RMSE": cv_rmse(y, yhat),
        "MAPE": mape(y, yhat),
        "DirAcc": directional_accuracy(y, yhat),
    }
    if per_model_yhat:
        out["Regret"] = cumulative_regret(y, yhat, per_model_yhat)
    if drift_points is not None and len(drift_points):
        recs, nonrec = recovery_times(y, yhat, drift_points)
        out["RecoveryMedian"] = float(np.median(recs)) if recs else float("nan")
        out["NonRecoveryRate"] = nonrec / max(1, len(drift_points))
    return out


def _changes(seq):
    """Number of positions where a sequence differs from its previous element."""
    return int(sum(1 for a, b in zip(seq, seq[1:]) if a != b))


def operational_stats(diag, n_steps):
    """
    Switching, retraining and compute statistics for one controller run, from the
    per-step diagnostics (and diag["ops"] timing) recorded by AdaptiveController.run.

      leader_switches   - times the lowest-EWMA-error model changed
      blendset_changes  - times the set of models in the served top-k blend changed
      arm_switches      - times the bandit flipped between follow_blend / force_best
      drift_events      - drift alarms (each one triggers a targeted retrain)
      refits_*          - individual model refits, by cause (drift / scheduled)
      ms_per_step       - mean wall-clock per hourly step, total and by phase
      control_share     - fraction of wall-clock spent in the controller's own logic
                          (weighting, bandit, error tracking, drift test), i.e. the
                          overhead on top of simply running the model pool
    """
    weeks = n_steps / 168.0
    best = [b for b in diag["best"] if b is not None]
    blendsets = [tuple(sorted(w)) for w in diag["weights"]]
    ops = diag["ops"]
    sec = ops["sec"]
    total = sum(sec.values())
    ref_d = sum(ops["refits"]["drift"].values())
    ref_s = sum(ops["refits"]["scheduled"].values())
    ref_f = sum(ops["refits"].get("followup", {}).values())
    out = {
        "leader_switches": _changes(best),
        "blendset_changes": _changes(blendsets),
        "arm_switches": _changes(diag["arm"]),
        "mean_blend_size": float(np.mean([len(w) for w in diag["weights"]])),
        "drift_events": int(sum(diag["drift"])),
        "refits_drift": int(ref_d),
        "refits_scheduled": int(ref_s),
        "refits_followup": int(ref_f),
        "refits_total": int(ref_d + ref_s + ref_f),
        "refits_by_model": {n: sum(c.get(n, 0) for c in ops["refits"].values())
                            for n in ops["refits"]["drift"]},
        "total_sec": float(total),
        "ms_per_step": float(total / max(1, n_steps) * 1000),
        "ms_per_step_by_phase": {k: float(v / max(1, n_steps) * 1000) for k, v in sec.items()},
        "control_share": float(sec["control"] / total) if total else float("nan"),
        "model_sec": {k: float(v) for k, v in ops["model_sec"].items()},
        "combiner_resets": int(ops.get("combiner_resets", 0)),
    }
    for k in ("leader_switches", "blendset_changes", "arm_switches", "drift_events",
              "refits_total"):
        out[k + "_per_week"] = float(out[k] / weeks) if weeks else float("nan")
    return out


def shift_metrics(y, yhat, alarms, events, windows=(168, 672), detect_h=336,
                  rec_window=24, base_span=336, tol=0.25, sustain=24, cap=672):
    """
    Step 4: behaviour around known injected shifts. `events` and `alarms` are indices
    into y (block-relative).
      detection delay   first alarm in [e, e + detect_h) minus e; missed if none
      false alarms      alarms outside every [e, e + detect_h) window, per week of the rest
      post-shift error  MAE and MAPE over [e, e + w) for each w in `windows`, and the MAE
                        ratio to the [e - w, e) pre-shift window (> 1 = worse after)
      recovery          relative error |e_t| / y_t (scale-free, so a level shift does not
                        count as permanent damage) on a `rec_window`-hour rolling mean;
                        hours until it stays within (1 + tol) x its median over the
                        `base_span` hours before the event for `sustain` hours; capped
    Returns per-event rows and a summary.
    """
    y = np.asarray(y, float); yhat = np.asarray(yhat, float)
    floor = 0.1 * float(np.mean(y))
    rel = np.abs(y - yhat) / np.maximum(y, floor)
    rrel = rolling_mae(rel, rec_window)
    alarms = np.asarray(sorted(alarms), int)
    rows = []
    covered = np.zeros(len(y), bool)
    for e in events:
        covered[e:e + detect_h] = True
        hit = alarms[(alarms >= e) & (alarms < e + detect_h)]
        row = {"event": int(e), "delay": int(hit[0] - e) if hit.size else None}
        for w in windows:
            post = slice(e, min(len(y), e + w)); pre = slice(max(0, e - w), e)
            row[f"MAE_{w}"] = mae(y[post], yhat[post])
            row[f"MAPE_{w}"] = mape(y[post], yhat[post])
            row[f"ratio_{w}"] = row[f"MAE_{w}"] / max(1e-9, mae(y[pre], yhat[pre]))
        base = np.nanmedian(rrel[max(0, e - base_span):e])
        rec, run = None, 0
        for tau in range(0, min(cap, len(y) - e)):
            if rrel[e + tau] <= base * (1 + tol):
                run += 1
                if run >= sustain:
                    rec = tau - sustain + 1
                    break
            else:
                run = 0
        row["recovery"] = rec
        rows.append(row)
    n_out = int((~covered).sum())
    false = int(sum(1 for a in alarms if not covered[a]))
    delays = [r["delay"] for r in rows if r["delay"] is not None]
    recs = [r["recovery"] for r in rows if r["recovery"] is not None]
    summ = {"n_events": len(rows),
            "detected": len(delays),
            "delay_median": float(np.median(delays)) if delays else float("nan"),
            "false_alarms_per_week": false / max(1e-9, n_out / 168),
            "recovery_median": float(np.median(recs)) if recs else float("nan"),
            "not_recovered": len(rows) - len(recs)}
    for w in windows:
        for k in ("MAE", "MAPE", "ratio"):
            summ[f"{k}_{w}"] = float(np.mean([r[f"{k}_{w}"] for r in rows])) if rows else float("nan")
    return rows, summ
