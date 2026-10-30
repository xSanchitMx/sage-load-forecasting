# Step 3 comparison (test block, mean over 8 clients)

## Static baselines (weekly scheduled refit)

| Method | MAE | RMSE | CV-RMSE % | MAPE % |
|---|---|---|---|---|
| seasonal_naive | 135.28 | 206.08 | 13.61 | 9.62 |
| holt_winters | 107.40 | 151.85 | 9.96 | 9.63 |
| sarima | 75.19 | 117.30 | 7.92 | 6.25 |
| lightgbm | 78.36 | 125.68 | 7.86 | 5.55 |
| online_linear | 84.95 | 121.83 | 7.69 | 6.17 |
| validation-chosen single | 73.54 | 115.17 | 7.47 | 5.19 |
| equal-weight ensemble | 79.51 | 117.90 | 7.59 | 6.14 |
| hindsight-best single (oracle, not deployable) | 72.79 | 111.49 | 7.01 | 5.24 |

## Retraining policy (rules-only controller)

| Method | MAE | RMSE | CV-RMSE % | MAPE % |
|---|---|---|---|---|
| weekly schedule only (no drift) | 69.91 | 105.49 | 6.70 | 5.14 |
| weekly schedule + calibrated drift | 69.70 | 105.18 | 6.65 | 5.10 |
| retrain every step | 68.23 | 103.14 | 6.49 | 4.93 |
| equal-weight ensemble, retrain every step | 83.69 | 122.12 | 7.94 | 6.88 |

## Existing adaptive combiners, pool with weekly refit

| Method | MAE | RMSE | CV-RMSE % | MAPE % |
|---|---|---|---|---|
| ftl | 72.84 | 111.82 | 7.36 | 5.20 |
| hedge ({"eta": 0.01}) | 70.98 | 108.66 | 7.11 | 5.13 |
| dwm ({"beta": 0.5}) | 68.69 | 106.53 | 6.96 | 4.98 |
| mlpol | 68.17 | 103.22 | 6.55 | 5.02 |
| melo ({"eps0": 0.01}) | 66.50 | 101.37 | 6.47 | 4.82 |

## Existing adaptive combiners, pool with refit every step

| Method | MAE | RMSE | CV-RMSE % | MAPE % |
|---|---|---|---|---|
| ftl | 69.46 | 107.01 | 6.64 | 4.85 |
| hedge ({"eta": 0.01}) | 68.88 | 105.73 | 6.55 | 4.84 |
| dwm ({"beta": 0.5}) | 67.32 | 104.58 | 6.54 | 4.79 |
| mlpol | 66.21 | 100.87 | 6.31 | 4.77 |
| melo ({"eps0": 0.01}) | 65.54 | 100.19 | 6.26 | 4.68 |

## Proposed controller and ablations (weekly refit + calibrated drift)

| Method | MAE | RMSE | CV-RMSE % | MAPE % |
|---|---|---|---|---|
| full (k=3, demotion, ADWIN+PH) | 69.70 | 105.18 | 6.65 | 5.10 |
| + bandit (main result) | 69.84 | 106.54 | 6.74 | 5.01 |
| no drift, + bandit | 69.93 | 106.71 | 6.76 | 5.06 |
| no demotion | 69.91 | 105.56 | 6.67 | 5.14 |
| k = 1 | 69.88 | 107.30 | 6.81 | 5.01 |
| k = 5 | 70.16 | 105.67 | 6.67 | 5.13 |
| ADWIN only | 69.81 | 105.61 | 6.71 | 5.12 |
| Page-Hinkley only | 69.74 | 105.06 | 6.64 | 5.10 |

## Controller with the MELO combiner (weekly refit)

| Method | MAE | RMSE | CV-RMSE % | MAPE % |
|---|---|---|---|---|
| MELO combiner, no drift (= MELO alone) | 66.50 | 101.37 | 6.47 | 4.82 |
| MELO combiner + drift-triggered retraining | 66.53 | 101.21 | 6.33 | 4.80 |
| MELO combiner + drift retraining + covariance reset on alarm | 66.61 | 101.81 | 6.38 | 4.81 |
