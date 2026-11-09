# Explainer video

`out/channel-displacement-16x9.mp4` (submission) and `out/channel-displacement-4x5.mp4` (feed crop).

- `script.json`: the narration, one line per scene. Every claim is checked against the paper and `analyze.py`.
- `log_excerpt.py`: writes `edit/public/data.json`: the on-screen log of one real run
  (DeepSeek-V4.1-Flash, `close`, seed 7, all eight workers correct) and the bar heights from `paper/fig1-numbers.txt`.
- `prep_explainer.py`: stages the narration takes and writes `edit/src/manifest.json`.
- `edit/src/Promo.tsx`: the Remotion edit (16:9 and 4:5).
- `modal/`: voice cloning (Qwen3-TTS, open weights) and the render, run on Modal.

Narration is an AI-generated voice (Qwen3-TTS), the same designed voice as the companion
[Agent Channel Audit](https://github.com/kaiser-data/agent-channel-audit) explainer, whose pipeline this reuses
(adapted from the author's pre-existing video template kit). All numbers and logs come from the study's own data;
there is no AI-generated imagery.

Rebuild (from `video/`): `python3 log_excerpt.py && modal run modal/tts_qwen.py --voices qwen-m-scientist --takes 3 &&
python3 modal/pick_qwen.py qwen-m-scientist script.json "dashboard" && python3 prep_explainer.py --voice qwen-m-scientist &&
modal run modal/render.py`. `edit/node_modules` is installed with `cd edit && npm ci`.
