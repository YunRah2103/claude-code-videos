"""stop-start: engine off at red lights (car stuff, explained; shared/series10 engine, opening: pull-back).
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
from pixanim.engine import Engine, crank_angle
DASH = Dashboard(outside=G.base()); ENG = Engine()
HOOK = ((('Engine', None), ('OFF', '#e8343f')), (('at red lights?', None),))
KEYCOL = {'off': RED, 'red': RED, 'stop-start.': YEL, 'save': GRN, 'fuel': GRN, 'restarts': YEL, 'brake.': YEL}


def shot_open(t):
    f = lerp(0.2, 0.0, oc(prog(t, -0.4, 1.2)))
    img = DASH.frame(t, rpm_deg=cb.rpm_deg(f)).copy()
    layer(img, (X.traffic_light('red'), 6, 960, 470), (X.ss_icon(True), 8, 790, 985))
    fx.ring(img, (t % 0.8), 0, 790, 985, (90, 220, 120), life=0.6, r1=170)
    return img


def shot_cut(t):
    img = layer(garage(t), (X.traffic_light('red'), 9, 300, 760), (X.ss_icon(True), 14, 690, 760))
    fx.ring(img, (t % 0.9), 0, 690, 760, (90, 220, 120), life=0.7, r1=260)
    cb.pill(img, t, sw(1) + 0.2, 99, 'STOP-START', (690, 640), (470, 420), *PY)
    return img


RESTART = None
PROFILE = None


def shot_key(t):
    r = sw(3) + 0.9
    th = crank_angle(t, [(0, 0), (r, 0), (r + 0.3, 6)])
    img = ENG.frame(t, theta=th, firing=t >= r).copy()
    light = 'green' if t >= sw(3) + 0.5 else 'red'
    layer(img, (X.traffic_light(light), 7, 860, 420))
    if t < sw(3): layer(img, (cb.fuel_cut(), 12, 880, 1420))
    cb.pill(img, t, sw(2) + 0.2, sw(3) - 0.1, 'CAN SAVE FUEL', (880, 1340), (470, 420), *PY)
    cb.pill(img, t, sw(3) + 0.3, 99, 'LIFT OFF = RESTART', Engine.BLOCK, (470, 420), *PW)
    return img


CUES = [(0.2, 'poof', 0.6), (0.3, 'click', 0.7), (sw(1) + 0.2, 'pop', 0.6), (sw(2) + 0.2, 'ding', 0.4), (sw(3) + 0.5, 'beep', 0.5), (sw(3) + 0.9, 'vroom', 0.9)]
S.build(HERE, WORDS, HOOK, KEYCOL, 'pull-back', (560, 900), (790, 985), (shot_open, shot_cut, shot_key), 2,
        ('Would you turn it off yourself?', (('YES', GRN), ('NO', RED)), ov.SAFE_CX, 760, -2), CUES, cut_point=(690, 760), key_point=Engine.BLOCK, ask_prop=lambda t: (X.ss_icon(int(t * 2) % 2 == 0), 9))

if __name__ == '__main__':
    D.cli()
