"""
Step 6 - column-width (3.5 in) versions of the final figures for the two-column paper
(paper/paper.docx). Same data, colours and helpers as make_final_figs.py; layouts are single or
vertically stacked panels so text stays readable at print size. Writes paper/figures_v2/:

  fig_accuracy      MAPE by method, real test data (all baselines)
  fig_per_client    per-client MAPE: Hedge, DWM, MLpol, MELO, SAGE
  fig_shifts        % change vs MELO under each shift: Hedge, DWM, MLpol, MELO daily refit, SAGE
  fig_demo          one injected level shift (MT_132)
  fig_case_105      MT_105's real ~5x load jump on 23 Oct 2014
  fig_case_135      MT_135's inverted daily profile: MAPE and agent weights by hour

The final system is SAGE; MAPE is the primary metric. Hourly refitting is not shown.
"""
from __future__ import annotations
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))   # code/: core modules
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import adaptive_baselines as AB
import metrics as M
import make_final_figs as FF
from make_final_figs import (SLOT, GREY, INK, INK2, GRID, SAGE, COL, POOL, POOL_COL, SCEN, load,
                             real_rows, shift_rel, per_client, case_data, mt135_profile, JUMP_DAY)

PROJECT = FF.PROJECT
CODE = FF.CODE
OUT = os.path.join(PROJECT, "paper", "figures_v2")
os.makedirs(OUT, exist_ok=True)
W = 3.5
plt.rcParams.update({
    "font.size": 7, "axes.titlesize": 7.5, "axes.labelsize": 7, "xtick.labelsize": 6.5,
    "ytick.labelsize": 6.5, "legend.fontsize": 6.5, "savefig.dpi": 300, "figure.dpi": 150,
    "savefig.bbox": "tight", "savefig.pad_inches": 0.03,
    "figure.facecolor": "white", "axes.facecolor": "white", "savefig.facecolor": "white",
    "axes.edgecolor": GRID, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.5,
    "axes.spines.top": False, "axes.spines.right": False, "legend.frameon": False,
    "text.color": INK, "lines.linewidth": 1.0,
})
STACK = [COL["MELO"]] + POOL_COL
STACK_LAB = ["MELO", "s-naive", "H-W", "SARIMA", "LightGBM", "online"]


def stack_legend(ax, y=-0.42):
    ax.legend(loc="upper center", ncol=6, fontsize=5.6, bbox_to_anchor=(0.5, y),
              handlelength=1.0, columnspacing=0.6)


def fig_accuracy():
    rows = real_rows()
    gcol = {"sage": SLOT[0], "melo": SLOT[1]}
    fig, ax = plt.subplots(figsize=(W, 3.1))
    y = np.arange(len(rows)); v = [r[1] for r in rows]
    ax.barh(y, v, height=0.62, color=[gcol.get(r[3], GREY) for r in rows], edgecolor="white", lw=1)
    for yi, vi in zip(y, v):
        ax.text(vi + 0.1, yi, f"{vi:.2f}", va="center", fontsize=6.0, color=INK2)
    ax.set_yticks(y, [r[0].replace(" (2026)", "") for r in rows])
    ax.get_yticklabels()[-1].set_fontweight("bold"); ax.invert_yaxis()
    for b in (4.5, 6.5, 11.5):
        ax.axhline(b, color=GRID, lw=0.8)
    ax.set_xlim(0, 10.8); ax.grid(axis="y", visible=False)
    ax.set_xlabel("test MAPE (%), mean of 8 clients")
    fig.savefig(os.path.join(OUT, "fig_accuracy.png")); plt.close(fig)


def fig_per_client():
    V = per_client()
    clients = list(V[SAGE])
    fig, ax = plt.subplots(figsize=(W, 2.7))
    yy = np.arange(len(clients)); off = np.linspace(-0.3, 0.3, len(V))
    for o, lab in zip(off, V):
        ax.plot([V[lab][c][0] for c in clients], yy + o, "o", ms=3.2, color=COL[lab], mec="white", mew=0.6, label=lab)
    ax.set_yticks(yy, clients); ax.invert_yaxis(); ax.grid(axis="y", visible=False)
    ax.set_xlabel("test MAPE (%)")
    ax.legend(loc="lower right")
    fig.savefig(os.path.join(OUT, "fig_per_client.png")); plt.close(fig)


