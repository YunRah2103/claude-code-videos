"""Renders 'Car stuff, explained': why the engine revs up when the A/C turns on. V2: directed as a miniature film.

Shots (all timed to the aligned voiceover and the unchanged sound cues):
  1 dash1   0.00  dashboard close-up: he flies in, presses A/C, the rev needle jumps, he recoils toward camera
  2 garage  2.45  whip-pan follow; he lands on the car roof, calms the worry, stomps the NOT BROKEN stamp, opens the bonnet
  3 engine  4.60  iris into the bay: animated cutaway, he orbits the compressor, clutch engages, load, he braces the crank
  4 idle    6.26  he flies into the lens; rev counter close-up: he lifts the needle, IDLE UP
  5 split   7.96  dive down into a split-screen comparison: no idle boost stalls, idle boost runs (presenter off-stage)
  6 street  10.26 he pushes the split aside; side-scrolling convoy, the ECU signals every car
  7 dash2   12.40 zoom through a windscreen; he sits on the cluster, the needle jumps, NORMAL
  8 teaser  15.38 whip to the garage: confetti, he lifts the sheet on the next episode; loops back to shot 1
"""
import json, math, os, sys, subprocess
from functools import lru_cache
from multiprocessing import Pool
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import pix, sfx
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'shared'))
from backdrops.garage import Garage
from pixanim.motion import Track, Orbit, Seq, clamp, prog, lerp, ob, oc, ic, io, springs, wob
from pixanim.camera import Camera
from pixanim.presenter import Presenter, Fn, reach
from pixanim import fx, transitions as T, diagram as dg
from pixanim.fx import blit, popin, popout
from pixanim.car import car, wheel_deg, ROOF as CAR_ROOF, BAY as CAR_BAY, EXHAUST as CAR_EXH, HEADLIGHT as CAR_HL
from pixanim.dash import Dashboard, _gauge_face
from pixanim.engine import Engine, crank_angle
from pixanim.street import Street
from pixanim.props import robot, sheet
from pixanim.grid import up

W, H, FPS, S = 1080, 1920, 60, 9
GROUND = 1180
DUR = 17.1
BG = (14, 15, 18)
NAVY = (26, 26, 46)
VO_OFF = 0.0  # the voice starts on frame 0 so the hook lands immediately
LEAD = VO_OFF
GAR = Garage(W, H, GROUND, S)
WORDS = [dict(w, s=round(w['s'] + VO_OFF, 2), e=round(w['e'] + VO_OFF, 2)) for w in json.load(open('words.json'))]


@lru_cache(None)
def big(name, *args, s=S):          # episode sprites (progress-bar car)
    return pix.up(getattr(pix, name)(*args), s)


@lru_cache(None)
def world(name):
    if name == 'dash': return Dashboard(outside=GAR.base())
    if name == 'engine': return Engine()
    if name == 'street': return Street()
    if name == 'road_refl': return Garage(W, H, Street.ROAD_Y, S)
    raise KeyError(name)


def layer(): return Image.new('RGBA', (W, H), (0, 0, 0, 0))


GLOW_Y, GLOW_G, GLOW_R = (255, 214, 90, 50), (110, 230, 140, 40), (255, 96, 96, 38)
IDLE = 205
TACH, BTN = Dashboard.TACHO, Dashboard.AC_BTN


def shiver(t): return 1.3 * math.sin(t * 31) + 0.6 * math.sin(t * 53)


def rev_marks(cv, t, t0, x, y, r=250, life=0.7):
    if not (t0 <= t < t0 + life) or int(t * 20) % 2 == 0: return
    d = ImageDraw.Draw(cv)
    for a in (-160, -125, -90, -55, -20):
        rr = r + 40 * prog(t, t0, life)
        x0, y0 = x + rr * math.cos(math.radians(a)), y + rr * math.sin(math.radians(a))
        d.rectangle((x0 - S, y0 - S, x0 + S, y0 + S), fill=(255, 210, 63), outline=NAVY, width=3)


def vroom(cv, t, t0, x, y):
    if t < t0 or t > t0 + 1.0: return
    k = popin(t, t0, 0.2) * (1 - ic(prog(t, t0 + 0.8, 0.2)))
    sw = 10 * math.sin(2 * math.pi * 2.0 * (t - t0)) * math.exp(-0.9 * (t - t0))
    blit(cv, fx.big('label', 'VROOM', '#ffd23f', s=9), x, y, k, k, sw, anchor='center')


def finish(img, fg, cam, t, rim=True):
    """Composite a foreground layer (rim-lit) over a world image, then frame it with the shot camera."""
    if rim: fg = GAR.rim(fg)
    img = img.copy(); img.alpha_composite(fg)
    return cam.apply(img.convert('RGB'), t, BG)


# ================================================================== shot 1: dashboard hook
def rpm1(t): return springs(t, IDLE, [(1.05, IDLE + 8, 14, 8), (1.88, 176, 17, 5)]) + shiver(t)
def tip1(t): return world('dash').needle_tip(rpm1(t))

PRESS = reach((548, 1236), 50, 5, -1).at(0)
P1 = Presenter([
    (-1.0, dict(path=Track([(-1.0, (1500, 860)), (0.0, (900, 960)), (0.42, (PRESS[0] + 14, PRESS[1] - 36), 'oc'),
                            (0.55, (PRESS[0] + 4, PRESS[1] - 14), 'io'), (0.6, PRESS, 'ic'), (0.8, (PRESS[0] + 8, PRESS[1] - 20), 'oc'),
                            (1.3, (720, 1010), 'io'), (1.86, (700, 998), 'sine'), (2.06, (640, 1160), 'oc'),
                            (2.3, (620, 1130), 'sine'), (2.62, (-260, 820), 'back')], smooth=True),
                size=Track([(1.86, 5), (2.06, 7, 'oc'), (2.32, 7), (2.6, 6)]),
                legs='auto', arms='fly', expr='grin', look=BTN, face=-1, hover=8)),
    (0.34, dict(arms=('aim', 50))),
    (0.6, dict(squash=True, expr='smirk')),
    (0.8, dict(arms='point', point=tip1, look=tip1, face=None, expr='smile')),
    (1.05, dict(expr='think')),
    (1.88, dict(arms='shock', expr='shock', squash=True, point=None)),
    (2.14, dict(arms='point', point=tip1, expr='wow')),
    (2.36, dict(arms='fly', point=None, look=None, face=-1, expr='grin')),
], words=WORDS, base_size=5)
CAM1 = Camera(W, H, [(-1.0, (560, 1060, 1.45)), (0.0, (560, 1060, 1.45)), (0.6, (560, 1110, 1.5), 'io'),
                     (1.3, (470, 930, 1.36), 'io'), (1.86, (450, 900, 1.33)), (2.3, (430, 880, 1.3), 'io'), (2.68, (360, 900, 1.3))],
              kicks=[(-0.02, 0.08, 560, 1060), (0.57, 0.06, *BTN), (1.88, 0.2, *TACH), (2.14, 0.05, *TACH)],
              shakes=[(1.88, 0.4, 24)])


