# Step 4: injected demand shifts (test block, mean over 8 clients)

Two events per client per scenario (shifts.py). MAPE_168 / MAPE_672 = MAPE over the 168 h / 672 h after each event; ratio_168 = MAE in the week after / week before (a +30% level shift alone gives ~1.3). Recovery = hours until the relative error is back within 25% of its pre-event level (capped at 672 h; 'not rec.' counts events that never got there). Detection = alarms within 336 h of an event.

## level

| Method | MAPE | CV-RMSE | MAPE 168h | MAPE 672h | ratio 168h | recovery h | not rec. | detected | delay h | false/wk | refits/wk |
|---|---|---|---|---|---|---|---|---|---|---|---|
| equal-weight ensemble (weekly refit) | 6.34 | 7.90 | 10.62 | 7.51 | 3.93 | 211.75 | 0.00 | 0/16 | - | 0.00 | 2.96 |
| equal-weight ensemble (daily refit) | 6.35 | 7.75 | 9.31 | 7.22 | 3.00 | 195.06 | 0.00 | 0/16 | - | 0.00 | 20.97 |
| blend controller, no drift | 5.26 | 6.84 | 6.20 | 5.81 | 1.82 | 174.38 | 0.00 | 0/16 | - | 0.00 | 2.96 |
| blend controller + drift (old response) | 5.20 | 6.76 | 5.80 | 5.68 | 1.66 | 109.12 | 0.00 | 12/16 | 58.44 | 0.21 | 3.40 |
| blend controller + drift + follow-up refits | 5.16 | 6.71 | 5.64 | 5.56 | 1.60 | 119.12 | 0.00 | 13/16 | 55.94 | 0.22 | 4.63 |
| blend controller, daily refit | 5.14 | 6.76 | 5.61 | 5.55 | 1.67 | 120.56 | 0.00 | 0/16 | - | 0.00 | 20.97 |
| MELO alone (= MELO combiner, no drift) | 4.90 | 6.61 | 5.22 | 5.39 | 1.56 | 114.44 | 1.00 | 0/16 | - | 0.00 | 2.96 |
| MELO combiner + drift (old response) | 4.86 | 6.49 | 5.11 | 5.35 | 1.54 | 96.75 | 1.00 | 11/16 | 45.14 | 0.19 | 3.35 |
| MELO combiner + drift + follow-up refits (proposed) | 4.86 | 6.45 | 5.13 | 5.33 | 1.53 | 96.56 | 1.00 | 11/16 | 45.07 | 0.20 | 4.45 |
| ftl (weekly refit) | 5.29 | 7.54 | 6.84 | 5.94 | 2.18 | 184.12 | 0.00 | 0/16 | - | 0.00 | 2.96 |
| hedge (weekly refit) | 5.24 | 7.21 | 6.80 | 5.88 | 2.17 | 189.62 | 0.00 | 0/16 | - | 0.00 | 2.96 |
| dwm (weekly refit) | 5.07 | 7.04 | 6.13 | 5.69 | 1.91 | 168.31 | 1.00 | 0/16 | - | 0.00 | 2.96 |
| mlpol (weekly refit) | 5.15 | 6.71 | 6.01 | 5.79 | 1.76 | 182.62 | 1.00 | 0/16 | - | 0.00 | 2.96 |
| melo (weekly refit) | 4.90 | 6.61 | 5.22 | 5.39 | 1.56 | 114.44 | 1.00 | 0/16 | - | 0.00 | 2.96 |
| ftl (daily refit) | 5.16 | 7.43 | 6.05 | 5.69 | 2.06 | 204.50 | 0.00 | 0/16 | - | 0.00 | 20.97 |
| hedge (daily refit) | 5.09 | 7.07 | 5.82 | 5.56 | 1.96 | 158.31 | 0.00 | 0/16 | - | 0.00 | 20.97 |
| dwm (daily refit) | 4.95 | 7.05 | 5.52 | 5.41 | 1.65 | 149.19 | 0.00 | 0/16 | - | 0.00 | 20.97 |
| mlpol (daily refit) | 5.01 | 6.60 | 5.53 | 5.47 | 1.66 | 124.00 | 1.00 | 0/16 | - | 0.00 | 20.97 |
| melo (daily refit) | 4.84 | 6.48 | 5.03 | 5.25 | 1.54 | 89.62 | 1.00 | 0/16 | - | 0.00 | 20.97 |

