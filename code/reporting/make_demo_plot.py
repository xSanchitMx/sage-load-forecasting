"""
Demo figure for the adaptive controller, from results/initial_controller/initial_controller_hourly_<client>.json.

Three stacked panels:
  (1) served forecast vs actual over a two-week slice;
  (2) rolling MAE of the controller vs the best single model in hindsight, with
      drift-detection events marked;
  (3) which pool model the controller rates best (lowest EWMA error) over time,
      showing that the served mixture tracks a shifting winner.
"""
from __future__ import annotations
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))   # code/: core modules
import json, os, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import metrics as M

PROJECT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main(client="MT_132"):
    diag_path = os.path.join(PROJECT, "code", f"controller_diag_{client}.json")
    if not os.path.exists(diag_path):
        print("missing", diag_path); sys.exit(1)
    with open(diag_path) as f:
        D = json.load(f)

    y = np.array(D["y_true"])
    served = np.array(D["served_det"])
    per_model = {k: np.array(v) for k, v in D["per_model"].items()}
    best_per_step = D["best_per_step"]
    drift = D["drift_points"]

    best_name = min(per_model, key=lambda k: np.abs(y - per_model[k]).sum())
    best_fc = per_model[best_name]

    roll_ctrl = M.rolling_mae(np.abs(y - served), window=168)
    roll_best = M.rolling_mae(np.abs(y - best_fc), window=168)

    names = list(per_model.keys())
    name_to_i = {n: i for i, n in enumerate(names)}
    best_idx = np.array([name_to_i.get(b, -1) for b in best_per_step], dtype=float)
    best_idx[best_idx < 0] = np.nan

    STEEL, RUST, GREEN = "#3b6ea5", "#b5533b", "#4a8a5c"
    fig, ax = plt.subplots(3, 1, figsize=(11, 9), height_ratios=[1.1, 1.0, 0.8])

    # (1) two-week slice
    sl = slice(0, min(336, len(y)))
    ax[0].plot(np.arange(sl.stop), y[sl], color="#555", lw=1.3, label="actual")
    ax[0].plot(np.arange(sl.stop), served[sl], color=STEEL, lw=1.3, label="controller (served)")
    ax[0].set_title(f"{client}: served forecast vs actual (first two weeks of test block)")
    ax[0].set_ylabel("load (kW)")
    ax[0].legend(loc="upper right", frameon=False)

    # (2) rolling MAE, controller vs best single, with drift events
    ax[1].plot(roll_best, color="#999", lw=1.2, label=f"best single in hindsight ({best_name})")
    ax[1].plot(roll_ctrl, color=STEEL, lw=1.4, label="adaptive controller")
    for i, dp in enumerate(drift):
        ax[1].axvline(dp, color=RUST, alpha=0.25, lw=1.0,
                      label="drift detected" if i == 0 else None)
    ax[1].set_title("Rolling MAE (168 h window): controller tracks the best model, drift triggers retraining")
    ax[1].set_ylabel("rolling MAE (kW)")
    ax[1].legend(loc="upper right", frameon=False)

    # (3) best-rated model over time
    ax[2].plot(best_idx, color=GREEN, lw=0.8, drawstyle="steps-post")
    ax[2].set_yticks(range(len(names)))
    ax[2].set_yticklabels(names)
    ax[2].set_title("Model the controller currently rates best (lowest EWMA error)")
    ax[2].set_xlabel("hours into test block")
    ax[2].set_ylim(-0.5, len(names) - 0.5)

    for a in ax:
        a.grid(True, alpha=0.2)
    fig.tight_layout()
    out = os.path.join(PROJECT, "paper", "controller_demo.png")
    fig.savefig(out, dpi=150)
    print("saved ->", out)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "MT_132")
