"""
Offline calibration of the Module 3 drift detectors on the validation block.

Replays DriftMonitor over the served-residual stream of the deterministic controller
(served = blend), from the streams saved by
    run_controller.py --block val --no-bandit --streams-out results/forecasts/initial_controller_forecasts_val.json
using the same scale normalisation as controller.py. For each detector setting it reports:
  alarms_per_week - alarm rate
  timer_share     - share of inter-alarm gaps exactly equal to PH's min_instances (a value
                    near 1 means the detector fires as soon as it is allowed, i.e. it is a timer)
  lift            - mean over alarms of (24 h rolling MAE at the alarm) / (median 24 h
                    rolling MAE over the preceding week); > 1 means alarms coincide with a
                    real rise in error
The replay ignores the effect of alarm-triggered retrains on later residuals, so the
shortlisted settings are confirmed with full controller runs on the validation block.
"""
from __future__ import annotations
import argparse, itertools, json, os
import numpy as np

from drift import DriftMonitor

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def normalised_residuals(y, served, alpha=1 / 168):
    z, scale = np.empty(len(y)), None
    for t in range(len(y)):
        ae = abs(y[t] - served[t])
        z[t] = ae / (scale if scale else 1.0)
        scale = ae if scale is None else alpha * ae + (1 - alpha) * scale
    return z


def replay(z, ae, **kw):
    mon = DriftMonitor(**kw)
    for v in z:
        mon.step(float(v))
    pts = np.array(mon.drift_points)
    r24 = np.convolve(ae, np.ones(24) / 24, mode="full")[:len(ae)]
    lifts = [r24[t] / np.median(r24[t - 168:t]) for t in pts if t >= 168 + 24]
    gaps = np.diff(pts)
    return {"alarms": len(pts), "adwin": len(mon.adwin_points), "ph": len(mon.ph_points),
            "timer_share": float(np.mean(gaps == kw.get("ph_min_instances", 168)))
            if len(gaps) else 0.0,
            "lift": float(np.mean(lifts)) if lifts else float("nan")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--streams", default=os.path.join(PROJECT, "code", "results/forecasts/initial_controller_forecasts_val.json"))
    ap.add_argument("--out", default=os.path.join(PROJECT, "code", "results/tuning/drift_tuning.json"))
    args = ap.parse_args()
    S = json.load(open(args.streams))
    data = {}
    for c, d in S.items():
        y, served = np.asarray(d["y"], float), np.asarray(d["blend"], float)
        data[c] = (normalised_residuals(y, served), np.abs(y - served))
    weeks = np.mean([len(z) for z, _ in data.values()]) / 168

    def evaluate(kw):
        res = [replay(z, ae, **kw) for z, ae in data.values()]
        return {"alarms_per_week": float(np.mean([r["alarms"] for r in res]) / weeks),
                "adwin_share": float(np.sum([r["adwin"] for r in res]) /
                                     max(1, np.sum([r["alarms"] for r in res]))),
                "timer_share": float(np.mean([r["timer_share"] for r in res])),
                "lift": float(np.nanmean([r["lift"] for r in res]))}

    rows = []
    print("original setting (ph thr 3, both, no clip, min 168):")
    orig = dict(ph_threshold=3.0, ph_mode="both", clip=None, ph_min_instances=168)
    rows.append({"cfg": orig, **evaluate(orig)}); print("  ", rows[-1])

    print("\nPage-Hinkley alone (one-sided):")
    for clip, thr, mi in itertools.product((None, 5.0, 10.0), (10, 25, 50, 100, 200), (24, 168)):
        kw = dict(use_adwin=False, ph_mode="up", clip=clip, ph_threshold=float(thr),
                  ph_min_instances=mi)
        r = evaluate(kw); rows.append({"cfg": kw, **r})
        print(f"  clip {str(clip):>5} thr {thr:>4} min {mi:>3} | alarms/wk {r['alarms_per_week']:.3f}"
              f"  timer {r['timer_share']:.2f}  lift {r['lift']:.2f}", flush=True)

    print("\nADWIN alone:")
    for clip, delta in itertools.product((None, 5.0, 10.0), (0.002, 0.01, 0.05, 0.2)):
        kw = dict(use_ph=False, clip=clip, adwin_delta=delta)
        r = evaluate(kw); rows.append({"cfg": kw, **r})
        print(f"  clip {str(clip):>5} delta {delta:<6} | alarms/wk {r['alarms_per_week']:.3f}"
              f"  lift {r['lift']:.2f}", flush=True)

    with open(args.out, "w") as f:
        json.dump(rows, f, indent=2)
    print(f"\nsaved -> {args.out}")


if __name__ == "__main__":
    main()
