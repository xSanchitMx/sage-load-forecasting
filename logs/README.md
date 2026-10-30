# Run logs

> **2026-10-29 reorganisation:** this folder moved from `code/logs/` to the project root, and the result files moved into `code/results/<topic>/` with readable names. Entries below use the paths and file names that were current when each run was made. `RENAMES.md` in the project root maps every old name to its new one. The `.sh` scripts kept here are records of what was run, so they still use the old paths and assume they're run from `code/`.

One folder per experiment session, named `YYYY-MM-DD_<what>`. Each holds the console logs
of every run in that session (numbered in the order they ran), plus any one-off
diagnostic scripts and their output. The result JSONs in `code/` are always the latest
run; earlier JSONs live in `_archive/code (...)/`.

All commands are run from `code/` with `.venv/bin/python`.

---

## 2026-09-09_v1_original

The original controller run (before the step-1 fixes). Its code and JSON results are in
`_archive/code (v1 - before step-1 fixes)/`.

| File | Command |
|---|---|
| `controller_run.log` | `run_controller.py` (bandit gamma 0.95, c 1.0; serial) |

Headline (test, mean of 8 clients, MAPE): bandit 5.31, deterministic 5.40, hindsight-best
single 5.43, equal-weight ensemble 10.85. Holt-Winters and SARIMA were broken (see below).

---

## 2026-10-22_step1_bugfixes

Step 1: the bug fixes, then a full re-run.

**Fixes (code changes):**
- `models.py` HoltWinters `_seed`: the seasonal profile was stored at the wrong phase slot
  (`seas[h]` instead of `seas[(lo+h) % m]`). This shifted the daily profile whenever the
  model re-seeded at an hour not divisible by 24 (test-boundary start, drift retrains).
- `models.py` SARIMA: it forecast `t - fit_at` steps ahead (up to 168 h) without ever
  seeing new observations. Now each realised value is filtered in (`res.extend`), so every
  forecast is one step ahead. There is also a sanity bound that falls back to seasonal-naive
  on a non-finite or out-of-range forecast (the val MAPE on MT_269 had been 9e9).
- `metrics.py` `recovery_times`: the old version (168 h window, baseline including the
  error build-up) returned 1 h for every client. The new one uses a 24 h window, a baseline
  ending one window before the alarm, and requires 12 h sustained.
- `run_baselines.py`: the default `--out` pointed to a non-existent `src/` folder.
- Both runners gained `--workers` (parallel clients). `run_controller.py` gained `--block`,
  `--gamma`, `--ucb-c`, `--no-bandit` and `--streams-out`. New `tune_bandit.py`.

| File | Command |
|---|---|
| `01_controller_val_run.log` | `run_controller.py --block val --no-bandit --workers 6 --out val_controller_results.json --streams-out val_streams.json` |
| `02_bandit_tuning.log` | `tune_bandit.py` (offline replay on `val_streams.json` -> `bandit_tuning.json`) |
| `03_controller_test_run.log` | `run_controller.py --gamma 0.995 --ucb-c 0.2 --workers 6` -> `controller_results.json` |
| `04_baseline_test_run.log` | `run_baselines.py --workers 6` -> `baseline_results.json` |
| `diagnostics/` | `hw_diag.py`, `hw_time.py`, `hw_m.py`, `sar.py`, which found the HW/SARIMA bugs. `before_fix_outputs.txt` has their original output; `after_fix_outputs.txt` has the re-run on the fixed code. |

Headline (test, mean of 8 clients, MAPE):

| Method | before | after |
|---|---|---|
| Holt-Winters | 29.8 | 9.6 |
| SARIMA | 19.4 | 6.0 (best single on 6/8 clients) |
| LightGBM | 5.55 | 5.80 |
| Validation-chosen single | 10.29 | 5.19 |
| Equal-weight ensemble | 10.86 | 6.14 |
| Controller, deterministic | 5.40 | 5.13 |
| Controller, + bandit | 5.31 | 5.01 |

Bandit tuning grid was flat (val MAPE 4.41-4.51 over all gamma x c). A per-step oracle
choosing blend vs. best model reaches 3.59 on val, which leaves room for a contextual agent.
Recovery time (new metric): median 3 h across clients, non-recovery 0-3%.

---

## 2026-10-22_step2_ops_accounting

Step 2: switching frequency, retraining frequency and compute overhead.

**Code changes (instrumentation only):** forecasts are unchanged, and accuracy reproduces step 1 exactly.
- `controller.py`: per-phase wall-clock (predict, update, drift retrain, scheduled retrain,
  control logic), per-model seconds, and refit counts by cause, in `diag["ops"]`.