def press1(t):
    if 0.5 <= t < 0.57: return prog(t, 0.5, 0.07)
    if 0.57 <= t < 0.72: return 1.0
    if 0.72 <= t < 0.84: return 1 - prog(t, 0.72, 0.12)
    return 0.0


def shot_dash1(t):
    D = world('dash')
    img = D.frame(t, rpm_deg=rpm1(t), ac_on=t >= 0.57, press=press1(t))
    fg = layer()
    for i, (vx, vy) in enumerate(D.VENTS):
        fx.flakes(fg, t, 0.62, vx, vy - 20, n=7, seed=61 + i, spread=170, rise=320)
    fx.ring(fg, t, 0.57, *BTN, (127, 212, 255), life=0.35, r1=200)
    if 0.57 <= t < 1.4:
        k = popin(t, 0.6, 0.2) * popout(t, 1.2)
        blit(fg, fx.big('label', 'CLICK!', '#ffffff', s=7), BTN[0] + 120, BTN[1] - 120, k, k, 10 + 3 * math.sin(t * 6), anchor='center')
    fx.glint(fg, t, 0.12, *TACH, r=200); fx.glint(fg, t, 2.0, *TACH, r=200)
    fx.ring(fg, t, 1.9, *TACH, (255, 210, 63), life=0.4, r1=300)
    fx.burst(fg, t, 1.88, *TACH, r0=230, r1=430)
    rev_marks(fg, t, 1.88, *TACH, r=240)
    P1.draw(fg, t)
    if 1.88 <= t < 2.5:
        x, y = P1.pos(t); s = P1.size(t)
        kx = popin(t, 1.88, 0.22) * (1 + 0.08 * math.sin(t * 14))
        blit(fg, fx.big('glyph', '!', '#e0303a', s=10), x - 10, y - 66 * s, kx, kx, -8, anchor='center')
    return finish(img, fg, CAM1, t)


# ================================================================== shot 2: garage, car, NOT BROKEN
CAR_X, CS = 520, 8
def cpx(gx, gy): return (CAR_X - 45 * CS + gx * CS, GROUND - 50 * CS + gy * CS)
ROOF_Y = cpx(*CAR_ROOF)[1]
BONNET_Y = 996
BAY_PX = cpx(*CAR_BAY)
STAMP_AT = cpx(40, 33)
QMARKS = [(cpx(24, 4), 2.88), (cpx(48, -2), 3.0), (cpx(70, 6), 3.12)]
TICK2 = (760, 870)

P2 = Presenter([
    (2.40, dict(path=Track([(2.40, (1240, 380)), (2.62, (500, ROOF_Y), 'ic'), (3.44, (500, ROOF_Y)), (3.66, (500, ROOF_Y - 170), 'oc'),
                            (3.81, (500, ROOF_Y), 'ic'), (4.38, (500, ROOF_Y)), (4.48, (690, ROOF_Y - 120), 'oc'), (4.56, (770, BONNET_Y), 'ic'),
                            (4.9, (790, BONNET_Y))]),
                size=8, legs='auto', arms='fly', expr='grin', face=-1, ground=None)),
    (2.61, dict(ground=ROOF_Y, arms='down', expr='smile', face=None, look=lambda t: QMARKS[1][0])),
    (2.62, dict(squash=True)),
    (2.88, dict(arms='shrug', look=None, look_camera=True, face=1)),
    (3.3, dict(arms='talkB')),
    (3.45, dict(squash=True)),
    (3.52, dict(arms='cheer1', expr='grin')),
    (3.81, dict(squash=True, arms='hips', expr='smirk')),
    (4.25, dict(arms='thumb', expr='grin')),
    (4.4, dict(ground=None, arms='fly', look=BAY_PX, look_camera=False)),
    (4.55, dict(ground=BONNET_Y, squash=True, arms='hold', expr='wow')),
], words=WORDS, base_size=8)
CAM2 = Camera(W, H, [(2.40, (540, 960, 1.12)), (3.6, (520, 930, 1.1)), (4.3, (560, 950, 1.12)), (4.62, (700, 980, 1.3), 'io'), (4.9, (720, 990, 1.35))],
              kicks=[(2.62, 0.06, 500, 900), (3.81, 0.12, *STAMP_AT), (4.25, 0.05, *TICK2)], shakes=[(3.81, 0.35, 22)])


def shot_garage(t):
    img = GAR.frame(t).convert('RGBA')
    fg = layer()
    lights = 4.25 <= t < 4.33 or 4.41 <= t < 4.49
    bon = oc(prog(t, 4.56, 0.16))
    sx, sy = wob(t, (2.62, 3.81, 4.56), 0.04)
    fx.contact_shadow(fg, CAR_X, GROUND, 700, s=CS, alpha=130)
    if lights:   # headlight beam across the floor
        d = ImageDraw.Draw(fg); hx, hy = cpx(*CAR_HL)
        d.polygon([(hx, hy - 10), (hx + 400, hy - 90), (hx + 400, hy + 160), (hx, hy + 16)], fill=(255, 248, 210, 60))
    blit(fg, up(car('red', 0, lights, False, round(bon * 20) / 20), CS), CAR_X, GROUND, sx, sy)
    ex, ey = cpx(*CAR_EXH)
    for k in range(7):
        fx.puff(fg, t, 2.4 + k * 0.36, ex - 20, ey, seed=80 + k, life=0.8, size=0.8, drift=(-160, -90))
    for (qx, qy), t0 in QMARKS:
        if t0 <= t < 3.81:
            kq = popin(t, t0, 0.25)
            blit(fg, fx.big('glyph', '?', '#e0303a', s=10), qx, qy + 10 * math.sin(t * 7 + t0 * 9), kq, kq, 8 * math.sin(t * 5 + t0), anchor='center')
        fx.poof(fg, t, 3.81, qx, qy, seed=int(t0 * 10), life=0.4, scale=0.35)
    fx.dust(fg, t, 3.83, cpx(21, 49)[0], GROUND - 10, n=10, seed=43); fx.dust(fg, t, 3.83, cpx(69, 49)[0], GROUND - 10, n=10, seed=44)
    P2.draw(fg, t)
    fx.dust(fg, t, 2.62, 500, ROOF_Y, n=8, seed=41, life=0.4)
    fx.stamp_at(fg, t, 3.81, 'NOT BROKEN', *STAMP_AT, -8, 8)
    fx.burst(fg, t, 3.81, *STAMP_AT, (224, 48, 58), seed=72)
    if 4.25 <= t < 4.5:
        kc = popin(t, 4.25) * popout(t, 4.42, 0.08)
        blit(fg, fx.big('check', s=10), *TICK2, kc, kc, anchor='center')
        fx.gsparkles(fg, t, *TICK2, 300, 240, n=8, seed=37)
    fx.burst(fg, t, 4.25, *TICK2, (60, 200, 90), n=10, r0=70, r1=240, seed=73)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM2, t)


