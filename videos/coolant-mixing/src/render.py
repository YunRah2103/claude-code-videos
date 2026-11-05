"""coolant-mixing: don't mix coolant types (car stuff, explained; shared/series10 engine, opening: tilt).
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

GREEN, PINK = (60, 200, 110), (236, 90, 150)
HOOK = ((("Don't", None), ('MIX', '#e8343f')), (('coolant types', None),))
KEYCOL = {'mix': RED, 'types.': YEL, 'colour': YEL, 'chemistry.': YEL, 'sludge': RED, 'blocks': RED, 'manual': YEL}


def shot_open(t):
    img = garage(t)
    a = 6 * math.sin(t * 4)
    layer(img, (X.coolant_bottle(0.75, GREEN, 0, t), 9, 330, 860), (X.coolant_bottle(0.75, PINK, 0, t + 1), 9, 760, 860))
    fx.stamp_at(img, max(t, 0.35), 0.3, 'X', 545, 860, s=16)
    return img


def shot_cut(t):
    img = layer(garage(t), (X.coolant_bottle(0.7, GREEN, 0, t), 9, 330, 860), (X.coolant_bottle(0.7, GREEN, 0, t + 1), 9, 760, 860))
    for x, lab in ((330, 'TYPE A'), (760, 'TYPE B')):
        d = ImageDraw.Draw(img); d.text((x, 1200), lab, font=S.X._font(56), fill=(240, 242, 248), anchor='mm', stroke_width=6, stroke_fill=(26, 26, 46))
    cb.pill(img, t, sw(1) + 0.3, 99, 'SAME COLOUR?', (545, 760), (470, 420), *PY)
    return img


def shot_key(t):
    k = io(prog(t, sw(2) + 0.2, 1.6))
    col = tuple(int(a + (b - a) * k) for a, b in zip(GREEN, (130, 110, 60)))
    img = layer(garage(t), (X.coolant_bottle(0.75, col, k, t), 10, 330, 800), (X.hose(t, k), 6, 760, 1000))
    cb.pill(img, t, sw(2) + 0.4, sw(3) - 0.1, 'SLUDGE', (760, 1000), (470, 420), *PR)
    cb.pill(img, t, sw(3), 99, 'CHECK THE MANUAL', (330, 600), (470, 420), *PW)
    return img


CUES = [(0.3, 'stamp', 0.7), (sw(1) + 0.3, 'pop', 0.6), (sw(2) + 0.2, 'slide_down', 0.7), (sw(2) + 0.6, 'poof', 0.6), (sw(3), 'ding', 0.5)]
S.build(HERE, WORDS, HOOK, KEYCOL, 'tilt', (545, 900), (545, 860), (shot_open, shot_cut, shot_key), 2,
        ('Ever topped up with the wrong one?', (('YES', GRN), ('NO', RED)), ov.SAFE_CX + 30, 560, 4), CUES, cut_point=(545, 860), key_point=(760, 1000))

if __name__ == '__main__':
    D.cli()
