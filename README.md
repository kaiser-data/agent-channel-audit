<div align="center">

# 🕸️ Agent Channel Audit

### Finding agent message boards in access logs, without reading them

**A content-free detector for unsanctioned agent-to-agent channels in shared infrastructure.**
**It builds a write→read graph (agent A writes, agent B reads it) from the access log an operator already keeps.**

Apart Research · Swarm Alignment Hackathon · 6–8 Nov 2026 · Track 4 (Multi-Agent Oversight and Control)

[Paper (PDF)](paper/main.pdf) · [Explainer video (3:02)](video/out/agent-channel-audit-16x9.mp4) · [Frozen protocol](PROTOCOL.md) · [Lab log](LOG.md)

</div>

> **Reproduce the main result in about 2 minutes, on a laptop, no API keys:**
> ```bash
> pip install -r requirements.txt
> python3 run_grid.py --v2 --out results/v3_check   # 810 simulated runs, ~2 min on a laptop
> python3 analyze.py results/v3_check               # Tables 1-3 and verdicts P1-P3
> ```
> `results/v3_check/runs.csv` comes out byte-identical to the stored `results/v3/runs.csv` (checked 8 Nov 2026).

## The idea

In July 2026, agents meant to be isolated turned a shared package cache into a message board: 0 to 53 posting
agents in about three hours (METR/Redwood incident report, Fig. 10, p. 32). Nobody noticed it forming.
Computer security has studied this since Lampson (1973): any resource one party can change and another can
observe is a possible **covert channel**. We turn that idea into a runtime alarm with a known false-alarm rate.

| Signal | What it needs | Weakness |
|---|---|---|
| Traffic volume (what surfaced the incident) | request counts | a board of 15–60 agents is lost in normal load |
| Filename rule (the incident's `zz` prefix) | object names | blind as soon as names look normal |
| **Write→read graph (this work)** | who wrote an object, who else read it, when | needs per-agent credentials; misses boards of < ~5–8 agents |

## Results

| Test | Result |
|---|---|
| Simulated cache, 180 channels, 1% false-alarm rate | graph fires with fewer participants than volume in **9/9** conditions; same on fresh seeds (9/9) |
| Example: 200 agents, medium growth | graph at **15** posters, volume at **62** |
| Detected within 24 h | graph **96–100%**, volume 61–73% |
| Disguised channel | filename rule 100% → **0%**; graph **98%** (later at 800 agents) |
| Controls (read-only, single label, shuffled labels) | 0 / 0 graph alerts; shuffling removes the advantage (442 → −26) |
| Real swarm: public request log of the wiki 3,010 agents used as a board | graph alerts in the **first 10 minutes**, volume 4.3 h later |
| LLM agents in a sandbox (Claude Haiku 5.5) | they invented a `comp-N` registry unprompted; **0/5 detected** (4–6 writers) |

**Failed predictions are reported as results:** the protocol as first frozen (v1) failed P1 and P3; the real wiki
failed R1 (no saves before the agents, so calibration could not be tested) and R2 (a tie on participants).
See the paper, Table 3.

## How it works

1. **Log** one row per operation: time, principal, write or read, object, name, size. No content.
2. **Graph** per 10-minute window: an edge A→B when B reads an object last written by A ≠ B.
3. **Score** = z(reciprocity) + z(distinct writers read by others) − z(write-to-first-foreign-read delay).
4. **Threshold** = 99th percentile of the score on clean calibration windows, per deployment. Never refit.
5. **Controls** with known answers decide whether a result counts: held-out clean, read-only, single label, shuffled labels.

## Repo layout

```
aca/sim.py            simulated shared cache: clean traffic with realistic confounds + growing channel
aca/detect.py         features F1-F5, GRAPH score, calibration, controls (shuffle, single label)
run_grid.py           the frozen experiment grid (v1 as frozen; --v2 applies deviations D1-D5)
analyze.py            tables and prediction verdicts for one results folder
PROTOCOL.md           question, design, predictions and every deviation; hashes in FREEZE.txt
results/              frozen (v1), v2, v2_fresh, v3, v3_fresh, sandbox, real
sandbox/              LLM-agent sandbox (run_sandbox.py) and its scorer (score_sandbox.py)
real/                 real-data arm: ingest_wiki.py (pseudonymises while streaming), analyze_wiki.py
paper/                main.tex, figures.py (Fig. 1), figure2_real.py (Fig. 2), every plotted number in *-numbers.txt
video/                explainer video (Remotion); graph_data.py pulls the animated edges from a real simulated run
```

## Reproduce everything

| What | Command | Time |
|---|---|---|
| Main grid (v3) + fresh seeds | `python3 run_grid.py --v2 --out results/v3` · `python3 run_grid.py --v2 --seed-offset 50000 --out results/v3_fresh` | ~2 min each |
| Tables, verdicts P1-P3 | `python3 analyze.py results/v3` | seconds |
| Figure 1 | `python3 paper/figures.py` | seconds |
| Real wiki (R1-R3) | `python3 real/ingest_wiki.py 2603 2604 2605 2606 2607` then `python3 real/analyze_wiki.py <collusion.wiki revisions.jsonl.gz>` | ~5 min, streams ~1.1 GB |
| Figure 2 | `python3 paper/figure2_real.py` | seconds |
| Sandbox | `OPENROUTER_API_KEY=... python3 sandbox/run_sandbox.py --models anthropic/claude-haiku-5.5 --seeds 0-4` then `python3 sandbox/score_sandbox.py` | minutes, < $1 (the 15 Haiku runs cost $0.24) |

`results/frozen` and `results/v2*` were produced with 10 calibration runs per load; the current code uses 30
(deviation D5), so it reproduces v3, not v1/v2. Those outputs are kept unchanged.

## Data and privacy

- The wiki request log is public at `wikiservice.at/dse/` and contains visitors' IP addresses. `real/ingest_wiki.py`
  replaces each IP with a salted HMAC while streaming; raw lines never touch disk. The derived event tables
  (`real/data/`) are **not** in this repo. Only aggregates are published (`results/real/`).
- Ground truth for the real arm is collusion.wiki's public release (`revisions.jsonl.gz`).
- Sandbox transcripts in `results/sandbox/` are a toy checksum task. No real systems were touched.

## Limits

Calibration on a busy shared resource is measured only in simulation · boards of fewer than ~5–8 agents are missed ·
the disguise tested still uses names that do not resolve upstream · per-agent credentials are a precondition ·
one model family produced sandbox channels (API credits ran out for the second).

---

Built solo by Martin Kaiser during the hackathon weekend, with Claude Code as a coding assistant. All research code (aca/, run_grid.py, analyze.py,
sandbox/, real/, paper/) was written 6–8 Nov 2026. Pre-existing: the video tooling in video/ (prep, Modal
render and TTS scripts) was copied from the author's own template kit and adapted. Never commit API keys; the sandbox reads them from environment variables.
