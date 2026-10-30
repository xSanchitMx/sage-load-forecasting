"""
Step-3 comparison table: static baselines, retraining policies, existing adaptive
combiners (incl. MELO) and controller variants/ablations, all on the test block.

Reads the result JSONs in code/ and writes results/summaries/step3_baselines_and_ablations.md / .json (mean over clients).
"""
from __future__ import annotations
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))   # code/: core modules
import json, os
import numpy as np

PROJECT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CODE = os.path.join(PROJECT, "code")
METRICS = ("MAE", "RMSE", "CV_RMSE", "MAPE")


def load(name):
    return json.load(open(os.path.join(CODE, name)))


def mean_of(res, key):
    clients = [c for c in res if not c.startswith("_")]
    return {m: float(np.mean([res[c][key][m] for c in clients])) for m in METRICS}


def main():
    base = load("results/baselines/static_baselines.json")
    ctrl = load("results/initial_controller/initial_controller.json")
    nod = load("results/initial_controller/initial_controller_no_drift.json")
    alw = load("results/initial_controller/initial_controller_hourly_refit.json")
    ada = load("results/baselines/online_combiners.json")

    sections = []
    rows = [(n.split(":", 1)[1], mean_of(base, n)) for n in base[next(iter(base))]
            if n.startswith("single:")]
    rows += [("validation-chosen single", mean_of(base, "val_best_single")),
             ("equal-weight ensemble", mean_of(base, "equal_weight_ensemble")),
             ("hindsight-best single (oracle, not deployable)", mean_of(base, "best_static_single"))]
    sections.append(("Static baselines (weekly scheduled refit)", rows))

    sections.append(("Retraining policy (rules-only controller)", [
        ("weekly schedule only (no drift)", mean_of(nod, "adaptive_deterministic")),
        ("weekly schedule + calibrated drift", mean_of(ctrl, "adaptive_deterministic")),
        ("retrain every step", mean_of(alw, "adaptive_deterministic")),
        ("equal-weight ensemble, retrain every step", mean_of(alw, "equal_weight_ensemble")),
    ]))

    for tag, label in (("pool_forecasts_test", "weekly refit"),
                       ("pool_forecasts_test_hourly_refit", "refit every step")):
        per = ada["test"][tag]
        rows = [(f"{m} ({json.dumps(ada['chosen_params'][m])})" if ada["chosen_params"][m] else m,
                 {k: per[m]["_mean"][k] for k in METRICS}) for m in per]
        sections.append((f"Existing adaptive combiners, pool with {label}", rows))

    rows = [("full (k=3, demotion, ADWIN+PH)", mean_of(ctrl, "adaptive_deterministic")),
            ("+ bandit (main result)", mean_of(ctrl, "adaptive_bandit")),
            ("no drift, + bandit", mean_of(nod, "adaptive_bandit"))]
    for f, label in (("results/initial_controller/ablation_no_demotion.json", "no demotion"), ("results/initial_controller/ablation_top1.json", "k = 1"),
                     ("results/initial_controller/ablation_top5.json", "k = 5"), ("results/initial_controller/ablation_adwin_only.json", "ADWIN only"),
                     ("results/initial_controller/ablation_page_hinkley_only.json", "Page-Hinkley only")):
        rows.append((label, mean_of(load(f), "adaptive_deterministic")))
    sections.append(("Proposed controller and ablations (weekly refit + calibrated drift)", rows))

    rows = []
    for f, label in (("results/melo/melo_alone.json", "MELO combiner, no drift (= MELO alone)"),
                     ("results/melo/melo_with_drift.json", "MELO combiner + drift-triggered retraining"),
                     ("results/melo/melo_with_drift_reset_on_alarm.json",
                      "MELO combiner + drift retraining + covariance reset on alarm")):
        if os.path.exists(os.path.join(CODE, f)):
            rows.append((label, mean_of(load(f), "adaptive_deterministic")))
    if rows:
        sections.append(("Controller with the MELO combiner (weekly refit)", rows))

    lines = ["# Step 3 comparison (test block, mean over 8 clients)", ""]
    out = {}
    for title, rows in sections:
        lines += [f"## {title}", "", "| Method | MAE | RMSE | CV-RMSE % | MAPE % |", "|---|---|---|---|---|"]
        for label, r in rows:
            lines.append(f"| {label} | {r['MAE']:.2f} | {r['RMSE']:.2f} | {r['CV_RMSE']:.2f} | {r['MAPE']:.2f} |")
        lines.append("")
        out[title] = {label: r for label, r in rows}
    with open(os.path.join(CODE, "results/summaries/step3_baselines_and_ablations.json"), "w") as f:
        json.dump(out, f, indent=2)
    with open(os.path.join(CODE, "results/summaries/step3_baselines_and_ablations.md"), "w") as f:
        f.write("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
