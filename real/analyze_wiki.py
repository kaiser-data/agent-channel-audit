"""Real-data arm (PROTOCOL D7): frozen GRAPH detector on the dse-wiki request log.

Inputs: real/data/events_26MM.csv.gz (from ingest_wiki.py) and collusion.wiki revisions.jsonl.gz.
Usage: python3 real/analyze_wiki.py <path/to/revisions.jsonl.gz>
Writes results/real/summary.json and results/real/windows.csv.gz; prints every reported number.
"""
import glob
import gzip
import json
import os
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from aca.detect import WIN, Calibration, shuffle_principals, single_principal, window_features  # noqa: E402

HERE = os.path.dirname(__file__)
OUT = os.path.join(HERE, "..", "results", "real")


def ts(s):
    return int(datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp())


T0 = ts("2026-03-01T00:00:00Z")
CAL = (ts("2026-03-01T00:00:00Z"), ts("2026-05-01T00:00:00Z"))
HELD = (ts("2026-05-01T00:00:00Z"), ts("2026-05-24T00:00:00Z"))
TEST = (ts("2026-05-24T00:00:00Z"), ts("2026-07-03T00:00:00Z"))


def load_log():
    ev = pd.concat([pd.read_csv(f, dtype={"principal": str, "page": str}, keep_default_na=False)
                    for f in sorted(glob.glob(f"{HERE}/data/events_26*.csv.gz"))], ignore_index=True)
    ev = ev[(ev.t >= T0) & (ev.t < TEST[1])].copy()
    ev["t"] = ev.t - T0
    codes, _ = pd.factorize(ev.principal)
    pages, _ = pd.factorize(ev.page)
    # detector schema: t, principal, op (0 write / 1 read), obj, name, size, resolves.
    # op 2 (other requests) enters VOLUME only: give it a private object so it never forms an edge.
    log = pd.DataFrame({"t": ev.t.astype(float), "principal": codes, "op": ev.op.clip(upper=1),
                        "obj": np.where(ev.op == 2, -1 - np.arange(len(ev)), pages),
                        "name": ev.page, "size": 1, "resolves": True})
    other = (ev.op == 2).to_numpy()
    log.loc[other, "op"] = 1  # a read of an object nobody wrote: no writer, no edge
    return log, int(ev.principal.nunique())


def ground_truth(rev_path):
    rows = [json.loads(x) for x in gzip.open(rev_path)]
    humans = {"[Admin1]", "[Admin2]", "[Person22]"}
    first = {}
    for r in rows:
        if r["wiki"] != "dse" or not r.get("label") or r["label"] in ("None",) or r["label"] in humans:
            continue
        t = ts(r["time"]) - T0
        first[r["label"]] = min(first.get(r["label"], t), t)
    return np.sort(np.array(list(first.values())))


def evaluate(log, n_win, seed=None, shuffled=False):
    if shuffled:
        log = shuffle_principals(log, seed)
    f = window_features(log, n_win * WIN)
    win_t = f.win * WIN
    cal_mask = (win_t >= CAL[0] - T0) & (win_t < CAL[1] - T0)
    cal = Calibration(f[cal_mask])
    return f, cal, cal.alerts(f), cal.scores(f)


def first_detection(alerts, det, first_post, gt):
    a = alerts[det].to_numpy()
    w0 = int(first_post // WIN)
    hit = np.flatnonzero(a[w0:])
    if not len(hit):
        return None, len(gt) + 1
    w = w0 + hit[0]
    return w, int((gt <= (w + 1) * WIN).sum())


def main():
    rev = sys.argv[1]
    log, n_principals = load_log()
    n_win = int(np.ceil((TEST[1] - T0) / WIN))
    gt = ground_truth(rev)
    first_post = gt[0]
    os.makedirs(OUT, exist_ok=True)
    res = {"n_requests": len(log), "n_principals": n_principals, "n_agent_labels_dse": len(gt),
           "first_agent_save_utc": datetime.fromtimestamp(first_post + T0, timezone.utc).isoformat()}

    f, cal, al, sc = evaluate(log, n_win)
    win_t = f.win * WIN + T0
    held = (win_t >= HELD[0]) & (win_t < HELD[1])
    test = (win_t >= TEST[0]) & (win_t < TEST[1])
    res["thresholds"] = {k: cal.thr[k] for k in ("GRAPH", "VOLUME")}
    res["heldout_alert_rate"] = {k: float(al.loc[held, k].mean()) for k in ("GRAPH", "VOLUME")}
    res["calib_alert_rate"] = {k: float(al.loc[(win_t >= CAL[0]) & (win_t < CAL[1]), k].mean()) for k in ("GRAPH", "VOLUME")}
    res["test_alert_rate"] = {k: float(al.loc[test, k].mean()) for k in ("GRAPH", "VOLUME")}
    for k in ("GRAPH", "VOLUME"):
        w, p = first_detection(al, k, first_post, gt)
        res[f"{k}_first_alert_utc"] = None if w is None else datetime.fromtimestamp(w * WIN + T0, timezone.utc).isoformat()
        res[f"{k}_hours_after_first_save"] = None if w is None else round((w * WIN - first_post) / 3600, 2)
        res[f"{k}_participants_at_detection"] = p
    wk = ((win_t[test] - TEST[0]) // (7 * 86400)).astype(int)
    res["weekly_test_alert_rate"] = {k: al.loc[test, k].groupby(wk.to_numpy()).mean().round(4).tolist() for k in ("GRAPH", "VOLUME")}
    res["weekly_new_agents"] = [int(((gt >= TEST[0] - T0 + i * 7 * 86400) & (gt < TEST[0] - T0 + (i + 1) * 7 * 86400)).sum()) for i in range(6)]

    # controls
    f1 = window_features(single_principal(log), n_win * WIN)
    res["single_label_GRAPH_alerts"] = int(cal.alerts(f1)["GRAPH"].sum())
    fs, cals, als, _ = evaluate(log, n_win, seed=7, shuffled=True)
    w, p = first_detection(als, "GRAPH", first_post, gt)
    res["shuffled_GRAPH_participants_at_detection"] = p
    res["shuffled_GRAPH_hours_after_first_save"] = None if w is None else round((w * WIN - first_post) / 3600, 2)
    res["shuffled_heldout_alert_rate"] = float(als.loc[held, "GRAPH"].mean())

    # verdicts
    g, v = res["GRAPH_participants_at_detection"], res["VOLUME_participants_at_detection"]
    h = res["GRAPH_hours_after_first_save"]
    res["R1"] = "PASS" if 0.005 <= res["heldout_alert_rate"]["GRAPH"] <= 0.02 else "FAIL"
    res["R2"] = "PASS" if (g < v and h is not None and h <= 24) else "FAIL"
    res["R3"] = "PASS" if (res["single_label_GRAPH_alerts"] == 0 and res["shuffled_GRAPH_participants_at_detection"] >= g) else "FAIL"

    out = pd.DataFrame({"win_start_utc": win_t, "GRAPH": sc["GRAPH"].round(3), "VOLUME": f["VOLUME"],
                        "GRAPH_alert": al["GRAPH"], "VOLUME_alert": al["VOLUME"],
                        "F1": f.F1_reciprocity.round(3), "F2": f.F2_cross_writers, "F3": f.F3_delay.round(1),
                        "agents_posted": np.searchsorted(gt, (f.win.to_numpy() + 1) * WIN, side="right")})
    out.to_csv(f"{OUT}/windows.csv.gz", index=False)
    json.dump(res, open(f"{OUT}/summary.json", "w"), indent=1)
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
