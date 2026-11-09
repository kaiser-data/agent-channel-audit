"""Figure 1: where agents post their version numbers, before and after the cache is closed at round 8.
Counts of version-bearing writes (accepted) per surface, pooled over the 4 Nebius models x 10 seeds.
Reads results/runs/*.json. Prints every plotted number. Usage: python3 paper/figure.py"""
import glob, json, os
import matplotlib; import matplotlib.pyplot as plt
matplotlib.rcParams.update({"pdf.fonttype": 42, "font.family": "serif", "font.size": 8})
HERE = os.path.dirname(__file__)
cnt = {}
for f in glob.glob(os.path.join(HERE, "..", "results", "runs", "*.json")):
    d = json.load(open(f)); v = d["versions"]
    for e in d["log"]:
        if e["op"] == "write" and e["ok"] and e["worker"] >= 0 and e["surface"] in ("cache", "dashboard") and str(v[e["worker"]]) in e["text"]:
            k = (d["condition"], "rounds 1-7" if e["round"] < 7 else "rounds 8-20", e["surface"]); cnt[k] = cnt.get(k, 0) + 1
conds = [("open", "Open"), ("close", "Close"), ("close_noalt", "Close, no dashboard")]
fig, axes = plt.subplots(1, 3, figsize=(6.9, 2.2), sharey=True)
lines = []
for ax, (c, lab) in zip(axes, conds):
    for j, ph in enumerate(("rounds 1-7", "rounds 8-20")):
        ca, da = cnt.get((c, ph, "cache"), 0), cnt.get((c, ph, "dashboard"), 0)
        ax.bar(j - 0.18, ca, 0.34, color="#7a7a7a")
        if c != "close_noalt": ax.bar(j + 0.18, da, 0.34, color="#2a6fdb")
        ax.text(j - 0.18, ca + 3, str(ca), ha="center", fontsize=7); (ax.text(j + 0.18, da + 3, str(da), ha="center", fontsize=7) if c != "close_noalt" else ax.text(j + 0.18, 4, "no\ndashboard", ha="center", fontsize=6, color="#2a6fdb"))
        lines.append(f"{c:12s} {ph:12s} cache={ca:4d} dashboard={da:4d}")
    ax.set_xticks([0, 1]); ax.set_xticklabels(["rounds 1-7", "rounds 8-20"]); ax.set_title(lab)
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
axes[0].set_ylabel("Writes carrying a version number")
axes[1].axvline(0.5, color="black", lw=0.6, ls=":"); axes[2].axvline(0.5, color="black", lw=0.6, ls=":")
axes[1].text(0.47, 120, "cache\nclosed", fontsize=7, ha="right")
fig.legend(handles=[plt.Rectangle((0, 0), 1, 1, color="#7a7a7a"), plt.Rectangle((0, 0), 1, 1, color="#2a6fdb")],
           labels=["artifact cache", "CI dashboard"], loc="lower center", ncol=2, frameon=False, bbox_to_anchor=(0.5, -0.04))
fig.tight_layout(rect=(0, 0.08, 1, 1))
fig.savefig(os.path.join(HERE, "fig1-displacement.pdf")); fig.savefig(os.path.join(HERE, "fig1-displacement.png"), dpi=200)
open(os.path.join(HERE, "fig1-numbers.txt"), "w").write("\n".join(lines) + "\n"); print("\n".join(lines))
