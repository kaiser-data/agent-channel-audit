"""Qwen3-TTS "design then clone": one designed reference take -> every script line, N seeds each.

  modal run modal/tts_qwen.py --voices qwen-f-upbeat,qwen-m-upbeat --script script-promo-v2.json --takes 3
Reference = out/casting3/<voice>-a-s1.wav (VoiceDesign take) with its exact words.
Outputs: out/tts/<voice>-takes/<line-id>-t<k>.wav ; pick with modal/pick_qwen.py.
"""
import json
import pathlib
import time

import modal

app = modal.App("video-tts-qwen")
hf_cache = modal.Volume.from_name("astrolab-hf-cache", create_if_missing=True)
ROOT = pathlib.Path(__file__).resolve().parent.parent
image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("ffmpeg", "libsndfile1", "git", "sox")
    .pip_install("qwen-tts", "soundfile", "huggingface_hub[hf_transfer]")
    .env({"HF_HOME": "/cache/hf", "HF_HUB_ENABLE_HF_TRANSFER": "1"})
)
REF_TEXT = ("So we asked a simple question. Could the people running that infrastructure have seen the board form, "
            "from the access logs they already keep, without reading a single message?")


@app.function(image=image, gpu="L40S", volumes={"/cache": hf_cache}, timeout=2400)
def clone(ref_wav: bytes, lines: list[dict], takes: int) -> dict:
    import io
    import tempfile

    import soundfile as sf
    import torch
    from qwen_tts import Qwen3TTSModel

    m = Qwen3TTSModel.from_pretrained("Qwen/Qwen3-TTS-12Hz-1.7B-Base", device_map="cuda:0",
                                      dtype=torch.bfloat16, attn_implementation="sdpa")
    with tempfile.NamedTemporaryFile(suffix=".wav") as fh:
        fh.write(ref_wav); fh.flush()
        prompt = m.create_voice_clone_prompt(ref_audio=fh.name, ref_text=REF_TEXT, x_vector_only_mode=False)
    out = {}
    for ln in lines:
        for k in range(takes):
            torch.manual_seed(100 + k)
            wavs, sr = m.generate_voice_clone(text=ln["text"], language="English", voice_clone_prompt=prompt)
            buf = io.BytesIO(); sf.write(buf, wavs[0], sr, format="WAV")
            out[f"{ln['id']}-t{k}"] = buf.getvalue()
    hf_cache.commit()
    return out


@app.local_entrypoint()
def main(voices: str = "qwen-f-upbeat", script: str = "script.json", takes: int = 3):
    t0 = time.time()
    # Qwen reads the display spelling correctly (casting: name heard in 12/12 takes), so use "text", not the alias
    lines = [{"id": l["id"], "text": l["text"]} for l in json.loads((ROOT / script).read_text())["lines"]]
    handles = {v: clone.spawn((ROOT / "out" / "casting" / f"{v}-a-s1.wav").read_bytes(), lines, takes)
               for v in voices.split(",")}
    for v, h in handles.items():
        res = h.get()
        dest = ROOT / "out" / "tts" / f"{v}-takes"; dest.mkdir(parents=True, exist_ok=True)
        for k, b in res.items():
            (dest / f"{k}.wav").write_bytes(b)
        with (ROOT / "out" / "runs.jsonl").open("a") as fh:
            fh.write(json.dumps({"job": "tts-clone", "model": "qwen3-tts-1.7b-base", "voice": v, "gpu": "L40S",
                                 "lines": len(lines), "takes": takes, "seconds": round(time.time() - t0), "ts": time.time()}) + "\n")
        print(v, len(res), "files")
