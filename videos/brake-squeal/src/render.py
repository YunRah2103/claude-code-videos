"""brake-squeal: That squeal from your brakes (car stuff, explained; shared/series10 engine, opening: whip-pan).
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

from pixanim.car import car
HOOK = ((('That brake', None), ('SQUEAL', '#e8343f')), (('might be a warning', None),))
KEYCOL = {'squeal': RED, 'warning.': YEL, 'tab.': YEL, 'thin,': RED, 'scrapes': RED, 'noise.': YEL}


def shot_open(t):
    img = garage(t); stop = oc(prog(t, -0.25, 1.15)); x = lerp(-450, 600, stop)
    layer(img, (car('red', int(x * 0.9) % 360, brake=True), 9, x, 1560, 'bottom'))
    for k in range(3): fx.ring(img, (t + k * 0.22) % 0.66, 0, x + 212, 1470, (255, 210, 63), life=0.6, r1=230)
    return img


def shot_cut(t):
    img = layer(garage(t), (X.pad_section(0.3, t), 11, 560, 760))
    tx, ty = X.PAD_TAB(0.3)
    cb.pill(img, t, sw(1) + 0.3, 99, 'WEAR TAB', (560 - 385 + tx * 11, 760 - 440 + ty * 11 + 22), (470, 420), *PY)
    return img


def wear(t): return lerp(0.3, 1.0, io(prog(t, sw(2), 1.4)))


def shot_key(t):
    w = wear(t); img = layer(garage(t), (X.pad_section(w, t), 11, 560, 760))
    tx, ty = X.PAD_TAB(w); px, py = 560 - 385 + tx * 11, 760 - 440 + ty * 11 + 22
    if tx <= 17:
        fx.burst(img, (t * 9) % 1 / 9 + 0.0, 0, px, py, (255, 210, 63), n=10, life=0.11, r0=20, r1=140)
        fx.ring(img, (t * 3) % 0.33, 0, px, py, (255, 210, 63), life=0.3, r1=200)
    cb.pill(img, t, sw(2) + 1.3, sw(3) - 0.1, 'SCRAPE = SQUEAL', (px, py), (470, 420), *PR)
    cb.pill(img, t, sw(3), 99, 'MADE TO BE HEARD', (px, py), (470, 420), *PY)
    return img


CUES = [(0.05, 'screech', 0.5), (0.4, 'scrape', 0.5), (sw(1) + 0.3, 'pop', 0.6), (sw(2) + 1.3, 'scrape', 1.0), (sw(2) + 2.0, 'scrape', 0.8), (sw(3), 'ding', 0.5)]
S.build(HERE, WORDS, HOOK, KEYCOL, 'whip-pan', (560, 1200), (760, 1460), (shot_open, shot_cut, shot_key), 2,
        ('Have you heard yours?', (('YES', GRN), ('NO', RED)), ov.SAFE_CX + 10, 520, 3), CUES, cut_point=(470, 1050), key_point=(470, 1050), ask_prop=lambda t: (X.pad_section(1.0, t), 5))

if __name__ == '__main__':
    D.cli()
