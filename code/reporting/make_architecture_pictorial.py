"""
Pictorial architecture diagram: the approved block/arrow data-flow, with small plots of
the REAL system data embedded at each stage (input load, candidate forecasts, agent
weights, served forecast, residual/drift) - the load-forecasting analogue of a diagram
that shows what the data looks like as it moves through the system.

Final system (step 6): MELO combiner + contextual serving agent, drift-triggered refits
with follow-ups. Data: final-system run on MT_132, test block, no shift
(results/sage/hourly_detail/sage_MT_132_none.json). Output: paper/architecture_pictorial_v2.png
(the original v1 figure is kept).
"""
from __future__ import annotations
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))   # code/: core modules
import os, json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

import metrics as M

PROJECT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
D = json.load(open(os.path.join(PROJECT, "code", "results", "sage", "hourly_detail", "sage_MT_132_none.json")))
S5 = json.load(open(os.path.join(PROJECT, "code", "results/summaries/step5_sage_vs_melo.json")))["accuracy"]["none"]
BASE = json.load(open(os.path.join(PROJECT, "code", "results/baselines/static_baselines.json")))
y = np.array(D["y_true"]); served = np.array(D["served_det"])
per_model = {k: np.array(v) for k, v in D["per_model"].items()}
drift = D["drift_points"]

names = list(per_model.keys())
# mean agent weight over the test block, per candidate (MELO + the five models)
cands = D["agent_candidates"]
mw = dict(zip(cands, np.asarray(D["agent_weights"]).mean(axis=0)))

plt.rcParams.update({"font.family": "DejaVu Sans"})
BLUE_F, BLUE_E = "#e2edf7", "#3b6ea5"
ORNG_F, ORNG_E = "#f9edd6", "#c9902b"
GRN_F, GRN_E = "#e0efe1", "#4a8a5c"
RED_F, RED_E = "#f7e0e0", "#b5533b"
INK = "#232323"
MCOL = {"lightgbm": "#3b6ea5", "online_linear": "#1a9e77", "seasonal_naive": "#c9902b",
        "holt_winters": "#8a6bbf", "sarima": "#b5533b", "melo": "#232323"}

fig = plt.figure(figsize=(16, 8.2), dpi=150)
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")


def box(x, y0, w, h, fill, edge, title=None, ty=None, tsize=13):
    ax.add_patch(FancyBboxPatch((x, y0), w, h, boxstyle="round,pad=0.006,rounding_size=0.018",
                                linewidth=2.2, edgecolor=edge, facecolor=fill, zorder=1))
    if title:
        ax.text(x + w / 2, ty if ty else y0 + h - 0.035, title, ha="center", va="top",
                fontsize=tsize, fontweight="bold", color=INK, zorder=3)


def arrow(p0, p1, color, lw=2.8, rad=0.0):
    ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle="-|>", mutation_scale=22,
                                 lw=lw, color=color, zorder=2,
                                 connectionstyle=f"arc3,rad={rad}",
                                 capstyle="round"))


def inset(x, y0, w, h, spine="#b9b9b9"):
    a = fig.add_axes([x, y0, w, h]); a.set_zorder(4)
    a.set_facecolor("white")
    for s in a.spines.values():
        s.set_linewidth(0.7); s.set_color(spine)
    a.set_xticks([]); a.set_yticks([])
    a.tick_params(length=0)
    return a


def ititle(a, t):
    a.set_title(t, fontsize=8.5, color="#555", pad=3)


# ================= main forward path =================
# Data Stream
box(0.015, 0.545, 0.155, 0.315, BLUE_F, BLUE_E, "Data Stream", ty=0.845)
a = inset(0.033, 0.595, 0.122, 0.145)
a.plot(y[:168], color=BLUE_E, lw=1.1)
ititle(a, "hourly load (1 week)")
ax.text(0.0925, 0.568, "+ calendar features", ha="center", fontsize=8.5, color="#555", zorder=3)

# Model Pool
box(0.205, 0.375, 0.205, 0.485, BLUE_F, BLUE_E, "Forecasting Model Pool", ty=0.845)
mp = [("Seasonal-naive", "seasonal_naive"), ("Holt–Winters", "holt_winters"),
      ("SARIMA", "sarima"), ("LightGBM", "lightgbm"), ("Online-linear (SGD)", "online_linear")]
for i, (lbl, key) in enumerate(mp):
    yy = 0.795 - i * 0.040
    ax.add_patch(plt.Circle((0.226, yy), 0.005, color=MCOL[key], zorder=3, transform=ax.transData))
    ax.text(0.237, yy, lbl, ha="left", va="center", fontsize=10.5, color=INK, zorder=3)
a = inset(0.226, 0.398, 0.165, 0.14)
n = 96
a.plot(y[:n], color="#8a8a8a", lw=1.6, zorder=1)
for m in ("lightgbm", "online_linear", "seasonal_naive"):
    a.plot(per_model[m][:n], color=MCOL[m], lw=1.0, alpha=0.95)
