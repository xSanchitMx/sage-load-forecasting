"""
Module 5 - operational summary: accuracy alongside switching frequency, retraining
frequency and compute cost, for every method, from the latest
results/initial_controller/initial_controller.json and results/baselines/static_baselines.json.

Writes results/summaries/ops_summary.json and results/summaries/ops_summary.md (mean over clients; rates per week of test
data; ms/step is mean wall-clock per hourly step under the same parallel-worker load).
"""
from __future__ import annotations
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))   # code/: core modules
import json, os
import numpy as np

PROJECT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CODE = os.path.join(PROJECT, "code")


def main():
    ctrl = json.load(open(os.path.join(CODE, "results/initial_controller/initial_controller.json")))
    base = json.load(open(os.path.join(CODE, "results/baselines/static_baselines.json")))
    clients = [c for c in ctrl if not c.startswith("_")]
    weeks = {c: ctrl[c]["_n_steps"] / 168.0 for c in clients}
    mean = lambda xs: float(np.mean(xs))

    rows = {}
    # static strategies: no switching, scheduled refits only
    single_names = [k.split(":", 1)[1] for k in base[clients[0]] if k.startswith("single:")]
    for key, label in ([(f"single:{n}", n) for n in single_names] +
                       [("val_best_single", "val-chosen single"),
                        ("equal_weight_ensemble", "equal-weight ensemble")]):
        rows[label] = {
            "MAPE": mean([base[c][key]["MAPE"] for c in clients]),
            "CV_RMSE": mean([base[c][key]["CV_RMSE"] for c in clients]),
            "switches_per_week": 0.0,
            "refits_per_week": mean([base[c][key]["refits"] / weeks[c] for c in clients]),
            "ms_per_step": mean([base[c][key]["ms_per_step"] for c in clients]),
        }
    for key, label in (("adaptive_deterministic", "controller (deterministic)"),
                       ("adaptive_bandit", "controller (+ bandit)")):
        ops = [ctrl[c][key]["ops"] for c in clients]
        rows[label] = {
            "MAPE": mean([ctrl[c][key]["MAPE"] for c in clients]),
            "CV_RMSE": mean([ctrl[c][key]["CV_RMSE"] for c in clients]),
            "switches_per_week": mean([o["leader_switches_per_week"] for o in ops]),
            "blendset_changes_per_week": mean([o["blendset_changes_per_week"] for o in ops]),
            "arm_switches_per_week": mean([o["arm_switches_per_week"] for o in ops]),
            "drift_per_week": mean([o["drift_events_per_week"] for o in ops]),
            "refits_per_week": mean([o["refits_total_per_week"] for o in ops]),
            "refits_drift_share": mean([o["refits_drift"] / max(1, o["refits_total"]) for o in ops]),
            "ms_per_step": mean([o["ms_per_step"] for o in ops]),
            "control_share": mean([o["control_share"] for o in ops]),
            "ms_per_step_by_phase": {p: mean([o["ms_per_step_by_phase"][p] for o in ops])
                                     for p in ops[0]["ms_per_step_by_phase"]},
        }
    sn = rows["seasonal_naive"]["ms_per_step"]
    pool = mean([base[c]["_ops"]["ms_per_step_pool"] for c in clients])
    for r in rows.values():
        r["cost_vs_pool"] = r["ms_per_step"] / pool

    with open(os.path.join(CODE, "results/summaries/ops_summary.json"), "w") as f:
        json.dump({"clients": clients, "pool_ms_per_step": pool,
                   "seasonal_naive_ms_per_step": sn, "rows": rows}, f, indent=2)

    lines = ["# Operational summary (test block, mean over %d clients)" % len(clients), "",
             "Rates are per week (168 h) of test data. ms/step = mean wall-clock per hourly "
             "step; cost vs pool = relative to running all five models with scheduled "
             "retraining (the equal-weight ensemble).", "",
             "| Method | MAPE % | CV-RMSE % | leader switches/wk | refits/wk | ms/step | cost vs pool |",
             "|---|---|---|---|---|---|---|"]
    for label, r in rows.items():
        lines.append(f"| {label} | {r['MAPE']:.2f} | {r['CV_RMSE']:.2f} | "
                     f"{r['switches_per_week']:.2f} | {r['refits_per_week']:.2f} | "
                     f"{r['ms_per_step']:.2f} | {r['cost_vs_pool']:.2f}x |")
    lines += ["", "## Controller detail", "",
              "| | deterministic | + bandit |", "|---|---|---|"]
    d, b = rows["controller (deterministic)"], rows["controller (+ bandit)"]
    for k, fmt in (("blendset_changes_per_week", "{:.2f}"), ("arm_switches_per_week", "{:.2f}"),
                   ("drift_per_week", "{:.2f}"), ("refits_drift_share", "{:.0%}"),
                   ("control_share", "{:.2%}")):
        lines.append(f"| {k} | {fmt.format(d[k])} | {fmt.format(b[k])} |")
    for p in d["ms_per_step_by_phase"]:
        lines.append(f"| ms/step: {p} | {d['ms_per_step_by_phase'][p]:.2f} | "
                     f"{b['ms_per_step_by_phase'][p]:.2f} |")
    with open(os.path.join(CODE, "results/summaries/ops_summary.md"), "w") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
