"""Builds Project_Explainer.docx: a quick plain-language guide to the project (final system: SAGE).
Numbers come from code/results_summary.md, code/figures_final/ and the case-study analysis in
code/logs/2026-10-29_sage_cases/."""
import os
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

PROJ = "/mnt/c/Users/mukhe/Desktop/VIT Chennai/Year 4/Predictive Analytics/Project"
OUT = os.path.join(PROJ, "Project_Explainer.docx")
FIGS = os.path.join(PROJ, "code", "figures_final")
NAME = "SAGE"

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


def para(text, bold_lead=None, italic=False, size=None):
    p = doc.add_paragraph()
    if bold_lead:
        p.add_run(bold_lead).bold = True
    r = p.add_run(text); r.italic = italic
    if size: r.font.size = Pt(size)
    return p


def bullets(items):
    for it in items:
        p = doc.add_paragraph(style="List Bullet")
        if isinstance(it, tuple):
            p.add_run(it[0]).bold = True; p.add_run(it[1])
        else:
            p.add_run(it)


def shade(cell, hexcol):
    tcPr = cell._tc.get_or_add_tcPr()
    s = OxmlElement("w:shd"); s.set(qn("w:val"), "clear"); s.set(qn("w:color"), "auto"); s.set(qn("w:fill"), hexcol)
    tcPr.append(s)


def table(header, rows, widths, bold_rows=()):
    t = doc.add_table(rows=1, cols=len(header)); t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(header):
        c = t.rows[0].cells[i]; c.text = ""; r = c.paragraphs[0].add_run(h); r.bold = True; r.font.size = Pt(9.5)
        shade(c, "DCE6F0")
    for ri, row in enumerate(rows):
        cells = t.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = ""; r = cells[i].paragraphs[0].add_run(str(v)); r.font.size = Pt(9.5)
            if ri in bold_rows:
                r.bold = True; shade(cells[i], "EEF4E8")
            if i > 0: cells[i].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
    for row in t.rows:
        for i, w in enumerate(widths):
            row.cells[i].width = Inches(w)
    doc.add_paragraph()
    return t


def figure(name, caption, width=6.2, folder=FIGS):
    doc.add_picture(os.path.join(folder, name), width=Inches(width))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    p = doc.add_paragraph(); r = p.add_run(caption); r.italic = True; r.font.size = Pt(9.5)
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER


# ---------------- title ----------------
t = doc.add_paragraph(); t.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = t.add_run("Project Explainer"); r.bold = True; r.font.size = Pt(22); r.font.color.rgb = RGBColor(0x1F, 0x3A, 0x5F)
t = doc.add_paragraph(); t.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = t.add_run("Real-Time Self-Adaptive Agentic Intelligence for Electricity Load Forecasting "
              "Under Dynamic Demand Shifts"); r.font.size = Pt(12)
t = doc.add_paragraph(); t.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = t.add_run("Predictive Analytics subject project, VIT Chennai. A quick guide to the project, not the paper."); r.italic = True; r.font.size = Pt(10)

# ---------------- 1 ----------------
doc.add_heading("1. The project in one minute", 1)
para("We forecast the electricity load of 8 customers one hour ahead, every hour, as new data arrives. "
     "Demand changes over time, sometimes suddenly (a new machine, a holiday season, a lockdown), and "
     "a model trained once slowly goes stale. Our system notices these changes on its own and reacts: "
     "it retrains its models when needed and changes which forecast it trusts.")
para(f"The system is called {NAME}: Self-Adaptive aGEntic forecaster. It has four layers:")
bullets([
    ("Model pool. ", "Five ordinary forecasting models run side by side."),
    ("MELO combiner. ", "A recent (2026) published method that blends the five forecasts and corrects their bias."),
    ("Drift watchdog. ", "Two change detectors watch the errors. On an alarm the models are retrained, then retrained again 1, 3 and 7 days later."),
    ("Contextual agent. ", "Each hour it looks at the situation (time of day, recent errors, alarms) and decides how much to trust MELO versus each single model."),
])
p = para("", bold_lead="Headline: ")
p.add_run(f"{NAME} has the lowest error of every method we tested, on both MAPE (4.70%, against 4.82% for MELO) "
          "and CV-RMSE (6.34% against 6.47%). It beats MELO in every demand-shift scenario too, and the gain is "
          "statistically significant. It retrains about 4 times a week, against 21 times for a MELO that retrains "
          "daily, and it still beats that MELO on MAPE. Its biggest wins come from a real sudden jump in demand "
          "(MT_105) and from a customer with an unusual daily pattern (MT_135). On regular customers it is level with MELO.")

