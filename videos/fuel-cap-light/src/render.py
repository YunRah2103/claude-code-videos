"""Renders 'car stuff, explained': engine light on? check the fuel cap (14 s, loops).

Shots (timed to words.json, faster-whisper on out/fuel-cap-light/voiceover.wav; the mixer holds a 1.0 s pause after
'clicks,' so the drive beat has room, and the words after it are shifted to match):
  1 dash    0.00  dashboard close-up, the engine warning light already flashing amber on frame 0; headline
  2 cap     1.80  fuel flap open, the cap loose (wobbling, fuel vapour leaking): LOOSE CAP; he turns it until it clicks
  3 drive   7.25  night street, the car drives on; three drive ticks pop in, the warning light goes out
  4 ask     8.87  garage: presenter asks, poll 'Did you know that? YES / NO'; whips back to shot 1 (loop)
    python render.py still <dir> t... | safecheck | safestill <dir> t... | cover <png> | video <vo.wav> <out.mp4> [t0 t1]
"""
import math, os, sys
from functools import lru_cache
from PIL import Image, ImageDraw, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared'))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared', 'assets'))
import episode as kit
from episode import W, H, RED, YEL, GRN, WHITE
from backdrops.garage import Garage
from pixanim.motion import prog, lerp, io, oc
from pixanim.presenter import Presenter, Fn
from pixanim.dash import Dashboard
from pixanim.grid import up
from pixanim import fx
from assets import overlays as ov, carbits as cb
import dashep as D

GAP_T, GAP_D = 6.25, 1.0                            # held pause after 'clicks,'
WORDS = kit.shift_words(kit.load_words(HERE), GAP_T, GAP_D)
def ws(i): return WORDS[i]['s']

DUR, END_T = 14.0, 13.62
T2, TIGHT, CLICK = ws(5) - 0.1, ws(13), ws(17) + 0.12
T3, T4 = ws(18) - 0.15, ws(24) - 0.15
TICKS = [ws(19), ws(21) + 0.1, ws(23)]
LAMP_OFF = ws(23) + 0.45
G = Garage(W, H, 1520, 9)
DASH = Dashboard(outside=Garage(W, H, 1180, 9).base())
LAMP = (482, 1047)                                  # the ENG lamp slot on the dashboard
HOOK = ((('ENGINE', None),), (('LIGHT', '#ffd93b'), ('ON?', None)))
KEYCOL = {'light': YEL, 'fuel': YEL, 'loose': RED, 'trigger': YEL, 'tighten': YEL, 'clicks': YEL, 'know': YEL}


def flash(t): return (t * 3.2) % 1 < 0.6


