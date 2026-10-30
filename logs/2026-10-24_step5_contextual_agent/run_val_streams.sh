#!/bin/bash
# Step 5: per-step streams (y, MELO output, every model's forecast) of the proposed system
# (MELO combiner + calibrated drift + follow-up refits) on the validation block, without and
# with each injected shift. Used to prototype / tune the contextual agent offline. Run from code/.
L=logs/2026-10-24_step5_contextual_agent
for sc in none level ramp amplitude temporary; do
  while [ "$(jobs -rp | wc -l)" -ge 3 ]; do wait -n; done
  .venv/bin/python run_controller.py --block val --no-bandit --workers 4 --diag-client none \
      --combiner melo --alarm-response '{}' --shift $sc \
      --out step5_streams/val_${sc}_results.json --streams-out step5_streams/val_${sc}.json \
      > $L/01_val_streams_${sc}.log 2>&1 &
done
wait
echo "all done"
