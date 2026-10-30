"""
Generate the Results & Discussion figures for the paper from the saved result files.

Figures 1-5 read only the JSON outputs (instant). Figure 6 needs per-model validation
metrics and is produced by make_val_vs_test.py.

Palette: Okabe-Ito (colorblind-safe by construction). Method -> colour is consistent
across every figure:  adaptive = blue (hero), equal-weight = orange, val-best = purple.
"""
from __future__ import annotations
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))   # code/: core modules
import os, json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import metrics as M

PROJECT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FIGDIR = os.path.join(PROJECT, "paper")

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 11, "axes.titlesize": 12.5, "axes.labelsize": 11,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.alpha": 0.22, "grid.linewidth": 0.6,
    "figure.dpi": 150, "savefig.dpi": 150, "savefig.bbox": "tight",
    "legend.frameon": False,
})

# Okabe-Ito
C_HERO = "#0072B2"   # adaptive controller (blue)
C_EQ   = "#E69F00"   # equal-weight ensemble (orange)
C_VAL  = "#CC79A7"   # validation-best single (purple)
C_NEU  = "#7a7a7a"   # neutral / actual / best-single line (grey)
C_DRIFT = "#D55E00"  # drift markers (vermillion)
C_BAR  = "#b8c2cb"   # non-highlighted bars

baseline = json.load(open(os.path.join(PROJECT, "code", "results/baselines/static_baselines.json")))
ctrl = json.load(open(os.path.join(PROJECT, "code", "results/initial_controller/initial_controller.json")))
CLIENTS = [c for c in ctrl if not c.startswith("_")]


def _mean(d, method, metric):
    return float(np.mean([d[c][method][metric] for c in d if method in d[c]]))


def label_bars_h(ax, bars, vals, fmt="{:.2f}"):
    for b, v in zip(bars, vals):
        ax.text(b.get_width() + ax.get_xlim()[1] * 0.01, b.get_y() + b.get_height() / 2,
                fmt.format(v), va="center", ha="left", fontsize=9.5, color="#333")


# ---------- Figure 1: ranked mean MAPE by method ----------
def fig1():
    rows = [
        ("Seasonal-naive",        _mean(baseline, "single:seasonal_naive", "MAPE"), C_BAR),
        ("Holt-Winters",          _mean(baseline, "single:holt_winters", "MAPE"), C_BAR),
        ("SARIMA",                _mean(baseline, "single:sarima", "MAPE"), C_BAR),
        ("LightGBM",              _mean(baseline, "single:lightgbm", "MAPE"), C_BAR),
        ("Online-linear",         _mean(baseline, "single:online_linear", "MAPE"), C_BAR),
        ("Best single\n(val-chosen)", _mean(baseline, "val_best_single", "MAPE"), C_VAL),
        ("Equal-weight\nensemble", _mean(baseline, "equal_weight_ensemble", "MAPE"), C_EQ),
        ("Adaptive\ncontroller",  _mean(ctrl, "adaptive_deterministic", "MAPE"), C_HERO),
    ]
    rows.sort(key=lambda r: r[1], reverse=True)   # worst at bottom, best at top
    names = [r[0] for r in rows]; vals = [r[1] for r in rows]; cols = [r[2] for r in rows]
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    y = np.arange(len(names))
    bars = ax.barh(y, vals, color=cols, height=0.68)
    ax.set_yticks(y); ax.set_yticklabels(names, fontsize=10)
    ax.set_xlabel("MAPE (%)  — mean over 8 clients, test block")
    ax.set_title("Forecast error by method (lower is better)")
    ax.set_xlim(0, max(vals) * 1.15)
    label_bars_h(ax, bars, vals)
    ax.invert_yaxis()
    fig.savefig(os.path.join(FIGDIR, "fig1_method_mape.png"))
    plt.close(fig); print("fig1_method_mape.png")


# ---------- Figure 2: per-client CV-RMSE, three strategies ----------
def fig2():
    methods = [("adaptive_deterministic", "Adaptive controller", C_HERO, ctrl),
               ("equal_weight_ensemble", "Equal-weight ensemble", C_EQ, baseline),
               ("val_best_single", "Best single (val-chosen)", C_VAL, baseline)]
    x = np.arange(len(CLIENTS)); w = 0.26
    fig, ax = plt.subplots(figsize=(9.5, 4.4))
    for i, (key, lab, col, src) in enumerate(methods):
        vals = [src[c][key]["CV_RMSE"] for c in CLIENTS]
        ax.bar(x + (i - 1) * w, vals, width=w, color=col, label=lab)
    ax.set_xticks(x); ax.set_xticklabels(CLIENTS, rotation=0, fontsize=9.5)
    ax.set_ylabel("CV-RMSE (%)")
    ax.set_title("Per-client accuracy: the controller is lowest on almost every client")
    ax.legend(loc="upper left", ncol=3, fontsize=9.5)
    fig.savefig(os.path.join(FIGDIR, "fig2_perclient_cvrmse.png"))
    plt.close(fig); print("fig2_perclient_cvrmse.png")


