"""Stage assets into edit/public and write edit/src/manifest.json.

  python3 prep.py [--voice voxcpm|chatterbox]
- narration: loudness-normalised to -16 LUFS, 48 kHz
- Wan b-roll: motion-interpolated 16 -> 60 fps (smooth when slowed down); placeholder if not rendered yet
- app clips: copied as-is
- tool cards: real numbers from the Astrolab dataset
"""
import argparse
import os
import json
import pathlib
import shutil
import subprocess

ROOT = pathlib.Path(__file__).resolve().parent
PUB = ROOT / "edit" / "public"
# Optional: a JSON dataset whose real numbers feed the "tools" cards (list of repo dicts, or {"repos": [...]}).
DATA = pathlib.Path(os.environ["VIDEO_DATA"]) if os.environ.get("VIDEO_DATA") else None

CUTS = {  # where to start in each real-time recording, and how fast to play it
    "map": {"start": 12.0, "rate": 4.0, "zoom": [1.05, 1.18], "origin": "38% 55%"},
    "risk": {"start": 2.2, "rate": 1.6, "zoom": [1.0, 1.35], "origin": "20% 85%"},
    "reports": {"start": 2.2, "rate": 2.2, "zoom": [1.0, 1.3], "origin": "10% 60%"},
    "ask": {"start": 3.5, "rate": 1.6, "zoom": [1.2, 1.5], "origin": "0% 100%"},
}
# chosen take per shot (contact-sheet originals vs. Lightning takes, then fill this in)
PICKS: dict[str, str] = {}
TOOLS = [("microsoft/playwright", "records the app"), ("Wan-Video/Wan2.2", "paints the sky"),
         ("OpenBMB/VoxCPM", "the narration"), ("remotion-dev/remotion", "the edit")]


def dur(p):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                          "-of", "csv=p=0", str(p)]).decode().strip())


def ff(*args):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *map(str, args)], check=True)


def phone_score():
    """Scores carry much of their energy below 200 Hz, which phone speakers cannot play, so on a
    phone the bed vanishes. Trim sub-bass and lift what a phone does play - but around the voice, not
    into it: 1-4 kHz is where narration is understood, so the music gets a dip there (a 1.8 kHz boost
    here masked the voice on the Silverblock cut) and its lift sits at 500-900 Hz and above 5 kHz."""
    src, dst = PUB / "score.wav", PUB / "score-phone.wav"
    if not src.exists():
        return None
    ff("-i", src, "-af", "highpass=f=45,lowshelf=f=160:g=-5,equalizer=f=700:t=o:w=1.2:g=2.5,"
       "equalizer=f=2500:t=o:w=1.4:g=-3.5,highshelf=f=5500:g=3,alimiter=limit=0.89", "-ar", "48000", dst)
    return dst.name


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--voice", default="voxcpm"); a = ap.parse_args()
    script = json.loads((ROOT / "script.json").read_text())
    for d in ("vo", "clips", "broll"):
        (PUB / d).mkdir(parents=True, exist_ok=True)

    lines = {}
    for ln in script["lines"]:
        src = ROOT / "out" / "tts" / a.voice / f"{ln['id']}.wav"
        dst = PUB / "vo" / f"{ln['id']}.wav"
        # one shared gain for every line, gentle compression, a soft room. No per-line loudnorm:
        # it lifts quiet lines into a shout.
        ff("-i", src, "-af", "silenceremove=start_periods=1:start_threshold=-50dB,areverse,"
           "silenceremove=start_periods=1:start_threshold=-50dB,areverse,"
           "acompressor=threshold=-24dB:ratio=2:attack=25:release=300,volume=6dB,"
           "aecho=0.85:0.55:70|130:0.10|0.06,alimiter=limit=0.89",
           "-ar", "48000", dst)
        lines[ln["id"]] = {"file": f"vo/{dst.name}", "dur": round(dur(dst), 3), "text": ln["text"]}

    clips = {}
    for n in CUTS:
        src = ROOT / "capture" / "clips" / f"{n}.mp4"
        if src.exists():
            dst = PUB / "clips" / src.name
            if not dst.exists() or dst.stat().st_mtime < src.stat().st_mtime:
                shutil.copy2(src, dst)
            clips[n] = {"file": f"clips/{n}.mp4", "dur": round(dur(dst), 2)}

    broll = {}
    for n in ("s1-sky", "s2-astrolabe", "s3-galaxy", "s4-align"):
        src = ROOT / "out" / PICKS.get(n, f"wan/{n}.mp4")
        dst = PUB / "broll" / f"{n}.mp4"
        if src.exists():
            if not dst.exists() or dst.stat().st_mtime < src.stat().st_mtime:
                shutil.copy2(src, dst)  # raw 16 fps; modal/render.py interpolates to 60 fps remotely
        elif not dst.exists():  # placeholder so drafts render before the GPU job lands
            ff("-f", "lavfi", "-i", "color=c=0x0b0e17:s=1920x1080:r=60:d=5", "-c:v", "libx264", dst)
        broll[n] = {"file": f"broll/{n}.mp4", "dur": round(dur(dst), 2), "placeholder": not src.exists()}

    tools = []
    if DATA and DATA.exists():
        rows = json.loads(DATA.read_text())
        rows = rows if isinstance(rows, list) else rows["repos"]
        by = {r["full_name"]: r for r in rows}
        tools = [{"repo": n, "role": role, "stage": by[n]["lifecycle_stage"], "health": by[n]["health_score"],
                  "license": by[n]["license"] if by[n]["license"] != "NOASSERTION" else "custom",
                  "stars": by[n]["stars"]} for n, role in TOOLS if n in by]

    manifest = {
        "voice": a.voice, "lines": lines, "clips": clips, "broll": broll, "cuts": CUTS, "tools": tools,
        "music": phone_score(),
        # bar-snapped scene lengths from music_cue.py; Promo.tsx uses them so cuts land on the beat
        "cue": ({x["id"]: x["sec"] for x in json.loads(CUE.read_text())["scenes"]}
                if (CUE := ROOT / "out" / "cue.json").exists() else {}),
        "cue_arc": ({x["id"]: x["arc"] for x in json.loads(CUE.read_text())["scenes"]} if CUE.exists() else {}),
        "disclosure": "Narration: AI-generated voice (VoxCPM2). Sky and astrolabe shots: AI-generated (Wan2.2). "
                      "App footage: real screen recording." if a.voice.startswith("voxcpm") else
                      "Narration: AI-generated voice (Chatterbox). Sky and astrolabe shots: AI-generated (Wan2.2). "
                      "App footage: real screen recording.",
    }
    (ROOT / "edit" / "src" / "manifest.json").write_text(json.dumps(manifest, indent=1))
    print(json.dumps({k: (v if k != "lines" else {i: x["dur"] for i, x in v.items()}) for k, v in manifest.items()
                      if k in ("lines", "clips", "broll")}, indent=1))


main()
