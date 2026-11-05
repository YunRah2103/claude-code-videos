"""ev-one-gear: why electric cars have one gear (car stuff, explained; shared/series10 engine, opening: cut-in).
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
def garage(t): return G.frame(t).convert('RGBA')

from pixanim.car import car
from assets.seriesbits import motor
HOOK = ((('EVs have', None), ('ONE', '#ffd23f'), ('gear', None)),)
KEYCOL = {'one': YEL, 'gear,': YEL, 'simple.': RED, 'full': GRN, 'pulling': GRN, 'standstill.': YEL, 'single': YEL, 'reduction': YEL}


def shot_open(t):
    img = garage(t); x = 560 + 10 * math.sin(t * 2)
    layer(img, (car('blue', int(t * 200) % 360), 9, x, 1560, 'bottom'))
    d = ImageDraw.Draw(img); k = 1 + 0.08 * math.sin(t * 8)
    d.rounded_rectangle((440, 760, 640, 1000), 30, fill=(255, 210, 63), outline=(26, 26, 46), width=10)
    d.text((540, 880), '1', font=X._font(int(180 * k)), fill=(26, 26, 46), anchor='mm')
    return img


def shot_cut(t):
    img = garage(t); X.torque_graph(img, 230, 520, 640, 520, min(1, max(0, (t - sw(1)) / 1.6)))
    cb.pill(img, t, sw(1) + 0.4, 99, 'FULL PULL FROM 0', (240, 600), (470, 400), *PY)
    return img


def shot_key(t):
    img = layer(garage(t), (X.gear_pair(t * 900), 8, 600, 820), (motor(t), 9, 250, 850))
    cb.pill(img, t, sw(2) + 0.2, 99, 'ONE REDUCTION GEAR', (720, 820), (470, 420), *PY)
    return img


CUES = [(0.0, 'thump', 0.7), (0.28, 'thump', 0.6), (0.56, 'thump', 0.6), (sw(1) + 0.2, 'hum', 0.6), (sw(1) + 0.4, 'pop', 0.6), (sw(2), 'whirr', 0.6), (sw(2) + 0.2, 'pop', 0.6)]
S.build(HERE, WORDS, HOOK, KEYCOL, 'cut-in', (540, 900), (540, 880), (shot_open, shot_cut, shot_key), 2,
        ('Would you miss the gearbox?', (('YES', GRN), ('NO', RED)), ov.SAFE_CX, 820, 3), CUES, cut_point=(240, 1000), key_point=(600, 820))

if __name__ == '__main__':
    D.cli()