- `metrics.py`: `operational_stats()` covers leader switches, blend-set changes, bandit
  arm flips, drift events, refits (total, per week) and the control-logic share of wall-clock.
- `run_baselines.py`: per-model ms/step and refit counts per strategy (`_ops`).
- `run_controller.py`: stores `ops` per controller variant and prints an OPERATIONS block.
- New `summarize_ops.py` writes `ops_summary.md` / `ops_summary.json`.

| File | Command |
|---|---|
| `00_smoke_controller.log`, `00_smoke_baselines.log` | 2 clients x 400 steps smoke tests |
| `01_controller_test_run.log` | `run_controller.py --workers 6` |
| `02_baseline_test_run.log` | `run_baselines.py --workers 6` |
| `03_summarize_ops.log` | `summarize_ops.py` |
| `04_drift_gap_check.log` | inline check of the gaps between drift alarms (MT_132) |
| `diagnostics/drift_calibration.py` (+ `_output.txt`) | replays ADWIN and Page-Hinkley separately, with a PH-threshold sweep |

Headline (mean of 8 clients, per week of test data):
- Controller: leader switches 1.8/wk, blend-set changes 2.0/wk, bandit arm flips 1.7/wk,
  refits 3.1/wk (equal-weight pool on a weekly schedule: 3.0/wk).
- Compute: 18 ms/step for the controller vs 18.3 for running the pool (0.99x). The control
  logic itself is 0.2-0.3% of wall-clock. SARIMA is about 92% of pool cost (16.9 ms/step);
  every other model is at or below 1.1 ms/step.
- **Problem found: drift detection is a de-facto weekly timer.** On MT_132 all 53
  gaps between alarms are exactly 168 h. ADWIN never fires (0 alarms). Page-Hinkley
  (threshold 3, min_instances 168) fires as soon as it is allowed after every reset. Alarms
  only become data-driven around threshold 25-50. Scheduled retrains never fire because
  the "drift" alarm always comes first. This was already the case in the v1 original run.

---

## 2026-10-22_step2b_drift_calibration

Fixing the drift detector found in step 2.

**Code changes:**
- `drift.py`: the residual is winsorised at `clip` before the detectors; Page-Hinkley
  `mode` is configurable (it was two-sided, so a *fall* in error triggered a retrain); all
  settings are passed in; detectors can be switched off. New defaults = "sparse": PH
  threshold 50, one-sided "up", min_instances 24, ADWIN delta 0.002, clip 10.
- `controller.py`: takes `drift_kw`. `run_controller.py` gained `--drift '<json>'` and `--no-drift`.
- New `tune_drift.py`: offline replay of the detectors on the val served-residual stream
  (alarm rate, timer share, lift) -> `drift_tuning.json`.

| File | Command |
|---|---|
| `01_tune_drift_replay.log` | `tune_drift.py` |
| `run_val_candidates.sh` | full val runs of the shortlist (all with clip 10, PH up, min 24) |
| `02..05_val_*.log` | frequent (PH 10 / ADWIN 0.05), medium (25 / 0.01), sparse (50 / 0.002), no drift -> `val_drift_*.json` |
| `06_val_candidates_summary.log` | comparison table of the val runs |
| `07_controller_test_sparse.log` | `run_controller.py --workers 6` (new defaults) -> `controller_results.json` |
| `08_controller_test_nodrift.log` | `run_controller.py --workers 6 --no-drift --diag-client none --out test_controller_nodrift.json` |
| `09_summarize_ops.log`, `10_test_comparison.log` | `summarize_ops.py`; three-way test comparison |

Results:
- Replay: with PH one-sided and threshold >= 25 (or min_instances 24) the timer pattern
  disappears. Alarms coincide with real error rises (lift 1.3-2.8x). ADWIN does fire on val.
- **Val: every setting ties** (MAPE 4.498-4.510, including no drift at all). With the 168 h
  scheduled retrain in place, drift-triggered retraining adds no accuracy on this data.
- Test (mean of 8 clients, MAPE): deterministic 5.13 / 5.10 / 5.14 and bandit
  5.01 / 5.01 / 5.06 for weekly-timer / calibrated / no drift. Differences are ~0.05 pt. The
  calibrated setting raises 0.21 alarms/wk and costs ~13% more refits than no drift.
- Recovery time is now meaningful: median 36-45 h after a (real) alarm, vs. the 3 h artefact
  that the timer produced.
- Step 2 results before this change: `../2026-10-22_step2_ops_accounting/controller_results_step2.json`.

---

## 2026-10-22_step3_baselines_ablations

Step 3: the missing baselines, existing adaptive methods and ablations. (The always-retrain
run finished on 2026-10-23, so it is filed here too.)

