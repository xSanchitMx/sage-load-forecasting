"""
Prequential baseline runner (Modules 2 + 5, no controller yet).

Runs each pool model and four baselines over the test block in a strict
predict -> observe -> update loop, and reports the accuracy metrics. This produces the
first real numbers for Table 1 of the Results section and validates the whole pipeline
before drift detection and the controller are added.

Baselines:
  (a) best single static model  - each pool model run standalone (self-updating members
      update online; batch members are refit only on the weekly schedule)
  (b) equal-weight ensemble     - unweighted mean of all pool models
  (c) always-retrain            - batch models refit every step (expensive)
  (d) scheduled-retrain (168h)  - batch models refit weekly  [this is the default below]
"""
from __future__ import annotations
import os
os.environ.setdefault("OMP_NUM_THREADS", "1")   # one thread per worker; clients run in parallel
import argparse, time, json
from concurrent.futures import ProcessPoolExecutor
import numpy as np

from data_pipeline import prepare
from models import build_pool
import metrics as M

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run_client(cs, block="test", retrain_mode="scheduled", schedule=168,
               include_online=True, max_steps=None, verbose=False):
    """
    Run all pool models prequentially over one split block for one client.
    block: which split to run over ('test' or 'val').
    retrain_mode: 'scheduled' (weekly), 'always' (every step), or 'none'.
    Returns (y_true, {model_name: forecasts}, timing_seconds, ops) where ops holds
    per-model wall-clock seconds and refit counts (instrumentation only).
    """
    y = cs.y.values.astype(float)
    feats = cs.feats
    pool = build_pool(y, feats, include_online=include_online)
    lo, hi = cs.splits[block]
    if max_steps:
        hi = min(hi, lo + max_steps)

    # warm-start: fit batch models once at the start of the test block
    for m in pool:
        if m.retrainable:
            m.retrain(lo)
    # warm-up: pre-fit self-updating incremental models on recent history so they do
    # not enter the test block cold (which causes SGD divergence)
    warm_from = max(200, lo - 24 * 90)   # up to ~90 days of history
    for m in pool:
        if getattr(m, "self_updating", False):
            for s in range(warm_from, lo):
                m.update(s, y[s])

    y_true = []
    preds = {m.name: [] for m in pool}
    last_refit = {m.name: lo for m in pool}
    model_sec = {m.name: 0.0 for m in pool}
    refits = {m.name: 0 for m in pool}
    clock = time.perf_counter

    def timed(m, fn, *a):
        c = clock()
        out = fn(*a)
        model_sec[m.name] += clock() - c
        return out

    t0 = clock()
    for t in range(lo, hi):
        for m in pool:
            preds[m.name].append(max(0.0, timed(m, m.predict, t)))   # load is non-negative
        yt = y[t]
        y_true.append(yt)
        for m in pool:
            timed(m, m.update, t, yt)
        # retraining policy for batch models
        if retrain_mode == "always":
            for m in pool:
                if m.retrainable:
                    timed(m, m.retrain, t + 1)
                    refits[m.name] += 1
        elif retrain_mode == "scheduled":
            for m in pool:
                if m.retrainable and (t + 1 - last_refit[m.name]) >= schedule:
                    timed(m, m.retrain, t + 1)
                    refits[m.name] += 1
                    last_refit[m.name] = t + 1
        if verbose and (t - lo) % 2000 == 0:
            print(f"    step {t-lo}/{hi-lo}", flush=True)

    elapsed = time.perf_counter() - t0
    y_true = np.array(y_true)
    preds = {k: np.array(v) for k, v in preds.items()}
    return y_true, preds, elapsed, {"model_sec": model_sec, "refits": refits}


