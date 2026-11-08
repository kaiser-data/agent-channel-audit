"""Score to picture: cue sheet from the locked edit, then measure how well each music take fits it.

  python3 music_cue.py cue  [--bpm 84]          # after prep.py: snap scenes to whole bars, write out/cue.json
  modal run modal/music.py --cue out/cue.json   # generate takes at the cue's bpm and length, with sections
  python3 music_cue.py fit  out/music/take-*.wav           # rank takes against the cue (no GPU)
  python3 music_cue.py fit  out/music/take-*.wav --apply   # stage the best take: bar-aligned head trim, no stretch
  python3 prep.py                                          # re-run: phone EQ + manifest pick up cue and score

Why: on the Silverblock promo (2026-11-04) the bed was an 84 s take time-stretched to 93 s (atempo 0.903)
for a cut that later shrank to 69 s. The loudness was flat (-13..-15 dB from 8 s to the end, no arc), scene
changes fell anywhere in the bar, and the take's own ending was faded off before it played. Music that
"doesn't fit the video" is mostly these four: wrong length, no arc, cuts off the beat grid, no ending.

The scene timings are read from edit/src/Promo.tsx (LEAD, TAIL, FPS, minSec) and the voice lengths from
edit/src/manifest.json, so the cue matches what Remotion renders. Promo.tsx uses manifest.cue when present.
"""
import argparse
import json
import math
import pathlib
import re
import shutil
import subprocess

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent
SRC = ROOT / "edit" / "src"
CUE = ROOT / "out" / "cue.json"
SR = 22050


def scene_spec():
    tsx = (SRC / "Promo.tsx").read_text()
    num = lambda name, d: float(m.group(1)) if (m := re.search(rf"const {name} = ([\d.]+)", tsx)) else d
    lead, tail, fps = num("LEAD", 0.35), num("TAIL", 0.75), num("FPS", 30)
    ids = re.findall(r"\{ id: '([^']+)'([^}]*?)render", tsx)
    man = json.loads((SRC / "manifest.json").read_text())
    out = []
    for sid, rest in ids:
        m = re.search(r"minSec: ([\d.]+)", rest)
        if sid not in man["lines"]:
            raise SystemExit(f"manifest.json has no line '{sid}' - re-run prep.py for the current script first")
        need = max(float(m.group(1)) if m else 0.0, lead + man["lines"][sid]["dur"] + tail)
        out.append((sid, need))
    return out, fps


def arc(i, n):
    """Section role per scene: quiet open, steady middle, lift on the last feature beats, resolve on the CTA."""
    if i == 0: return "intro"
    if i == n - 1: return "outro"
    if i >= n - 3: return "lift"
    return "main"


def cmd_cue(a):
    spec, fps = scene_spec()
    def padding(bpm):
        bar = 240 / bpm
        return sum(math.ceil(need / bar) * bar - need for _, need in spec)
    bpm = a.bpm or min(range(72, 109, 2), key=padding)  # calm narrated films sit at 72-108
    bar = 240 / bpm
    t, scenes = 0.0, []
    for i, (sid, need) in enumerate(spec):
        sec = math.ceil(need / bar) * bar
        if sec - bar >= need - 0.25:  # shave up to 0.25 s of tail rather than add a whole bar
            sec -= bar
        scenes.append({"id": sid, "start": round(t, 3), "sec": round(sec, 3), "bars": round(sec / bar, 2),
                       "arc": arc(i, len(spec))})
        t += sec
    cue = {"bpm": bpm, "bar_sec": round(bar, 4), "total_sec": round(t, 3), "fps": fps, "scenes": scenes}
    CUE.parent.mkdir(exist_ok=True)
    CUE.write_text(json.dumps(cue, indent=1))
    man = json.loads((SRC / "manifest.json").read_text())
    man["cue"] = {s["id"]: s["sec"] for s in scenes}
    (SRC / "manifest.json").write_text(json.dumps(man, indent=1))
    print(f"bpm {bpm}, bar {bar:.2f} s, film {t:.1f} s, padding {padding(bpm):.1f} s")
    for s in scenes: print(f"  {s['start']:6.1f}s  {s['sec']:5.2f}s  {s['bars']:4.1f} bars  {s['arc']:6}  {s['id']}")


def load(f):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(f), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32)


def db(x):
    return 20 * math.log10(float(np.sqrt(np.mean(x ** 2))) + 1e-9)


def onset_env(x, hop=512):
    fr = np.lib.stride_tricks.sliding_window_view(x, 1024)[::hop]
    spec = np.abs(np.fft.rfft(fr * np.hanning(1024), axis=1))
    flux = np.maximum(0, np.diff(np.log1p(spec), axis=0)).sum(1)
    return flux - flux.mean(), SR / hop