# ================================================================== shot 3: engine cutaway
COMP_C = (170, 842)
CRANK_PX = Engine.CRANK
ORB = Orbit(4.92, 5.6, (200, 842), 150, 175, 200, 545)
PUSH_AT = (CRANK_PX[0] - 68 - 100, CRANK_PX[1] + 135)
PROFILE3 = [(4.4, 1.5), (5.65, 1.5), (5.85, 1.0), (6.6, 1.0)]

P3 = Presenter([
    (4.6, dict(path=Seq([(4.6, Track([(4.6, (-200, 360)), (4.92, ORB.at(4.92), 'oc')], smooth=True)), (4.92, ORB),
                         (5.6, Track([(5.6, ORB.at(5.6)), (5.72, (300, 1080), 'oc'), (5.86, PUSH_AT, 'io'), (6.2, PUSH_AT)]))]),
               size=5, legs='auto', arms='fly', expr='grin', face=1,
               z=lambda t: 'back' if 4.92 <= t < 5.6 and ORB.depth(t) < 0 else 'front')),
    (4.92, dict(arms='point', point=COMP_C, look=COMP_C, face=None, expr='smirk')),
    (5.65, dict(arms='shock', expr='shock', squash=True, point=None, look=CRANK_PX)),
    (5.86, dict(arms='push', expr='think', face=1, legs='run', ground=PUSH_AT[1])),
    (6.26, dict(visible=False)),
], words=WORDS, base_size=5)
CAM3 = Camera(W, H, [(4.6, (540, 900, 1.0)), (4.95, (330, 860, 1.28), 'io'), (5.6, (330, 880, 1.28)), (5.86, (420, 940, 1.2), 'io'), (6.46, (440, 960, 1.16))],
              kicks=[(4.72, 0.06, 540, 900), (4.92, 0.05, *COMP_C), (5.65, 0.14, *COMP_C), (5.7, 0.04, *CRANK_PX)], shakes=[(5.65, 0.35, 18)])


def drag_arrows(cv, t, t0, c, r=100):
    """Red arcs turning against the crank: the extra load the compressor puts on it."""
    if t < t0: return
    k = oc(prog(t, t0, 0.3)); d = ImageDraw.Draw(cv); rot = -(t - t0) * 120
    for i in range(2):
        a0 = rot + i * 180
        box = (c[0] - r, c[1] - r, c[0] + r, c[1] + r)
        d.arc(box, a0, a0 + 110 * k, fill=NAVY, width=24); d.arc(box, a0, a0 + 110 * k, fill=(232, 52, 63), width=14)
        a = math.radians(a0)
        hx, hy = c[0] + r * math.cos(a), c[1] + r * math.sin(a)
        tx, ty = -math.sin(a), math.cos(a)
        d.polygon([(hx - tx * 34, hy - ty * 34), (hx + ty * 26, hy - tx * 26), (hx - ty * 26, hy + tx * 26)], fill=(232, 52, 63), outline=NAVY)


def shot_engine(t):
    E = world('engine')
    th = crank_angle(t, PROFILE3)
    judder = (6 * math.sin(t * 60) * math.exp(-(t - 5.65) * 5), 0) if t >= 5.65 else (0, 0)
    rpm = springs(t, IDLE, [(5.68, 214, 12, 6)]) + shiver(t)
    img = E.frame(t, theta=th, clutch=t >= 5.65, clutch_t0=5.65, frost=prog(t, 5.8, 1.4), load=oc(prog(t, 5.65, 0.25)),
                  shake=judder, rpm_deg=rpm)
    fg = layer()
    back = layer(); P3.draw(back, t, 'back')
    if back.getbbox():
        img.alpha_composite(back); img.paste(E.frame(t, theta=th, clutch=t >= 5.65, clutch_t0=5.65, frost=prog(t, 5.8, 1.4),
                                                     load=oc(prog(t, 5.65, 0.25)), shake=judder, rpm_deg=rpm), (0, 0), E.comp_mask())
    fx.ring(fg, t, 4.92, *COMP_C, (127, 212, 255), life=0.35, r1=240)
    dg.label(fg, t, 4.92, 'AC COMPRESSOR', (190, 760), (330, 560), '#3d7fd6', '#ffffff', '#2b5fa8', s=5)
    if t >= 5.65:
        fx.burst(fg, t, 5.65, *COMP_C, (127, 212, 255), n=12, r0=120, r1=330, seed=74)
        fx.ring(fg, t, 5.66, *COMP_C, (160, 220, 255), life=0.3, r1=200)
        drag_arrows(fg, t, 5.68, CRANK_PX, r=100)
        dg.label(fg, t, 5.7, 'LOAD', (CRANK_PX[0] - 60, CRANK_PX[1] + 70), (230, 1190), '#e0303a', '#ffffff', '#b5222c', s=7)
    P3.draw(fg, t, 'front')
    return finish(img, fg, CAM3, t)


# lens: he launches at the camera, fills the frame, and we come out on the rev counter
def _lens_start(t=6.26):
    x, y = CAM3.to_screen(t, *P3.pos(t)); return (x, y)
PL = Presenter([
    (6.26, dict(path=Fn(lambda t: lerp(_lens_start(), (540, 2350), ic(prog(t, 6.26, 0.11))) if t < 6.37 else lerp((540, 2350), (700, 3700), prog(t, 6.37, 0.09))),
                size=Fn(lambda t: 6 + 30 * ic(prog(t, 6.26, 0.11)) + 28 * prog(t, 6.37, 0.09)),
                legs='tuck', arms='cheer1', expr='grin', face=1, trail=False, hover=0, look_camera=True)),
], base_size=6)


# ================================================================== shot 4: idle up (rev counter close-up)
def rpm4(t): return springs(t, 211, [(6.98, 188, 15, 6)]) + shiver(t)
def tip4(t): return world('dash').needle_tip(rpm4(t), frac=0.8)
LABEL4 = (300, 520)
GRAB = reach(tip4, 15, 5, 1)

P4 = Presenter([
    (6.36, dict(path=Seq([(6.36, Track([(6.36, (240, 1600)), (6.86, GRAB.at(6.86), 'oc')], smooth=True)), (6.86, GRAB),
                          (7.45, Track([(7.45, GRAB.at(7.45)), (7.68, (170, 980), 'oc'), (7.86, (180, 960), 'sine'), (8.14, (320, 2000), 'back')]))]),
                size=5, legs='auto', arms='fly', expr='grin', face=1)),
    (6.8, dict(arms=('aim', 15), look=tip4, expr='smirk')),
    (6.98, dict(expr='grin', squash=True)),
    (7.45, dict(arms='point', point=LABEL4, look=LABEL4, expr='smile')),
    (7.72, dict(arms='thumb', point=None, look=None, look_camera=True, expr='grin', face=1)),
    (7.86, dict(arms='fly', squash=True, expr='wow')),
], words=WORDS, base_size=5)
CAM4 = Camera(W, H, [(6.36, (330, 800, 1.75)), (7.3, (340, 780, 1.7)), (7.6, (380, 760, 1.6), 'io'), (8.14, (380, 900, 1.6))],
              kicks=[(6.4, 0.05, *TACH), (6.98, 0.08, 204, 823), (7.42, 0.06, *LABEL4)])


