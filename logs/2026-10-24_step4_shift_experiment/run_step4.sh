#!/bin/bash
# Step 4 grid (run from code/). Every run: test block, 8 clients, deterministic arm only,
# calibrated drift (drift.py defaults) unless --no-drift. Results -> step4_results/<scenario>__<variant>.json
# Up to 3 runs at a time (4 workers each; RAM-bound). Daily-retrain runs use 4 workers too.
L=logs/2026-10-24_step4_shift_experiment
R=step4_results
job() {  # job <scenario> <variant> [run_controller args...]
  sc=$1; v=$2; shift 2
  .venv/bin/python run_controller.py --no-bandit --workers 4 --diag-client none --shift $sc \
      --out $R/${sc}__${v}.json "$@" > $L/${sc}__${v}.log 2>&1
  echo "$(date +%H:%M) done $sc $v"
}
export -f job; export L R
{
for sc in level ramp amplitude temporary; do
  echo "$sc daily_retrain --no-drift --schedule 24 --streams-out $R/${sc}__daily_retrain_streams.json"
done
for sc in level ramp amplitude temporary; do
  echo "$sc blend_nodrift --no-drift --streams-out $R/${sc}__blend_nodrift_streams.json"
  echo "$sc blend_drift"
  echo "$sc blend_drift_resp --alarm-response {}"
  echo "$sc melo_nodrift --combiner melo --no-drift"
  echo "$sc melo_drift --combiner melo"
  echo "$sc melo_drift_resp --combiner melo --alarm-response {}"
  echo "$sc melo_drift_resp_cov --combiner melo --alarm-response {} --melo-reset {\"on\":\"alarm\",\"cov_reset\":true}"
done
echo "none blend_drift"
echo "none blend_drift_resp --alarm-response {}"
echo "none melo_drift_resp --combiner melo --alarm-response {}"
echo "none melo_drift_resp_cov --combiner melo --alarm-response {} --melo-reset {\"on\":\"alarm\",\"cov_reset\":true}"
} | xargs -P 3 -L 1 bash -c 'job "$@"' _
