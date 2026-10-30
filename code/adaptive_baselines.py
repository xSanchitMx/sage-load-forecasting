"""
Existing adaptive-combination methods as baselines, replayed over the SAME pool forecasts
the controller sees.

With drift detection off, the pool's forecasts do not depend on how they are combined
(retraining is on the fixed schedule only), so replaying a combiner over the saved
per-model streams is exactly equivalent to running it inside the prequential loop. Streams
come from
    run_controller.py --no-drift --no-bandit --streams-out <file>
(validation block for tuning, test block for reporting).

Methods (all strictly online: the forecast at t uses losses up to t-1 only):
  ftl          Follow-the-Leader: serve the model with the lowest cumulative loss so far.
  hedge        Exponentially weighted average forecaster (Hedge / EWA; Littlestone &
               Warmuth 1994, Cesa-Bianchi & Lugosi 2006): w_i ~ exp(-eta * L_i).
  dwm          Dynamic Weighted Majority (Kolter & Maloof 2007), adapted to regression with
               a fixed pool: an expert "errs" when its error exceeds the median error
               across experts at that step; its weight is multiplied by beta and weights
               are renormalised with a floor theta. DWM's expert creation and removal are
               not used, because the pool is fixed.
  mlpol        MLpol (Gaillard, Stoltz & van Erven 2014): parameter-free aggregation by
               positive cumulative pseudo-regrets (squared loss), on the raw pool.
  melo         MELO (Wang, Goude & Yao 2026): MLpol over the raw pool plus 16 multi-scale
               EWLS correction experts (online affine combinations of the pool forecasts
               with an intercept). Only eps0 is tuned on validation, as in the paper.
Losses for ftl/hedge/dwm are scale-free: |y - f_i| / s_t, where s_t is a running (EWMA, 1/168) mean of the
pool's absolute error up to t-1, capped at 10 (as for the drift residual).

Hyper-parameters are chosen on the validation block (lowest mean MAPE over clients) and
then frozen for the test block.
"""
from __future__ import annotations
import argparse, json, os
import numpy as np

import metrics as M
from combiners import MELO, mlpol_weights

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CODE = os.path.join(PROJECT, "code")


def _losses(y, F, alpha=1 / 168, cap=10.0):
    """Scale-free per-model losses, shape (T, N); normalisation uses only the past."""
    T, N = F.shape
    ae = np.abs(y[:, None] - F)
    out = np.empty_like(ae)
    s = None
    for t in range(T):
        out[t] = np.minimum(ae[t] / (s if s else 1.0), cap)
        m = ae[t].mean()
        s = m if s is None else alpha * m + (1 - alpha) * s
    return out


def ftl(y, F, L):
    cum = np.vstack([np.zeros(F.shape[1]), np.cumsum(L, axis=0)[:-1]])
    return F[np.arange(len(y)), np.argmin(cum, axis=1)]


def hedge(y, F, L, eta):
    out = np.empty(len(y))
    logw = np.zeros(F.shape[1])
    for t in range(len(y)):
        w = np.exp(logw - logw.max()); w /= w.sum()
        out[t] = w @ F[t]
        logw -= eta * L[t]
    return out


def dwm(y, F, L, beta, theta=0.01):
    N = F.shape[1]
    out = np.empty(len(y))
    w = np.full(N, 1.0 / N)
    for t in range(len(y)):
        out[t] = w @ F[t]
        errs = L[t] > np.median(L[t])
        w = np.where(errs, w * beta, w); w /= w.sum()
        w = np.maximum(w, theta); w /= w.sum()
    return out


def mlpol(y, F, L):
    """MLpol (Gaillard, Stoltz & van Erven 2014) on the raw pool, squared loss,
    gradient-trick pseudo-regrets. Parameter-free."""
    out = np.empty(len(y))
    R = np.zeros(F.shape[1])
    for t in range(len(y)):
        out[t] = mlpol_weights(R) @ F[t]
        g = 2.0 * (out[t] - y[t])
        R += g * (out[t] - F[t])
    return out


