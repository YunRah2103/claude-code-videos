"""Renders 'speed-limit-deal' (3D version): the German 155 mph gentleman's agreement as a 3D pixel short.

Shared with the 2D version (videos/speed-limit-deal-2d): script, voiceover, words.json, beats/text/sound (beats.py).
The world is a Three.js scene (scene3d.js, built from shared/assets/pix3d) rendered at 270x480 in Chromium, no AA,
upscaled 4x nearest; headline, captions, chips, stamp, poll, tag and progress bar are drawn sharp at 1080x1920 on top
(shared/assets/overlays.py). The presenter is the 2D pixel sprite as a flat billboard pinned to a 3D floor point.
    python render.py frames3d [step] | still <dir> t... | safecheck | safestill <dir> t... | video <vo.wav> <out.mp4> [t0 t1]
"""
import json, os, subprocess, sys
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..', '..', '..')
sys.path.insert(0, HERE)
import beats as B
import episode as kit
from episode import W, H
from assets import overlays as ov

OUT = os.path.join(ROOT, 'out', 'speed-limit-deal-3d')
F3D = os.path.join(OUT, 'frames3d')
DUR, FPS = B.DUR, B.FPS

_A = {}
def anchor(name, t):
    if not _A: _A.update(json.load(open(os.path.join(F3D, 'anchors.json'))))
    a = _A.get(str(min(max(round(t * FPS), 0), round(DUR * FPS) - 1)))
    return tuple(a[name][:2]) if a else (W / 2, H / 2)


P = B.presenter(anchor)


def shot(t):
    """One continuous 3D take (the beat changes are camera moves inside scene3d.js): load + upscale, then the presenter."""
    ov.reset()
    n = min(max(round(t * FPS), 0), round(DUR * FPS) - 1)
    img = ov.upscale(os.path.join(F3D, f'f_{n}.png')).convert('RGBA')
    if P.get('visible', t, True): P.draw(img, t)
    return img.convert('RGB')


B.setup(HERE, shot, anchor, 'silver')

if __name__ == '__main__':
    if sys.argv[1] == 'frames3d':
        subprocess.run(['node', os.path.join(ROOT, 'shared', 'assets', 'pix3d', 'render3d.mjs'), os.path.join(HERE, 'scene3d.js'), F3D,
                        str(FPS), '0', str(DUR)] + sys.argv[2:], check=True)
    elif sys.argv[1] == 'safecheck':
        raise SystemExit(0 if B.safecheck() else 1)
    elif sys.argv[1] == 'safestill':
        os.makedirs(sys.argv[2], exist_ok=True)
        for ts in sys.argv[3:]:
            im = Image.frombytes('RGB', (W, H), kit.frame(round(float(ts) * FPS))).convert('RGBA'); ov.draw_safe(im)
            im.convert('RGB').save(f'{sys.argv[2]}/safe_{ts}.png')
    else:
        kit.main()
