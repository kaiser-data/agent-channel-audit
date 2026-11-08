"""Score with ACE-Step 1.5 on Modal: instrumental bed scored to the cut, several seeds.

  modal run modal/music.py --dry-run                     # wave 0: CPU, build image, import, show downloader API
  python3 music_cue.py cue                               # lock the edit first: bpm, bar-snapped scenes, length
  modal run modal/music.py --cue out/cue.json            # 4 takes at the cue's bpm, length and section arc
  python3 music_cue.py fit out/music/take-*.wav --apply  # rank, back-time, stage (never time-stretch)

Score the locked cut, not a draft: re-run cue + music whenever the script or a voice take changes length.
Section tags go in the lyrics field ([Intro - sparse] ... [Outro - final chord]); tempo and key go in the
bpm/keyscale params, never in the caption (ACE-Step 1.5 tutorial).
"""
import json
import pathlib
import time

import modal

ROOT = pathlib.Path(__file__).resolve().parent.parent
app = modal.App("astrolab-promo-music")
ckpt = modal.Volume.from_name("acestep-checkpoints", create_if_missing=True)

image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("git", "ffmpeg", "libsndfile1")
    .run_commands("git clone --depth 1 https://github.com/ace-step/ACE-Step-1.5 /opt/ace",
                  "pip install uv", "cd /opt/ace && uv pip install --system -e .")
    .env({"HF_HOME": "/opt/ace/checkpoints/hf"})
)

CAPTIONS = {
    # default for narrated product films: the music is a bed under a voice, so it must leave the
    # 1-4 kHz speech band and the rhythm of speech alone - no lead melody, no busy arpeggios.
    "underscore": ("Warm, unhurried instrumental underscore for a narrated product film. Soft electric piano "
                   "chords, warm analog pads, round sub bass, light brushed percussion with a gentle steady pulse, "
                   "a simple four-note motif that returns. Sparse and open in the midrange, leaves room for a "
                   "speaking voice, no lead melody over the narration, no busy arpeggios, no risers, no vocals, no vocal chops or chopped voice samples, no house beat. "
                   "Quietly confident and optimistic, clean modern production."),
    "build": ("Epic cinematic trailer score, instrumental. Opens hushed and mysterious under a night sky: "
              "soft felt piano and shimmering celesta. Then a pulsing low string ostinato starts, a deep heartbeat "
              "drum enters, brass and choir swell in layers, tension rising steadily like something big is about "
              "to arrive. Builds to a powerful, luminous, triumphant crescendo near the end, then a final "
              "ringing chord. Wonder and anticipation, not aggression. No vocals, no lyrics."),
}
CAPTION = ("Cinematic ambient instrumental score for a film about the night sky. Slow and mysterious, "
           "full of wonder and curiosity. Felt piano motif, soft celesta and glassy bell tones, warm analog "
           "synth pads, distant wordless choir, gentle strings that swell slowly, shimmering reverb. "
           "No drums, no vocals, no percussion. Builds very gently and resolves on a luminous final chord.")


@app.function(image=image, volumes={"/opt/ace/checkpoints": ckpt}, timeout=900)
def check() -> str:
    import inspect

    import acestep.inference as inf
    from acestep import model_downloader as md
    from acestep.llm_inference import LLMHandler
    fns = [n for n, o in inspect.getmembers(md, inspect.isfunction) if not n.startswith("_")]
    return (f"generate_music{inspect.signature(inf.generate_music)}\n"
            f"LLMHandler.initialize{inspect.signature(LLMHandler.initialize)}\n"
            f"model_downloader: {fns}")


@app.function(image=image, gpu="L40S", volumes={"/opt/ace/checkpoints": ckpt}, timeout=1800)
def score(duration: float, takes: int, caption: str = "", bpm: int = 68, lyrics: str = "[Instrumental]",
          key: str = "D major", seed0: int = 1000) -> dict:
    import os

    from acestep.handler import AceStepHandler
    from acestep.inference import GenerationConfig, GenerationParams, generate_music
    from acestep.llm_inference import LLMHandler

    t0 = time.time()
    dit = AceStepHandler()
    msg, ok = dit.initialize_service(project_root="/opt/ace", config_path="acestep-v15-turbo",
                                     device="cuda", offload_to_cpu=False)
    assert ok, msg
    llm = LLMHandler()
    msg, ok = llm.initialize(checkpoint_dir="/opt/ace/checkpoints", lm_model_path="acestep-5Hz-lm-1.7B",
                             backend="pt", device="cuda", offload_to_cpu=False, dtype=None)
    assert ok, msg
    ckpt.commit()
    out = {}
    for k in range(takes):
        params = GenerationParams(task_type="text2music", caption=caption or CAPTION, lyrics=lyrics,
                                  instrumental=True, bpm=bpm, keyscale=key, timesignature="4",
                                  duration=duration, inference_steps=8, guidance_scale=1.0, seed=seed0 + k,
                                  fade_in_duration=0.5, fade_out_duration=2.5)  # let the take's own ending ring
        res = generate_music(dit, llm, params=params, config=GenerationConfig(batch_size=1, audio_format="wav"),
                             save_dir=f"/tmp/take{k}")
        assert res.success, res.status_message
        path = res.audios[0]["path"]
        out[f"take-{k}"] = pathlib.Path(path).read_bytes()
        os.remove(path)
    return {"wavs": out, "seconds": round(time.time() - t0, 1)}


TAGS = {"intro": "[Intro - sparse, soft]", "main": "[Main Theme - gentle pulse]",
        "lift": "[Build - fuller, rising]", "outro": "[Outro - resolve, final chord]"}


def cue_lyrics(cue: dict) -> str:
    """One section tag per run of scenes with the same role, so the arc follows the edit."""
    tags, prev = [], None
    for s in cue["scenes"]:
        if s["arc"] != prev:
            tags.append(TAGS[s["arc"]]); prev = s["arc"]
    return "\n\n".join(tags)


@app.local_entrypoint()
def main(dry_run: bool = False, duration: float = 64.0, takes: int = 4, style: str = "underscore", bpm: int = 0,
         cue: str = "", key: str = "D major", seed: int = 1000):
    if dry_run:
        print(check.remote()); return
    lyrics = "[Instrumental]"
    if cue:
        c = json.loads((ROOT / cue).read_text() if not pathlib.Path(cue).is_absolute() else pathlib.Path(cue).read_text())
        duration = c["total_sec"] + 4 * c["bar_sec"] + 4  # ACE-Step often ends ~10 s early: generous headroom; fit back-times it
        bpm = bpm or c["bpm"]
        lyrics = cue_lyrics(c)
    bpm = bpm or 84
    dest = ROOT / "out" / ((f"music-{style}" if style else "music") + (f"-s{seed}" if seed != 1000 else "")); dest.mkdir(parents=True, exist_ok=True)
    print(f"{takes} takes, {duration:.1f} s, {bpm} bpm, {key}, style {style}, sections: {lyrics!r}")
    res = score.remote(duration, takes, CAPTIONS.get(style, ""), bpm, lyrics, key, seed)
    for k, b in res["wavs"].items():
        (dest / f"{k}.wav").write_bytes(b)
    rec = {"job": "music", "model": "ACE-Step-1.5 turbo", "gpu": "L40S", "takes": takes, "bpm": bpm,
           "duration": duration, "style": style,
           "seconds": res["seconds"], "ts": time.time()}
    with (ROOT / "out" / "runs.jsonl").open("a") as f: f.write(json.dumps(rec) + "\n")
    print(rec)