**Code changes:**
- `run_controller.py`: `--schedule`, `--topk` and `--demote-factor` (for retrain-every-step and the ablations).
- New `adaptive_baselines.py`: FTL, Hedge/EWA, DWM-style, MLpol and MELO (Wang, Goude & Yao
  2026, arXiv 2605.06541), replayed over the saved per-model streams. This is exact when drift
  is off, because the pool's forecasts then don't depend on the combiner. Hyper-parameters are
  tuned on val and frozen for test. MELO has a numerical safeguard (symmetrise P, cap its
  trace); see `diagnostics/melo_windup*`. Fixed-Share was implemented, then removed at the user's request.
- New `make_step3_table.py` writes `step3_comparison.md` / `.json` (the full table).

| File | Command |
|---|---|
| `00_smoke_always_retrain.log` | smoke test of `--schedule 1` |
| `01_controller_test_always_retrain.log` | `run_controller.py --schedule 1 --no-drift --no-bandit --workers 8 --diag-client none --out test_controller_always_retrain.json --streams-out test_streams_always_retrain.json` (~8 h wall) |
| `02_controller_val_nodrift_streams.log` | `run_controller.py --block val --no-drift --no-bandit --streams-out val_streams_nodrift.json` (tuning streams) |
| `03_controller_test_nodrift_streams.log` | `run_controller.py --no-drift --no-bandit --streams-out test_streams_nodrift.json` |
| `04_adaptive_baselines_synthetic_check.log`, `07_melo_synthetic_check.log` | sanity checks on synthetic data |
| `05`, `06`, `08`, `09` | development runs of `adaptive_baselines.py` (first grid, wider grid, MELO before/after the P fix) |
| `15_adaptive_baselines_final.log` | `adaptive_baselines.py` without Fixed-Share |
| `run_ablations.sh`, `10..14_ablation_*.log` | controller ablations -> `ablation_*.json` |
| `16_timing_probe_always_retrain_100steps.*` | 100-step timing probe under load (3.2 s/step, 94% SARIMA refits) |
| `17_adaptive_baselines_both_streams.log` | `adaptive_baselines.py --test test_streams_nodrift.json test_streams_always_retrain.json` |
| `18_step3_comparison.log` | `make_step3_table.py` |

Headline (test, mean of 8 clients, MAPE / CV-RMSE):
- Controller: rules only 5.10 / 6.65, + bandit 5.01 / 6.74. Val-chosen single 5.19 / 7.47, equal-weight ensemble 6.14 / 7.59.
- Weekly-refit pool: MELO 4.82 / 6.47 (best on every metric), DWM 4.98, MLpol 5.02 / 6.55, Hedge 5.13, FTL 5.20.
- Retrain every step: controller 4.93 / 6.49, but at 2,850 ms/step vs ~18 ms (~160x). MELO on
  that pool gets 4.68 / 6.26, the best overall.
- Ablations: all within 0.1 pt of the full system (k=1 5.01 but worse RMSE; no demotion 5.14; k=5 5.13; ADWIN-only 5.12; PH-only 5.10).
- Takeaway: the combiner is the weak point. MELO/MLpol-style weighting beats the
  inverse-error top-k blend on the same forecasts. This feeds step 5.

---

## 2026-10-24_melo_combiner

MELO becomes the controller's combiner, with hooks that let the controller reset it.

**Code changes:**
- New `combiners.py`: online `MELO` class (`predict(f_t)`, `update(y_t)`, `reset(regret_shrink, cov_reset)`).
  `adaptive_baselines.melo()` now replays this same class, so the offline baseline and the
  in-controller combiner are one implementation.
- `controller.py`: `combiner="blend"|"melo"`, `melo_eps0`, `melo_reset={"on": "alarm"|"refit", ...}`.
  Default behaviour is unchanged. `run_controller.py` gained `--combiner`, `--melo-eps0` and `--melo-reset`.
- `metrics.operational_stats` reports `combiner_resets`. `make_step3_table.py` has a MELO-combiner section.

