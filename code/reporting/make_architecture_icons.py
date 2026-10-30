"""
Pictorial architecture of SAGE (layered icon diagram), sized for one column of the
two-column paper. Complements the data-flow view in architecture_pictorial_v2.png.
Writes paper/architecture_icons.png (300 dpi) and code/figures_final/fig0_architecture_icons.png.
Every element is drawn from matplotlib primitives, so no external images are needed.
"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))   # code/: core modules
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Circle, Polygon, Rectangle, Wedge, FancyArrowPatch, Arc

PROJECT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUTS = [os.path.join(PROJECT, "paper", "architecture_icons.png"),
        os.path.join(PROJECT, "code", "figures_final", "fig0_architecture_icons.png")]

BLUE, ORANGE, AQUA, YELLOW, MAGENTA, GREEN = "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300"
RED = "#c8442f"
INK, INK2, GRID = "#1d1d1b", "#52514e", "#d6d4cd"
TIER = ["#eef4fb", "#f1f8f4", "#fdf3e9", "#eef4fb", "#fbeeee"]
LW = 0.9

fig = plt.figure(figsize=(3.5, 5.385))
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, 104); ax.set_ylim(0, 160); ax.set_aspect("equal"); ax.axis("off")


def box(x, y, w, h, fc, ec=GRID, r=2.2, lw=0.7, z=1):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0,rounding_size={r}",
                                fc=fc, ec=ec, lw=lw, zorder=z))


def text(x, y, s, size=6.2, color=INK, weight="normal", ha="center", va="center", style="normal", z=5):
    ax.text(x, y, s, fontsize=size, color=color, weight=weight, ha=ha, va=va, style=style, zorder=z)


def arrow(p, q, color=BLUE, lw=1.1, rad=0.0, z=4, ls="-"):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle="-|>", mutation_scale=6.5, color=color, lw=lw,
                                 connectionstyle=f"arc3,rad={rad}", zorder=z, linestyle=ls,
                                 shrinkA=0, shrinkB=0))


def badge(x, y, n, color=INK2):
    ax.add_patch(Circle((x, y), 2.4, fc=color, ec="none", zorder=6))
    text(x, y, str(n), size=5.6, color="white", weight="bold", z=7)


# ---------------------------------------------------------------- icons
def pylon(cx, by, h=14, color=INK2):
    w = h * 0.55
    top = by + h
    pts = [(cx - w / 2, by), (cx - w * 0.12, top - h * 0.25), (cx, top), (cx + w * 0.12, top - h * 0.25), (cx + w / 2, by)]
    ax.plot([p[0] for p in pts], [p[1] for p in pts], color=color, lw=LW, zorder=3)
    for f in (0.35, 0.6):                                    # cross arms
        yy = by + h * f
        half = w / 2 * (1 - f) + w * 0.12 * f
        ax.plot([cx - half - 2.6, cx + half + 2.6], [yy + h * 0.12] * 2, color=color, lw=LW, zorder=3)
    for k in range(3):                                       # lattice
        y0, y1 = by + h * k / 4, by + h * (k + 1) / 4
        x0, x1 = w / 2 * (1 - k / 4 * 0.85), w / 2 * (1 - (k + 1) / 4 * 0.85)
        ax.plot([cx - x0, cx + x1], [y0, y1], color=color, lw=0.5, zorder=3)
        ax.plot([cx + x0, cx - x1], [y0, y1], color=color, lw=0.5, zorder=3)


def meter(cx, cy, s=1.0):
    box(cx - 4.2 * s, cy - 5 * s, 8.4 * s, 10 * s, "white", INK2, r=1.2 * s, lw=0.7, z=3)
    ax.add_patch(Rectangle((cx - 3 * s, cy + 1 * s), 6 * s, 2.6 * s, fc="#dff0e6", ec=INK2, lw=0.5, zorder=4))
    text(cx, cy + 2.3 * s, "kWh", size=3.6, color=GREEN, weight="bold", z=5)
    ax.add_patch(Wedge((cx, cy - 2 * s), 2.3 * s, 0, 180, fc="none", ec=INK2, lw=0.5, zorder=4))
    ax.plot([cx, cx + 1.4 * s], [cy - 2 * s, cy - 0.6 * s], color=RED, lw=0.6, zorder=5)


def house(cx, by, s=1.0, fc="white"):
    ax.add_patch(Polygon([(cx - 3.6 * s, by), (cx - 3.6 * s, by + 4.2 * s), (cx, by + 7.4 * s),
                          (cx + 3.6 * s, by + 4.2 * s), (cx + 3.6 * s, by)], closed=True, fc=fc, ec=INK2, lw=0.6, zorder=3))
    ax.add_patch(Rectangle((cx - 0.9 * s, by), 1.8 * s, 2.6 * s, fc=INK2, ec="none", zorder=4))


def factory(cx, by, s=1.0):
    pts = [(cx - 5 * s, by), (cx - 5 * s, by + 4 * s), (cx - 2.5 * s, by + 6 * s), (cx - 2.5 * s, by + 4 * s),
           (cx, by + 6 * s), (cx, by + 4 * s), (cx + 2.5 * s, by + 4 * s), (cx + 2.5 * s, by + 8.5 * s),
           (cx + 4 * s, by + 8.5 * s), (cx + 4 * s, by + 4 * s), (cx + 5 * s, by + 4 * s), (cx + 5 * s, by)]
    ax.add_patch(Polygon(pts, closed=True, fc="white", ec=INK2, lw=0.6, zorder=3))


def card(cx, cy, label, color, glyph):
    w, h = 15.2, 13.5
    box(cx - w / 2, cy - h / 2, w, h, "white", color, r=1.6, lw=0.9, z=3)
    ax.add_patch(Rectangle((cx - w / 2 + 0.4, cy + h / 2 - 2.0), w - 0.8, 1.6, fc=color, ec="none", zorder=4))
    gx = np.linspace(cx - 5.2, cx + 5.2, 60)
    gy = cy + 1.0
    if glyph == "repeat":                                     # same week again
        y = gy + 1.6 * np.sin((gx - gx[0]) / 10.4 * 4 * np.pi)
        ax.plot(gx[:30], y[:30], color=color, lw=0.8, zorder=5)
        ax.plot(gx[30:], y[:30], color=color, lw=0.8, zorder=5, ls=(0, (1.2, 0.8)))
    elif glyph == "smooth":                                   # level + trend + season
        ax.plot(gx, gy - 1.4 + 0.25 * (gx - gx[0]) + 1.2 * np.sin((gx - gx[0]) / 10.4 * 4 * np.pi), color=color, lw=0.8, zorder=5)
    elif glyph == "arima":                                    # autocorrelated wiggle with lags
        rng = np.random.default_rng(3)
        e = np.cumsum(rng.normal(0, 0.35, 60)); e -= e.mean()
        ax.plot(gx, gy + e + 1.0 * np.sin((gx - gx[0]) / 10.4 * 4 * np.pi), color=color, lw=0.7, zorder=5)
    elif glyph == "tree":                                     # boosted trees
        for dx in (-3.2, 3.2):
            r = (cx + dx, gy + 2.4)
            for side in (-1, 1):
                l = (r[0] + side * 1.8, gy - 0.2)
                ax.plot([r[0], l[0]], [r[1], l[1]], color=color, lw=0.7, zorder=5)
                for s2 in (-1, 1):
                    ax.plot([l[0], l[0] + s2 * 0.9], [l[1], l[1] - 2.0], color=color, lw=0.6, zorder=5)
            ax.add_patch(Circle(r, 0.5, fc=color, ec="none", zorder=6))
    elif glyph == "line":                                     # online regression
        rng = np.random.default_rng(1)
        px = np.linspace(cx - 4.6, cx + 4.6, 9); py = gy - 1.8 + 0.4 * (px - px[0]) + rng.normal(0, 0.45, 9)
        ax.scatter(px, py, s=1.5, color=INK2, zorder=5, linewidths=0)
        ax.plot([px[0], px[-1]], [gy - 1.8, gy - 1.8 + 0.4 * (px[-1] - px[0])], color=color, lw=0.9, zorder=5)
    text(cx, cy - 4.4, label, size=4.6, color=INK, weight="bold")


def robot(cx, cy, s=1.0):
    ax.plot([cx, cx], [cy + 5.2 * s, cy + 7.2 * s], color=INK2, lw=0.8, zorder=3)
    ax.add_patch(Circle((cx, cy + 7.7 * s), 0.9 * s, fc=ORANGE, ec="none", zorder=4))
    box(cx - 6 * s, cy - 4.4 * s, 12 * s, 9.6 * s, "white", BLUE, r=2.4 * s, lw=1.1, z=3)
    for dx in (-2.4, 2.4):
        ax.add_patch(Circle((cx + dx * s, cy + 1.3 * s), 1.3 * s, fc=BLUE, ec="none", zorder=4))
        ax.add_patch(Circle((cx + dx * s + 0.35 * s, cy + 1.6 * s), 0.4 * s, fc="white", ec="none", zorder=5))
    ax.add_patch(Arc((cx, cy - 1.4 * s), 5 * s, 2.6 * s, theta1=200, theta2=340, color=BLUE, lw=0.9, zorder=4))
    for dx in (-6.6, 6.6):
        ax.add_patch(Rectangle((cx + dx * s - 0.6 * s, cy - 1.2 * s), 1.2 * s, 3.4 * s, fc=BLUE, ec="none", zorder=4))


def dial(cx, cy, label, frac, r=3.0):
    ax.add_patch(Wedge((cx, cy), r, 0, 180, fc="white", ec=INK2, lw=0.6, zorder=3))
    for f, c in ((0.33, AQUA), (0.66, YELLOW), (1.0, RED)):
        ax.add_patch(Wedge((cx, cy), r, 180 * (1 - f), 180 * (1 - f + 0.33), width=0.8, fc=c, ec="none", zorder=4))
    a = np.pi * (1 - frac)
    ax.plot([cx, cx + 0.8 * r * np.cos(a)], [cy, cy + 0.8 * r * np.sin(a)], color=INK, lw=0.8, zorder=5)
    text(cx, cy - 2.7, label, size=4.2, color=INK2)


def bell(cx, cy, s=1.0, color=RED):
    u = np.linspace(0, 1, 30)                                 # 0 = rim, 1 = top
    half = (1.5 + 2.1 * (1 - u) ** 2.2) * s
    yy = cy - 2.8 * s + 5.4 * s * u
    pts = list(zip(cx - half, yy)) + list(zip(cx + half[::-1], yy[::-1]))
    ax.add_patch(Polygon(pts, closed=True, fc=color, ec="none", zorder=4))
    ax.add_patch(Circle((cx, cy + 2.6 * s), 1.5 * s, fc=color, ec="none", zorder=4))
    ax.add_patch(Circle((cx, cy + 4.5 * s), 0.55 * s, fc="none", ec=color, lw=0.8, zorder=4))
    ax.add_patch(Rectangle((cx - 4.0 * s, cy - 3.4 * s), 8 * s, 0.9 * s, fc=color, ec="none", zorder=4))
    ax.add_patch(Circle((cx, cy - 4.0 * s), 0.8 * s, fc=color, ec="none", zorder=4))
    for side in (-1, 1):                                      # ringing marks
        ax.add_patch(Arc((cx, cy), 10 * s, 9 * s, theta1=90 - side * 25 - 12, theta2=90 - side * 25 + 12,
                         color=color, lw=0.7, zorder=4))


def gear(cx, cy, r=4.2, teeth=8, color=RED):
    ang = np.linspace(0, 2 * np.pi, teeth * 4, endpoint=False)
    rr = np.where((np.arange(len(ang)) // 2) % 2 == 0, r, r * 0.76)
    ax.add_patch(Polygon(np.c_[cx + rr * np.cos(ang), cy + rr * np.sin(ang)], closed=True, fc=color, ec="none", zorder=4))
    ax.add_patch(Circle((cx, cy), r * 0.36, fc="white", ec="none", zorder=5))


def chart(cx, cy, w=16, h=9):
    box(cx - w / 2, cy - h / 2, w, h, "white", INK2, r=1.0, lw=0.6, z=3)
    x = np.linspace(cx - w / 2 + 1.2, cx + w / 2 - 1.2, 80)
    base = cy - 0.6 + 2.2 * np.sin((x - x[0]) / (w - 2.4) * 4 * np.pi)
    ax.plot(x, base, color=INK, lw=0.6, zorder=4)
    ax.plot(x, base + 0.45 * np.sin((x - x[0]) * 2.7), color=BLUE, lw=0.8, zorder=5)


# ---------------------------------------------------------------- tiers
tiers = [(138, 20, "Data", "8 customers · hourly load (UCI)"),
         (110, 26, "Model pool", "five forecasters, run every hour"),
         (86, 22, "MELO", ""),
         (49, 35, "Contextual agent", ""),
         (5, 42, "Serve · watch · retrain", "")]
for k, (y, h, title, sub) in enumerate(tiers):
    box(3, y, 94, h, TIER[k], GRID, r=2.4, lw=0.6, z=1)
    badge(7.5, y + h - 4.0, k + 1)
    text(11.5, y + h - 4.0, title, size=6.4, weight="bold", ha="left")
    if sub:
        text(95, y + h - 4.0, sub, size=4.6, color=INK2, ha="right", style="italic")

# 1. data
pylon(14, 140.5, h=12)
for cx in (32, 50, 68):
    meter(cx, 147.0, s=0.82)
house(83, 141, s=0.95); factory(91, 141, s=0.75)
ax.plot([18, 85], [151.5, 151.5], color=INK2, lw=0.4, zorder=2, ls=(0, (2, 1.5)))

# 2. model pool
names = [("Seasonal\nnaive", GREY := "#8c8b86", "repeat"), ("Holt-\nWinters", MAGENTA, "smooth"),
         ("SARIMA", YELLOW, "arima"), ("LightGBM", AQUA, "tree"), ("Online\nlinear", GREEN, "line")]
for i, (lab, col, g) in enumerate(names):
    card(14 + i * 18, 120.5, lab, col, g)
arrow((50, 138), (50, 128.6))

# 3. MELO funnel
fx, fy = 50, 92
ax.add_patch(Polygon([(fx - 15, fy + 9), (fx + 15, fy + 9), (fx + 3.2, fy + 1.5), (fx + 3.2, fy - 1.0),
                      (fx - 3.2, fy - 1.0), (fx - 3.2, fy + 1.5)], closed=True, fc="#fde3cf", ec=ORANGE, lw=0.9, zorder=3))
rng = np.random.default_rng(7)
for j in range(21):                                           # 5 raw + 16 corrected forecasts
    px, py = fx - 13 + 26 * (j % 11) / 10, fy + 7.3 - 2.2 * (j // 11) + rng.normal(0, 0.15)
    ax.add_patch(Circle((px, py), 0.55, fc=(INK2 if j < 5 else ORANGE), ec="none", zorder=4))
text(fx, fy + 0.3, "1", size=4.0, color=ORANGE, weight="bold", z=6)
text(20, fy + 8.2, "combiner", size=4.6, color=ORANGE, weight="bold")
text(20, fy + 5.5, "5 raw", size=4.4, color=INK2)
text(20, fy + 2.6, "+16 corrected", size=4.4, color=ORANGE)
text(80, fy + 5.5, "MLpol weights", size=4.4, color=INK2)
text(80, fy + 2.6, "by recent regret", size=4.4, color=INK2)
for i in range(5):
    arrow((14 + i * 18, 113.6), (fx - 13 + 26 * i / 4 * 0.9 + 1.2, fy + 9.6), color=BLUE, lw=0.7)

# 4. agent
robot(50, 66.5, s=1.05)
arrow((50, fy - 1.0), (50, 74.8))
text(50, 57.6, "predicts each of 6 candidates' error\n(MELO + 5 models) → soft mix", size=4.4, color=INK2)
for i, (lab, f) in enumerate((("hour /\nday", 0.4), ("recent\nerrors", 0.7), ("alarm\nrecency", 0.2))):
    dial(14, 74 - i * 7.6, lab, f, r=2.6)
ax.add_patch(FancyArrowPatch((19, 66.5), (41, 66.5), arrowstyle="-|>", mutation_scale=6, color=INK2, lw=0.8, zorder=4))
text(30, 68.6, "28 context\nfeatures", size=4.2, color=INK2)
# real mean agent weights of SAGE on MT_132 (test block, after the 1-week warm-up)
import json
_D = json.load(open(os.path.join(PROJECT, "code", "results", "sage", "hourly_detail", "sage_MT_132_none.json")))
_w = np.asarray(_D["agent_weights"])[168:].mean(axis=0)      # melo, s-naive, H-W, SARIMA, LightGBM, online
bars = [("MELO", _w[0], ORANGE), ("SARIMA", _w[3], YELLOW), ("LightGBM", _w[4], AQUA),
        ("online", _w[5], GREEN), ("other 2", _w[1] + _w[2], GRID)]
for i, (lab, w, c) in enumerate(bars):
    yb = 72 - i * 3.6
    ax.add_patch(Rectangle((78, yb - 1.1), 55 * w, 2.2, fc=c, ec="none", zorder=4))
    text(77, yb, lab, size=4.2, color=INK2, ha="right")
    text(78.6 + 55 * w, yb, f"{w:.2f}", size=3.8, color=INK2, ha="left")
text(84, 76.6, "mean mix weights (MT_132)", size=4.2, color=INK2)
ax.add_patch(FancyArrowPatch((57.8, 66.5), (64.5, 66.5), arrowstyle="-|>", mutation_scale=6, color=INK2, lw=0.8, zorder=4))

# 5. serve / watch / retrain
chart(22, 30, w=26, h=13)
text(22, 21.0, "served forecast vs actual", size=4.6, color=INK2)
arrow((42, 55.0), (24, 36.8), rad=0.12)
bell(52, 30.5, s=1.0)
text(52, 21.0, "drift watchdog\nADWIN + Page–Hinkley", size=4.4, color=RED)
arrow((35.5, 30), (46.5, 30), color=RED, lw=0.9)
text(41, 32.6, "error", size=4.2, color=RED)
gear(80, 31.5, r=4.6); gear(86.5, 26, r=3.0)
text(81, 19.0, "retrain H-W, SARIMA,\nLightGBM: now, +1 d, +3 d, +7 d", size=4.2, color=RED)
arrow((57.5, 30.5), (74.2, 30.5), color=RED, lw=0.9)
text(66, 33.0, "alarm", size=4.2, color=RED)
# feedback loop back to the model pool, along the right edge
ax.add_patch(FancyArrowPatch((91, 35.5), (100, 47), arrowstyle="-", color=RED, lw=0.9, zorder=4,
                             connectionstyle="arc3,rad=0.25"))
ax.plot([100, 100], [47, 120.5], color=RED, lw=0.9, zorder=4)
arrow((100, 120.5), (97.4, 120.5), color=RED, lw=0.9)
text(102, 84, "refit the models", size=4.4, color=RED, ha="center", va="center")
ax.texts[-1].set_rotation(90)
# legend strip
for i, (c, lab) in enumerate(((BLUE, "forecast path"), (RED, "adaptation (drift → retrain)"))):
    ax.plot([8 + i * 38, 14 + i * 38], [9, 9], color=c, lw=1.2)
    text(15.5 + i * 38, 9, lab, size=4.4, color=INK2, ha="left")
text(50, 13.2, "everything learns from each new hour: MELO, the agent and the online models", size=4.4,
     color=INK2, style="italic")

for p in OUTS:
    fig.savefig(p, dpi=300, facecolor="white")
print("->", OUTS)