def shot_idle(t):
    D = world('dash')
    img = D.frame(t, rpm_deg=rpm4(t), ac_on=True)
    fg = layer()
    dg.glow_arc(fg, t, 7.0, *TACH, Dashboard.TACHO_R + 14, 211, 188)
    fx.ring(fg, t, 7.0, *TACH, (60, 200, 90), life=0.4, r1=280)
    fx.gsparkles(fg, t, *tip4(t), 160, 160, n=6, seed=39) if t >= 7.0 else None
    if t >= 7.42:
        dg.label(fg, t, 7.42, 'IDLE UP', tip4, LABEL4, '#3cc85a', '#ffffff', '#2a9a45', s=7)
        fx.burst(fg, t, 7.56, *LABEL4, (60, 200, 90), n=10, r0=110, r1=280, seed=75)
    fx.glint(fg, t, 6.5, *TACH, r=200)
    P4.draw(fg, t)
    return finish(img, fg, CAM4, t)


# ================================================================== shot 5: split-screen comparison
PANELS = ((40, 236, 1040, 752), (40, 786, 1040, 1302))
PROFILE_A = [(7.9, 1.05), (8.6, 1.0), (8.72, 0.5), (8.8, 0.85), (8.9, 0.35), (8.98, 0.55), (9.02, 0.2), (9.16, 0.0), (10.6, 0.0)]
PROFILE_B = [(7.9, 1.45), (10.6, 1.45)]


@lru_cache(None)
def _dial_face(r):
    img = Image.new('RGBA', (2 * r + 4, 2 * r + 4), (0, 0, 0, 0))
    _gauge_face(ImageDraw.Draw(img), r + 2, r + 2, r, red_from=6.5, label='RPM', majors=9)
    return img


def mini_dial(deg, r=40, s=3):
    img = _dial_face(r).copy(); d = ImageDraw.Draw(img); c = r + 2
    a = math.radians(deg)
    tip = (c + (r - 9) * math.cos(a), c - (r - 9) * math.sin(a))
    d.line(((c, c), tip), fill=(120, 30, 10), width=4); d.line(((c, c), tip), fill=(255, 96, 40), width=2)
    d.ellipse((c - 4, c - 4, c + 4, c + 4), fill=(90, 96, 110))
    return up(img, s)


def rpmA(t):
    if t >= 9.0: return springs(t, 212, [(9.0, 225, 10, 6)])
    return springs(t, 212, [(8.72, 220, 18, 8), (8.84, 212, 18, 8), (8.9, 222, 18, 8)]) + shiver(t)


def shot_split(t):
    E = world('engine')
    img = Image.blend(GAR.frame(t), Image.new('RGB', (W, H), (8, 8, 10)), 0.55).convert('RGBA')
    fg = layer(); d = ImageDraw.Draw(fg)
    stalled = t >= 9.05
    for i, ((x0, y0, x1, y1), prof) in enumerate(zip(PANELS, (PROFILE_A, PROFILE_B))):
        a = i == 0
        k = popin(t, 7.98 + 0.06 * i, 0.3)
        if k <= 0.02: continue
        shake = (int(10 * math.sin(t * 70)) if a and 8.72 <= t < 9.05 else 0)
        eng = E.frame(t, theta=crank_angle(t, prof), clutch=True, frost=1.0, load=1.0, firing=not (a and stalled),
                      stalled=a and stalled, as_grid=True)
        crop = up(eng.crop((8, 86, 188, 232)).convert('RGBA'), 3)
        panel = Image.new('RGBA', (x1 - x0, y1 - y0), (18, 19, 23, 255)); pd = ImageDraw.Draw(panel)
        panel.paste(crop, (10 + shake, 40))
        dial = mini_dial(rpmA(t) if a else 188 + shiver(t))
        panel.paste(dial, (x1 - x0 - dial.width - 30, 130), dial)
        if a and stalled:
            dark = Image.new('RGBA', panel.size, (0, 0, 0, 0)); ImageDraw.Draw(dark).rectangle((0, 0, *panel.size), fill=(0, 0, 0, int(90 * prog(t, 9.05, 0.3))))
            panel.alpha_composite(dark)
        pd.rounded_rectangle((0, 0, panel.width - 1, panel.height - 1), 22, outline=(150, 156, 170), width=6)
        mask = Image.new('L', panel.size, 0); ImageDraw.Draw(mask).rounded_rectangle((0, 0, panel.width - 1, panel.height - 1), 22, fill=255)
        if k != 1:
            panel = panel.resize((int(panel.width * k), int(panel.height * k)), Image.NEAREST); mask = mask.resize(panel.size, Image.NEAREST)
        fg.paste(panel, (int((x0 + x1) / 2 - panel.width / 2), int((y0 + y1) / 2 - panel.height / 2)), mask)
    for i, ((x0, y0, x1, y1), txt, cols) in enumerate(zip(PANELS, ('NO IDLE BOOST', 'IDLE BOOST'),
                                                         (('#e0303a', '#ffffff', '#b5222c'), ('#3cc85a', '#ffffff', '#2a9a45')))):
        kb = popin(t, 8.3 + 0.04 * i)
        blit(fg, fx.big('badge', txt, *cols, s=6), x0 + 60 + len(txt) * 15, y0 + 8, kb, kb, -3, anchor='center')
        ka = popin(t, 8.36 + 0.04 * i)
        blit(fg, fx.big('badge', 'AC ON', '#7fd4ff', '#1a1a2e', '#4a9ed0', s=5), x1 - 150, y1 - 40, ka, ka, 3, anchor='center')
    ax, ay = (PANELS[0][0] + 300, PANELS[0][1] + 200)
    fx.puff(fg, t, 8.72, ax, ay, seed=91, life=0.9, size=1.4, drift=(60, -200), col=(120, 122, 130))
    fx.puff(fg, t, 8.9, ax + 60, ay, seed=92, life=0.9, size=1.6, drift=(80, -220), col=(110, 112, 120))
    fx.puff(fg, t, 9.0, ax + 20, ay - 20, seed=93, life=1.2, size=2.0, drift=(40, -260), col=(96, 98, 106))
    if t >= 9.0:
        fx.stamp_at(fg, t, 9.0, 'STALL', 560, 520, -8, 11)
    if t >= 9.4:
        bx, by = 600, 1060
        kc = popin(t, 9.4)
        blit(fg, fx.big('check', s=12), bx, by, kc, kc, anchor='center')
        fx.burst(fg, t, 9.4, bx, by, (60, 200, 90), n=12, r0=90, r1=300, seed=76)
        fx.gsparkles(fg, t, bx, by, 520, 300, n=10, seed=38)
    img.alpha_composite(fg)
    return img.convert('RGB')