| File | Command / content |
|---|---|
| `diagnostics/check_online_melo.py` (+ output) | online class vs. old batch MELO on test streams: max abs diff 2e-11, identical MAPE |
| `00_smoke_melo_combiner.log` | 2 clients x 400 steps, MELO + refit reset |
| `01_regression_blend_nodrift.log` (+ `.json`) | default controller, `--no-drift --no-bandit`: identical to `test_controller_nodrift.json` (MAPE diff 0.0) |
| `02_test_melo_nodrift.log` | `--combiner melo --no-drift --no-bandit` -> `test_controller_melo_nodrift.json`; identical to offline MELO (4.82) |
| `run_val_resets.sh`, `10..19_val_melo_*.log` | val sweep: drift on/off, reset on alarm/refit, regret shrink 0/0.5/1, covariance reset -> `val_melo_*.json` |
| `20_val_resets_summary.log` | val table (its "resets" column reads 0 because the field was added afterwards) |
| `21_test_melo_drift_noreset.log` | `--combiner melo` (calibrated drift) -> `test_controller_melo_drift.json` |
| `22_test_melo_alarm_cov.log` | `--combiner melo --melo-reset '{"on":"alarm","cov_reset":true}'` -> `test_controller_melo_alarm_cov.json` |
| `23_comparison_table.log` | `make_step3_table.py` (new section) |

Results (mean of 8 clients, MAPE / CV-RMSE):
- Val: old blend controller 4.51 / 6.20. MELO combiner: no drift 4.34 / 6.16, + drift 4.35 / 6.12,
  + alarm covariance reset 4.36 / 6.13. Other alarm resets 4.38-4.44. Resetting on every refit
  hurts (4.41-4.61), because it discards what MELO learned at every weekly refit.
- Test: MELO alone 4.82 / 6.47, MELO + drift retraining 4.80 / 6.33, + alarm covariance reset 4.81 / 6.38
  (11 resets per client). The old controller was 5.10 / 6.65 (+ bandit 5.01 / 6.74).
- Cost: 23.7 ms/step vs ~18 for the blend controller. Control logic is 1.3% of wall-clock.
- Takeaway: with MELO as the combiner the system matches or slightly beats MELO alone
  (CV-RMSE 6.33 vs 6.47). The reset hooks don't help on real data, where alarms are rare
  (~0.2/wk). Their real test is the step-4 shift experiment.

---

## 2026-10-24_step4_shift_experiment

Step 4: synthetic demand shifts injected at known times, and a redesigned alarm response.

**Code changes:**
- New `shifts.py`: scenarios `level` (x1.3, then back), `ramp` (to x1.3 over 4 weeks, then back),
  `amplitude` (daily cycle x1.6, then back) and `temporary` (x1.4 for one week, twice). There are
  two events per client: test at block start + 2016 h and + 5544 h; val at + 1008 h and + 2688 h.
  `run_controller.py --shift <scenario>` (any block).
- `metrics.shift_metrics`: detection delay, false alarms/wk, MAPE over the 168 h / 672 h after
  each event, the week-after/week-before MAE ratio, and recovery on relative error. `operational_stats`
  counts follow-up refits.
- `models.py`: `retrain(t, since=None)` can start the window at a change point.
- `controller.py` `alarm_response` (`--alarm-response '{}'`): follow-up refits at alarm
  +24/+72/+168 h on normal windows, plus a fast error EWMA for a week. An optional change-point
  cut (`cut`, `scope`, `min_window`) was rejected on validation (below).
- New `make_step4_table.py` writes `step4_comparison.md` / `.json`. Results are in `code/step4_results/`
  (test) and `code/step4_val/` (val).

| File | Content |
|---|---|
| `diagnostics/check_shifts_output.txt` | the scenarios do what they claim (multipliers, untouched history) |
| `diagnostics/event_error_profile.py` (+ output) | per-model error by week around event 1, and detector delays for 3 settings |
| `run_step4.sh`, `run_step4_progress.log`, `<scenario>__<variant>.log` | main test grid (daily refit, no drift, drift with the old response) |
| `v1_scope_all/` | first version of the response (cut on all refits, 168 h minimum window), plus the 2-client smoke tests. Rejected: worse overall (e.g. no shift 5.10 -> 5.24). The covariance-reset runs there failed (xargs stripped the JSON quotes). |
| `run_step4_val.sh`, `run_step4_val_round2.sh`, `val/*.log`, `val/summary_round{1,2}.log` | val tuning: 10 variants x (4 shifts + none) |
| `val/check_new_default_level_melo.log` | the new code default `{}` reproduces the val follow-up run exactly |
| `run_step4_final.sh`, `run_step4_final_progress.log`, `*__*_drift_follow.log` | final test pass with the chosen response |
| `91_step4_table_final.log` | `make_step4_table.py` |

Validation (mean over 4 shifts + none, MAPE / CV-RMSE):
- MELO: no drift 7.256 / 6.640, drift + plain refit 7.283 / 6.577, cut response 8.36 / 6.69,
  + cov reset 8.31 / 6.67, **follow-ups 7.238 / 6.544** (chosen).
