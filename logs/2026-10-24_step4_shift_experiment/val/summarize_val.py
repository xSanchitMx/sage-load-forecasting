"""Step-4 validation summary: per variant, mean over 8 clients of overall MAPE / CV-RMSE per
scenario, the mean over the five scenarios (the selection rule), and the post-shift MAPE.
Run from code/."""
import json, glob, os, numpy as np
SC = ["level", "ramp", "amplitude", "temporary", "none"]
VAR = ["blend_nodrift", "blend_drift", "blend_resp", "blend_resp_nofast", "blend_follow",
       "melo_nodrift", "melo_drift", "melo_resp", "melo_resp_cov", "melo_follow"]
def load(sc, v):
    p = f"step4_val/{sc}__{v}.json"
    if not os.path.exists(p): return None
    d = json.load(open(p)); cs = [c for c in d if not c.startswith("_")]
    r = [d[c]["adaptive_deterministic"] for c in cs]
    m = lambda k: float(np.mean([x[k] for x in r]))
    sh = [x["shift"] for x in r if "shift" in x]
    return {"MAPE": m("MAPE"), "CV": m("CV_RMSE"),
            "M168": float(np.mean([s["MAPE_168"] for s in sh])) if sh else np.nan,
            "M672": float(np.mean([s["MAPE_672"] for s in sh])) if sh else np.nan}
for metric, title in (("MAPE", "overall MAPE"), ("CV", "overall CV-RMSE"),
                      ("M168", "MAPE over 168 h after events"), ("M672", "MAPE over 672 h after events")):
    print(f"\n=== val, {title} (mean over 8 clients) ===")
    print(f"{'variant':20s}" + "".join(f"{s:>11s}" for s in SC) + f"{'mean':>9s}")
    for v in VAR:
        vals = [load(s, v) for s in SC]
        xs = [x[metric] if x else np.nan for x in vals]
        print(f"{v:20s}" + "".join(f"{x:11.3f}" for x in xs) + f"{np.nanmean(xs):9.3f}")
