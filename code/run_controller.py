"""
Prequential runner for the adaptive controller (Modules 3 + 4).

For each client it runs, over the same test block used for the baselines:
  - the deterministic controller (Algorithm 1),
  - the bandit-extended controller (Algorithms 1 + 2),
and, from the per-model forecasts collected during the deterministic run, the two
reference baselines (best single static model, equal-weight ensemble) under identical
conditions. This produces the proposed-system rows for the Results table.

Diagnostics for one client are dumped to results/initial_controller/initial_controller_hourly_<client>.json for the demo plot.
"""
from __future__ import annotations
import os
os.environ.setdefault("OMP_NUM_THREADS", "1")   # one thread per worker; clients run in parallel
import argparse, time, json
from concurrent.futures import ProcessPoolExecutor
import numpy as np

from data_pipeline import prepare
from controller import AdaptiveController
import shifts
import metrics as M

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def evaluate_client(cs, block="test", schedule=168, include_online=True, max_steps=None,
                    gamma=0.995, ucb_c=0.2, run_bandit=True, drift_kw=None, topk=3,
                    demote_factor=1.5, combiner="blend", melo_eps0=0.01, melo_reset=None,
                    alarm_response=None, agent_kw=None, shift=None, diag_out=None, verbose=False):
    lo, hi = cs.splits[block]
    if max_steps:
        hi = min(hi, lo + max_steps)
    y_arr = cs.y.values.astype(float)
    # step 4: inject a synthetic shift scenario (events are absolute step indices)
    y_arr, events = shifts.apply(y_arr, lo, shift, block)
    ev = [e - lo for e in events if e < hi]          # block-relative, inside the run
    feats = cs.feats
    results = {}

    # --- deterministic controller (Algorithm 1) ---
    t0 = time.perf_counter()
    det = AdaptiveController(y_arr, feats, schedule=schedule,
                             include_online=include_online, use_bandit=False,
                             drift_kw=drift_kw, topk=topk, demote_factor=demote_factor,
                             combiner=combiner, melo_eps0=melo_eps0, melo_reset=melo_reset,
                             alarm_response=alarm_response, agent_kw=agent_kw)
    y, served_det, per_model, diag, drift_pts = det.run(lo, hi, verbose=verbose)
    det_sec = time.perf_counter() - t0

    # baselines computed from the SAME per-model forecasts (identical conditions)
    best_name = min(per_model, key=lambda k: M.mae(y, per_model[k]))
    results["best_static_single"] = dict(M.summarize(y, per_model[best_name], per_model),
                                         which=best_name)
    ens = np.mean(np.stack(list(per_model.values())), axis=0)
    results["equal_weight_ensemble"] = M.summarize(y, ens, per_model)

    results["adaptive_deterministic"] = M.summarize(y, served_det, per_model,
                                                    drift_points=drift_pts)
    results["adaptive_deterministic"]["n_drift"] = len(drift_pts)
    results["adaptive_deterministic"]["ops"] = M.operational_stats(diag, len(y))
    if ev:
        results["_events"] = ev
        for key, fc, al in (("adaptive_deterministic", served_det, drift_pts),
                            ("equal_weight_ensemble", ens, [])):
            rows, summ = M.shift_metrics(y, fc, al, ev)
            results[key]["shift"] = summ
            results[key]["shift_events"] = rows
    # per-step served candidates, for replaying the bandit offline (bandit tuning)
    streams = {"y": y.tolist(), "served": served_det.tolist(), "blend": diag["blend"],
               "best_pred": diag["best_pred"],
               "per_model": {k: v.tolist() for k, v in per_model.items()}}
    results["_timing_sec"] = {"deterministic": det_sec}
    results["_n_steps"] = int(len(y))
    if diag_out is not None:
        payload = {
            "y_true": y.tolist(),
            "served_det": served_det.tolist(),
            "combiner_out": diag["blend"],
            "per_model": {k: v.tolist() for k, v in per_model.items()},
            "best_per_step": diag["best"],
            "drift_points": drift_pts,
            "refit_any": diag["refit_any"],
            "events": ev,
            "weights": diag["weights"],
        }
        for k in ("agent_weights", "agent_candidates", "agent_choice"):
            if k in diag:
                payload[k] = diag[k]
        with open(diag_out, "w") as f:
            json.dump(payload, f)
        print(f"    diagnostics -> {diag_out}", flush=True)
    if not run_bandit:
        return results, streams

    # --- bandit-extended controller (Algorithms 1 + 2) ---
    t0 = time.perf_counter()
    ban = AdaptiveController(y_arr, feats, schedule=schedule,
                            include_online=include_online, use_bandit=True,
                            gamma=gamma, ucb_c=ucb_c, drift_kw=drift_kw, topk=topk,
                            demote_factor=demote_factor, combiner=combiner,
                            melo_eps0=melo_eps0, melo_reset=melo_reset,
                            alarm_response=alarm_response)
    y2, served_ban, per_model2, diag2, drift_pts2 = ban.run(lo, hi, verbose=verbose)
    ban_sec = time.perf_counter() - t0
    results["adaptive_bandit"] = M.summarize(y2, served_ban, per_model2,
                                             drift_points=drift_pts2)
    results["adaptive_bandit"]["n_drift"] = len(drift_pts2)
    force_best_share = float(np.mean(diag2["arm"])) if diag2["arm"] else float("nan")
    results["adaptive_bandit"]["force_best_share"] = force_best_share
    results["adaptive_bandit"]["ops"] = M.operational_stats(diag2, len(y2))
    if ev:
        rows, summ = M.shift_metrics(y2, served_ban, drift_pts2, ev)
        results["adaptive_bandit"]["shift"] = summ
        results["adaptive_bandit"]["shift_events"] = rows

    results["_timing_sec"]["bandit"] = ban_sec

    return results, streams


