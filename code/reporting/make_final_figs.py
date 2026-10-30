"""
Step 6 - figures for the final system, SAGE (Self-Adaptive aGEntic forecaster: MELO combiner +
calibrated drift + follow-up refits + contextual agent), from the saved results. Writes
code/figures_final/:

  fig1_real_data_accuracy.png   MAPE and CV-RMSE on the real test data, every method
  fig2_shift_vs_baselines.png   % change vs MELO under each injected shift, for SAGE and baselines
  fig3_demo_level_shift.png     one level-shift event: the median (MAPE change vs MELO over the
                                next 336 h) of the 10 events the detector caught = MT_132,
                                event 2 (../logs/2026-10-25_step6_wrapup/03_demo_event_choice.log)
  fig4_per_client.png           per-client MAPE (primary) / CV-RMSE on the real test data
  fig5_case_MT_105.png          case: MT_105's ~5x load jump on 23 Oct 2014 (real data)
  fig6_case_MT_135.png          case: MT_135's inverted daily profile and low-load hours (real data)

The two case figures need results/sage/hourly_detail/sage_<client>_none.json
(../logs/2026-10-29_sage_cases/). MAPE is the primary metric. Hourly refitting is not shown: it
is not a feasible operating point. Colours follow the entity, in fixed slot order: SAGE blue,
MELO orange, MLpol aqua, DWM yellow, MELO daily refit magenta, Hedge green; other baselines neutral grey.
The per-client and shift figures compare SAGE with the four best baselines (MELO, DWM, MLpol, Hedge).
"""
from __future__ import annotations
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))   # code/: core modules
import json, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import adaptive_baselines as AB
import metrics as M

PROJECT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CODE = os.path.join(PROJECT, "code")
OUT = os.path.join(CODE, "figures_final")
os.makedirs(OUT, exist_ok=True)

SLOT = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300"]
GREY, INK, INK2, GRID, SURF = "#b9b8b2", "#0b0b0b", "#52514e", "#e6e5e0", "#fcfcfb"
SAGE = "SAGE"
COL = {SAGE: SLOT[0], "MELO": SLOT[1], "MLpol": SLOT[2], "DWM": SLOT[3],
       "MELO, daily refit": SLOT[4], "Hedge": SLOT[5]}
TOP = ("Hedge", "DWM", "MLpol", "MELO", SAGE)        # SAGE + the 4 best baselines on real-data MAPE
POOL = ["s-naive", "Holt-Winters", "SARIMA", "LightGBM", "online linear"]
POOL_COL = ["#d9d8d3", "#8c8b86", SLOT[3], SLOT[2], SLOT[4]]     # agent-weight stacks (MELO = orange; blue stays SAGE-only)
plt.rcParams.update({
    "figure.dpi": 150, "savefig.dpi": 200, "savefig.bbox": "tight",
    "figure.facecolor": SURF, "axes.facecolor": SURF, "savefig.facecolor": SURF,
    "font.size": 9, "axes.titlesize": 10, "axes.labelsize": 9,
    "axes.edgecolor": GRID, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
    "axes.spines.top": False, "axes.spines.right": False, "legend.frameon": False,
    "text.color": INK,
})


def load(name):
    return json.load(open(os.path.join(CODE, name)))


def mean_over_clients(res, key, metric):
    cs = [c for c in res if not c.startswith("_")]
    return float(np.mean([res[c][key][metric] for c in cs]))


def melo_eps0():
    return load("results/baselines/online_combiners.json")["chosen_params"]["melo"]["eps0"]


# ---------------------------------------------------------------- shared data
def real_rows():
    """(label, MAPE, CV-RMSE, group) for every method on the real test data."""
    base = load("results/baselines/static_baselines.json")
    ada = load("results/baselines/online_combiners.json")["test"]["pool_forecasts_test"]
    ctrl = load("results/initial_controller/initial_controller.json")
    s5 = load("results/summaries/step5_sage_vs_melo.json")["accuracy"]["none"]
    mc = lambda k: (mean_over_clients(base, k, "MAPE"), mean_over_clients(base, k, "CV_RMSE"))
    rows = [(lab, *mc(f"single:{k}"), "single") for lab, k in
            (("Seasonal naive", "seasonal_naive"), ("Holt-Winters", "holt_winters"), ("SARIMA", "sarima"),
             ("LightGBM", "lightgbm"), ("Online linear", "online_linear"))]
    rows += [("Equal-weight ensemble", *mc("equal_weight_ensemble"), "combo"),
             ("Best single model (val.)", *mc("val_best_single"), "combo")]
    rows += [(lab, ada[k]["_mean"]["MAPE"], ada[k]["_mean"]["CV_RMSE"], "agg") for lab, k in
             (("FTL", "ftl"), ("Hedge", "hedge"), ("DWM", "dwm"), ("MLpol", "mlpol"))]
    rows += [("Initial controller", mean_over_clients(ctrl, "adaptive_bandit", "MAPE"),
              mean_over_clients(ctrl, "adaptive_bandit", "CV_RMSE"), "agg"),
             ("MELO (2026)", s5["MELO alone"]["MAPE"], s5["MELO alone"]["CV_RMSE"], "melo"),
             (SAGE, s5["proposed + agent"]["MAPE"], s5["proposed + agent"]["CV_RMSE"], "sage")]
    return rows


