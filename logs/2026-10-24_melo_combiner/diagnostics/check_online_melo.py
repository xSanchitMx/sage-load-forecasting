"""Check: online combiners.MELO (one step at a time) == batch adaptive_baselines.melo
on the saved test streams (no-drift pool), per client."""
import os, sys, numpy as np
sys.path.insert(0, os.getcwd())
import adaptive_baselines as AB, metrics as M
from combiners import MELO
data = AB.load("test_streams_nodrift.json")
for c, (y, F, L) in data.items():
    a = AB.melo(y, F, L, eps0=0.01)
    m = MELO(F.shape[1], eps0=0.01)
    b = np.empty(len(y))
    for t in range(len(y)):
        b[t] = m.predict(F[t]); m.update(y[t])
    print(f"{c}: max|diff| {np.max(np.abs(a-b)):.3e}  rel {np.max(np.abs(a-b)/np.maximum(1,np.abs(a))):.3e}  "
          f"MAPE batch {M.mape(y,a):.4f} online {M.mape(y,b):.4f}")
