#!/bin/bash
# Controller ablations on the test block (run from code/). Each removes or changes ONE
# component of the full system (calibrated drift, 168 h schedule, top-k = 3, demotion 1.5x).
# Deterministic controller only. The bandit ablation (with/without) is already in
# controller_results.json. Results -> ablation_<name>.json.
L=logs/2026-10-22_step3_baselines_ablations
run() {  # run <name> <logfile> [run_controller args...]
  .venv/bin/python run_controller.py --no-bandit --workers 4 --diag-client none \
      --out ablation_$1.json "${@:3}" > $L/$2 2>&1
}
run no_demotion 10_ablation_no_demotion.log --demote-factor inf
run k1          11_ablation_k1.log          --topk 1
run k5          12_ablation_k5_all.log      --topk 5
run adwin_only  13_ablation_adwin_only.log  --drift '{"use_ph": false}'
run ph_only     14_ablation_ph_only.log     --drift '{"use_adwin": false}'
