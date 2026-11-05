"""Wiring for the looping 'car stuff, explained' dashboard shorts (red-zone, fuel-cap-light, windscreen-glass).

Same kit as videos/speed-limit-deal-3d/src/beats.py: shared/episode.py progress bar + caption chunks + mixer + CLI, with
all text drawn through assets/overlays.py inside the TikTok safe zone (12-62 % height, left 85 % width).
    import dashep as D   (from shared/assets, with shared/ and shared/assets on sys.path via the episode)
    D.wire(HERE, words, dur, end_t, scene, marks, cues, keycol, overlay, cap=(t_from, y[, mute]), gap=(t, d))
    D.cli()   # still <dir> t... | safecheck | safestill <dir> t... | cover <png> | video <vo.wav> <out.mp4> [t0 t1]
The loop: from end_t the shot whips back to the cold-open scene (scene(t - dur)), so the last frame matches frame 0.
"""
import os, sys
from PIL import Image
import episode as kit
from episode import W, H, FPS
from pixanim.motion import prog, io
from pixanim import transitions as T
from assets import overlays as ov

CFG = {}


def loop_shot(scene, dur, end_t):
    def shot(t):
        ov.reset()
        if t >= end_t:
            e = io(prog(t, end_t, 0.26))
            return scene(t - dur) if e >= 1 else T.whip(scene(end_t - 0.01), scene(t - dur), e, dx=-1)
        return scene(t)
    return shot


def wire(here, words, dur, end_t, scene, marks, cues, keycol, overlay, cap=(0.0, 1075), gap=None, bar_car='red', lufs=-16):
    shot = loop_shot(scene, dur, end_t)
    CFG.update(dur=dur, end_t=end_t, cap=cap)
    kit.setup(here, words, dur, end_t, [(-3.0, shot)] + [(m, shot) for m in marks], {}, cues, keycol, overlay=overlay,
              bar_car=bar_car, gauge=False, loud=lufs, gap=gap, crisp=True, end=False, flash=False, tag='corner')
    kit.sway = lambda cv, t: cv                       # no handheld resample: keeps the pixel grid exact
    kit.series_tag = lambda cv, t: ov.tag(cv)
    kit.captions = captions
    kit.credit_img = lambda: None


def captions(cv, t):
    """Spoken-word captions; none while the headline already shows the same words (before cap[0]), inside the optional
    mute windows cap[2] (a callout already shows those words) or after end_t."""
    t0, y = CFG['cap'][:2]
    if any(a <= t < b for a, b in (CFG['cap'][2] if len(CFG['cap']) > 2 else ())): return
    if t0 <= t < CFG['end_t']: ov.captions(cv, t, y)


def safecheck(step=0.05):
    bad = []
    for i in range(int(CFG['dur'] / step)):
        kit.frame(round(i * step * FPS))
        bad += [(round(i * step, 2), lab, b) for lab, b in ov.violations()]
    print(f'safe zone {ov.SAFE}: {len(bad)} violations'); [print(*b) for b in bad[:20]]
    return not bad


def cli():
    a = sys.argv[1:]
    if a[0] == 'safecheck': raise SystemExit(0 if safecheck() else 1)
    if a[0] == 'cover':
        Image.frombytes('RGB', (W, H), kit.frame(0)).save(a[1]); return
    if a[0] == 'safestill':
        os.makedirs(a[1], exist_ok=True)
        for ts in a[2:]:
            im = Image.frombytes('RGB', (W, H), kit.frame(round(float(ts) * FPS))).convert('RGBA'); ov.draw_safe(im)
            im.convert('RGB').save(f'{a[1]}/safe_{ts}.png')
        return
    kit.main()


def camera(img, t, z=1.0, cx=W / 2, cy=H / 2, sh=0.0):
    """Push-in / shake on a full-res world image: crop + NEAREST resize, so the pixel grid stays hard."""
    import math
    w, h = W / z, H / z
    ox, oy = sh * math.sin(t * 13), sh * math.cos(t * 11)   # slow handheld drift: a frame-0 loop seam stays small
    x0 = min(max(cx - w * (cx / W) + ox, 0), W - w); y0 = min(max(cy - h * (cy / H) + oy, 0), H - h)
    return img.crop((round(x0), round(y0), round(x0 + w), round(y0 + h))).resize((W, H), Image.NEAREST)


def sequence(shots, whip=0.22):
    """shots = [(t_start, fn(t) -> RGB image), ...]; whips from one shot into the next over `whip` s at each start."""
    def scene(t):
        i = max([k for k, (s, _) in enumerate(shots) if t >= s] or [0])
        s, fn = shots[i]
        if i and t < s + whip:
            return T.whip(shots[i - 1][1](t), fn(t), io(prog(t, s, whip)), dx=1 if i % 2 else -1)
        return fn(t)
    return scene
