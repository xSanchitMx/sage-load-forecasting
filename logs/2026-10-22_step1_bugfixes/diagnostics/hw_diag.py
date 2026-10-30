import sys, numpy as np
sys.path.insert(0, ".")
from data_pipeline import load_hourly, ClientSeries
from models import HoltWinters
df = load_hourly()
for cid in ["MT_269", "MT_163", "MT_132"]:
    cs = ClientSeries(df[cid]); y = cs.y.values.astype(float)
    lo, hi = cs.splits["test"]
    m = HoltWinters(y); m.retrain(lo)
    last = lo; P = []
    for t in range(lo, hi):
        P.append(max(0, m.predict(t))); m.update(t, y[t])
        if t + 1 - last >= 168: m.retrain(t + 1); last = t + 1
    P = np.array(P); yt = y[lo:hi]; ape = np.abs(yt - P) / np.maximum(yt, 1e-6) * 100
    print(cid, "MAPE", ape.mean().round(2), "median APE", np.median(ape).round(2),
          "zeros in y", (yt == 0).sum(), "min y", yt.min(), "mean y", yt.mean().round(0))
    worst = np.argsort(ape)[-5:]
    for w in worst: print("   t", lo + w, "y", yt[w], "pred", round(P[w], 1), "level", )
    # trend check
    print("   trend at end", round(m.trend, 2), "level", round(m.level, 1))
