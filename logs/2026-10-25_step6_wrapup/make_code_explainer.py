"""Builds Code_Explainer.docx: a guided tour of the code behind SAGE."""
import os
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

PROJ = "/mnt/c/Users/mukhe/Desktop/VIT Chennai/Year 4/Predictive Analytics/Project"
OUT = os.path.join(PROJ, "Code_Explainer.docx")

doc = Document()
sec = doc.sections[0]
sec.page_width, sec.page_height = Inches(8.27), Inches(11.69)
for side in ("left_margin", "right_margin"):
    setattr(sec, side, Inches(0.9))
sec.top_margin = sec.bottom_margin = Inches(0.8)
st = doc.styles["Normal"]
st.font.name = "Calibri"; st.font.size = Pt(11)
st.element.rPr.rFonts.set(qn("w:eastAsia"), "Calibri")
st.paragraph_format.space_after = Pt(6)
for lvl, size in ((1, 15), (2, 12.5)):
    h = doc.styles[f"Heading {lvl}"]
    h.font.name = "Calibri"; h.font.size = Pt(size); h.font.bold = True
    h.font.color.rgb = RGBColor(0x1F, 0x3A, 0x5F)
    h.paragraph_format.space_before = Pt(14 if lvl == 1 else 10)
    h.paragraph_format.space_after = Pt(4)


def shade_par(p, hexcol):
    pPr = p._p.get_or_add_pPr()
    s = OxmlElement("w:shd"); s.set(qn("w:val"), "clear"); s.set(qn("w:color"), "auto"); s.set(qn("w:fill"), hexcol)
    pPr.append(s)


def para(text="", bold_lead=None, italic=False, size=None):
    p = doc.add_paragraph()
    if bold_lead:
        p.add_run(bold_lead).bold = True
    r = p.add_run(text); r.italic = italic
    if size: r.font.size = Pt(size)
    return p


def rich(*parts):
    """parts: plain strings, or ('code', text) / ('b', text) tuples, inline."""
    p = doc.add_paragraph()
    for part in parts:
        if isinstance(part, tuple):
            kind, txt = part
            r = p.add_run(txt)
            if kind == "code":
                r.font.name = "Consolas"; r.font.size = Pt(9.5); r.font.color.rgb = RGBColor(0x8A, 0x2B, 0x0E)
            elif kind == "b":
                r.bold = True
        else:
            p.add_run(part)
    return p


def bullets(items):
    for it in items:
        p = doc.add_paragraph(style="List Bullet")
        parts = it if isinstance(it, (list, tuple)) and not (len(it) == 2 and it[0] in ("code", "b")) else [it]
        if isinstance(it, tuple) and len(it) == 2 and isinstance(it[0], str) and it[0] not in ("code", "b"):
            p.add_run(it[0]).bold = True; p.add_run(it[1]); continue
        for part in parts:
            if isinstance(part, tuple):
                r = p.add_run(part[1])
                if part[0] == "code":
                    r.font.name = "Consolas"; r.font.size = Pt(9.5); r.font.color.rgb = RGBColor(0x8A, 0x2B, 0x0E)
                else:
                    r.bold = True
            else:
                p.add_run(part)


def code(block):
    for line in block.strip("\n").split("\n"):
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(0); p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.left_indent = Inches(0.15)
        r = p.add_run(line if line else " "); r.font.name = "Consolas"; r.font.size = Pt(8.5)
        shade_par(p, "F3F2EE")
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def shade(cell, hexcol):
    tcPr = cell._tc.get_or_add_tcPr()
    s = OxmlElement("w:shd"); s.set(qn("w:val"), "clear"); s.set(qn("w:color"), "auto"); s.set(qn("w:fill"), hexcol)
    tcPr.append(s)


def table(header, rows, widths, mono_col=None):
    t = doc.add_table(rows=1, cols=len(header)); t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(header):
        c = t.rows[0].cells[i]; c.text = ""; r = c.paragraphs[0].add_run(h); r.bold = True; r.font.size = Pt(9.5)
        shade(c, "DCE6F0")
    for row in rows:
        cells = t.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = ""; r = cells[i].paragraphs[0].add_run(str(v)); r.font.size = Pt(9.5)
            if mono_col is not None and i in (mono_col if isinstance(mono_col, tuple) else (mono_col,)):
                r.font.name = "Consolas"; r.font.size = Pt(8.5)
    for row in t.rows:
        for i, w in enumerate(widths):
            row.cells[i].width = Inches(w)
    doc.add_paragraph()


