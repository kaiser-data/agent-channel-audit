"""Figure 2: the real swarm on the dse wiki. Daily share of 10-minute windows that alert (GRAPH vs
VOLUME, frozen D7 thresholds) and cumulative agents that had saved a page.

Reads results/real/windows.csv.gz (from real/analyze_wiki.py). Prints every plotted number.
Usage: python3 paper/figure2_real.py
"""
import os

import matplotlib
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

matplotlib.rcParams.update({"pdf.fonttype": 42, "font.family": "serif", "font.size": 8})
HERE = os.path.dirname(__file__)
W = os.path.join(HERE, "..", "results", "real", "windows.csv.gz")


def main():
    w = pd.read_csv(W)
    w["day"] = pd.to_datetime(w.win_start_utc, unit="s").dt.floor("D")
    d = w[w.day >= "2026-05-10"].groupby("day").agg(GRAPH=("GRAPH_alert", "mean"), VOLUME=("VOLUME_alert", "mean"),
                                                    agents=("agents_posted", "max"))
    fig, ax = plt.subplots(figsize=(6.9, 2.3))
    ax.step(d.index, d.GRAPH * 100, where="post", color="#2a6fdb", lw=1.4)
    ax.step(d.index, d.VOLUME * 100, where="post", color="#7a7a7a", lw=1.4)
    ax.set_ylabel("Windows alerting per day (%)")
    ax.set_ylim(0, 105)
    ax.axvline(pd.Timestamp("2026-05-24"), color="black", lw=0.6, ls=":")
    ax.text(pd.Timestamp("2026-05-24 06:00"), 98, "first agent save\n24 May 06:02 UTC", va="top", fontsize=7)
    ax.text(pd.Timestamp("2026-05-09"), 16, "clean period:\nno saves, 0 graph alerts", fontsize=7, color="#2a6fdb")
    ax2 = ax.twinx()
    ax2.plot(d.index, d.agents, color="#d9822b", lw=1.0, ls="--")
    ax2.set_ylabel("Agents that had saved (dashed)", color="#d9822b")
    ax2.tick_params(axis="y", colors="#d9822b")
    ax.text(d.index[-1], d.GRAPH.iloc[-1] * 100 - 8, "Graph detector", color="#2a6fdb", ha="right", fontsize=7)
    ax.text(d.index[-1], d.VOLUME.iloc[-1] * 100 + 3, "Volume", color="#7a7a7a", ha="right", fontsize=7)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    for a in (ax, ax2):
        a.spines["top"].set_visible(False)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "fig2-real-wiki.pdf"))
    fig.savefig(os.path.join(HERE, "fig2-real-wiki.png"), dpi=200)
    with open(os.path.join(HERE, "fig2-numbers.txt"), "w") as f:
        f.write(d.round(4).to_string())
    print(d.round(3).to_string())


if __name__ == "__main__":
    main()