def tempo(env, rate):
    ac = np.correlate(env, env, "full")[len(env) - 1:]
    lags = np.arange(int(rate * 60 / 180), int(rate * 60 / 55))
    return 60 * rate / lags[np.argmax(ac[lags])]


def beat_phase(env, rate, bpm):
    """Offset (s) of the beat grid inside the first beat that collects the most onset energy."""
    beat = 60 / bpm
    best = max(np.arange(0, beat, 0.01), key=lambda p: env[np.clip(
        ((np.arange(p, len(env) / rate, beat)) * rate).astype(int), 0, len(env) - 1)].sum())
    return float(best)


def fit_one(f, cue):
    x = load(f)
    total, bar, bpm = cue["total_sec"], cue["bar_sec"], cue["bpm"]
    win = [db(x[i:i + SR]) for i in range(0, len(x) - SR, SR // 2)]  # 1 s windows, 0.5 s hop
    sound = [i * 0.5 for i, v in enumerate(win) if v > -32]
    end = (sound[-1] + 1.0) if sound else 0.0  # where the take actually stops sounding
    env, rate = onset_env(x)
    est = tempo(env, rate)
    ratio = min(abs(est / bpm - r) for r in (0.5, 1, 2))
    phase = beat_phase(env, rate, bpm)
    # back-time: the take's own ending should land ~1 s after the film ends, trimmed in whole bars
    trim = math.floor(max(0.0, end - total - 1.0) / bar) * bar + phase
    issues = []
    if end - trim < total:
        issues.append(f"too short: sounds for {end:.1f} s, film needs {total + trim:.1f} s - regenerate longer, never stretch")
    y = x[int(trim * SR):]
    sec_db = [db(y[int(s["start"] * SR):int((s["start"] + s["sec"]) * SR)]) if len(y) > s["start"] * SR else -90
              for s in cue["scenes"]]
    body = sec_db[1:-1] or sec_db
    spread = max(body) - min(body)
    if spread < 2.5:
        issues.append(f"flat: scene loudness spread {spread:.1f} dB - no arc, reads as a loop")
    lift = np.mean(sec_db[-3:-1]) - np.mean(sec_db[1:3]) if len(sec_db) >= 5 else 0
    if lift < 1.5:
        issues.append(f"no lift into the CTA ({lift:+.1f} dB)")
    gaps = [i * 0.5 - trim for i, v in enumerate(win) if v < -40 and trim + 1 < i * 0.5 < trim + total - 1]
    if gaps:
        issues.append(f"drops out at {gaps[0]:.1f} s")
    if ratio > 0.04:
        issues.append(f"tempo {est:.0f} bpm, cue asks {bpm} - cuts will not land on the beat")
    return {"take": str(f), "trim_s": round(trim, 3), "sounds_until_s": end, "bpm_est": round(est, 1),
            "scene_db": [round(v, 1) for v in sec_db], "spread_db": round(spread, 1), "lift_db": round(float(lift), 1),
            "issues": issues}


def cmd_fit(a):
    cue = json.loads(CUE.read_text())
    res = sorted((fit_one(f, cue) for f in a.takes), key=lambda r: (len(r["issues"]), -r["lift_db"]))
    for r in res:
        print(f"{pathlib.Path(r['take']).name}: trim {r['trim_s']} s, bpm~{r['bpm_est']}, lift {r['lift_db']:+} dB, "
              f"scenes {r['scene_db']}")
        for i in r["issues"]: print(f"    - {i}")
        if not r["issues"]: print("    ok")
    (ROOT / "out" / "music-fit.json").write_text(json.dumps(res, indent=1))
    if a.apply:
        best = res[0]
        if any(i.startswith("too short") for i in best["issues"]):
            raise SystemExit("best take is too short - regenerate with --cue, do not stretch")
        dst = ROOT / "edit" / "public" / "score.wav"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", str(best["trim_s"]), "-i", best["take"],
                        "-t", str(cue["total_sec"] + 2), "-ar", "48000", str(dst)], check=True)
        shutil.copy2(best["take"], ROOT / "out" / "score-source.wav")
        print(f"staged {pathlib.Path(best['take']).name} -> {dst} (head trim {best['trim_s']} s). Re-run prep.py.")


def main():
    ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("cue"); c.add_argument("--bpm", type=int, default=0)
    f = sub.add_parser("fit"); f.add_argument("takes", nargs="+"); f.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    {"cue": cmd_cue, "fit": cmd_fit}[a.cmd](a)


if __name__ == "__main__":
    main()
