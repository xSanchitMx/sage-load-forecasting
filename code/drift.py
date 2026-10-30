"""
Module 3 - Concept-Drift Detection.

Two complementary detectors run on the residual stream of the *served* forecast:
  - ADWIN         : adaptive windowing, sensitive to abrupt regime changes.
  - Page-Hinkley  : cumulative-deviation test, sensitive to gradual mean shifts.

The controller feeds the scale-normalised absolute served error each hour and retrains
its batch models whenever either detector fires. Detection is strictly online: each
detector only ever sees past residuals.

Calibration (2026-10-22, see tune_drift.py / logs): the residual is winsorised at `clip`
before it reaches the detectors, so a single outage hour (normalised error up to ~280)
cannot trip them on its own. Page-Hinkley is one-sided ("up"), because a fall in error
is not a reason to retrain. The thresholds are chosen on the validation block. The
original setting (threshold 3, two-sided, no clip) fired on every allowed step, i.e.
every 168 h, like a timer.
"""
from __future__ import annotations
from river import drift


class DriftMonitor:
    # defaults = the "sparse" setting chosen on the validation block (2026-10-22): all
    # calibrated settings tied on val MAPE (4.50-4.51), so the one with the fewest, most
    # error-coincident alarms (~0.2/week) was kept
    def __init__(self, adwin_delta: float = 0.002, ph_min_instances: int = 24,
                 ph_delta: float = 0.01, ph_threshold: float = 50.0,
                 ph_alpha: float = 1 - 1e-4, ph_mode: str = "up",
                 clip: float | None = 10.0, use_adwin: bool = True, use_ph: bool = True):
        self.adwin = drift.ADWIN(delta=adwin_delta) if use_adwin else None
        self.ph = (drift.PageHinkley(min_instances=ph_min_instances, delta=ph_delta,
                                     threshold=ph_threshold, alpha=ph_alpha, mode=ph_mode)
                   if use_ph else None)
        self.clip = clip
        self.t = 0
        self.drift_points: list[int] = []
        self.adwin_points: list[int] = []
        self.ph_points: list[int] = []

    def step(self, residual: float) -> bool:
        """Ingest one served-forecast residual; return True if drift is flagged."""
        if self.clip is not None:
            residual = min(residual, self.clip)
        a = p = False
        if self.adwin is not None:
            self.adwin.update(residual)
            a = self.adwin.drift_detected
        if self.ph is not None:
            self.ph.update(residual)
            p = self.ph.drift_detected
        if a:
            self.adwin_points.append(self.t)
        if p:
            self.ph_points.append(self.t)
        fired = a or p
        if fired:
            self.drift_points.append(self.t)
        self.t += 1
        return fired