SCEN = ["none", "level", "ramp", "amplitude", "temporary"]


def shift_rel():
    """% change vs MELO (weekly refit) for each method, scenario and metric."""
    s5 = load("results/summaries/step5_sage_vs_melo.json")["accuracy"]
    s4 = load("results/summaries/step4_shift_experiment.json")
    ada = load("results/baselines/online_combiners.json")["test"]["pool_forecasts_test"]

    def val(method, sc, m):
        if method == SAGE:
            return s5[sc]["proposed + agent"][m]
        if method == "MELO, daily refit":
            return s4[sc]["melo (daily refit)"][m] if sc != "none" else np.nan
        k = method.lower()
        return ada[k]["_mean"][m] if sc == "none" else s4[sc][f"{k} (weekly refit)"][m]
    return {method: {m: [100 * (val(method, sc, m) / s5[sc]["MELO alone"][m] - 1) for sc in SCEN]
                     for m in ("MAPE", "CV_RMSE")}
            for method in ("Hedge", "DWM", "MLpol", "MELO, daily refit", SAGE)}


def per_client():
    """{method: {client: (MAPE, CV-RMSE)}} on the real test data, for SAGE and the top-4 baselines."""
    S = AB.load(os.path.join(CODE, "results/forecasts/pool_forecasts_test.json"))
    A = load("results/sage/sage_none_forecasts.json")
    ada = load("results/baselines/online_combiners.json")["test"]["pool_forecasts_test"]
    eps0 = melo_eps0()
    out = {m: {} for m in TOP}
    for c in S:
        y, F, L = S[c]
        for m in ("Hedge", "DWM", "MLpol"):
            out[m][c] = (ada[m.lower()][c]["MAPE"], ada[m.lower()][c]["CV_RMSE"])
        m = AB.melo(y, F, L, eps0=eps0)
        out["MELO"][c] = (M.mape(y, m), M.cv_rmse(y, m))
        a = np.asarray(A[c]["served"])
        out[SAGE][c] = (M.mape(y, a), M.cv_rmse(y, a))
    return out


def case_data(client):
    """Diagnostics of SAGE on one client (real data) plus the MELO-alone replay."""
    D = load(f"results/sage/hourly_detail/sage_{client}_none.json")
    S = AB.load(os.path.join(CODE, "results/forecasts/pool_forecasts_test.json"))
    y, F, L = S[client]
    assert np.allclose(np.asarray(D["y_true"]), y)
    from data_pipeline import prepare
    cs = prepare()[client]
    lo = cs.splits["test"][0]
    idx = cs.y.index[lo:lo + len(y)]
    return dict(y=y, F=np.asarray(F), melo=AB.melo(y, F, L, eps0=melo_eps0()),
                sage=np.asarray(D["served_det"]), W=np.asarray(D["agent_weights"]),
                alarms=D["drift_points"], refit=np.asarray(D["refit_any"], bool), idx=idx)


def mt135_profile(C):
    """Mean load, MAPE (MELO, SAGE) and mean agent weights by hour of day."""
    y, W, hrs = C["y"], C["W"], C["idx"].hour
    ok = y >= 1.0                                       # MAPE is undefined at zero-load hours
    H = np.arange(24)
    load_h = np.array([y[hrs == h].mean() for h in H])
    mape = {lab: np.array([100 * np.mean(np.abs(y - f)[(hrs == h) & ok] / y[(hrs == h) & ok]) for h in H])
            for lab, f in (("MELO", C["melo"]), (SAGE, C["sage"]))}
    wmean = np.array([W[hrs == h].mean(axis=0) for h in H])
    return H, load_h, mape, wmean