# ---------------- 2 ----------------
doc.add_heading("2. Data and how we test", 1)
bullets([
    ("Data: ", "UCI ElectricityLoadDiagrams, 370 Portuguese customers, 2012–2014, aggregated to hourly. "
     "We chose 8 customers of different sizes and behaviours (MT_024, MT_105, MT_118, MT_121, MT_132, MT_135, MT_163, MT_269)."),
    ("Split: ", "first 50% of each series to train, next 15% to tune settings (validation), last 35% to test "
     "(9,207 hours, about a year: Dec 2013 to Dec 2014). Every setting was chosen on validation before looking at test."),
    ("Prequential (test-then-train): ", "at each hour the system forecasts first, then sees the true value and learns from it. "
     "This copies how it would run live, so there is no peeking at the future."),
    ("Injected shifts: ", "real data has few clear shocks, so we also add artificial ones to the test data at known times: "
     "level jump (+30%), slow ramp (+30% over 4 weeks), bigger daily swings (×1.6) and a temporary spike (+40% for a week). "
     "Knowing when each shift happens lets us measure detection and recovery."),
])

# ---------------- 3 ----------------
doc.add_heading(f"3. How {NAME} works", 1)
figure("architecture_icons.png",
       f"Figure 1. {NAME} as five layers: meters → five models → MELO → contextual agent → serve, watch and retrain. "
       "The red loop is the drift watchdog retraining the models.", 3.6, folder=os.path.join(PROJ, "paper"))
figure("architecture_pictorial_v2.png",
       f"The same system as a data-flow diagram (the paper's Fig. 1).", 6.3, folder=os.path.join(PROJ, "paper"))

doc.add_heading("Layer 1: the model pool", 2)
table(["Model", "Idea in one line"], [
    ["Seasonal-naive", "Load now = load at the same hour last week"],
    ["Holt-Winters", "Smoothed level + trend + daily/weekly pattern"],
    ["SARIMA", "Classical statistical time-series model with seasonality"],
    ["LightGBM", "Gradient-boosted trees on lags and calendar features"],
    ["Online linear", "Linear model that updates its weights every hour"],
], [1.6, 5.0])
para("By default the heavy models (Holt-Winters, SARIMA, LightGBM) are retrained on a weekly schedule.")

doc.add_heading("Layer 2: MELO combiner", 2)
para("MELO stands for Memory-hedged Exponentially Weighted Least-Squares Online aggregation (Wang, Goude & Yao, "
     "2026, arXiv preprint). It runs MLpol, an online weighting rule that shifts weight towards whichever forecasts "
     "have been doing best, and adds 16 small correction experts that learn and remove systematic bias at different "
     "memory lengths, from a few hours to months. On its own it was already the best published baseline we "
     "tested, so it became our base. It never retrains the models; that is what SAGE adds.")

doc.add_heading("Layer 3: drift watchdog and follow-up retrains", 2)
bullets([
    "Two detectors, ADWIN and Page–Hinkley, watch the recent forecast errors (scaled and clipped so one odd hour can't trigger them).",
    "Thresholds were tuned on validation to give about one false alarm every 5 weeks (0.2 per week).",
    "On an alarm, retrain the models now, then again after 24 h, 72 h and 168 h. Each retrain sees more post-shift data. A single retrain right at the alarm sees almost none.",
    "For a week after an alarm a fast-reacting average is used for blending, so the system adapts quickly.",
])

doc.add_heading("Layer 4: contextual agent", 2)
para("This is the 'agentic' part: it observes the situation, decides, and learns from the outcome every hour.")
bullets([
    ("Observes: ", "28 features: hour and weekday, each candidate's recent error (short and long memory), whether an alarm fired recently, and so on."),
    ("Decides: ", "predicts each candidate's error for this hour (MELO plus the 5 models) and gives more weight to the ones predicted to do well (a soft choice, not winner-takes-all)."),
    ("Learns: ", "once the truth arrives, it updates every candidate's error model, slowly forgetting old data (forgetting factor 0.999, about 6 weeks of memory)."),
])
para("In machine-learning terms it is a full-information contextual bandit with a recursive least-squares model per candidate.", italic=True, size=10)