# push: he shoves the split screen off to the left, revealing the street
def _push_e(t): return io(prog(t, 10.26, 0.2))
PP = Presenter([
    (10.2, dict(path=Fn(lambda t: (W * (1 - _push_e(t)) + 120, 1080)), size=6, legs='run', arms='push', face=-1, expr='think', trail=False, hover=0)),
], base_size=6)


# ================================================================== shot 6: street convoy, ECU
CARS = [(280, 10.49, 'red'), (540, 10.6, 'blue'), (800, 10.71, 'silver')]
CAR3 = 3
RB = (540, 600)
WINDSCREEN = (561, 1063)
def scroll6(t): return 520 * (t - 10.26)
def car6_x(t, x, t0): return x - 900 * (1 - oc(prog(t, t0 - 0.32, 0.32)))

P6 = Presenter([
    (10.46, dict(path=Track([(10.46, (120, 1080)), (10.8, (170, 760), 'oc'), (11.2, (190, 740), 'sine'), (11.45, (330, 640), 'io'),
                             (12.05, (320, 660), 'sine'), (12.42, WINDSCREEN, 'ic')], smooth=True),
                 size=Track([(10.46, 6), (10.8, 4, 'oc'), (12.1, 4), (12.42, 2, 'ic')]),
                 legs='auto', arms='present', look=(540, 1050), expr='smile', face=1)),
    (11.3, dict(arms='point', point=RB, look=RB, expr='wow')),
    (11.65, dict(arms='cheer', point=None, look=(540, 1050), expr='grin')),
    (12.05, dict(arms='fly', look=WINDSCREEN, expr='grin')),
    (12.43, dict(visible=False)),
], words=WORDS, base_size=4)
CAM6 = Camera(W, H, [(10.26, (540, 960, 1.0)), (12.62, (540, 960, 1.0))],
              kicks=[(10.49, 0.03, 280, 1080), (10.71, 0.03, 800, 1080), (11.3, 0.08, *RB), (11.95, 0.04, 800, 1000)], clamp_view=True)


def shot_street(t):
    ST = world('street')
    sc = scroll6(t)
    img = ST.frame(t, sc).convert('RGBA')
    cars = layer()
    for x, t0, col in CARS:
        cx = car6_x(t, x, t0)
        if cx < -300: continue
        brake = t0 <= t < t0 + 0.25
        spr = up(car(col, wheel_deg(sc + cx - x, CAR3), True, brake), CAR3)
        fx.contact_shadow(cars, cx, Street.ROAD_Y, 250, s=CAR3, alpha=140)
        d = ImageDraw.Draw(cars); hx = cx + 135
        d.polygon([(hx, Street.ROAD_Y - 66), (hx + 260, Street.ROAD_Y - 110), (hx + 260, Street.ROAD_Y + 10), (hx, Street.ROAD_Y - 52)], fill=(255, 248, 210, 34))
        blit(cars, spr, cx, Street.ROAD_Y)
        fx.puff(cars, t, t0 + 0.1, cx - 140, Street.ROAD_Y - 24, seed=int(x), life=0.7, size=0.6, drift=(-120, -70))
    world('road_refl').reflect(img, cars, depth=160, strength=0.3)
    img.alpha_composite(cars)
    fg = layer(); d = ImageDraw.Draw(fg)
    if t >= 11.3:
        fx.rays(fg, t, 11.3, *RB, GLOW_Y, life=1.2, r=480)
        for i in range(3):                       # signal rings spreading from the ECU
            ph = ((t - 11.4) * 1.3 + i / 3) % 1
            if t >= 11.4:
                R = 80 + 420 * ph
                d.arc((RB[0] - R, RB[1] - R * 0.7, RB[0] + R, RB[1] + R * 0.7), 20, 160, fill=(60, 200, 90, int(200 * (1 - ph))), width=8)
        if t >= 11.5:
            for x, _, _ in CARS:
                for j in range(6):
                    u = (j / 6 + t * 1.6) % 1
                    px, py = RB[0] + (x - RB[0]) * u, RB[1] + 130 + (Street.ROAD_Y - 170 - RB[1] - 130) * u
                    d.rectangle((fx.snap(px, 3) - 6, fx.snap(py, 3) - 6, fx.snap(px, 3) + 6, fx.snap(py, 3) + 6), fill=(60, 200, 90), outline=NAVY, width=3)
    kr = popin(t, 11.3, 0.3)
    rx, ry = wob(t, (11.55,), 0.1)
    blit(fg, up(robot((t % 1.7) < 0.12, 2 if t >= 11.4 else 0), 7), RB[0], RB[1] + 12 * math.sin(t * 3), kr * rx, kr * ry, 3 * math.sin(t * 2), anchor='center')
    fx.ring(fg, t, 11.32, *RB, (255, 210, 63), life=0.4, r1=300)
    fx.burst(fg, t, 11.3, *RB, seed=77)
    if t >= 11.3: fx.sparkles(fg, t * 1.5, *RB, 480, 380, n=10, seed=52)
    ka = popin(t, 11.55)
    blit(fg, fx.big('badge', 'AUTO', '#ffd23f', '#d6303a', '#e8b923', s=6), 780, 470, ka, ka, 8 + 3 * math.sin(t * 4), anchor='center')
    for i, (x, _, _) in enumerate(CARS):
        t0 = 11.65 + i * 0.15
        if t >= t0:
            kt = popin(t, t0)
            blit(fg, fx.big('check', s=6), x, Street.ROAD_Y - 200, kt, kt, anchor='center')
            fx.ring(fg, t, t0, x, Street.ROAD_Y - 200, (60, 200, 90), life=0.3, r1=120)
    P6.draw(fg, t)
    return finish(img, fg, CAM6, t)


# ================================================================== shot 7: back in the car, NORMAL
def rpm7(t): return springs(t, IDLE, [(13.98, 176, 17, 5)]) + shiver(t)
def tip7(t): return world('dash').needle_tip(rpm7(t))
LEDGE = 505
SIT = (600, LEDGE + 70)
P7 = Presenter([
    (12.42, dict(path=Track([(12.42, (560, 2100)), (12.86, SIT, 'oc'), (13.96, SIT), (14.08, (600, SIT[1] - 70), 'oc'), (14.22, SIT, 'ic'),
                             (14.6, SIT), (14.7, (600, LEDGE), 'io'), (15.24, (600, LEDGE)), (15.62, (1400, 360), 'back')]),
                 size=Track([(12.42, 16), (12.86, 5, 'oc')]), legs='tuck', arms='fly', expr='grin', face=1, look_camera=True, hover=0)),
    (12.86, dict(legs='sit', arms='talkR', squash=True)),
    (13.4, dict(arms='point', point=tip7, look=tip7, face=-1, expr='smirk')),
    (13.98, dict(arms='cheer', expr='grin', point=None, squash=True, look_camera=True, face=1)),
    (14.6, dict(legs='stand', arms='talkR', expr='smile', ground=LEDGE)),
    (15.03, dict(arms='thumb', expr='smirk', squash=True)),
    (15.24, dict(ground=None, legs='auto', arms='fly', expr='grin')),
], words=WORDS, base_size=5)
CAM7 = Camera(W, H, [(12.42, (540, 900, 1.0)), (13.4, (520, 860, 1.05)), (13.9, (430, 790, 1.3), 'io'), (14.6, (470, 800, 1.22)),
                     (15.1, (470, 800, 1.25)), (15.6, (620, 780, 1.2))],
              kicks=[(12.6, 0.05, 540, 900), (13.48, 0.05, *TACH), (13.98, 0.18, *TACH), (15.03, 0.14, *TACH)],
              shakes=[(13.98, 0.4, 24), (15.03, 0.3, 18)])