def fig_shifts():
    R = shift_rel()
    names = ["No\nshift", "Level", "Ramp", "Ampli-\ntude", "Tempo-\nrary"]
    fig, axes = plt.subplots(2, 1, figsize=(W, 3.3), sharex=True)
    x = np.arange(len(SCEN)); w = 0.16
    for ax, metric, lab in ((axes[0], "MAPE", "MAPE (primary)"), (axes[1], "CV_RMSE", "CV-RMSE")):
        for i, method in enumerate(R):
            ax.bar(x + (i - 2) * w, R[method][metric], width=w, color=COL[method], edgecolor="white",
                   lw=0.5, label=method)
        ax.axhline(0, color=INK2, lw=0.7)
        ax.set_ylabel(f"{lab}:\n% vs MELO")
        ax.grid(axis="x", visible=False)
    lo, hi = axes[0].get_ylim(); axes[0].set_ylim(lo, hi * 1.35)
    axes[0].legend(loc="upper left", ncol=3, columnspacing=0.8, handlelength=1.2)
    axes[1].set_xticks(x, names)
    fig.savefig(os.path.join(OUT, "fig_shifts.png")); plt.close(fig)


def fig_demo(client="MT_132", event=1):
    D = load(f"results/sage/hourly_detail/sage_{client}_level.json")
    y = np.asarray(D["y_true"]); served = np.asarray(D["served_det"])
    S = AB.load(os.path.join(CODE, "results", "shift_experiment", "level__blend_nodrift_streams.json"))
    yb, F, Lb = S[client]
    melo = AB.melo(yb, F, Lb, eps0=FF.melo_eps0())
    e = D["events"][event]; lo, hi = e - 7 * 24, e + 14 * 24
    t = (np.arange(lo, hi) - e) / 24.0
    alarms = [a for a in D["drift_points"] if lo <= a < hi]
    refits = [i for i in range(lo, hi) if D["refit_any"][i]]
    fig, axes = plt.subplots(3, 1, figsize=(W, 3.05), sharex=True,
                             gridspec_kw={"height_ratios": [1.4, 1.0, 1.0]})
    ax = axes[0]
    ax.plot(t, y[lo:hi] / 1000, color=INK, lw=0.7, label="actual")
    ax.plot(t, melo[lo:hi] / 1000, color=COL["MELO"], lw=0.8, label="MELO")
    ax.plot(t, served[lo:hi] / 1000, color=COL[SAGE], lw=0.8, label=SAGE)
    y0, y1 = ax.get_ylim(); ax.set_ylim(y0, y1 + 0.18 * (y1 - y0))
    ax.set_ylabel("load (MW)"); ax.legend(loc="upper center", ncol=3)
    ax = axes[1]
    for f, lab in ((melo, "MELO"), (served, SAGE)):
        rel = np.abs(y - f) / np.maximum(y, 0.1 * y.mean())
        ax.plot(t, (M.rolling_mae(rel, 24) * 100)[lo:hi], color=COL[lab], lw=1.0)
    ax.set_ylabel("24 h abs.\n% error")
    for rf in refits:
        ax.plot((rf - e) / 24.0, ax.get_ylim()[1] * 0.96, marker="v", ms=3, color=INK2, ls="none")
    ax = axes[2]
    Wall = np.asarray(D["agent_weights"])
    Ws = np.column_stack([np.convolve(Wall[:, j], np.ones(24) / 24, mode="same")
                          for j in range(Wall.shape[1])])[lo:hi]
    ax.stackplot(t, Ws.T, colors=STACK, labels=STACK_LAB, edgecolor="white", lw=0.3)
    ax.set_ylim(0, 1); ax.set_ylabel("agent\nweight")
    stack_legend(ax, -0.5)
    ax.set_xlabel("days from the shift")
    for a in axes:
        a.axvline(0, color=INK, lw=0.8)
        for al in alarms:
            a.axvline((al - e) / 24.0, color=INK2, lw=0.6, ls="--")
    fig.savefig(os.path.join(OUT, "fig_demo.png")); plt.close(fig)


