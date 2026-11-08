"""Content-free detectors over access logs. Feature definitions follow PROTOCOL.md exactly.

Detectors see only: t, principal, op, obj, name, size, resolves. They never see `board`.
Everything is computed online: a window's features use only events up to that window's end.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

WIN = 600  # seconds, frozen
FEATURES = ["F1_reciprocity", "F2_cross_writers", "F3_delay", "F4_size", "F5_unresolved"]
# sign: +1 means larger = more suspicious
SIGN = {"F1_reciprocity": 1, "F2_cross_writers": 1, "F3_delay": -1, "F4_size": -1, "F5_unresolved": 1}
GRAPH = ["F1_reciprocity", "F2_cross_writers", "F3_delay"]
META = ["F4_size", "F5_unresolved"]
DEFAULT_SIZE = 300e3


def shuffle_principals(log: pd.DataFrame, seed: int) -> pd.DataFrame:
    """Control 4: permute principal labels across events within each window."""
    rng = np.random.default_rng(seed)
    out = log.copy()
    w = (out.t // WIN).astype(int).to_numpy()
    p = out.principal.to_numpy().copy()
    for wi in np.unique(w):
        idx = np.flatnonzero(w == wi)
        p[idx] = rng.permutation(p[idx])
    out["principal"] = p
    return out


def single_principal(log: pd.DataFrame) -> pd.DataFrame:
    """Control 3: replay the log with every event attributed to one principal."""
    out = log.copy()
    out["principal"] = 0
    return out


def window_features(log: pd.DataFrame, duration: float, service=()) -> pd.DataFrame:
    """Per-window features. `service`: declared service principals (v2, D2) whose writes are
    kept for attribution but excluded from the graph and from F3-F5."""
    n_win = int(np.ceil(duration / WIN))
    log = log.sort_values("t", kind="stable").reset_index(drop=True)
    log["win"] = (log.t // WIN).astype(int)

    # attribute every read to the last write of that object before it
    is_w = log.op == 0
    log["w_idx"] = np.where(is_w, log.index, np.nan)
    log["w_idx"] = log.groupby("obj")["w_idx"].ffill()
    log["writer"] = np.where(is_w, log.principal, np.nan)
    log["writer"] = log.groupby("obj")["writer"].ffill()

    reads = log[(log.op == 1) & log.writer.notna()]
    svc = np.asarray(list(service))
    cross = reads[(reads.writer != reads.principal) & ~reads.writer.isin(svc)]

    # F1, F2: per-window edge set
    edges = cross[["win", "writer", "principal"]].drop_duplicates()
    edges = edges.astype({"writer": int, "principal": int})
    f1 = np.zeros(n_win)
    f2 = np.zeros(n_win)
    if len(edges):
        e = edges.rename(columns={"writer": "a", "principal": "b"})
        rev = e.rename(columns={"a": "b", "b": "a"})
        m = e.merge(rev, on=["win", "a", "b"], how="left", indicator=True)
        recip = (m["_merge"] == "both").groupby(m.win).mean()
        f1[recip.index.to_numpy()] = recip.to_numpy()
        cw = e.groupby("win").a.nunique()
        f2[cw.index.to_numpy()] = cw.to_numpy()

    # F3: median delay from write to first foreign read, censored at window end
    writes = log[is_w & ~log.principal.isin(svc)][["t", "win", "obj", "size", "resolves", "principal"]].copy()
    first_foreign = cross.groupby("w_idx").t.min()
    writes["first_read"] = first_foreign.reindex(writes.index).to_numpy()
    wend = (writes.win + 1) * WIN
    seen = writes.first_read.notna() & (writes.first_read < wend)
    writes["delay"] = np.where(seen, writes.first_read - writes.t, WIN)
    f3 = np.full(n_win, float(WIN))
    d = writes.groupby("win").delay.median()
    f3[d.index.to_numpy()] = d.to_numpy()

    # F4: median size of objects written in window and cross-read within it
    f4 = np.full(n_win, DEFAULT_SIZE)
    s = writes[seen].groupby("win")["size"].median()
    f4[s.index.to_numpy()] = s.to_numpy()

    # F5: share of objects written in window whose name does not resolve upstream
    f5 = np.zeros(n_win)
    u = (~writes.resolves.astype(bool)).groupby(writes.win).mean()
    f5[u.index.to_numpy()] = u.to_numpy()

    vol = np.bincount(log.win, minlength=n_win)[:n_win]
    pref = np.zeros(n_win, bool)
    zz = log[log.name.astype(str).str.startswith("zz")].win.unique()
    pref[zz[zz < n_win]] = True

    return pd.DataFrame({"win": np.arange(n_win), "F1_reciprocity": f1, "F2_cross_writers": f2,
                         "F3_delay": f3, "F4_size": np.log10(np.maximum(f4, 1)),
                         "F5_unresolved": f5, "VOLUME": vol.astype(float), "PREFIX": pref})


class Calibration:
    """z-scoring stats and 99th-percentile thresholds fitted on calibration clean windows only."""

    def __init__(self, calib_feats: pd.DataFrame, q: float = 0.99):
        self.mu = calib_feats[FEATURES].mean()
        self.sd = calib_feats[FEATURES].std().replace(0, 1.0)
        sc = self.scores(calib_feats)
        self.thr = {c: float(np.quantile(sc[c], q)) for c in sc.columns if c != "PREFIX"}
        self.thr["PREFIX"] = 0.5

    def scores(self, f: pd.DataFrame) -> pd.DataFrame:
        z = (f[FEATURES] - self.mu) / self.sd
        for c in FEATURES:
            z[c] = z[c] * SIGN[c]
        out = pd.DataFrame(index=f.index)
        out["GRAPH"] = z[GRAPH].sum(axis=1)
        out["GRAPH+META"] = z[GRAPH + META].sum(axis=1)
        out["VOLUME"] = f["VOLUME"]
        out["PREFIX"] = f["PREFIX"].astype(float)
        for c in FEATURES:
            out[c] = z[c]
        return out

    def alerts(self, f: pd.DataFrame) -> pd.DataFrame:
        sc = self.scores(f)
        return pd.DataFrame({c: sc[c] > self.thr[c] for c in sc.columns})
