"""Renders 'rear-engine-3d': why some sports cars carry the engine at the back (16 s, loops, no voiceover).

World: Three.js scene (scene.js, built from shared/assets/3d-car) rendered as ID/light/depth tiles at 270x480 (30 fps, held x2), reduced to a 135x240 pixel grid, mapped to
a fixed <=40-colour palette with Bayer-dithered ramps and navy outlines (pixpost.py), upscaled exactly 8x nearest. Leader lines are drawn on the same 8 px grid.
The presenter is the main guy rebuilt as a 3D toon figure in the same pass. Text is drawn sharp at 1080x1920 on top
(shared/assets/overlays.py, safe zone 12-62 % height, left 85 % width). Sound: code-synth engine idle + sfx.py cues.
    python render.py frames3d | still <dir> t... | safecheck | cover <png> | video none <out.mp4> [t0 t1]
"""
import json, os, subprocess, sys, types, wave
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..', '..', '..')
sys.path.insert(0, os.path.join(ROOT, 'shared')); sys.path.insert(0, os.path.join(ROOT, 'shared', 'assets', '3d-car'))
import episode as kit
from episode import W, H, RED, YEL, GRN, WHITE
from assets import overlays as ov
from audio import sfx
from pixpost import post, up

OUT = os.path.join(ROOT, 'out', 'rear-engine-3d')
F3D = os.path.join(OUT, 'frames3d')                  # scratch PNG tiles (out/ is git-ignored)
DUR, FPS = 16.0, 60
FPS3 = 30                                            # 3D animates at 30 fps, each frame held twice (pixel-animation cadence)
CUTS = [1.0, 2.0, 3.5, 5.0, 6.5, 8.0, 9.5, 11.0, 12.5, 14.0]
BEATS = [2.0, 5.0, 8.0, 11.0, 14.0]
ORG, TEAL = (255, 150, 60), (120, 220, 210)
Y_, R_ = '#ffd93b', '#ff5a5a'
HEADS = [  # (t0, t1, lines): <= 6 words, >= 2 s each, one highlighted word (or phrase)
    (0.0, 1.8, ((('Why is the engine', None),), (('at the', None), ('BACK?', Y_)))),
    (2.0, 4.8, ((('Weight sits over', None),), (('the', None), ('REAR', Y_), ('wheels', None)))),
    (5.0, 7.8, ((('Can help', None), ('GRIP', Y_)), (('when you accelerate', None),))),
    (8.0, 10.8, ((('But the tail', None),), (('can', None), ('SWING OUT', R_)))),
    (11.0, 13.8, ((('Engineers can', None),), (('TAME', Y_), ('it', None)))),
]
HEAD_Y = 480

_A = {}
def anchors(t):
    if not _A: _A.update(json.load(open(os.path.join(F3D, 'anchors.json'))))
    return _A[str(min(max(int(t * FPS3 + 1e-6), 0), round(DUR * FPS3) - 1))]


def anc(t, name):
    a = anchors(t)[name]; return (a[0], a[1]) if a[2] else None


def shot(t):
    ov.reset()
    n = min(max(int(t * FPS3 + 1e-6), 0), round(DUR * FPS3) - 1)
    return up(post(os.path.join(F3D, f'f_{n}.png'), anchors(t)['_x']))


def overlay(cv, t):
    for t0, t1, lines in HEADS:
        if t0 <= t < t1 + 0.2: ov.headline(cv, t - t0, t1 - t0, lines, y=HEAD_Y, sz=100)
    if t >= 15.78: ov.headline(cv, max(-0.35, t - DUR), HEADS[0][1], HEADS[0][2], y=HEAD_Y, sz=100)   # loop into frame 0
    def follow(name, x0, k=0.5): a = anc(t, name); return x0 if not a else x0 + (a[0] - x0) * k
    ov.pin(cv, t, 0.35, 1.8, 'REAR-ENGINE CAR', anc(t, 'engine' if t < 1 else 'tail'), follow('engine', 560), 760, YEL, grid=8)
    ov.pin(cv, t, 2.45, 4.8, 'ENGINE', anc(t, 'engine'), follow('engine', 300, 0.6), 760, ORG, grid=8)
    ov.pin(cv, t, 2.85, 4.8, 'REAR AXLE', anc(t, 'rear_axle'), follow('rear_axle', 640, 0.6), 940, TEAL, grid=8)
    ov.pin(cv, t, 8.45, 10.8, 'OVERSTEER', anc(t, 'tail'), follow('tail', 600, 0.4), 800, RED, grid=8)
    ov.pin(cv, t, 11.3, 13.8, 'WIDER REAR TYRES', anc(t, 'rear_tyre'), 480, 780, YEL, grid=8)
    ov.pin(cv, t, 12.7, 13.8, 'ELECTRONICS', None, 690, 960, TEAL, sz=54, icon='chip', grid=8)
    ov.poll(cv, t, 14.05, 15.5, 'Front engine or rear engine?', ov.SAFE_CX, 760, 0.9,
            opts=(('FRONT', GRN), ('REAR', YEL)))


