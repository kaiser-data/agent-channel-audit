"""Stage narration for the research explainer and write edit/src/manifest.json.

  python3 prep_explainer.py [--voice <dir under out/tts>]
Lines without a rendered take get an estimated length (140 wpm) so drafts and stills work early.
One shared gain + gentle compression for all lines (no per-line loudnorm).
"""
import argparse
import json
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parent
PUB = ROOT / "edit" / "public"


def dur(p):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                          "-of", "csv=p=0", str(p)]).decode().strip())


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--voice", default=""); a = ap.parse_args()
    script = json.loads((ROOT / "script.json").read_text())
    (PUB / "vo").mkdir(parents=True, exist_ok=True)
    lines = {}
    for ln in script["lines"]:
        src = ROOT / "out" / "tts" / a.voice / f"{ln['id']}.wav"
        dst = PUB / "vo" / f"{ln['id']}.wav"
        if a.voice and src.exists():
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-af",
                            "silenceremove=start_periods=1:start_threshold=-50dB,areverse,"
                            "silenceremove=start_periods=1:start_threshold=-50dB,areverse,"
                            "acompressor=threshold=-24dB:ratio=2:attack=25:release=300,volume=6dB,alimiter=limit=0.89",
                            "-ar", "48000", str(dst)], check=True)
            lines[ln["id"]] = {"file": f"vo/{dst.name}", "dur": round(dur(dst), 3), "text": ln["text"]}
        else:
            lines[ln["id"]] = {"file": None, "dur": round(len(ln["text"].split()) / 140 * 60, 2), "text": ln["text"]}
    model = {"": "none yet"}.get(a.voice, "Qwen3-TTS")
    manifest = {"voice": a.voice, "lines": lines,
                "disclosure": f"Narration: AI-generated voice ({model}). Figures, numbers and graphs: from the study's "
                              "own data and code. No AI-generated imagery."}
    (ROOT / "edit" / "src" / "manifest.json").write_text(json.dumps(manifest, indent=1))
    print({k: v["dur"] for k, v in lines.items()}, "total", round(sum(v["dur"] for v in lines.values()), 1))


main()