- Blend: plain refit 7.788 / 6.743, cut 8.51 / 6.84, follow-ups 6.807 / 6.682.
- The cut response loses even in the week right after an event: 168 h of data makes SARIMA /
  LightGBM much weaker, and every false alarm triggers it.

Test (overall MAPE / CV-RMSE, mean of 8 clients):

| | none | level | ramp | amplitude | temporary | refits/wk |
|---|---|---|---|---|---|---|
| MELO alone | 4.82 / 6.47 | 4.90 / 6.61 | 4.86 / 6.50 | 8.70 / 7.68 | 4.94 / 6.80 | 3.0 |
| MELO + drift + follow-ups (proposed) | 4.80 / 6.33 | 4.86 / 6.45 | 4.82 / 6.39 | 9.20 / 7.58 | 4.89 / 6.56 | 4.4 |
| MELO, daily refit | - | 4.84 / 6.48 | 4.80 / 6.39 | 8.95 / 7.59 | 4.88 / 6.57 | 21.0 |

- The proposed system beats MELO alone on CV-RMSE in every scenario and on MAPE in every one
  except amplitude. The amplitude MAPE is distorted by MT_135, whose near-zero hours become
  ~0 under the stretch: post-event MAPE 50-86% on that client alone.
- It matches daily-refit MELO on CV-RMSE with ~5x fewer refits.
- Detection (default detector): 11-15/16 for level / temporary, 7-10/16 for ramp / amplitude.
  False alarms ~0.2/wk. Delay is median 12-60 h for the sudden shifts.
- Recovery after temporary shocks: 102 h vs 149 h for MELO alone.
- Blend controller with follow-ups: no shift 5.10 -> 5.06. Weeks after amplitude: 14.4% -> 10.8%.
- The differences are small (0.02-0.05 MAPE, 0.1-0.25 CV-RMSE) and no significance test has been run yet.

---

## 2026-10-24_step5_contextual_agent

Step 5: a contextual serving agent on top of the proposed system, plus significance tests.

**Code changes:**
- New `agent.py`: `ContextBuilder` (causal features: hour sin/cos, weekend, holiday, candidate
  disagreement, fast/slow EWMA of each candidate's scaled loss, each candidate's deviation from
  MELO, 24 h / 168 h level change, recency of the last alarm and refit) and `ContextualSelector`
  (full-information contextual bandit: per-candidate RLS model of the next loss with forgetting,
  shared covariance with a trace cap; `argmin` with a margin or `soft` softmin mixing).
  Candidates: [MELO output, 5 pool models].
- `controller.py` `agent_kw` (`run_controller.py --agent '<json>'`, needs `--no-bandit`): serves
  the agent's forecast, and the drift monitor watches its residual. Streams now include `served`.
- New `tune_agent.py`: offline replay on val streams (alarm / refit clocks reconstructed) ->
  `agent_tuning.json`. Selection rule: mean over scenarios of per-client MAPE relative to MELO,
  because MT_135's near-zero hours dominate plain MAPE means.
- New `significance.py`: Diebold-Mariano (Newey-West lag 24, HLN correction) on absolute,
  squared and absolute-percentage loss, plus a Wilcoxon signed-rank test across series.
- New `make_step5_table.py` -> `step5_comparison.md` / `.json`. Results are in `code/step5_results/`;
  val streams are in `code/step5_streams/`.

| File | Content |
|---|---|
| `run_val_streams.sh`, `01_*.log` | val streams of the proposed system (none + 4 shifts) |
| `02_tune_agent.log` | first tuning (selection by plain mean MAPE, dominated by MT_135; superseded) |
| `03_tune_agent_rel.log` | tuning with the relative-MAPE rule. Chosen: soft, forget 0.999, temp 0.3 (val rel. MAPE 0.979, CV-RMSE 6.576 vs MELO 6.544) |
| `04_tune_agent_with_sq.log` | + squared-loss target: clearly worse (rel. MAPE 1.02-1.11) |
| `05_val_none_agent_inloop.log` | in-loop agent on val, no shift: MAPE 4.20 (MELO 4.33), CV-RMSE 6.09 (= MELO) |
| `run_step5_test.sh`, `10_*.log` | final test: agent and proposed (rerun with streams) x 5 scenarios |
| `20_step5_table.log` | `make_step5_table.py` |
| `diagnostics/significance_sanity.txt` | DM / Wilcoxon sanity check on synthetic data |

Test (MAPE / CV-RMSE, mean of 8 clients):

