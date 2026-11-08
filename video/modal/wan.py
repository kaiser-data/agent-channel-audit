"""Cinematic b-roll with Wan2.2 T2V-A14B on Modal.

  modal run modal/wan.py --dry-run               # wave 0: CPU, image build + weight download to volume
  modal run modal/wan.py --shots s1-sky          # wave 1: one anchor shot on GPU
  modal run modal/wan.py                         # wave 2: remaining shots (existing skipped)
Outputs: out/wan/<shot>.mp4 (1280x720, 81 frames @16fps = ~5s). Runs logged to out/runs.jsonl.
"""
import json
import pathlib
import time

import modal

MODEL_ID = "Wan-AI/Wan2.2-T2V-A14B-Diffusers"
GPU = "H200"

app = modal.App("astrolab-promo-wan")
hf_cache = modal.Volume.from_name("astrolab-hf-cache", create_if_missing=True)

image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("ffmpeg", "git")
    .pip_install("torch==2.6.0", "torchvision==0.21.0")
    .pip_install("diffusers>=0.35.1", "transformers>=4.51", "accelerate", "ftfy",
                 "imageio", "imageio-ffmpeg", "sentencepiece", "huggingface_hub[hf_transfer]")
    .env({"HF_HOME": "/cache/hf", "HF_HUB_ENABLE_HF_TRANSFER": "1"})
)

STYLE = ", cinematic, anamorphic lens, film grain, deep navy and warm gold palette, high detail, 4k"
NEG = ("text, watermark, logo, subtitles, ugly, blurry, low quality, jpeg artifacts, deformed, "
       "oversaturated, static, frozen frame, people, faces, hands")
SHOTS = {
    "s1-sky": "Night sky over a quiet desert, thousands of bright stars, slow dolly forward; thin golden "
              "lines begin to connect the stars one by one into a glowing constellation network",
    "s2-astrolabe": "Macro shot of an antique brass astrolabe slowly rotating on a dark walnut desk, warm "
                    "candle light, engraved star charts glinting, floating dust particles, shallow depth of field",
    "s3-galaxy": "Thousands of tiny glowing points of light in many colors drift and gather into clusters, "
                 "forming a three-dimensional galaxy-like network joined by faint threads of light, slow "
                 "orbiting camera, black background, volumetric glow",
    "s4-align": "The brass rings of an astrolabe slowly turn and align, a beam of golden sunrise light flares "
                "through the center, sparks of starlight scatter outward, slow motion",
}

ROOT = pathlib.Path(__file__).resolve().parent.parent


@app.function(image=image, volumes={"/cache": hf_cache}, timeout=3600, cpu=4)
def download() -> str:
    from huggingface_hub import snapshot_download
    import diffusers
    p = snapshot_download(MODEL_ID)
    hf_cache.commit()
    return f"diffusers {diffusers.__version__}; weights at {p}"


@app.function(image=image, gpu=GPU, volumes={"/cache": hf_cache}, timeout=3600)
def render(shots: dict, steps: int = 40) -> dict:
    import tempfile

    import torch
    from diffusers import AutoencoderKLWan, WanPipeline
    from diffusers.utils import export_to_video

    t0 = time.time()
    vae = AutoencoderKLWan.from_pretrained(MODEL_ID, subfolder="vae", torch_dtype=torch.float32)
    pipe = WanPipeline.from_pretrained(MODEL_ID, vae=vae, torch_dtype=torch.bfloat16).to("cuda")
    load_s = time.time() - t0
    out, per = {}, {}
    for name, prompt in shots.items():
        t1 = time.time()
        frames = pipe(prompt=prompt + STYLE, negative_prompt=NEG, height=720, width=1280,
                      num_frames=81, guidance_scale=4.0, guidance_scale_2=3.0,
                      num_inference_steps=steps,
                      generator=torch.Generator("cuda").manual_seed(7)).frames[0]
        with tempfile.NamedTemporaryFile(suffix=".mp4") as f:
            export_to_video(frames, f.name, fps=16)
            out[name] = pathlib.Path(f.name).read_bytes()
        per[name] = round(time.time() - t1, 1)
    return {"mp4": out, "load_s": round(load_s, 1), "per_shot_s": per}


@app.local_entrypoint()
def main(shots: str = "", dry_run: bool = False, steps: int = 40):
    if dry_run:
        print(download.remote())
        print("shots:", list(SHOTS))
        return
    want = shots.split(",") if shots else list(SHOTS)
    dest = ROOT / "out" / "wan"; dest.mkdir(parents=True, exist_ok=True)
    todo = {k: SHOTS[k] for k in want if not (dest / f"{k}.mp4").exists()}
    if not todo:
        print("all shots exist, skipping"); return
    t0 = time.time()
    # one container per shot: same GPU-seconds, wall time of a single shot
    for res in render.map([{k: v} for k, v in todo.items()], kwargs={"steps": steps}):
        for k, b in res["mp4"].items():
            (dest / f"{k}.mp4").write_bytes(b)
        rec = {"job": "wan", "gpu": GPU, "shots": list(res["mp4"]), "steps": steps,
               "load_s": res["load_s"], "per_shot_s": res["per_shot_s"],
               "wall_s": round(time.time() - t0, 1), "ts": time.time()}
        with (ROOT / "out" / "runs.jsonl").open("a") as f: f.write(json.dumps(rec) + "\n")
        print(rec)
