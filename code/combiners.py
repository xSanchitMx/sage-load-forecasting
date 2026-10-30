"""
Online forecast combiners that can sit inside the controller's prequential loop.

MELO (Wang, Goude & Yao 2026, arXiv 2605.06541, Algorithm 1): MLpol over the raw pool plus
K EWLS (forgotten-RLS) correction experts, each an online affine combination of the pool
forecasts with an intercept, one per forgetting factor. Covariance inflation
eps_k = eps0 * (1 - gamma_k) (their eq. 32, alpha = 1). Cold start as in their B.4: for the
first M+5 steps each EWLS expert serves the pool average, then its state is initialised by
a batch EWLS solve on those steps and updated by RLS thereafter.

Used one step at a time: predict(f_t) with the pool forecasts for hour t, then update(y_t).
adaptive_baselines.melo() replays the same class over saved streams, so the offline baseline
and the in-controller combiner are one implementation.

Numerical safeguard (not in the paper): P is re-symmetrised after every update and its
trace capped at its post-cold-start value. Without it, the shortest-memory expert
(gamma 0.95) loses positive-definiteness and diverges over ~9,000 hourly steps (the paper's
run is 746 daily steps); see ../logs/2026-10-22_step3_baselines_ablations/diagnostics/melo_windup*.

Scaling: the EWLS experts work on series divided by `scale` (by default the mean pool
forecast over the cold-start steps, known before the first EWLS forecast) so that one eps0
suits clients of different magnitude. MLpol's weights are invariant to a positive rescaling
of its regrets, so it runs in raw units.

Controller hook (this project's addition): reset(regret_shrink, cov_reset) lets the
controller tell MELO that the pool has changed (a model was refitted, or drift was flagged).
regret_shrink in [0, 1] shrinks MLpol's cumulative regrets towards zero, so the mixture
re-learns from recent losses; cov_reset puts every EWLS expert's covariance back to its
post-cold-start value, so the correction weights re-adapt quickly (the standard RLS
response to a detected change).
"""
from __future__ import annotations
import numpy as np


def melo_gammas(h_min=20.0, h_max=5000.0, k=15):
    """MELO's fixed grid: k forgetting factors geometric in memory length h = 1/(1-gamma)
    over [h_min, h_max], plus the no-forgetting endpoint gamma = 1."""
    h = np.geomspace(h_min, h_max, k)
    return np.append(1.0 - 1.0 / h, 1.0)


def mlpol_weights(R):
    pos = np.maximum(R, 0.0)
    s = pos.sum()
    return pos / s if s > 0 else np.full(len(R), 1.0 / len(R))


class MELO:
    def __init__(self, n_models: int, eps0: float = 0.01, gammas=None, scale: float | None = None):
        self.M = n_models
        self.gammas = melo_gammas() if gammas is None else np.asarray(gammas, float)
        self.K = len(self.gammas)
        self.d = self.M + 1
        self.n0 = self.M + 5
        self.eps = eps0 * (1.0 - self.gammas)
        self.scale = scale
        self.W = np.zeros((self.K, self.d))
        self.P = self.P0 = self.P_cap = None
        self.R = np.zeros(self.M + self.K)
        self.t = 0
        self._Fc, self._yc = [], []                 # cold-start buffer (raw units)
        self._f = self._cand = None
        self._out = None
        self.n_resets = 0

    @property
    def labels(self):
        return [f"ewls_h{('inf' if g >= 1 else round(1 / (1 - g)))}" for g in self.gammas]

    def weights(self):
        """Current mixture weights over (pool models, EWLS experts)."""
        return mlpol_weights(self.R)

    def predict(self, f) -> float:
        f = np.asarray(f, float)
        if self.t < self.n0:
            ew = np.full(self.K, f.mean())               # cold start: pool average
        else:
            ew = (self.W @ np.append(f / self.scale, 1.0)) * self.scale
        self._f = f
        self._cand = np.concatenate([f, ew])
        self._out = float(mlpol_weights(self.R) @ self._cand)
        return self._out

    def update(self, y: float):
        f, cand, out = self._f, self._cand, self._out
        self.R += 2.0 * (out - y) * (out - cand)         # MLpol, squared-loss gradient trick
        if self.t < self.n0:
            self._Fc.append(f); self._yc.append(y)
            if self.t == self.n0 - 1:
                self._cold_start_solve()
        else:
            self._rls(np.append(f / self.scale, 1.0), y / self.scale)
        self.t += 1

    def _cold_start_solve(self):
        Fc = np.array(self._Fc)
        if self.scale is None:
            self.scale = float(np.mean(Fc)) or 1.0
        Zc = np.column_stack([Fc / self.scale, np.ones(len(Fc))])
        yc = np.array(self._yc) / self.scale
        ridge = 1e-6 * float(np.mean(Zc ** 2))
        n0, d = len(Zc), self.d
        self.P = np.zeros((self.K, d, d))
        for k, gm in enumerate(self.gammas):
            wts = gm ** np.arange(n0 - 1, -1, -1)
            A = (Zc * wts[:, None]).T @ Zc + ridge * np.eye(d)
            self.P[k] = np.linalg.inv(A)
            self.W[k] = self.P[k] @ ((Zc * wts[:, None]).T @ yc)
        self.P0 = self.P.copy()
        self.P_cap = np.trace(self.P, axis1=1, axis2=2)
        self._Fc = self._yc = None

    def _rls(self, z, ys):
        """Forgotten-RLS update for all K experts at once (Algorithm 1, lines 14-18)."""
        g = self.gammas
        Pz = self.P @ z                                  # (K, d)
        s = g + Pz @ z                                   # (K,)
        self.W += (Pz / s[:, None]) * (ys - self.W @ z)[:, None]
        P = (self.P - Pz[:, :, None] * Pz[:, None, :] / s[:, None, None]) / g[:, None, None]
        P += self.eps[:, None, None] * np.eye(self.d)
        P = 0.5 * (P + P.transpose(0, 2, 1))
        tr = np.trace(P, axis1=1, axis2=2)
        over = tr > self.P_cap
        if over.any():
            P[over] *= (self.P_cap[over] / tr[over])[:, None, None]
        self.P = P

    def reset(self, regret_shrink: float = 0.0, cov_reset: bool = False):
        """Controller hook: the pool has changed (refit or drift)."""
        self.R *= (1.0 - regret_shrink)
        if cov_reset and self.P0 is not None:
            self.P = self.P0.copy()
        self.n_resets += 1