| | none | level | ramp | amplitude | temporary |
|---|---|---|---|---|---|
| MELO alone | 4.82 / 6.47 | 4.90 / 6.61 | 4.86 / 6.50 | 8.70 / 7.68 | 4.94 / 6.80 |
| proposed (no agent) | 4.80 / 6.33 | 4.86 / 6.45 | 4.82 / 6.39 | 9.20 / 7.58 | 4.89 / 6.56 |
| proposed + agent | 4.70 / 6.34 | 4.75 / 6.45 | 4.74 / 6.40 | 8.38 / 7.59 | 4.79 / 6.58 |

Significance (40 client x scenario series; Wilcoxon p across series):
- Proposed vs MELO alone: better on absolute (p 0.005), squared (0.006) and % error (0.017).
  It is never significantly worse in any of the 40 series. **This is the robust result.**
- Agent vs MELO alone: better overall (p 0.01-0.04), but significantly worse in 5-8 series.
- Agent vs proposed: not significant on any loss (p 0.25-0.33). The agent lowers mean MAPE by
  ~0.1 pt (~2%) while MAE rises slightly, so it trades absolute for percentage accuracy. Its
  gain is inconsistent across series. Report it as an exploratory extension, not the headline.

---

## 2026-10-25_step6_wrapup

Step 6: the demo, figures, consolidated results and reproducibility files.

**Code changes:**
- `run_controller.py`: per-step diagnostics are now written even with `--no-bandit` (before, only
  in bandit runs). They gain the combiner output, refit flags, shift events and the agent's weights;
  `--diag-out FILE`. Instrumentation only: the demo run reproduces the step-5 test numbers exactly.
- `controller.py` / `agent.py`: record `refit_any`, `agent_weights` and `agent_candidates`.
- New `make_final_figs.py` -> `figures_final/` (5 figures). New `make_results_summary.py` ->
  `results_summary.md`. New `requirements.txt` and `code/README.md`.

| File | Content |
|---|---|
| `01_demo_run_level_MT_163.log` | final system, level shift, diagnostics for MT_163 (first demo pick; replaced, its diag file deleted) |
| `03_demo_event_choice.log` | per-event MAPE change vs MELO over the 336 h after each level shift. The demo uses the median of the 10 detected events (MT_132, event 2), not a hand-picked one |
| `04_demo_run_level_MT_132.log` | same run with diagnostics for MT_132 -> `step5_results/demo_diag_MT_132_level.json` |
| `02_make_final_figs.log`, `05_figs_v2.log` | figure renders (v2 = layout fixes and the new demo event) |
| `06_results_summary.log` | `make_results_summary.py` |

Notes:
- In the 336 h right after a level shift, the agent beats MELO in 8 of 16 events and loses in 8.
  Its overall MAPE gain comes mostly from normal periods.
- Colour palette: reference categorical slots in fixed order. The palette validator needs node,
  which is not installed, so the documented validation of that order was relied on.

### 2026-10-25 (continued): paper.docx updated to the final system

- `paper/paper.docx` was rewritten for the final system. Backup: `_archive/paper (before step-6 update)/paper.docx`.
  - Abstract, index terms, contributions and the Fig. 1 caption.
  - III.C: drift calibration paragraph.
  - III.D: MELO (16)–(18), drift response, contextual agent (19)–(21), new Algorithms 1–2. The old top-3 blend / demotion / bandit equations are gone. Numbering is unchanged.
  - III.E: recovery-time definition (26) now matches the shift metric, plus a shift-experiment and significance paragraph.
  - IV: new Table II (17 methods incl. refits/wk), new Tables III (shifts) and IV (Diebold–Mariano), subsections C–F, Figs. 2–6. Old Figs. 2–7 and the "bandit deferred" note removed.
  - New V. Conclusion. References [28]–[31] added (MLpol, Cesa-Bianchi & Lugosi, Diebold–Mariano, Littlestone & Warmuth).
- Figures: `paper/architecture_pictorial_v2.png` (updated `make_architecture_pictorial.py`, data from
  `step5_results/demo_diag_MT_132_none.json`, run logged as `07_diag_run_none_MT_132.log`). Column-width paper
  figures are in `paper/figures_v2/` (`make_paper_figs_v2.py`, `08_paper_figs_v2.log`).
- `paper_update/`: `edit_paper.py` (the editing script; it starts from the archived backup, so it can be rerun),
  `omml.py` (LaTeX-subset -> Word equation converter), `paper_numbers.json` (every number used, computed from
  the result files), and `paper_text_after_update.txt` (text dump used for proofreading).
- Checks: the docx schema validator passes. It was not rendered visually, because LibreOffice is not installed.

