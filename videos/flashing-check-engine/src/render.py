"""flashing-check-engine: a flashing check engine light (car stuff, explained; shared/series10 engine, opening: drop-in).
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

from pixanim.dash import Dashboard
from pixanim.engine import Engine
from assets.seriesbits import exhaust
DASH = Dashboard(outside=G.base()); ENG = Engine()
HOOK = ((('A', None), ('FLASHING', '#e8343f')), (('check engine light', None),))
KEYCOL = {'flashes': RED, 'urgent.': RED, 'steady': YEL, 'soon.': YEL, 'flashing': RED, 'misfire.': RED, 'catalytic': YEL, 'safely': GRN}


def flash(t, rate=3.0): return (t * rate) % 1 < 0.55


def shot_open(t):
    img = DASH.frame(t, rpm_deg=cb.rpm_deg(0.25 + 0.04 * math.sin(t * 17))).copy()
    layer(img, (cb.warn_lamp(flash(t)), 16, 540, 1000))
    if flash(t): fx.ring(img, (t * 3) % 1, 0, 540, 1000, (255, 150, 30), life=0.4, r1=260)
    return img


def shot_cut(t):
    img = layer(garage(t), (cb.warn_lamp(True), 14, 300, 800), (cb.warn_lamp(flash(t)), 14, 780, 800))
    d = ImageDraw.Draw(img)
    for x, lab in ((300, 'STEADY'), (780, 'FLASHING')):
        d.text((x, 1010), lab, font=X._font(56), fill=(240, 242, 248), anchor='mm', stroke_width=6, stroke_fill=(26, 26, 46))
    cb.pill(img, t, sw(1) + 0.2, 99, 'CHECK SOON', (300, 700), (420, 420), *PY)
    return img


def shot_key(t):
    if t < sw(3):
        img = ENG.frame(t, theta=t * 2000, firing=int(t * 7) % 3 != 0, shake=(round(2 * math.sin(t * 50)), 0)).copy()
        rise = oc(prog(t, sw(2), 0.8))
        layer(img, (cb.warn_lamp(flash(t, 4)), int(6 + 8 * rise), 800, int(1300 - 560 * rise)))
        cb.pill(img, t, sw(2) + 0.3, 99, 'MISFIRE', Engine.BLOCK, (420, 420), *PR)
        return img
    img = garage(t); hot = oc(prog(t, sw(3), 1.0)) * (0.7 + 0.3 * math.sin(t * 9))
    layer(img, (exhaust(t, hot), 5, 560, 820))
    S.X  # exhaust: catalytic converter glows
    cb.pill(img, t, sw(3) + 0.2, sw(4) - 0.1, 'CAT CONVERTER', (560, 800), (470, 420), *PR)
    cb.pill(img, t, sw(4), 99, 'PULL OVER SAFELY', (560, 800), (470, 420), *PW)
    return img


CUES = [(0.05, 'thump', 0.8), (0.1, 'beep', 0.7), (0.43, 'beep', 0.6), (sw(1) + 0.2, 'pop', 0.6), (sw(2), 'beep', 0.8),
        (sw(2) + 0.3, 'buzzer', 0.5), (sw(3) + 0.2, 'hiss', 0.6), (sw(4), 'ding', 0.5)]
S.build(HERE, WORDS, HOOK, KEYCOL, 'drop-in', (540, 1000), (540, 1000), (shot_open, shot_cut, shot_key), 2,
        ('Would you know the difference?', (('YES', GRN), ('NO', RED)), ov.SAFE_CX + 20, 420, -2), CUES, cut_point=(780, 800), key_point=Engine.BLOCK)

if __name__ == '__main__':
    D.cli()
