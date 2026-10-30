#!/bin/bash
# Step 4 tuning of the alarm response on the VALIDATION block with injected shifts
# (shifts.py "val" offsets) plus no shift. Run from code/. Up to 3 runs at a time.
# The selection rule: lowest mean val MAPE over the five scenarios (incl. "none").
L=logs/2026-10-24_step4_shift_experiment/val
R=step4_val
job() {  # job <scenario> <variant> [run_controller args...]
  local sc=$1 v=$2; shift 2
  .venv/bin/python run_controller.py --block val --no-bandit --workers 4 --diag-client none \
      --shift $sc --out $R/${sc}__${v}.json "$@" > $L/${sc}__${v}.log 2>&1
  echo "$(date +%H:%M) done $sc $v"
}
for sc in level ramp amplitude temporary none; do
  for v in blend_nodrift blend_drift blend_resp blend_resp_nofast melo_nodrift melo_drift melo_resp melo_resp_cov; do
    while [ "$(jobs -rp | wc -l)" -ge 3 ]; do wait -n; done
    case $v in
      blend_nodrift)     job $sc $v --no-drift & ;;
      blend_drift)       job $sc $v & ;;
      blend_resp)        job $sc $v --alarm-response '{}' & ;;
      blend_resp_nofast) job $sc $v --alarm-response '{"fast_hold": 0}' & ;;
      melo_nodrift)      job $sc $v --combiner melo --no-drift & ;;
      melo_drift)        job $sc $v --combiner melo & ;;
      melo_resp)         job $sc $v --combiner melo --alarm-response '{}' & ;;
      melo_resp_cov)     job $sc $v --combiner melo --alarm-response '{}' --melo-reset '{"on":"alarm","cov_reset":true}' & ;;
    esac
  done
done
wait
echo "$(date +%H:%M) all done"
