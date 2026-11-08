"""Pick one take per line from out/tts/<voice>-takes/: WER <= 0.12, product name heard when the line has it,
then the take whose loudness is closest to the voice's median (keeps lines level). Writes out/tts/<voice>/<id>.wav
and out/tts/<voice>/picks.json.

  python3 modal/pick_qwen.py qwen-f-upbeat [script.json] [ProductName]
"""
import json
import pathlib
import re
import shutil
import statistics
import subprocess
import sys

from faster_whisper import WhisperModel

ROOT = pathlib.Path(__file__).resolve().parent.parent
voice = sys.argv[1]
script = sys.argv[2] if len(sys.argv) > 2 else "script.json"
PRODUCT = sys.argv[3].lower() if len(sys.argv) > 3 else "product"   # name that must be heard
src, dst = ROOT / "out" / "tts" / f"{voice}-takes", ROOT / "out" / "tts" / voice
dst.mkdir(parents=True, exist_ok=True)
norm = lambda s: re.sub(r"[^a-z0-9 ]", " ", s.lower().replace("-", " ").replace("\u2019", "").replace("'", "")).split()


def wer(r, h):
    r, h = norm(r), norm(h); d = list(range(len(h) + 1))
    for i in range(1, len(r) + 1):
        p, d[0] = d[0], i
        for j in range(1, len(h) + 1):
            p, d[j] = d[j], min(d[j] + 1, d[j - 1] + 1, p + (r[i - 1] != h[j - 1]))
    return d[len(h)] / max(1, len(r))


def lufs(f):
    e = subprocess.run(["ffmpeg", "-nostats", "-i", str(f), "-af", "ebur128", "-f", "null", "-"], capture_output=True, text=True).stderr
    return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", e)[-1])


m = WhisperModel("small.en", device="cpu", compute_type="int8")
rows = []
for ln in json.loads((ROOT / script).read_text())["lines"]:
    for f in sorted(src.glob(f"{ln['id']}-t*.wav")):
        # no initial_prompt: a prompt containing the name would make Whisper "hear" it even when mispronounced
        txt = " ".join(s.text for s in m.transcribe(str(f))[0]).strip()
        has_name = PRODUCT in ln["text"].lower()
        heard = PRODUCT.replace(" ", "") in txt.lower().replace(" ", "").replace("-", "")
        rows.append({"id": ln["id"], "file": f.name, "wer": round(wer(ln["text"], txt), 3), "lufs": lufs(f),
                     "name_ok": heard or not has_name, "txt": txt})
med = statistics.median(r["lufs"] for r in rows)
picks = {}
for lid in dict.fromkeys(r["id"] for r in rows):
    c = [r for r in rows if r["id"] == lid]
    ok = [r for r in c if r["wer"] <= 0.12 and r["name_ok"]] or [r for r in c if r["wer"] <= 0.12] or c
    best = min(ok, key=lambda r: (abs(r["lufs"] - med), r["wer"]))
    shutil.copy2(src / best["file"], dst / f"{lid}.wav")
    picks[lid] = best
    print(f"{lid:14} {best['file']:20} wer={best['wer']} lufs={best['lufs']} name_ok={best['name_ok']} | {best['txt'][:60]}")
(dst / "picks.json").write_text(json.dumps({"median_lufs": med, "picks": picks, "all": rows}, indent=1))
