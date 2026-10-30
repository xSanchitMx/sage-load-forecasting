"""Replay the drift detectors on the served-residual stream of MT_132 (from
controller_diag_MT_132.json): which detector fires, and how alarm counts depend on the
Page-Hinkley threshold. Run from code/."""
import json, sys
import numpy as np
from river import drift
d = json.load(open("controller_diag_MT_132.json"))
y = np.array(d["y_true"]); s = np.array(d["served_det"])
ae = np.abs(y - s); scale = None; z = []
for a in ae:                               # same normalisation as controller.py
    z.append(a / (scale if scale else 1.0))
    scale = a if scale is None else a / 168 + (1 - 1 / 168) * scale
z = np.array(z)
print("normalised residual: mean %.2f  median %.2f  p95 %.2f  max %.1f" %
      (z.mean(), np.median(z), np.percentile(z, 95), z.max()))

def count(det):
    pts = []
    for i, v in enumerate(z):
        det.update(v)
        if det.drift_detected:
            pts.append(i)
    g = np.diff(pts)
    return len(pts), (int(np.median(g)) if len(g) else None), (round(float(np.mean(g == 168)), 2) if len(g) else None)

print("ADWIN delta 0.002          :", count(drift.ADWIN(delta=0.002)))
for thr in (3, 10, 25, 50, 100, 200):
    print(f"PageHinkley threshold {thr:>4} :", count(drift.PageHinkley(min_instances=168, delta=0.01,
                                               threshold=thr, alpha=1 - 1e-4)),
          "  (alarms, median gap h, share of gaps == 168)")
