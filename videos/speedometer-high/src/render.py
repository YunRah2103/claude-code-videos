"""speedometer-high: 'Your speedo reads HIGH' (car stuff, explained; series6 via series10 engine, opening: glitch-in).
    python render.py still <dir> t... | safecheck | safestill <dir> t... | cover <png> | video <vo.wav> <out.mp4> [t0 t1]"""
import math, os, sys
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared', 'series10'))
import engine as S
from engine import W, H, G, kit, cb, X, fx, up, D, prog, oc, io, lerp
from pixanim.dash import Dashboard
from assets import series6bits as B

WORDS = kit.load_words(HERE); ST = S.sentences(WORDS)
def sw(n): return WORDS[ST[n]]['s']
DASH = Dashboard(outside=G.base())
HOOK = ((('Your speedo reads', None),), (('HIGH', '#ffd23f'), ('on purpose', None)))
KEYCOL = {'speedometer': kit.YEL, 'high': kit.YEL, 'purpose': kit.YEL, 'rules': kit.YEL, 'over-read': kit.RED,
          'safety': kit.YEL, 'margin': kit.YEL, 'speed': kit.RED, 'accident': kit.RED}
TRUE, BAND = 0.45, (0.45, 0.56)


def shown(t): return 0.5 + 0.015 * math.sin(t * 3) + 0.006 * (int(t * 8) % 2)       # ticks a little above true


def at(frac, rr, s, cx, cy):
    a = math.radians(225 - 270 * frac); return cx + rr * s * math.cos(a), cy - rr * s * math.sin(a)


def layer(img, spr, s, x, y):
    fg = Image.new('RGBA', (W, H), (0, 0, 0, 0)); fx.blit(fg, up(spr, s), x, y, anchor='center'); img.alpha_composite(G.rim(fg))


def shot_open(t):
    img = DASH.frame(t, rpm_deg=cb.rpm_deg(0.35 + 0.02 * math.sin(t * 6)), speed_deg=cb.rpm_deg(shown(t))).copy()
    cb.pill(img, t, 0.35, 99, 'SPEEDO', (790, 800), (560, 640), '#ffd23f', '#1a1a2e', '#c9a21c')
    return img


def shot_cut(t):
    img = S.stage(t); k = oc(prog(t, sw(1) + 0.4, 0.8))
    layer(img, B.speedo(shown(t), TRUE, (BAND[0], lerp(BAND[0] + 0.001, BAND[1], k)), t=t), 6, 600, 1440)
    cb.pill(img, t, sw(1) + 0.4, 99, 'OVER-READ ALLOWED', at(0.53, 30, 6, 600, 1440), (470, 560), '#ffd23f', '#1a1a2e', '#c9a21c')
    return img


def shot_key(t):
    img = S.stage(t)
    layer(img, B.speedo(shown(t), TRUE, BAND, t=t), 6, 620, 1440)
    cb.pill(img, t, sw(2) + 0.2, 99, 'SAFETY MARGIN', at(0.53, 30, 6, 620, 1440), (480, 560), '#ffd23f', '#1a1a2e', '#c9a21c')
    cb.pill(img, t, sw(2) + 0.9, 99, 'TRUE SPEED', at(TRUE, 40, 6, 620, 1440), (380, 800), '#46d26e', '#1a1a2e', '#2f9a4e')
    return img


CUES = [(0.35, 'tick', 0.8), (0.6, 'tick', 0.6), (sw(1) + 0.4, 'pop', 0.6)] + \
       [(sw(2) + 0.2 + 0.5 * i, 'tick', 0.7) for i in range(4)] + [(sw(2) + 0.9, 'ding', 0.4)]
S.build(HERE, WORDS, HOOK, KEYCOL, 'glitch-in', (760, 860), (790, 800), (shot_open, shot_cut, shot_key), 2,
        ('Does yours read high?', (('YES', S.ov.GRN), ('NO', S.ov.RED)), 450, 560, -5), CUES, cut_point=(600, 1300),
        key_point=(620, 1250), lufs=-15.3, ask_prop=lambda t: (B.speedo(shown(t), TRUE, BAND, t=t), 3))

if __name__ == '__main__':
    D.cli()
