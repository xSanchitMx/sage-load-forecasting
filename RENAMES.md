# Renamed files (2026-10-29)

The project was reorganised so the folder layout explains itself. Nothing was deleted, and every result is byte-for-byte the same: all tables and the summary were regenerated from the new locations and compared with the old ones. A full copy of the old layout is in `_archive/before tidy-up (2026-10-29)/`.

## What moved

- `code/logs/` → **`logs/`** (project root)
- About 75 loose result files in `code/` → **`code/results/<topic>/`**, with readable names
- The final system's files use the name **SAGE**. The interim name A-MELO is gone everywhere except inside archived copies.
- Every script in `code/` was updated to the new paths. The old `.sh` run scripts in `logs/` are kept as a record of what was run, so they still show the old names.
- Inside `results/baselines/online_combiners.json` the result keys follow the new forecast file names: `test_streams_nodrift` → `pool_forecasts_test`, `test_streams_always_retrain` → `pool_forecasts_test_hourly_refit`.

## New layout

```
logs/                         run logs, one folder per session (index: logs/README.md)
code/
  *.py                        the system and its runners (run_controller, run_baselines, tune_*)
  reporting/                  scripts that only make tables, the summary and figures
  results_summary.md          headline numbers
  figures_final/              full-width figures
  results/
    sage/                     SAGE on real data and each shift; sage_without_agent_* = ablation
      hourly_detail/          hour-by-hour diagnostics (demo and case-study figures)
    baselines/                static baselines, online combiners (FTL, Hedge, DWM, MLpol, MELO)
    melo/                     MELO run inside the controller (alone / + drift)
    initial_controller/       our first design and its ablations
    shift_experiment/         step-4 grid: <scenario>__<variant>.json
    forecasts/                saved per-hour pool forecasts (inputs for replaying combiners)
    tuning/                   drift, bandit and agent tuning
    summaries/                step-3/4/5 comparison tables, ops summary
    validation/               validation-block runs
paper/                        paper.docx and its figures
_archive/                     older versions
```

Scenario names in file names: `none` = real data with no injected shift; `level`, `ramp`, `amplitude`, `temporary` = the injected shifts.

## Old name → new name

### SAGE (the final system)

| Old (in `code/`) | New (in `code/`) |
|---|---|
| `step5_results/amplitude__agent.json` | `results/sage/sage_amplitude.json` |
| `step5_results/amplitude__agent_streams.json` | `results/sage/sage_amplitude_forecasts.json` |
| `step5_results/amplitude__proposed.json` | `results/sage/sage_without_agent_amplitude.json` |
| `step5_results/amplitude__proposed_streams.json` | `results/sage/sage_without_agent_amplitude_forecasts.json` |
| `step5_results/demo_diag_MT_132_level.json` | `results/sage/hourly_detail/sage_MT_132_level.json` |
| `step5_results/demo_diag_MT_132_none.json` | `results/sage/hourly_detail/sage_MT_132_none.json` |
| `step5_results/level__agent.json` | `results/sage/sage_level.json` |
| `step5_results/level__agent_streams.json` | `results/sage/sage_level_forecasts.json` |
| `step5_results/level__proposed.json` | `results/sage/sage_without_agent_level.json` |
| `step5_results/level__proposed_streams.json` | `results/sage/sage_without_agent_level_forecasts.json` |
| `step5_results/none__agent.json` | `results/sage/sage_none.json` |
| `step5_results/none__agent_streams.json` | `results/sage/sage_none_forecasts.json` |
| `step5_results/none__proposed.json` | `results/sage/sage_without_agent_none.json` |
| `step5_results/none__proposed_streams.json` | `results/sage/sage_without_agent_none_forecasts.json` |
| `step5_results/ramp__agent.json` | `results/sage/sage_ramp.json` |
| `step5_results/ramp__agent_streams.json` | `results/sage/sage_ramp_forecasts.json` |
| `step5_results/ramp__proposed.json` | `results/sage/sage_without_agent_ramp.json` |
| `step5_results/ramp__proposed_streams.json` | `results/sage/sage_without_agent_ramp_forecasts.json` |
| `step5_results/temporary__agent.json` | `results/sage/sage_temporary.json` |
| `step5_results/temporary__agent_streams.json` | `results/sage/sage_temporary_forecasts.json` |
| `step5_results/temporary__proposed.json` | `results/sage/sage_without_agent_temporary.json` |
| `step5_results/temporary__proposed_streams.json` | `results/sage/sage_without_agent_temporary_forecasts.json` |
| `step6_cases/diag_MT_105_none.json` | `results/sage/hourly_detail/sage_MT_105_none.json` |
| `step6_cases/diag_MT_135_none.json` | `results/sage/hourly_detail/sage_MT_135_none.json` |
| `step6_cases/run_MT_105_none.json` | `results/sage/hourly_detail/sage_MT_105_none_run.json` |
| `step6_cases/run_MT_135_none.json` | `results/sage/hourly_detail/sage_MT_135_none_run.json` |

### Baselines

| Old (in `code/`) | New (in `code/`) |
|---|---|
| `adaptive_baselines_results.json` | `results/baselines/online_combiners.json` |
| `baseline_results.json` | `results/baselines/static_baselines.json` |

### MELO runs inside the controller

| Old (in `code/`) | New (in `code/`) |
|---|---|
| `test_controller_melo_alarm_cov.json` | `results/melo/melo_with_drift_reset_on_alarm.json` |
| `test_controller_melo_drift.json` | `results/melo/melo_with_drift.json` |
| `test_controller_melo_nodrift.json` | `results/melo/melo_alone.json` |

