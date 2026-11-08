"""Run the frozen PROTOCOL.md grid: calibration, held-out clean, channel grid, controls.

Usage: python3 run_grid.py [--out results/frozen] [--workers 8]
Writes: windows.csv.gz (per-window features of every run), calibration.json, runs.csv (per run x detector).
"""
from __future__ import annotations

import argparse
import json
import os
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

from aca.detect import WIN, Calibration, shuffle_principals, single_principal, window_features
from aca.sim import CACHE_SYSTEM, DAY, GROWTH, LOAD, N_CI, Config, simulate

CALIB_SEEDS = range(0, 30)
HELDOUT_SEEDS = range(100, 130)
CHANNEL_SEEDS = range(1000, 1010)


def job(spec):
    kind, load, growth, disguise, seed, variant, v2 = spec
    cfg = Config(n_agents=LOAD[load], seed=seed, read_only=(kind == "readonly"))
    if kind == "channel":
        cfg.channel = True
        cfg.p_adopt = GROWTH[growth]
        cfg.disguise = disguise
    log, truth = simulate(cfg)
    b = log[log.board & (log.op == 0)]
    firsts = b.groupby("principal").t.min().to_numpy()  # ground truth, taken before any relabelling
    if variant == "shuffled":
        log = shuffle_principals(log, seed + 7)
    elif variant == "single":
        log = single_principal(log)
    service = [CACHE_SYSTEM, *range(LOAD[load], LOAD[load] + N_CI)] if v2 else ()
    f = window_features(log.drop(columns="board"), DAY, service=service)
    meta = dict(kind=kind, load=load, growth=growth, disguise=disguise, seed=seed, variant=variant)
    for k, v in meta.items():
        f[k] = v
    if truth["channel"]:
        win_end = (np.arange(len(f)) + 1) * WIN
        posters_by_win = np.searchsorted(np.sort(firsts), win_end, side="left")
        f["posters"] = posters_by_win
        f["start"] = truth["start"]
    else:
        f["posters"] = 0
        f["start"] = np.nan
    return f


def specs(v2, off=0):
    out = []
    for load in LOAD:
        out += [("calib", load, None, False, s, "none") for s in CALIB_SEEDS]
        if v2:  # D3: shuffled control gets its own calibration
            out += [("calib", load, None, False, s, "shuffled") for s in CALIB_SEEDS]
        out += [("heldout", load, None, False, s, "none") for s in HELDOUT_SEEDS]
        out += [("readonly", load, None, False, s, "none") for s in HELDOUT_SEEDS]
        out += [("heldout", load, None, False, s, "single") for s in HELDOUT_SEEDS]
        for g in GROWTH:
            for d in (False, True):
                out += [("channel", load, g, d, s, "none") for s in CHANNEL_SEEDS]
            out += [("channel", load, g, False, s, "shuffled") for s in CHANNEL_SEEDS]
            out += [("channel", load, g, False, s, "single") for s in CHANNEL_SEEDS]
    return [(o[0], o[1], o[2], o[3], o[4] + off, o[5], v2) for o in out]


def summarise(win: pd.DataFrame, cal: Calibration, v2: bool = False) -> pd.DataFrame:
    rows = []
    al = cal.alerts(win)
    win = pd.concat([win.reset_index(drop=True), al.add_prefix("A_").reset_index(drop=True)], axis=1)
    keys = ["kind", "load", "growth", "disguise", "seed", "variant"]
    for key, g in win.groupby(keys, dropna=False, sort=False):
        g = g.sort_values("win")
        rec = dict(zip(keys, key))
        for det in al.columns:
            a = g["A_" + det].to_numpy()
            if rec["kind"] == "channel":
                w0 = int(g.start.iloc[0] // WIN)
                ok = a[w0:] & (g.posters.to_numpy()[w0:] >= 1) if v2 else a[w0:]  # D4
                hit = np.flatnonzero(ok)
                final = int(g.posters.iloc[-1])
                if hit.size:
                    w = w0 + hit[0]
                    rows.append({**rec, "detector": det, "detected": True,
                                 "participants": int(g.posters.iloc[w]),
                                 "minutes": (w + 1) * WIN / 60 - g.start.iloc[0] / 60,
                                 "final_participants": final, "fpr_prestart": a[:w0].mean()})
                else:
                    rows.append({**rec, "detector": det, "detected": False,
                                 "participants": final + 1, "minutes": np.nan,
                                 "final_participants": final, "fpr_prestart": a[:w0].mean()})
            else:
                rows.append({**rec, "detector": det, "alert_rate": a.mean(), "any_alert": bool(a.any())})
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="results/frozen")
    ap.add_argument("--workers", type=int, default=os.cpu_count())
    ap.add_argument("--v2", action="store_true", help="apply PROTOCOL.md deviations D1-D4")
    ap.add_argument("--seed-offset", type=int, default=0, help="fresh-seed confirmation run")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    sp = specs(a.v2, a.seed_offset)
    with ProcessPoolExecutor(a.workers) as ex:
        frames = list(ex.map(job, sp, chunksize=2))
    win = pd.concat(frames, ignore_index=True)
    win.to_csv(f"{a.out}/windows.csv.gz", index=False)
    if not a.v2:
        cal = Calibration(win[win.kind == "calib"])
        json.dump({"mu": cal.mu.to_dict(), "sd": cal.sd.to_dict(), "thr": cal.thr},
                  open(f"{a.out}/calibration.json", "w"), indent=1)
        runs = summarise(win[win.kind != "calib"], cal)
    else:  # D1 per-load calibration; D3 shuffled runs use shuffled calibration
        parts, dump = [], {}
        calvar = np.where(win.variant == "shuffled", "shuffled", "none")
        for load in LOAD:
            for cv in ("none", "shuffled"):
                m = (win.load == load) & (calvar == cv)
                cal = Calibration(win[m & (win.kind == "calib")])
                dump[f"{load}/{cv}"] = {"mu": cal.mu.to_dict(), "sd": cal.sd.to_dict(), "thr": cal.thr}
                ev = win[m & (win.kind != "calib")]
                if len(ev):
                    parts.append(summarise(ev, cal, v2=True))
        json.dump(dump, open(f"{a.out}/calibration.json", "w"), indent=1)
        runs = pd.concat(parts, ignore_index=True)
    runs.to_csv(f"{a.out}/runs.csv", index=False)
    print(f"{len(sp)} runs -> {a.out}")


if __name__ == "__main__":
    main()
