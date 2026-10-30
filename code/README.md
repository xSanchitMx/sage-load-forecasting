# SAGE: real-time self-adaptive agentic load forecasting (code)

Hourly electricity-load forecasting for 8 UCI ElectricityLoadDiagrams clients. Evaluation is
prequential: each hour is forecast first, then its true value is revealed and used for
learning. The final system, **SAGE** (Self-Adaptive aGEntic forecaster), combines a pool of five
models with MELO, detects demand shifts with ADWIN + Page–Hinkley, retrains on alarms (now and
at +24/+72/+168 h), and uses a contextual agent to re-weight the forecasts each hour.

The headline numbers are in **`results_summary.md`**, and the figures are in **`figures_final/`**.
Every run's console output is kept in `../logs/` (index: `../logs/README.md`). `../RENAMES.md`
maps the file names used before the 2026-10-29 reorganisation to the current ones.

## Setup

```bash
cd code
python3.14 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

The data file `../Dataset/electricity_hourly_2012_2014.csv` must be present. All commands below
run from `code/` with `.venv/bin/python` (reporting scripts as `.venv/bin/python reporting/<script>.py`). Runs use one thread per worker (`--workers N` runs N
clients in parallel; each needs about 230 MB of RAM).

## Modules

| File | What it does |
|---|---|
| `data_pipeline.py` | loading, stratified selection of 8 clients (seed 42), calendar features, 50/15/35 warm/val/test split |
| `models.py` | the pool: seasonal-naive, Holt-Winters, SARIMA, LightGBM, online linear (river) |
| `drift.py` | ADWIN + Page-Hinkley on the clipped, scale-normalised served residual |
| `combiners.py` | online MELO (MLpol + 16 multi-scale EWLS correction experts) |
| `agent.py` | contextual serving agent (full-information contextual bandit, RLS) |
| `controller.py` | the prequential loop: combiner, drift alarms, refits (scheduled, on alarm, follow-ups), agent or bandit |
| `shifts.py` | injected demand-shift scenarios (level, ramp, amplitude, temporary) |
| `metrics.py` | MAE / RMSE / CV-RMSE / MAPE, recovery, shift metrics, operational stats |
| `significance.py` | Diebold-Mariano (Newey-West) and Wilcoxon signed-rank tests |
| `run_controller.py` | runs the controller for every client (CLI below) |
| `run_baselines.py` | static baselines (single models, val-chosen single, equal-weight ensemble) |
| `adaptive_baselines.py` | FTL, Hedge, DWM, MLpol, MELO replayed over saved pool forecasts |
| `tune_bandit.py`, `tune_drift.py`, `tune_agent.py` | offline tuning on the validation block |
| `reporting/` | tables, summary and figures (not part of the system): `make_step3_table.py` … `make_step5_table.py`, `make_results_summary.py`, `make_final_figs.py`, `make_paper_figs_v2.py`, `summarize_ops.py`, `make_architecture_pictorial.py`, plus older figure scripts |

## Reproducing SAGE

SAGE on the real test data (`--shift none`):

```bash
.venv/bin/python run_controller.py --no-bandit --workers 8 --combiner melo \
    --alarm-response '{}' --agent '{"mode": "soft", "forget": 0.999, "temp": 0.3}' \
    --shift none --out results/sage/sage_none.json --streams-out results/sage/sage_none_forecasts.json
```

Use `--shift level|ramp|amplitude|temporary` for the shift scenarios (outputs
`results/sage/sage_<scenario>.json`). Drop `--agent ...` for the ablation without the agent
(`results/sage/sage_without_agent_<scenario>.json`).

Other results:

| Result | Command → output |
|---|---|
| static baselines | `run_baselines.py --workers 6` → `results/baselines/static_baselines.json` |
| initial controller (blend, ± bandit) | `run_controller.py --workers 6` → `results/initial_controller/initial_controller.json` |
| pool forecasts for replays | `run_controller.py --no-drift --no-bandit --streams-out results/forecasts/pool_forecasts_test.json` (and `--block val ... results/forecasts/pool_forecasts_val.json`) |
| FTL / Hedge / DWM / MLpol / MELO | `adaptive_baselines.py` → `results/baselines/online_combiners.json` |
| MELO alone inside the controller | `run_controller.py --combiner melo --no-drift --no-bandit --out results/melo/melo_alone.json` |
| shift grid (step 4) | `../logs/2026-10-24_step4_shift_experiment/run_step4*.sh` (old paths; outputs now live in `results/shift_experiment/`) |
| agent tuning | `tune_agent.py` (reads `results/validation/agent_tuning_forecasts/`) |
| case-study diagnostics | `run_controller.py ... --only MT_105 --diag-client MT_105 --diag-out results/sage/hourly_detail/sage_MT_105_none.json` |
| tables, summary, figures | `reporting/make_step3_table.py`, `reporting/make_step4_table.py`, `reporting/make_step5_table.py`, `reporting/make_results_summary.py`, `reporting/make_final_figs.py`, `reporting/make_paper_figs_v2.py` |

Useful `run_controller.py` options:
- `--block val|test`
- `--combiner blend|melo`
- `--no-drift`, `--drift '<json>'`
- `--alarm-response '<json>'`
- `--melo-reset '<json>'`
- `--agent '<json>'` (needs `--no-bandit`)
- `--schedule H`, `--topk K`, `--demote-factor F`
- `--shift S`
- `--only MT_105,MT_135` (run selected clients only)
- `--max-steps N` (quick smoke run)
- `--streams-out FILE`
- `--diag-client ID --diag-out FILE` (per-step diagnostics for one client)

## Where results live

| Path | Content |
|---|---|
| `results/sage/` | SAGE on real data and each shift, plus `sage_without_agent_*` (ablation); `hourly_detail/` has per-hour diagnostics |
| `results/baselines/` | static baselines and online combiners |
| `results/melo/` | MELO run inside the controller (alone, with drift) |
| `results/initial_controller/` | our first design (top-3 blend + bandit) and its ablations |
| `results/shift_experiment/` | step-4 grid, `<scenario>__<variant>.json` |
| `results/forecasts/` | saved per-hour pool forecasts, used to replay combiners quickly |
| `results/tuning/`, `results/validation/` | tuning grids and validation-block runs |
| `results/summaries/` | step-3/4/5 comparison tables and the ops summary |
| `results_summary.md`, `figures_final/` | consolidated results and figures |
| `../logs/` | console logs of every run, with `../logs/README.md` as the index |

Scenario names in file names: `none` = real data, no injected shift.
