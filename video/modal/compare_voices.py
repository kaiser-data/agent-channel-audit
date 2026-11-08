"""Compare narration sets: mean/max WER, loudness mean±std across lines, loudness spread, total length."""
import json, pathlib, re, subprocess, sys
import numpy as np, soundfile as sf
from faster_whisper import WhisperModel
ROOT = pathlib.Path(__file__).resolve().parent.parent
script = {l["id"]: l["text"] for l in json.loads((ROOT / "script.json").read_text())["lines"]}
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
def spread(f):
    a, sr = sf.read(f); a = a if a.ndim == 1 else a.mean(1); n = int(sr * .05)
    r = np.array([np.sqrt(np.mean(a[i:i + n] ** 2)) for i in range(0, len(a) - n, n)]); r = r[r > 1e-3]
    db = 20 * np.log10(r); return float(np.percentile(db, 95) - np.percentile(db, 50))
m = WhisperModel("small.en", device="cpu", compute_type="int8", cpu_threads=2)
for v in sys.argv[1].split(","):
    W, L, S, D = [], [], [], 0.0
    for lid, ref in script.items():
        f = ROOT / "out/tts" / v / f"{lid}.wav"
        W.append(wer(ref, " ".join(s.text for s in m.transcribe(str(f), beam_size=3)[0])))
        L.append(lufs(f)); S.append(spread(f)); D += sf.info(str(f)).duration
    print(f"{v:18s} meanWER={np.mean(W):.3f} maxWER={max(W):.2f} LUFS={np.mean(L):6.1f}±{np.std(L):.1f} spread={np.mean(S):4.1f} total={D:5.1f}s", flush=True)