def shot_dash2(t):
    D = world('dash')
    img = D.frame(t, rpm_deg=rpm7(t), ac_on=True)
    fg = layer()
    for i, (vx, vy) in enumerate(D.VENTS):
        fx.flakes(fg, t, 12.4, vx, vy - 20, n=5, seed=71 + i, spread=170, rise=300)
    fx.glint(fg, t, 12.7, *TACH, r=200); fx.glint(fg, t, 14.15, *TACH, r=200)
    fx.ring(fg, t, 14.0, *TACH, (255, 210, 63), life=0.4, r1=300)
    fx.burst(fg, t, 13.98, *TACH, r0=230, r1=430, seed=78)
    rev_marks(fg, t, 13.98, *TACH, r=240)
    vroom(fg, t, 14.0, TACH[0] + 40, TACH[1] - 300)
    P7.draw(fg, t)
    if t >= 15.03:
        fx.rays(fg, t, 15.03, *TACH, GLOW_G, hold=True, r=520)
        fx.gsparkles(fg, t, TACH[0], TACH[1] - 20, 600, 520, n=14, seed=49)
        fx.ring(fg, t, 15.1, *TACH, (60, 200, 90), life=0.45, r1=420)
        fx.stamp_at(fg, t, 15.03, 'NORMAL', TACH[0], TACH[1] - 10, -8, 10, '#2a9a45')
        fx.burst(fg, t, 15.03, TACH[0], TACH[1] - 10, (60, 200, 90), n=14, seed=79)
    return finish(img, fg, CAM7, t)


# ================================================================== shot 8: next-episode teaser (garage)
SHEET_X, BENCH_Y = 620, 828
SHEET_CORNER = (SHEET_X - 200, BENCH_Y - 30)
P8 = Presenter([
    (15.38, dict(path=Track([(15.38, (240, 700)), (15.72, (300, 860), 'oc'), (15.98, reach(SHEET_CORNER, 30, 8, 1).at(0), 'io'),
                             (16.36, (250, 830), 'oc'), (16.62, (260, 800), 'sine'), (17.15, (1500, 520), 'back')], smooth=True),
                 size=8, legs='auto', arms='fly', expr='grin', face=1, look=(SHEET_X, 640))),
    (15.72, dict(arms='point', point=(SHEET_X, 640), expr='smirk')),
    (15.98, dict(arms=('aim', 30), expr='wow')),
    (16.36, dict(arms='thumb', look=None, point=None, look_camera=True, expr='grin', squash=True)),
    (16.66, dict(arms='fly', expr='grin')),
], words=WORDS, base_size=8)
CAM8 = Camera(W, H, [(15.38, (600, 760, 1.15)), (16.0, (560, 740, 1.25), 'io'), (16.6, (580, 760, 1.2)), (17.1, (640, 760, 1.2))],
              kicks=[(15.8, 0.05, 560, 380), (16.0, 0.08, SHEET_X, 640)])


def shot_teaser(t):
    img = GAR.frame(t).convert('RGBA')
    fg = layer()
    lift = oc(prog(t, 16.0, 0.35)) * 0.85
    fx.rays(fg, t, 15.8, SHEET_X, 640, GLOW_Y, hold=True, r=520)
    spr = up(sheet(round(lift * 20) / 20), 8).transpose(Image.FLIP_LEFT_RIGHT)
    blit(fg, spr, SHEET_X, BENCH_Y)
    if lift > 0.3:
        fx.sparkles(fg, t * 1.6, SHEET_X - 170, BENCH_Y - 60, 120, 80, n=6, seed=58)
    dg.label(fg, t, 15.8, 'NEXT EPISODE', (SHEET_X, 500), (560, 360), '#ffd23f', '#1a1a2e', '#e8b923', s=7)
    if t >= 16.0:
        kq = popin(t, 16.0, 0.25) * (1 + 0.1 * math.sin(t * 9))
        blit(fg, fx.big('glyph', '?', '#e0303a', s=16), SHEET_X + 40, 650, kq, kq, 8 * math.sin(t * 6), anchor='center')
        fx.burst(fg, t, 16.0, SHEET_X + 40, 650, seed=81)
    P8.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM8, t)


# ================================================================== edit: shots + character-driven transitions
SHOTS = [(-1.0, shot_dash1), (2.45, shot_garage), (4.6, shot_engine), (6.26, shot_idle), (7.96, shot_split),
         (10.26, shot_street), (12.4, shot_dash2), (15.38, shot_teaser)]
SCENES = SHOTS            # progress-bar checkpoints at each shot start
TRANS = {1: (2.45, 2.68, 'whip', dict(dx=-1)), 2: (4.6, 4.86, 'iris', 'bay'), 3: (6.26, 6.46, 'lens', None),
         4: (7.96, 8.14, 'whip', dict(dx=0, dy=1)), 5: (10.26, 10.46, 'push', None), 6: (12.4, 12.62, 'iris', 'windscreen'),
         7: (15.38, 15.6, 'whip', dict(dx=1))}
LOOP = 0.3  # final whip back into the opening frame so the clip loops seamlessly
AUTH_END = DUR + LEAD


def iris_centre(kind):
    if kind == 'bay': return CAM2.to_screen(4.6, *BAY_PX)
    return CAM6.to_screen(12.4, *WINDSCREEN)


def picture(t):
    """Screen image (before vignette, captions and progress) for time t."""
    if t >= AUTH_END - LOOP:
        e = io(prog(t, AUTH_END - LOOP, LOOP))
        return T.whip(shot_teaser(t), shot_dash1(t - DUR), e, dx=1)
    idx = max(i for i, (s, _) in enumerate(SHOTS) if t >= s)
    if idx in TRANS:
        t0, t1, kind, opt = TRANS[idx]
        if t < t1:
            e = prog(t, t0, t1 - t0)
            a, b = SHOTS[idx - 1][1](t), SHOTS[idx][1](t)
            if kind == 'whip': return T.whip(a, b, io(e), **opt)
            if kind == 'iris':
                cx, cy = iris_centre(opt); return T.iris(a, b, e, cx, cy)
            if kind == 'push':
                out = T.push(a, b, e, dx=-1).convert('RGBA'); PP.draw(out, t, None); return out.convert('RGB')
            if kind == 'lens':
                out = T.cut(a, b, e, at=0.5).convert('RGBA'); PL.draw(out, t, None); return out.convert('RGB')
    return SHOTS[idx][1](t)


