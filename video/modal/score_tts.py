"""Objective TTS check: faster-whisper transcript -> WER vs script, peak level, longest internal silence."""
import json, re, sys, pathlib, subprocess
import numpy as np, soundfile as sf
from faster_whisper import WhisperModel
ROOT = pathlib.Path(__file__).resolve().parent.parent
script = {l["id"]: l["text"] for l in json.loads((ROOT/"script.json").read_text())["lines"]}
norm = lambda s: re.sub(r"[^a-z0-9 ]", " ", s.lower().replace("-", " ")).split()
def wer(ref, hyp):
    r, h = norm(ref), norm(hyp); d = list(range(len(h)+1))
    for i in range(1, len(r)+1):
        p, d[0] = d[0], i
        for j in range(1, len(h)+1):
            p, d[j] = d[j], min(d[j]+1, d[j-1]+1, p+(r[i-1]!=h[j-1]))
    return d[len(h)]/max(1,len(r))
m = WhisperModel("small.en", device="cpu", compute_type="int8")
for model in sys.argv[1].split(","):
    tot = []
    for lid, ref in script.items():
        f = ROOT/"out"/"tts"/model/f"{lid}.wav"
        a, sr = sf.read(f); a = a if a.ndim == 1 else a.mean(1)
        hyp = " ".join(s.text for s in m.transcribe(str(f), beam_size=5)[0])
        frame = int(sr*0.02); env = np.array([np.abs(a[i:i+frame]).max() for i in range(0, len(a)-frame, frame)])
        voiced = np.where(env > 0.02)[0]; gaps = np.diff(voiced)*0.02 if len(voiced) > 1 else [0]
        w = wer(ref, hyp); tot.append(w)
        print(f"{model:10s} {lid:10s} wer={w:.2f} peak={np.abs(a).max():.2f} maxgap={max(gaps):.2f}s sr={sr} | {hyp.strip()[:90]}")
    print(f"{model}: mean WER {np.mean(tot):.3f}\n")
