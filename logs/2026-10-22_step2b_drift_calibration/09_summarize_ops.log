# Operational summary (test block, mean over 8 clients)

Rates are per week (168 h) of test data. ms/step = mean wall-clock per hourly step; cost vs pool = relative to running all five models with scheduled retraining (the equal-weight ensemble).

| Method | MAPE % | CV-RMSE % | leader switches/wk | refits/wk | ms/step | cost vs pool |
|---|---|---|---|---|---|---|
| seasonal_naive | 9.62 | 13.61 | 0.00 | 0.00 | 0.00 | 0.00x |
| holt_winters | 9.63 | 9.96 | 0.00 | 0.99 | 0.01 | 0.00x |
| sarima | 6.25 | 7.92 | 0.00 | 0.99 | 16.86 | 0.92x |
| lightgbm | 5.55 | 7.86 | 0.00 | 0.99 | 1.13 | 0.06x |
| online_linear | 6.17 | 7.69 | 0.00 | 0.00 | 0.27 | 0.01x |
| val-chosen single | 5.19 | 7.47 | 0.00 | 0.99 | 13.19 | 0.72x |
| equal-weight ensemble | 6.14 | 7.59 | 0.00 | 2.96 | 18.28 | 1.00x |
| controller (deterministic) | 5.10 | 6.65 | 1.98 | 3.34 | 20.25 | 1.11x |
| controller (+ bandit) | 5.01 | 6.74 | 1.73 | 3.38 | 19.30 | 1.06x |

## Controller detail

| | deterministic | + bandit |
|---|---|---|
| blendset_changes_per_week | 1.98 | 2.21 |
| arm_switches_per_week | 0.00 | 1.75 |
| drift_per_week | 0.21 | 0.25 |
| refits_drift_share | 19% | 22% |
| control_share | 0.18% | 0.29% |
| ms/step: predict | 1.49 | 1.44 |
| ms/step: update | 2.76 | 2.66 |
| ms/step: retrain_drift | 3.20 | 3.23 |
| ms/step: retrain_scheduled | 12.76 | 11.92 |
| ms/step: control | 0.04 | 0.05 |
