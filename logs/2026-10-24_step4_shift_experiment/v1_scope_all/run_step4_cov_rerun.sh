#!/bin/bash
# Rerun of the 5 covariance-reset jobs from run_step4.sh: there xargs stripped the double
# quotes from the --melo-reset JSON, so those jobs failed at argument parsing.
L=logs/2026-10-24_step4_shift_experiment
R=step4_results
for sc in level ramp amplitude temporary none; do
  .venv/bin/python run_controller.py --no-bandit --workers 4 --diag-client none --shift $sc \
      --combiner melo --alarm-response '{}' --melo-reset '{"on":"alarm","cov_reset":true}' \
      --out $R/${sc}__melo_drift_resp_cov.json > $L/${sc}__melo_drift_resp_cov.log 2>&1 &
  [ $sc = ramp ] || [ $sc = temporary ] && wait
done
wait
