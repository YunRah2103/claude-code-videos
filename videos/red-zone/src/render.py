"""Renders 'car stuff, explained': the red zone on the rev counter (14 s, loops).

Shots (timed to words.json, faster-whisper on out/red-zone/voiceover.wav):
  1 dash    0.00  dashboard, the needle already revving into the red on frame 0; presenter points at it; headline
  2 dial    2.40  close-up of the red section: pulsing red ring, REV LIMIT callout, needle bouncing on the limiter
  3 engine  4.20  engine cutaway revving hot: TOO LONG = DAMAGE; on 'cut' the fuel-cut icon pops and the engine calms
  4 ask     10.45 garage: presenter asks, poll 'Ever go in the red? YES / NO'; whips back to shot 1 (loop)
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
from pixanim.motion import prog, lerp, io, oc, ob
from pixanim.presenter import Presenter, Fn
from pixanim.dash import Dashboard
from pixanim.engine import Engine, crank_angle
from pixanim.grid import up
from pixanim import fx
from assets import overlays as ov, carbits as cb
import dashep as D

WORDS = kit.load_words(HERE)
def ws(i): return WORDS[i]['s']

DUR, END_T = 14.0, 13.62
T2, T3, T4 = 2.4, 4.2, 10.45
CUT = ws(26)                                       # 'cut'
DMG = ws(15)                                       # 'too' (long)
G = Garage(W, H, 1520, 9)
DASH = Dashboard(outside=Garage(W, H, 1180, 9).base())
ENG = Engine()
TACHO, TR = Dashboard.TACHO, Dashboard.TACHO_R
HOOK = ((('Your rev counter', None),), (('has a', None), ('RED ZONE', '#e8343f')))
KEYCOL = {'red': RED, 'zone': RED, 'decoration': YEL, 'damaged': RED, 'cut': YEL, 'power': YEL}


def limiter(t): return 0.035 * abs(math.sin(t * 23)) + 0.01 * math.sin(t * 61)


def rev1(t):
    """Needle fraction: already climbing on frame 0, slams into the red, then bounces on the limiter."""
    u = oc(prog(t, -0.4, 1.3))
    f = lerp(0.3, 0.86, u) + 0.06 * math.sin(t * 9) * (1 - u)
    return f - limiter(t) if u > 0.97 else f


def red_ring(fg, cx, cy, r, k, width=20):
    if k < 0.02: return
    d = ImageDraw.Draw(fg); a0 = -cb.RED_DEG
    for w, a in ((width + 16, int(70 * k)), (width, int(220 * k))):
        d.arc((cx - r, cy - r, cx + r, cy + r), a0 - 4, 49, fill=RED + (a,), width=w)


def pulse(t, rate=7.0): return 0.55 + 0.45 * math.sin(t * rate)


# ------------------------------------------------------------------ shot 1: dashboard hook
P1 = Presenter([(-9, dict(path=Fn(lambda t: (200, 1600)), size=6, legs='stand', arms='point', point=(TACHO[0] + 40, TACHO[1]),
                          expr='grin', ground=None, look=TACHO))], words=WORDS)


def shot_dash(t):
    img = DASH.frame(t, rpm_deg=cb.rpm_deg(rev1(t))).copy()
    fg = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    red_ring(fg, TACHO[0], TACHO[1], TR + 12, pulse(t, 14) * oc(prog(t, 0.6, 0.3)))
    fx.ring(fg, t % 0.7, 0, TACHO[0] + 0.8 * TR * math.cos(-0.35), TACHO[1] + 0.8 * TR * math.sin(0.35), (255, 90, 90), life=0.5, r1=150)
    img.alpha_composite(fg); P1.draw(img, t)
    z = lerp(1.38, 1.06, oc(prog(t, -0.6, 1.5))); sh = 10 + 18 * math.exp(-max(0, t) * 2)
    return D.camera(img.convert('RGB'), t, z, TACHO[0] + 80, TACHO[1] + 120, sh)


# ------------------------------------------------------------------ shot 2: red-zone close-up
DIAL, DS = (300, 840), 12


def red_point(r_grid=40, deg=-20):
    a = math.radians(deg); return DIAL[0] + r_grid * DS * math.cos(a), DIAL[1] - r_grid * DS * math.sin(a)


def shot_dial(t):
    img = G.frame(t).convert('RGBA')
    fg = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    k = pulse(t, 10)
    fx.blit(fg, up(cb.rpm_gauge(cb.rpm_deg(0.86 - limiter(t)), k), DS), DIAL[0], DIAL[1], anchor='center')
    fx.ring(fg, (t - T2) % 0.6, 0, *red_point(), (255, 90, 90), life=0.45, r1=200)
    img.alpha_composite(G.rim(fg))
    cb.pill(img, t, T2 + 0.25, T3 - 0.1, 'REV LIMIT', red_point(), (600, 470), '#e8343f', '#ffffff', '#a01c26')
    z = lerp(1.25, 1.08, oc(prog(t, T2, 0.6)))
    return D.camera(img.convert('RGB'), t, z, 640, 900, 6 + 10 * k)


# ------------------------------------------------------------------ shot 3: engine cutaway
PROFILE = [(0, 2.5), (T3, 5.5), (DMG, 7.5), (CUT, 7.5), (CUT + 0.3, 2.2)]
P3 = Presenter([(-9, dict(visible=False, path=Fn(lambda t: (175, 1640)))),
                (T3 + 0.3, dict(visible=True, size=5, legs='stand', arms='point', point=Engine.BLOCK, expr='smile', ground=None,
                                squash=True)),
                (ws(22) - 0.1, dict(arms='shock', expr='shock', squash=True)),   # 'damaged'
                (CUT + 0.2, dict(arms='point', point=(760, 560), expr='grin'))], words=WORDS)


def shot_engine(t):
    hot = 0 if t >= CUT + 0.2 else oc(prog(t, DMG, 1.0))
    sh = (round(2 * hot * math.sin(t * 50)), 0)
    img = ENG.frame(t, theta=crank_angle(t, PROFILE), firing=t < CUT, shake=sh).copy()
    fg = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    if hot > 0.01:                                                    # overheating glow on the block
        g = Image.new('L', (W, H), 0); ImageDraw.Draw(g).ellipse((420, 520, 1000, 1080), fill=int(120 * hot * pulse(t, 12)))
        fg.paste((255, 70, 50, 255), (0, 0), g.filter(__import__('PIL.ImageFilter', fromlist=['x']).GaussianBlur(60)))
    img.alpha_composite(fg)
    if t >= CUT - 0.05:
        k = fx.popin(t, CUT, 0.3)
        fx.blit(img, up(cb.fuel_cut(), 12), 760, 560, k, k, 4 * math.sin(t * 3), anchor='center')
    P3.draw(img, t)
    cb.pill(img, t, DMG + 0.05, T4 - 0.15, 'TOO LONG = DAMAGE', Engine.BLOCK, (470, 400), '#e8343f', '#ffffff', '#a01c26')
    z = lerp(1.2, 1.06, oc(prog(t, T3, 0.7))) + 0.04 * hot
    return D.camera(img.convert('RGB'), t, z, 620, 860, 4 + 10 * hot)


# ------------------------------------------------------------------ shot 4: the question
P4 = Presenter([(-9, dict(visible=True, path=Fn(lambda t: (300, 1600)), size=9, legs='stand', arms='shrug', expr='smile', ground=1600,
                          look_camera=True, squash=True)),
                (ws(30) + 0.3, dict(arms=('aim', -12), expr='grin', squash=True))], words=WORDS)


def shot_ask(t):
    img = G.frame(t).convert('RGBA')
    fg = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    fx.blit(fg, up(cb.rpm_gauge(cb.rpm_deg(0.86 - limiter(t)), pulse(t, 8)), 4), 780, 1420 + 8 * math.sin(t * 2), anchor='center')
    img.alpha_composite(G.rim(fg)); P4.draw(img, t)
    return D.camera(img.convert('RGB'), t, lerp(1.15, 1.04, oc(prog(t, T4, 0.6))), 540, 1300, 5)


SCENE = D.sequence([(-9, shot_dash), (T2, shot_dial), (T3, shot_engine), (T4, shot_ask)])


def overlay(cv, t):
    ov.headline(cv, t, T2 - 0.25, HOOK, y=430)
    if t >= END_T: ov.headline(cv, max(-0.35, t - DUR), T2 - 0.25, HOOK, y=430)
    ov.poll(cv, t, ws(30) - 0.1, END_T - 0.1, 'Ever go in the red?', ov.SAFE_CX, 640, 0.9)


CUES = [(0.0, 'vroom', 1.0), (0.05, 'whoosh', 0.6), (0.62, 'beep', 0.9), (ws(5), 'beep', 0.8), (T2 + 0.25, 'pop', 0.6),
        (T2 + 0.3, 'beep', 1.0), (T2 + 0.95, 'beep', 0.7), (T3 + 0.1, 'vroom', 0.8), (DMG, 'vroom', 0.6),
        (DMG + 0.05, 'pop', 0.6), (ws(22), 'buzzer', 0.5), (ws(22), 'thump', 0.6), (CUT, 'poof', 0.7), (CUT, 'click', 0.9),
        (CUT + 0.05, 'pop', 0.6), (ws(30) - 0.1, 'pop', 0.8), (ws(30), 'sparkle', 0.5), (END_T, 'whoosh', 0.6)]

D.wire(HERE, WORDS, DUR, END_T, SCENE, [T2, T3, T4], CUES, KEYCOL, overlay, cap=(ws(7) - 0.05, 1075))

if __name__ == '__main__':
    D.cli()
