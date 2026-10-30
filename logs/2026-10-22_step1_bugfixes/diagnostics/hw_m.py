import sys, numpy as np
sys.path.insert(0, ".")
from data_pipeline import prepare
from models import HoltWinters
import metrics as M
data = prepare()
for cid, cs in data.items():
    y = cs.y.values.astype(float); row = [cid]
    for blk in ("val", "test"):
        lo, hi = cs.splits[blk]
        for m_, kw in [(24, {})]:
            m = HoltWinters(y, m=m_, **kw); m.retrain(lo); last = lo; P = []
            for t in range(lo, hi):
                P.append(max(0, m.predict(t))); m.update(t, y[t])
                if t + 1 - last >= 168: m.retrain(t + 1); last = t + 1
            row.append(f"{blk}/m{m_}{'*' if kw else ''} {M.mape(y[lo:hi], np.array(P)):.1f}")
    print(" | ".join(row), flush=True)
