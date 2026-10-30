import sys, numpy as np, pandas as pd
sys.path.insert(0, ".")
from data_pipeline import load_hourly, ClientSeries
from models import HoltWinters
df = load_hourly()
cs = ClientSeries(df["MT_269"]); y = cs.y.values.astype(float)
lo, hi = cs.splits["val"][0], cs.splits["test"][1]
m = HoltWinters(y); m.retrain(lo); last = lo; P = []; S=[]
for t in range(lo, hi):
    P.append(max(0, m.predict(t))); m.update(t, y[t])
    if t + 1 - last >= 168: m.retrain(t + 1); last = t + 1
P = np.array(P); yt = y[lo:hi]; idx = cs.index[lo:hi]
ape = pd.Series(np.where(yt > 0, np.abs(yt - P) / np.maximum(yt,1) * 100, np.nan), index=idx)
bias = pd.Series(P - yt, index=idx)
print("test starts", cs.index[cs.splits["test"][0]])
print(pd.DataFrame({"MAPE": ape.resample("ME").mean().round(1), "bias": bias.resample("ME").mean().round(0),
                    "meanY": pd.Series(yt, index=idx).resample("ME").mean().round(0)}).to_string())
# one test week: hour-of-day pattern of errors
w = slice(cs.splits["test"][0]-lo+2000, cs.splits["test"][0]-lo+2048)
print(np.c_[np.arange(48)%24, yt[w], P[w].round(0)][:48:3])
