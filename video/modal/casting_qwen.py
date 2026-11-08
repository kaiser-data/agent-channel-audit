"""Upbeat voice casting on Modal: Qwen3-TTS VoiceDesign vs VoxCPM2, same 2 lines, 2 seeds each.

Model choice (2026-11-02): both repos are in the Astrolab stars (voice-agents report: VoxCPM 40.9k★,
Qwen3-TTS 14.1k★) and both weights are Apache-2.0 on Hugging Face (VoxCPM2 ♥1.7k / 0.97M dl30,
Qwen3-TTS VoiceDesign ♥465 / 0.53M dl30). OmniVoice (2.9M dl30) was excluded: weights CC-BY-NC.

  modal run modal/casting_qwen.py
Outputs: out/casting3/<engine>-<voice>-<line>-s<seed>.wav (+ runs.jsonl)
"""
import json
import pathlib
import time

import modal

app = modal.App("video-casting-qwen")
hf_cache = modal.Volume.from_name("astrolab-hf-cache", create_if_missing=True)
ROOT = pathlib.Path(__file__).resolve().parent.parent

vox_image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("ffmpeg", "libsndfile1", "git")
    .pip_install("torch==2.6.0", "torchaudio==2.6.0")
    .pip_install("voxcpm", "soundfile", "huggingface_hub[hf_transfer]")
    .env({"HF_HOME": "/cache/hf", "HF_HUB_ENABLE_HF_TRANSFER": "1"})
)
qwen_image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("ffmpeg", "libsndfile1", "git", "sox")
    .pip_install("qwen-tts", "soundfile", "huggingface_hub[hf_transfer]")
    .env({"HF_HOME": "/cache/hf", "HF_HUB_ENABLE_HF_TRANSFER": "1"})
)

VOICES = {
    "m-scientist": "A calm, thoughtful male science narrator in his late forties. Grounded baritone, quiet authority, "
                   "unhurried and clear, curious rather than dramatic, neutral English accent. Never loud.",
    "f-scientist": "A calm, thoughtful female science narrator in her forties. Warm, clear and precise, quietly curious, "
                   "unhurried documentary pace, neutral English accent. Never loud.",
    "m-explainer": "A friendly male researcher in his thirties explaining his work to a smart friend. Relaxed, warm, "
                   "clear diction, natural pace, gently enthusiastic, neutral English accent.",
}
LINES = {
    "a": "So we asked a simple question. Could the people running that infrastructure have seen the board form, "
         "from the access logs they already keep, without reading a single message?",
    "b": "{name}. Watch the shared spaces, not only the messages.",
}
SEEDS = [1, 2]
PRODUCT = "Agent Channel Audit"  # display spelling: Qwen reads it as written
PRODUCT_ALIAS = "Agent Channel Audit"  # VoxCPM2 spelling hint, e.g. "Lynn-fluence"


@app.function(image=qwen_image, gpu="L40S", volumes={"/cache": hf_cache}, timeout=2400)
def cast_qwen() -> dict:
    import io

    import soundfile as sf
    import torch
    from qwen_tts import Qwen3TTSModel

    m = Qwen3TTSModel.from_pretrained("Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign", device_map="cuda:0",
                                      dtype=torch.bfloat16, attn_implementation="sdpa")
    if not hasattr(m, "generate_voice_design"):
        raise RuntimeError("no generate_voice_design; methods: " + ", ".join(x for x in dir(m) if x.startswith("generate")))
    out = {}
    for v, instruct in VOICES.items():
        for lid, text in LINES.items():
            for s in SEEDS:
                torch.manual_seed(s)
                wavs, sr = m.generate_voice_design(text=text.format(name=PRODUCT), language="English", instruct=instruct)
                buf = io.BytesIO(); sf.write(buf, wavs[0], sr, format="WAV")
                out[f"qwen-{v}-{lid}-s{s}"] = buf.getvalue()
    hf_cache.commit()
    return out


@app.function(image=vox_image, gpu="L40S", volumes={"/cache": hf_cache}, timeout=1800)
def cast_vox() -> dict:
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
                wav = m.generate(text=f"({style}){text.format(name=PRODUCT_ALIAS)}", cfg_value=2.0, inference_timesteps=10)
                buf = io.BytesIO(); sf.write(buf, wav, sr, format="WAV")
                out[f"vox-{v}-{lid}-s{s}"] = buf.getvalue()
    return out


@app.local_entrypoint()
def main():
    t0 = time.time()
    hq, hv = cast_qwen.spawn(), cast_vox.spawn()
    dest = ROOT / "out" / "casting"; dest.mkdir(parents=True, exist_ok=True)
    n = 0
    for name, h in (("qwen3-tts-voicedesign", hq), ("voxcpm2", hv)):
        try:
            res = h.get()
        except Exception as e:  # keep the other engine's takes
            print("FAILED", name, repr(e)); continue
        for k, b in res.items():
            (dest / f"{k}.wav").write_bytes(b); n += 1
        with (ROOT / "out" / "runs.jsonl").open("a") as fh:
            fh.write(json.dumps({"job": "casting-v2", "model": name, "gpu": "L40S", "files": len(res),
                                 "wall_s": round(time.time() - t0), "ts": time.time()}) + "\n")
    print({"files": n, "wall_s": round(time.time() - t0)})
