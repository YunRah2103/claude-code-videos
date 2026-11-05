"""Renders 'car stuff, explained' ep 3: never open a hot radiator cap (13 s, loops).

Shots (timed to words.json, faster-whisper on out/hot-radiator/voiceover.wav):
  1 cap     0.00  steaming radiator, pressure needle already rising on frame 0; headline NEVER (red)
  2 system  T2    cooling-system cutaway: engine, hoses with coolant flowing, gauge in the red, UNDER PRESSURE
  3 spray   T3    the cap blows, hot coolant sprays, presenter steps back, BURN RISK; on 'Wait' it cools to green
  4 ask     T4    garage: presenter asks, poll 'Would you have known? YES / NO'; whips back to shot 1 (loop)
    python render.py still <dir> t... | safecheck | safestill <dir> t... | cover <png> | video <vo.wav> <out.mp4> [t0 t1]
"""
import math, os, sys
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared'))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared', 'assets'))
import episode as kit
from episode import W, H, RED, YEL, WHITE
from backdrops.garage import Garage
from pixanim.motion import prog, lerp, io, oc
from pixanim.presenter import Presenter, Fn
from pixanim.engine import Engine, crank_angle
from pixanim.grid import up
from pixanim import fx
from assets import overlays as ov, carbits as cb, garagebits as gb
import dashep as D

WORDS = kit.load_words(HERE)
def ws(i): return WORDS[i]['s']
def we(i): return WORDS[i]['e']

DUR, END_T = 13.0, 12.62
T2, T3, T4 = ws(6) - 0.3, ws(12) - 0.3, ws(26) - 0.5    # 'The cooling', 'Hot coolant', 'Would you'
SPRAY, WAIT = ws(15), ws(20)                           # 'spray', 'Wait'
G = Garage(W, H, 1520, 9)
ENG = Engine()
HOOK = ((('NEVER', '#e8343f'), ('open a', None)), (('HOT radiator cap', None),))
KEYCOL = {'pressure.': RED, 'spray': RED, 'burn': RED, 'cool.': (79, 179, 255), 'known?': YEL}


def pulse(t, rate=7.0): return 0.55 + 0.45 * math.sin(t * rate)


def hot_bg(t, k=1.0):
    img = G.frame(t).convert('RGBA')
    img.alpha_composite(Image.new('RGBA', (W, H), (90, 30, 20, int(60 * k))))
    return img


