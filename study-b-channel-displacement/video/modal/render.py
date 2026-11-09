"""Render the Remotion edit on Modal instead of the laptop (CPU-heavy, needs disk).

  modal run modal/render.py                      # both compositions, in parallel
  modal run modal/render.py --comps Promo        # one
Clips are re-encoded in the container with a keyframe every 0.5 s (fast seeking for Remotion).
Outputs: out/<name>.mp4 ; run logged to out/runs.jsonl.
"""
import json
import pathlib
import time

import modal

ROOT = pathlib.Path(__file__).resolve().parent.parent
EDIT = ROOT / "edit"

image = (
    modal.Image.from_registry("node:20-bookworm-slim", add_python="3.11")
    .apt_install("ffmpeg", "fonts-ebgaramond", "fonts-inter", "fonts-dejavu-core",
                 "libnss3", "libdbus-1-3", "libatk1.0-0", "libatk-bridge2.0-0", "libgbm1", "libasound2",
                 "libxrandr2", "libxkbcommon0", "libxfixes3", "libxcomposite1", "libxdamage1",
                 "libpango-1.0-0", "libcairo2", "libcups2")
    .add_local_file(str(EDIT / "package.json"), "/work/package.json", copy=True)
    .add_local_file(str(EDIT / "package-lock.json"), "/work/package-lock.json", copy=True)
    .run_commands("cd /work && npm ci --no-audit --no-fund && npx remotion browser ensure")
    .add_local_dir(str(EDIT / "src"), "/work/src")
    .add_local_file(str(EDIT / "tsconfig.json"), "/work/tsconfig.json")
    .add_local_dir(str(EDIT / "public"), "/assets/public")
)
app = modal.App("cd-explainer-render", image=image)

OUTS = {"Promo": ("channel-displacement-16x9.mp4", 16), "PromoFeed": ("channel-displacement-4x5.mp4", 18)}


@app.function(cpu=16, memory=32768, timeout=3600)
def render(comp: str) -> dict:
    import shutil
    import subprocess

    t0 = time.time()
    shutil.copytree("/assets/public", "/work/public", dirs_exist_ok=True)
    for clip in pathlib.Path("/work/public/clips").glob("*.mp4"):
        tmp = clip.with_suffix(".tmp.mp4")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(clip), "-c:v", "libx264", "-crf", "17",
                        "-preset", "fast", "-g", "15", "-keyint_min", "15", "-pix_fmt", "yuv420p", "-an", str(tmp)],
                       check=True)
        tmp.replace(clip)
    for b in pathlib.Path("/work/public/broll").glob("*.mp4"):
        fps = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=r_frame_rate",
                              "-of", "csv=p=0", str(b)], capture_output=True, text=True).stdout.strip()
        if fps and eval(fps) < 30:  # generated b-roll: motion-interpolate to 60 fps so slowed shots stay smooth
            tmp = b.with_suffix(".tmp.mp4")
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(b), "-vf",
                            "minterpolate=fps=60:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1,"
                            "scale=1920:1080:flags=lanczos,format=yuv420p", "-c:v", "libx264", "-crf", "15", str(tmp)],
                           check=True)
            tmp.replace(b)
    name, crf = OUTS[comp]
    out = f"/tmp/{name}"
    subprocess.run(["npx", "remotion", "render", "src/index.ts", comp, out, "--codec", "h264", "--crf", str(crf),
                    "--timeout", "120000", "--log", "error"], cwd="/work", check=True)
    # master the finished mix as a whole (keeps the relative dynamics between lines), video untouched
    mastered = out.replace(".mp4", ".m.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", out, "-c:v", "copy", "-af",
                    "acompressor=threshold=-18dB:ratio=1.6:attack=20:release=300:makeup=1.5,loudnorm=I=-14:TP=-1.5:LRA=11,alimiter=limit=0.8:level=false", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", mastered],
                   check=True)
    out = mastered
    return {"name": name, "mp4": pathlib.Path(out).read_bytes(), "seconds": round(time.time() - t0, 1)}


@app.local_entrypoint()
def main(comps: str = "Promo,PromoFeed"):
    (ROOT / "out").mkdir(exist_ok=True)
    for res in render.map(comps.split(",")):
        (ROOT / "out" / res["name"]).write_bytes(res["mp4"])
        rec = {"job": "render", "file": res["name"], "cpu": 16, "seconds": res["seconds"], "ts": time.time()}
        with (ROOT / "out" / "runs.jsonl").open("a") as f: f.write(json.dumps(rec) + "\n")
        print(rec)
