"""abs-pumping: 'Stop pumping your brakes' (car stuff, explained; series10 engine, opening: push-in).
    python render.py still <dir> t... | safecheck | safestill <dir> t... | cover <png> | video <vo.wav> <out.mp4> [t0 t1]"""
import math, os, sys
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared', 'series10'))
import engine as S
from engine import W, H, G, kit, cb, X, fx, up, D, prog, oc, io, lerp
from pixanim.dash import Dashboard
from assets.seriesbits import tyre

WORDS = kit.load_words(HERE); ST = S.sentences(WORDS)
def ws(i): return WORDS[i]['s']
def sw(n): return ws(ST[n])
DASH = Dashboard(outside=G.base())
ABS_LAMP = (742, 1046)
HOOK = ((('Stop', None), ('PUMPING', '#e8343f')), (('your brakes', None),))
KEYCOL = {'pumping': S.kit.RED, 'abs.': S.kit.YEL, 'pulses': S.kit.YEL, 'lock.': S.kit.RED, 'firmly': S.kit.YEL, 'hold': S.kit.YEL, 'steering': S.kit.YEL}


def pump(t): return 0.5 + 0.5 * math.sin(t * 13)


def shot_open(t):
    img = DASH.frame(t, rpm_deg=cb.rpm_deg(0.22 + 0.03 * math.sin(t * 5)), speed_deg=cb.rpm_deg(0.45)).copy()
    fg = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    if int(t * 6) % 2 == 0: fx.ring(fg, (t * 6 % 1) / 6, 0, *ABS_LAMP, (255, 170, 40), life=0.16, r1=90)
    fx.blit(fg, up(X.pedal(pump(t)), 10), 800, 1760, anchor='bottom')
    img.alpha_composite(fg)
    cb.pill(img, t, 0.5, 99, 'PUMP? NO', (760, 1500), (640, 1150), '#e8343f', '#ffffff', '#a01c26')
    return img


def wheel_layer(img, t, locked=False, pulsing=0.0, cx=540, cy=760, s=11):
    rot = 0 if locked else t * 420
    fg = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    fx.blit(fg, up(tyre(rot), s), cx, cy, anchor='center')
    clamp = pump(t * 1.1) if pulsing else 0.0
    fx.blit(fg, up(X.disc_caliper(rot, clamp), s - 4), cx, cy, anchor='center')
    img.alpha_composite(G.rim(fg))


def shot_cut(t):
    img = S.stage(t); wheel_layer(img, t, pulsing=0.5)
    cb.pill(img, t, sw(1) + 0.3, 99, 'ABS', (640, 640), (470, 400), '#ffd23f', '#1a1a2e', '#c9a21c')
    return img


def wave(img, t, x0=360, y0=1400, w=560):
    """Scrolling ABS pulse trace: brake pressure on / off many times a second."""
    d = ImageDraw.Draw(img); pts = []
    for i in range(0, w, 6):
        on = (int((i + t * 500) / 60) % 2) == 0; pts.append((x0 + i, y0 - (70 if on else 0)))
    d.line(pts, fill=(26, 26, 46), width=22); d.line(pts, fill=(255, 210, 63), width=10)


def shot_key(t):
    img = S.stage(t); wheel_layer(img, t, pulsing=1.0, cy=700)
    if int(t * 14) % 2 == 0: fx.ring(img, (t * 14 % 1) / 14, 0, 640, 600, (255, 210, 63), life=0.07, r1=140)
    wave(img, t)
    fg = Image.new('RGBA', (W, H), (0, 0, 0, 0)); fx.blit(fg, up(X.pedal(0.9 + 0.1 * pump(t * 1.1)), 9), 840, 1800); img.alpha_composite(fg)
    cb.pill(img, t, sw(2) + 0.4, sw(3) - 0.1, 'PULSES FOR YOU', (620, 560), (470, 400), '#ffd23f', '#1a1a2e', '#c9a21c')
    cb.pill(img, t, sw(3), sw(4) - 0.1, 'PRESS + HOLD', (840, 1560), (470, 400), '#ffffff', '#1a1a2e', '#d6d9e2')
    cb.pill(img, t, sw(4), 99, 'KEEP STEERING', (540, 760), (470, 400), '#ffffff', '#1a1a2e', '#d6d9e2')
    return img


CUES = [(0.1, 'thump', 0.6), (0.35, 'thump', 0.5), (0.6, 'thump', 0.5), (0.5, 'buzzer', 0.4), (sw(1) + 0.3, 'pop', 0.6),
        (sw(2), 'pulse', 1.0), (sw(2) + 0.6, 'pulse', 0.9), (sw(3), 'click', 0.8), (sw(4), 'pop', 0.6), (sw(4) + 0.1, 'screech', 0.3)]
S.build(HERE, WORDS, HOOK, KEYCOL, 'push-in', (560, 900), (800, 1500), (shot_open, shot_cut, shot_key), 2,
        ('Did you know that?', (('YES', S.ov.GRN), ('NO', S.ov.RED)), S.ov.SAFE_CX, 640, -3), CUES, cut_point=(640, 640), key_point=(640, 620), ask_prop=lambda t: (X.disc_caliper(t * 300, 0.5 + 0.5 * math.sin(t * 14)), 7))

if __name__ == '__main__':
    D.cli()
