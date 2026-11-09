"""Extract the on-screen log for the explainer from one real run and the figure numbers from the paper.

  python3 video/log_excerpt.py
Writes edit/public/data.json: the version-bearing writes of DeepSeek-V4.1-Flash, CLOSE, seed 7 (all 8 workers
correct), the operator's closure, and the per-surface counts printed in paper/fig1-numbers.txt.
"""
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent
REPO = ROOT.parent
RUN = REPO / "results" / "runs" / "nebius-deepseek-ai_DeepSeek-V4.1-Flash__close__7.json"

d = json.loads(RUN.read_text())
rows = []
for e in d["log"]:
    if e["op"] == "close":
        rows.append({"r": e["round"], "w": None, "s": "operator", "txt": "cache closed: worker writes rejected", "ok": True})
    elif e["op"] == "write":
        txt = f'{e["name"]} = {e["text"]}' if e["surface"] == "cache" else e["text"]
        rows.append({"r": e["round"], "w": e["worker"], "s": e["surface"], "txt": txt, "ok": e["ok"]})

counts = {}
for line in (REPO / "paper" / "fig1-numbers.txt").read_text().splitlines():
    m = re.match(r"(\w+)\s+rounds (\S+)\s+cache=\s*(\d+) dashboard=\s*(\d+)", line)
    if m:
        counts.setdefault(m.group(1), {})[m.group(2)] = {"cache": int(m.group(3)), "dashboard": int(m.group(4))}

out = {"run": RUN.name, "versions": d["versions"], "sum": sum(d["versions"]), "answers": d["answers"],
       "correct": sum(d["correct"]), "rows": rows, "counts": counts}
(ROOT / "edit" / "public" / "data.json").write_text(json.dumps(out, indent=1))
print(len(rows), "rows; close at round", [r["r"] for r in rows if r["s"] == "operator"], "; counts", counts)
