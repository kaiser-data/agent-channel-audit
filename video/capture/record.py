"""Record real app footage from the live site, one webm per scene, 1920x1080.

  python3 capture/record.py            # all scenes
  python3 capture/record.py map,risk   # subset
Each scene: open page, wait until ready, then perform a slow scripted interaction.
Output: capture/clips/<scene>.webm (first ~1.5s of load is trimmed later in the edit).
"""
import asyncio
import pathlib
import sys

from playwright.async_api import async_playwright

BASE = "https://star-astrolab.vercel.app"
OUT = pathlib.Path(__file__).parent / "clips"
VW, VH = 1920, 1080


async def smooth_scroll(pg, dy, ms):
    steps = max(1, ms // 16)
    for _ in range(steps):
        await pg.mouse.wheel(0, dy / steps)
        await pg.wait_for_timeout(16)


async def glide(pg, x0, y0, x1, y1, ms):
    steps = max(1, ms // 16)
    for i in range(steps + 1):
        t = i / steps
        e = t * t * (3 - 2 * t)
        await pg.mouse.move(x0 + (x1 - x0) * e, y0 + (y1 - y0) * e)
        await pg.wait_for_timeout(16)


# --- manual / tutorial helpers -------------------------------------------------------------
# A CDP screencast does not contain the mouse pointer. For a how-to film inject a visible
# pointer that follows the real mouse and pulses on every click (add_init_script(CURSOR_JS)).
CURSOR_JS = """
document.addEventListener('DOMContentLoaded', () => {
  const c = document.createElement('div');
  c.style.cssText = 'position:fixed;left:0;top:0;width:26px;height:26px;margin:-13px 0 0 -13px;border-radius:50%;'
    + 'background:rgba(17,24,39,.55);border:3px solid #fff;box-shadow:0 2px 10px rgba(0,0,0,.35);'
    + 'z-index:2147483647;pointer-events:none;transition:transform .15s ease;transform:translate(-100px,-100px)';
  document.body.appendChild(c);
  let x = -100, y = -100, s = 1;
  const paint = () => { c.style.transform = `translate(${x}px,${y}px) scale(${s})`; };
  addEventListener('mousemove', e => { x = e.clientX; y = e.clientY; paint(); }, true);
  addEventListener('mousedown', () => {
    s = 0.7; paint();
    const r = document.createElement('div');
    r.style.cssText = `position:fixed;left:${x}px;top:${y}px;width:20px;height:20px;margin:-10px 0 0 -10px;border-radius:50%;`
      + 'border:4px solid #2563eb;z-index:2147483646;pointer-events:none;transition:all .6s ease-out;opacity:1';
    document.body.appendChild(r);
    requestAnimationFrame(() => { r.style.transform = 'scale(4)'; r.style.opacity = '0'; });
    setTimeout(() => r.remove(), 700);
  }, true);
  addEventListener('mouseup', () => { s = 1; paint(); }, true);
});
"""
# Hide UI that must not be filmed (settings with keys, internal banners) with CSS, never blur later.
HIDE_CSS = ""
SHOW_CURSOR = True  # manuals: yes; a promo with no clicks may set False

import json
import time
MARKS: list = []


def mark(name):
    """Timestamp an event; record() writes clips/<scene>.marks.json in seconds from the first frame.
    Scripted moves drift 2-4x, so set CUTS from these marks instead of from the plan."""
    MARKS.append((name, time.time()))


async def glide_to(pg, sel, ms=900, frm=(960, 540)):
    b = await pg.locator(sel).first.bounding_box()
    await glide(pg, frm[0], frm[1], b["x"] + b["width"] / 2, b["y"] + b["height"] / 2, ms)
    return (b["x"] + b["width"] / 2, b["y"] + b["height"] / 2)


async def scroll_to(pg, sel, ms=1800, top=140):
    """Wheel-scroll until sel sits `top` px below the viewport top (works for inner scrollers too)."""
    b = await pg.locator(sel).first.bounding_box()
    await smooth_scroll(pg, b["y"] - top, ms)


async def jump(pg, text, top=70, tag="h1,h2,h3,td,strong"):
    """Instant jump so the element starting with `text` sits `top` CSS px below the viewport top.
    Re-measures until late-loading images stop shifting the layout; the cut in the edit hides the jump."""
    js = """([t, tags]) => { const e=[...document.querySelectorAll(tags)].find(x=>x.textContent.trim().startsWith(t));
        return e ? e.getBoundingClientRect().top + window.scrollY : null; }"""
    y = await pg.evaluate(js, [text, tag])
    assert y is not None, f"not found: {text}"
    for _ in range(3):
        await pg.evaluate(f"window.scrollTo({{top: {y - top}, behavior: 'instant'}})")
        await pg.wait_for_timeout(500)
        y2 = await pg.evaluate(js, [text, tag])
        if abs(y2 - y) < 2:
            break
        y = y2


async def scene_landing(pg):
    await pg.goto(BASE + "/", wait_until="networkidle")
    await pg.wait_for_timeout(2500)
    await glide(pg, 300, 900, 960, 560, 1800)
    await pg.wait_for_timeout(800)
    await smooth_scroll(pg, 520, 3000)
    await pg.wait_for_timeout(1500)


async def scene_map(pg):
    await pg.goto(BASE + "/lab?tab=map", wait_until="networkidle")
    await pg.wait_for_timeout(2500)
    # bring the canvas to the top of the viewport so the graph fills the frame
    await pg.evaluate("window.scrollTo({top: 375, behavior: 'instant'})")
    await pg.wait_for_timeout(400)
    cx, cy = 640, 480
    await pg.mouse.move(cx, cy)
    await smooth_scroll(pg, -1400, 2200)     # zoom in toward the cluster
    await pg.wait_for_timeout(300)
    # slow orbit: left-drag
    await pg.mouse.down()
    await glide(pg, cx, cy, cx + 520, cy + 60, 4200)
    await pg.mouse.up()
    await pg.wait_for_timeout(300)
    await smooth_scroll(pg, -500, 1500)
    await pg.mouse.down()
    await glide(pg, cx + 100, cy, cx - 250, cy - 80, 3500)
    await pg.mouse.up()
    await pg.wait_for_timeout(800)


async def scene_risk(pg):
    await pg.goto(BASE + "/lab?tab=risk", wait_until="networkidle")
    await pg.wait_for_timeout(2500)
    await smooth_scroll(pg, 420, 2000)
    await pg.wait_for_timeout(500)
    await glide(pg, 1500, 700, 520, 560, 3500)   # sweep across into the low-health zone
    await pg.wait_for_timeout(1500)


async def scene_reports(pg):
    await pg.goto(BASE + "/lab?tab=reports", wait_until="networkidle")
    await pg.wait_for_timeout(2500)
    await smooth_scroll(pg, 360, 1600)
    await glide(pg, 300, 500, 960, 420, 1500)
    await pg.wait_for_timeout(600)
    # open the "Trending Now" or first report card
    card = pg.locator("text=Charting & Data-Visualization Tools").first
    if await card.count():
        box = await card.bounding_box()
        if box:
            await glide(pg, 960, 420, box["x"] + 80, box["y"] + 10, 900)
        await card.click()
        await pg.wait_for_timeout(2500)
        await smooth_scroll(pg, 1600, 5000)
    await pg.wait_for_timeout(1000)


async def scene_ask(pg):
    await pg.goto(BASE + "/lab?tab=ask", wait_until="networkidle")
    await pg.wait_for_timeout(2000)
    await pg.evaluate("window.scrollTo({top: 330, behavior: 'instant'})")
    chip = pg.get_by_text("Which repos are at risk of being abandoned but still get attention?").first
    b = await chip.bounding_box()
    await glide(pg, 900, 300, b["x"] + 120, b["y"] + 12, 1400)
    await pg.wait_for_timeout(400)
    await chip.click()
    await pg.wait_for_timeout(300)
    await pg.wait_for_timeout(2500)
    # follow the answer as it streams in below the suggestion chips
    await pg.mouse.move(700, 700)
    await smooth_scroll(pg, 700, 2500)
    await pg.wait_for_timeout(1500)
    await smooth_scroll(pg, 900, 6000)
    await pg.wait_for_timeout(1500)
    print("ANSWER:", (await pg.inner_text("body"))[-1500:].replace("\n", " | "))


SCENES = {"landing": scene_landing, "map": scene_map, "risk": scene_risk,
          "reports": scene_reports, "ask": scene_ask}


async def record(p, name):
    """CDP screencast at JPEG q95 -> timestamped frames -> constant-30fps H.264 via ffmpeg concat."""
    import base64
    import shutil
    import subprocess

    fdir = OUT / "_frames" / name
    shutil.rmtree(fdir, ignore_errors=True); fdir.mkdir(parents=True)
    b = await p.chromium.launch(channel="chromium",
                                args=["--use-gl=angle", "--enable-webgl", "--ignore-gpu-blocklist"])
    # 1200x675 CSS at 1.6x = 1920x1080 frames with 1.6x larger text (tables stay readable on a phone)
    ctx = await b.new_context(viewport={"width": 1200, "height": 675}, device_scale_factor=1.6,
                              color_scheme="dark", accept_downloads=True)
    MARKS.clear()
    if SHOW_CURSOR:
        await ctx.add_init_script(CURSOR_JS)
    if HIDE_CSS:
        await ctx.add_init_script("document.addEventListener('DOMContentLoaded',()=>{const s=document.createElement('style');"
                                  "s.textContent=%r;document.head.appendChild(s)})" % HIDE_CSS)
    await ctx.grant_permissions(["clipboard-read", "clipboard-write"], origin=BASE)  # copy buttons
    pg = await ctx.new_page()
    pg.on("dialog", lambda d: asyncio.ensure_future(d.accept()))
    cdp = await ctx.new_cdp_session(pg)
    frames: list[tuple[float, pathlib.Path]] = []

    async def on_frame(ev):
        f = fdir / f"{len(frames):06d}.jpg"
        f.write_bytes(base64.b64decode(ev["data"]))
        frames.append((ev["metadata"]["timestamp"], f))
        try:
            await cdp.send("Page.screencastFrameAck", {"sessionId": ev["sessionId"]})
        except Exception:
            pass

    cdp.on("Page.screencastFrame", lambda ev: asyncio.ensure_future(on_frame(ev)))
    await cdp.send("Page.startScreencast", {"format": "jpeg", "quality": 95,
                                            "maxWidth": VW, "maxHeight": VH, "everyNthFrame": 1})
    await SCENES[name](pg)
    await pg.wait_for_timeout(300)
    await cdp.send("Page.stopScreencast")
    await b.close()

    frames.sort()
    lst = fdir / "list.txt"
    with lst.open("w") as fh:
        for (t, f), (t2, _) in zip(frames, frames[1:] + [(frames[-1][0] + 1 / 30, None)]):
            fh.write(f"file '{f.name}'\nduration {max(t2 - t, 1 / 60):.4f}\n")
        fh.write(f"file '{frames[-1][1].name}'\n")
    dst = OUT / f"{name}.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst),
                    "-vf", f"fps=30,scale={VW}:{VH}:flags=lanczos,format=yuv420p",
                    "-c:v", "libx264", "-crf", "14", "-preset", "slow", str(dst)], check=True)
    span = frames[-1][0] - frames[0][0]
    (OUT / f"{name}.marks.json").write_text(json.dumps({k: round(t - frames[0][0], 2) for k, t in MARKS}))
    shutil.rmtree(fdir, ignore_errors=True)  # frames are encoded; free the disk now
    print(f"recorded {dst} frames={len(frames)} span={span:.1f}s")


async def main():
    names = sys.argv[1].split(",") if len(sys.argv) > 1 else list(SCENES)
    async with async_playwright() as p:
        for n in names:
            await record(p, n)


asyncio.run(main())