# ---------------- 4 ----------------
doc.add_heading("4. The metrics, and what winning each one means", 1)
para("All of them are errors, so lower is better. Each one rewards a different kind of good forecast.")
table(["Metric", "What it measures", "Being best on it means"], [
    ["MAPE (primary)", "Average miss as a % of the actual load at that hour",
     "Small relative errors in every hour, including quiet night hours and small customers. "
     "A 10 kW miss at 50 kW load counts as much as a 100 kW miss at 500 kW."],
    ["CV-RMSE", "Root-mean-square error ÷ mean load, in %",
     "Avoids big misses. Squaring makes large errors, usually at peak hours or sudden changes, dominate."],
    ["MAE", "Average miss in kW",
     "Smallest absolute error. Mostly driven by the large customers and busy hours."],
], [1.2, 2.0, 3.4], bold_rows=(0,))
para("We use MAPE as the primary metric. It is the most common accuracy measure in load forecasting, it is "
     "easy to read (“on average we are off by 4.7%”), and it doesn't depend on the customer's size, so "
     "small and large customers count equally. Its weak spot is hours where the load is close to zero: a tiny "
     "absolute miss becomes a huge percentage. That's why CV-RMSE is always reported next to it.")
p = para("", bold_lead=f"{NAME} wins both: ")
p.add_run("it is better than MELO in relative terms (MAPE), mostly in quiet hours and on irregular customers, and "
          "at avoiding big misses (CV-RMSE), mostly right after sudden changes. Its MAE is very slightly higher than "
          "MELO's (66.7 vs 66.5 kW), because the agent trades a little absolute accuracy in busy hours for better "
          "accuracy in quiet ones.")

# ---------------- 5 ----------------
doc.add_heading("5. Results", 1)
doc.add_heading("Real data (no injected shifts)", 2)
para("Averages over the 8 customers on the test year. Lower is better for every column. MAPE is the primary metric.")
table(["Method", "MAPE %", "CV-RMSE %"], [
    ["Seasonal naive (single model)", "9.62", "13.61"],
    ["Holt-Winters (single model)", "9.63", "9.96"],
    ["SARIMA (single model)", "6.25", "7.92"],
    ["LightGBM (single model)", "5.55", "7.86"],
    ["Online linear (single model)", "6.17", "7.69"],
    ["Equal-weight average of the 5 models", "6.14", "7.59"],
    ["Best single model (picked on validation)", "5.19", "7.47"],
    ["Hedge (classic online weighting)", "5.13", "7.11"],
    ["DWM (dynamic weighted majority)", "4.98", "6.96"],
    ["MLpol", "5.02", "6.55"],
    ["Initial controller (our first design)", "5.01", "6.74"],
    ["MELO (2026)", "4.82", "6.47"],
    [NAME, "4.70", "6.34"],
], [3.6, 1.1, 1.1], bold_rows=(12,))
para(f"{NAME} retrains about 4.3 times a week (MELO: 3, on its weekly schedule) and costs about 31 ms per hourly "
     "step on a laptop. The agentic logic (drift watchdog, MELO, agent) is under 2% of that; the rest is the models.")
figure("fig1_real_data_accuracy.png",
       "Figure 2. Test MAPE and CV-RMSE for every method. Blue = SAGE, orange = MELO.", 6.2)

