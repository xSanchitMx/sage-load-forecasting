#!/bin/bash
# Validation sweep for the MELO combiner inside the controller (run from code/).
# All runs: calibrated drift (drift.py defaults), weekly schedule, deterministic arm only.
# Varies when the controller resets MELO and how. Results -> val_melo_<name>.json.
L=logs/2026-10-24_melo_combiner
run() {  # run <name> <logfile> [run_controller args...]
  .venv/bin/python run_controller.py --block val --no-bandit --workers 4 --diag-client none \
      --combiner melo --out val_melo_$1.json "${@:3}" > $L/$2 2>&1
}
run nodrift          10_val_melo_nodrift.log          --no-drift &
run drift_noreset    11_val_melo_drift_noreset.log    &
wait
run alarm_r05        12_val_melo_alarm_r05.log        --melo-reset '{"on":"alarm","regret_shrink":0.5}' &
run alarm_cov        13_val_melo_alarm_cov.log        --melo-reset '{"on":"alarm","cov_reset":true}' &
wait
run alarm_r05_cov    14_val_melo_alarm_r05_cov.log    --melo-reset '{"on":"alarm","regret_shrink":0.5,"cov_reset":true}' &
run alarm_r1_cov     15_val_melo_alarm_r1_cov.log     --melo-reset '{"on":"alarm","regret_shrink":1.0,"cov_reset":true}' &
wait
run refit_r05        16_val_melo_refit_r05.log        --melo-reset '{"on":"refit","regret_shrink":0.5}' &
run refit_cov        17_val_melo_refit_cov.log        --melo-reset '{"on":"refit","cov_reset":true}' &
wait
run refit_r05_cov    18_val_melo_refit_r05_cov.log    --melo-reset '{"on":"refit","regret_shrink":0.5,"cov_reset":true}' &
run refit_r1_cov     19_val_melo_refit_r1_cov.log     --melo-reset '{"on":"refit","regret_shrink":1.0,"cov_reset":true}' &
wait