# ======================================================================= title
t = doc.add_paragraph(); t.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = t.add_run("Code Explainer"); r.bold = True; r.font.size = Pt(22); r.font.color.rgb = RGBColor(0x1F, 0x3A, 0x5F)
t = doc.add_paragraph(); t.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = t.add_run("How the code behind SAGE is organised, and what happens when you run it"); r.font.size = Pt(12)
t = doc.add_paragraph(); t.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = t.add_run("All files are in code/. Python 3.14; dependencies pinned in requirements.txt."); r.italic = True; r.font.size = Pt(10)

# ======================================================================= 1
doc.add_heading("1. The big picture", 1)
para("The code has three layers. The core modules are the system itself. The experiment scripts run it on every "
     "client and save results as JSON. The reporting scripts turn those JSON files into tables, figures, the "
     "summary and the paper.")
table(["Layer", "Files", "Job"], [
    ["Core system", "data_pipeline, models, combiners, drift, agent, controller", "SAGE itself: data in, one forecast per hour out"],
    ["Experiment support", "shifts, metrics, significance", "inject demand shifts, score forecasts, test significance"],
    ["Runners", "run_controller, run_baselines, adaptive_baselines, tune_*", "run the system and the baselines over all clients, tune settings on validation; outputs go to code/results/"],
    ["Reporting (code/reporting/)", "make_step3/4/5_table, make_results_summary, make_final_figs, make_paper_figs_v2", "tables, results_summary.md, figures"],
], [1.4, 3.0, 2.2])

doc.add_heading("What happens in one run", 2)
para("This is the path through the code when you run SAGE on the test data:")
code("""
run_controller.py main()
  └─ data_pipeline.prepare()                 load CSV, pick 8 clients, build ClientSeries
  └─ for each client (in parallel):
       evaluate_client()
         └─ shifts.apply()                    (optional) inject a demand shift
         └─ AdaptiveController(...)           build pool + MELO + drift monitor + agent
         └─ controller.run(lo, hi)            the hour-by-hour loop  ← the heart of SAGE
         └─ metrics.summarize(), shift_metrics(), operational_stats()
  └─ write results JSON (+ forecasts JSON, + hourly-detail JSON for one client) under code/results/
""")

doc.add_heading("Where SAGE's pieces live", 2)
table(["Piece of SAGE", "Where in the code"], [
    ["The five forecasting models", "models.py: SeasonalNaive, HoltWinters, SARIMAModel, LightGBMModel, OnlineLinear; build_pool()"],
    ["MELO combiner (MLpol + 16 correction experts)", "combiners.py: class MELO, mlpol_weights(), melo_gammas()"],
    ["Drift watchdog (ADWIN + Page–Hinkley)", "drift.py: class DriftMonitor"],
    ["Alarm response (retrain now + follow-ups at +24/+72/+168 h)", "controller.py: run(), the block after monitor.step()"],
    ["Contextual agent", "agent.py: ContextBuilder (features), ContextualSelector (decision + learning)"],
    ["The loop that ties them together", "controller.py: AdaptiveController.run()"],
], [2.6, 4.0], mono_col=1)

# ======================================================================= 2
doc.add_heading("2. Core modules, one by one", 1)

doc.add_heading("data_pipeline.py: loading and preparing the data", 2)
bullets([
    [("code", "load_hourly()"), " reads ../Dataset/electricity_hourly_2012_2014.csv (370 customers, hourly)."],
    [("code", "select_clients(df, n=8, seed=42)"), " picks 8 customers: it sorts them by how variable their load is, "
     "splits into three groups (steady / medium / volatile) and samples from each, so the 8 are a fair mix."],
    [("code", "calendar_features()"), " adds hour, weekday, weekend and holiday columns, used by LightGBM, the online model and the agent."],
    [("code", "make_splits()"), " gives the 50 / 15 / 35 % warm-up / validation / test boundaries."],
    [("code", "ClientSeries"), " holds one customer: the series ", ("code", "y"), ", the features ", ("code", "feats"),
     ", the ", ("code", "splits"), ", and a scaler that only uses past data (no peeking)."],
    [("code", "prepare()"), " does all of the above and returns ", ("code", "{client_id: ClientSeries}"), "."],
])