# ---------------------------------------------------------------- fig 1
def fig1():
    rows = real_rows()
    fig, axes = plt.subplots(1, 2, figsize=(9.5, 5.0), sharey=True)
    y = np.arange(len(rows))
    gcol = {"sage": SLOT[0], "melo": SLOT[1]}
    for ax, j, title in ((axes[0], 1, "MAPE (%), primary metric"), (axes[1], 2, "CV-RMSE (%)")):
        vals = [r[j] for r in rows]
        ax.barh(y, vals, height=0.62, color=[gcol.get(r[3], GREY) for r in rows], edgecolor=SURF, linewidth=2)
        for yi, v in zip(y, vals):
            ax.text(v + 0.15, yi, f"{v:.2f}", va="center", fontsize=8, color=INK2)
        ax.set_xlim(0, max(vals) * 1.12)
        ax.set_title(title, loc="left", color=INK)
        ax.grid(axis="y", visible=False)
        for b in (4.5, 6.5, 11.5):
            ax.axhline(b, color=GRID, linewidth=1.0)
    axes[0].set_yticks(y, [r[0] for r in rows])
    axes[0].get_yticklabels()[-1].set_fontweight("bold")
    axes[0].invert_yaxis()
    fig.suptitle("Accuracy on the real test data (mean of 8 clients; lower is better)",
                 x=0.01, ha="left", fontsize=11)
    fig.text(0.01, -0.02, "Groups: single models | simple combinations | online aggregation and our initial "
             "controller | MELO and SAGE. Blue = SAGE, orange = MELO.", fontsize=7.5, color=INK2)
    fig.savefig(os.path.join(OUT, "fig1_real_data_accuracy.png"))
    plt.close(fig)


# ---------------------------------------------------------------- fig 2
def fig2():
    R = shift_rel()
    names = ["No\nshift", "Level\n+30%", "Ramp", "Ampli-\ntude", "Temporary\nshock"]
    fig, axes = plt.subplots(1, 2, figsize=(9.5, 3.9))
    x = np.arange(len(SCEN)); w = 0.16
    for ax, metric, title in ((axes[0], "MAPE", "MAPE (primary)"), (axes[1], "CV_RMSE", "CV-RMSE")):
        for i, method in enumerate(R):
            ax.bar(x + (i - 2) * w, R[method][metric], width=w, color=COL[method], edgecolor=SURF,
                   linewidth=1.0, label=method)
        ax.axhline(0, color=INK2, linewidth=0.8)
        ax.set_xticks(x, names, fontsize=8)
        ax.set_title(f"{title}: % change vs MELO", loc="left")
        ax.grid(axis="x", visible=False)
    axes[0].legend(loc="upper left", fontsize=8, ncol=2)
    lo, hi = axes[0].get_ylim(); axes[0].set_ylim(lo, hi * 1.3)
    fig.suptitle("Injected demand shifts: SAGE and baselines against MELO (below 0 = better than MELO)",
                 x=0.01, ha="left", fontsize=11, y=1.03)
    fig.text(0.01, -0.03, "Test block, mean of 8 clients. MELO, Hedge, DWM and MLpol refit weekly; no daily-refit run "
             "exists for the no-shift case. The equal-weight ensemble (+26-39% MAPE) is off the scale.",
             fontsize=7.5, color=INK2)
    fig.savefig(os.path.join(OUT, "fig2_shift_vs_baselines.png"))
    plt.close(fig)


