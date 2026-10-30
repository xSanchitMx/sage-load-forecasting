"""
Module 4 - Self-Adaptive Agentic Controller.

Supervises the five-model pool prequentially, one hour at a time:

  Algorithm 1 (deterministic core)
    - track each model's recent accuracy with an EWMA of its absolute error, E_m,
      with weight alpha = 1/W (W = 168 h, one week);
    - serve an inverse-error weighted blend of the top-k models;
    - demote (bench, but keep warm) any model whose error exceeds 1.5x the best;
    - on drift (from Module 3, on the served residual) retrain the batch models,
      and additionally retrain them on a 168 h background schedule.

  Algorithm 2 (bandit layer, optional)
    - a Discounted-UCB1 bandit with two arms, {follow_blend, force_best}, learns
      from reward r_t = -|e_t| (scale-normalised) whether to trust the deterministic
      blend or fall back to the single best model at each step.

  Combiner option (combiner="melo")
    - the served blend is MELO (combiners.MELO: MLpol over the pool plus multi-scale EWLS
      correction experts) instead of the top-k inverse-error blend. The controller keeps
      its decisions (drift detection, retraining) and can tell MELO when the pool has
      changed: melo_reset = {"on": "alarm" | "refit", "regret_shrink": r, "cov_reset": b}
      calls MELO.reset() after every drift alarm, or after every refit (drift or scheduled).

  Alarm response option (alarm_response = {...}, step 4)
    - follow-up refits of the batch models at alarm + each of `followups` hours
      (default 24, 72, 168), on the usual windows, so each refit sees more of the new
      regime as it arrives;
    - for `fast_hold` hours after the alarm the per-model error EWMA uses weight
      `fast_alpha` instead of 1/W, so the top-k blend re-ranks models quickly;
    - optional change-point cut (cut=True; rejected on validation): the alarm refit and
      its follow-ups use data from max(t_alarm - margin, t - min_window) onwards only.
      With scope="all" the scheduled refits are restricted too. Both versions lost
      accuracy, because 168 h of data makes SARIMA / LightGBM much weaker and every false
      alarm triggers it (../logs/2026-10-24_step4_shift_experiment).
    The default {} = follow-ups + fast EWMA, no cut (chosen on validation shifts).
    Without it (None), an alarm triggers one refit on the usual windows, as before.

  Contextual agent option (agent_kw = {...}, step 5; agent.py)
    - each hour a contextual selector chooses what to serve from [combiner output, each
      pool model] (soft mode: a softmin-weighted mix by predicted loss), given calendar,
      recent per-candidate errors, candidate disagreement, level change and the time since
      the last alarm / refit. Full-information feedback (every candidate's loss is seen).
      It replaces the two-arm bandit; the drift monitor then watches the agent's residual.

Every forecast uses information strictly before the step being predicted.
"""
from __future__ import annotations
import math
import time
import numpy as np

from models import build_pool
from drift import DriftMonitor
from combiners import MELO
from agent import ContextBuilder, ContextualSelector

RETRAIN_ON_DRIFT = {"holt_winters", "sarima", "lightgbm"}