doc.add_heading("models.py: the five forecasters", 2)
para("Every model has the same three methods, so the controller can treat them identically:")
code("""
class BaseModel:
    def predict(self, t) -> float        # forecast hour t using data before t only
    def update(self, t, y)               # see the real value of hour t (cheap, every hour)
    def retrain(self, t, since=None)     # refit from scratch on recent history (expensive)
""")
table(["Class", "How it forecasts", "update() / retrain()"], [
    ["SeasonalNaive", "Same hour one week ago", "nothing to learn"],
    ["HoltWinters", "Smoothed level + trend + 24 h seasonal pattern", "updates its state every hour; retrain re-seeds it"],
    ["SARIMAModel", "statsmodels SARIMA (1,0,1)(1,0,1,24)", "feeds each new value into the fitted model; retrain refits"],
    ["LightGBMModel", "Gradient-boosted trees on lags + calendar, trained on the last 60 days", "retrain refits the trees"],
    ["OnlineLinear", "river linear regression on lags + calendar", "learns a little from every hour (never retrained)"],
], [1.3, 3.0, 2.3], mono_col=0)
rich(("code", "build_pool(y, feats)"), " creates the five. Models with ", ("code", "retrainable = True"),
     " (Holt-Winters, SARIMA, LightGBM) are the ones the drift watchdog retrains.")

doc.add_heading("combiners.py: MELO", 2)
para("This is our own implementation of MELO (Wang, Goude & Yao 2026), following the paper's equations.")
code("""
melo_gammas()          # 15 forgetting factors, memory 20 h ... 5000 h, plus 1.0 (never forget)
mlpol_weights(R)       # MLpol: weight = positive part of regret, normalised

class MELO:
    predict(f)         # f = the 5 model forecasts
                       #   -> 16 experts each compute  w_k · [f, 1]   (corrected forecasts)
                       #   -> blend the 5 raw + 16 corrected with MLpol weights
    update(y)          # real value arrives:
                       #   -> update MLpol regrets R      (who would have helped?)
                       #   -> update every expert's w_k by recursive least squares (RLS)
""")
bullets([
    "Cold start: for the first few hours there isn't enough data to fit the experts, so it uses the plain average of the pool.",
    [("code", "eps0"), " (0.01, tuned on validation) controls how much each expert's uncertainty is allowed to grow, which sets how fast it can adapt."],
    "Numerical safety: the experts' covariance matrices are re-symmetrised and their size (trace) is capped, otherwise "
    "they can blow up over 9,000+ hours.",
    [("code", "reset()"), " exists for an experiment we rejected (resetting MELO after alarms); SAGE does not use it."],
])

doc.add_heading("drift.py: the watchdog", 2)
code("""
class DriftMonitor:
    def step(self, residual) -> bool:
        residual = min(residual, 10)          # clip: one odd hour can't fire an alarm
        adwin.update(residual)                # river's ADWIN, delta = 0.002
        ph.update(residual)                   # river's Page-Hinkley, threshold 50, mode "up"
        return adwin.drift_detected or ph.drift_detected
""")
para("The residual fed in is SAGE's absolute error divided by its usual error size, so the same thresholds work for "
     "small and large customers. The defaults were chosen on validation to give about 0.2 alarms a week.")

doc.add_heading("agent.py: the contextual agent", 2)
rich(("b", "ContextBuilder"), " makes the 28 features the agent looks at, using only information available before the hour:")
code("""
[1, sin(hour), cos(hour), weekend, holiday, disagreement between candidates,
 fast EWMA loss of each of the 6 candidates,        # last ~day
 slow EWMA loss of each candidate,                  # last ~week
 each candidate's distance from MELO,
 load change vs 24 h ago, load change vs 1 week ago,
 recency of last alarm, recency of last refit]      # = 6 + 3*6 + 4 = 28
""")
rich(("b", "ContextualSelector"), " holds one small linear model per candidate that predicts that candidate's error from the features:")
code("""
choose(x, cands):
    predicted_loss = W @ x                             # one number per candidate
    weights = softmax(-(predicted_loss - min) / 0.3)   # lower predicted loss -> more weight
    return weights · cands                             # the forecast SAGE serves

update(x, losses):                                     # after the real value arrives
    recursive least squares with forgetting 0.999      # all 6 candidates updated at once
""")
bullets([
    "For the first week (warmup = 168 h) it just serves MELO while it learns.",
    "Losses are absolute errors scaled by MELO's usual error and capped at 10, so one bad hour can't dominate.",
    "It updates every candidate every hour, because it can see all of their errors. That's 'full information', and why it needs no exploration.",
])

