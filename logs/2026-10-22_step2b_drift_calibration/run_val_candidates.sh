#!/bin/bash
# Full deterministic-controller runs on the validation block for each shortlisted drift
# setting (run from code/). Results -> val_drift_<name>.json, logs alongside this script.
L=logs/2026-10-22_step2b_drift_calibration
COMMON='"clip": 10, "ph_mode": "up", "ph_min_instances": 24'
run() {  # run <name> <logfile> [run_controller args...]
  .venv/bin/python run_controller.py --block val --no-bandit --workers 6 \
      --diag-client none --out val_drift_$1.json "${@:3}" > $L/$2 2>&1
}
run frequent 02_val_frequent.log --drift "{$COMMON, \"ph_threshold\": 10, \"adwin_delta\": 0.05}"
run medium   03_val_medium.log   --drift "{$COMMON, \"ph_threshold\": 25, \"adwin_delta\": 0.01}"
run sparse   04_val_sparse.log   --drift "{$COMMON, \"ph_threshold\": 50, \"adwin_delta\": 0.002}"
run nodrift  05_val_nodrift.log  --no-drift
