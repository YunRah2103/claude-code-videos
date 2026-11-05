"""wheel-nut-order: the order you tighten wheel nuts (car stuff, explained; shared/series10 engine, opening: wipe).
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

HOOK = ((('Wheel nut', None), ('ORDER', '#ffd23f')), (('matters', None),))
KEYCOL = {'order': YEL, 'matters.': YEL, 'circle.': RED, 'star': YEL, 'flat.': GRN, 'torque': YEL, 'manual.': YEL}
HUB = (560, 820); SC = 12


def hub(img, t, done=0, hi=-1, rot=0):
    fg = Image.new('RGBA', (W, H), (0, 0, 0, 0)); fx.blit(fg, up(X.wheel_hub(done, hi), SC), HUB[0], HUB[1], rot=rot, anchor='center')
    img.alpha_composite(G.rim(fg))


def shot_open(t):
    img = garage(t); hub(img, t, hi=X.STAR[5][int(t * 5) % 5], rot=150 * (1 - oc(prog(t, -0.4, 1.4))))
    return img


def shot_cut(t):
    img = garage(t); hub(img, t)
    X.circle_lines(img, *HUB, 17 * SC, (t - sw(1)) * 4)
    if t > sw(1) + 1.0: fx.stamp_at(img, t, sw(1) + 1.0, 'NO', HUB[0], HUB[1], s=14)
    cb.pill(img, t, sw(1) + 0.1, 99, 'NOT ROUND THE CIRCLE', (HUB[0], HUB[1] - 17 * SC), (470, 400), *PR)
    return img


def k_star(t): return max(0.0, (t - sw(2) - 0.2) * 2.6)


def shot_key(t):
    img = garage(t); k = k_star(t); done = min(5, int(k + 0.5))
    hub(img, t, done, X.STAR[5][min(4, int(k))] if k < 4.6 else -1)
    X.star_lines(img, *HUB, 17 * SC, k)
    cb.pill(img, t, sw(2) + 0.3, sw(3) - 0.1, 'STAR PATTERN', (HUB[0], HUB[1] - 17 * SC), (470, 400), *PY)
    cb.pill(img, t, sw(3), 99, 'TORQUE: SEE MANUAL', (HUB[0], HUB[1]), (470, 400), *PW)
    return img


CUES = [(0.1, 'click', 0.7), (0.3, 'click', 0.5), (sw(1) + 0.1, 'pop', 0.6), (sw(1) + 1.0, 'stamp', 0.7)] + \
       [(sw(2) + 0.2 + i / 2.6, 'click', 0.9) for i in range(5)] + [(sw(3), 'ding', 0.5)]
S.build(HERE, WORDS, HOOK, KEYCOL, 'wipe', (560, 900), HUB, (shot_open, shot_cut, shot_key), 2,
        ('Did you know that?', (('YES', GRN), ('NO', RED)), ov.SAFE_CX - 30, 880, 2), CUES, cut_point=HUB, key_point=HUB)

if __name__ == '__main__':
    D.cli()
