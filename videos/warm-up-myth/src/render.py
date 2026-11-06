"""warm-up-myth: do you need to warm up your car (car stuff, explained; shared/series10 engine, opening: glitch-in).
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
from pixanim.props import stopwatch
from assets.seriesbits import wear_bar
HOOK = ((('Warm up for', None), ('MINUTES?', '#ffd23f')),)
KEYCOL = {'minutes?': YEL, 'gently': GRN, 'soon': GRN, 'waste': RED, 'fuel.': RED, 'faster': GRN, 'idling.': RED}


def puffs(img, t, x, y, n=3):
    for k in range(n): fx.puff(img, (t + k * 0.3) % 0.9, 0, x, y, seed=k + 2, life=0.9, size=1.2, drift=(-200, -120))


def shot_open(t):
    img = garage(t); layer(img, (car('silver', 0), 9, 600, 1560, 'bottom'), (stopwatch((t * 0.5) % 1), 9, 760, 860))
    puffs(img, t, 220, 1450)
    return img


def shot_cut(t):
    img = garage(t); k = io(prog(t, sw(1) + 0.4, 2.2)); x = lerp(420, 900, k)
    layer(img, (car('silver', int(x) % 360), 9, x, 1560, 'bottom'))
    cb.pill(img, t, sw(1) + 0.3, 99, 'DRIVE OFF GENTLY', (x, 1400), (470, 420), *PY)
    return img


def shot_key(t):
    img = garage(t)
    if t < sw(3):
        f = lerp(0.9, 0.35, io(prog(t, sw(2), 2.2)))
        layer(img, (car('silver', 0), 9, 600, 1560, 'bottom'), (wear_bar(f, (232, 52, 63)), 10, 560, 820))
        puffs(img, t, 220, 1450)
        cb.pill(img, t, sw(2) + 0.2, 99, 'LONG IDLE = FUEL', (560, 820), (470, 420), *PR)
        return img
    k1 = oc(prog(t, sw(3) + 0.2, 2.5)); k2 = 0.35 * k1
    layer(img, (X.thermo(k2), 9, 320, 700), (X.thermo(k1), 9, 760, 700))
    d = ImageDraw.Draw(img)
    for x, lab in ((320, 'IDLING'), (760, 'DRIVING')):
        d.text((x, 960), lab, font=X._font(56), fill=(240, 242, 248), anchor='mm', stroke_width=6, stroke_fill=(26, 26, 46))
    cb.pill(img, t, sw(3) + 0.3, 99, 'WARMS UP FASTER', (760, 560), (470, 420), *PY)
    return img


CUES = [(0.0, 'glass_crack', 0.5), (0.1, 'hum', 0.5), (sw(1) + 0.3, 'pop', 0.6), (sw(1) + 0.4, 'vroom', 0.6), (sw(2) + 0.2, 'buzzer', 0.4),
        (sw(3) + 0.3, 'pop', 0.6), (sw(3) + 0.4, 'sparkle', 0.5)]
S.build(HERE, WORDS, HOOK, KEYCOL, 'glitch-in', (560, 1100), (760, 860), (shot_open, shot_cut, shot_key), 2,
        ('Did you think you needed to?', (('YES', GRN), ('NO', RED)), ov.SAFE_CX - 20, 900, 3), CUES, cut_point=(600, 1300), key_point=(560, 820), ask_prop=lambda t: (X.thermo(0.5 + 0.5 * math.sin(t * 1.5) ** 2), 7))

if __name__ == '__main__':
    D.cli()
