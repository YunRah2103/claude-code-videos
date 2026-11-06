"""airbag-light: 'Airbag light ON?' (car stuff, explained; series6 via series10 engine, opening: tilt).
    python render.py still <dir> t... | safecheck | safestill <dir> t... | cover <png> | video <vo.wav> <out.mp4> [t0 t1]"""
import math, os, sys
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared', 'series10'))
import engine as S
from engine import W, H, G, kit, cb, X, fx, up, D, prog, oc, io, lerp
from pixanim.dash import Dashboard
from assets import series6bits as B

WORDS = kit.load_words(HERE); ST = S.sentences(WORDS)
def sw(n): return WORDS[ST[n]]['s']
DASH = Dashboard(outside=G.base())
LAMP = (560, 1046)
HOOK = ((('Airbag light', None), ('ON?', '#e8343f')),)
KEYCOL = {'airbag': kit.YEL, 'bulb': kit.YEL, 'fault': kit.RED, 'sensor': kit.YEL, 'connector': kit.YEL, 'checked': kit.RED, 'soon': kit.RED}
MX, MY, MS = 600, 1390, 7                                    # module sprite centre + scale
def m(x, y): return MX - 55 * MS + x * MS, MY - 35 * MS + y * MS


def blink(t): return int(t * 3) % 2 == 0


def layer(img, spr, s, x, y):
    fg = Image.new('RGBA', (W, H), (0, 0, 0, 0)); fx.blit(fg, up(spr, s), x, y, anchor='center'); img.alpha_composite(G.rim(fg))


def shot_open(t):
    img = DASH.frame(t, rpm_deg=cb.rpm_deg(0.25 + 0.02 * math.sin(t * 6)), speed_deg=cb.rpm_deg(0.4)).copy()
    layer(img, B.airbag_icon(blink(t)), 5, *LAMP)
    if blink(t): fx.ring(img, (t * 3 % 1) / 3, 0, *LAMP, (232, 52, 63), life=0.3, r1=90)
    cb.pill(img, t, 0.35, 99, 'AIRBAG LIGHT', LAMP, (600, 680), '#e8343f', '#ffffff', '#a01c26')
    return img


def shot_cut(t):
    img = S.stage(t)
    layer(img, B.airbag_icon(blink(t)), 18, 620, 1440)
    if t >= sw(1) + 0.4:                                     # a crossed-out bulb: it's not just a bulb
        k = fx.popin(t, sw(1) + 0.3, 0.3)
        layer(img, B.bulb(oc(prog(t, sw(1) + 0.6, 0.3))), max(1, round(6 * k)), 800, 780)
    cb.pill(img, t, sw(1) + 0.3, sw(2) - 0.1, 'NOT JUST A BULB', (800, 760), (440, 520), '#ffffff', '#1a1a2e', '#d6d9e2')
    cb.pill(img, t, sw(2), 99, 'SYSTEM FAULT', (620, 1340), (440, 520), '#e8343f', '#ffffff', '#a01c26')
    return img


def shot_key(t):
    img = S.stage(t); layer(img, B.airbag_module(t, 1.0 if t < sw(4) + 0.5 else 0.0), MS, MX, MY)
    cb.pill(img, t, sw(3) + 0.2, 99, 'SENSOR', m(10, 60), (330, 640), '#ffffff', '#1a1a2e', '#d6d9e2')
    cb.pill(img, t, sw(3) + 0.7, 99, 'CONNECTOR', m(55, 50), (640, 800), '#ffd23f', '#1a1a2e', '#c9a21c')
    cb.pill(img, t, sw(4), 99, 'GET IT CHECKED', m(55, 20), (520, 470), '#e8343f', '#ffffff', '#a01c26')
    return img


CUES = [(0.3, 'alert', 0.7), (0.9, 'alert', 0.5), (sw(1) + 0.4, 'snap', 0.6), (sw(2), 'buzzer', 0.4), (sw(3) + 0.2, 'pop', 0.5),
        (sw(3) + 0.7, 'click', 0.8), (sw(4), 'alert', 0.8)]
S.build(HERE, WORDS, HOOK, KEYCOL, 'tilt', (560, 980), LAMP, (shot_open, shot_cut, shot_key), 3,
        ('Know what it meant?', (('YES', S.ov.GRN), ('NO', S.ov.RED)), 466, 900, 3), CUES, cut_point=(620, 1340),
        key_point=m(55, 50), lufs=-15.5, ask_prop=lambda t: (B.airbag_icon(blink(t)), 6))

if __name__ == '__main__':
    D.cli()