### Initial controller and its ablations

| Old (in `code/`) | New (in `code/`) |
|---|---|
| `ablation_adwin_only.json` | `results/initial_controller/ablation_adwin_only.json` |
| `ablation_k1.json` | `results/initial_controller/ablation_top1.json` |
| `ablation_k5.json` | `results/initial_controller/ablation_top5.json` |
| `ablation_no_demotion.json` | `results/initial_controller/ablation_no_demotion.json` |
| `ablation_ph_only.json` | `results/initial_controller/ablation_page_hinkley_only.json` |
| `controller_diag_MT_132.json` | `results/initial_controller/initial_controller_hourly_MT_132.json` |
| `controller_results.json` | `results/initial_controller/initial_controller.json` |
| `test_controller_always_retrain.json` | `results/initial_controller/initial_controller_hourly_refit.json` |
| `test_controller_nodrift.json` | `results/initial_controller/initial_controller_no_drift.json` |

### Shift experiment (test)

| Old (in `code/`) | New (in `code/`) |
|---|---|
| `step4_results` | `results/shift_experiment` |

### Saved per-hour forecasts

| Old (in `code/`) | New (in `code/`) |
|---|---|
| `test_streams_always_retrain.json` | `results/forecasts/pool_forecasts_test_hourly_refit.json` |
| `test_streams_nodrift.json` | `results/forecasts/pool_forecasts_test.json` |
| `val_streams.json` | `results/forecasts/initial_controller_forecasts_val.json` |
| `val_streams_nodrift.json` | `results/forecasts/pool_forecasts_val.json` |

### Tuning

| Old (in `code/`) | New (in `code/`) |
|---|---|
| `agent_tuning.json` | `results/tuning/agent_tuning.json` |
| `bandit_tuning.json` | `results/tuning/bandit_tuning.json` |
| `drift_tuning.json` | `results/tuning/drift_tuning.json` |

### Summary tables

| Old (in `code/`) | New (in `code/`) |
|---|---|
| `ops_summary.json` | `results/summaries/ops_summary.json` |
| `ops_summary.md` | `results/summaries/ops_summary.md` |
| `step3_comparison.json` | `results/summaries/step3_baselines_and_ablations.json` |
| `step3_comparison.md` | `results/summaries/step3_baselines_and_ablations.md` |
| `step4_comparison.json` | `results/summaries/step4_shift_experiment.json` |
| `step4_comparison.md` | `results/summaries/step4_shift_experiment.md` |
| `step5_comparison.json` | `results/summaries/step5_sage_vs_melo.json` |
| `step5_comparison.md` | `results/summaries/step5_sage_vs_melo.md` |
| `val_vs_test.json` | `results/summaries/val_vs_test.json` |

### Validation runs

| Old (in `code/`) | New (in `code/`) |
|---|---|
| `step4_val` | `results/validation/shift_experiment` |
| `step5_streams` | `results/validation/agent_tuning_forecasts` |
| `val_controller_nodrift.json` | `results/validation/val_controller_nodrift.json` |
| `val_controller_results.json` | `results/validation/val_controller_results.json` |
| `val_drift_frequent.json` | `results/validation/val_drift_frequent.json` |
| `val_drift_medium.json` | `results/validation/val_drift_medium.json` |
| `val_drift_nodrift.json` | `results/validation/val_drift_nodrift.json` |
| `val_drift_sparse.json` | `results/validation/val_drift_sparse.json` |
| `val_melo_alarm_cov.json` | `results/validation/val_melo_alarm_cov.json` |
| `val_melo_alarm_r05.json` | `results/validation/val_melo_alarm_r05.json` |
| `val_melo_alarm_r05_cov.json` | `results/validation/val_melo_alarm_r05_cov.json` |
| `val_melo_alarm_r1_cov.json` | `results/validation/val_melo_alarm_r1_cov.json` |
| `val_melo_drift_noreset.json` | `results/validation/val_melo_drift_noreset.json` |
| `val_melo_nodrift.json` | `results/validation/val_melo_nodrift.json` |
| `val_melo_refit_cov.json` | `results/validation/val_melo_refit_cov.json` |
| `val_melo_refit_r05.json` | `results/validation/val_melo_refit_r05.json` |
| `val_melo_refit_r05_cov.json` | `results/validation/val_melo_refit_r05_cov.json` |
| `val_melo_refit_r1_cov.json` | `results/validation/val_melo_refit_r1_cov.json` |

### Archive folders

| Old | New |
|---|---|
| `_archive/figures_final_before_amelo/` (+ `make_final_figs_before_amelo.py`) | `_archive/figures_final (before SAGE naming)/` |
| `_archive/paper (step-6, before A-MELO rename)/` | `_archive/paper (step-6, before SAGE naming)/` |
| `_archive/before SAGE rename (2026-10-29)/` | `_archive/interim version, before SAGE rename (2026-10-29)/` |

The script that did the move is `logs/2026-10-29_sage_cases/tidy_up.py`.

### Reporting scripts

The scripts that only produce tables, the summary and figures moved from `code/` to `code/reporting/`. Run them from `code/` as `.venv/bin/python reporting/<script>.py`. Their outputs and output locations are unchanged.

`make_architecture.py`, `make_architecture_pictorial.py`, `make_demo_plot.py`, `make_final_figs.py`, `make_paper_figs.py`, `make_paper_figs_v2.py`, `make_results_summary.py`, `make_step3_table.py`, `make_step4_table.py`, `make_step5_table.py`, `make_val_vs_test.py`, `summarize_ops.py`
