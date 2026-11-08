"""Pick the calmest correct take per line: WER <= 0.12, then lowest loudness (LUFS) and lowest pitch spread."""
import json, pathlib, re, subprocess, shutil, sys
import numpy as np, soundfile as sf
from faster_whisper import WhisperModel
ROOT = pathlib.Path(__file__).resolve().parent.parent
script = {l["id"]: l["text"] for l in json.loads((ROOT / "script.json").read_text())["lines"]}
V = sys.argv[1] if len(sys.argv) > 1 else "voxcpm-soft"
src, dst = ROOT / f"out/tts/{V}-takes", ROOT / f"out/tts/{V}"
dst.mkdir(exist_ok=True)
norm = lambda s: re.sub(r"[^a-z0-9 ]", " ", s.lower().replace("-", " ")).split()
def wer(r, h):
    r, h = norm(r), norm(h); d = list(range(len(h) + 1))
    for i in range(1, len(r) + 1):
        p, d[0] = d[0], i
        for j in range(1, len(h) + 1):
            p, d[j] = d[j], min(d[j] + 1, d[j - 1] + 1, p + (r[i - 1] != h[j - 1]))
    return d[len(h)] / max(1, len(r))
def lufs(f):
    o = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(f), "-af", "ebur128", "-f", "null", "-"], capture_output=True, text=True).stderr
    return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", o)[-1])
def loud_spread(f):  # 95th-5th percentile of 50 ms RMS in dB over voiced frames: shouting = big spikes
    a, sr = sf.read(f); a = a if a.ndim == 1 else a.mean(1); n = int(sr * .05)
    r = np.array([np.sqrt(np.mean(a[i:i + n] ** 2)) for i in range(0, len(a) - n, n)]); r = r[r > 1e-3]
    db = 20 * np.log10(r); return float(np.percentile(db, 95) - np.percentile(db, 50))
m = WhisperModel("small.en", device="cpu", compute_type="int8")
ids = sorted({p.stem.split(".")[0] for p in src.glob("*.wav")})
for lid in ids:
    rows = []
    for f in sorted(src.glob(f"{lid}.t*.wav")):
        hyp = " ".join(s.text for s in m.transcribe(str(f), beam_size=5)[0])
        rows.append((wer(script[lid], hyp), lufs(f), loud_spread(f), f, hyp))
    ok = [r for r in rows if r[0] <= 0.12] or rows
    best = min(ok, key=lambda r: (r[1] + r[2]))
    for r in rows:
        print(f"{'*' if r is best else ' '} {r[3].name:18s} wer={r[0]:.2f} lufs={r[1]:6.1f} spread={r[2]:4.1f} | {r[4].strip()[:70]}")
    shutil.copy(best[3], dst / f"{lid}.wav")
for lid in script:  # lines without new takes fall back to the original voxcpm render
    if not (dst / f"{lid}.wav").exists():
        shutil.copy(ROOT / "out/tts/voxcpm" / f"{lid}.wav", dst / f"{lid}.wav")
print("done:", sorted(p.name for p in dst.glob("*.wav")))
