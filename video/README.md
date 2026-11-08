# Explainer video

`out/agent-channel-audit-16x9.mp4` (3:02, submission) and `out/agent-channel-audit-4x5.mp4` (feed crop).

- `script.json`: the narration, one line per scene. Every claim is checked against `results/` and the paper.
- `graph_data.py`: pulls the write→read edges shown in the graph scene from one real simulated run (seed 1000).
- `prep_explainer.py`: stages the narration takes and writes `edit/src/manifest.json`.
- `edit/src/Promo.tsx`: the Remotion edit (16:9 and 4:5).
- `modal/`: voice casting and cloning (Qwen3-TTS, open weights) and the render, run on Modal.

Narration is an AI-generated voice (Qwen3-TTS). All figures, numbers and graphs come from the study's own data;
there is no AI-generated imagery. The tooling in `modal/`, `prep.py` and `music_cue.py` was adapted from the
author's pre-existing video template kit.

Rebuild: `python3 graph_data.py && python3 prep_explainer.py --voice qwen-m-scientist && modal run modal/render.py`
(voice takes are not in the repo; regenerate with `modal run modal/casting_qwen.py` and `modal run modal/tts_qwen.py --voices qwen-m-scientist`).