class AdaptiveController:
    def __init__(self, y, feats, W: int = 168, topk: int = 3, demote_factor: float = 1.5,
                 schedule: int = 168, include_online: bool = True,
                 use_bandit: bool = False, gamma: float = 0.995, ucb_c: float = 0.2,
                 drift_kw: dict | None = None, combiner: str = "blend",
                 melo_eps0: float = 0.01, melo_reset: dict | None = None,
                 alarm_response: dict | None = None, agent_kw: dict | None = None):
        self.y = np.asarray(y, dtype=float)
        self.pool = build_pool(self.y, feats, include_online=include_online)
        self.names = [m.name for m in self.pool]
        self.W = W
        self.alpha = 1.0 / W
        self.topk = topk
        self.demote_factor = demote_factor
        self.schedule = schedule

        self.E = {n: None for n in self.names}          # EWMA abs error per model
        self.err_scale = None                            # EWMA abs served error (reward scale)

        # bandit state: arm 0 = follow_blend, arm 1 = force_best
        self.use_bandit = use_bandit
        self.gamma = gamma
        self.ucb_c = ucb_c
        self.bN = [0.0, 0.0]                              # discounted play counts
        self.bG = [0.0, 0.0]                              # discounted reward sums

        self.monitor = DriftMonitor(**(drift_kw or {}))

        if combiner not in ("blend", "melo"):
            raise ValueError(f"unknown combiner {combiner!r}")
        self.combiner = combiner
        self.melo = MELO(len(self.names), eps0=melo_eps0) if combiner == "melo" else None
        self.melo_reset = melo_reset
        self.agent = self.ctx = None
        if agent_kw is not None:
            if use_bandit:
                raise ValueError("the contextual agent replaces the bandit; use one or the other")
            kw = dict(agent_kw)
            lp = kw.pop("loss_power", 1)
            self.ctx = ContextBuilder(self.y, feats, 1 + len(self.names), loss_power=lp)
            self.agent = ContextualSelector(1 + len(self.names), self.ctx.dim, **kw)
        self.response = None
        if alarm_response is not None:
            self.response = dict(margin=24, min_window=168, followups=(24, 72, 168),
                                 fast_alpha=1 / 24, fast_hold=168, cut=False, scope="alarm")
            self.response.update(alarm_response)
        if melo_reset and melo_reset.get("on") not in ("alarm", "refit"):
            raise ValueError("melo_reset['on'] must be 'alarm' or 'refit'")

    # ---- Algorithm 1 helpers ------------------------------------------------
    def _weights(self):
        """Return (blend_weights dict over top-k active models, best_model_name)."""
        known = {n: e for n, e in self.E.items() if e is not None}
        if not known:
            # cold start: equal weight over the whole pool
            w = {n: 1.0 / len(self.names) for n in self.names}
            return w, None
        best_name = min(known, key=lambda n: known[n])
        best = known[best_name]
        # demotion: keep only models within demote_factor x of the best
        active = {n: e for n, e in known.items() if e <= self.demote_factor * best + 1e-12}
        top = sorted(active, key=lambda n: active[n])[:self.topk]
        inv = {n: 1.0 / (active[n] + 1e-6) for n in top}
        s = sum(inv.values())
        w = {n: inv[n] / s for n in top}
        return w, best_name

    # ---- Algorithm 2 helpers (Discounted-UCB1) ------------------------------
    def _ucb_select(self) -> int:
        for i in (0, 1):
            if self.bN[i] <= 0:
                return i                                 # play each arm once first
        total = self.bN[0] + self.bN[1]
        scores = [self.bG[i] / self.bN[i] + self.ucb_c * math.sqrt(math.log(total) / self.bN[i])
                  for i in (0, 1)]
        return int(np.argmax(scores))

    def _ucb_update(self, arm: int, reward: float):
        for i in (0, 1):                                 # discount everything, then credit
            self.bN[i] *= self.gamma
            self.bG[i] *= self.gamma
        self.bN[arm] += 1.0
        self.bG[arm] += reward

    # ---- main prequential loop ---------------------------------------------
    def run(self, lo: int, hi: int, warm_days: int = 90, verbose: bool = False):
        y = self.y
        # warm-start batch members once at the start of the test block
        for m in self.pool:
            if m.retrainable:
                m.retrain(lo)
        # warm-up self-updating members on recent history (avoids SGD cold-start divergence)
        warm_from = max(200, lo - 24 * warm_days)
        for m in self.pool:
            if getattr(m, "self_updating", False):
                for s in range(warm_from, lo):
                    m.update(s, y[s])

        last_refit = {n: lo for n in self.names}
        y_true, served = [], []
        per_model = {n: [] for n in self.names}
        diag = {"weights": [], "best": [], "drift": [], "arm": [], "retrained": [],
                "blend": [], "best_pred": []}
        # operational accounting (Module 5): wall-clock per phase and per model, and
        # model refits by cause. Instrumentation only - it does not affect any forecast.
        clock = time.perf_counter
        sec = {"predict": 0.0, "update": 0.0, "retrain_drift": 0.0,
               "retrain_scheduled": 0.0, "control": 0.0}
        model_sec = {n: 0.0 for n in self.names}
        refits = {"drift": {n: 0 for n in self.names}, "scheduled": {n: 0 for n in self.names},
                  "followup": {n: 0 for n in self.names}}
        cut = None                  # change point from the latest alarm (alarm response)
        followups = set()           # steps at which a follow-up refit is due
        fast_until = -1             # error EWMA uses fast_alpha while t < fast_until
        resp = self.response
        last_alarm, last_any_refit = -10**9, lo
        agent_choice, agent_w, refit_any = [], [], []

        def since(s):
            if cut is None or not resp["cut"]:
                return None
            return min(cut, s - resp["min_window"])

        def timed(m, fn, *a):
            t0 = clock()
            out = fn(*a)
            model_sec[m.name] += clock() - t0
            return out

        for t in range(lo, hi):
            c0 = clock()
            preds = {m.name: max(0.0, timed(m, m.predict, t)) for m in self.pool}
            c1 = clock()
            sec["predict"] += c1 - c0
            for n, p in preds.items():
                per_model[n].append(p)

            w, best_name = self._weights()
            if self.melo is not None:
                blend = self.melo.predict([preds[n] for n in self.names])
                mw = self.melo.weights()
                w = {n: float(v) for n, v in zip(self.names + self.melo.labels, mw) if v > 0}
            else:
                blend = sum(w[n] * preds[n] for n in w) if w else preds[self.names[0]]

            if self.agent is not None:
                cands = [blend] + [preds[n] for n in self.names]
                x_ctx = self.ctx.features(t, cands, t - last_alarm, t - last_any_refit)
                yhat, ch = self.agent.choose(x_ctx, cands)
                agent_choice.append(ch)
                agent_w.append(self.agent.last_weights.tolist())
                arm = 0
            elif self.use_bandit and best_name is not None:
                arm = self._ucb_select()
                yhat = blend if arm == 0 else preds[best_name]
            else:
                arm = 0
                yhat = blend

            yt = y[t]
            e = yt - yhat
            served.append(yhat)
            y_true.append(yt)

            # update per-model EWMA errors (each model judged on its own forecast)
            a_t = resp["fast_alpha"] if (resp and t < fast_until) else self.alpha
            for n, p in preds.items():
                err = abs(yt - p)
                self.E[n] = err if self.E[n] is None else a_t * err + (1 - a_t) * self.E[n]

            ae = abs(e)
            scale = self.err_scale if self.err_scale else 1.0
            norm_resid = ae / scale            # scale-free residual for reward & drift
            # bandit reward on the played arm
            if self.use_bandit and best_name is not None:
                self._ucb_update(arm, -norm_resid)
            self.err_scale = ae if self.err_scale is None else self.alpha * ae + (1 - self.alpha) * self.err_scale
            if self.melo is not None:
                self.melo.update(yt)
            if self.agent is not None:
                self.agent.update(x_ctx, self.ctx.observe(yt, cands))

            # let models observe the realised value
            c2 = clock()
            sec["control"] += c2 - c1
            for m in self.pool:
                timed(m, m.update, t, yt)
            c3 = clock()
            sec["update"] += c3 - c2

            # drift on the (scale-normalised) served residual -> targeted retrain
            fired = self.monitor.step(norm_resid)
            c4 = clock()
            sec["control"] += c4 - c3
            retrained = False
            if fired and resp:
                cut = max(0, t + 1 - resp["margin"])
                followups = {t + 1 + h for h in resp["followups"]}
                fast_until = t + 1 + resp["fast_hold"]
            due = fired or (t + 1) in followups
            if due:
                cause = "drift" if fired else "followup"
                for m in self.pool:
                    if m.retrainable and m.name in RETRAIN_ON_DRIFT:
                        timed(m, m.retrain, t + 1, since(t + 1))
                        last_refit[m.name] = t + 1
                        refits[cause][m.name] += 1
                retrained = True
            c5 = clock()
            sec["retrain_drift"] += c5 - c4
            # background scheduled retrain
            sched = False
            for m in self.pool:
                if m.retrainable and (t + 1 - last_refit[m.name]) >= self.schedule:
                    timed(m, m.retrain, t + 1,
                          since(t + 1) if resp and resp["scope"] == "all" else None)
                    last_refit[m.name] = t + 1
                    refits["scheduled"][m.name] += 1
                    sched = True
            c6 = clock()
            sec["retrain_scheduled"] += c6 - c5
            if fired:
                last_alarm = t + 1
            if retrained or sched:
                last_any_refit = t + 1
            refit_any.append(bool(retrained or sched))
            # tell the combiner the pool has changed
            if self.melo_reset and ((self.melo_reset["on"] == "alarm" and fired) or
                                    (self.melo_reset["on"] == "refit" and (retrained or sched))):
                self.melo.reset(regret_shrink=self.melo_reset.get("regret_shrink", 0.0),
                                cov_reset=self.melo_reset.get("cov_reset", False))
            sec["control"] += clock() - c6

            diag["weights"].append(dict(w))
            diag["best"].append(best_name)
            diag["drift"].append(bool(fired))
            diag["arm"].append(int(arm))
            diag["retrained"].append(bool(retrained))
            diag["blend"].append(float(blend))
            diag["best_pred"].append(float(preds[best_name]) if best_name is not None else float(blend))

            if verbose and (t - lo) % 2000 == 0:
                print(f"    step {t-lo}/{hi-lo}", flush=True)

        diag["ops"] = {"sec": sec, "model_sec": model_sec, "refits": refits,
                       "combiner_resets": self.melo.n_resets if self.melo is not None else 0}
        diag["refit_any"] = refit_any
        if self.agent is not None:
            diag["agent_choice"] = agent_choice
            diag["agent_weights"] = agent_w
            diag["agent_candidates"] = ["melo" if self.melo is not None else "blend"] + self.names
        y_true = np.array(y_true)
        served = np.array(served)
        per_model = {k: np.array(v) for k, v in per_model.items()}
        return y_true, served, per_model, diag, list(self.monitor.drift_points)
