"""headlight-yellow: why headlights go yellow (car stuff, explained; shared/series10 engine, opening: zoom-out).
    python render.py still <dir> t... | safecheck | safestill <dir> t... | cover <png> | video <vo.wav> <out.mp4> [t0 t1]"""
import math, os, sys
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared', 'series10'))
import engine as S
from engine import W, H, G, kit, cb, X, fx, up, D, ov, prog, oc, io, lerp

WORDS = kit.load_words(HERE); ST = S.sentences(WORDS)
def sw(n): return WORDS[ST[n]]['s']
RED, YEL, GRN = kit.RED, kit.YEL, ov.GRN
PR = ('#e8343f', '#ffffff', '#a01c26'); PY = ('#ffd23f', '#1a1a2e', '#c9a21c'); PW = ('#ffffff', '#1a1a2e', '#d6d9e2')
def layer(img, *items):
    """items: (sprite, scale, x, y[, anchor]) blitted with the garage rim light."""
    fg = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    for it in items: fx.blit(fg, up(it[0], it[1]), it[2], it[3], anchor=it[4] if len(it) > 4 else 'center')
    img.alpha_composite(G.rim(fg)); return img
def garage(t): return S.stage(t)

from assets.seriesbits import sun
HOOK = ((('Why do headlights', None),), (('go', None), ('YELLOW?', '#ffd23f')))
KEYCOL = {'yellow?': YEL, 'uv': YEL, 'coating.': YEL, 'sunlight': YEL, 'haze': YEL, 'cut': RED, 'polishing': GRN, 'lens': GRN, 'help.': GRN}
LAMP = (560, 820)


def beam(img, k, x, y, w=420):
    fg = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(fg)
    d.polygon([(x, y - 60), (x + w, y - 220 * k), (x + w, y + 220 * k), (x, y + 60)], fill=(255, 244, 190, int(110 * k)))
    img.alpha_composite(fg)


def shot_open(t):
    img = garage(t); layer(img, (X.headlight(0.85), 10, *LAMP))
    fx.sparkles(img, t, LAMP[0], LAMP[1], 700, 400, n=5, seed=3)
    return img


def shot_cut(t):
    img = layer(garage(t), (X.lens_layers(1.0, t), 10, 540, 860), (sun(t), 12, 820, 440))
    cb.pill(img, t, sw(1) + 0.2, 99, 'UV COATING', (300, 760), (420, 420), *PY)
    return img


def uv(t): return lerp(1.0, 0.0, io(prog(t, sw(2), 1.6)))


def shot_key(t):
    img = garage(t)
    if t < sw(3):
        layer(img, (X.lens_layers(uv(t), t), 10, 540, 860), (sun(t), 12, 820, 440))
        for k in range(3): fx.ring(img, (t + k * 0.3) % 0.9, 0, 820, 440, (255, 210, 63), life=0.8, r1=300)
        cb.pill(img, t, sw(2) + 0.2, sw(3) - 0.1, 'SUN + AGE', (540, 760), (420, 420), *PY)
        return img
    haze = 0.9 if t < sw(4) else lerp(0.9, 0.0, io(prog(t, sw(4) + 0.2, 1.2)))
    beam(img, 1.0 - 0.75 * haze, LAMP[0] + 330, LAMP[1])
    layer(img, (X.headlight(haze), 8, LAMP[0] - 120, LAMP[1]))
    if t >= sw(4): fx.sparkles(img, t, LAMP[0] - 120, LAMP[1], 600, 400, n=8, seed=5)
    cb.pill(img, t, sw(3) + 0.2, sw(4) - 0.1, 'LESS LIGHT', (LAMP[0] + 250, LAMP[1]), (420, 420), *PR)
    cb.pill(img, t, sw(4) + 0.1, 99, 'POLISH OR NEW LENS', (LAMP[0] - 120, LAMP[1] - 160), (450, 420), *PY)
    return img


CUES = [(0.0, 'boom', 0.4), (sw(1) + 0.2, 'pop', 0.6), (sw(2) + 0.2, 'hum', 0.5), (sw(3) + 0.2, 'buzzer', 0.4), (sw(4) + 0.2, 'sparkle', 0.8)]
S.build(HERE, WORDS, HOOK, KEYCOL, 'zoom-out', LAMP, LAMP, (shot_open, shot_cut, shot_key), 2,
        ('Have yours gone cloudy?', (('YES', GRN), ('NO', RED)), ov.SAFE_CX, 420, -3), CUES, cut_point=(300, 860), key_point=LAMP, ask_prop=lambda t: (X.headlight(0.5 + 0.45 * math.sin(t * 2.5)), 5))

if __name__ == '__main__':
    D.cli()
