"""
Step 4 tables: how every method copes with the injected shifts (shifts.py).

Reads results/shift_experiment/<scenario>__<variant>.json (run_step4.sh, run_step4_final.sh) and replays the existing
adaptive combiners (FTL, Hedge, DWM, MLpol, MELO; hyper-parameters frozen from
results/baselines/online_combiners.json) over the saved no-drift pool forecasts of each scenario,
both with the weekly refit and with a daily refit. Writes results/summaries/step4_shift_experiment.md / .json.
"""
from __future__ import annotations
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))   # code/: core modules
import json, os
import numpy as np

import adaptive_baselines as AB
import metrics as M
from shifts import SCENARIOS

PROJECT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CODE = os.path.join(PROJECT, "code")
R = os.path.join(CODE, "results", "shift_experiment")

VARIANTS = [  # (file variant, result key, label)
    ("blend_nodrift", "equal_weight_ensemble", "equal-weight ensemble (weekly refit)"),
    ("daily_retrain", "equal_weight_ensemble", "equal-weight ensemble (daily refit)"),
    ("blend_nodrift", "adaptive_deterministic", "blend controller, no drift"),
    ("blend_drift", "adaptive_deterministic", "blend controller + drift (old response)"),
    ("blend_drift_follow", "adaptive_deterministic", "blend controller + drift + follow-up refits"),
    ("daily_retrain", "adaptive_deterministic", "blend controller, daily refit"),
    ("melo_nodrift", "adaptive_deterministic", "MELO alone (= MELO combiner, no drift)"),
    ("melo_drift", "adaptive_deterministic", "MELO combiner + drift (old response)"),
    ("melo_drift_follow", "adaptive_deterministic", "MELO combiner + drift + follow-up refits (proposed)"),
]
COLS = ("MAPE", "CV_RMSE", "MAPE_168", "MAPE_672", "ratio_168", "recovery_median",
        "not_recovered", "detected", "delay_median", "false_alarms_per_week", "refits_per_week")


def _load(path):
    return json.load(open(path)) if os.path.exists(path) else None


def _row(per_client):
    """Mean over clients of overall + shift metrics; counts are summed."""
    out = {}
    for k in ("MAPE", "CV_RMSE"):
        out[k] = float(np.mean([p["MAPE" if k == "MAPE" else "CV_RMSE"] for p in per_client]))
    sh = [p.get("shift") for p in per_client]
    shift_keys = ("MAPE_168", "MAPE_672", "ratio_168", "recovery_median", "delay_median",
                  "false_alarms_per_week")
    if any(s is None for s in sh):          # no-shift reference runs
        out.update({k: float("nan") for k in shift_keys})
        out["not_recovered"], out["detected"] = "-", "-"
    else:
        for k in shift_keys:
            out[k] = float(np.nanmean([s[k] for s in sh]))
        out["not_recovered"] = int(sum(s["not_recovered"] for s in sh))
        out["detected"] = f"{sum(s['detected'] for s in sh)}/{sum(s['n_events'] for s in sh)}"
    rpw = [p["ops"]["refits_total_per_week"] for p in per_client if "ops" in p]
    out["refits_per_week"] = float(np.mean(rpw)) if rpw else float("nan")
    return out


# no-shift runs made earlier (step 2b / 3 / MELO combiner), reused for the "none" table
NONE_EXTRA = {"blend_nodrift": "results/initial_controller/initial_controller_no_drift.json",
              "melo_nodrift": "results/melo/melo_alone.json",
              "melo_drift": "results/melo/melo_with_drift.json"}


def controller_rows(scenario):
    rows = {}
    for variant, key, label in VARIANTS:
        res = _load(os.path.join(R, f"{scenario}__{variant}.json"))
        if res is None and scenario == "none" and variant in NONE_EXTRA \
                and key == "adaptive_deterministic":
            res = _load(os.path.join(CODE, NONE_EXTRA[variant]))
        if res is None:
            continue
        cs = [c for c in res if not c.startswith("_")]
        if key not in res[cs[0]]:
            continue
        per = [res[c][key] for c in cs]
        if key == "equal_weight_ensemble":
            rpw = [res[c]["adaptive_deterministic"]["ops"]["refits_total_per_week"] for c in cs]
            per = [dict(p, ops={"refits_total_per_week": r}) for p, r in zip(per, rpw)]
        rows[label] = _row(per)
    return rows


def combiner_rows(scenario, chosen):
    rows = {}
    for variant, tag in (("blend_nodrift", "weekly refit"), ("daily_retrain", "daily refit")):
        spath = os.path.join(R, f"{scenario}__{variant}_streams.json")
        res = _load(os.path.join(R, f"{scenario}__{variant}.json"))
        if res is None or not os.path.exists(spath):
            continue
        data = AB.load(spath)
        for method, params in chosen.items():
            per = []
            for c, (y, F, L) in data.items():
                fc = AB.FN[method](y, F, L, **params)
                p = M.summarize(y, fc)
                _, p["shift"] = M.shift_metrics(y, fc, [], res[c]["_events"])
                p["ops"] = {"refits_total_per_week":
                            res[c]["adaptive_deterministic"]["ops"]["refits_total_per_week"]}
                per.append(p)
            rows[f"{method} ({tag})"] = _row(per)
    return rows


def fmt(v):
    if isinstance(v, str):
        return v
    return "-" if not np.isfinite(v) else f"{v:.2f}"


def main():
    chosen = json.load(open(os.path.join(CODE, "results/baselines/online_combiners.json")))["chosen_params"]
    out = {}
    lines = ["# Step 4: injected demand shifts (test block, mean over 8 clients)", "",
             "Two events per client per scenario (shifts.py). MAPE_168 / MAPE_672 = MAPE over the "
             "168 h / 672 h after each event; ratio_168 = MAE in the week after / week before "
             "(a +30% level shift alone gives ~1.3). Recovery = hours until the relative error "
             "is back within 25% of its pre-event level (capped at 672 h; 'not rec.' counts "
             "events that never got there). Detection = alarms within 336 h of an event.", ""]
    hdr = ("| Method | MAPE | CV-RMSE | MAPE 168h | MAPE 672h | ratio 168h | recovery h | "
           "not rec. | detected | delay h | false/wk | refits/wk |")
    for sc in SCENARIOS + ("none",):
        rows = controller_rows(sc)
        if sc != "none":
            rows.update(combiner_rows(sc, chosen))
        if not rows:
            continue
        out[sc] = rows
        lines += [f"## {sc}", "", hdr, "|" + "---|" * 12]
        for label, r in rows.items():
            lines.append(f"| {label} | " + " | ".join(fmt(r[k]) for k in COLS) + " |")
        lines.append("")
    with open(os.path.join(CODE, "results/summaries/step4_shift_experiment.json"), "w") as f:
        json.dump(out, f, indent=2)
    with open(os.path.join(CODE, "results/summaries/step4_shift_experiment.md"), "w") as f:
        f.write("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