doc.add_heading("controller.py: the hour-by-hour loop", 2)
rich(("code", "AdaptiveController"), " builds everything in ", ("code", "__init__"), " (pool, MELO, drift monitor, agent) and ",
     ("code", "run(lo, hi)"), " walks through the hours. Simplified, one hour looks like this (line numbers refer to controller.py):")
code("""
for t in range(lo, hi):
    preds  = {m.name: m.predict(t) for m in pool}               # 1. five forecasts     (l.193)
    blend  = melo.predict(preds)                                 # 2. MELO               (l.201)
    cands  = [blend] + preds                                     # 3. agent picks mix    (l.208-210)
    yhat   = agent.choose(ctx.features(t, cands, ...), cands)
    served.append(yhat)

    y_t = y[t]                                                   # 4. truth arrives
    melo.update(y_t);  agent.update(x, losses)                   #    everything learns  (l.239-242)
    for m in pool: m.update(t, y_t)                              #                       (l.247)

    fired = monitor.step(|y_t - yhat| / usual_error)             # 5. drift check        (l.253)
    if fired:  schedule follow-ups at t+24, t+72, t+168          #                       (l.257-260)
    if fired or follow-up due:  retrain HW, SARIMA, LightGBM     # 6. alarm response     (l.261-269)
    if 168 h since a model's last retrain:  retrain it           # 7. weekly schedule    (l.274-280)
""")
bullets([
    "With combiner='blend' and no agent it reproduces our initial controller (top-3 inverse-error blend, optionally with the "
    "Discounted-UCB1 bandit). Those code paths are still there because the baselines use them.",
    "Timing is measured per phase (predict, update, control, retrain) only for the cost numbers; it doesn't affect forecasts.",
    [("code", "diag"), " collects per-hour diagnostics (weights, alarms, refits, agent weights) for the demo and case-study figures."],
])

doc.add_heading("shifts.py, metrics.py, significance.py", 2)
bullets([
    [("code", "shifts.apply(y, lo, scenario)"), " multiplies the series by a profile to inject a level jump, ramp, "
     "amplitude change or temporary spike at two fixed times in the block, and returns the event times."],
    [("code", "metrics.py"), ": ", ("code", "mape, cv_rmse, mae, rmse"), " (MAPE skips hours with exactly zero load), ",
     ("code", "shift_metrics()"), " (detection, delay, recovery after injected events), ",
     ("code", "operational_stats()"), " (refits per week, ms per step)."],
    [("code", "significance.py"), ": Diebold–Mariano test with Newey–West variance (24 h lag, small-sample correction) "
     "and the Wilcoxon signed-rank test across series."],
])

# ======================================================================= 3
doc.add_heading("3. Runners and experiments", 1)
table(["Script", "What it does", "Main output"], [
    ["run_controller.py", "Runs the controller for every client. Flags choose the configuration (see section 4).", "results JSON, streams JSON, diagnostics JSON"],
    ["run_baselines.py", "Single models, validation-chosen single model, equal-weight ensemble.", "results/baselines/static_baselines.json"],
    ["adaptive_baselines.py", "Replays FTL, Hedge, DWM, MLpol and MELO over saved pool forecasts (fast: no models are re-run).", "results/baselines/online_combiners.json"],
    ["tune_drift.py, tune_agent.py, tune_bandit.py", "Grid searches on the validation block.", "results/tuning/*.json"],
    ["significance.py (via make_step5_table.py)", "Diebold–Mariano and Wilcoxon tests.", "results/summaries/step5_sage_vs_melo.json"],
], [1.8, 3.2, 1.6], mono_col=0)
para("The 'streams' trick: running the pool once and saving every model's hourly forecast lets the combiners be "
     "replayed in seconds instead of re-running SARIMA and LightGBM for an hour each time. That is how the MELO, "
     "MLpol, DWM, Hedge and FTL baselines are computed, on exactly the same forecasts SAGE sees.")

