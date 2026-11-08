"""Voice casting on Modal: the same 2 lines in several VoxCPM2 designed voices, 2 seeds each.

  modal run modal/casting.py
Outputs: out/casting/<voice>-<line>-s<seed>.wav  (+ a runs.jsonl record)
"""
import json
import pathlib
import time

import modal

app = modal.App("video-casting")
hf_cache = modal.Volume.from_name("astrolab-hf-cache", create_if_missing=True)
image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("ffmpeg", "libsndfile1", "git")
    .pip_install("torch==2.6.0", "torchaudio==2.6.0")
    .pip_install("voxcpm", "soundfile", "huggingface_hub[hf_transfer]")
    .env({"HF_HOME": "/cache/hf", "HF_HUB_ENABLE_HF_TRANSFER": "1"})
)
ROOT = pathlib.Path(__file__).resolve().parent.parent

VOICES = {
    "f-calm": "(A calm, friendly woman in her thirties, clear and patient, explaining step by step, warm but not bubbly)",
    "f-mature": "(A grounded woman in her late forties, soft-spoken, steady and reassuring, like a trusted career coach)",
    "m-calm": "(A calm, friendly man in his thirties, clear and patient, explaining step by step, relaxed and warm)",
    "m-mature": "(A mature man in his fifties, grounded, calm authority, unhurried and kind)",
}
LINES = {
    "a": "Paste the link to your LinkedIn profile, and tick the box that says it is your own.",
    "b": "Each score is a mark out of one hundred, like a school report. Start with the lowest one.",
}
SEEDS = [1, 2]


@app.function(image=image, gpu="L40S", volumes={"/cache": hf_cache}, timeout=1800)
def cast() -> dict:
    import io

    import soundfile as sf
    import torch
    from voxcpm import VoxCPM

    m = VoxCPM.from_pretrained("openbmb/VoxCPM2", load_denoiser=False)
    sr = m.tts_model.sample_rate
    out = {}
    for v, style in VOICES.items():
        for lid, text in LINES.items():
            for s in SEEDS:
                torch.manual_seed(s)
                wav = m.generate(text=style + text, cfg_value=2.0, inference_timesteps=10)
                buf = io.BytesIO(); sf.write(buf, wav, sr, format="WAV")
                out[f"{v}-{lid}-s{s}"] = buf.getvalue()
    return out


@app.local_entrypoint()
def main():
    t0 = time.time()
    res = cast.remote()
    dest = ROOT / "out" / "casting"; dest.mkdir(parents=True, exist_ok=True)
    for k, b in res.items():
        (dest / f"{k}.wav").write_bytes(b)
    rec = {"job": "casting", "model": "voxcpm2", "gpu": "L40S", "files": len(res), "wall_s": round(time.time() - t0)}
    with (ROOT / "out" / "runs.jsonl").open("a") as fh:
        fh.write(json.dumps(rec) + "\n")
    print(rec)