# ------------------------------------------------------------------ captions
FONT_PATH = os.environ.get('PIXEL_FONT', '/usr/share/fonts/opentype/inter/Inter-Black.otf')

def font(size):
    if os.path.isfile(FONT_PATH):
        return ImageFont.truetype(FONT_PATH, size)
    try:
        return ImageFont.truetype('DejaVuSans-Bold.ttf', size)
    except OSError:
        return ImageFont.load_default(size=size)

FONT = font(104)
EMPH = {'con', 'revs', 'broken', 'compressor', 'load', 'idle', 'stalling', 'automatically', 'jump', 'normal'}

def make_chunks():
    sents, cur = [], []
    for i, w in enumerate(WORDS):
        cur.append(i)
        if w['w'][-1] in '.,?!':
            sents.append(cur); cur = []
    if cur: sents.append(cur)
    chunks = []
    for s in sents:
        k = math.ceil(len(s) / 3)
        base, extra = divmod(len(s), k)
        j = 0
        for c in range(k):
            n = base + (1 if c < extra else 0)
            chunks.append(s[j:j + n]); j += n
    out = []
    for ci, c in enumerate(chunks):
        st = WORDS[c[0]]['s'] - 0.04
        nxt = WORDS[chunks[ci + 1][0]]['s'] - 0.04 if ci + 1 < len(chunks) else DUR + LEAD
        en = min(nxt, WORDS[c[-1]]['e'] + 0.45)
        out.append((st, en, c))
    return out
CHUNKS = make_chunks()

def clean(w):
    w = w.lower().strip('.,!')
    return w