# ------------------------------------------------------------------ shot 1: steaming radiator, needle rising
RS = 7
RAD_C = (540, 1000)
CAP = (RAD_C[0] - gb.RAD_W * RS // 2 + gb.CAP_XY[0] * RS, RAD_C[1] - gb.RAD_H * RS // 2 + gb.CAP_XY[1] * RS)


def needle1(t): return lerp(0.45, 0.92, oc(prog(t, -0.5, 1.4))) + 0.02 * math.sin(t * 19)


def shot_cap(t):
    img = hot_bg(t)
    fg = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    fx.blit(fg, up(gb.radiator(4 * math.sin(t * 9), t, pulse(t, 5)), RS), *RAD_C, anchor='center')
    gb.steam(fg, t, CAP[0], CAP[1] - 30, size=1.2)
    gb.steam(fg, t + 0.7, CAP[0] + 220, RAD_C[1] - 200, seed=5, size=0.8)
    fx.blit(fg, up(gb.pressure_gauge(needle1(t), pulse(t, 12) * oc(prog(t, 0.4, 0.3))), 6), 800, 1500, anchor='center')
    img.alpha_composite(G.rim(fg))
    z = lerp(1.5, 1.04, oc(prog(t, -0.5, 1.4))); sh = 16 + 28 * math.exp(-max(0, t) * 1.6)
    return D.camera(img.convert('RGB'), t, z, 560, 1050, sh)


# ------------------------------------------------------------------ shot 2: cooling-system cutaway
HOSES = [((300, 1190), (300, 1060), (520, 1060), (520, 700)),     # top hose: radiator -> engine head
         ((640, 1140), (640, 1600), (300, 1600), (300, 1530))]    # bottom hose: engine -> radiator
def _pt(path, u):
    seg = [math.dist(a, b) for a, b in zip(path, path[1:])]; L = sum(seg) * (u % 1)
    for (a, b), s in zip(zip(path, path[1:]), seg):
        if L <= s: return a[0] + (b[0] - a[0]) * L / s, a[1] + (b[1] - a[1]) * L / s
        L -= s
    return path[-1]


def shot_system(t):
    img = ENG.frame(t, theta=crank_angle(t, [(0, 3.0)]), firing=True).copy()
    img.alpha_composite(Image.new('RGBA', (W, H), (20, 10, 12, 110)))
    fg = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(fg)
    for path in HOSES:
        d.line(path, fill=(26, 26, 46), width=44, joint='curve'); d.line(path, fill=(60, 64, 78), width=30, joint='curve')
        for k in range(14):                                    # coolant flowing in the hose
            x, y = _pt(path, k / 14 + t * 0.35)
            d.rectangle((x - 7, y - 7, x + 7, y + 7), fill=gb.COOLANT if k % 2 else gb.COOLANT_HI)
    fx.blit(fg, up(gb.radiator(0, t, 0.8), 4), 300, 1360, anchor='center')
    gb.steam(fg, t, 300, 1190, size=0.7)
    g = 0.94 + 0.03 * math.sin(t * 23)
    fx.blit(fg, up(gb.pressure_gauge(g, pulse(t, 12)), 7), 820, 1480, 1, 1, 2 * math.sin(t * 30), anchor='center')
    fx.ring(fg, (t - T2) % 0.6, 0, 905, 1440, (255, 90, 90), life=0.45, r1=220)
    img.alpha_composite(fg)
    cb.pill(img, t, T2 + 0.25, T3 - 0.1, 'UNDER PRESSURE', (880, 1330), (500, 470), '#e8343f', '#ffffff', '#a01c26')
    z = lerp(1.2, 1.05, oc(prog(t, T2, 0.6)))
    return D.camera(img.convert('RGB'), t, z, 560, 1150, 5 + 4 * pulse(t, 9))


# ------------------------------------------------------------------ shot 3: the spray
P3 = Presenter([(-9, dict(path=Fn(lambda t: (lerp(470, 170, oc(prog(t, SPRAY, 0.5))), 1700)), size=6, legs='stand', arms='point',
                          point=CAP, expr='smile', ground=None, squash=True)),
                (SPRAY, dict(arms='shock', expr='shock', squash=True)),
                (WAIT + 0.3, dict(arms=('aim', 20), expr='smile', squash=True))], words=WORDS)


def cap_fly(t):
    """The cap twists, then pops off and tumbles away up and to the right."""
    if t < SPRAY: return CAP[0], CAP[1] - 10, 0, 1.0
    a = t - SPRAY
    return CAP[0] + 700 * a, CAP[1] - 10 - 1400 * a + 1500 * a * a, 600 * a, 1.0


def shot_spray(t):
    cool = io(prog(t, WAIT, 1.2))
    img = hot_bg(t, 1 - cool)
    fg = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    turn = 120 * io(prog(t, T3 + 0.2, SPRAY - T3 - 0.2))
    rad = gb.radiator(turn, t, (1 - cool) * pulse(t, 6))
    if t >= SPRAY:                                             # cap gone: paint the open neck
        rd = ImageDraw.Draw(rad); cx, cy = gb.CAP_XY
        rd.rectangle((cx - 12, cy - 9, cx + 12, cy + 5), fill=(0, 0, 0, 0))
        rd.rectangle((57, 12, 73, 19), fill=(26, 26, 46)); rd.rectangle((59, 13, 71, 17), fill=(10, 60, 30))
    fx.blit(fg, up(rad, RS), *RAD_C, anchor='center')
    gb.spray(fg, t, SPRAY, CAP[0], CAP[1] + 20, n=110, s=12, t1=WAIT - 0.2)
    if t < WAIT + 1.0: gb.steam(fg, t, CAP[0], CAP[1] - 30, size=1.6 * (1 - cool) + 0.2)
    x, y, rot, k = cap_fly(t)
    if t >= SPRAY and y > -200: fx.blit(fg, up(_cap_sprite(), RS), x, y, 1, 1, rot, anchor='center')
    gauge = lerp(0.95, 0.2, cool) + 0.02 * math.sin(t * 21) * (1 - cool)
    fx.blit(fg, up(gb.pressure_gauge(gauge, pulse(t, 12) * (1 - cool)), 5), 850, 1520, anchor='center')
    if t > WAIT: k2 = fx.popin(t, WAIT + 0.9, 0.3); fx.blit(fg, up(gb.snowflake(), 8), 850, 1300, k2, k2, 12 * t, anchor='center')
    img.alpha_composite(G.rim(fg)); P3.draw(img, t)
    cb.pill(img, t, SPRAY + 0.3, T4 - 0.15, 'BURN RISK', (CAP[0] + 40, CAP[1] - 120), (640, 460), '#e8343f', '#ffffff', '#a01c26')
    sh = 14 * math.exp(-max(0, t - SPRAY) * 3) if t >= SPRAY else 3
    z = lerp(1.22, 1.06, oc(prog(t, T3, 0.7))) + 0.06 * oc(prog(t, SPRAY, 0.2)) * (1 - cool)
    return D.camera(img.convert('RGB'), t, z, 560, 1000, sh)


def _cap_sprite():
    img = Image.new('RGBA', (26, 16), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.ellipse((1, 1, 25, 15), fill=(26, 26, 46)); d.ellipse((2, 2, 24, 13), fill=(210, 214, 222))
    d.ellipse((6, 4, 20, 11), fill=(176, 182, 194)); d.line((1, 8, 25, 8), fill=(26, 26, 46), width=2)
    return img


# ------------------------------------------------------------------ shot 4: the question
P4 = Presenter([(-9, dict(visible=True, path=Fn(lambda t: (300, 1600)), size=9, legs='stand', arms='shrug', expr='smile', ground=1600,
                          look_camera=True, squash=True)),
                (ws(28), dict(arms=('aim', -12), expr='grin', squash=True))], words=WORDS)


def shot_ask(t):
    img = G.frame(t).convert('RGBA')
    fg = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    fx.blit(fg, up(gb.radiator(0, t, 0.3), 3), 800, 1460 + 8 * math.sin(t * 2), anchor='center')
    gb.steam(fg, t, 800, 1330, size=0.5)
    img.alpha_composite(G.rim(fg)); P4.draw(img, t)
    return D.camera(img.convert('RGB'), t, lerp(1.15, 1.04, oc(prog(t, T4, 0.6))), 540, 1300, 5)


SCENE = D.sequence([(-9, shot_cap), (T2, shot_system), (T3, shot_spray), (T4, shot_ask)])


def overlay(cv, t):
    ov.headline(cv, t, T2 - 0.25, HOOK, y=430)
    if t >= END_T: ov.headline(cv, max(-0.35, t - DUR), T2 - 0.25, HOOK, y=430)
    ov.poll(cv, t, ws(26) - 0.1, END_T - 0.1, 'Would you have known?', ov.SAFE_CX, 640, 0.9)


CUES = [(0.0, 'hiss', 1.0), (0.05, 'whoosh', 0.6), (0.6, 'beep', 0.7), (T2 + 0.25, 'pop', 0.6), (T2 + 0.3, 'hiss', 0.7),
        (T2 + 1.2, 'beep', 0.6), (T3 + 0.2, 'creak', 0.6), (SPRAY, 'boom', 0.5), (SPRAY, 'hiss', 1.0), (SPRAY + 0.6, 'hiss', 0.8),
        (we(19) + 0.05, 'pop', 0.7), (WAIT + 0.9, 'sparkle', 0.5), (ws(26) - 0.1, 'pop', 0.8), (END_T, 'whoosh', 0.6)]

D.wire(HERE, WORDS, DUR, END_T, SCENE, [T2, T3, T4], CUES, KEYCOL, overlay,
       cap=(T2 - 0.05, 1075, ((T2 - 0.05, T3), (ws(18) - 0.05, WAIT))))   # UNDER PRESSURE / BURN RISK pills already say those words

if __name__ == '__main__':
    D.cli()
