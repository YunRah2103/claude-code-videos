"""Renders 'car stuff, explained' ep 2: why cold mornings are hard on batteries (13 s, loops).

Shots (timed to words.json, faster-whisper on out/cold-battery/voiceover.wav):
  1 cold    0.00  icy garage, snow falling, battery icon already flickering on frame 0, snowflake pops; headline COLD
  2 cells   T2    battery cutaway: ions slow down as the cells frost over, SLOWER callout
  3 crank   T3    starter motor turning the flywheel slowly, battery bar draining, ENGINE NEEDS MORE POWER
  4 ask     T4    icy garage: presenter asks, poll 'Does yours start first time? YES / NO'; whips back to shot 1 (loop)
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
from pixanim.grid import up
from pixanim import fx, autos
from assets import overlays as ov, carbits as cb, garagebits as gb
import dashep as D

WORDS = kit.load_words(HERE)
def ws(i): return WORDS[i]['s']
def we(i): return WORDS[i]['e']

DUR, END_T = 13.0, 12.62
T2, T3, T4 = ws(6) - 0.3, ws(12) - 0.3, ws(21) - 0.5    # 'Cold slows', 'The engine', 'Does your car'
SLOW = ws(7)                                           # 'slows'
G = Garage(W, H, 1520, 9)
BLUE = (79, 179, 255)
HOOK = ((('COLD', '#4fb3ff'), ('MORNINGS', None)), (('are HARD on batteries', None),))
KEYCOL = {'slows': BLUE, 'chemical': YEL, 'more': YEL, 'power': YEL, 'winter?': BLUE}


def icy(t, k=1.0):
    """The garage, cooled blue, with falling snow and frosted corners."""
    img = G.frame(t).convert('RGBA')
    img.alpha_composite(Image.new('RGBA', (W, H), (40, 90, 160, int(70 * k))))
    gb.snow(img, t); gb.frost(img, 0.8 * k)
    return img


def flicker(t):
    """Battery level flicker: fast irregular blink between weak and dead (already running on frame 0)."""
    v = math.sin(t * 31) + math.sin(t * 17.3 + 1)
    return 0.2 if v > 0.4 else 0.4 if v > -0.6 else 0.1


# ------------------------------------------------------------------ shot 1: cold garage hook
P1 = Presenter([(-9, dict(path=Fn(lambda t: (260 + 4 * math.sin(t * 40), 1640)), size=7, legs='stand', arms='brace',
                          expr='shock', ground=None, look_camera=True, squash=True)),
                (ws(3), dict(arms='shrug', expr='sad', squash=True))], words=WORDS)


def shot_cold(t):
    img = icy(t)
    fg = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    bat = up(autos.battery(flicker(t)), 9)
    fx.blit(fg, bat, 760, 1120 + 8 * math.sin(t * 3), 1, 1, 3 * math.sin(t * 5), anchor='center')
    if flicker(t) < 0.15: fx.ring(fg, t % 0.25, 0, 760, 1120, (255, 90, 90), life=0.25, r1=260)
    k = fx.popin(t, -0.15, 0.35)
    fx.blit(fg, up(gb.snowflake(), 14), 790, 1460, k, k, 25 * t, anchor='center')
    img.alpha_composite(fg); P1.draw(img, t)
    z = lerp(1.5, 1.04, oc(prog(t, -0.5, 1.4))); sh = 16 + 28 * math.exp(-max(0, t) * 1.6)
    return D.camera(img.convert('RGB'), t, z, 560, 1200, sh)


# ------------------------------------------------------------------ shot 2: battery cutaway, the reaction slows
BS = 8
BAT_XY = (540, 900)


def bat_rate(t): return lerp(1.0, 0.18, io(prog(t, SLOW, 1.2)))


def bat_phase(t):
    """Integrated ion time, so slowing the rate never makes the ions jump backwards."""
    a, b = SLOW, SLOW + 1.2
    if t <= a: return t
    u = min(t, b); x = (u - a) / 1.2
    p = a + 1.2 * (x - 0.82 * (x ** 3 - x ** 4 / 2))   # integral of lerp(1, .18, io(x)) with io = 3x^2 - 2x^3
    return p + 0.18 * max(0, t - b)


def shot_cells(t):
    img = icy(t, 0.7)
    fg = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    cold = oc(prog(t, SLOW, 1.4))
    bat = up(gb.battery_cutaway(bat_phase(t), 1.0, cold, 0.6 - 0.25 * cold), BS)
    fx.blit(fg, bat, BAT_XY[0], BAT_XY[1] + 5 * math.sin(t * 2), anchor='center')
    img.alpha_composite(G.rim(fg))
    k = fx.popin(t, SLOW, 0.3)
    fx.blit(img, up(gb.snowflake(), 8), 880, 600, k, k, 10 * t, anchor='center')
    cb.pill(img, t, SLOW + 0.1, T3 - 0.1, 'SLOWER', (BAT_XY[0] - 120, BAT_XY[1] - 40), (360, 520), '#4fb3ff', '#ffffff', '#2a6fb0')
    z = lerp(1.22, 1.06, oc(prog(t, T2, 0.6))) + 0.04 * cold
    return D.camera(img.convert('RGB'), t, z, 540, 900, 5)


# ------------------------------------------------------------------ shot 3: slow crank
GEAR_XY, PIN_XY = (600, 900), (300, 1160)


def crank_deg(t):
    """Laboured cranking: each tooth step slows and lurches (no full speed)."""
    u = max(0.0, t - T3)
    return 40 * u + 9 * math.sin(u * 2 * math.pi * 1.1)


P3 = Presenter([(-9, dict(visible=False, path=Fn(lambda t: (600, 1700)))),
                (T3 + 0.3, dict(visible=True, size=5, legs='stand', arms='brace', expr='think', ground=None, squash=True)),
                (ws(16), dict(arms='push', expr='shock', squash=True))], words=WORDS)


def shot_crank(t):
    img = icy(t, 0.6)
    fg = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = crank_deg(t)
    fx.blit(fg, up(gb.gear(d, 30, 34), 9), *GEAR_XY, 1, 1, 0, anchor='center')
    fx.blit(fg, up(gb.gear(-d * 4, 8, 9, (200, 170, 90)), 9), PIN_XY[0] + 150, PIN_XY[1] - 40, 1, 1, 0, anchor='center')
    on = 0.5 + 0.5 * math.sin(t * 9)
    fx.blit(fg, up(autos.motor(on), 9), PIN_XY[0] - 30, PIN_XY[1] + 40, anchor='center')
    lv = max(0.1, 0.6 - 0.4 * prog(t, T3, T4 - T3))
    fx.blit(fg, up(autos.battery(round(lv, 1)), 6), 900, 1520, anchor='center')
    if (t - T3) % 0.9 < 0.1: fx.puff(fg, t, t - (t - T3) % 0.9, PIN_XY[0] - 120, PIN_XY[1] - 40, size=0.6)
    img.alpha_composite(G.rim(fg)); P3.draw(img, t)
    cb.pill(img, t, ws(12) - 0.05, T4 - 0.15, 'ENGINE NEEDS MORE POWER', (GEAR_XY[0] - 60, GEAR_XY[1] - 300), (460, 430),
            '#ffd23f', '#1a1a2e', '#e8b923')
    z = lerp(1.2, 1.06, oc(prog(t, T3, 0.7)))
    return D.camera(img.convert('RGB'), t, z, 560, 980, 4 + 6 * on)


# ------------------------------------------------------------------ shot 4: the question
P4 = Presenter([(-9, dict(visible=True, path=Fn(lambda t: (300 + 3 * math.sin(t * 38), 1600)), size=9, legs='stand', arms='brace',
                          expr='smile', ground=1600, look_camera=True, squash=True)),
                (ws(24), dict(arms=('aim', -12), expr='grin', squash=True))], words=WORDS)


def shot_ask(t):
    img = icy(t)
    fg = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    fx.blit(fg, up(autos.battery(flicker(t)), 7), 800, 1420 + 10 * math.sin(t * 2), 1, 1, 6 * math.sin(t * 1.7), anchor='center')
    img.alpha_composite(G.rim(fg)); P4.draw(img, t)
    return D.camera(img.convert('RGB'), t, lerp(1.15, 1.04, oc(prog(t, T4, 0.6))), 540, 1300, 5)


SCENE = D.sequence([(-9, shot_cold), (T2, shot_cells), (T3, shot_crank), (T4, shot_ask)])


def overlay(cv, t):
    ov.headline(cv, t, T2 - 0.25, HOOK, y=430)
    if t >= END_T: ov.headline(cv, max(-0.35, t - DUR), T2 - 0.25, HOOK, y=430)
    ov.poll(cv, t, ws(21) - 0.1, END_T - 0.1, 'Does yours start first time?', ov.SAFE_CX, 640, 0.9)


CUES = [(0.0, 'whoosh', 0.7), (0.02, 'buzzer', 0.4), (0.05, 'sparkle', 0.6), (ws(3), 'thump', 0.5), (SLOW, 'slide_down', 0.6),
        (SLOW + 0.1, 'pop', 0.6), (T3 + 0.05, 'whirr', 1.0), (T3 + 1.0, 'whirr', 1.0), (T3 + 1.95, 'whirr', 0.9),
        (ws(12) - 0.05, 'pop', 0.7), (ws(21) - 0.1, 'pop', 0.8), (ws(24), 'sparkle', 0.5), (END_T, 'whoosh', 0.6)]

D.wire(HERE, WORDS, DUR, END_T, SCENE, [T2, T3, T4], CUES, KEYCOL, overlay,
       cap=(T2 - 0.05, 1075, ((ws(12) - 0.05, T4),)))   # the pill already says the 'engine needs more power' line

if __name__ == '__main__':
    D.cli()