## ramp

| Method | MAPE | CV-RMSE | MAPE 168h | MAPE 672h | ratio 168h | recovery h | not rec. | detected | delay h | false/wk | refits/wk |
|---|---|---|---|---|---|---|---|---|---|---|---|
| equal-weight ensemble (weekly refit) | 6.22 | 7.60 | 5.64 | 6.58 | 1.25 | 30.62 | 1.00 | 0/16 | - | 0.00 | 2.96 |
| equal-weight ensemble (daily refit) | 6.27 | 7.56 | 5.62 | 6.58 | 1.21 | 30.50 | 1.00 | 0/16 | - | 0.00 | 20.97 |
| blend controller, no drift | 5.20 | 6.72 | 4.20 | 5.26 | 1.12 | 26.38 | 0.00 | 0/16 | - | 0.00 | 2.96 |
| blend controller + drift (old response) | 5.16 | 6.68 | 4.23 | 5.26 | 1.12 | 28.19 | 0.00 | 6/16 | 144.30 | 0.20 | 3.35 |
| blend controller + drift + follow-up refits | 5.14 | 6.63 | 4.20 | 5.24 | 1.11 | 27.31 | 1.00 | 6/16 | 176.75 | 0.22 | 4.49 |
| blend controller, daily refit | 5.11 | 6.66 | 4.12 | 5.16 | 1.11 | 55.62 | 0.00 | 0/16 | - | 0.00 | 20.97 |
| MELO alone (= MELO combiner, no drift) | 4.86 | 6.50 | 4.05 | 5.03 | 1.10 | 41.12 | 0.00 | 0/16 | - | 0.00 | 2.96 |
| MELO combiner + drift (old response) | 4.83 | 6.43 | 4.00 | 5.01 | 1.10 | 36.00 | 0.00 | 8/16 | 149.10 | 0.21 | 3.37 |
| MELO combiner + drift + follow-up refits (proposed) | 4.82 | 6.39 | 4.01 | 5.00 | 1.10 | 50.62 | 0.00 | 7/16 | 118.80 | 0.21 | 4.45 |
| ftl (weekly refit) | 5.24 | 7.37 | 4.33 | 5.42 | 1.29 | 44.81 | 0.00 | 0/16 | - | 0.00 | 2.96 |
| hedge (weekly refit) | 5.19 | 7.06 | 4.28 | 5.30 | 1.23 | 39.69 | 0.00 | 0/16 | - | 0.00 | 2.96 |
| dwm (weekly refit) | 5.04 | 6.94 | 4.12 | 5.19 | 1.12 | 29.56 | 0.00 | 0/16 | - | 0.00 | 2.96 |
| mlpol (weekly refit) | 5.08 | 6.58 | 4.15 | 5.26 | 1.11 | 29.56 | 0.00 | 0/16 | - | 0.00 | 2.96 |
| melo (weekly refit) | 4.86 | 6.50 | 4.05 | 5.03 | 1.10 | 41.12 | 0.00 | 0/16 | - | 0.00 | 2.96 |
| ftl (daily refit) | 5.13 | 7.26 | 4.18 | 5.32 | 1.22 | 46.50 | 1.00 | 0/16 | - | 0.00 | 20.97 |
| hedge (daily refit) | 5.06 | 6.95 | 4.09 | 5.18 | 1.16 | 33.62 | 1.00 | 0/16 | - | 0.00 | 20.97 |
| dwm (daily refit) | 4.92 | 6.98 | 4.06 | 5.07 | 1.12 | 51.94 | 0.00 | 0/16 | - | 0.00 | 20.97 |
| mlpol (daily refit) | 4.97 | 6.49 | 4.03 | 5.12 | 1.09 | 30.00 | 1.00 | 0/16 | - | 0.00 | 20.97 |
| melo (daily refit) | 4.80 | 6.39 | 3.98 | 4.94 | 1.10 | 45.94 | 0.00 | 0/16 | - | 0.00 | 20.97 |

## amplitude