def evaluate_client(cs, **kw):
    y, preds, elapsed, ops = run_client(cs, **kw)
    per_model = {k: v for k, v in preds.items()}
    results = {}

    # (a) each single model
    for name, fc in preds.items():
        results[f"single:{name}"] = M.summarize(y, fc, per_model)
    # best single by hindsight (lowest MAE over the test block itself - an oracle choice)
    best_name = min(preds, key=lambda k: M.mae(y, preds[k]))
    results["best_static_single"] = dict(results[f"single:{best_name}"], which=best_name)
    # validation-best single: pick the model with the lowest MAE on the validation block
    # (no test-block knowledge - the realistic deploy-time choice), report its TEST metrics.
    val_kw = {k: v for k, v in kw.items() if k not in ("block", "verbose")}
    yv, predsv, _, _ = run_client(cs, block="val", verbose=False, **val_kw)
    val_best = min(predsv, key=lambda k: M.mae(yv, predsv[k]))
    results["val_best_single"] = dict(results[f"single:{val_best}"], which=val_best)
    # (b) equal-weight ensemble
    ens = np.mean(np.stack(list(preds.values())), axis=0)
    results["equal_weight_ensemble"] = M.summarize(y, ens, per_model)

    results["_timing_sec"] = elapsed
    # compute cost of each strategy: a single model costs its own time; the equal-weight
    # ensemble runs (and pays for) the whole pool
    n = len(y)
    ms = {k: v / n * 1000 for k, v in ops["model_sec"].items()}
    results["_ops"] = {"ms_per_step_by_model": ms,
                       "ms_per_step_pool": float(sum(ms.values())),
                       "refits_by_model": ops["refits"]}
    for name in preds:
        results[f"single:{name}"]["ms_per_step"] = ms[name]
        results[f"single:{name}"]["refits"] = ops["refits"][name]
    for key in ("best_static_single", "val_best_single"):
        results[key]["ms_per_step"] = ms[results[key]["which"]]
        results[key]["refits"] = ops["refits"][results[key]["which"]]
    results["equal_weight_ensemble"]["ms_per_step"] = float(sum(ms.values()))
    results["equal_weight_ensemble"]["refits"] = int(sum(ops["refits"].values()))
    results["_n_steps"] = int(len(y))
    return results


def _job(job):
    cid, cs, kw = job
    print(f"[{cid}] running test block ...", flush=True)
    res = evaluate_client(cs, **kw)
    b = res["best_static_single"]
    ew = res["equal_weight_ensemble"]
    print(f"[{cid}] best single = {b['which']:14s} MAE {b['MAE']:.1f} | "
          f"equal-ens MAE {ew['MAE']:.1f} | {res['_timing_sec']:.1f}s "
          f"for {res['_n_steps']} steps", flush=True)
    return cid, res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--clients", type=int, default=8)
    ap.add_argument("--max-steps", type=int, default=None,
                    help="cap test steps per client (for a quick smoke run)")
    ap.add_argument("--retrain", default="scheduled",
                    choices=["scheduled", "always", "none"])
    ap.add_argument("--no-online", action="store_true")
    ap.add_argument("--workers", type=int, default=4, help="clients run in parallel")
    ap.add_argument("--out", default=os.path.join(PROJECT, "code", "results/baselines/static_baselines.json"))
    args = ap.parse_args()

    data = prepare(n_clients=args.clients)
    jobs = [(cid, cs, dict(retrain_mode=args.retrain, include_online=not args.no_online,
                           max_steps=args.max_steps))
            for cid, cs in data.items()]
    all_results = {}
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        for cid, res in ex.map(_job, jobs):
            all_results[cid] = res

    # aggregate mean across clients for the headline methods
    def agg(method, metric):
        vals = [all_results[c][method][metric] for c in all_results
                if method in all_results[c] and metric in all_results[c][method]]
        return float(np.mean(vals)) if vals else float("nan")

    print("\n=== AGGREGATE (mean over clients) ===")
    for method in ["best_static_single", "val_best_single", "equal_weight_ensemble"]:
        print(f"  {method:24s} MAE {agg(method,'MAE'):8.2f}  RMSE {agg(method,'RMSE'):8.2f}  "
              f"MAPE {agg(method,'MAPE'):6.2f}  DirAcc {agg(method,'DirAcc'):5.1f}")

    with open(args.out, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\nsaved -> {args.out}")


if __name__ == "__main__":
    main()