ititle(a, "candidate forecasts")

# Controller
box(0.445, 0.44, 0.20, 0.42, ORNG_F, ORNG_E, "Agentic Controller", ty=0.845)
ax.text(0.545, 0.80, "MELO combiner → contextual agent\nre-weights MELO + models each hour",
        ha="center", va="top", fontsize=8.6, color="#555", zorder=3)
a = inset(0.475, 0.495, 0.14, 0.155)
order = sorted([k for k in cands if mw[k] > 0.001], key=lambda k: mw[k])
a.barh(range(len(order)), [mw[k] * 100 for k in order],
       color=[MCOL[k] for k in order], height=0.62)
a.set_yticks(range(len(order)))
a.set_yticklabels([("MELO" if k == "melo" else k.split("_")[0]) for k in order], fontsize=7.5, color=INK)
a.tick_params(axis="y", length=0)
ititle(a, "mean agent weights (%)")

# Served Forecast
box(0.68, 0.52, 0.135, 0.315, GRN_F, GRN_E, "Served Forecast", ty=0.81)
a = inset(0.695, 0.565, 0.105, 0.15)
a.plot(y[:n], color="#8a8a8a", lw=1.3)
a.plot(served[:n], color=GRN_E, lw=1.3)
ititle(a, "ŷ  vs  actual")

# Evaluation
box(0.85, 0.545, 0.135, 0.315, BLUE_F, BLUE_E, "Evaluation", ty=0.845)
a = inset(0.868, 0.60, 0.10, 0.14)
eq = float(np.mean([BASE[c]["equal_weight_ensemble"]["MAPE"] for c in BASE if not c.startswith("_")]))
a.bar(range(3), [S5["proposed + agent"]["MAPE"], S5["MELO alone"]["MAPE"], eq],
      color=[GRN_E, ORNG_E, "#a86fa0"], width=0.64)
a.set_xticks(range(3)); a.set_xticklabels(["SAGE", "MELO", "Eq-wt"], fontsize=7, color=INK)
a.tick_params(axis="x", length=0)
ititle(a, "MAPE (%)")

# ================= feedback loop =================
box(0.30, 0.135, 0.40, 0.205, RED_F, RED_E, "Concept-Drift Detection", ty=0.315)
ax.text(0.50, 0.285, "ADWIN + Page–Hinkley on residual  e_t = y_t − ŷ_t",
        ha="center", va="top", fontsize=9.5, color="#555", zorder=3)
a = inset(0.395, 0.15, 0.21, 0.085)
roll = M.rolling_mae(np.abs(y - served), 168)
a.plot(roll, color=RED_E, lw=1.2)
ymax = np.nanmax(roll)
a.vlines(drift, ymax * 0.86, ymax, color="#8a2b2b", alpha=0.55, lw=0.6)
a.set_ylim(0, ymax * 1.05)
ititle(a, "rolling error + drift flags")

# ---- forward arrows (blue) ----
arrow((0.170, 0.70), (0.205, 0.70), BLUE_E)
arrow((0.410, 0.65), (0.445, 0.65), BLUE_E)
arrow((0.645, 0.665), (0.680, 0.665), BLUE_E)
arrow((0.815, 0.70), (0.850, 0.70), BLUE_E)
ax.text(0.187, 0.716, "stream", ha="center", fontsize=8.5, fontweight="bold", color=BLUE_E, zorder=3)
ax.text(0.427, 0.668, "candidate\nforecasts", ha="center", fontsize=8, fontweight="bold", color=BLUE_E, zorder=3)

# ground truth into evaluation
arrow((0.917, 0.915), (0.917, 0.860), "#666")
ax.text(0.917, 0.935, "ground truth  y_t", ha="center", fontsize=9, color="#666", zorder=3)

# ---- feedback arrows (red) ----
arrow((0.917, 0.545), (0.917, 0.237), RED_E)
arrow((0.917, 0.237), (0.700, 0.237), RED_E)
ax.text(0.808, 0.252, "residual  e_t", ha="center", fontsize=9, fontweight="bold", color=RED_E, zorder=3)
arrow((0.50, 0.340), (0.50, 0.44), RED_E)
ax.text(0.513, 0.392, "drift flag", ha="left", fontsize=9, fontweight="bold", color=RED_E, zorder=3)
arrow((0.30, 0.255), (0.16, 0.255), RED_E)
arrow((0.16, 0.255), (0.16, 0.375), RED_E)
ax.text(0.235, 0.270, "refit + follow-up refits", ha="center", fontsize=8.5,
        fontweight="bold", color=RED_E, zorder=3)

out = os.path.join(PROJECT, "paper", "architecture_pictorial_v2.png")
fig.savefig(out, dpi=150, bbox_inches="tight", pad_inches=0.18)
print("saved ->", out)
