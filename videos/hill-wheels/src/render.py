"""hill-wheels: which way to turn your wheels on a hill (car stuff, explained; shared/series10 engine, opening: slow-motion).
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
HOOK = ((('Wheels on a', None), ('HILL', '#ffd23f')), (('which way?', None),))
KEYCOL = {'hill?': YEL, 'downhill': YEL, 'towards': YEL, 'kerb,': YEL, 'uphill': YEL, 'away.': YEL, 'differ': RED, 'country.': RED}
ANG = 14


def slope(img, t):
    d = ImageDraw.Draw(img); a = math.tan(math.radians(ANG))
    d.polygon([(0, 1500 - 540 * a), (W, 1500 + 540 * a), (W, H), (0, H)], fill=(58, 60, 70))
    d.line([(0, 1500 - 540 * a), (W, 1500 + 540 * a)], fill=(200, 200, 210), width=14)


def shot_open(t):
    img = garage(t); slope(img, t)
    c = car('red', 0, brake=True).rotate(-ANG, expand=True, resample=Image.NEAREST)
    roll = 6 * math.sin(t * 3)
    layer(img, (c, 9, 560 + roll, 1460 + roll * math.tan(math.radians(ANG))))
    return img


def panel(img, t, x, label, steer, kerb_right=True, start=0):
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((x - 200, 560, x + 200, 1180), 30, fill=(70, 72, 82), outline=(26, 26, 46), width=8)
    d.rectangle((x + 150, 580, x + 190, 1160), fill=(200, 200, 210))      # kerb on the right
    s = steer * oc(prog(t, start, 0.5))
    layer(img, (X.car_top(s), 7, x, 880))
    d.text((x, 520), label, font=X._font(52), fill=(240, 242, 248), anchor='mm', stroke_width=6, stroke_fill=(26, 26, 46))


def shot_cut(t):
    img = garage(t); i_down = sw(1) + 1.2
    panel(img, t, 300, 'DOWNHILL', 28, start=i_down)
    panel(img, t, 780, 'UPHILL', -28, start=i_down + 1.3)
    cb.pill(img, t, i_down, i_down + 1.25, 'TO THE KERB', (380, 760), (470, 420), *PY)
    cb.pill(img, t, i_down + 1.3, 99, 'AWAY FROM IT', (700, 760), (470, 420), *PY)
    return img


def shot_key(t):
    img = garage(t); d = ImageDraw.Draw(img)
    for i, (x, y) in enumerate(((300, 760), (780, 760), (540, 1080))):
        k = fx.popin(t, sw(2) + 0.15 * i, 0.3)
        if k <= 0: continue
        r = int(150 * k); d.rounded_rectangle((x - r, y - r, x + r, y + r), 30, fill=(236, 240, 248), outline=(26, 26, 46), width=8)
        d.text((x, y), '?', font=X._font(int(200 * k) + 1), fill=(232, 52, 63) if i == 1 else (26, 26, 46), anchor='mm')
    cb.pill(img, t, sw(2) + 0.3, 99, 'CHECK LOCAL RULES', (540, 900), (470, 420), *PR)
    return img


CUES = [(0.0, 'creak', 0.6), (sw(1) + 1.2, 'click', 0.8), (sw(1) + 2.5, 'click', 0.8), (sw(2), 'pop', 0.6), (sw(2) + 0.15, 'pop', 0.6), (sw(2) + 0.3, 'pop', 0.6)]
S.build(HERE, WORDS, HOOK, KEYCOL, 'slow-motion', (560, 1250), (560, 1380), (shot_open, shot_cut, shot_key), 2,
        ('Which way do you turn yours?', (('TOWARDS', GRN), ('AWAY', RED)), ov.SAFE_CX - 20, 680, -4, 0.8), CUES, cut_point=(300, 880), key_point=(540, 900), ask_prop=lambda t: (X.car_top(28 * math.sin(t * 2.2)), 6))

if __name__ == '__main__':
    D.cli()
