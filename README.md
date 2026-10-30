# SAGE: Real-Time Self-Adaptive Agentic Intelligence for Electricity Load Forecasting Under Dynamic Demand Shifts

Predictive Analytics project, VIT Chennai. Sanchit Mukherjee (23BCE5126).

**SAGE** (Self-Adaptive aGEntic forecaster) forecasts hourly electricity load for individual
customers and adapts on its own when demand changes. Each hour:

1. five forecasters (seasonal-naive, Holt-Winters, SARIMA, LightGBM, online linear) predict the next hour;
2. **MELO** (MLpol + 16 bias-correcting experts) combines them;
3. a **contextual agent** mixes MELO and the five models, using 28 features of the current situation;
4. a **drift watchdog** (ADWIN + Page–Hinkley) watches the forecast error and, on an alarm,
   retrains the models now and again 1, 3 and 7 days later.

Evaluated prequentially (forecast, then learn) on 8 customers of the UCI ElectricityLoadDiagrams20112014
dataset, over a one-year test period:

| Method | MAPE % | CV-RMSE % |
|---|---|---|
| Best single model (chosen on validation) | 5.19 | 7.47 |
| DWM | 4.98 | 6.96 |
| MLpol | 5.02 | 6.55 |
| MELO (2026) | 4.82 | 6.47 |
| **SAGE** | **4.70** | **6.34** |

SAGE is significantly more accurate than MELO (Diebold–Mariano / Wilcoxon, p = 0.01–0.04), beats it in
all four injected demand-shift scenarios, and refits its models about 4 times a week.
Full results: [`code/results_summary.md`](code/results_summary.md). Paper: [`paper/paper.pdf`](paper/paper.pdf).

## Repository layout

```
code/                 the system, runners and tuning scripts (see code/README.md)
  reporting/          scripts that make the tables, summary and figures
  results/            every result file, one folder per topic
  figures_final/      full-width figures
  results_summary.md  headline numbers
Dataset/              hourly dataset used by the code + download script for the full original
logs/                 console logs of every experiment run (index: logs/README.md)
paper/                the paper (Word + PDF) and its figures
Project_Explainer.docx, Code_Explainer.docx   plain-language guides to the project and the code
```

## Dataset

- Source: UCI Machine Learning Repository, ElectricityLoadDiagrams20112014 (ID 321),
  https://archive.ics.uci.edu/dataset/321/electricityloaddiagrams20112014
- `Dataset/electricity_hourly_2012_2014.csv` (in this repo) is the file the code reads: 2012–2014,
  hourly, 321 clients. It is the standard hourly packaging of the UCI data (LSTNet release).
- The complete original (370 clients, 15-minute readings, 711 MB unzipped) is over GitHub's file-size
  limit, so it is downloaded rather than stored:

```bash
python Dataset/download_dataset.py            # full UCI original + hourly file, rebuilds the CSV
python Dataset/download_dataset.py --skip-raw # hourly file only
```

## Running it

```bash
cd code
python3.14 -m venv .venv
.venv/bin/pip install -r requirements.txt

# SAGE on the real test data (all 8 clients in parallel)
.venv/bin/python run_controller.py --no-bandit --workers 8 --combiner melo \
    --alarm-response '{}' --agent '{"mode": "soft", "forget": 0.999, "temp": 0.3}' \
    --shift none --out results/sage/sage_none.json --streams-out results/sage/sage_none_forecasts.json

# quick demo: one client, first 2,000 hours
.venv/bin/python run_controller.py --no-bandit --workers 1 --only MT_105 --combiner melo \
    --alarm-response '{}' --agent '{"mode": "soft", "forget": 0.999, "temp": 0.3}' \
    --max-steps 2000 --out results/demo.json
```

`code/README.md` lists every script, option and result file. Tables and figures are rebuilt from the saved
results with the scripts in `code/reporting/`.