doc.add_heading("Customer by customer", 2)
table(["Customer", "Hedge", "DWM", "MLpol", "MELO", NAME], [
    ["MT_132", "5.69", "5.47", "5.22", "5.12", "5.21"], ["MT_269", "3.31", "3.15", "3.22", "3.11", "3.15"],
    ["MT_163", "3.39", "3.33", "3.33", "3.09", "3.14"], ["MT_024", "7.35", "7.27", "7.13", "7.06", "7.09"],
    ["MT_135", "13.47", "12.77", "13.41", "12.48", "11.53"], ["MT_105", "5.46", "5.48", "5.41", "5.30", "5.18"],
    ["MT_121", "1.07", "1.02", "1.06", "1.02", "0.98"], ["MT_118", "1.35", "1.34", "1.35", "1.33", "1.30"],
], [1.3, 1.05, 1.05, 1.05, 1.05, 1.05], bold_rows=(4, 5))
para(f"Test MAPE %, SAGE against the four strongest baselines. {NAME} beats Hedge, DWM and MLpol on CV-RMSE for every "
     "customer and on MAPE for 7 of 8 (DWM is 0.001 ahead on MT_269), and MELO on 4 of 8. On the four "
     "regular customers (MT_132, MT_269, MT_163, MT_024) it is within 0.1 point of MELO, with MELO slightly ahead. "
     "Its big wins are MT_135 and MT_105, explained in section 6. Most of the average MAPE gain over MELO comes "
     "from MT_135, so say that openly if asked.")
figure("fig4_per_client.png", "Figure 3. Per-customer MAPE (left, primary) and CV-RMSE (right).", 6.2)

doc.add_heading("Under injected demand shifts", 2)
table(["Scenario", "DWM", "MLpol", "MELO", "MELO daily", NAME], [
    ["No shift", "4.98 / 6.96", "5.02 / 6.55", "4.82 / 6.47", "–", "4.70 / 6.34"],
    ["Level jump", "5.07 / 7.04", "5.15 / 6.71", "4.90 / 6.61", "4.84 / 6.48", "4.75 / 6.45"],
    ["Slow ramp", "5.04 / 6.94", "5.08 / 6.58", "4.86 / 6.50", "4.80 / 6.39", "4.74 / 6.40"],
    ["Bigger swings", "9.73 / 8.22", "10.25 / 7.82", "8.70 / 7.68", "8.95 / 7.59", "8.38 / 7.59"],
    ["Temporary spike", "5.19 / 7.23", "5.27 / 6.91", "4.94 / 6.80", "4.88 / 6.57", "4.79 / 6.58"],
], [1.3, 1.05, 1.05, 1.05, 1.05, 1.05])
para("Each cell is MAPE % / CV-RMSE %. 'MELO daily' retrains its models every day (21 times a week). The 'bigger "
     "swings' MAPE is inflated by MT_135, whose near-zero hours make percentage errors explode, so look at CV-RMSE there.",
     size=10)
bullets([
    f"{NAME} beats MELO on both MAPE and CV-RMSE in every scenario. DWM and MLpol are worse than MELO in every scenario.",
    f"{NAME} beats MELO-retrained-daily on MAPE in every scenario and ties it on CV-RMSE, while retraining about 4 times a week instead of 21.",
    "Detection: the watchdog caught 14/16 temporary spikes (median 30 h), 10/16 level jumps (25 h), 9/16 swing changes and "
    "5/16 slow ramps, with about 0.2 false alarms a week. Slow ramps are the hardest to notice, which is expected.",
    f"Recovery: after temporary spikes {NAME} got back to normal error faster than MELO (median 133 h vs 149 h), but after "
    "level jumps it was slower (138 h vs 114 h).",
])
figure("fig2_shift_vs_baselines.png",
       "Figure 4. Change in MAPE and CV-RMSE against MELO, for each injected shift. Below zero = better than MELO.", 6.2)
figure("fig3_demo_level_shift.png",
       "Figure 5. One injected level shift (customer MT_132, the median detected event). Top: load and forecasts. "
       "Middle: error, with retrains marked. Bottom: how the agent's trust moves between candidates.", 6.2)

