"""Real write->read edges for the video's graph scene, taken from one simulated run (not drawn by hand).

200 agents, medium growth, seed 1000, channel start fixed at hour 6. Two 10-minute windows:
'clean' = an hour before the channel starts, 'board' = the window 3 h after it starts.
Edges exclude declared service principals (cache system, CI), as the v3 detector does.
Writes edit/public/graph.json. Usage: python3 video/graph_data.py
"""
import json
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from aca.detect import WIN  # noqa: E402
from aca.sim import CACHE_SYSTEM, LOAD, N_CI, Config, simulate  # noqa: E402

N = LOAD["medium"]
log, truth = simulate(Config(n_agents=N, seed=1000, channel=True, p_adopt=0.05, channel_start=6 * 3600))
service = {CACHE_SYSTEM, *range(N, N + N_CI)}
log = log.sort_values("t", kind="stable")


def edges(w0):
    last, out = {}, {}
    for e in log[log.t < (w0 + 1) * WIN].itertuples():
        if e.op == 0:
            last[e.obj] = (e.principal, e.board)
        elif e.t >= w0 * WIN and e.obj in last:
            a, board = last[e.obj]
            if a != e.principal and a not in service and e.principal not in service:
                out[(int(a), int(e.principal))] = out.get((int(a), int(e.principal)), False) or bool(board)
    return [{"a": a, "b": b, "board": v} for (a, b), v in out.items()]


clean = edges(int(5 * 3600 // WIN))
board = edges(int(9 * 3600 // WIN))
recip = lambda E: sum(1 for e in E if any(f["a"] == e["b"] and f["b"] == e["a"] for f in E)) / max(len(E), 1)
nodes = [{"id": i, "x": 0.5 + 0.42 * math.cos(2 * math.pi * i / N), "y": 0.5 + 0.42 * math.sin(2 * math.pi * i / N)}
         for i in range(N)]
posted = sorted(int(p) for p, t in truth["first"].items() if t <= 10 * 3600) if isinstance(truth.get("first"), dict) else []
rows = log[(log.t >= 9 * 3600) & (log.t < 9 * 3600 + 40)].head(9)
logrows = [{"t": f"{int(r.t // 3600):02d}:{int(r.t % 3600 // 60):02d}:{int(r.t % 60):02d}",
            "who": ("cache" if r.principal == CACHE_SYSTEM else ("ci" if r.principal >= N else f"agent-{int(r.principal)}")),
            "op": "write" if r.op == 0 else "read", "name": str(r.name), "size": int(r.size)} for r in rows.itertuples()]
out = {"logrows": logrows, "n": N, "nodes": nodes, "clean": clean, "board": board, "posted_by_window_end": posted,
       "stats": {"clean_edges": len(clean), "board_edges": len(board),
                 "board_channel_edges": sum(e["board"] for e in board),
                 "clean_reciprocity": round(recip(clean), 3), "board_reciprocity": round(recip(board), 3)}}
dst = os.path.join(os.path.dirname(__file__), "edit", "public", "graph.json")
os.makedirs(os.path.dirname(dst), exist_ok=True)
json.dump(out, open(dst, "w"))
print(out["stats"], "posters:", len(posted), type(truth.get("first")))
