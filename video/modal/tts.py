"""Narration A/B on Modal: VoxCPM2 vs Chatterbox, one wav per script line.

  modal run modal/tts.py --dry-run                 # wave 0: CPU, image + imports only
  modal run modal/tts.py --models voxcpm,chatterbox # wave 1: render every line with both
Outputs land in out/tts/<model>/<line-id>.wav; existing files are skipped.
"""
import json
import pathlib
import time

import modal

app = modal.App("video-tts")
hf_cache = modal.Volume.from_name("astrolab-hf-cache", create_if_missing=True)

image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("ffmpeg", "libsndfile1", "git")
    .pip_install("torch==2.6.0", "torchaudio==2.6.0")
    .pip_install("voxcpm", "chatterbox-tts", "soundfile", "huggingface_hub[hf_transfer]")
    .env({"HF_HOME": "/cache/hf", "HF_HUB_ENABLE_HF_TRANSFER": "1"})
)

ROOT = pathlib.Path(__file__).resolve().parent.parent


@app.function(image=image, volumes={"/cache": hf_cache}, timeout=600)
def check_imports() -> str:
    import chatterbox.tts  # noqa: F401
    import inspect

    import voxcpm  # noqa: F401
    from voxcpm import VoxCPM
    return "imports ok; VoxCPM._generate" + str(inspect.signature(VoxCPM._generate))


@app.function(image=image, gpu="L40S", volumes={"/cache": hf_cache}, timeout=1800)
def synth(model_name: str, lines: list[dict], style: str) -> dict:
    import io

    import soundfile as sf

    t0 = time.time()
    out: dict[str, bytes] = {}
    if model_name == "voxcpm":
        from voxcpm import VoxCPM

        m = VoxCPM.from_pretrained("openbmb/VoxCPM2", load_denoiser=False)
        sr = m.tts_model.sample_rate
        import torch
        for ln in lines:
            torch.manual_seed(42)
            wav = m.generate(text=style + ln["text"], cfg_value=2.0, inference_timesteps=10)
            buf = io.BytesIO(); sf.write(buf, wav, sr, format="WAV"); out[ln["id"]] = buf.getvalue()
    elif model_name == "chatterbox":
        import torch
        from chatterbox.tts import ChatterboxTTS

        m = ChatterboxTTS.from_pretrained(device="cuda")
        for ln in lines:
            torch.manual_seed(42)
            wav = m.generate(ln["text"], exaggeration=0.45, cfg_weight=0.45)
            buf = io.BytesIO(); sf.write(buf, wav.squeeze(0).cpu().numpy(), m.sr, format="WAV")
            out[ln["id"]] = buf.getvalue()
    else:
        raise ValueError(model_name)
    hf_cache.commit()
    return {"wavs": out, "seconds": time.time() - t0}


@app.function(image=image, gpu="L40S", volumes={"/cache": hf_cache}, timeout=2400)
def synth_soft(lines: list[dict], style: str, ref_wav: bytes, ref_text: str, takes: int = 3) -> dict:
    """VoxCPM2 cloned from a reference take the user liked; several seeds per line."""
    import io, tempfile

    import soundfile as sf
    import torch
    from voxcpm import VoxCPM

    t0 = time.time()
    m = VoxCPM.from_pretrained("openbmb/VoxCPM2", load_denoiser=False)
    sr = m.tts_model.sample_rate
    ref = tempfile.NamedTemporaryFile(suffix=".wav", delete=False); ref.write(ref_wav); ref.close()
    out: dict[str, bytes] = {}
    for ln in lines:
        for k in range(takes):
            torch.manual_seed(100 + k)
            wav = m.generate(text=ln["text"], prompt_wav_path=ref.name, prompt_text=ref_text,
                             reference_wav_path=ref.name, cfg_value=1.6, inference_timesteps=12)
            buf = io.BytesIO(); sf.write(buf, wav, sr, format="WAV"); out[f"{ln['id']}.t{k}"] = buf.getvalue()
    hf_cache.commit()
    return {"wavs": out, "seconds": time.time() - t0}


@app.local_entrypoint()
def main(models: str = "voxcpm,chatterbox", dry_run: bool = False, soft: str = "", takes: int = 3,
         ref: str = "", ref_text: str = "", dest_name: str = "voxcpm-soft-takes"):
    script = json.loads((ROOT / "script.json").read_text())
    if soft:  # e.g. --soft 03-map,04-risk : re-voice these lines cloned from the reference line
        ids = [l["id"] for l in script["lines"]] if soft == "all" else soft.split(",")
        ref_id = script["reference_line"]
        ref_line = next(l for l in script["lines"] if l["id"] == ref_id)
        ref_wav = pathlib.Path(ref).read_bytes() if ref else (ROOT / "out" / "tts" / "voxcpm" / f"{ref_id}.wav").read_bytes()
        dest = ROOT / "out" / "tts" / dest_name; dest.mkdir(parents=True, exist_ok=True)
        todo = [l for l in script["lines"] if l["id"] in ids]
        res = synth_soft.remote(todo, script["voice_style_soft"], ref_wav, ref_text or script.get("reference_text", ref_line["text"]), takes)
        for k, b in res["wavs"].items():
            (dest / f"{k}.wav").write_bytes(b)
        rec = {"job": "tts-soft", "model": "voxcpm-clone", "gpu": "L40S", "lines": len(todo), "takes": takes,
               "seconds": round(res["seconds"], 1), "ts": time.time()}
        with (ROOT / "out" / "runs.jsonl").open("a") as f: f.write(json.dumps(rec) + "\n")
        print(rec); return
    if dry_run:
        print(check_imports.remote())
        print(f"{len(script['lines'])} lines, models={models}")
        return
    log = ROOT / "out" / "runs.jsonl"
    for name in models.split(","):
        dest = ROOT / "out" / "tts" / name
        dest.mkdir(parents=True, exist_ok=True)
        todo = [ln for ln in script["lines"] if not (dest / f"{ln['id']}.wav").exists()]
        if not todo:
            print(f"{name}: all lines exist, skipping"); continue
        res = synth.remote(name, todo, script["voice_style_voxcpm"])
        for k, b in res["wavs"].items():
            (dest / f"{k}.wav").write_bytes(b)
        rec = {"job": "tts", "model": name, "gpu": "L40S", "lines": len(todo),
               "seconds": round(res["seconds"], 1), "ts": time.time()}
        with log.open("a") as f: f.write(json.dumps(rec) + "\n")
        print(rec)
