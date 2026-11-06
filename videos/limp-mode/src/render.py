"""limp-mode: 'Suddenly slow? Limp mode' (car stuff, explained; series6 via series10 engine, opening: whip-pan).
    python render.py still <dir> t... | safecheck | safestill <dir> t... | cover <png> | video <vo.wav> <out.mp4> [t0 t1]"""
import math, os, sys
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared', 'series10'))
import engine as S
from engine import W, H, G, kit, cb, X, fx, up, D, prog, oc, io, lerp
from pixanim.dash import Dashboard
from pixanim.car import car
from assets import series6bits as B

WORDS = kit.load_words(HERE); ST = S.sentences(WORDS)
def sw(n): return WORDS[ST[n]]['s']
DASH = Dashboard(outside=G.base())
LAMP = (420, 1046)
HOOK = ((('Suddenly', None), ('SLOW?', '#e8343f')), (('Limp mode', None),))
KEYCOL = {'slow': kit.RED, 'warning': kit.YEL, 'limp': kit.YEL, 'mode': kit.YEL, 'cuts': kit.RED, 'power': kit.RED,
          'protect': kit.YEL, 'damage': kit.RED, 'protection': kit.YEL}
CUT = sw(2) + 0.35                                             # power-cut moment


def lamp(img, t, x=LAMP[0], y=LAMP[1], s=5):
    fg = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    fx.blit(fg, up(cb.warn_lamp(int(t * 3) % 2 == 0), s), x, y, anchor='center')
    if int(t * 3) % 2 == 0: fx.ring(fg, (t * 3 % 1) / 3, 0, x, y, (255, 150, 30), life=0.3, r1=90)
    img.alpha_composite(fg)


def shot_open(t):
    sp = 0.55 - 0.25 * oc(prog(t, 0.2, 1.4))                 # speed sagging as power drops
    img = DASH.frame(t, rpm_deg=cb.rpm_deg(0.3 + 0.03 * math.sin(t * 7)), speed_deg=cb.rpm_deg(sp)).copy()
    lamp(img, t)
    cb.pill(img, t, 0.4, 99, 'WARNING LIGHT', LAMP, (640, 660), '#ffd23f', '#1a1a2e', '#c9a21c')
    return img


def crawl(img, t, x=660, y=1600, s=8):
    fg = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    fx.blit(fg, up(car('red', wheel_deg=-t * 60, lights=True), s), x + 10 * math.sin(t * 0.8), y, anchor='bottom')
    img.alpha_composite(G.rim(fg))


def shot_cut(t):
    img = S.stage(t); crawl(img, t)
    fg = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    fx.blit(fg, up(B.power_meter(0.4 + 0.05 * math.sin(t * 3), True, t), 6), 800, 1000, anchor='bottom'); img.alpha_composite(G.rim(fg))
    cb.pill(img, t, sw(1) + 0.3, 99, 'LIMP MODE', (660, 1360), (470, 560), '#ffd23f', '#1a1a2e', '#c9a21c')
    return img


def shot_key(t):
    img = S.stage(t); k = 1 - 0.7 * io(prog(t, CUT, 0.9))
    fg = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    fx.blit(fg, up(B.power_meter(k, k < 0.5, t), 7), 800, 1720, anchor='bottom')
    rpm = lerp(0.85, 0.42, io(prog(t, CUT, 0.9))) + 0.03 * math.sin(t * 9)
    fx.blit(fg, up(cb.rpm_gauge(cb.rpm_deg(rpm), 1.0 if t < CUT + 0.9 else 0.0), 4), 440, 1390, anchor='center')
    img.alpha_composite(G.rim(fg))
    if CUT <= t < CUT + 0.5: fx.ring(img, t, CUT, 800, 1480, (232, 52, 63), life=0.5, r1=260)
    cb.pill(img, t, CUT, sw(3) - 0.1, 'POWER CUT', (800, 1400), (470, 560), '#e8343f', '#ffffff', '#a01c26')
    cb.pill(img, t, sw(3), 99, 'PROTECTION', (440, 1390), (470, 560), '#ffffff', '#1a1a2e', '#d6d9e2')
    return img


CUES = [(0.3, 'alert', 0.6), (0.9, 'power_down', 0.5), (sw(1) + 0.3, 'pop', 0.6), (CUT, 'power_down', 1.0),
        (CUT + 0.05, 'thump', 0.6), (sw(3), 'click', 0.7)]
S.build(HERE, WORDS, HOOK, KEYCOL, 'whip-pan', (540, 960), LAMP, (shot_open, shot_cut, shot_key), 2,
        ('Ever had that happen?', (('YES', S.ov.GRN), ('NO', S.ov.RED)), 470, 640, -3), CUES, cut_point=(660, 1360),
        key_point=(800, 1400), lufs=-15.1, ask_prop=lambda t: (B.power_meter(0.3 + 0.2 * math.sin(t * 2) ** 2, True, t), 5))

if __name__ == '__main__':
    D.cli()
