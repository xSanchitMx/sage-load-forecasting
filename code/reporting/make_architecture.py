"""
Left-to-right system architecture diagram (no module framing).

Draws the system as one continuous data-flow pipeline: a forward forecast path
(data -> model pool -> performance-weighted fusion + bandit -> served forecast ->
evaluation) with the two adaptation feedback loops beneath it (drift detection ->
retrain; reward -> bandit). Renders paper/architecture_flow.png.
"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))   # code/: core modules
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

PROJECT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(PROJECT, "paper", "architecture_flow.png")

# ---- palette -------------------------------------------------------------
FWD_FILL, FWD_EDGE = "#E3EEFB", "#2E5E8C"    # forward pipeline (cool)
CTRL_FILL, CTRL_EDGE = "#FBEBD0", "#B5791C"  # controller (warm)
SERVE_FILL, SERVE_EDGE = "#DCEBDD", "#3B7A3F"# served output
FB_FILL, FB_EDGE = "#FADBDD", "#B03A46"      # drift / feedback (accent)
CHIP_FILL, CHIP_EDGE = "#FFFFFF", "#8A94A3"  # model chips
TXT = "#16202B"
FWD_ARROW = "#2E5E8C"
FB_ARROW = "#B03A46"

fig, ax = plt.subplots(figsize=(16, 8.2), dpi=200)
ax.set_xlim(0, 16)
ax.set_ylim(0, 8.2)
ax.axis("off")


def box(cx, cy, w, h, fill, edge, lw=2.0, rad=0.10, z=2):
    ax.add_patch(FancyBboxPatch(
        (cx - w / 2, cy - h / 2), w, h,
        boxstyle=f"round,pad=0.02,rounding_size={rad}",
        linewidth=lw, edgecolor=edge, facecolor=fill, zorder=z))


def title_block(cx, cy, w, h, fill, edge, title, sub=None, tsize=14, ssize=10.5, lw=2.0):
    box(cx, cy, w, h, fill, edge, lw=lw)
    if sub:
        ax.text(cx, cy + 0.20, title, ha="center", va="center",
                fontsize=tsize, fontweight="bold", color=TXT, zorder=4)
        ax.text(cx, cy - h / 2 + 0.34, sub, ha="center", va="center",
                fontsize=ssize, color="#44515F", zorder=4)
    else:
        ax.text(cx, cy, title, ha="center", va="center",
                fontsize=tsize, fontweight="bold", color=TXT, zorder=4)


def arrow(x1, y1, x2, y2, color=FWD_ARROW, lw=2.4, rad=0.0, ls="-"):
    ax.add_patch(FancyArrowPatch(
        (x1, y1), (x2, y2),
        arrowstyle="-|>", mutation_scale=20, linewidth=lw,
        color=color, linestyle=ls,
        connectionstyle=f"arc3,rad={rad}", zorder=3,
        shrinkA=0, shrinkB=0))


def label(x, y, s, color=TXT, size=10.5, weight="bold", bg=True, ha="center"):
    bbox = dict(boxstyle="round,pad=0.18", fc="white", ec="none", alpha=0.9) if bg else None
    ax.text(x, y, s, ha=ha, va="center", fontsize=size, color=color,
            fontweight=weight, zorder=5, bbox=bbox)


# ================= FORWARD PATH (top spine, y = 5.3) =====================
Y = 5.3

# 1. Data stream / preprocessing
box(1.75, Y, 2.9, 2.0, FWD_FILL, FWD_EDGE)
ax.text(1.75, Y + 0.62, "Data Stream", ha="center", va="center",
        fontsize=14.5, fontweight="bold", color=TXT, zorder=4)
ax.text(1.75, Y - 0.22, "hourly load\n+ calendar features\ncausal scaling",
        ha="center", va="center", fontsize=10, color="#44515F", zorder=4)

# 2. Model pool (5 chips)
POOL_CX, POOL_W, POOL_H = 5.35, 3.1, 4.6
title_block(POOL_CX, Y, POOL_W, POOL_H, FWD_FILL, FWD_EDGE, "", None)
ax.text(POOL_CX, Y + POOL_H / 2 - 0.34, "Forecasting Model Pool",
        ha="center", va="center", fontsize=14, fontweight="bold", color=TXT, zorder=4)
models = ["Seasonal-naive", "Holt–Winters", "SARIMA",
          "LightGBM", "Online linear (SGD)"]
chip_h = 0.62
top = Y + POOL_H / 2 - 0.95
for i, m in enumerate(models):
    cy = top - i * (chip_h + 0.12)
    box(POOL_CX, cy, POOL_W - 0.7, chip_h, CHIP_FILL, CHIP_EDGE, lw=1.4, rad=0.06, z=3)
    ax.text(POOL_CX, cy, m, ha="center", va="center", fontsize=10.5,
            color=TXT, zorder=4)

# 3. Controller: fusion + bandit (two stacked sub-panels)
CTRL_CX, CTRL_W, CTRL_H = 9.35, 3.15, 4.6
title_block(CTRL_CX, Y, CTRL_W, CTRL_H, CTRL_FILL, CTRL_EDGE, "", None)
ax.text(CTRL_CX, Y + CTRL_H / 2 - 0.34, "Adaptive Controller",
        ha="center", va="center", fontsize=14, fontweight="bold", color=TXT, zorder=4)
# sub-panel: performance-weighted fusion
box(CTRL_CX, Y + 0.68, CTRL_W - 0.55, 1.5, "#FFFFFF", CTRL_EDGE, lw=1.5, rad=0.07, z=3)
ax.text(CTRL_CX, Y + 1.12, "Performance-weighted fusion", ha="center", va="center",
        fontsize=10.8, fontweight="bold", color=TXT, zorder=4)
ax.text(CTRL_CX, Y + 0.52, "EWMA error → inverse-error\ntop-k blend · demote weak",
        ha="center", va="center", fontsize=9.6, color="#44515F", zorder=4)
# sub-panel: bandit
box(CTRL_CX, Y - 1.02, CTRL_W - 0.55, 1.42, "#FFFFFF", CTRL_EDGE, lw=1.5, rad=0.07, z=3)
ax.text(CTRL_CX, Y - 0.62, "Discounted-UCB1 bandit", ha="center", va="center",
        fontsize=10.8, fontweight="bold", color=TXT, zorder=4)
ax.text(CTRL_CX, Y - 1.22, "arg max Uᵢ :\nfollow_blend vs force_best",
        ha="center", va="center", fontsize=9.6, color="#44515F", zorder=4)

# 4. Served forecast
SERVE_CX = 12.55
title_block(SERVE_CX, Y, 2.0, 2.0, SERVE_FILL, SERVE_EDGE, "", None)
ax.text(SERVE_CX, Y + 0.42, "Served", ha="center", va="center",
        fontsize=13.5, fontweight="bold", color=TXT, zorder=4)
ax.text(SERVE_CX, Y + 0.02, "Forecast", ha="center", va="center",
        fontsize=13.5, fontweight="bold", color=TXT, zorder=4)
ax.text(SERVE_CX, Y - 0.5, r"$\hat{y}_t$", ha="center", va="center",
        fontsize=16, color=SERVE_EDGE, zorder=4)

# 5. Evaluation & reward
EVAL_CX = 14.9
title_block(EVAL_CX, Y, 2.0, 2.0, FWD_FILL, FWD_EDGE, "", None)
ax.text(EVAL_CX, Y + 0.55, "Evaluation", ha="center", va="center",
        fontsize=12.5, fontweight="bold", color=TXT, zorder=4)
ax.text(EVAL_CX, Y - 0.15, "MAE  RMSE\nMAPE · regret\nrecovery time",
        ha="center", va="center", fontsize=9.6, color="#44515F", zorder=4)

# ---- forward arrows ----
arrow(1.75 + 2.9 / 2, Y, POOL_CX - POOL_W / 2, Y)
label((1.75 + 2.9 / 2 + POOL_CX - POOL_W / 2) / 2, Y + 0.42, "stream")
arrow(POOL_CX + POOL_W / 2, Y, CTRL_CX - CTRL_W / 2, Y)
label((POOL_CX + POOL_W / 2 + CTRL_CX - CTRL_W / 2) / 2, Y + 0.42,
      "candidate\nforecasts", size=9.8)
arrow(CTRL_CX + CTRL_W / 2, Y, SERVE_CX - 1.0, Y)
arrow(SERVE_CX + 1.0, Y, EVAL_CX - 1.0, Y)

# ground-truth y_t entering evaluation from the top
arrow(EVAL_CX, 7.9, EVAL_CX, Y + 1.0, color="#44515F", lw=2.0)
label(EVAL_CX, 7.95, r"ground truth $y_t$", size=10, color="#44515F")

# ================= FEEDBACK LOOPS (lower lane) ===========================
# Drift detection box, centered beneath the controller
DRIFT_CX, DRIFT_Y = 9.35, 1.55
title_block(DRIFT_CX, DRIFT_Y, 4.4, 1.5, FB_FILL, FB_EDGE,
            "Concept Drift Detection",
            "ADWIN  +  Page–Hinkley   on residual  $e_t = y_t-\\hat{y}_t$",
            tsize=13, ssize=10.5)

# residual e_t : evaluation -> drift detector
arrow(EVAL_CX, Y - 1.0, EVAL_CX, DRIFT_Y, color=FB_ARROW, lw=2.4)
arrow(EVAL_CX, DRIFT_Y, DRIFT_CX + 4.4 / 2, DRIFT_Y, color=FB_ARROW, lw=2.4)
label((EVAL_CX + DRIFT_CX + 2.2) / 2 + 0.1, DRIFT_Y + 0.34,
      r"residual $e_t$", color=FB_ARROW, size=10)

# drift flag : drift detector -> controller (up)
arrow(DRIFT_CX + 1.1, DRIFT_Y + 0.75, DRIFT_CX + 1.1, Y - CTRL_H / 2,
      color=FB_ARROW, lw=2.4)
label(DRIFT_CX + 1.1, (DRIFT_Y + 0.75 + Y - CTRL_H / 2) / 2, "drift\nflag",
      color=FB_ARROW, size=9.6)

# retrain command : drift/controller -> model pool (long return arrow along lane)
RETRAIN_Y = 0.55
arrow(DRIFT_CX - 4.4 / 2, DRIFT_Y, DRIFT_CX - 4.4 / 2 - 0.4, DRIFT_Y,
      color=FB_ARROW, lw=2.4)
ax.plot([DRIFT_CX - 4.4 / 2 - 0.4, DRIFT_CX - 4.4 / 2 - 0.4],
        [DRIFT_Y, RETRAIN_Y], color=FB_ARROW, lw=2.4, zorder=3)
ax.plot([DRIFT_CX - 4.4 / 2 - 0.4, POOL_CX], [RETRAIN_Y, RETRAIN_Y],
        color=FB_ARROW, lw=2.4, zorder=3)
arrow(POOL_CX, RETRAIN_Y, POOL_CX, Y - POOL_H / 2, color=FB_ARROW, lw=2.4)
label((POOL_CX + DRIFT_CX - 2.6) / 2, RETRAIN_Y + 0.26,
      "retrain command  ·  reset scores  ·  reinstate demoted",
      color=FB_ARROW, size=9.8)

# reward r_t : evaluation -> bandit (curved return, upper)
arrow(EVAL_CX - 1.0, Y - 0.55, CTRL_CX + CTRL_W / 2, Y - 1.02,
      color=CTRL_EDGE, lw=2.4, rad=-0.28)
label((EVAL_CX - 1.0 + CTRL_CX + CTRL_W / 2) / 2, Y - 2.05,
      r"reward $r_t=-|e_t|$", color=CTRL_EDGE, size=10)

# ================= title & legend ========================================
ax.text(8.0, 7.75, "Real-Time Self-Adaptive Agentic Load-Forecasting System",
        ha="center", va="center", fontsize=17, fontweight="bold", color=TXT)

# legend
lx, ly = 0.55, 0.55
ax.add_patch(FancyArrowPatch((lx, ly + 0.35), (lx + 0.9, ly + 0.35),
             arrowstyle="-|>", mutation_scale=16, color=FWD_ARROW, lw=2.4, zorder=5))
ax.text(lx + 1.05, ly + 0.35, "forward forecast path", va="center",
        fontsize=10, color=TXT)
ax.add_patch(FancyArrowPatch((lx, ly - 0.15), (lx + 0.9, ly - 0.15),
             arrowstyle="-|>", mutation_scale=16, color=FB_ARROW, lw=2.4, zorder=5))
ax.text(lx + 1.05, ly - 0.15, "adaptation / feedback loop", va="center",
        fontsize=10, color=TXT)

plt.tight_layout(pad=0.4)
fig.savefig(OUT, bbox_inches="tight", facecolor="white")
print("saved ->", OUT)