# ---------------- 6 ----------------
doc.add_heading(f"6. Where {NAME} helps most, and why", 1)
doc.add_heading("MT_105: a real fivefold jump in demand (23 Oct 2014)", 2)
para(f"MT_105 is {NAME}'s biggest CV-RMSE win: 5.79% against 6.93% for MELO. The cause is one real event in the data.")
bullets([
    ("What happened: ", "after about four quiet weeks at roughly 100 kW (late Sep to 22 Oct 2014), the customer's load "
     "jumped about five times, to around 800 kW, within a few hours on 23 October, stayed there for about a day, then "
     "settled at a higher level than before."),
    (f"What {NAME} did: ", "SARIMA picked up the new level fastest, and the agent moved almost all of its weight onto "
     "SARIMA within five hours. The drift watchdog fired 7 h and 15 h after the jump, and the retrains it triggered "
     "already included the new data. Errors stayed small throughout."),
    ("What MELO did: ", "in MELO's weekly-retrained pool, SARIMA fell back to the old ~100 kW level nine hours after "
     "the jump. MELO's correction experts tried to compensate, and because they can extrapolate beyond the models, "
     "they overshot. At that hour MELO forecast 1,993 kW when the actual load was 824 kW."),
    ("Being honest about it: ", "that one hour accounts for 84% of the squared-error difference on this customer. "
     f"Without it, {NAME} is still better (CV-RMSE 5.80% vs 5.99%), but the big headline number for MT_105 is "
     "mainly MELO's one blow-up. It is still a real failure that SAGE avoided, which is the point of adapting."),
])
figure("fig5_case_MT_105.png",
       "Figure 6. MT_105, 19–31 Oct 2014. Top: load and forecasts. Middle: absolute error, with retrains marked. "
       "Bottom: the agent's weights. Note MELO's spike nine hours after the jump.", 6.2)

doc.add_heading("MT_135: an upside-down daily pattern", 2)
para(f"MT_135 is {NAME}'s biggest MAPE win: 11.53% against 12.48% for MELO, and 7–9% lower in every shift scenario.")
bullets([
    ("What is different about it: ", "most customers use the most power in the daytime. MT_135 is the opposite. "
     "Its load peaks at night (about 680 kW around midnight to 1 am) and drops to 150–300 kW during the day. It is "
     "also the most irregular of the 8 customers, with some hours near zero."),
    ("Where MELO goes wrong: ", "in the quietest quarter of hours, MELO over-forecasts by about 13 kW on average. "
     "That's small in kW but large as a percentage of a ~130 kW load, so MAPE in those hours is 17.7%."),
    (f"What {NAME} does: ", "the agent learns that in these quiet hours the seasonal-naive forecast (the same hour one "
     "week earlier) is more reliable, and almost doubles its weight there (0.16 to 0.30). Bias drops to about 9 kW "
     "and MAPE in those hours drops to 14.1%. At the morning and evening transitions (08:00, 19:00–21:00), where "
     "load changes fastest, it leans on LightGBM, and those hours improve the most (08:00: 27% to 21%)."),
    ("Why this matters: ", "this is the agent doing what it is designed for: learning, from the situation, which "
     "forecaster to trust. MELO weights by recent overall performance and can't tell quiet hours from busy ones."),
])
figure("fig6_case_MT_135.png",
       "Figure 7. MT_135 by hour of day. Top: average load (note the night peak). Middle: MAPE for MELO and SAGE. "
       "Bottom: the agent's average weights.", 6.2)

doc.add_heading("Is the improvement real? (significance)", 2)
para("We ran a Diebold–Mariano test, the standard test for 'is forecast A really better than forecast B?', on each of "
     "40 series (8 customers × 5 scenarios), plus a Wilcoxon test across all 40.")
bullets([
    (f"{NAME} vs MELO: ", "significantly better overall on absolute, squared and percentage error (p ≈ 0.01–0.04). It is "
     "significantly better on 17 series and significantly worse on 5–8, so it doesn't win everywhere."),
    ("Which part does the work: ", "in an ablation without the agent, the drift watchdog and retraining alone give the "
     "same CV-RMSE gain, and the agent adds about 0.1 MAPE point that isn't statistically significant by itself. "
     "Section 6 shows where that agent gain comes from (MT_135)."),
])

# ---------------- 7 ----------------
doc.add_heading("7. What did not work, and bugs fixed", 1)
para("Ideas we tried and dropped (validation showed they were worse):")
bullets([
    "Retraining only on post-shift data. One week is too little for SARIMA and LightGBM.",
    "Resetting MELO after an alarm. It throws away useful history.",
    "Training the agent on squared errors. It over-reacts to rare large errors.",
    "Our initial top-3 inverse-error blend with a bandit. Every adaptive combiner beat it, which is why we moved to MELO.",
])
para("Bugs found in the original code and fixed:")
bullets([
    "Holt-Winters used the wrong seasonal phase.",
    "SARIMA was forecasting up to 168 h ahead without seeing new data.",
    "The drift detector fired almost exactly weekly, acting as a timer rather than a detector.",
    "The recovery-time metric always returned 1 hour.",
])