def fig_case_105(client="MT_105", d0=312, d1=320):
    C = case_data(client)
    lo, hi, j0 = d0 * 24, d1 * 24, JUMP_DAY * 24
    t = (np.arange(lo, hi) - j0) / 24.0
    y, melo, sage, Wt = C["y"], C["melo"], C["sage"], C["W"]
    fig, axes = plt.subplots(2, 1, figsize=(W, 2.8), sharex=True, gridspec_kw={"height_ratios": [1.6, 1.0]})
    ax = axes[0]
    ax.plot(t, y[lo:hi], color=INK, lw=0.7, label="actual")
    ax.plot(t, melo[lo:hi], color=COL["MELO"], lw=0.8, label="MELO")
    ax.plot(t, sage[lo:hi], color=COL[SAGE], lw=0.8, label=SAGE)
    ax.set_ylabel("load (kW)"); ax.legend(loc="upper right", ncol=1)
    pk = int(np.argmax(melo[j0:j0 + 24])) + j0
    ax.annotate(f"MELO {melo[pk]:,.0f} kW\n(actual {y[pk]:,.0f})", ((pk - j0) / 24.0, melo[pk]),
                xytext=(8, -12), textcoords="offset points", fontsize=5.8, color=INK2)
    ax = axes[1]
    Ws = np.column_stack([np.convolve(Wt[:, j], np.ones(6) / 6, mode="same") for j in range(Wt.shape[1])])[lo:hi]
    ax.stackplot(t, Ws.T, colors=STACK, labels=STACK_LAB, edgecolor="white", lw=0.3)
    ax.set_ylim(0, 1); ax.set_ylabel("agent\nweight")
    stack_legend(ax, -0.5)
    ax.set_xlabel("days from the jump (23 Oct 2014)")
    for a in axes:
        a.axvline(0, color=INK, lw=0.8)
        for al in C["alarms"]:
            if lo <= al < hi:
                a.axvline((al - j0) / 24.0, color=INK2, lw=0.6, ls="--")
    fig.savefig(os.path.join(OUT, "fig_case_105.png")); plt.close(fig)


def fig_case_135(client="MT_135"):
    C = case_data(client)
    H, load_h, mape, wmean = mt135_profile(C)
    fig, axes = plt.subplots(3, 1, figsize=(W, 3.15), sharex=True, gridspec_kw={"height_ratios": [0.8, 1.3, 1.0]})
    ax = axes[0]
    ax.bar(H, load_h, color=GREY, edgecolor="white", width=0.8)
    ax.set_ylabel("mean load\n(kW)"); ax.grid(axis="x", visible=False)
    ax = axes[1]
    for lab in ("MELO", SAGE):
        ax.plot(H, mape[lab], color=COL[lab], marker="o", ms=2.8, lw=1.1, label=lab)
    ax.set_ylabel("MAPE (%)"); ax.legend(loc="upper right")
    ax = axes[2]
    ax.stackplot(H, wmean.T, colors=STACK, labels=STACK_LAB, edgecolor="white", lw=0.3)
    ax.set_ylim(0, 1); ax.set_ylabel("mean agent\nweight")
    stack_legend(ax, -0.55)
    ax.set_xticks(H[::3], [f"{h:02d}" for h in H[::3]]); ax.set_xlabel("hour of day")
    fig.savefig(os.path.join(OUT, "fig_case_135.png")); plt.close(fig)


if __name__ == "__main__":
    for old in ("fig_cost.png",):
        if os.path.exists(os.path.join(OUT, old)):
            os.remove(os.path.join(OUT, old))
    for f in (fig_accuracy, fig_per_client, fig_shifts, fig_demo, fig_case_105, fig_case_135):
        f(); print("done", f.__name__, flush=True)
    print("->", OUT)
