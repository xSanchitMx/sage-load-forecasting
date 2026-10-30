"""
Step 5 tables: MELO alone vs the proposed system (MELO combiner + drift + follow-up
refits) vs the same with the contextual agent, on the test block without and with each
injected shift, plus Diebold-Mariano significance tests (significance.py).

MELO alone is replayed exactly over the saved no-drift pool streams (the pool forecasts do
not depend on the combiner when drift is off): results/forecasts/pool_forecasts_test.json for "none",
results/shift_experiment/<scenario>__blend_nodrift_streams.json for the shifts. The other two come
from results/sage/sage_{,without_agent_}<scenario>_forecasts.json (served forecasts).
Writes results/summaries/step5_sage_vs_melo.md / .json.
"""
from __future__ import annotations
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))   # code/: core modules
import json, os
import numpy as np

import adaptive_baselines as AB
import metrics as M
import significance as S

PROJECT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CODE = os.path.join(PROJECT, "code")
SCEN = ("none", "level", "ramp", "amplitude", "temporary")
METHODS = ("MELO alone", "proposed (no agent)", "proposed + agent")


def load_series():
    eps0 = json.load(open(os.path.join(CODE, "results/baselines/online_combiners.json")))["chosen_params"]["melo"]["eps0"]
    out = {}
    for sc in SCEN:
        base = (os.path.join(CODE, "results/forecasts/pool_forecasts_test.json") if sc == "none" else
                os.path.join(CODE, "results", "shift_experiment", f"{sc}__blend_nodrift_streams.json"))
        B = AB.load(base)
        P = json.load(open(os.path.join(CODE, "results", "sage", f"sage_without_agent_{sc}_forecasts.json")))
        A = json.load(open(os.path.join(CODE, "results", "sage", f"sage_{sc}_forecasts.json")))
        Ares = json.load(open(os.path.join(CODE, "results", "sage", f"sage_{sc}.json")))
        for c, (y, F, L) in B.items():
            yp = np.asarray(P[c]["y"], float)
            assert np.allclose(y, yp), f"{sc}/{c}: series differ"
            out[(sc, c)] = {
                "y": y,
                "MELO alone": AB.melo(y, F, L, eps0=eps0),
                "proposed (no agent)": np.asarray(P[c]["served"], float),
                "proposed + agent": np.asarray(A[c]["served"], float),
                "events": Ares[c].get("_events", []),
            }
    return out


def main():
    data = load_series()
    res = {"accuracy": {}, "significance": {}}
    lines = ["# Step 5: contextual agent (test block, mean over 8 clients)", "",
             "MELO alone = MELO over the pool with weekly refit, no drift. Proposed = MELO "
             "combiner + calibrated drift + follow-up refits. + agent = the contextual serving "
             "agent on top (soft, forget 0.999, temp 0.3; chosen on validation).", ""]
    hdr = "| Method | MAE | RMSE | CV-RMSE % | MAPE % | MAPE 168h after events | MAPE 672h |"
    for sc in SCEN:
        keys = [k for k in data if k[0] == sc]
        lines += [f"## {sc}", "", hdr, "|---|---|---|---|---|---|---|"]
        res["accuracy"][sc] = {}
        for m in METHODS:
            rows = [M.summarize(data[k]["y"], data[k][m]) for k in keys]
            agg = {q: float(np.mean([r[q] for r in rows])) for q in ("MAE", "RMSE", "CV_RMSE", "MAPE")}
            if data[keys[0]]["events"]:
                sh = [M.shift_metrics(data[k]["y"], data[k][m], [], data[k]["events"])[1] for k in keys]
                agg["MAPE_168"] = float(np.mean([s["MAPE_168"] for s in sh]))
                agg["MAPE_672"] = float(np.mean([s["MAPE_672"] for s in sh]))
            res["accuracy"][sc][m] = agg
            f = lambda q: f"{agg[q]:.2f}" if q in agg else "-"
            lines.append(f"| {m} | {f('MAE')} | {f('RMSE')} | {f('CV_RMSE')} | {f('MAPE')} | "
                         f"{f('MAPE_168')} | {f('MAPE_672')} |")
        lines.append("")

    lines += ["## Significance (Diebold-Mariano, Newey-West lag 24 h, 8 clients x 5 scenarios = 40 series)", "",
              "Per pair and loss: series where method 1 has lower loss / significantly lower "
              "(p < 0.05) / significantly higher; mean relative loss difference (negative = "
              "method 1 better); Wilcoxon signed-rank p over the 40 series.", "",
              "| Method 1 vs method 2 | loss | favours 1 | sig. better | sig. worse | mean rel. diff | Wilcoxon p |",
              "|---|---|---|---|---|---|---|"]
    pairs = [("proposed + agent", "MELO alone"), ("proposed (no agent)", "MELO alone"),
             ("proposed + agent", "proposed (no agent)")]
    for m1, m2 in pairs:
        for power, lname in ((1, "absolute"), (2, "squared"), ("ape", "abs. % error")):
            series = {f"{sc}/{c}": (d["y"], d[m1], d[m2]) for (sc, c), d in data.items()}
            per, summ = S.compare(series, power=power)
            res["significance"][f"{m1} vs {m2} ({lname})"] = {"summary": summ, "per_series": per}
            lines.append(f"| {m1} vs {m2} | {lname} | {summ['favour_1']}/{summ['n_series']} | "
                         f"{summ['sig_better_1']} | {summ['sig_worse_1']} | "
                         f"{100 * summ['mean_rel_diff']:+.2f}% | {summ['wilcoxon']['p']:.3g} |")
    lines.append("")
    with open(os.path.join(CODE, "results/summaries/step5_sage_vs_melo.json"), "w") as f:
        json.dump(res, f, indent=2)
    with open(os.path.join(CODE, "results/summaries/step5_sage_vs_melo.md"), "w") as f:
        f.write("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
