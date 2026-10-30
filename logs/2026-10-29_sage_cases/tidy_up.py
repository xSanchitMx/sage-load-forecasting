"""One-off reorganisation (2026-10-29): result files -> code/results/<topic>/ with readable names,
code/logs -> Project/logs, scripts updated to the new paths. Writes the old->new map to RENAMES.md data."""
import glob, json, os, re, shutil, sys

PROJ = "/mnt/c/Users/mukhe/Desktop/VIT Chennai/Year 4/Predictive Analytics/Project"
CODE = os.path.join(PROJ, "code")
DRY = "--dry" in sys.argv
SC = ["none", "level", "ramp", "amplitude", "temporary"]

# ---------------------------------------------------------------- file map (relative to code/)
M = {
    # baselines
    "baseline_results.json": "results/baselines/static_baselines.json",
    "adaptive_baselines_results.json": "results/baselines/online_combiners.json",
    # initial controller (top-3 blend + bandit) and its ablations
    "controller_results.json": "results/initial_controller/initial_controller.json",
    "controller_diag_MT_132.json": "results/initial_controller/initial_controller_hourly_MT_132.json",
    "test_controller_nodrift.json": "results/initial_controller/initial_controller_no_drift.json",
    "test_controller_always_retrain.json": "results/initial_controller/initial_controller_hourly_refit.json",
    "ablation_no_demotion.json": "results/initial_controller/ablation_no_demotion.json",
    "ablation_k1.json": "results/initial_controller/ablation_top1.json",
    "ablation_k5.json": "results/initial_controller/ablation_top5.json",
    "ablation_adwin_only.json": "results/initial_controller/ablation_adwin_only.json",
    "ablation_ph_only.json": "results/initial_controller/ablation_page_hinkley_only.json",
    # MELO runs inside the controller (step 3)
    "test_controller_melo_nodrift.json": "results/melo/melo_alone.json",
    "test_controller_melo_drift.json": "results/melo/melo_with_drift.json",
    "test_controller_melo_alarm_cov.json": "results/melo/melo_with_drift_reset_on_alarm.json",
    # saved per-hour forecasts of the pool (inputs for replaying the combiners)
    "test_streams_nodrift.json": "results/forecasts/pool_forecasts_test.json",
    "test_streams_always_retrain.json": "results/forecasts/pool_forecasts_test_hourly_refit.json",
    "val_streams_nodrift.json": "results/forecasts/pool_forecasts_val.json",
    "val_streams.json": "results/forecasts/initial_controller_forecasts_val.json",
    # tuning
    "agent_tuning.json": "results/tuning/agent_tuning.json",
    "bandit_tuning.json": "results/tuning/bandit_tuning.json",
    "drift_tuning.json": "results/tuning/drift_tuning.json",
    # summary tables
    "step3_comparison.json": "results/summaries/step3_baselines_and_ablations.json",
    "step3_comparison.md": "results/summaries/step3_baselines_and_ablations.md",
    "step4_comparison.json": "results/summaries/step4_shift_experiment.json",
    "step4_comparison.md": "results/summaries/step4_shift_experiment.md",
    "step5_comparison.json": "results/summaries/step5_sage_vs_melo.json",
    "step5_comparison.md": "results/summaries/step5_sage_vs_melo.md",
    "ops_summary.json": "results/summaries/ops_summary.json",
    "ops_summary.md": "results/summaries/ops_summary.md",
    "val_vs_test.json": "results/summaries/val_vs_test.json",
    # folders
    "step4_results": "results/shift_experiment",
    "step4_val": "results/validation/shift_experiment",
    "step5_streams": "results/validation/agent_tuning_forecasts",
}
for f in glob.glob(os.path.join(CODE, "val_*.json")):          # validation runs, no script reads them
    b = os.path.basename(f)
    if b not in M:
        M[b] = f"results/validation/{b}"
# SAGE (step5_results + step6_cases)
for sc in SC:
    M[f"step5_results/{sc}__agent.json"] = f"results/sage/sage_{sc}.json"
    M[f"step5_results/{sc}__agent_streams.json"] = f"results/sage/sage_{sc}_forecasts.json"
    M[f"step5_results/{sc}__proposed.json"] = f"results/sage/sage_without_agent_{sc}.json"
    M[f"step5_results/{sc}__proposed_streams.json"] = f"results/sage/sage_without_agent_{sc}_forecasts.json"
for sc in ("none", "level"):
    M[f"step5_results/demo_diag_MT_132_{sc}.json"] = f"results/sage/hourly_detail/sage_MT_132_{sc}.json"