| Method | MAPE | CV-RMSE | MAPE 168h | MAPE 672h | ratio 168h | recovery h | not rec. | detected | delay h | false/wk | refits/wk |
|---|---|---|---|---|---|---|---|---|---|---|---|
| equal-weight ensemble (weekly refit) | 12.12 | 8.98 | 18.25 | 18.36 | 1.89 | 87.62 | 7.00 | 0/16 | - | 0.00 | 2.96 |
| equal-weight ensemble (daily refit) | 11.99 | 8.88 | 15.80 | 16.87 | 1.66 | 85.25 | 6.00 | 0/16 | - | 0.00 | 20.97 |
| blend controller, no drift | 9.67 | 8.02 | 12.70 | 14.88 | 1.64 | 32.56 | 7.00 | 0/16 | - | 0.00 | 2.96 |
| blend controller + drift (old response) | 9.65 | 7.96 | 12.05 | 14.42 | 1.56 | 30.31 | 7.00 | 9/16 | 86.19 | 0.18 | 3.34 |
| blend controller + drift + follow-up refits | 9.13 | 7.90 | 11.18 | 10.76 | 1.54 | 54.38 | 6.00 | 10/16 | 86.56 | 0.20 | 4.47 |
| blend controller, daily refit | 9.39 | 7.94 | 10.99 | 13.96 | 1.52 | 31.88 | 7.00 | 0/16 | - | 0.00 | 20.97 |
| MELO alone (= MELO combiner, no drift) | 8.70 | 7.68 | 9.87 | 11.20 | 1.46 | 25.94 | 7.00 | 0/16 | - | 0.00 | 2.96 |
| MELO combiner + drift (old response) | 9.04 | 7.60 | 8.64 | 15.13 | 1.45 | 25.56 | 7.00 | 9/16 | 86.50 | 0.19 | 3.31 |
| MELO combiner + drift + follow-up refits (proposed) | 9.20 | 7.58 | 8.55 | 16.42 | 1.44 | 13.00 | 8.00 | 9/16 | 92.31 | 0.19 | 4.37 |
| ftl (weekly refit) | 11.41 | 8.65 | 14.53 | 26.55 | 1.85 | 33.25 | 7.00 | 0/16 | - | 0.00 | 2.96 |
| hedge (weekly refit) | 11.29 | 8.34 | 14.54 | 26.04 | 1.76 | 21.25 | 8.00 | 0/16 | - | 0.00 | 2.96 |
| dwm (weekly refit) | 9.73 | 8.22 | 12.47 | 17.05 | 1.68 | 64.44 | 7.00 | 0/16 | - | 0.00 | 2.96 |
| mlpol (weekly refit) | 10.25 | 7.82 | 12.70 | 19.66 | 1.60 | 69.88 | 6.00 | 0/16 | - | 0.00 | 2.96 |
| melo (weekly refit) | 8.70 | 7.68 | 9.87 | 11.20 | 1.46 | 25.94 | 7.00 | 0/16 | - | 0.00 | 2.96 |
| ftl (daily refit) | 10.62 | 8.50 | 10.68 | 21.98 | 1.59 | 18.88 | 8.00 | 0/16 | - | 0.00 | 20.97 |
| hedge (daily refit) | 10.54 | 8.19 | 10.60 | 21.76 | 1.57 | 18.88 | 8.00 | 0/16 | - | 0.00 | 20.97 |
| dwm (daily refit) | 9.85 | 8.24 | 10.40 | 16.59 | 1.53 | 42.62 | 7.00 | 0/16 | - | 0.00 | 20.97 |
| mlpol (daily refit) | 10.20 | 7.71 | 10.58 | 20.27 | 1.49 | 57.94 | 7.00 | 0/16 | - | 0.00 | 20.97 |
| melo (daily refit) | 8.95 | 7.59 | 8.40 | 13.30 | 1.43 | 41.81 | 7.00 | 0/16 | - | 0.00 | 20.97 |

## temporary

