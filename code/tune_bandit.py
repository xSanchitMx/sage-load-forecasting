"""
Offline tuning of the Algorithm 2 bandit (Discounted-UCB1) on the validation block.

Replays the bandit over per-step streams saved by
    run_controller.py --block val --no-bandit --streams-out results/forecasts/initial_controller_forecasts_val.json
Each stream holds, per hour, the truth y, the deterministic blend and the current best
model's forecast; the bandit picks one of the two each step, exactly as in controller.py.
The replay ignores the bandit's second-order effect on drift-triggered retraining
(the served residual feeds the drift monitor), so chosen values are confirmed by a full
controller run afterwards.
"""
from __future__ import annotations
import argparse, json, math, os
import numpy as np

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def replay(y, blend, best, gamma, c, alpha=1 / 168):
    """Return (served forecasts, share of steps on arm 1 = force_best)."""
    N, G = [0.0, 0.0], [0.0, 0.0]
    scale = None
    served, arms = np.empty(len(y)), np.empty(len(y), dtype=int)
    for t in range(len(y)):
        if N[0] <= 0 or N[1] <= 0:
            arm = 0 if N[0] <= 0 else 1
        else:
            tot = N[0] + N[1]
            sc = [G[i] / N[i] + c * math.sqrt(math.log(tot) / N[i]) for i in (0, 1)]
            arm = int(np.argmax(sc))
        yhat = blend[t] if arm == 0 else best[t]
        ae = abs(y[t] - yhat)
        r = -ae / (scale if scale else 1.0)
        for i in (0, 1):
            N[i] *= gamma; G[i] *= gamma
        N[arm] += 1.0; G[arm] += r
        scale = ae if scale is None else alpha * ae + (1 - alpha) * scale
        served[t], arms[t] = yhat, arm
    return served, float(arms.mean())


def mape(y, yhat):
    m = y > 1e-6
    return float(np.mean(np.abs((y[m] - yhat[m]) / y[m])) * 100)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--streams", default=os.path.join(PROJECT, "code", "results/forecasts/initial_controller_forecasts_val.json"))
    ap.add_argument("--out", default=os.path.join(PROJECT, "code", "results/tuning/bandit_tuning.json"))
    args = ap.parse_args()
    S = json.load(open(args.streams))
    S = {c: {k: np.asarray(v, dtype=float) for k, v in d.items()} for c, d in S.items()}

    ref = {"blend_only": np.mean([mape(d["y"], d["blend"]) for d in S.values()]),
           "best_only": np.mean([mape(d["y"], d["best_pred"]) for d in S.values()]),
           "oracle_per_step": np.mean([mape(d["y"], np.where(
               np.abs(d["y"] - d["blend"]) <= np.abs(d["y"] - d["best_pred"]),
               d["blend"], d["best_pred"])) for d in S.values()])}
    print("reference (mean val MAPE over clients):",
          {k: round(v, 3) for k, v in ref.items()})

    grid = []
    for gamma in (0.95, 0.99, 0.995, 0.999):
        for c in (0.02, 0.05, 0.1, 0.2, 0.5, 1.0):
            m, share = [], []
            for d in S.values():
                served, sh = replay(d["y"], d["blend"], d["best_pred"], gamma, c)
                m.append(mape(d["y"], served)); share.append(sh)
            grid.append({"gamma": gamma, "c": c, "MAPE": float(np.mean(m)),
                         "force_best_share": float(np.mean(share))})
            print(f"  gamma {gamma:<6} c {c:<5} MAPE {np.mean(m):.3f}  "
                  f"force_best {np.mean(share):.2f}", flush=True)
    best = min(grid, key=lambda g: g["MAPE"])
    print("best:", best)
    with open(args.out, "w") as f:
        json.dump({"reference": ref, "grid": grid, "best": best}, f, indent=2)
    print(f"saved -> {args.out}")


if __name__ == "__main__":
    main()
