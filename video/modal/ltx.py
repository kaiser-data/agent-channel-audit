"""B-roll with LTX-2.5 (22B distilled, native 1080p) on Modal — free weights, Modal GPU time only.

  modal run modal/ltx.py --dry-run                 # wave 0: CPU, build, CLI help, weights -> Volume
  modal run modal/ltx.py --shots s1-sky            # wave 1: one shot, look at it
  modal run modal/ltx.py                           # wave 2: remaining shots, one container each
Outputs out/ltx/<shot>.mp4 (1920x1088, 24 fps, 121 frames). Licence: LTX-2 licence (free < $10M revenue).
"""
import json
import pathlib
import time

import modal

from wan import NEG, SHOTS, STYLE  # same shot list and look as the Wan pass

ROOT = pathlib.Path(__file__).resolve().parent.parent
app = modal.App("astrolab-promo-ltx")
weights = modal.Volume.from_name("ltx25-weights", create_if_missing=True)
hf_secret = modal.Secret.from_name("huggingface-secret")
W = "/weights"
FILES = ["diffusion_models/ltx-2.5-22b-distilled-transformer-bf16.safetensors",
         "text_encoders/gemma4-12b-with-proj-ltx-2.5-bf16.safetensors",
         "vae/ltx-2.5-video-vae-bf16.safetensors",
         "vae/ltx-2.5-audio-vae-bf16.safetensors",
         "latent_upscale_models/ltx-2.5-latent-spatial-upscaler-x2-bf16-1.0.safetensors"]

image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("git", "ffmpeg", "build-essential")
    .pip_install("uv", "huggingface_hub[hf_xet]")
    .run_commands("git clone --depth 1 https://github.com/Lightricks/LTX-2 /opt/ltx",
                  # the natten extra pins an unresolvable wheel; it is an optional speed-up
                  # uv resolves optional extras too; the pinned natten wheel is not on its index -> drop it
                  "cd /opt/ltx && sed -i '/natten==/d; /^natten = { index/d' packages/ltx-core/pyproject.toml",
                  "cd /opt/ltx && uv sync")
    .add_local_python_source("wan")
)


@app.function(image=image, volumes={W: weights}, secrets=[hf_secret], timeout=3600, cpu=8)
def prepare() -> str:
    import subprocess

    from huggingface_hub import hf_hub_download
    for f in FILES:
        hf_hub_download("Lightricks/LTX-2.5", f, local_dir=W)
    weights.commit()
    h = subprocess.run(["/opt/ltx/.venv/bin/python", "-m", "ltx_pipelines.distilled", "--help"],
                       capture_output=True, text=True, cwd="/opt/ltx")
    return (h.stdout or h.stderr)


@app.function(image=image, gpu="H200", volumes={W: weights}, timeout=3600)
def render(name: str, seed: int = 42) -> dict:
    import subprocess

    t0 = time.time()
    out = f"/tmp/{name}.mp4"
    cmd = ["/opt/ltx/.venv/bin/python", "-m", "ltx_pipelines.distilled",
           "--transformer-path", f"{W}/{FILES[0]}", "--text-encoder-path", f"{W}/{FILES[1]}",
           "--video-vae-path", f"{W}/{FILES[2]}", "--audio-vae-path", f"{W}/{FILES[3]}",
           "--spatial-upsampler-path", f"{W}/{FILES[4]}",
           "--width", "1920", "--height", "1088", "--num-frames", "121", "--seed", str(seed),
           "--output-path", out, "--prompt", SHOTS[name] + STYLE]
    subprocess.run(cmd, check=True, cwd="/opt/ltx")
    return {"name": name, "mp4": pathlib.Path(out).read_bytes(), "seconds": round(time.time() - t0, 1)}


@app.local_entrypoint()
def main(shots: str = "", dry_run: bool = False):
    if dry_run:
        print(prepare.remote()); return
    dest = ROOT / "out" / "ltx"; dest.mkdir(parents=True, exist_ok=True)
    names = [n for n in (shots.split(",") if shots else list(SHOTS)) if not (dest / f"{n}.mp4").exists()]
    for res in render.map(names):
        (dest / f"{res['name']}.mp4").write_bytes(res["mp4"])
        rec = {"job": "ltx", "model": "LTX-2.5 22B distilled", "gpu": "H200", "shot": res["name"],
               "seconds": res["seconds"], "ts": time.time()}
        with (ROOT / "out" / "runs.jsonl").open("a") as f: f.write(json.dumps(rec) + "\n")
        print(rec)
