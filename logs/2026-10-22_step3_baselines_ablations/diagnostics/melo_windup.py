"""Diagnose MELO's EWLS experts on real val data (MT_132): growth of trace(P) per forgetting
factor, first non-finite step, and collinearity of the pool forecasts. Run from code/."""
import json, os, sys, numpy as np
sys.path.insert(0, os.getcwd())
import adaptive_baselines as AB
S = json.load(open("val_streams_nodrift.json"))["MT_132"]
names = list(S["per_model"]); y = np.asarray(S["y"], float)
F = np.column_stack([np.asarray(S["per_model"][n], float) for n in names])
print("pool corr matrix (min off-diagonal):", np.corrcoef(F.T)[~np.eye(len(names), dtype=bool)].min().round(4))
Z = np.column_stack([F / F[:10].mean(), np.ones(len(y))])
print("condition number of Z'Z:", f"{np.linalg.cond(Z.T @ Z):.2e}")
gam = AB.melo_gammas(); d = Z.shape[1]; ys = y / F[:10].mean(); eps0 = 1e-8
for k in (0, 7, 14, 15):
    g = gam[k]; n0 = 10; wts = g ** np.arange(n0 - 1, -1, -1)
    A = (Z[:n0] * wts[:, None]).T @ Z[:n0] + 1e-6 * np.mean(Z[:n0] ** 2) * np.eye(d)
    P = np.linalg.inv(A); w = P @ ((Z[:n0] * wts[:, None]).T @ ys[:n0]); bad = None; tr = []
    for t in range(n0, len(y)):
        z = Z[t]; Pz = P @ z; s = g + z @ Pz
        w = w + Pz / s * (ys[t] - w @ z)
        P = (P - np.outer(Pz, Pz) / s) / g + eps0 * (1 - g) * np.eye(d)
        tr.append(np.trace(P))
        if bad is None and not np.all(np.isfinite(P)): bad = t
    tr = np.array(tr)
    print(f"gamma {g:.5f} (h={1/(1-g) if g < 1 else np.inf:7.1f}): trace(P) start {tr[0]:.2e}  "
          f"max {np.nanmax(tr):.2e}  end {tr[-1]:.2e}  first non-finite step: {bad}  |w|_end {np.linalg.norm(w):.2e}")

print("\nwith safeguard (symmetrise P each step + cap trace(P) at its post-cold-start value):")
for k in range(len(gam)):
    g = gam[k]; n0 = 10; wts = g ** np.arange(n0 - 1, -1, -1)
    A = (Z[:n0] * wts[:, None]).T @ Z[:n0] + 1e-6 * np.mean(Z[:n0] ** 2) * np.eye(d)
    P = np.linalg.inv(A); w = P @ ((Z[:n0] * wts[:, None]).T @ ys[:n0]); cap = np.trace(P)
    pred = []; capped = 0
    for t in range(n0, len(y)):
        z = Z[t]; pred.append(w @ z); Pz = P @ z; s = g + z @ Pz
        w = w + Pz / s * (ys[t] - w @ z)
        P = (P - np.outer(Pz, Pz) / s) / g + eps0 * (1 - g) * np.eye(d)
        P = 0.5 * (P + P.T); tr = np.trace(P)
        if tr > cap: P *= cap / tr; capped += 1
    pred = np.array(pred); yy = ys[n0:]
    mape = np.mean(np.abs(yy - pred)[yy > 1e-6] / yy[yy > 1e-6]) * 100
    print(f"  gamma {g:.5f} (h={1/(1-g) if g < 1 else np.inf:7.1f}): MAPE {mape:6.2f}  "
          f"min eig(P) end {np.linalg.eigvalsh(P).min():.1e}  steps capped {capped}")
