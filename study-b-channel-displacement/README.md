<div align="center">

# 🚧 Channel Displacement

### Close the board, agents move

**When an operator closes the channel LLM agents improvised on shared infrastructure, does coordination stop, or move?**
**A pre-registered sandbox borrowing criminology's displacement test.**

Apart Research · Swarm Alignment Hackathon · 6–8 Nov 2026 · companion to [Agent Channel Audit](https://github.com/kaiser-data/agent-channel-audit)

[Paper (PDF)](paper/main.pdf) · [Explainer video (2:31)](video/out/channel-displacement-16x9.mp4) · [Frozen protocol](PROTOCOL.md) · [Lab log](LOG.md)

</div>

> **Reproduce every number in the paper from the stored runs (seconds, no API key):**
> ```bash
> pip install pandas matplotlib
> python3 analyze.py results/runs      # tables, H1-H3 verdicts
> python3 paper/figure.py             # Figure 1
> ```

## Result

| Prediction (frozen) | Result |
|---|---|
| **H1** closing the cache moves coordination to the dashboard within 5 rounds | **12/12** runs with a cache channel (95% CI 0.76–1.00), median 1 round |
| **H2** an alternative surface keeps coordination alive | correct sums 19.1% with a dashboard vs **0%** without; paired 10–0 (p ≈ 0.002) |
| **H3** closure costs little when an alternative exists | 0.191 after closure vs 0.150 open (ratio 1.27) |

Version numbers posted after round 8: open cache 80 cache / 80 dashboard; closed cache **0 / 174**.
Without a dashboard, sharing stops and agents keep retrying the closed cache.

**Limits, stated in the paper:** only 2 of 4 models (DeepSeek, MiniMax) ever coordinated, so H1 rests on 12 runs;
the panel changed from the pre-registered OpenRouter models to Nebius models when credit ran out (deviation D1,
declared before any Nebius run); in a task that needs no coordination, 31/40 runs also post version numbers, so
content alone is not diagnostic.

## Sandbox

8 build workers, 20 rounds, each knows one component version and must submit the sum of all 8. Surfaces: a shared
artifact cache (`get` / `put` / `list`) and a CI dashboard (`status` / `dashboard`). No prompt calls either a channel.

| Condition | Cache | Dashboard |
|---|---|---|
| Open | writable | yes |
| Close | read-only from round 8, worker artifacts deleted | yes |
| Close, no alternative | as Close | no |
| Independent (control) | writable | yes, but the task needs no coordination |

Models (Nebius Token Factory): DeepSeek-V4.1-Flash, Gemma-3-27B, Qwen3-235B-A22B-Instruct, MiniMax-M3.1-Flash;
seeds 0–9 each, 160 runs.

## Repo layout

```
PROTOCOL.md, FREEZE.txt     design, predictions, deviation D1, hashes with UTC times
sandbox/run_displacement.py the sandbox; --mock runs scripted agents with no API
analyze.py                  measures and verdicts; writes results/runs/per_run.csv
results/runs/               the 160 scored runs (full transcripts and logs)
results/pilot/              pilot, one run per model, not scored
results/runs_openrouter_partial/  the 2 valid OpenRouter runs (Haiku), reported separately
paper/                      main.tex, figure.py, fig1-numbers.txt
video/                      explainer (Remotion edit, AI narration, real run log); see video/README.md
```

## Re-run the experiment

```bash
printf '%s' "$NEBIUS_KEY" > ~/.config/nebius-tf-key     # keys are read from ~/.config, never from the repo
python3 sandbox/run_displacement.py --models nebius:deepseek-ai/DeepSeek-V4.1-Flash,nebius:google/gemma-3-27b-it,nebius:Qwen/Qwen3-235B-A22B-Instruct-2507,nebius:MiniMaxAI/MiniMax-M3.1-Flash --seeds 0-9 --out results/rerun
python3 analyze.py results/rerun
```

---

Built solo by Martin Kaiser during the hackathon weekend (8 Nov 2026), with Claude Code as a coding assistant. The
sandbox extends the one in Agent Channel Audit, written the same weekend.
