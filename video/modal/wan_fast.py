"""Extra takes per b-roll shot with Wan2.2 T2V-A14B + LightX2V Lightning LoRA (4 steps, CFG 1).

  modal run modal/wan_fast.py --dry-run           # wave 0: CPU, verify LoRA loading API
  modal run modal/wan_fast.py --shots s1-sky --takes 1   # wave 1: one take, look at it
  modal run modal/wan_fast.py --takes 3           # wave 2: all shots, 3 seeds each, one container per shot
Outputs out/wan-takes/<shot>.t<k>.mp4 ; existing takes are skipped.
"""
import json
import pathlib
import time

import modal

from wan import MODEL_ID, NEG, SHOTS, STYLE, image, hf_cache  # same prompts + cached weights

LORA_REPO = "lightx2v/Wan2.2-Lightning"
LORA_HI = "Wan2.2-T2V-A14B-4steps-lora-250928/high_noise_model.safetensors"
LORA_LO = "Wan2.2-T2V-A14B-4steps-lora-250928/low_noise_model.safetensors"
GPU = "H200"
ROOT = pathlib.Path(__file__).resolve().parent.parent
app = modal.App("astrolab-promo-wan-fast")
img = image.pip_install("peft").add_local_python_source("wan")


@app.function(image=img, volumes={"/cache": hf_cache}, timeout=1800, cpu=4)
def check() -> str:
    import inspect

    from diffusers import WanPipeline
    from huggingface_hub import hf_hub_download
    sig = inspect.signature(WanPipeline.load_lora_weights)
    for f in (LORA_HI, LORA_LO):
        hf_hub_download(LORA_REPO, f)
    hf_cache.commit()
    return f"load_lora_weights{sig}\nLoRAs cached"


@app.function(image=img, gpu=GPU, volumes={"/cache": hf_cache}, timeout=3600)
def render(name: str, seeds: list[int]) -> dict:
    import tempfile

    import torch
    from diffusers import AutoencoderKLWan, WanPipeline
    from diffusers.utils import export_to_video

    t0 = time.time()
    vae = AutoencoderKLWan.from_pretrained(MODEL_ID, subfolder="vae", torch_dtype=torch.float32)
    pipe = WanPipeline.from_pretrained(MODEL_ID, vae=vae, torch_dtype=torch.bfloat16).to("cuda")
    pipe.load_lora_weights(LORA_REPO, weight_name=LORA_HI, adapter_name="lightning")
    pipe.load_lora_weights(LORA_REPO, weight_name=LORA_LO, adapter_name="lightning_2", load_into_transformer_2=True)
    load_s = time.time() - t0
    out, per = {}, {}
    for s in seeds:
        t1 = time.time()
        frames = pipe(prompt=SHOTS[name] + STYLE, negative_prompt=NEG, height=720, width=1280, num_frames=81,
                      guidance_scale=1.0, guidance_scale_2=1.0, num_inference_steps=4,
                      generator=torch.Generator("cuda").manual_seed(s)).frames[0]
        with tempfile.NamedTemporaryFile(suffix=".mp4") as f:
            export_to_video(frames, f.name, fps=16)
            out[f"{name}.t{s}"] = pathlib.Path(f.name).read_bytes()
        per[s] = round(time.time() - t1, 1)
    return {"mp4": out, "load_s": round(load_s, 1), "per_take_s": per}


@app.local_entrypoint()
def main(shots: str = "", takes: int = 3, dry_run: bool = False):
    if dry_run:
        print(check.remote()); return
    dest = ROOT / "out" / "wan-takes"; dest.mkdir(parents=True, exist_ok=True)
    names = shots.split(",") if shots else list(SHOTS)
    jobs = []
    for n in names:
        seeds = [s for s in range(11, 11 + takes) if not (dest / f"{n}.t{s}.mp4").exists()]
        if seeds: jobs.append((n, seeds))
    if not jobs:
        print("all takes exist"); return
    t0 = time.time()
    for res in render.starmap(jobs):
        for k, b in res["mp4"].items():
            (dest / f"{k}.mp4").write_bytes(b)
        rec = {"job": "wan-fast", "gpu": GPU, "takes": list(res["mp4"]), "load_s": res["load_s"],
               "per_take_s": res["per_take_s"], "wall_s": round(time.time() - t0, 1), "ts": time.time()}
        with (ROOT / "out" / "runs.jsonl").open("a") as f: f.write(json.dumps(rec) + "\n")
        print(rec)