@lru_cache(2)
def bloom(r=230):
    g = Image.new('L', (2 * r, 2 * r), 0); ImageDraw.Draw(g).ellipse((r // 3, r // 3, 2 * r - r // 3, 2 * r - r // 3), fill=150)
    return g.filter(ImageFilter.GaussianBlur(r // 4))


def lamp(img, t, xy, s, on):
    if on:
        b = bloom(); img.paste((255, 150, 30, 255), (int(xy[0] - b.width / 2), int(xy[1] - b.height / 2)), b)
    fx.blit(img, up(cb.warn_lamp(on), s), xy[0], xy[1], anchor='center')


# ------------------------------------------------------------------ shot 1: the warning light
P1 = Presenter([(-9, dict(path=Fn(lambda t: (230, 1560)), size=6, legs='stand', arms='point', point=LAMP, expr='shock',
                          ground=None, look=LAMP))], words=WORDS)


def shot_dash(t):
    img = DASH.frame(t, rpm_deg=205 + 1.3 * math.sin(t * 31)).copy()
    lamp(img, t, LAMP, 5, flash(t))
    if flash(t): fx.ring(img, (t * 3.2) % 1 / 3.2, 0, *LAMP, (255, 170, 60), life=0.3, r1=220)
    P1.draw(img, t)
    z = lerp(1.75, 1.4, oc(prog(t, -0.6, 1.4))); sh = 8 + 14 * math.exp(-max(0, t) * 2)
    return D.camera(img.convert('RGB'), t, z, LAMP[0], LAMP[1] - 60, sh)


# ------------------------------------------------------------------ shot 2: the fuel cap
PS, PX, PY = 11, 540, 1150                          # sprite bottom-centre
CAP = (PX - 48 * PS + cb.CAP_XY[0] * PS + PS // 2, PY - 70 * PS + cb.CAP_XY[1] * PS + PS // 2)
P2 = Presenter([(-9, dict(visible=True, path=Fn(lambda t: (880, 1700)), size=7, legs='stand', arms='point', point=CAP, expr='smile',
                          ground=None, look=CAP, squash=True)),
                (TIGHT, dict(arms=('aim', 60), expr='grin')),
                (CLICK, dict(arms='cheer', expr='grin', squash=True))], words=WORDS)


def cap_rot(t):
    if t < TIGHT: return 18 * math.sin(t * 7)
    return 18 * math.sin(TIGHT * 7) - 320 * io(prog(t, TIGHT, CLICK - TIGHT))


def shot_cap(t):
    img = G.frame(t).convert('RGBA'); fg = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    loose = t < CLICK
    pop = 0 if not loose else 4 + 3 * math.sin(t * 13)                        # loose cap sits proud and rattles
    fx.blit(fg, up(cb.fuel_cap(cap_rot(t), 1.0), PS), PX, PY, anchor='bottom')
    if loose:
        for k in range(3):                                                    # fuel vapour seeping out
            fx.puff(fg, t, math.floor((t - k * 0.33) / 1.0) * 1.0 + k * 0.33, CAP[0] + 60, CAP[1] - 120, seed=k + 3, life=0.9, size=0.5,
                    drift=(160, -240), col=(214, 222, 200))
    else:
        fx.burst(fg, t, CLICK, *CAP, (255, 210, 63), n=12, r0=180, r1=380); fx.ring(fg, t, CLICK, *CAP, (255, 255, 255), life=0.35, r1=260)
        fx.sparkles(fg, t, CAP[0], CAP[1], 400, 400, n=6, seed=7)
    img.alpha_composite(G.rim(fg)); P2.draw(img, t)
    cb.pill(img, t, ws(8) - 0.05, TIGHT - 0.1, 'LOOSE CAP', (CAP[0] + 90, CAP[1] - 110 - pop), (600, 420), '#ffd23f', '#1a1a2e', '#e8b923')
    z = lerp(1.22, 1.08, oc(prog(t, T2, 0.6))) + (0.05 * math.exp(-(t - CLICK) * 6) if t >= CLICK else 0)
    return D.camera(img.convert('RGB'), t, z, 540, 860, 4 + (14 * math.exp(-(t - CLICK) * 5) if t >= CLICK else 0))


# ------------------------------------------------------------------ shot 3: a few drives
def shot_drive(t):
    scroll = 700 * (t - T3)
    img = kit.street(t, scroll); fg = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    kit.headlights(fg, 540 + 45 * 9, kit.ROAD_Y - 120, 380)
    kit.draw_car(fg, 'red', 540, 9, y=kit.ROAD_Y, dist=scroll, lights=True)
    img.alpha_composite(fg)
    for i, t0 in enumerate(TICKS):
        if t >= t0:
            k = fx.popin(t, t0, 0.25); fx.blit(img, up(cb.tick(True), 10), 300 + 170 * i, 640, k, k, 6 * math.sin(t * 3 + i), anchor='center')
            fx.burst(img, t, t0, 300 + 170 * i, 640, (90, 220, 120), n=8, r0=70, r1=170)
        else:
            fx.blit(img, up(cb.tick(False), 10), 300 + 170 * i, 640, anchor='center')
    lamp(img, t, (840, 640), 7, t < LAMP_OFF and flash(t))
    if t >= LAMP_OFF: fx.ring(img, t, LAMP_OFF, 840, 640, (90, 220, 120), life=0.35, r1=180)
    return D.camera(img.convert('RGB'), t, 1.06, 540, 900, 4)


# ------------------------------------------------------------------ shot 4: the question
P4 = Presenter([(-9, dict(visible=True, path=Fn(lambda t: (300, 1600)), size=9, legs='stand', arms='shrug', expr='smile', ground=1600,
                          look_camera=True, squash=True)),
                (ws(26), dict(arms=('aim', -12), expr='grin', squash=True))], words=WORDS)


def shot_ask(t):
    img = G.frame(t).convert('RGBA'); fg = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    fx.blit(fg, up(cb.fuel_cap(-320 + 10 * math.sin(t * 2), 1.0), 4), 790, 1580 + 8 * math.sin(t * 2), anchor='bottom')
    img.alpha_composite(G.rim(fg)); P4.draw(img, t)
    return D.camera(img.convert('RGB'), t, lerp(1.15, 1.04, oc(prog(t, T4, 0.6))), 540, 1300, 5)


SCENE = D.sequence([(-9, shot_dash), (T2, shot_cap), (T3, shot_drive), (T4, shot_ask)])


def overlay(cv, t):
    ov.headline(cv, t, ws(3) - 0.15, HOOK, y=440)
    if t >= END_T: ov.headline(cv, max(-0.35, t - DUR), ws(3) - 0.15, HOOK, y=440)
    ov.chip(cv, t, ws(19) - 0.05, T4 - 0.1, 'GIVE IT A FEW DRIVES', ov.SAFE_CX, 420, GRN, 60, rot=-3)
    ov.poll(cv, t, ws(24) - 0.1, END_T - 0.1, 'Did you know that?', ov.SAFE_CX, 640, 0.9)


CUES = [(0.0, 'beep', 1.0), (0.05, 'whoosh', 0.6), (0.62, 'beep', 0.8), (ws(3), 'beep', 0.6), (ws(8) - 0.05, 'pop', 0.7),
        (ws(8), 'poof', 0.4), (TIGHT, 'creak', 0.5), (CLICK - 0.06, 'click', 1.0), (CLICK, 'click', 1.0), (CLICK + 0.02, 'sparkle', 0.7),
        (T3 + 0.05, 'vroom', 0.6), (ws(19) - 0.05, 'pop', 0.7)] + [(t0, 'ding', 0.5 + 0.15 * i) for i, t0 in enumerate(TICKS)] + [
        (LAMP_OFF, 'click', 0.8), (LAMP_OFF + 0.02, 'sparkle', 0.6), (ws(24) - 0.1, 'pop', 0.8), (END_T, 'whoosh', 0.6)]

D.wire(HERE, WORDS, DUR, END_T, SCENE, [T2, T3, T4], CUES, KEYCOL, overlay, cap=(ws(3) - 0.05, 1075, [(ws(18) - 0.1, T4)]),
       gap=(GAP_T, GAP_D))

if __name__ == '__main__':
    D.cli()
