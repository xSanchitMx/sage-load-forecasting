"""
Step 4 - synthetic demand shifts injected into the real load series at known times.

Each scenario changes the client's series from two event times inside the evaluation block:
on test t1 = lo + 2016 h (12 weeks in) and t2 = lo + 5544 h (33 weeks in); on the shorter
validation block (used for tuning) t1 = lo + 1008 h and t2 = lo + 2688 h. Either way there
are at least four clean weeks after each event before the next one or the block end. The second event
reverses the first (except for the temporary shock, which happens twice), so every client
contributes two events per scenario, one "up" and one "down" where that applies.

  level      demand x1.3 from t1 (e.g. a new tenant); back to x1.0 from t2
  ramp       linear growth to x1.3 over 4 weeks from t1; linear decline back over 4 weeks from t2
  amplitude  the daily cycle around its 24 h mean is stretched x1.6 from t1 (peakier
             demand, e.g. new peak-hour load), back to x1.0 from t2
  temporary  demand x1.4 for one week from t1 and again from t2 (e.g. a heat wave)

The transform defines the ground truth, so it may use the whole series (the centred 24 h
mean in "amplitude"). The forecasters still only ever see values before the step they
predict. Calendar features are unchanged, and every lag is read from the shifted series.
"""
from __future__ import annotations
import numpy as np

EVENT_OFFSETS = {"test": (2016, 5544),
                 # the validation block is 3,946 h long: same design, earlier events (used
                 # to tune the alarm response without touching the test block)
                 "val": (1008, 2688)}
SCENARIOS = ("level", "ramp", "amplitude", "temporary")
RAMP_H = 672
SHOCK_H = 168


def _profile(n, events, scenario):
    """Multiplier / amplitude factor per step (1 = unchanged)."""
    t1, t2 = events
    f = np.ones(n)
    if scenario == "level":
        f[t1:t2] = 1.3
    elif scenario == "ramp":
        up = np.linspace(1.0, 1.3, RAMP_H + 1)[1:]
        f[t1:t1 + RAMP_H] = up
        f[t1 + RAMP_H:t2] = 1.3
        f[t2:t2 + RAMP_H] = up[::-1] - 0.3 / RAMP_H      # 1.3 -> 1.0
    elif scenario == "amplitude":
        f[t1:t2] = 1.6
    elif scenario == "temporary":
        f[t1:t1 + SHOCK_H] = 1.4
        f[t2:t2 + SHOCK_H] = 1.4
    else:
        raise ValueError(f"unknown scenario {scenario!r}")
    return f


def apply(y, lo, scenario, block="test"):
    """Return (shifted copy of y, [event times]) for a scenario starting at block start lo.
    scenario "none" returns y unchanged with no events."""
    y = np.asarray(y, float)
    if scenario in (None, "none"):
        return y.copy(), []
    events = [lo + o for o in EVENT_OFFSETS[block]]
    if events[-1] >= len(y):
        raise ValueError("block too short for the shift events")
    f = _profile(len(y), events, scenario)
    if scenario == "amplitude":
        base = np.convolve(y, np.ones(24) / 24, mode="same")
        out = base + f * (y - base)
    else:
        out = y * f
    return np.maximum(out, 0.0), events