CUES = ([(c, 'whoosh', 0.55) for c in CUTS] + [(h[0] + 0.02, 'click', 0.7) for h in HEADS] +
        [(0.37, 'pop', 0.4), (2.47, 'pop', 0.45), (2.87, 'pop', 0.45), (8.47, 'pop', 0.45), (11.32, 'pop', 0.45),
         (12.72, 'pop', 0.45), (14.05, 'ding', 0.45), (2.05, 'hum', 0.35), (8.6, 'screech', 0.18), (15.8, 'click', 0.5)])


def engine(n):
    """Low flat-six style idle: harmonics of the firing frequency + rumble, builds a little on the launch (5-8 s)."""
    tt = np.arange(n) / sfx.SR
    up = np.clip((tt - 5.0) / 2.6, 0, 1) * (tt < 8.2) + np.clip(1 - (tt - 8.2) / 0.6, 0, 1) * (tt >= 8.2) * 0.9
    corner = 0.35 * np.exp(-((tt - 9.6) / 1.2) ** 2)
    f = 39 + 52 * up ** 1.4 + 18 * corner
    ph = 2 * np.pi * np.cumsum(f) / sfx.SR
    x = sum(np.sin(k * ph + 0.3 * k) / k ** 1.1 for k in range(1, 8))
    rng = np.random.default_rng(3); rum = np.convolve(rng.standard_normal(n), np.ones(60) / 60, 'same')
    x = x * (0.75 + 0.25 * np.sin(ph / 3)) + rum * 1.2 * (1 + 0.6 * np.sin(ph))
    return x * (0.25 + 0.3 * up + 0.08 * corner)


def build_audio(_vo, out_wav):
    n = int(sfx.SR * DUR)
    fx = sfx.render(CUES, DUR); eng = engine(n)
    mix = fx / max(1e-9, np.max(np.abs(fx))) + 0.55 * eng / max(1e-9, np.max(np.abs(eng)))
    k = int(sfx.SR * 0.08); mix[:k] *= np.linspace(0, 1, k); mix[-k:] *= np.linspace(1, 0, k)   # click-free loop edges
    mix /= max(1.0, np.max(np.abs(mix)) / 0.95)
    with wave.open(out_wav, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sfx.SR); w.writeframes((mix * 32767).astype('<i2').tobytes())


kit.setup(HERE, [], DUR, DUR, [(-3.0, shot)] + [(b, shot) for b in BEATS], {}, CUES, {}, overlay=overlay, bar_car='yellow',
          gauge=False, loud=-18, crisp=True, end=False, flash=False, tag='corner')
kit.sway = lambda cv, t: cv                          # keep the 3x pixel grid exact
kit.GAR = types.SimpleNamespace(vignette=lambda cv: None)
kit.series_tag = lambda cv, t: ov.tag(cv)
kit.captions = lambda cv, t: None                    # no voiceover: headlines only
kit.credit_img = lambda: None
kit.build_audio = build_audio


def safecheck(step=0.05):
    from PIL import Image
    bad = []
    for i in range(int(DUR / step)):
        kit.frame(round(i * step * FPS)); bad += [(round(i * step, 2), lab, b) for lab, b in ov.violations()]
    print(f'safe zone {ov.SAFE}: {len(bad)} violations'); [print(*b) for b in bad[:20]]
    return not bad


if __name__ == '__main__':
    from PIL import Image
    if sys.argv[1] == 'frames3d':
        subprocess.run(['node', os.path.join(ROOT, 'shared', 'assets', 'pix3d', 'render3d.mjs'), os.path.join(HERE, 'scene.js'), F3D,
                        str(FPS3), '0', str(DUR)] + sys.argv[2:], check=True)
    elif sys.argv[1] == 'safecheck':
        raise SystemExit(0 if safecheck() else 1)
    elif sys.argv[1] == 'cover':
        Image.frombytes('RGB', (W, H), kit.frame(0)).save(sys.argv[2])
    else:
        kit.main()