def melo(y, F, L, eps0, gammas=None, scale=None):
    """MELO (Wang, Goude & Yao 2026), replayed with the same online class the controller
    uses (combiners.MELO; see its docstring for the algorithm, the numerical safeguard and
    the per-client scaling)."""
    m = MELO(F.shape[1], eps0=eps0, gammas=gammas, scale=scale)
    out = np.empty(len(y))
    for t in range(len(y)):
        out[t] = m.predict(F[t])
        m.update(y[t])
    return out


GRIDS = {
    "ftl": [{}],
    "hedge": [{"eta": e} for e in (0.0003, 0.001, 0.003, 0.01, 0.03, 0.1, 0.3, 1.0, 3.0)],
    "dwm": [{"beta": b} for b in (0.1, 0.2, 0.3, 0.5, 0.7, 0.9, 0.95, 0.99)],
    "mlpol": [{}],
    # MELO's only validated parameter (their B.5 sweeps 1e-13..1e-5; widened here because
    # the per-client scaling changes the magnitude of P)
    "melo": [{"eps0": e} for e in (1e-13, 1e-11, 1e-9, 1e-8, 1e-7, 1e-6, 1e-5, 1e-4, 1e-3, 1e-2)],
}
FN = {"ftl": ftl, "hedge": hedge, "dwm": dwm,
      "mlpol": mlpol, "melo": melo}


def load(path):
    S = json.load(open(path))
    out = {}
    for c, d in S.items():
        names = list(d["per_model"])
        y = np.asarray(d["y"], float)
        F = np.column_stack([np.asarray(d["per_model"][n], float) for n in names])
        out[c] = (y, F, _losses(y, F))
    return out


def run(method, params, data):
    return {c: FN[method](y, F, L, **params) for c, (y, F, L) in data.items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--val", default=os.path.join(CODE, "results/forecasts/pool_forecasts_val.json"))
    ap.add_argument("--test", nargs="+", default=[os.path.join(CODE, "results/forecasts/pool_forecasts_test.json")],
                    help="one or more test stream files (e.g. scheduled and always-retrain)")
    ap.add_argument("--out", default=os.path.join(CODE, "results/baselines/online_combiners.json"))
    args = ap.parse_args()

    val = load(args.val)
    chosen, tuning = {}, {}
    print("=== tuning on validation (mean MAPE over clients) ===")
    for method, grid in GRIDS.items():
        scores = []
        for params in grid:
            fc = run(method, params, val)
            scores.append(float(np.mean([M.mape(val[c][0], fc[c]) for c in val])))
            print(f"  {method:12s} {json.dumps(params):32s} val MAPE {scores[-1]:.3f}", flush=True)
        i = int(np.argmin(scores))
        chosen[method] = grid[i]
        tuning[method] = [{"params": p, "val_MAPE": s} for p, s in zip(grid, scores)]
        print(f"  -> {method}: {json.dumps(grid[i])}  (val MAPE {scores[i]:.3f})\n")

    results = {"chosen_params": chosen, "tuning": tuning, "test": {}}
    for path in args.test:
        test = load(path)
        tag = os.path.splitext(os.path.basename(path))[0]
        per = {}
        print(f"=== test: {tag} (mean over {len(test)} clients) ===")
        for method, params in chosen.items():
            fc = run(method, params, test)
            per[method] = {c: M.summarize(test[c][0], fc[c]) for c in test}
            agg = {k: float(np.mean([per[method][c][k] for c in test]))
                   for k in ("MAE", "RMSE", "CV_RMSE", "MAPE", "DirAcc")}
            per[method]["_mean"] = agg
            print(f"  {method:12s} MAE {agg['MAE']:7.2f}  RMSE {agg['RMSE']:7.2f}  "
                  f"CV-RMSE {agg['CV_RMSE']:5.2f}%  MAPE {agg['MAPE']:5.2f}%", flush=True)
        results["test"][tag] = per
    with open(args.out, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nsaved -> {args.out}")


if __name__ == "__main__":
    main()
