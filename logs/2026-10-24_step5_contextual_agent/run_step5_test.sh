#!/bin/bash
# Step 5 final test pass (run from code/). For each scenario (none + 4 shifts):
#   agent      : MELO combiner + drift + follow-up refits + contextual agent (chosen on val)
#   proposed   : same without the agent (= step-4 melo_drift_follow, rerun to save streams)
# Streams (incl. the served forecast) feed the significance tests.
L=logs/2026-10-24_step5_contextual_agent
R=step5_results
AG='{"mode": "soft", "forget": 0.999, "temp": 0.3}'
job() {
  local sc=$1 v=$2; shift 2
  .venv/bin/python run_controller.py --no-bandit --workers 4 --diag-client none \
      --combiner melo --alarm-response '{}' --shift $sc \
      --out $R/${sc}__${v}.json --streams-out $R/${sc}__${v}_streams.json "$@" \
      > $L/10_test_${sc}__${v}.log 2>&1
  echo "$(date +%H:%M) done $sc $v"
}
for sc in none level ramp amplitude temporary; do
  for v in agent proposed; do
    while [ "$(jobs -rp | wc -l)" -ge 3 ]; do wait -n; done
    if [ $v = agent ]; then job $sc $v --agent "$AG" & else job $sc $v & fi
  done
done
wait
echo "$(date +%H:%M) all done"
