"""Per-model and served relative error (MAE / mean load) by week around the first shift event,
and how a range of drift-detector settings react. Input: --no-drift streams over the first
2,700 test steps (event 1 at step 2016)."""
import json, sys, os, numpy as np
sys.path.insert(0, os.getcwd())
from tune_drift import normalised_residuals
from drift import DriftMonitor
E = 2016
for path in sys.argv[1:]:
    S = json.load(open(path)); print(f"\n##### {os.path.basename(path)}")
    rows = {}
    for c, d in S.items():
        y = np.array(d["y"]); fc = {"served": np.array(d["blend"]), **{k: np.array(v) for k, v in d["per_model"].items()}}
        for k, f in fc.items():
            rel = [np.mean(np.abs(y[a:a+168]-f[a:a+168]))/np.mean(y[a:a+168]) for a in (E-168, E, E+168, E+336, E+504)]
            rows.setdefault(k, []).append(rel)
    print("relative MAE (% of mean load), mean over clients: week -1 | wk 0 | wk 1 | wk 2 | wk 3 after event")
    for k, v in rows.items():
        print(f"  {k:15s} " + "  ".join(f"{x*100:5.2f}" for x in np.mean(v, axis=0)))
    print("detector alarms in [E, E+336) per client (sparse=default, medium, frequent):")
    for name, kw in (("sparse", {}), ("medium", dict(ph_threshold=25, adwin_delta=0.01)),
                     ("frequent", dict(ph_threshold=10, adwin_delta=0.05))):
        hits, fa = [], []
        for c, d in S.items():
            y = np.array(d["y"]); z = normalised_residuals(y, np.array(d["blend"]))
            m = DriftMonitor(**kw)
            for v in z: m.step(float(v))
            p = np.array(m.drift_points)
            h = p[(p >= E) & (p < E + 336)]
            hits.append(int(h[0] - E) if h.size else None)
            fa.append(int(((p < E) | (p >= E + 336)).sum()))
        print(f"  {name:9s} delay per client {hits}  false alarms elsewhere (2,700 h) {fa}")
