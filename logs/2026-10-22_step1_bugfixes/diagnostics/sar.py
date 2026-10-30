import sys, time, warnings, numpy as np
warnings.filterwarnings("ignore")
sys.path.insert(0, ".")
from data_pipeline import load_hourly, ClientSeries
from models import SARIMAModel
import metrics as M
df = load_hourly()
for cid in sys.argv[1:]:
    cs = ClientSeries(df[cid]); y = cs.y.values.astype(float)
    for blk in ("val", "test"):
        lo, hi = cs.splits[blk]; hi = min(hi, lo + 1500)
        m = SARIMAModel(y); m.retrain(lo); last = lo; P = []; t0 = time.perf_counter()
        for t in range(lo, hi):
            P.append(max(0, m.predict(t))); m.update(t, y[t])
            if t + 1 - last >= 168: m.retrain(t + 1); last = t + 1
        print(cid, blk, "MAPE", round(M.mape(y[lo:hi], np.array(P)), 2),
              f"{(time.perf_counter()-t0)/len(P)*1000:.1f} ms/step", flush=True)
