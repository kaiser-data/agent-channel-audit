"""Tables and frozen-prediction verdicts for one results directory.

Usage: python3 analyze.py results/v2
"""
import sys

import pandas as pd

pd.set_option("display.width", 220)
pd.set_option("display.max_columns", 40)
MAIN = ["GRAPH", "GRAPH+META", "VOLUME", "PREFIX"]
CELLS = [(lo, g) for lo in ("low", "medium", "high") for g in ("slow", "medium", "fast")]


def q(x):
    return f"{x.median():.0f} [{x.quantile(.25):.0f}-{x.quantile(.75):.0f}]"


def main(d):
    r = pd.read_csv(f"{d}/runs.csv")
    c = r[r.kind != "channel"]
    print("== realised per-window alert rate (clean / controls), by load ==")
    print(c.pivot_table(index="detector", columns=["kind", "variant", "load"], values="alert_rate",
                        aggfunc="mean").round(3).loc[MAIN + ["F1_reciprocity", "F2_cross_writers",
                                                             "F3_delay", "F4_size", "F5_unresolved"]])
    ch = r[r.kind == "channel"].copy()
    ch["detected"] = ch.detected.astype(bool)
    for v, dis in [("none", False), ("none", True), ("shuffled", False), ("single", False)]:
        s = ch[(ch.variant == v) & (ch.disguise == dis)]
        print(f"\n== participants at detection, median [IQR], 10 seeds: variant={v} disguise={dis} ==")
        t = s.groupby(["detector", "load", "growth"]).participants.apply(q).unstack(["load", "growth"])
        print(t[[c for c in CELLS if c in t.columns]])
        print("detection rate:", s.groupby("detector").detected.mean().round(2).to_dict())

    med = ch.groupby(["variant", "disguise", "detector", "load", "growth"]).participants.median()
    rate = ch.groupby(["variant", "disguise", "detector"]).detected.mean()
    print("\n== frozen predictions ==")
    wins = sum(med[("none", False, "GRAPH", lo, g)] < med[("none", False, "VOLUME", lo, g)] for lo, g in CELLS)
    print(f"P1 GRAPH < VOLUME median participants in {wins}/9 cells (need >=7): {'PASS' if wins >= 7 else 'FAIL'}")
    p2a = all(med[("none", False, "PREFIX", lo, g)] <= med[("none", False, "GRAPH", lo, g)] for lo, g in CELLS)
    pr_on = rate[("none", True, "PREFIX")]
    g_off, g_on = rate[("none", False, "GRAPH")], rate[("none", True, "GRAPH")]
    p2 = p2a and pr_on == 0 and g_on > 0.5 * g_off
    print(f"P2 prefix<=graph off-disguise all cells: {p2a}; prefix rate on-disguise {pr_on:.2f}; "
          f"GRAPH rate off {g_off:.2f} -> on {g_on:.2f}: {'PASS' if p2 else 'FAIL'}")
    adv = sum(med[("none", False, "VOLUME", lo, g)] - med[("none", False, "GRAPH", lo, g)] for lo, g in CELLS)
    adv_s = sum(med[("shuffled", False, "VOLUME", lo, g)] - med[("shuffled", False, "GRAPH", lo, g)] for lo, g in CELLS)
    if adv > 0:
        print(f"P3 summed GRAPH advantage over VOLUME: real {adv:.0f}, shuffled {adv_s:.0f} "
              f"(need shuffled <= 50% of real): {'PASS' if adv_s <= 0.5 * adv else 'FAIL'}")
    else:
        print(f"P3 not testable: GRAPH has no advantage over VOLUME on real labels (summed {adv:.0f})")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "results/v2")