# ======================================================================= 4
doc.add_heading("4. How to run things", 1)
para("From code/, after setting up the virtual environment:")
code("""
python3.14 -m venv .venv
.venv/bin/pip install -r requirements.txt
""")
rich(("b", "SAGE on the real test data"), " (each client takes several minutes; --workers runs clients in parallel, ~230 MB RAM each):")
code("""
.venv/bin/python run_controller.py --no-bandit --workers 8 --combiner melo \\
    --alarm-response '{}' --agent '{"mode": "soft", "forget": 0.999, "temp": 0.3}' \\
    --shift none --out results/sage/sage_none.json \\
    --streams-out results/sage/sage_none_forecasts.json
""")
table(["Flag", "Meaning"], [
    ["--combiner melo", "use MELO (blend = our old top-3 blend)"],
    ["--alarm-response '{}'", "turn on the alarm response with default settings (follow-ups at +24/+72/+168 h)"],
    ["--agent '{...}'", "turn on the contextual agent (needs --no-bandit)"],
    ["--shift level|ramp|amplitude|temporary", "inject a demand shift"],
    ["--block val", "run on the validation block instead of test"],
    ["--only MT_105", "run just one client"],
    ["--diag-client MT_105 --diag-out results/sage/hourly_detail/x.json", "save hour-by-hour diagnostics for one client"],
    ["--max-steps 500", "quick smoke test"],
    ["--no-drift", "switch the watchdog off (MELO alone = --combiner melo --no-drift --no-bandit)"],
], [2.6, 4.0], mono_col=0)
rich(("b", "Rebuild every table and figure"), " from saved results (no re-running needed):")
code("""
.venv/bin/python reporting/make_step5_table.py       # results/summaries/step5_sage_vs_melo.md/.json
.venv/bin/python reporting/make_results_summary.py   # results_summary.md
.venv/bin/python reporting/make_final_figs.py        # figures_final/fig1..fig6
.venv/bin/python reporting/make_paper_figs_v2.py     # paper/figures_v2/ (column width)
""")

# ======================================================================= 5
doc.add_heading("5. Reading the result files", 1)
para("All results are under code/results/, one folder per topic: sage/, baselines/, melo/, initial_controller/, "
     "shift_experiment/, forecasts/, tuning/, summaries/, validation/. In file names, none means real data with no injected "
     "shift. A results JSON has one entry per client plus a config record:")
code("""
{
  "MT_132": {
    "adaptive_deterministic": {        # = the controller's served forecast (SAGE in results/sage/)
        "MAPE": 5.21, "CV_RMSE": 6.65, "MAE": ..., "n_drift": ...,
        "ops":   {"refits_total_per_week": ..., "ms_per_step": 28.6, ...},
        "shift": {"detected": ..., "delay_median": ..., "recovery_median": ...}       # shift runs only
    },
    "best_static_single": {...}, "equal_weight_ensemble": {...}
  },
  ...,
  "_config": {... every flag used ...}
}
""")
table(["Name in code / files", "Name in the paper"], [
    ["results/sage/sage_<scenario>.json; label 'proposed + agent' inside summaries", "SAGE"],
    ["results/sage/sage_without_agent_<scenario>.json; label 'proposed (no agent)'", "ablation without the agent"],
    ["results/melo/melo_alone.json; labels 'MELO alone', 'melo (weekly refit)'", "MELO"],
    ["'melo (daily refit)' in results/summaries/step4_shift_experiment.json", "MELO, daily refit"],
    ["'adaptive_bandit' in results/initial_controller/initial_controller.json", "Initial controller"],
    ["val_best_single", "Best single model (validation-chosen)"],
], [4.0, 2.6], mono_col=0)
para("Every run's console output is in logs/<date>_<what>/ in the project root, and logs/README.md says which command "
     "produced which file. RENAMES.md (project root) maps file names used before the 2026-10-29 reorganisation to the current ones.")

# ======================================================================= 6
doc.add_heading("6. Design choices worth knowing", 1)
bullets([
    ("No peeking. ", "Every forecast for hour t uses only data before t: predict, then reveal, then update. The scaler, "
     "the agent's features and the drift residual are all built from the past only."),
    ("Same forecasts for everyone. ", "The baselines are computed from the same pool forecasts SAGE uses, so differences "
     "come from combining and adapting, not from different models."),
    ("Validation first. ", "Every tuned setting (drift thresholds, MELO's eps0, the alarm response, the agent's forgetting "
     "and temperature) was chosen on the validation block before the test block was run."),
    ("Cheap by design. ", "Only three models are ever retrained, and only on alarms, follow-ups or the weekly schedule. "
     "The agentic logic is under 2% of the 31 ms per step."),
    ("Left-over code paths. ", "Flags like --melo-reset, alarm-response 'cut', the bandit and the top-k blend belong to "
     "experiments that lost on validation or to the initial controller. They are kept so earlier results can be reproduced."),
])

doc.save(OUT)
print("->", OUT)
