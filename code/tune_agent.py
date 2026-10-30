"""
Offline tuning of the step-5 contextual agent (agent.py) on the validation block.

Replays the agent over the per-step streams of the proposed system (MELO combiner +
calibrated drift + follow-up refits), saved by run_step5 val runs into results/validation/agent_tuning_forecasts/,
without and with each injected shift. The candidates are [MELO, pool models...]. The drift
alarms and refit times the agent sees are reconstructed exactly as the controller produces
them (same detector, same residual normalisation, same schedule / follow-up rule) from the
MELO stream. The replay ignores the effect of the agent's own choices on later alarms; the
chosen setting is then confirmed in the controller loop.

Reports, per scenario and averaged over the five: mean val MAPE, mean CV-RMSE, and the
mean over clients of MAPE relative to MELO (rel; the selection rule, because one client,
MT_135, has near-zero hours that let its MAPE dominate plain averages). Rows: MELO, a
per-step oracle (hindsight best candidate each hour: an upper bound, not achievable) and
every agent setting -> results/tuning/agent_tuning.json.
"""
from __future__ import annotations
import argparse, itertools, json, os
import numpy as np

import metrics as M
from agent import ContextBuilder, ContextualSelector
from data_pipeline import prepare
from drift import DriftMonitor
from tune_drift import normalised_residuals

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CODE = os.path.join(PROJECT, "code")
SCEN = ("none", "level", "ramp", "amplitude", "temporary")


def alarm_refit_clock(y, served, schedule=168, followups=(24, 72, 168)):
    """Hours since the last alarm and since the last refit, per step (as seen before y_t)."""
    z = normalised_residuals(y, served)
    mon = DriftMonitor()
    T = len(y)
    since_alarm = np.full(T, 1e6); since_refit = np.zeros(T)
    last_alarm, last_refit, fu = -10**9, 0, set()
    for t in range(T):
        since_alarm[t] = t - last_alarm
        since_refit[t] = t - last_refit
        fired = mon.step(float(z[t]))
        if fired:
            last_alarm = t + 1
            fu = {t + 1 + h for h in followups}
        if fired or (t + 1) in fu or (t + 1 - last_refit) >= schedule:
            last_refit = t + 1
    return since_alarm, since_refit


def load(block="val"):
    data = prepare(n_clients=8)
    out = {}
    for sc in SCEN:
        S = json.load(open(os.path.join(CODE, "results", "validation", "agent_tuning_forecasts", f"{block}_{sc}.json")))
        for c, d in S.items():
            cs = data[c]
            lo, hi = cs.splits[block]
            y = np.asarray(d["y"], float)
            names = list(d["per_model"])
            C = np.column_stack([d["blend"]] + [d["per_model"][n] for n in names])
            sa, sr = alarm_refit_clock(y, np.asarray(d["blend"], float))
            # full-length series for the context's lag features (shift applied to the block only)
            full = cs.y.values.astype(float).copy()
            full[lo:lo + len(y)] = y
            out[(sc, c)] = dict(y=y, C=C, sa=sa, sr=sr, lo=lo, full=full, feats=cs.feats)
    return out


def replay(d, loss_power=1, **kw):
    y, C, lo = d["y"], d["C"], d["lo"]
    K = C.shape[1]
    cb = ContextBuilder(d["full"], d["feats"], K, loss_power=loss_power)
    ag = ContextualSelector(K, cb.dim, **kw)
    out = np.empty(len(y)); choice = np.empty(len(y), int)
    for i in range(len(y)):
        t = lo + i
        x = cb.features(t, C[i], d["sa"][i], d["sr"][i])
        out[i], choice[i] = ag.choose(x, C[i])
        l = cb.observe(y[i], C[i])
        ag.update(x, l)
    return out, choice


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(CODE, "results/tuning/agent_tuning.json"))
    args = ap.parse_args()
    data = load("val")

    melo_mape = {k: M.mape(d["y"], d["C"][:, 0]) for k, d in data.items()}

    def score(fc_fn):
        mp, cv, rel = ({sc: [] for sc in SCEN} for _ in range(3))
        for (sc, c), d in data.items():
            f = fc_fn(d)
            m = M.mape(d["y"], f)
            mp[sc].append(m); cv[sc].append(M.cv_rmse(d["y"], f))
            rel[sc].append(m / melo_mape[(sc, c)])
        r = {sc: float(np.mean(v)) for sc, v in mp.items()}
        r["mean"] = float(np.mean([r[sc] for sc in SCEN]))
        r["cv"] = {sc: float(np.mean(v)) for sc, v in cv.items()}
        r["cv_mean"] = float(np.mean(list(r["cv"].values())))
        r["rel"] = {sc: float(np.mean(v)) for sc, v in rel.items()}
        r["rel_mean"] = float(np.mean(list(r["rel"].values())))
        return r

    rows = []
    def show(name, r, extra=""):
        print(f"  {name:44s} MAPE " + " ".join(f"{r[sc]:6.3f}" for sc in SCEN)
              + f" | rel " + " ".join(f"{r['rel'][sc]:.3f}" for sc in SCEN)
              + f" | rel mean {r['rel_mean']:.4f}  CV mean {r['cv_mean']:.3f} {extra}", flush=True)

    base = score(lambda d: d["C"][:, 0]); show("MELO (served by the proposed system)", base)
    orc = score(lambda d: d["C"][np.arange(len(d["y"])), np.argmin(np.abs(d["y"][:, None] - d["C"]), 1)])
    show("per-step oracle (hindsight, not achievable)", orc)
    rows += [{"name": "melo", **base}, {"name": "oracle", **orc}]

    grid = [dict(mode="argmin", forget=f, margin=m) for f, m in
            itertools.product((0.99, 0.995, 0.999, 1.0), (0.0, 0.1, 0.25, 0.5))]
    grid += [dict(mode="soft", forget=f, temp=tp) for f, tp in
             itertools.product((0.995, 0.999, 1.0), (0.05, 0.1, 0.3, 1.0))]
    # squared-loss target (temperatures on the squared scale)
    grid += [dict(mode="soft", forget=f, temp=tp, loss_power=2) for f, tp in
             itertools.product((0.995, 0.999), (0.1, 0.3, 1.0, 3.0))]
    for kw in grid:
        shares = []
        def fc(d, kw=kw):
            o, ch = replay(d, **kw)
            shares.append(float(np.mean(ch != 0)))
            return o
        r = score(fc)
        show(json.dumps(kw), r, f"override {np.mean(shares):.1%}")
        rows.append({"name": "agent", "params": kw, "override_share": float(np.mean(shares)), **r})
    print(f"\n(scenario order: {', '.join(SCEN)})")
    best = min((r for r in rows if r["name"] == "agent"), key=lambda r: r["rel_mean"])
    print(f"best (lowest mean relative MAPE): {json.dumps(best['params'])}  rel {best['rel_mean']:.4f}"
          f"  CV {best['cv_mean']:.3f}  (MELO rel 1.0000, CV {base['cv_mean']:.3f})")
    with open(args.out, "w") as f:
        json.dump({"rows": rows, "best": best}, f, indent=2)
    print(f"saved -> {args.out}")


if __name__ == "__main__":
    main()
