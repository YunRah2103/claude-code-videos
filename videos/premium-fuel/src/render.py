"""premium-fuel: 'Is PREMIUM faster?' (car stuff, explained; series6 via series10 engine, opening: drop-in).
    python render.py still <dir> t... | safecheck | safestill <dir> t... | cover <png> | video <vo.wav> <out.mp4> [t0 t1]"""
import math, os, sys
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared', 'series10'))
import engine as S
from engine import W, H, G, kit, cb, X, fx, up, D, prog, oc, io, lerp
from pixanim.car import car
from assets import series6bits as B

WORDS = kit.load_words(HERE); ST = S.sentences(WORDS)
def sw(n): return WORDS[ST[n]]['s']
def wt(w): return next(x['s'] for x in WORDS if x['w'].lower().strip('.,?!') == w)
HOOK = ((('Is', None), ('PREMIUM', '#ffd23f'), ('fuel', None)), (('faster?', None),))
KEYCOL = {'premium': kit.YEL, 'faster': kit.YEL, 'no': kit.RED, 'manual': kit.YEL, 'regular': kit.YEL, 'fine': kit.YEL,
          'high-performance': kit.YEL, 'benefit': kit.YEL}
FILL = sw(2) + 0.4


def layer(img, spr, s, x, y, anchor='center'):
    fg = Image.new('RGBA', (W, H), (0, 0, 0, 0)); fx.blit(fg, up(spr, s), x, y, anchor=anchor); img.alpha_composite(G.rim(fg))


def shot_open(t):
    img = S.stage(t)
    layer(img, car('red', wheel_deg=-t * 300), 8, 640, 1780, 'bottom')
    layer(img, B.fuel_gauge(0.3 + 0.6 * oc(prog(t, 0.2, 1.5)), B.YEL), 7, 700, 1060)
    cb.pill(img, t, 0.3, 99, 'PREMIUM', (700, 1000), (480, 680), '#ffd23f', '#1a1a2e', '#c9a21c')
    return img


def shot_cut(t):
    img = S.stage(t)
    layer(img, car('red', wheel_deg=-t * 300), 8, 640, 1780, 'bottom')
    layer(img, B.fuel_gauge(0.9, B.YEL), 7, 700, 1060)
    cb.pill(img, t, sw(1) + 0.1, 99, 'USUALLY, NO', (640, 1500), (480, 640), '#e8343f', '#ffffff', '#a01c26')
    return img


def shot_key(t):
    img = S.stage(t); k = io(prog(t, FILL, 1.0))
    layer(img, B.fuel_compare(k, t), 5, 620, 1370)
    if t >= sw(3): layer(img, car('yellow', wheel_deg=-t * 500), 4, lerp(1300, 700, oc(prog(t, sw(3), 0.6))), 1770, 'bottom')
    cb.pill(img, t, sw(2) + 0.1, wt('regular') - 0.1, 'CHECK YOUR MANUAL', (620, 1190), (480, 600), '#ffd23f', '#1a1a2e', '#c9a21c')
    cb.pill(img, t, wt('regular'), sw(3) - 0.1, 'REGULAR IS FINE', (445, 1560), (480, 600), '#46d26e', '#1a1a2e', '#2f9a4e')
    cb.pill(img, t, sw(3) + 0.5, 99, 'SOME ENGINES BENEFIT', (700, 1660), (480, 600), '#ffffff', '#1a1a2e', '#d6d9e2')
    return img


CUES = [(0.45, 'thump', 0.6), (0.6, 'coin', 0.5), (sw(1) + 0.1, 'buzzer', 0.5), (sw(2) + 0.1, 'pop', 0.5),
        (FILL + 1.0, 'coin', 0.9), (FILL + 1.08, 'clink', 0.6), (sw(3), 'vroom', 0.4), (sw(3) + 0.2, 'pop', 0.5)]
S.build(HERE, WORDS, HOOK, KEYCOL, 'drop-in', (600, 1250), (700, 1000), (shot_open, shot_cut, shot_key), 2,
        ('Did you think it was faster?', (('YES', S.ov.GRN), ('NO', S.ov.RED)), 470, 600, 2), CUES, cut_point=(640, 1500),
        key_point=(600, 1400), ask_prop=lambda t: (B.fuel_gauge(0.6 + 0.2 * math.sin(t * 2), B.YEL), 4), lufs=-15.2)

if __name__ == '__main__':
    D.cli()
