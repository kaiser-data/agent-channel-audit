# Lab log

## Fri 6 Nov 2026 (evening, CET)

- 20:39 PROTOCOL.md frozen (hash in FREEZE.txt).
- Simulator (`aca/sim.py`) and detectors (`aca/detect.py`) built. Clean traffic carries the realistic confounds: requester-attributed cache fills, team artifact sharing (reciprocity), CI bots (short delays), diurnal load, rebuild storms. Channel tuned to the incident scale (fast: 0→~59 posters in 2 h).
- **v1 frozen grid** (`results/frozen`, 480 runs): the controls exposed three design flaws: pooled-load calibration (per-load FPR 0–2.2%, medium load never alerts), service-account fills tripping F3 in the read-only control (GRAPH alerts in 30–79% of windows), and a shuffled control without its own calibration. P1 FAIL (4/9), P2 PASS, P3 FAIL.
- 20:44 v2 deviations D1–D4 declared in PROTOCOL.md before running.
- **v2** (`results/v2`, 510 runs): per-load GRAPH FPR 0.6–0.8%; read-only and single-label controls give 0 alerts. P1 PASS 9/9, P2 PASS, P3 PASS.
- **v2 on fresh seeds** (`results/v2_fresh`, seed offset 50000, declared before running): P1 PASS 8/9, P2 PASS, P3 PASS. Held-out GRAPH FPR 0.9–1.5% (thresholds come from only 10 calibration runs per load).

### Caveats to carry into the paper
- Low load: the channel saturates at ~17 posters, so every detector looks similar; the advantage is at medium/high load.
- High load + fast growth is the weakest and noisiest cell (GRAPH median 28 vs 84 across the two seed sets; IQR spans 10–238).
- P2 as worded (detection *rate*) is insensitive: disguise barely changes GRAPH's rate but at high load it raises participants-at-detection a lot. Report participants, not just rate.
- F4 (size) collapses under disguise (detection rate 0.16), as designed; F5 (unresolved names) does not, because the disguised names still don't resolve. A stronger disguise class (names that resolve, e.g. squatted packages) is untested.
- v2 fixes were chosen after seeing v1. Mitigation: they were chosen from control failures, not from P1, and the fresh-seed run replicates.
- Main limit unchanged: clean traffic is synthetic.

### Next (Sat)
1. More calibration runs per load (10 → 30) to tighten the realised FPR; report the threshold's seed spread.
2. Figure 1: participants-at-detection, GRAPH vs VOLUME vs PREFIX, per load × growth, disguise off/on.
3. Agent sandbox (P4) via OpenRouter; go/no-go at 12:00.
4. collusion.wiki history check; Shared Resource Matrix filled from sources.

## Sat 7 Nov 2026

- 10:42 D5: calibration 10→30 runs per load. v3 and v3_fresh: P1 9/9 + 9/9, P2 PASS, P3 PASS; held-out GRAPH FPR 0.9–1.3%.
- Figure 1 (`paper/figures.py` → `paper/fig1-participants-at-detection.pdf`, numbers in `paper/fig1-numbers.txt`).
- Sandbox (`sandbox/run_sandbox.py`): 8 workers, 15 rounds, artifact cache never described as a channel. In the pressure condition Haiku workers invented a `comp-N` registry on their own (write once, poll many). Independent: 8/8 correct, no artifact writes. Read-only: no writes.
- OpenRouter credits ran out mid-grid → 28 runs invalid, quarantined in `results/sandbox_invalid_402/`. OpenAI key has no credits either. Valid: Haiku 15 runs (5 seeds × 3 conditions) + Qwen pressure seeds 0–1.
- **P4 FAIL**: 0/5 Haiku pressure channels detected at frozen thresholds; GRAPH max stays ~3.3 below threshold, same as clean. Consistent with the simulated floor: GRAPH needs ~8 posters at low load; sandbox channels have ~4.
- collusion.wiki: editor names redacted, no read log → arm dropped.
- Go/no-go (12:00): sandbox stays, as an honest negative that matches the simulated detection floor.

### Open decisions
- Second model family needs credits (OpenRouter or OpenAI).
- Exploratory E1 (must be declared before running): a per-pair detector (reciprocal write→read pairs on unresolved objects) that might catch small registries; needs its own FPR on simulated clean traffic.

## Sun 8 Nov 2026

- ~02:00 Paper draft v1: `paper/main.tex` → `paper/main.pdf` (6 pages, tectonic). Every number taken from `analyze.py` output on results/v3 and v3_fresh, `paper/fig1-numbers.txt`, and `results/sandbox/scores.csv`.
- E1 (per-pair detector for small registries) skipped: not declared, no time to measure its own FPR. Listed as future work in Limitations.
- Open before submitting: public repo URL (placeholder `[REPOSITORY URL]`), move to the official Apart template, check Lampson/Kemmerer/NCSC-TG-030 bibliographic details against the sources.
- Sprint page re-checked (Sun): deadline Nov 8 23:59 AoE (= Mon 9 Nov 12:59 CET); required: PDF on official template (Google Doc), ≤8 pages excl. refs/appendices, abstract 150–250 words, author + affiliation, Limitations & Dual-Use appendix; repo and video optional.
- Related work added: Lütje et al. arXiv:2609.12748 (closest; post-hoc wiki request-log forensics, no FPR), Metere arXiv:2605.20734 (egress content monitor), Schroeder de Witt et al. arXiv:2505.02077 (provenance-graph detection gap), ARMO blog. Intro now names how we differ from sprint examples "Catch the swarm at the gateway" and "Forensics on a real swarm". PDF 7 pages.
- 02:17 D7 declared (real-data arm on dse-wiki request log; hash in FREEZE.txt). Ingest bug (key/value offset → all IPs/names empty) gave one invalid run with 2 principals; discarded, fixed, rerun.
- Real wiki (results/real/summary.json): 4.33M requests, 275,708 principals, 3,010 agent names. No saves at all 1 Mar–23 May → GRAPH threshold 0, held-out FPR 0% (R1 FAIL). GRAPH alerts in the window of the first agent save (24 May 06:00 UTC), VOLUME 4.3 h later, both at 2 participants (R2 FAIL on tie). Single-label 0 alerts, shuffled not earlier (R3 PASS). Weekly alerting GRAPH 63/85/92/99/100/100%, VOLUME 12/3/9/67/49/21%. Fig 2 = paper/fig2-real-wiki.pdf. Paper now 8 pp incl. refs+appendices.
- ~03:20 Explainer video rendered (video/out/agent-channel-audit-16x9.mp4, 3:02). Citations verified via Crossref (Kemmerer DOI corrected). v3 grid re-run byte-identical (1:49). Public repo: https://github.com/kaiser-data/agent-channel-audit (real/data excluded).
