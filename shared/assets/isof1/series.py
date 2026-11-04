"""Wiring for a looping isometric-F1 short (f1-downforce series) on top of shared/episode.py:
progress bar + mixer + 60 fps H.264/AAC from the kit, no running captions (one headline at a time instead),
no series tag (the lap HUD owns the top-left), a loop window that crossfades the last frames into frame 0,
and a TikTok safe-zone check of every text element.
    python render.py still <dir> t... | safecheck | cover <png> | video <voiceover.wav> <out.mp4> [t0 t1]
"""
import os, sys
from PIL import Image
import episode as kit
from episode import W, H
from assets import overlays as ov
from pixanim.motion import prog, io

S = {}


def setup(here, words, dur, end_t, world, overlay, cues, marks, bar_car='blue', fps=60):
    """world(t) -> 1080x1920 RGB PIL image; overlay(cv, t) draws HUD/text/presenter (t may be negative in the loop)."""
    S.update(dur=dur, end_t=end_t, world=world, overlay=overlay, fps=fps)

    def picture(t):
        ov.reset()
        if t < end_t: return world(t)
        e = io(prog(t, end_t, dur - end_t - 1.5 / fps))                 # crossfade into the cold open (frame 0)
        b = world(t - dur)
        return b if e >= 1 else Image.blend(world(end_t - 1e-3), b, e)

    def over(cv, t):
        overlay(cv, t if t < end_t else t - dur)

    kit.setup(here, words, dur, end_t, [(-3.0, picture)] + [(m, picture) for m in marks], {}, cues, {},
              overlay=over, bar_car=bar_car, gauge=False, loud=True, crisp=True, end=False, flash=False, tag='corner')
    kit.sway = lambda cv, t: cv
    kit.series_tag = lambda cv, t: None
    kit.captions = lambda cv, t: None
    kit.credit_img = lambda: None


def safecheck(step=0.05):
    bad = []
    for i in range(int(S['dur'] / step)):
        kit.frame(round(i * step * S['fps']))
        bad += [(round(i * step, 2), lab, b) for lab, b in ov.violations()]
    print(f'safe zone {ov.SAFE}: {len(bad)} violations'); [print(*b) for b in bad[:20]]
    return not bad


def main():
    if sys.argv[1] == 'safecheck':
        raise SystemExit(0 if safecheck() else 1)
    if sys.argv[1] == 'cover':
        Image.frombytes('RGB', (W, H), kit.frame(0)).save(sys.argv[2]); return
    if sys.argv[1] == 'safestill':
        os.makedirs(sys.argv[2], exist_ok=True)
        for ts in sys.argv[3:]:
            im = Image.frombytes('RGB', (W, H), kit.frame(round(float(ts) * S['fps']))).convert('RGBA'); ov.draw_safe(im)
            im.convert('RGB').save(f'{sys.argv[2]}/safe_{ts}.png')
        return
    kit.main()