@lru_cache(None)
def caption_img(ci, active):
    idxs = CHUNKS[ci][2]
    words = [clean(WORDS[i]['w']) for i in idxs]
    d0 = ImageDraw.Draw(Image.new('RGB', (1, 1)))
    space = d0.textlength(' ', font=FONT)
    widths = [d0.textlength(w, font=FONT) for w in words]
    tw = sum(widths) + space * (len(words) - 1)
    pad = 40
    img = Image.new('RGBA', (int(tw + 2 * pad), 190), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    x = pad
    for i, (w, wd) in enumerate(zip(words, widths)):
        on = idxs[i] == active
        col = (255, 217, 59) if on else (255, 255, 255)
        if on and w.strip("?'") in EMPH: col = (255, 90, 90)
        d.text((x + 6, 30 + 8), w, font=FONT, fill=NAVY, stroke_width=14, stroke_fill=NAVY)
        d.text((x, 30), w, font=FONT, fill=col, stroke_width=13, stroke_fill=(10, 10, 16))
        x += wd + space
    if img.width > 1000:
        k = 1000 / img.width
        img = img.resize((1000, int(img.height * k)), Image.LANCZOS)
    return img


TFONT = font(80)


def _text_img(txt, col, sz):
    f = font(sz); d0 = ImageDraw.Draw(Image.new('RGB', (1, 1)))
    w = int(d0.textlength(txt, font=f)) + 60
    img = Image.new('RGBA', (w, int(sz * 1.5)), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.text((30 + 6, 8 + 8), txt, font=f, fill=NAVY, stroke_width=14, stroke_fill=NAVY)
    d.text((30, 8), txt, font=f, fill=col, stroke_width=13, stroke_fill=(10, 10, 16))
    return img


@lru_cache(None)
def tag_img(): return _text_img('car stuff, explained', (255, 255, 255), 62)


@lru_cache(None)
def question_img(): return _text_img('AC REVS UP?', (255, 90, 90), 108)


def title(cv, t, dx=0):
    # series tag from frame 0; the mystery question slams in as the needle jumps
    if t < 2.5:
        k = 1 - ic(prog(t, 2.2, 0.25))
        if k > 0.02:
            img = tag_img(); img = img.resize((int(img.width * k), int(img.height * k)), Image.BILINEAR)
            cv.paste(img, (int(W / 2 - img.width / 2) + dx, int(300 - img.height / 2)), img)
    if 1.95 <= t < 2.5:
        k = fx.slam(t, 1.95, 0.14, 0.9) * (1 - ic(prog(t, 2.3, 0.2)))
        if k > 0.02:
            img = question_img()
            img = img.resize((int(img.width * k), int(img.height * k)), Image.BILINEAR).rotate(-4 + 2 * math.sin(t * 9), resample=Image.BICUBIC, expand=True)
            cv.paste(img, (int(W / 2 - img.width / 2) + dx, int(430 - img.height / 2)), img)


@lru_cache(None)
def end_img():
    lines = [('car stuff, explained', (255, 255, 255), 76, 0), ('follow for the next one', (255, 217, 59), 96, 88)]
    img = Image.new('RGBA', (1300, 240), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for txt, col, sz, y in lines:
        f = font(sz); w = d.textlength(txt, font=f)
        d.text((650 - w / 2 + 6, y + 8), txt, font=f, fill=NAVY, stroke_width=14, stroke_fill=NAVY)
        d.text((650 - w / 2, y), txt, font=f, fill=col, stroke_width=13, stroke_fill=(10, 10, 16))
    bb = img.getbbox(); img = img.crop((bb[0] - 10, 0, bb[2] + 10, 240))
    if img.width > 1000:
        img = img.resize((1000, int(240 * 1000 / img.width)), Image.LANCZOS)
    return img

END_T = max(15.6, WORDS[-1]['e'] + 0.1)

def captions(cv, t):
    if t >= END_T:
        img = end_img(); k = 0.72 + 0.28 * ob(prog(t, END_T, 0.16))
        k *= 1 + 0.03 * math.sin((t - END_T) * 6)
        img = img.resize((int(img.width * k), int(img.height * k)), Image.BILINEAR)
        cv.paste(img, (int(W / 2 - img.width / 2), int(1400 - img.height / 2)), img)
        return
    for ci, (st, en, idxs) in enumerate(CHUNKS):
        if st <= t < en:
            active = None
            for i in idxs:
                if WORDS[i]['s'] - 0.04 <= t: active = i
            img = caption_img(ci, active)
            k = 0.72 + 0.28 * ob(prog(t, st, 0.16))
            if active is not None and active != idxs[0]:  # beat pop on each new word
                k *= 1 + 0.07 * math.exp(-(t - WORDS[active]['s'] + 0.04) * 14)
            dy = 18 * (1 - ob(prog(t, st, 0.2)))
            if active is not None: dy -= 12 * math.exp(-(t - WORDS[active]['s'] + 0.04) * 16)
            if k != 1:
                img = img.resize((int(img.width * k), int(img.height * k)), Image.BILINEAR)
            cv.paste(img, (int(W / 2 - img.width / 2), int(1390 + dy - img.height / 2)), img)
            return

# ------------------------------------------------------------------ frame + audio
def progress(cv, t):
    p = clamp(t / DUR)
    d = ImageDraw.Draw(cv)
    x0, x1, y, h = 100, W - 100, 120, 4 * S
    d.rounded_rectangle((x0 - 7, y - 7, x1 + 7, y + h + 7), 22, fill=NAVY)
    d.rounded_rectangle((x0, y, x1, y + h), 16, fill=(236, 236, 242))
    xp = x0 + (x1 - x0) * p
    if xp > x0 + 32:
        d.rounded_rectangle((x0, y, xp, y + h), 16, fill=(255, 210, 63))
        d.rectangle((x0 + 16, y + 7, xp - 16, y + 13), fill=(255, 238, 160))
    for tc, _ in SCENES[1:]:
        xc = x0 + (x1 - x0) * tc / DUR; yc = y + h / 2
        on = t >= tc
        r = 12 * (1 + 0.6 * math.exp(-(t - tc) * 10) if on else 1)
        d.ellipse((xc - r - 6, yc - r - 6, xc + r + 6, yc + r + 6), fill=NAVY)
        d.ellipse((xc - r, yc - r, xc + r, yc + r), fill=(60, 200, 90) if on else (200, 204, 212))
    blit(cv, big('car', 'red', int(t * 12) % 2, s=3), xp, y + 8 - S * (int(t * 8) % 2))

CONFETTI = [(15.35, 300, 700, 50, 4, 1.0), (15.4, 800, 640, 44, 8, 0.9), (16.1, 560, 600, 40, 9, 1.1)]


def frame(n):
    t = n / FPS + LEAD
    cv = picture(t)
    for t0, x, y, k, seed, sp in CONFETTI:
        fx.confetti(cv, t, t0, x, y, n=k, seed=seed, spread=sp)
    GAR.vignette(cv)
    if t >= AUTH_END - LOOP:
        title(cv, t - DUR, dx=int(W * (1 - io(prog(t, AUTH_END - LOOP, LOOP)))))
    else:
        title(cv, t)
    captions(cv, t)
    progress(cv, n / FPS)
    return cv.tobytes()

SCENE_WHOOSH = [2.5, 4.6, 6.26, 7.96, 10.26, 12.4, 16.8]
CUES = [
    (0.0, 'whoosh', 0.7), (0.0, 'sparkle', 0.6), (0.57, 'click', 1.0), (0.6, 'pop', 0.7), (0.64, 'sparkle', 0.5),
    (1.05, 'thump', 0.4), (1.88, 'vroom', 0.9), (1.88, 'boom', 0.35), (1.9, 'pop', 0.6), (1.95, 'sparkle', 0.8),
    (2.62, 'pop', 0.7), (2.88, 'pop', 0.5), (3.0, 'pop', 0.5), (3.12, 'pop', 0.5),
    (3.81, 'stamp', 1.0), (3.83, 'thump', 0.6), (4.25, 'ding', 0.9), (4.28, 'sparkle', 0.7),
    (4.72, 'pop', 0.7), (4.9, 'pop', 0.8), (4.95, 'pop', 0.5), (4.97, 'sparkle', 0.5),
    (5.65, 'thump', 0.9), (5.66, 'boom', 0.3), (5.7, 'pop', 0.7),
    (6.4, 'pop', 0.7), (6.98, 'vroom', 0.45), (7.0, 'sparkle', 0.6), (7.42, 'pop', 0.8),
    (8.1, 'vroom', 0.35), (8.3, 'pop', 0.6), (8.72, 'poof', 0.5), (8.9, 'poof', 0.35), (9.0, 'pop', 0.8), (9.02, 'thump', 0.5),
    (9.4, 'click', 0.7), (9.4, 'ding', 0.9), (9.43, 'sparkle', 0.7),
    (10.49, 'pop', 0.6), (10.6, 'pop', 0.6), (10.71, 'pop', 0.6), (11.3, 'pop', 0.9), (11.32, 'sparkle', 0.9), (11.55, 'pop', 0.6),
    (11.65, 'ding', 0.45), (11.8, 'ding', 0.5), (11.95, 'ding', 0.6),
    (12.52, 'pop', 0.7), (13.48, 'pop', 0.4), (13.98, 'vroom', 0.9), (13.98, 'boom', 0.35), (14.0, 'sparkle', 0.8),
    (15.03, 'stamp', 1.0), (15.06, 'ding', 0.9), (15.08, 'sparkle', 0.8),
    (15.35, 'confetti', 1.0), (15.62, 'pop', 0.6), (15.8, 'pop', 0.7), (16.0, 'pop', 0.5), (16.1, 'confetti', 0.6),
] + [(t, 'whoosh', 0.6) for t in SCENE_WHOOSH]

def build_audio(vo_path, out_wav):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', vo_path, '-ar', str(sfx.SR), '-ac', '1', '-f', 'f32le', '-'],
                         capture_output=True, check=True).stdout
    vo = np.frombuffer(raw, np.float32).astype(np.float64)
    n = int(sfx.SR * DUR)
    mix = np.zeros(n); m = min(n, len(vo)); mix[:m] = vo[:m]
    fx = sfx.render([(c - LEAD, nm, v) for c, nm, v in CUES if c >= LEAD], DUR)
    fx *= 0.32 * np.max(np.abs(vo)) / max(1e-9, np.max(np.abs(fx)))
    mix += fx
    mix /= max(1.0, np.max(np.abs(mix)) / 0.97)
    pcm = (mix * 32767).astype('<i2')
    import wave
    with wave.open(out_wav, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sfx.SR); w.writeframes(pcm.tobytes())

if __name__ == '__main__':
    mode = sys.argv[1]
    if mode == 'still':
        for ts in sys.argv[3:]:
            t = float(ts); n = int(t * FPS)
            Image.frombytes('RGB', (W, H), frame(n)).save(f'{sys.argv[2]}/f_{ts}.png')
    elif mode == 'video':
        vo, out = sys.argv[2], sys.argv[3]
        t0, t1 = (float(sys.argv[4]), float(sys.argv[5])) if len(sys.argv) > 5 else (0.0, DUR)  # optional test range
        build_audio(vo, 'mix.wav')
        F0, N = int(t0 * FPS), int(t1 * FPS)
        ff = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS),
                               '-i', '-', '-ss', str(t0), '-t', str(t1 - t0), '-i', 'mix.wav', '-c:v', 'libx264', '-preset', 'medium', '-crf', '17', '-pix_fmt', 'yuv420p',
                               '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', '-shortest', out], stdin=subprocess.PIPE)
        with Pool(4) as pool:
            for i, b in enumerate(pool.imap(frame, range(F0, N), chunksize=6)):
                ff.stdin.write(b)
                if i % 300 == 0: print(f'{i}/{N}', flush=True)
        ff.stdin.close(); ff.wait()
        print('done', ff.returncode)
        raise SystemExit(ff.returncode)
