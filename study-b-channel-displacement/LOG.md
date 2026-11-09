# Lab log

## Sun 8 Nov 2026
- ~03:30 Protocol drafted (not yet frozen). Sandbox + analysis written; mock dry run passes all code paths
  (results/mock, never scored). Waiting for OpenRouter credit (balance $0 at 03:22) for the pilot (seed 900).
- 03:39 Protocol frozen after pilot (Haiku 6/8 correct in OPEN at 20 rounds; others 0/8). OpenRouter credit ran out
  mid-grid: 2 valid Haiku runs, 134 runs failed with HTTP 402 and were discarded.
- 03:45 D1 declared: Nebius panel (DeepSeek-V4.1-Flash, Gemma-3-27B, Qwen3-235B-Instruct, MiniMax-M3.1-Flash), chosen
  by a format-only check. 160/160 runs valid.
- Results (analyze.py): H1 PASS 12/12 [0.76,1.00], median 1 round to relocate; H2 PASS 0.191 vs 0.000, sign +10/-0/=30;
  H3 PASS ratio 1.27. Post-closure version writes: OPEN 80 cache / 80 dashboard; CLOSE 0 / 174. Clean control:
  31/40 INDEPENDENT runs put a version in a status line (content is not diagnostic). Only DeepSeek and MiniMax ever
  coordinated; Qwen and Gemma never did.
