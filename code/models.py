"""
Module 2 - Forecasting Model Pool.

Five cheap, complementary one-step-ahead forecasters behind a uniform interface:
    predict(t)      -> forecast for step t (using history < t only)
    update(t, y)    -> observe the realised value at step t
    retrain(t)      -> refit on a recent window (no-op for models that self-update)
    retrain(t, since=s) -> same, but the window starts no earlier than s (used by the
                       controller's alarm response to drop data from before a change point)

All models operate on a single client's raw hourly load series `y` (a numpy array)
plus the calendar-feature frame for the feature-based model. Every forecast uses only
information available strictly before the step being predicted (prequential-safe).
"""
from __future__ import annotations
import warnings
import numpy as np


class BaseModel:
    name = "base"
    retrainable = False
    self_updating = False   # True if update() incrementally fits and it needs history warm-up

    def predict(self, t: int) -> float:
        raise NotImplementedError

    def update(self, t: int, y: float) -> None:
        pass

    def retrain(self, t: int, since: int | None = None) -> None:
        pass


class SeasonalNaive(BaseModel):
    """Forecast = value one seasonal period ago (weekly, falling back to daily)."""
    name = "seasonal_naive"
    retrainable = False

    def __init__(self, y: np.ndarray, weekly: int = 168, daily: int = 24):
        self.y = y
        self.weekly = weekly
        self.daily = daily

    def predict(self, t: int) -> float:
        if t - self.weekly >= 0:
            return float(self.y[t - self.weekly])
        if t - self.daily >= 0:
            return float(self.y[t - self.daily])
        return float(self.y[t - 1]) if t > 0 else 0.0


class HoltWinters(BaseModel):
    """
    Additive Holt-Winters with daily seasonality, updated recursively each step.
    Self-updating: retrain() forces a state re-seed from the recent window.
    """
    name = "holt_winters"
    retrainable = True

    def __init__(self, y: np.ndarray, m: int = 24, alpha=0.15, beta=0.02, gamma=0.10):
        self.y = y
        self.m = m
        self.alpha, self.beta, self.gamma = alpha, beta, gamma
        self.level = None
        self.trend = 0.0
        self.season = np.zeros(m)
        self._seeded_upto = 0

    def _seed(self, t: int, since: int | None = None):
        lo = max(0, t - self.m * 7)
        if since is not None:
            lo = max(lo, since)
        window = self.y[lo:t]
        if window.size >= self.m:
            self.level = float(window.mean())
            self.trend = 0.0
            seas = np.zeros(self.m)
            for h in range(self.m):
                vals = window[h::self.m]
                # window[h] is time lo + h, so it belongs to phase slot (lo + h) % m,
                # the slot predict()/update() index with t % m
                seas[(lo + h) % self.m] = float(vals.mean() - self.level) if vals.size else 0.0
            self.season = seas
        elif window.size:
            self.level = float(window.mean())
        else:
            self.level = 0.0
        self._seeded_upto = t

    def predict(self, t: int) -> float:
        if self.level is None:
            self._seed(t)
        h = t % self.m
        return float(self.level + self.trend + self.season[h])

    def update(self, t: int, y: float) -> None:
        if self.level is None:
            self._seed(t)
        h = t % self.m
        prev_level = self.level
        self.level = self.alpha * (y - self.season[h]) + (1 - self.alpha) * (self.level + self.trend)
        self.trend = self.beta * (self.level - prev_level) + (1 - self.beta) * self.trend
        self.season[h] = self.gamma * (y - self.level) + (1 - self.gamma) * self.season[h]

    def retrain(self, t: int, since: int | None = None) -> None:
        self._seed(t, since)


