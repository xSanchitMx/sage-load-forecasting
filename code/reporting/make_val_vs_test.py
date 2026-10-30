"""
Figure 6: validation-MAPE vs test-MAPE for every (client, model) pair.

Points on the diagonal mean validation performance predicted test performance;
points far above it are models that looked good on validation and then failed on
test - the fragility that makes 'pick the validation-best single model' risky.
The Holt-Winters / MT_269 point is the headline example (won validation, ~42% on test).

Runs a validation-block prequential pass per client (~5 min), then draws the scatter.
"""
from __future__ import annotations
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))   # code/: core modules
import os, json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from data_pipeline import prepare
from run_baselines import run_client
import metrics as M

PROJECT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FIGDIR = os.path.join(PROJECT, "paper")

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 11, "axes.titlesize": 12.5,
    "axes.labelsize": 11, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.alpha": 0.22, "grid.linewidth": 0.6,
    "figure.dpi": 150, "savefig.dpi": 150, "savefig.bbox": "tight", "legend.frameon": False,
})
C_HW = "#D55E00"      # Holt-Winters (the fragile one)
C_OTHER = "#8fa3b0"   # other models
MODELS = ["seasonal_naive", "holt_winters", "sarima", "lightgbm", "online_linear"]

baseline = json.load(open(os.path.join(PROJECT, "code", "results/baselines/static_baselines.json")))
data = prepare(n_clients=len(baseline))

pts = []   # (val_mape, test_mape, model, client)
for cid, cs in data.items():
    yv, predsv, _ = run_client(cs, block="val", verbose=False)
    for m in MODELS:
        vm = M.mape(yv, predsv[m])
        tm = baseline[cid][f"single:{m}"]["MAPE"]
        pts.append((vm, tm, m, cid))
        print(f"{cid:8s} {m:15s} val {vm:8.2f}%  test {tm:8.2f}%", flush=True)

json.dump([{"val": v, "test": t, "model": m, "client": c} for v, t, m, c in pts],
          open(os.path.join(PROJECT, "code", "results/summaries/val_vs_test.json"), "w"), indent=2)

# ---- plot (clip to a readable window; note anything off-scale) ----
XMAX, YMAX = 45.0, 50.0
shown = [(v, t, m, c) for v, t, m, c in pts if v <= XMAX and t <= YMAX]
omitted = len(pts) - len(shown)

fig, ax = plt.subplots(figsize=(7.0, 6.2))
lim = max(XMAX, YMAX)
ax.plot([0, lim], [0, lim], color="#999", lw=1.2, ls="--", label="val = test (ideal)")
for v, t, m, c in shown:
    col = C_HW if m == "holt_winters" else C_OTHER
    ax.scatter(v, t, s=55, color=col, edgecolor="white", linewidth=0.7, zorder=3)
# annotate the headline failure
for v, t, m, c in shown:
    if m == "holt_winters" and c == "MT_269":
        ax.annotate("Holt-Winters on MT_269\n(best on validation, ~42% on test)",
                    xy=(v, t), xytext=(v + 8, t - 6), fontsize=9.5, color="#333",
                    arrowprops=dict(arrowstyle="->", color="#666", lw=1.0))
# legend proxies
ax.scatter([], [], s=55, color=C_HW, edgecolor="white", label="Holt-Winters")
ax.scatter([], [], s=55, color=C_OTHER, edgecolor="white", label="other models")
ax.set_xlabel("validation-block MAPE (%)")
ax.set_ylabel("test-block MAPE (%)")
ax.set_title("Validation error does not always predict test error")
ax.set_xlim(0, XMAX); ax.set_ylim(0, YMAX)
ax.legend(loc="lower right")
if omitted:
    ax.text(0.02, 0.98, f"{omitted} extreme point(s) off-scale (SARIMA validation divergence)",
            transform=ax.transAxes, va="top", fontsize=8.5, color="#888")
fig.savefig(os.path.join(FIGDIR, "fig6_val_vs_test.png"))
plt.close(fig)
print("saved -> fig6_val_vs_test.png   (omitted off-scale:", omitted, ")")