### 2026-10-29: explainer doc + SAGE naming in figures_final (interim name at the time)
- `Project_Explainer.docx` (project root): a plain-language project guide, built by `2026-10-25_step6_wrapup/make_explainer.py`.
- The final system is called **SAGE** (Agentic MELO) in `figures_final/` and the explainer. MAPE is labelled as the primary metric, and the per-client figure now leads with MAPE and includes a note on MT_135. The previous figures and script are in `_archive/figures_final (before SAGE naming)/`.
- Per-client test MAPE: SAGE beats MELO on 4/8 clients. MT_135 (12.48 → 11.53) accounts for nearly all of the mean gain (4.82 → 4.70).
- paper.docx and paper/figures_v2 are unchanged.
- Later the same day: the hourly-refit rows were removed from `results_summary.md`, `make_results_summary.py` and the explainer. The user's reasoning was that hourly refitting isn't a feasible operating point. `figures_final/fig5_cost_vs_accuracy.png` was dropped and archived. The underlying run (`test_controller_always_retrain.json`) is kept. paper.docx is not changed yet.
- Also 2026-10-29: paper.docx was rebuilt with `paper_update/edit_paper.py`, run as before from the pre-step-6 backup. The changes:
  - The final system is named SAGE.
  - MAPE is stated as the primary metric.
  - The hourly-refit rows are gone from Table II, and the cost figure (old Fig. 6) is removed.
  - Fig. 3 now shows per-client MAPE, and the text notes MT_135.
  - The column-width figures were regenerated (`make_paper_figs_v2.py`, without fig_cost).
  - `paper_numbers.json` gained `per_client_mape`, `n_agent_better_mape` and `melo_daily_rpw`.
  - The docx validator passes.
  - The previous paper, figures and scripts are in `_archive/paper (step-6, before SAGE naming)/`.

## 2026-10-29_sage_cases: renamed to SAGE, no-agent variant dropped, case studies
- The final system is named **SAGE** (Self-Adaptive aGEntic forecaster) everywhere: figures, paper, explainer and results_summary. A short-lived interim name, SAGE, was replaced the same day.
- The no-agent variant was dropped from every table and figure. One ablation sentence stays in paper IV-F and in the summary and explainer: the agent's own gain is not significant, p 0.25–0.33.
- **Diagnostic runs** (`diag_MT_105.log`, `diag_MT_135.log`):
  - Hour-by-hour SAGE diagnostics for the two clients with the largest gains, in `code/step6_cases/`.
  - Command: `run_controller.py --no-bandit --workers 1 --only <client> --combiner melo --alarm-response '{}' --agent '{"mode":"soft","forget":0.999,"temp":0.3}' --shift none --diag-client <client>`.
  - The served MAPE and CV-RMSE match `step5_results/none__agent.json`.
  - A new `--only` option was added to run_controller.py.
- **MT_105:** CV-RMSE 5.79 vs 6.93 for MELO.
  - The cause is a real fivefold load jump on 23 Oct 2014, test day 314.
  - In MELO's weekly-refit pool SARIMA fell back to the old level at +9 h, and MELO's experts overshot to 1,993 kW against 824 actual. That one hour is 84% of the squared-error gain.
  - Without it, CV-RMSE is still 5.80 vs 5.99.
  - SAGE's agent moved to SARIMA within 5 h, and alarms at +7 h and +15 h triggered refits.
- **MT_135:** MAPE 11.53 vs 12.48.
  - This client has an inverted night-peak profile. In the bottom-quartile load hours, MELO's bias is +12.7 kW against SAGE's +9.2, and MAPE is 17.7% against 14.1%.
  - The agent raises the seasonal-naive weight there from 0.16 to 0.30, and leans on LightGBM at 08:00 and 19:00–21:00.
- **SAGE's own shift detection** (the paper previously quoted the no-agent run):
  - level 10/16, 25 h
  - ramp 5/16, 157 h
  - amplitude 9/16, 81 h
  - temporary 14/16, 30 h
  - false alarms 0.20 per week
  - Recovery vs MELO: temporary 133 vs 149 h, level 138 vs 114 h.
- **Figures:**
  - `figures_final/` was rebuilt: fig1 adds the single models; fig2 adds DWM, MLpol and daily-refit MELO; fig4 adds the best single model and MLpol. The new fig5 and fig6 are the case studies.
  - `paper/figures_v2/` gained `fig_case_105` and `fig_case_135`.
- **Paper:** paper.docx gained section IV-E "Where SAGE Helps Most" with Figs. 6–7. Significance moved to IV-F and "What did not work" to IV-G.
- **Explainer:** written to `Project_Explainer_SAGE.docx`, because `Project_Explainer.docx` was open in Word.
- **Archive:** the previous versions are in `_archive/interim version, before SAGE rename (2026-10-29)/`.
- 2026-10-29: `Code_Explainer.docx` (project root) is a guided tour of the code, built by `2026-10-25_step6_wrapup/make_code_explainer.py`.