for c in ("MT_105", "MT_135"):
    M[f"step6_cases/diag_{c}_none.json"] = f"results/sage/hourly_detail/sage_{c}_none.json"
    M[f"step6_cases/run_{c}_none.json"] = f"results/sage/hourly_detail/sage_{c}_none_run.json"

# ---------------------------------------------------------------- text replacements in scripts
# order matters: specific patterns first; plain names use a lookbehind so e.g.
# controller_results.json does not match inside val_controller_results.json
SPECIFIC = [
    ('"step5_results", "demo_diag_MT_132_none.json"', '"results", "sage", "hourly_detail", "sage_MT_132_none.json"'),
    ("step5_results/demo_diag_", "results/sage/hourly_detail/sage_"),
    ("step5_results/none__agent_streams.json", "results/sage/sage_none_forecasts.json"),
    ("step5_results/none__agent.json", "results/sage/sage_none.json"),
    ("step5_results/{s}__agent.json", "results/sage/sage_{s}.json"),
    ('"step5_results", f"{sc}__proposed_streams.json"', '"results", "sage", f"sage_without_agent_{sc}_forecasts.json"'),
    ('"step5_results", f"{sc}__agent_streams.json"', '"results", "sage", f"sage_{sc}_forecasts.json"'),
    ('"step5_results", f"{sc}__agent.json"', '"results", "sage", f"sage_{sc}.json"'),
    ("step5_results/<scenario>__{proposed,agent}_streams.json",
     "results/sage/sage_{,without_agent_}<scenario>_forecasts.json"),
    ("step6_cases/diag_{client}_none.json", "results/sage/hourly_detail/sage_{client}_none.json"),
    ("step6_cases/diag_<client>_none.json", "results/sage/hourly_detail/sage_<client>_none.json"),
    ("step5_results/demo_diag_MT_132_none.json", "results/sage/hourly_detail/sage_MT_132_none.json"),
    ('"step4_results"', '"results", "shift_experiment"'),
    ("step4_results/", "results/shift_experiment/"),
    ('"step5_streams"', '"results", "validation", "agent_tuning_forecasts"'),
    ("into step5_streams/", "into results/validation/agent_tuning_forecasts/"),
    ('f"controller_diag_{cid}.json"', 'f"results/initial_controller/initial_controller_hourly_{cid}.json"'),
    ("controller_diag_<client>.json", "results/initial_controller/initial_controller_hourly_<client>.json"),
    # result keys inside online_combiners.json follow the forecast file names
    ('["test_streams_nodrift"]', '["pool_forecasts_test"]'),
    ('["test_streams_always_retrain"]', '["pool_forecasts_test_hourly_refit"]'),
    ('"test_streams_always_retrain"', '"pool_forecasts_test_hourly_refit"'),
    ('"test_streams_nodrift"', '"pool_forecasts_test"'),
]
PLAIN = sorted([k for k in M if "/" not in k and k.endswith((".json", ".md"))], key=len, reverse=True)


def rewrite(text):
    for a, b in SPECIFIC:
        text = text.replace(a, b)
    for k in PLAIN:
        text = re.sub(r"(?<![\w/])" + re.escape(k), M[k], text)
    return text


def main():
    moved, missing = [], []
    for old, new in sorted(M.items(), key=lambda kv: kv[0].count("/"), reverse=True):
        src, dst = os.path.join(CODE, old), os.path.join(CODE, new)
        if not os.path.exists(src):
            missing.append(old); continue
        moved.append((old, new))
        if not DRY:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.move(src, dst)
    if not DRY:
        for d in ("step5_results", "step6_cases"):
            p = os.path.join(CODE, d)
            if os.path.isdir(p) and not os.listdir(p):
                os.rmdir(p)
        # keys inside online_combiners.json
        p = os.path.join(CODE, "results/baselines/online_combiners.json")
        R = json.load(open(p))
        R["test"] = {{"test_streams_nodrift": "pool_forecasts_test",
                      "test_streams_always_retrain": "pool_forecasts_test_hourly_refit"}.get(k, k): v
                     for k, v in R["test"].items()}
        json.dump(R, open(p, "w"), indent=2)
    changed = []
    for py in sorted(glob.glob(os.path.join(CODE, "*.py"))):
        s = open(py).read(); t = rewrite(s)
        if t != s:
            changed.append(os.path.basename(py))
            if not DRY:
                open(py, "w").write(t)
    json.dump({"moved": moved, "missing": missing, "scripts_changed": changed},
              open(os.path.join(os.path.dirname(__file__), "tidy_up_report.json"), "w"), indent=1)
    print(f"moved {len(moved)}, missing {len(missing)}: {missing}")
    print("scripts changed:", changed)


if __name__ == "__main__":
    main()
