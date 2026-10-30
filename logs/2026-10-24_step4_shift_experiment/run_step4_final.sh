#!/bin/bash
# Step 4 final test pass with the alarm response chosen on validation (default {} =
# follow-up refits at +24/+72/+168 h on normal windows + fast error EWMA). Run from code/.
L=logs/2026-10-24_step4_shift_experiment
R=step4_results
job() {
  local sc=$1 v=$2; shift 2
  .venv/bin/python run_controller.py --no-bandit --workers 4 --diag-client none \
      --shift $sc --out $R/${sc}__${v}.json "$@" > $L/${sc}__${v}.log 2>&1
  echo "$(date +%H:%M) done $sc $v"
}
for sc in level ramp amplitude temporary none; do
  for v in blend_drift_follow melo_drift_follow; do
    while [ "$(jobs -rp | wc -l)" -ge 3 ]; do wait -n; done
    case $v in
      blend_drift_follow) job $sc $v --alarm-response '{}' & ;;
      melo_drift_follow)  job $sc $v --combiner melo --alarm-response '{}' & ;;
    esac
  done
done
wait
echo "$(date +%H:%M) all done"
