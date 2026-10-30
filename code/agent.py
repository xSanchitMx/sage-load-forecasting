"""
Step 5 - contextual serving agent.

Each hour the agent chooses which candidate forecast to serve: MELO's combined forecast or
one of the pool models. It sees a context vector built only from information available
before the hour (calendar, each candidate's recent error, how far the candidates disagree,
recent change in load level, time since the last drift alarm and the last refit).

Feedback is full: once y_t is known, the loss of every candidate is known, not only the
served one, because all candidates are computed every hour. So the agent is a contextual
bandit with full information, and no exploration is needed. Each candidate k has an
online linear model of its next scale-free loss,  l_k(t) ~ w_k . x_t,  fitted by
recursive least squares with forgetting factor `forget` (one shared covariance, because
every arm sees the same x_t). The agent serves MELO unless some other candidate's
predicted loss is lower than MELO's by more than `margin` (in units of the running
error scale); mode="soft" instead serves a softmin-weighted average of the candidates.

ContextBuilder computes x_t, so the offline replay (tune_agent.py) and the in-controller
agent use exactly the same features.
"""
from __future__ import annotations
import numpy as np


class ContextBuilder:
    """Causal context features. Call features(t, cands, ...) before y_t is known, then
    observe(t, y_t, cands) once it is."""

    def __init__(self, y, feats, n_cand: int, fast: float = 1 / 24, slow: float = 1 / 168,
                 recency_h: float = 48.0, loss_power: int = 1):
        self.y = np.asarray(y, float)
        f = feats.reset_index(drop=True)
        self.hour = f["hour"].to_numpy()
        self.weekend = f["is_weekend"].to_numpy()
        self.holiday = f["is_holiday"].to_numpy()
        self.K = n_cand
        self.power = loss_power             # 1: learn |e|, 2: learn e^2 (weights big errors)
        self.fast, self.slow, self.rec = fast, slow, recency_h
        self.Ef = np.zeros(n_cand)          # fast / slow EWMA of each candidate's scaled loss
        self.Es = np.zeros(n_cand)
        self.scale = None                   # EWMA abs error of candidate 0 (MELO), for scaling
        self.n = 0

    @property
    def dim(self):
        return 6 + 3 * self.K + 4

    def features(self, t, cands, since_alarm: float, since_refit: float):
        y = self.y
        s = self.scale or max(1.0, float(np.mean(cands)) * 0.05)
        ang = 2 * np.pi * self.hour[t] / 24
        lvl = (y[t - 1] - y[t - 25]) / s if t >= 25 else 0.0
        wk = (y[t - 1] - y[t - 169]) / s if t >= 169 else 0.0
        disagree = float(np.std(cands)) / s
        dev = (np.asarray(cands) - cands[0]) / s
        x = np.concatenate([
            [1.0, np.sin(ang), np.cos(ang), self.weekend[t], self.holiday[t], disagree],
            self.Ef, self.Es, np.clip(dev, -10, 10),
            [np.clip(lvl, -10, 10), np.clip(wk, -10, 10),
             np.exp(-since_alarm / self.rec), np.exp(-since_refit / self.rec)],
        ])
        return x

    def losses(self, y_t, cands):
        s = self.scale or max(1.0, float(np.mean(cands)) * 0.05)
        return np.minimum(np.abs(y_t - np.asarray(cands)) / s, 10.0) ** self.power

    def observe(self, y_t, cands):
        l = self.losses(y_t, cands)
        if self.n == 0:
            self.Ef[:] = l; self.Es[:] = l
        else:
            self.Ef = self.fast * l + (1 - self.fast) * self.Ef
            self.Es = self.slow * l + (1 - self.slow) * self.Es
        ae = abs(y_t - cands[0])
        self.scale = ae if self.scale is None else self.slow * ae + (1 - self.slow) * self.scale
        self.n += 1
        return l


class ContextualSelector:
    """Full-information contextual selection over K candidates (index 0 = default, MELO)."""

    def __init__(self, n_cand: int, dim: int, forget: float = 0.999, ridge: float = 1.0,
                 margin: float = 0.1, mode: str = "argmin", temp: float = 0.1,
                 warmup: int = 168):
        self.K, self.d = n_cand, dim
        self.forget, self.margin, self.mode, self.temp = forget, margin, mode, temp
        self.warmup = warmup
        self.P = np.eye(dim) / ridge
        self.P_cap = float(np.trace(self.P))
        self.W = np.zeros((n_cand, dim))
        self.n = 0
        self.last_choice = 0
        self.last_weights = None            # weights over candidates actually served

    def predict_losses(self, x):
        return self.W @ x

    def choose(self, x, cands):
        """Return (served forecast, chosen index or -1 for a soft blend)."""
        cands = np.asarray(cands, float)
        if self.n < self.warmup:
            self.last_choice = 0
            self.last_weights = np.eye(self.K)[0]
            return float(cands[0]), 0
        pl = self.predict_losses(x)
        if self.mode == "soft":
            z = -(pl - pl.min()) / self.temp
            w = np.exp(z); w /= w.sum()
            self.last_choice = -1
            self.last_weights = w
            return float(w @ cands), -1
        k = int(np.argmin(pl))
        if k != 0 and pl[k] < pl[0] - self.margin:
            self.last_choice = k
            self.last_weights = np.eye(self.K)[k]
            return float(cands[k]), k
        self.last_choice = 0
        self.last_weights = np.eye(self.K)[0]
        return float(cands[0]), 0

    def update(self, x, losses):
        """RLS with forgetting, all K arms at once (shared P)."""
        Px = self.P @ x
        g = Px / (self.forget + x @ Px)
        self.W += np.outer(losses - self.W @ x, g)
        self.P = (self.P - np.outer(g, Px)) / self.forget
        self.P = 0.5 * (self.P + self.P.T)
        # forgetting inflates P along rarely-excited directions (e.g. the holiday flag);
        # cap its trace at the initial value, as for MELO's EWLS experts
        tr = np.trace(self.P)
        if tr > self.P_cap:
            self.P *= self.P_cap / tr
        self.n += 1