class SARIMAModel(BaseModel):
    """
    Seasonal ARIMA via statsmodels. Order is fixed once (passed in) and only the
    coefficients are re-estimated on a rolling window at retrain(); between retrains
    each realised value is filtered into the state (coefficients held fixed), so every
    forecast is one step ahead like the rest of the pool. Kept low-order for speed.
    A forecast that is non-finite or outside [0, bound x recent max] (an unstable fit)
    falls back to the daily seasonal-naive value.
    """
    name = "sarima"
    retrainable = True

    def __init__(self, y: np.ndarray, order=(1, 0, 1), seasonal_order=(1, 0, 1, 24),
                 window: int = 24 * 30, bound: float = 2.0):
        self.y = y
        self.order = order
        self.seasonal_order = seasonal_order
        self.window = window
        self.bound = bound
        self._res = None        # results whose state covers data strictly before _upto
        self._upto = -1
        self._cap = np.inf

    def _fit(self, t: int, since: int | None = None):
        from statsmodels.tsa.statespace.sarimax import SARIMAX
        lo = max(0, t - self.window)
        if since is not None:
            lo = max(lo, since)
        endog = self.y[lo:t]
        self._upto = t
        if endog.size < self.seasonal_order[3] * 2 + 10:
            self._res = None
            return
        self._cap = self.bound * float(endog.max())
        try:
            model = SARIMAX(endog, order=self.order, seasonal_order=self.seasonal_order,
                            enforce_stationarity=False, enforce_invertibility=False)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")      # capped-iteration convergence warnings
                self._res = model.fit(disp=False, maxiter=50, method="lbfgs")
        except Exception:
            self._res = None

    def _fallback(self, t: int) -> float:
        return float(self.y[t - 24]) if t >= 24 else (float(self.y[t - 1]) if t else 0.0)

    def predict(self, t: int) -> float:
        if self._res is None:
            if t < self.seasonal_order[3] * 2 + 10:
                return self._fallback(t)
            self._fit(t)
        if self._res is None:
            return self._fallback(t)
        try:
            fc = float(self._res.forecast(steps=max(1, t - self._upto + 1))[-1])
        except Exception:
            return self._fallback(t)
        if not np.isfinite(fc) or fc < 0 or fc > self._cap:
            return self._fallback(t)
        return fc

    def update(self, t: int, y: float) -> None:
        if self._res is not None and t == self._upto:
            try:
                self._res = self._res.extend(np.array([y]))
                self._upto = t + 1
            except Exception:
                self._res = None

    def retrain(self, t: int, since: int | None = None) -> None:
        self._fit(t, since)


class LightGBMModel(BaseModel):
    """Gradient-boosted trees on lag + calendar features; retrained on a sliding window."""
    name = "lightgbm"
    retrainable = True
    LAGS = [1, 2, 3, 24, 168]

    def __init__(self, y: np.ndarray, feats, window: int = 24 * 60):
        self.y = y
        self.feats = feats.reset_index(drop=True)
        self.window = window
        self._model = None

    def _row(self, t: int):
        if t < max(self.LAGS):
            return None
        lag_vals = [self.y[t - L] for L in self.LAGS]
        f = self.feats.iloc[t]
        return lag_vals + [f["hour"], f["dow"], f["month"], f["is_weekend"], f["is_holiday"]]

    def _fit(self, t: int, since: int | None = None):
        import lightgbm as lgb
        lo = max(max(self.LAGS), t - self.window)
        if since is not None:
            lo = max(lo, since)
        X, Y = [], []
        for s in range(lo, t):
            r = self._row(s)
            if r is not None:
                X.append(r); Y.append(self.y[s])
        if len(X) < 100:
            self._model = None
            return
        ds = lgb.Dataset(np.array(X), label=np.array(Y))
        params = dict(objective="regression", metric="l1", num_leaves=31,
                      learning_rate=0.05, verbose=-1, min_data_in_leaf=20)
        self._model = lgb.train(params, ds, num_boost_round=120)

    def predict(self, t: int) -> float:
        if self._model is None:
            self._fit(t)
        r = self._row(t)
        if self._model is None or r is None:
            return float(self.y[t - 24]) if t >= 24 else 0.0
        return float(self._model.predict(np.array([r]))[0])

    def retrain(self, t: int, since: int | None = None) -> None:
        self._fit(t, since)


class OnlineLinear(BaseModel):
    """Incremental linear model (river) updated one sample at a time; never batch-retrained."""
    name = "online_linear"
    retrainable = False
    self_updating = True          # warmed up on history before the test loop
    LAGS = [1, 2, 3, 24, 168]

    def __init__(self, y: np.ndarray, feats):
        from river import linear_model, preprocessing, optim
        self.y = y
        self.feats = feats.reset_index(drop=True)
        # StandardScaler on both inputs and target keeps SGD gradients well-scaled;
        # a small learning rate prevents early divergence on raw-kWh features.
        self.model = preprocessing.StandardScaler() | linear_model.LinearRegression(
            optimizer=optim.SGD(0.003))

    def _x(self, t: int):
        if t < max(self.LAGS):
            return None
        f = self.feats.iloc[t]
        x = {f"lag{L}": float(self.y[t - L]) for L in self.LAGS}
        x.update(hour=float(f["hour"]), dow=float(f["dow"]), month=float(f["month"]),
                 wknd=float(f["is_weekend"]), hol=float(f["is_holiday"]))
        return x

    def predict(self, t: int) -> float:
        x = self._x(t)
        if x is None:
            return float(self.y[t - 24]) if t >= 24 else 0.0
        return float(self.model.predict_one(x))

    def update(self, t: int, y: float) -> None:
        x = self._x(t)
        if x is not None:
            self.model.learn_one(x, float(y))


def build_pool(y: np.ndarray, feats, include_online: bool = True) -> list[BaseModel]:
    """Instantiate the model pool for one client series."""
    pool = [
        SeasonalNaive(y),
        HoltWinters(y),
        SARIMAModel(y),
        LightGBMModel(y, feats),
    ]
    if include_online:
        pool.append(OnlineLinear(y, feats))
    return pool