# ---------------------------------------------------------------- fig 3
def fig3(client="MT_132", event=1):
    D = load(f"results/sage/hourly_detail/sage_{client}_level.json")
    y = np.asarray(D["y_true"]); served = np.asarray(D["served_det"])
    S = AB.load(os.path.join(CODE, "results", "shift_experiment", "level__blend_nodrift_streams.json"))
    yb, F, Lb = S[client]
    assert np.allclose(yb, y)
    melo = AB.melo(yb, F, Lb, eps0=melo_eps0())
    e = D["events"][event]
    lo, hi = e - 7 * 24, e + 14 * 24
    t = (np.arange(lo, hi) - e) / 24.0
    alarms = [a for a in D["drift_points"] if lo <= a < hi]
    refits = [i for i in range(lo, hi) if D["refit_any"][i]]

    fig, axes = plt.subplots(3, 1, figsize=(9.5, 7.6), sharex=True,
                             gridspec_kw={"height_ratios": [2.2, 1.3, 1.4]})
    ax = axes[0]
    ax.plot(t, y[lo:hi], color=INK, linewidth=1.0, label="Actual load")
    ax.plot(t, melo[lo:hi], color=COL["MELO"], linewidth=1.2, label="MELO")
    ax.plot(t, served[lo:hi], color=COL[SAGE], linewidth=1.2, label=SAGE)
    ax.set_ylabel("kW")
    y0, y1 = ax.get_ylim(); ax.set_ylim(y0, y1 + 0.14 * (y1 - y0))
    ax.legend(loc="upper left", ncol=3, fontsize=8)
    what = "rises 30%" if event == 0 else "drops back to normal (removing the earlier +30%)"
    ax.set_title(f"{client}: demand {what} at day 0 (injected level shift, test block)\n"
                 "solid line = shift, dashed = drift alarms, ▼ = model refits", loc="left")

    ax = axes[1]
    for f, lab in ((melo, "MELO"), (served, SAGE)):
        rel = np.abs(y - f) / np.maximum(y, 0.1 * y.mean())
        ax.plot(t, (M.rolling_mae(rel, 24) * 100)[lo:hi], color=COL[lab], linewidth=1.4, label=lab)
    ax.set_ylabel("24 h rolling\nabs. % error")
    ax.legend(loc="upper right", fontsize=8)

    ax = axes[2]
    Wall = np.asarray(D["agent_weights"])
    k = np.ones(24) / 24
    # smooth over the whole run, then cut the window (avoids zero-padding droop at the edges)
    Ws = np.column_stack([np.convolve(Wall[:, j], k, mode="same") for j in range(Wall.shape[1])])[lo:hi]
    ax.stackplot(t, Ws.T, colors=[COL["MELO"]] + POOL_COL, labels=["MELO"] + POOL, edgecolor=SURF, linewidth=0.4)
    ax.set_ylim(0, 1)
    ax.set_ylabel("SAGE agent weight\n(24 h mean)")
    ax.legend(loc="upper left", ncol=6, fontsize=7.5, bbox_to_anchor=(0, -0.28))
    ax.set_xlabel("days from the shift")

    for a in axes:
        a.axvline(0, color=INK, linewidth=1.0)
        for al in alarms:
            a.axvline((al - e) / 24.0, color=INK2, linewidth=0.8, linestyle="--")
    for rf in refits:
        axes[1].plot((rf - e) / 24.0, axes[1].get_ylim()[1] * 0.97, marker="v", markersize=4,
                     color=INK2, linestyle="none")
    fig.savefig(os.path.join(OUT, "fig3_demo_level_shift.png"))
    plt.close(fig)


# ---------------------------------------------------------------- fig 4
def fig4():
    V = per_client()
    clients = list(V[SAGE])
    fig, axes = plt.subplots(1, 2, figsize=(9.5, 4.0))
    yy = np.arange(len(clients)); off = np.linspace(-0.3, 0.3, len(V))
    for ax, j, title in ((axes[0], 0, "MAPE (%), primary metric"), (axes[1], 1, "CV-RMSE (%)")):
        for o, lab in zip(off, V):
            ax.plot([V[lab][c][j] for c in clients], yy + o, marker="o", markersize=6, linestyle="none",
                    color=COL[lab], markeredgecolor=SURF, markeredgewidth=1.2, label=lab)
        ax.set_title(title, loc="left")
        ax.grid(axis="y", visible=False)
        ax.set_yticks(yy, clients)
        ax.invert_yaxis()
    axes[1].legend(loc="lower right", fontsize=8)
    wins = sum(V[SAGE][c][0] < V["MELO"][c][0] for c in clients)
    fig.suptitle("Per-client accuracy on the real test data (lower is better)", x=0.01, ha="left", fontsize=11)
    fig.text(0.01, -0.03, f"SAGE has lower MAPE than MELO on {wins} of {len(clients)} clients and beats Hedge, DWM and MLpol "
             "on CV-RMSE for every client. Its biggest gains are on MT_135 (MAPE)\nand MT_105 (CV-RMSE); figs 5-6 explain "
             "both.", fontsize=7.5, color=INK2)
    fig.savefig(os.path.join(OUT, "fig4_per_client.png"))
    plt.close(fig)


# ---------------------------------------------------------------- fig 5
JUMP_DAY = 314                      # MT_105: 23 Oct 2014 is test day 314