# ---------- diagnostics-based figures (MT_132) ----------
def _load_diag():
    p = os.path.join(PROJECT, "code", "results/initial_controller/initial_controller_hourly_MT_132.json")
    D = json.load(open(p))
    return D


# ---------- Figure 3: served vs actual, two-week slice ----------
def fig3():
    D = _load_diag()
    y = np.array(D["y_true"]); served = np.array(D["served_det"])
    n = min(336, len(y)); t = np.arange(n)
    fig, ax = plt.subplots(figsize=(9.5, 3.8))
    ax.plot(t, y[:n], color=C_NEU, lw=1.4, label="Actual load")
    ax.plot(t, served[:n], color=C_HERO, lw=1.4, label="Controller forecast")
    ax.set_xlabel("hours into test block"); ax.set_ylabel("load (kW)")
    ax.set_title("MT_132: controller forecast vs actual load (first two weeks)")
    ax.legend(loc="upper right", ncol=2)
    ax.set_xlim(0, n - 1)
    fig.savefig(os.path.join(FIGDIR, "fig3_served_vs_actual.png"))
    plt.close(fig); print("fig3_served_vs_actual.png")


# ---------- Figure 4: rolling MAE, controller vs best single, with drift ----------
def fig4():
    D = _load_diag()
    y = np.array(D["y_true"]); served = np.array(D["served_det"])
    per_model = {k: np.array(v) for k, v in D["per_model"].items()}
    drift = D["drift_points"]
    best_name = min(per_model, key=lambda k: np.abs(y - per_model[k]).sum())
    roll_c = M.rolling_mae(np.abs(y - served), window=168)
    roll_b = M.rolling_mae(np.abs(y - per_model[best_name]), window=168)
    fig, ax = plt.subplots(figsize=(9.5, 4.0))
    for i, dp in enumerate(drift):
        ax.axvline(dp, color=C_DRIFT, alpha=0.18, lw=0.9,
                   label="drift detected" if i == 0 else None)
    ax.plot(roll_b, color=C_NEU, lw=1.5, label=f"Best single model ({best_name})")
    ax.plot(roll_c, color=C_HERO, lw=1.7, label="Adaptive controller")
    ax.set_xlabel("hours into test block"); ax.set_ylabel("rolling MAE (kW, 168 h)")
    ax.set_title("MT_132: the controller stays at or below the best single model")
    ax.legend(loc="upper right")
    ax.set_xlim(0, len(roll_c) - 1)
    fig.savefig(os.path.join(FIGDIR, "fig4_rolling_mae.png"))
    plt.close(fig); print("fig4_rolling_mae.png")


# ---------- Figure 5: mean served weight per model ----------
def fig5():
    D = _load_diag()
    weights = D["weights"]  # list of {name: weight}
    names = list(D["per_model"].keys())
    tot = {n: 0.0 for n in names}
    for w in weights:
        for n, val in w.items():
            tot[n] += val
    n_steps = len(weights)
    mean_w = {n: tot[n] / n_steps for n in names}
    order = sorted(names, key=lambda n: mean_w[n])
    vals = [mean_w[n] * 100 for n in order]
    cols = [C_HERO if mean_w[n] > 0.05 else C_BAR for n in order]
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    y = np.arange(len(order))
    bars = ax.barh(y, vals, color=cols, height=0.62)
    ax.set_yticks(y); ax.set_yticklabels([n.replace("_", "-") for n in order])
    ax.set_xlabel("mean share of the served blend (%)")
    ax.set_title("MT_132: which models the controller actually uses")
    ax.set_xlim(0, max(vals) * 1.15)
    label_bars_h(ax, bars, vals, fmt="{:.1f}%")
    fig.savefig(os.path.join(FIGDIR, "fig5_model_weights.png"))
    plt.close(fig); print("fig5_model_weights.png")


if __name__ == "__main__":
    fig1(); fig2(); fig3(); fig4(); fig5()
    print("done ->", FIGDIR)
