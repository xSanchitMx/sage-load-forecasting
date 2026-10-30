#!/bin/bash
# Round 2 of the step-4 validation sweep: follow-up refits (+24/+72/+168 h) on the models'
# NORMAL windows (min_window huge => no change-point cut). Blend keeps the fast error
# EWMA for a week; MELO does not use it. Run from code/.
L=logs/2026-10-24_step4_shift_experiment/val
R=step4_val
job() {
  local sc=$1 v=$2; shift 2
  .venv/bin/python run_controller.py --block val --no-bandit --workers 4 --diag-client none \
      --shift $sc --out $R/${sc}__${v}.json "$@" > $L/${sc}__${v}.log 2>&1
  echo "$(date +%H:%M) done $sc $v"
}
for sc in level ramp amplitude temporary none; do
  for v in blend_follow melo_follow; do
    while [ "$(jobs -rp | wc -l)" -ge 3 ]; do wait -n; done
    case $v in
      blend_follow) job $sc $v --alarm-response '{"min_window": 1000000}' & ;;
      melo_follow)  job $sc $v --combiner melo --alarm-response '{"min_window": 1000000, "fast_hold": 0}' & ;;
    esac
  done
done
wait
echo "$(date +%H:%M) all done"