def fig5(client="MT_105", d0=310, d1=322):
    C = case_data(client)
    lo, hi, j0 = d0 * 24, d1 * 24, JUMP_DAY * 24
    t = (np.arange(lo, hi) - j0) / 24.0
    y, melo, sage, W = C["y"], C["melo"], C["sage"], C["W"]
    fig, axes = plt.subplots(3, 1, figsize=(9.5, 7.4), sharex=True,
                             gridspec_kw={"height_ratios": [2.2, 1.3, 1.4]})
    ax = axes[0]
    ax.plot(t, y[lo:hi], color=INK, linewidth=1.0, label="Actual load")
    ax.plot(t, melo[lo:hi], color=COL["MELO"], linewidth=1.1, label="MELO")
    ax.plot(t, sage[lo:hi], color=COL[SAGE], linewidth=1.1, label=SAGE)
    ax.set_ylabel("kW")
    ax.legend(loc="upper left", ncol=3, fontsize=8)
    pk = int(np.argmax(melo[j0:j0 + 24])) + j0
    ax.annotate(f"MELO: {melo[pk]:,.0f} kW\n(actual {y[pk]:,.0f})", ((pk - j0) / 24.0, melo[pk]),
                xytext=(14, -6), textcoords="offset points", fontsize=7.5, color=INK2)
    ax.set_title(f"{client}, {C['idx'][lo]:%d %b} – {C['idx'][hi - 1]:%d %b %Y} (real data): after four quiet "
                 "weeks the load jumps about 5× on 23 Oct\nsolid line = jump, dashed = drift alarms, "
                 "▼ = model refits", loc="left")
    ax = axes[1]
    for f, lab in ((melo, "MELO"), (sage, SAGE)):
        ax.plot(t, np.abs(y - f)[lo:hi], color=COL[lab], linewidth=1.0, label=lab)
    ax.set_ylabel("absolute error\n(kW)")
    ax.legend(loc="upper right", fontsize=8)
    ax = axes[2]
    k = np.ones(6) / 6
    Ws = np.column_stack([np.convolve(W[:, j], k, mode="same") for j in range(W.shape[1])])[lo:hi]
    ax.stackplot(t, Ws.T, colors=[COL["MELO"]] + POOL_COL, labels=["MELO"] + POOL, edgecolor=SURF, linewidth=0.3)
    ax.set_ylim(0, 1); ax.set_ylabel("SAGE agent weight\n(6 h mean)")
    ax.legend(loc="upper left", ncol=6, fontsize=7.5, bbox_to_anchor=(0, -0.28))
    ax.set_xlabel("days from the jump (23 Oct 2014, 09:00)")
    for a in axes:
        a.axvline(0, color=INK, linewidth=1.0)
        for al in C["alarms"]:
            if lo <= al < hi:
                a.axvline((al - j0) / 24.0, color=INK2, linewidth=0.8, linestyle="--")
    for i in np.flatnonzero(C["refit"][lo:hi]):
        axes[1].plot(t[i], axes[1].get_ylim()[1] * 0.97, marker="v", markersize=4, color=INK2, linestyle="none")
    fig.savefig(os.path.join(OUT, "fig5_case_MT_105.png"))
    plt.close(fig)


# ---------------------------------------------------------------- fig 6
def fig6(client="MT_135"):
    C = case_data(client)
    H, load_h, mape, wmean = mt135_profile(C)
    fig, axes = plt.subplots(3, 1, figsize=(9.5, 7.2), sharex=True,
                             gridspec_kw={"height_ratios": [1.2, 1.5, 1.3]})
    ax = axes[0]
    ax.bar(H, load_h, color=GREY, edgecolor=SURF, width=0.8)
    ax.set_ylabel("mean load\n(kW)"); ax.grid(axis="x", visible=False)
    ax.set_title(f"{client} (real test data): load peaks at night and is low by day; SAGE gains most in "
                 "the low-load and transition hours", loc="left")
    ax = axes[1]
    for lab in ("MELO", SAGE):
        ax.plot(H, mape[lab], color=COL[lab], marker="o", markersize=5, linewidth=1.6, label=lab)
    ax.set_ylabel("MAPE (%)\nby hour of day"); ax.legend(loc="upper right", fontsize=8)
    ax = axes[2]
    ax.stackplot(H, wmean.T, colors=[COL["MELO"]] + POOL_COL, labels=["MELO"] + POOL, edgecolor=SURF, linewidth=0.4)
    ax.set_ylim(0, 1); ax.set_ylabel("mean SAGE\nagent weight")
    ax.legend(loc="upper left", ncol=6, fontsize=7.5, bbox_to_anchor=(0, -0.3))
    ax.set_xticks(H[::2], [f"{h:02d}" for h in H[::2]]); ax.set_xlabel("hour of day")
    fig.savefig(os.path.join(OUT, "fig6_case_MT_135.png"))
    plt.close(fig)


if __name__ == "__main__":
    for old in ("fig2_shift_vs_melo.png",):
        if os.path.exists(os.path.join(OUT, old)):
            os.remove(os.path.join(OUT, old))
    for f in (fig1, fig2, fig3, fig4, fig5, fig6):
        f(); print("done", f.__name__, flush=True)
    print("figures ->", OUT)
