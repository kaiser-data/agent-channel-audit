"""Figure 1: participants at detection by load x growth, disguise off / on.

Reads results/v3/runs.csv (frozen v3 grid). Prints every plotted number.
Usage: python3 paper/figures.py
"""
import os

import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import FixedLocator, NullLocator

matplotlib.rcParams.update({"pdf.fonttype": 42, "font.family": "serif", "font.size": 8})
HERE = os.path.dirname(__file__)
RUNS = os.path.join(HERE, "..", "results", "v3", "runs.csv")
LOADS = [("low", 50), ("medium", 200), ("high", 800)]
GROWTHS = ["slow", "medium", "fast"]
DETS = [("GRAPH", "Graph detector (ours)", "#2a6fdb", "o"),
        ("VOLUME", "Volume baseline", "#7a7a7a", "s"),
        ("PREFIX", "Prefix rule (“zz”)", "#d9822b", "^")]


def main():
    r = pd.read_csv(RUNS)
    ch = r[(r.kind == "channel") & (r.variant == "none")]
    fig, axes = plt.subplots(1, 2, figsize=(6.9, 3.0), sharey=True)
    for ax, dis in zip(axes, (False, True)):
        s = ch[ch.disguise == dis]
        xs, labels = [], []
        for li, (lo, n) in enumerate(LOADS):
            for gi, g in enumerate(GROWTHS):
                xs.append(li * 3.6 + gi)
                labels.append(g[0].upper())
        # eventual channel size (median) as grey bars: the ceiling a detector can be judged against
        fin = [s[(s.load == lo) & (s.growth == g) & (s.detector == "GRAPH")].final_participants.median()
               for lo, _ in LOADS for g in GROWTHS]
        ax.bar(xs, fin, width=0.8, color="#e6e6e6", zorder=0, label="Channel size at 24 h")
        for di, (det, lab, col, mk) in enumerate(DETS):
            med, lo_q, hi_q = [], [], []
            for lo, _ in LOADS:
                for g in GROWTHS:
                    p = s[(s.load == lo) & (s.growth == g) & (s.detector == det)].participants
                    med.append(p.median())
                    lo_q.append(p.quantile(.25))
                    hi_q.append(p.quantile(.75))
                    print(f"disguise={dis} {det:7s} load={lo:6s} growth={g:6s} median={p.median():.0f} "
                          f"IQR=[{p.quantile(.25):.0f},{p.quantile(.75):.0f}] n={len(p)} "
                          f"detected={s[(s.load == lo) & (s.growth == g) & (s.detector == det)].detected.astype(bool).sum()}")
            off = (di - 1) * 0.22
            ax.errorbar([x + off for x in xs], med,
                        yerr=[[m - a for m, a in zip(med, lo_q)], [b - m for m, b in zip(med, hi_q)]],
                        fmt=mk, color=col, ms=4, lw=0.8, capsize=0, label=lab, zorder=3)
        ax.set_yscale("log")
        ax.yaxis.set_major_locator(FixedLocator([1, 3, 10, 30, 100, 300]))
        ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:g}"))
        ax.yaxis.set_minor_locator(NullLocator())
        ax.set_ylim(0.7, 400)
        ax.set_xticks(xs, labels, fontsize=6.5)
        for li, (lo, n) in enumerate(LOADS):
            ax.text(li * 3.6 + 1, -0.14, f"{n} agents", ha="center", va="top",
                    transform=ax.get_xaxis_transform(), fontsize=7)
        ax.set_title("Undisguised channel" if not dis else "Disguised channel", fontsize=8)
        ax.spines[["top", "right"]].set_visible(False)
    axes[0].set_ylabel("Agents posting when first detected\n(median, IQR; 10 seeds; lower is earlier)")
    h, lab = axes[0].get_legend_handles_labels()
    fig.legend(h, lab, fontsize=7, frameon=False, loc="lower center", ncol=4)
    fig.text(0.99, 0.13, "growth: S slow, M medium, F fast", ha="right", fontsize=6.5, color="#555")
    fig.tight_layout(w_pad=1.0, rect=(0, 0.1, 1, 1))
    for ext in ("pdf", "png"):
        fig.savefig(os.path.join(HERE, f"fig1-participants-at-detection.{ext}"), dpi=200)


if __name__ == "__main__":
    main()