## 2026-10-29: project tidy-up
- `code/logs/` → `logs/` (project root).
- 75 result files → `code/results/<topic>/` with readable names (full map in `RENAMES.md`). Scripts were updated, and the migration script is `2026-10-29_sage_cases/tidy_up.py`.
- Table, summary and figure scripts → `code/reporting/`. Each gained a `sys.path` line so it still imports the core modules from `code/`.
- **Verification:** all step-3/4/5 tables, the ops summary and `results_summary.md` were regenerated from the new locations and are byte-identical to the pre-tidy versions. All current figures were regenerated, and a 300-step SAGE smoke run worked.
- **Backup:** `_archive/before tidy-up (2026-10-29)/`.

## 2026-10-30: top-5 comparison charts and pictorial architecture (paper Fig. 2)
- The per-client chart and the shift chart now compare SAGE with the four strongest baselines on real-data MAPE: MELO, DWM, MLpol and Hedge. The shift chart also keeps daily-refit MELO. Changes are in `reporting/make_final_figs.py` (`TOP`, `per_client()`, `shift_rel()`) and `make_paper_figs_v2.py`.
- Per-client: SAGE has lower CV-RMSE than Hedge, DWM and MLpol on all 8 clients, and lower MAPE on 7/8. On MT_269, DWM gets 3.1517 against SAGE's 3.1525.
- New `reporting/make_architecture_icons.py`:
  - A layered icon diagram (data, model pool, MELO, agent, serve/watch/retrain), at single-column width.
  - It writes `paper/architecture_icons.png` and `figures_final/fig0_architecture_icons.png`.
  - The agent's bars are SAGE's real mean weights on MT_132 after the warm-up: MELO 0.27, SARIMA 0.21, LightGBM 0.18, online 0.15, other two 0.18.
- Fig. 1's small evaluation chart is relabelled from "Ours" to "SAGE".
- **paper.docx:**
  - The new diagram is inserted as Fig. 2 with a caption and a sentence pointing to it.
  - The old Figs. 2–7 are renumbered 3–8.
  - The per-client and shift captions and text name Hedge, DWM, MLpol and MELO.
  - The validator passes.
  - The previous script is in `_archive/edit_paper_before_fig2_icons.py`.
- `Project_Explainer.docx`: the per-client table now shows the top-5 methods, and the icon diagram is added.

## 2026-10-30_paper_layout: fixing gaps in paper.docx (checked against Word's own rendering)
- **Renderer:** the paper is exported with the installed Microsoft Word over COM (`render.ps1`), then rasterised with Windows' built-in PDF renderer (`pdf2png.ps1`). `render.sh` runs the whole loop. These are the first real Word renders of the paper. Before/after contact sheets are in `renders/` (v1 = before, v8 = final), and the final PDF is `paper_render_final.pdf`.
- **Fixes in `paper_update/edit_paper.py`:**
  - **Redundant section break removed:** a 2-column section break just after Fig. 2 made Word balance the columns around the tall figure.
  - **Fig. 2 moved:** it now comes after the notation paragraph, so text fills page 4 under Fig. 1. That page used to be mostly empty.
  - **Figures kept together:** each figure has keep-with-next, and each caption has keep-lines.
  - **Table I** starts on a new page with its caption.
  - **Shorter figures:** Figs. 5–8 were made shorter at the same width, in `reporting/make_paper_figs_v2.py`.
  - **Fig. 6 caption** shortened.
- **Result:** 12 → 11 pages. The one remaining gap is about 1/5 of a column at the bottom right of page 9, where Fig. 8 doesn't fit. The validator passes.

## 2026-10-30: submission package and GitHub repository
- `paper.docx`: "Dataset Link" and "GitHub Link" were added after the References as live hyperlinks (UCI page and https://github.com/xSanchitMx/sage-load-forecasting). The validator passes. `paper/paper.pdf` is Word's own export of that docx.
- `submission/23BCE5126/` holds the Word and PDF copies, and `submission/23BCE5126.zip` is the folder zipped. These are kept out of git.
- **Git repository** at the project root:
  - The whitelist `.gitignore` covers code, results, logs, paper, explainers and the hourly CSV. It leaves out personal drafts, research PDFs, `_archive/`, the venv and the 711 MB raw file.
  - The new `README.md` is the repo front page.
  - The new `Dataset/download_dataset.py` downloads the full UCI original and the LSTNet hourly file and rebuilds the CSV. It was checked to reproduce the committed CSV exactly.
- `Code_Explainer.docx` was rebuilt, because it was missing from the folder.
