"""Narration A/B with VibeVoice-Realtime-0.5B (MIT) on Modal.

  modal run modal/vibevoice.py --dry-run                 # wave 0: CPU, list voices + CLI help
  modal run modal/vibevoice.py --speakers Carter,Davis   # wave 1: all lines per speaker
Outputs out/tts/vibevoice-<speaker>/<line-id>.wav
"""
import json
import pathlib
import time

import modal

ROOT = pathlib.Path(__file__).resolve().parent.parent
app = modal.App("astrolab-promo-vibevoice")
hf_cache = modal.Volume.from_name("astrolab-hf-cache", create_if_missing=True)
MODEL = "microsoft/VibeVoice-Realtime-0.5B"

image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("git", "ffmpeg", "libsndfile1")
    .pip_install("torch==2.6.0", "torchaudio==2.6.0")
    .run_commands("git clone --depth 1 https://github.com/microsoft/VibeVoice /opt/vv",
                  "cd /opt/vv && pip install -e '.[streamingtts]'",
                  # run the demo from outside demo/, where a sibling module shadows the vibevoice package
                  "cp /opt/vv/demo/realtime_model_inference_from_file.py /opt/vv_rt.py",
                  "sed -i s/flash_attention_2/sdpa/g /opt/vv_rt.py",
                  "ln -s /opt/vv/demo/voices /opt/voices")
    .env({"HF_HOME": "/cache/hf", "PYTHONPATH": "/opt/vv"})
)


@app.function(image=image, volumes={"/cache": hf_cache}, timeout=600)
def check() -> str:
    import glob
    import subprocess
    voices = sorted(glob.glob("/opt/vv/demo/voices/**/*", recursive=True))
    helptext = subprocess.run(["python", "/opt/vv_rt.py", "--help"], cwd="/opt/vv",
                              capture_output=True, text=True)
    which = subprocess.run(["python", "-c", "import vibevoice,sys;print(vibevoice.__file__)"], cwd="/opt",
                           capture_output=True, text=True)
    return "WHICH: " + (which.stdout or which.stderr)[-400:] + "\nVOICES:\n" + "\n".join(voices[:60]) + "\nHELP:\n" + (helptext.stdout or helptext.stderr)[-2500:]


@app.function(image=image, gpu="L40S", volumes={"/cache": hf_cache}, timeout=1800)
def synth(speaker: str, lines: list[dict]) -> dict:
    import glob
    import os
    import subprocess

    t0 = time.time()
    out = {}
    for ln in lines:
        d = f"/tmp/{speaker}/{ln['id']}"; os.makedirs(d, exist_ok=True)
        txt = f"{d}/in.txt"; pathlib.Path(txt).write_text(ln["text"])
        subprocess.run(["python", "/opt/vv_rt.py", "--model_path", MODEL,
                        "--txt_path", txt, "--speaker_name", speaker, "--output_dir", d],
                       cwd="/opt/vv", check=True)
        wav = sorted(glob.glob(f"{d}/**/*.wav", recursive=True))
        assert wav, f"no wav for {ln['id']}"
        out[ln["id"]] = pathlib.Path(wav[-1]).read_bytes()
    hf_cache.commit()
    return {"wavs": out, "seconds": round(time.time() - t0, 1)}


@app.local_entrypoint()
def main(dry_run: bool = False, speakers: str = "Carter"):
    if dry_run:
        print(check.remote()); return
    script = json.loads((ROOT / "script.json").read_text())
    names = speakers.split(",")
    for sp, res in zip(names, synth.starmap([(s, script["lines"]) for s in names])):
        dest = ROOT / "out" / "tts" / f"vibevoice-{sp}"; dest.mkdir(parents=True, exist_ok=True)
        for k, b in res["wavs"].items():
            (dest / f"{k}.wav").write_bytes(b)
        rec = {"job": "tts", "model": f"vibevoice-rt-{sp}", "gpu": "L40S", "seconds": res["seconds"], "ts": time.time()}
        with (ROOT / "out" / "runs.jsonl").open("a") as f: f.write(json.dumps(rec) + "\n")
        print(rec)