def _job(job):
    cid, cs, kw = job
    print(f"[{cid}] running controller ...", flush=True)
    res, streams = evaluate_client(cs, **kw)
    d = res["adaptive_deterministic"]; b = res["best_static_single"]
    print(f"[{cid}] det MAPE {d['MAPE']:.2f}% CV-RMSE {d['CV_RMSE']:.2f}% | "
          f"best-single {b['which']} MAPE {b['MAPE']:.2f}% | "
          f"drift {d['n_drift']} | {res['_timing_sec']['deterministic']:.1f}s", flush=True)
    return cid, res, streams


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--clients", type=int, default=8)
    ap.add_argument("--max-steps", type=int, default=None,
                    help="cap test steps per client (for a quick smoke run)")
    ap.add_argument("--no-online", action="store_true")
    ap.add_argument("--only", default=None, help="comma-separated client ids to run (default: all)")
    ap.add_argument("--diag-client", default="MT_132",
                    help="client id whose per-step diagnostics are saved for the demo plot")
    ap.add_argument("--out", default=os.path.join(PROJECT, "code", "results/initial_controller/initial_controller.json"))
    ap.add_argument("--diag-out", default=None,
                    help="file (under code/) for the --diag-client diagnostics; default results/initial_controller/initial_controller_hourly_<client>.json")
    ap.add_argument("--block", default="test", choices=["test", "val"])
    ap.add_argument("--gamma", type=float, default=0.995,
                    help="bandit discount factor (tuned on val: tune_bandit.py)")
    ap.add_argument("--ucb-c", type=float, default=0.2, help="bandit exploration weight (tuned on val)")
    ap.add_argument("--no-bandit", action="store_true", help="deterministic controller only")
    ap.add_argument("--streams-out", default=None,
                    help="save per-step y / blend / best-model forecasts (for bandit tuning)")
    ap.add_argument("--workers", type=int, default=4, help="clients run in parallel")
    ap.add_argument("--drift", default=None,
                    help='JSON of DriftMonitor kwargs, e.g. \'{"ph_threshold": 25, "ph_mode": "up"}\'')
    ap.add_argument("--schedule", type=int, default=168,
                    help="scheduled retrain interval in hours (1 = retrain every step)")
    ap.add_argument("--topk", type=int, default=3, help="models in the served blend")
    ap.add_argument("--demote-factor", type=float, default=1.5,
                    help="bench models with error > factor x best ('inf' disables demotion)")
    ap.add_argument("--no-drift", action="store_true",
                    help="disable drift detection (scheduled retraining only)")
    ap.add_argument("--combiner", default="blend", choices=["blend", "melo"],
                    help="served combiner: top-k inverse-error blend, or MELO")
    ap.add_argument("--melo-eps0", type=float, default=0.01, help="MELO eps0 (tuned on val)")
    ap.add_argument("--melo-reset", default=None,
                    help='JSON, e.g. \'{"on": "alarm", "regret_shrink": 0.5, "cov_reset": true}\'')
    ap.add_argument("--alarm-response", default=None,
                    help='JSON (use \'{}\' for the defaults): margin, min_window, followups, '
                         'fast_alpha, fast_hold; see controller.py')
    ap.add_argument("--agent", default=None,
                    help='JSON of ContextualSelector kwargs (step 5), e.g. '
                         '\'{"mode": "soft", "forget": 0.999, "temp": 0.3}\'; serves the agent\'s choice')
    ap.add_argument("--shift", default="none", choices=("none",) + shifts.SCENARIOS,
                    help="inject a synthetic demand-shift scenario (step 4)")
    args = ap.parse_args()
    alarm_response = json.loads(args.alarm_response) if args.alarm_response else None
    agent_kw = json.loads(args.agent) if args.agent else None
    if agent_kw is not None and not args.no_bandit:
        ap.error("--agent replaces the bandit: add --no-bandit")
    melo_reset = json.loads(args.melo_reset) if args.melo_reset else None
    drift_kw = json.loads(args.drift) if args.drift else None
    if args.no_drift:
        drift_kw = dict(drift_kw or {}, use_adwin=False, use_ph=False)

    data = prepare(n_clients=args.clients)
    if args.only:
        data = {c: data[c] for c in args.only.split(",")}
    jobs = []
    for cid, cs in data.items():
        diag_out = (os.path.join(PROJECT, "code", args.diag_out or f"results/initial_controller/initial_controller_hourly_{cid}.json")
                    if cid == args.diag_client and args.block == "test" else None)
        jobs.append((cid, cs, dict(block=args.block, include_online=not args.no_online,
                                   max_steps=args.max_steps, gamma=args.gamma,
                                   ucb_c=args.ucb_c, run_bandit=not args.no_bandit,
                                   drift_kw=drift_kw, schedule=args.schedule,
                                   topk=args.topk, demote_factor=args.demote_factor,
                                   combiner=args.combiner, melo_eps0=args.melo_eps0,
                                   melo_reset=melo_reset, alarm_response=alarm_response,
                                   agent_kw=agent_kw,
                                   shift=args.shift, diag_out=diag_out)))
    all_results, all_streams = {}, {}
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        for cid, res, streams in ex.map(_job, jobs):
            all_results[cid] = res
            all_streams[cid] = streams

    def agg(method, metric):
        vals = [all_results[c][method][metric] for c in all_results
                if method in all_results[c] and metric in all_results[c][method]]
        return float(np.mean(vals)) if vals else float("nan")

    print("\n=== AGGREGATE (mean over clients) ===")
    for method in ["best_static_single", "equal_weight_ensemble",
                   "adaptive_deterministic", "adaptive_bandit"]:
        print(f"  {method:24s} MAE {agg(method,'MAE'):8.2f}  RMSE {agg(method,'RMSE'):8.2f}  "
              f"CV-RMSE {agg(method,'CV_RMSE'):6.2f}%  MAPE {agg(method,'MAPE'):6.2f}%")

    def agg_ops(method, key):
        vals = [all_results[c][method]["ops"][key] for c in all_results
                if method in all_results[c] and "ops" in all_results[c][method]]
        return float(np.mean(vals)) if vals else float("nan")

    print("\n=== OPERATIONS (mean over clients, per week of test data) ===")
    for method in ["adaptive_deterministic", "adaptive_bandit"]:
        if not any(method in all_results[c] for c in all_results):
            continue
        print(f"  {method:24s} leader sw {agg_ops(method,'leader_switches_per_week'):5.2f}  "
              f"blend-set chg {agg_ops(method,'blendset_changes_per_week'):5.2f}  "
              f"arm sw {agg_ops(method,'arm_switches_per_week'):6.2f}  "
              f"drift {agg_ops(method,'drift_events_per_week'):4.2f}  "
              f"refits {agg_ops(method,'refits_total_per_week'):5.2f}  |  "
              f"{agg_ops(method,'ms_per_step'):6.1f} ms/step, "
              f"control {100*agg_ops(method,'control_share'):4.1f}%")

    if any("_events" in all_results[c] for c in all_results):
        print("\n=== SHIFT RESPONSE (mean over clients; MAPE/ratio over the 168 h and 672 h after each event) ===")
        for method in ["equal_weight_ensemble", "adaptive_deterministic", "adaptive_bandit"]:
            sh = [all_results[c][method]["shift"] for c in all_results
                  if method in all_results[c] and "shift" in all_results[c][method]]
            if not sh:
                continue
            g = lambda k: float(np.nanmean([x[k] for x in sh]))
            det = sum(x["detected"] for x in sh); n = sum(x["n_events"] for x in sh)
            print(f"  {method:24s} detected {det}/{n}  delay {g('delay_median'):6.1f} h  "
                  f"false {g('false_alarms_per_week'):4.2f}/wk  MAPE168 {g('MAPE_168'):6.2f}%  "
                  f"MAPE672 {g('MAPE_672'):6.2f}%  ratio168 {g('ratio_168'):4.2f}  "
                  f"recovery {g('recovery_median'):6.1f} h (not rec. {sum(x['not_recovered'] for x in sh)})")

    all_results["_config"] = {"block": args.block, "gamma": args.gamma, "ucb_c": args.ucb_c,
                              "drift_kw": drift_kw, "schedule": args.schedule,
                              "topk": args.topk, "demote_factor": args.demote_factor,
                              "combiner": args.combiner, "melo_eps0": args.melo_eps0,
                              "melo_reset": melo_reset, "alarm_response": alarm_response,
                              "agent": agent_kw,
                              "shift": args.shift}
    with open(args.out, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\nsaved -> {args.out}")
    if args.streams_out:
        with open(args.streams_out, "w") as f:
            json.dump(all_streams, f)
        print(f"saved -> {args.streams_out}")


if __name__ == "__main__":
    main()


""".venv/bin/python run_controller.py --no-bandit --workers 8 --combiner melo \
    --alarm-response '{}' --agent '{"mode": "soft", "forget": 0.999, "temp": 0.3}' \
    --shift none --out step5_results/none__agent.json \
    --streams-out step5_results/none__agent_streams.json"""