| Method | MAPE | CV-RMSE | MAPE 168h | MAPE 672h | ratio 168h | recovery h | not rec. | detected | delay h | false/wk | refits/wk |
|---|---|---|---|---|---|---|---|---|---|---|---|
| equal-weight ensemble (weekly refit) | 6.61 | 8.67 | 11.01 | 9.45 | 5.87 | 327.19 | 0.00 | 0/16 | - | 0.00 | 2.96 |
| equal-weight ensemble (daily refit) | 6.60 | 8.35 | 8.98 | 8.99 | 4.29 | 318.19 | 0.00 | 0/16 | - | 0.00 | 20.97 |
| blend controller, no drift | 5.36 | 7.04 | 5.98 | 6.53 | 2.38 | 178.56 | 0.00 | 0/16 | - | 0.00 | 2.96 |
| blend controller + drift (old response) | 5.27 | 6.91 | 5.67 | 6.24 | 2.20 | 138.62 | 0.00 | 15/16 | 28.25 | 0.21 | 3.44 |
| blend controller + drift + follow-up refits | 5.25 | 6.87 | 5.39 | 6.23 | 2.10 | 91.19 | 0.00 | 15/16 | 28.88 | 0.21 | 4.67 |
| blend controller, daily refit | 5.21 | 6.92 | 5.54 | 6.05 | 2.20 | 138.62 | 0.00 | 0/16 | - | 0.00 | 20.97 |
| MELO alone (= MELO combiner, no drift) | 4.94 | 6.80 | 5.08 | 5.74 | 2.06 | 148.75 | 0.00 | 0/16 | - | 0.00 | 2.96 |
| MELO combiner + drift (old response) | 4.91 | 6.59 | 5.07 | 5.63 | 2.06 | 122.88 | 0.00 | 13/16 | 12.29 | 0.20 | 3.38 |
| MELO combiner + drift + follow-up refits (proposed) | 4.89 | 6.56 | 5.00 | 5.62 | 2.03 | 101.75 | 0.00 | 13/16 | 16.57 | 0.20 | 4.55 |
| ftl (weekly refit) | 5.38 | 7.89 | 6.61 | 6.62 | 2.99 | 219.31 | 0.00 | 0/16 | - | 0.00 | 2.96 |
| hedge (weekly refit) | 5.34 | 7.59 | 6.64 | 6.60 | 2.99 | 245.00 | 1.00 | 0/16 | - | 0.00 | 2.96 |
| dwm (weekly refit) | 5.19 | 7.23 | 6.34 | 6.34 | 2.72 | 234.31 | 0.00 | 0/16 | - | 0.00 | 2.96 |
| mlpol (weekly refit) | 5.27 | 6.91 | 5.74 | 6.40 | 2.25 | 138.94 | 1.00 | 0/16 | - | 0.00 | 2.96 |
| melo (weekly refit) | 4.94 | 6.80 | 5.08 | 5.74 | 2.06 | 148.75 | 0.00 | 0/16 | - | 0.00 | 2.96 |
| ftl (daily refit) | 5.21 | 7.71 | 5.99 | 6.07 | 2.71 | 144.94 | 1.00 | 0/16 | - | 0.00 | 20.97 |
| hedge (daily refit) | 5.16 | 7.38 | 5.82 | 5.97 | 2.66 | 163.06 | 0.00 | 0/16 | - | 0.00 | 20.97 |
| dwm (daily refit) | 5.03 | 7.22 | 5.81 | 5.99 | 2.29 | 141.38 | 0.00 | 0/16 | - | 0.00 | 20.97 |
| mlpol (daily refit) | 5.09 | 6.74 | 5.38 | 5.96 | 2.13 | 97.06 | 1.00 | 0/16 | - | 0.00 | 20.97 |
| melo (daily refit) | 4.88 | 6.57 | 4.99 | 5.52 | 2.04 | 92.44 | 1.00 | 0/16 | - | 0.00 | 20.97 |

## none

| Method | MAPE | CV-RMSE | MAPE 168h | MAPE 672h | ratio 168h | recovery h | not rec. | detected | delay h | false/wk | refits/wk |
|---|---|---|---|---|---|---|---|---|---|---|---|
| blend controller, no drift | 5.14 | 6.70 | - | - | - | - | - | - | - | - | 2.96 |
| blend controller + drift (old response) | 5.10 | 6.65 | - | - | - | - | - | - | - | - | 3.34 |
| blend controller + drift + follow-up refits | 5.06 | 6.60 | - | - | - | - | - | - | - | - | 4.40 |
| MELO alone (= MELO combiner, no drift) | 4.82 | 6.47 | - | - | - | - | - | - | - | - | 2.96 |
| MELO combiner + drift (old response) | 4.80 | 6.33 | - | - | - | - | - | - | - | - | 3.35 |
| MELO combiner + drift + follow-up refits (proposed) | 4.80 | 6.33 | - | - | - | - | - | - | - | - | 4.35 |