# ---------------- 8 ----------------
doc.add_heading("8. Glossary", 1)
table(["Term", "Meaning"], [
    ["SAGE", "Self-Adaptive aGEntic forecaster: our final system (MELO + drift watchdog + follow-up retrains + contextual agent)."],
    ["MAPE", "Mean absolute percentage error: the average % the forecast is off by."],
    ["CV-RMSE", "Root-mean-square error divided by mean load, in %. Punishes big misses more and isn't distorted by near-zero hours."],
    ["Prequential", "Forecast, then reveal the truth, then learn, one hour at a time. Simulates live operation."],
    ["Concept drift / demand shift", "The pattern in the data changes over time, so old models go stale."],
    ["ADWIN, Page–Hinkley", "Two classic change detectors. ADWIN compares recent vs older windows; Page–Hinkley tracks a cumulative drift in the mean."],
    ["MLpol", "Online expert-weighting rule with no tuning parameter, the core of MELO."],
    ["DWM, Hedge, FTL", "Other online weighting baselines: dynamic weighted majority, exponential weights, follow-the-leader."],
    ["Contextual bandit", "A learner that picks among options using the current situation (context) and learns from the outcome."],
    ["Ablation", "Removing one component to see how much it contributes."],
    ["Diebold–Mariano test", "Statistical test of whether two forecasts differ in accuracy, allowing for errors that are correlated over time."],
], [1.7, 4.9])

# ---------------- 9 ----------------
doc.add_heading("9. Questions you may be asked", 1)
qa = [
    ("What does SAGE stand for?",
     "Self-Adaptive aGEntic forecaster. It is built on MELO, a 2026 combiner, plus our drift watchdog, follow-up retraining and contextual agent."),
    ("Why not just retrain all the time?",
     "Retraining SARIMA, Holt-Winters and LightGBM constantly is impractical across many meters. We retrain only when "
     "the data says something changed, about 4 times a week, and that beats retraining daily (21 times a week) on MAPE."),
    ("What makes it 'agentic'?",
     "It runs a perceive–decide–act–learn loop on its own. It watches its errors, decides when to retrain, decides which forecast to trust, and learns from each outcome."),
    ("Why build on MELO instead of your own combiner?",
     "Our own first combiner lost to every published adaptive method. MELO was the strongest, so we added what it lacks: change detection, retraining and context."),
    ("Why MAPE as the main metric?",
     "It is the standard in load forecasting and doesn't depend on customer size. We report CV-RMSE next to it because MAPE can blow up at near-zero hours."),
    ("Why do you inject artificial shifts?",
     "Real data has few clearly dated shocks. Injecting them at known times lets us measure detection rate, delay and recovery."),
    ("Weakest point?",
     "On regular customers SAGE only matches MELO; most of its MAPE gain comes from MT_135 and most of its CV-RMSE gain on "
     "MT_105 from one hour where MELO blew up. The agent's own contribution, on top of the watchdog, isn't statistically significant."),
]
for q, a in qa:
    p = doc.add_paragraph(); p.add_run("Q: " + q).bold = True; p.paragraph_format.space_after = Pt(1)
    para("A: " + a)

# ---------------- 10 ----------------
doc.add_heading("10. Where things are", 1)
table(["Path", "What"], [
    ["paper/paper.docx", "The paper (IEEE two-column)"],
    ["code/README.md", "How to run everything, module by module"],
    ["code/results_summary.md", "All headline numbers in one place"],
    ["code/figures_final/, paper/figures_v2/", "Figures (full width / paper column width)"],
    ["code/controller.py, agent.py, combiners.py, drift.py", "The core of the system"],
    ["code/results/", "All result files, one folder per topic (sage/, baselines/, melo/, ...)"],
    ["logs/README.md", "Index of every experiment run"],
    ["RENAMES.md", "Old file names → new ones (2026-10-29 tidy-up)"],
], [2.9, 3.7])
para("SAGE's result files are code/results/sage/sage_*.json. Inside the summary tables it still carries its working label 'proposed + agent'.", italic=True, size=9.5)

doc.save(OUT)
print("->", OUT)
