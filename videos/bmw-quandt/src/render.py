"""Renders 'BMW almost became part of Mercedes': the 1959 rescue story and Herbert Quandt. Generic cars only.

Word times come from the aligned voiceover (align.py). The video is 28 s to fit the spoken script.
Shots, each with its own presenter path and camera, joined by character-driven transitions:
  1 hook    0.00  he dives in between two cars facing off; VS badge; points at each car on 'almost' / 'Mercedes'
  2 paper   2.97  whip; a giant 1959 newspaper drops in; the crack splits it on 'serious', TROUBLE stamp
  3 street  6.60  push to a night street; the small car sputters, the silver car rolls in, he lands and stops it; TAKEOVER
  4 reveal 11.90  iris through the stamp; a suited silhouette steps into a sunburst; HERBERT QUANDT label
  5 certs  14.90  whip; share certificates rain onto the small car; the silver car backs off; STAYED
  6 doubt  19.70  whip down to a face close-up; question marks, shrug; pull back as both cars drive off
  7 teaser 23.10  whip; NEXT EPISODE label over a dust sheet; he lifts it on 'almost'; confetti, 'Follow'
"""
import json, math, os, sys, subprocess, wave
from functools import lru_cache
from multiprocessing import Pool
import numpy as np
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'shared'))
from backdrops.garage import Garage
from audio import sfx
from pixanim.motion import Track, prog, lerp, clamp, ob, oc, ic, io, springs, wob
from pixanim.camera import Camera
from pixanim.presenter import Presenter, Fn
from pixanim import fx, transitions as T, diagram as dg
from pixanim.fx import blit, popin, popout
from pixanim.car import car, wheel_deg, HEADLIGHT, EXHAUST
from pixanim.dash import _gauge_face
from pixanim.street import Street
from pixanim.props import sheet
from pixanim.grid import up

W, H, FPS, S = 1080, 1920, 60, 9
GROUND = 1180
RY = Street.ROAD_Y
DUR = 28.0
BG = (14, 15, 18)
NAVY = (26, 26, 46)
GLOW = (255, 210, 63)
RED, YEL, GRN, WHITE = (255, 90, 90), (255, 217, 59), (90, 220, 120), (255, 255, 255)
GAR = Garage(W, H, GROUND, S)
WORDS = json.load(open('words.json'))
END_T = 26.9               # speech ends here; the 'Follow' card takes over


@lru_cache(None)
def world(name):
    if name == 'street': return Street()
    if name == 'road_refl': return Garage(W, H, RY, S)
    raise KeyError(name)


def layer(): return Image.new('RGBA', (W, H), (0, 0, 0, 0))


def finish(img, fg, cam, t, rim=True):
    """Composite a foreground layer (rim-lit) over the world image, then frame it with the shot camera."""
    if rim: fg = GAR.rim(fg)
    img = img.copy(); img.alpha_composite(fg)
    return cam.apply(img.convert('RGB'), t, BG)


def draw_car(cv, col, x, s, y=GROUND, flip=False, dist=0.0, lights=False, brake=False, sx=1.0, sy=1.0):
    blit(cv, up(car(col, wheel_deg(dist, s), lights, brake), s), x, y, sx, sy, flip=flip)


def car_pt(x, y, s, flip, g):   # grid anchor on a car drawn centred at x with its wheels on y
    return (x + 45 * s - g[0] * s if flip else x - 45 * s + g[0] * s, y - 50 * s + g[1] * s)


def beam(cv, x, y, s, flip, a=46):
    hx, hy = car_pt(x, y, s, flip, HEADLIGHT); k = -1 if flip else 1
    ImageDraw.Draw(cv).polygon([(hx, hy - 10), (hx + k * 440, hy - 110), (hx + k * 440, hy + 150), (hx, hy + 14)], fill=(255, 248, 210, a))


def rpm_deg(t):   # needle angle on the corner gauge: 225 is zero, lower is more revs
    return springs(t, 225, [(0.42, 150, 14, 6), (1.97, 120, 16, 5), (5.37, 200, 12, 6), (9.42, 110, 16, 5), (10.6, 200, 14, 6),
                            (12.8, 140, 14, 6), (18.1, 120, 16, 5), (21.6, 95, 16, 5), (24.0, 225, 10, 5)])


# ================================================================== shot 1: hook, two cars face off
H_RED, H_SIL = 170, 930
P1 = Presenter([
    (-1.0, dict(path=Track([(-1.0, (200, 250)), (0.0, (260, 360)), (0.42, (540, GROUND), 'ic')]),
                size=8, legs='auto', arms='fly', expr='wow', ground=None, face=1)),
    (0.42, dict(ground=GROUND, squash=True, arms='hips', expr='grin', face=None, look_camera=True)),
    (0.88, dict(arms='point', point=(H_RED, 1000), look=(H_RED, 1000), look_camera=False, expr='smirk')),
    (1.97, dict(arms='point', point=(H_SIL, 980), look=(H_SIL, 980), expr='shock', squash=True)),
], words=WORDS, base_size=8)
CAM1 = Camera(W, H, [(-1.0, (420, 700, 1.6)), (0.0, (420, 700, 1.6)), (0.45, (540, 1000, 1.3), 'io'), (1.0, (540, 980, 1.05), 'io'),
                     (1.97, (620, 980, 1.12), 'io'), (2.97, (640, 980, 1.16))],
              kicks=[(0.42, 0.12, 540, 1100), (0.88, 0.08, H_RED, 1000), (1.97, 0.1, H_SIL, 980)], shakes=[(0.42, 0.3, 16)])


def shot_hook(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    fx.contact_shadow(fg, H_RED, GROUND, 460, s=S, alpha=130); fx.contact_shadow(fg, H_SIL, GROUND, 540, s=S, alpha=130)
    lit = 1.97 <= t < 2.1 or 2.2 <= t < 2.4
    if lit: beam(fg, H_SIL, GROUND, 6, True)
    sr, sv = wob(t, (0.42, 0.88), 0.05)
    draw_car(fg, 'red', H_RED, 5, sx=sr, sy=sv)
    draw_car(fg, 'silver', H_SIL, 6, flip=True, lights=lit, sx=wob(t, (1.97,), 0.05)[0], sy=wob(t, (1.97,), 0.05)[1])
    fx.ring(fg, t, 0.42, 540, GROUND - 200, (224, 48, 58), life=0.4)
    fx.burst(fg, t, 0.42, 540, GROUND - 220, (224, 48, 58), n=14, seed=70)
    fx.dust(fg, t, 0.42, 540, GROUND - 10, n=12, seed=43)
    kv = popin(t, 0.62) * (1 + 0.06 * math.sin(t * 9))
    if t >= 0.62:
        blit(fg, fx.big('badge', 'VS', '#ffd23f', '#d6303a', '#e8b923', s=9), 540, 560, kv, kv, 6 * math.sin(t * 4), anchor='center')
    fx.burst(fg, t, 0.62, 540, 560, seed=71)
    P1.draw(fg, t)
    fx.dust(fg, t, 1.97, H_SIL - 200, GROUND - 10, n=8, seed=46)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM1, t)


# ================================================================== shot 2: the 1959 newspaper
PAPER_X = 450
def paper_y(t): return lerp(-600, 800, ob(prog(t, 2.97, 0.45)))
MAST = (PAPER_X, 800 - 192 * 1.5)
P2 = Presenter([
    (2.9, dict(path=Track([(2.9, (1300, 420)), (3.35, (880, GROUND), 'oc')]), size=7, legs='auto', arms='fly', expr='grin', face=-1, ground=None)),
    (3.35, dict(ground=GROUND, squash=True, arms='point', point=MAST, look=MAST, expr='smile', face=None)),
    (5.37, dict(arms='shock', expr='shock', squash=True, point=None)),
    (6.1, dict(arms='talkB', expr='sad', look=None, look_camera=True)),
], words=WORDS, base_size=7)
CAM2 = Camera(W, H, [(2.97, (560, 880, 1.1)), (4.4, (520, 860, 1.18), 'io'), (5.37, (500, 820, 1.28), 'io'), (6.8, (500, 820, 1.34))],
              kicks=[(3.26, 0.08, *MAST), (3.42, 0.05, PAPER_X, 800), (5.37, 0.14, PAPER_X, 820), (5.82, 0.1, PAPER_X, 900)],
              shakes=[(5.37, 0.4, 18), (5.82, 0.25, 10)])


def shot_paper(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    fx.rays(fg, t, 3.26, *MAST, GLOW, life=0.9, r=520)
    jx, jy = wob(t, (3.42, 5.37), 0.06)
    blit(fg, paper_frame(t), PAPER_X, paper_y(t), 1.5 * jx, 1.5 * jy, -4 + 2 * math.sin(t * 2), anchor='center')
    fx.burst(fg, t, 3.26, *MAST, seed=75); fx.ring(fg, t, 3.28, *MAST, GLOW, life=0.35, r1=240)
    fx.dust(fg, t, 3.42, PAPER_X, 1180, n=10, seed=47)
    fx.burst(fg, t, 5.37, PAPER_X, 800, (224, 48, 58), n=14, seed=76)
    fx.stamp_at(fg, t, 5.82, 'TROUBLE', PAPER_X, 960, -12, 11)
    P2.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM2, t)


# ================================================================== shot 3: night street, the takeover
RED3, SIL3 = 300, 620
def sil3_x(t):
    x = lerp(1450, 860, oc(prog(t, 8.6, 1.2)))
    return lerp(x, SIL3, ic(prog(t, 10.0, 0.55)))
def scroll3(t): return 60 * (t - 6.6)
P3 = Presenter([
    (9.9, dict(path=Track([(9.9, (470, 260)), (10.3, (470, RY), 'ic')]), size=5, legs='auto', arms='fly', expr='wow', ground=None, face=1)),
    (10.3, dict(ground=RY, squash=True, arms='point', point=(SIL3, RY - 120), look=(SIL3, RY - 120), expr='smirk')),
    (10.75, dict(squash=True, expr='grin')),
    (11.3, dict(arms='hips', look=None, look_camera=True)),
], words=WORDS, base_size=5)
CAM3 = Camera(W, H, [(6.6, (540, 1000, 1.2)), (7.3, (380, 1060, 1.7), 'io'), (8.6, (560, 1060, 1.45), 'io'), (9.6, (680, 1060, 1.5), 'io'),
                     (10.3, (480, 1080, 1.75), 'io'), (11.9, (540, 1060, 1.85))],
              kicks=[(7.65, 0.06, RED3, RY - 200), (9.42, 0.06, 900, RY - 100), (10.3, 0.08, 470, RY - 200), (10.6, 0.06, SIL3, RY - 100),
                     (10.75, 0.12, SIL3, RY - 200)],
              shakes=[(10.6, 0.25, 10), (10.75, 0.3, 14)])
STAMP3 = (590, RY - 120)


def shot_street(t):
    img = world('street').frame(t, scroll3(t)).convert('RGBA')
    cars = layer()
    sx = sil3_x(t); sputter = 7.28 <= t < 8.3
    lights = t >= 8.6
    if lights: beam(cars, sx, RY, 4, True, a=40)
    fx.contact_shadow(cars, RED3, RY, 260, s=3, alpha=140); fx.contact_shadow(cars, sx, RY, 340, s=4, alpha=140)
    draw_car(cars, 'red', RED3 + (5 * math.sin(t * 70) if sputter else 0), 3, y=RY)
    draw_car(cars, 'silver', sx, 4, y=RY, flip=True, dist=1450 - sx, lights=lights, brake=10.55 <= t < 11.2)
    world('road_refl').reflect(img, cars, depth=160, strength=0.3)
    img.alpha_composite(cars)
    fg = layer()
    ex, ey = car_pt(RED3, RY, 3, False, EXHAUST)
    for k in range(4):
        fx.puff(fg, t, 7.3 + k * 0.25, ex - 10, ey, seed=90 + k, life=0.7, size=0.7, drift=(-140, -80), col=(90, 92, 100))
    if 7.65 <= t < 8.9:
        kw = popin(t, 7.65) * popout(t, 8.7)
        blit(fg, fx.big('glyph', '!', '#e0303a', s=12), RED3, RY - 260 + 8 * math.sin(t * 9), kw, kw, anchor='center')
    for k in range(3):
        fx.puff(fg, t, 10.55 + k * 0.08, SIL3 + 120 - k * 40, RY - 10, seed=95 + k, life=0.6, size=0.8, drift=(160, -60))
    fx.dust(fg, t, 10.3, 470, RY - 10, n=10, seed=48)
    P3.draw(fg, t)
    fx.stamp_at(fg, t, 10.75, 'TAKEOVER', *STAMP3, -8, 7)
    fx.burst(fg, t, 10.75, *STAMP3, (224, 48, 58), seed=74)
    return finish(img, fg, CAM3, t)


# ================================================================== shot 4: the man in the sunburst
SIL4 = 600
def sil4_x(t): return lerp(1250, SIL4, oc(prog(t, 12.0, 0.6)))
HEAD4 = (SIL4, GROUND - 560)
P4 = Presenter([
    (11.9, dict(path=Track([(11.9, (-200, 600)), (12.3, (230, GROUND), 'oc')]), size=7, legs='auto', arms='fly', expr='grin', ground=None, face=1)),
    (12.3, dict(ground=GROUND, squash=True, arms='point', point=HEAD4, look=HEAD4, expr='smile')),
    (12.8, dict(expr='wow', squash=True)),
    (13.75, dict(arms='cheer1', expr='grin', point=None, look=None, look_camera=True)),
], words=WORDS, base_size=7)
CAM4 = Camera(W, H, [(11.9, (560, 900, 1.4)), (12.6, (560, 920, 1.25), 'io'), (13.75, (540, 840, 1.15), 'io'), (14.9, (540, 840, 1.2))],
              kicks=[(12.8, 0.1, SIL4, 850), (13.75, 0.08, 540, 520)], shakes=[(12.6, 0.2, 8)])


def shot_reveal(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    if t >= 12.8:
        fx.rays(fg, t, 12.8, SIL4, GROUND - 360, GLOW, hold=True, r=640, n=12)
        fx.sparkles(fg, t * 1.4, SIL4, GROUND - 360, 520, 520, n=10, seed=52)
    fx.ring(fg, t, 12.82, SIL4, GROUND - 360, GLOW, life=0.4, r1=360)
    x = sil4_x(t)
    fx.contact_shadow(fg, x, GROUND, 260, s=S, alpha=140)
    bob = 6 * abs(math.sin(t * 12)) if t < 12.6 else 0
    blit(fg, suit_img(), x, GROUND - bob, 1.25, 1.25)
    fx.dust(fg, t, 12.6, SIL4, GROUND - 10, n=10, seed=49)
    dg.label(fg, t, 13.75, 'HERBERT QUANDT', HEAD4, (540, 470), '#ffd23f', '#1a1a2e', '#e8b923', s=7)
    fx.burst(fg, t, 13.75, 540, 470, seed=73)
    P4.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM4, t)


# ================================================================== shot 5: certificates pile up, STAYED
CAR5 = 400
_rng = np.random.default_rng(11)
CERTS = [(_rng.uniform(-210, 210), _rng.uniform(-170, 30), _rng.uniform(-25, 25), 15.0 + i * 0.1) for i in range(22)]
def sil5_x(t): return lerp(lerp(1500, 1080, oc(prog(t, 16.3, 0.5))), 1600, ic(prog(t, 17.33, 0.6)))
P5 = Presenter([
    (14.9, dict(path=Track([(14.9, (1300, 500)), (15.25, (860, GROUND), 'oc')]), size=7, legs='auto', arms='fly', expr='grin', ground=None, face=-1)),
    (15.25, dict(ground=GROUND, squash=True, arms='cheer', look=(CAR5, 900), face=None)),
    (17.33, dict(arms='thumb', expr='grin', look=None, look_camera=True, squash=True)),
    (18.1, dict(arms='cheer1', squash=True)),
], words=WORDS, base_size=7)
CAM5 = Camera(W, H, [(14.9, (540, 960, 1.05)), (16.6, (480, 1000, 1.16), 'io'), (17.33, (600, 980, 1.12), 'io'), (18.1, (440, 940, 1.24), 'io'),
                     (19.7, (460, 940, 1.28))],
              kicks=[(17.33, 0.08, 860, 800), (18.1, 0.14, CAR5, 900)], shakes=[(18.1, 0.25, 10)])


def shot_certs(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    fx.contact_shadow(fg, CAR5, GROUND, 520, s=S, alpha=130)
    draw_car(fg, 'red', CAR5, 6)
    bx = sil5_x(t)
    if bx < 1500: draw_car(fg, 'silver', bx, 6, flip=True, dist=1500 - bx, brake=t >= 17.33)
    for dx, dy, rot, t0 in CERTS:
        if t >= t0:
            p = oc(prog(t, t0, 0.3))
            blit(fg, cert_img(), CAR5 + dx, GROUND - 130 + dy - 1100 * (1 - p), 1.4, 1.4, rot + 220 * (1 - p), anchor='center')
    for i in range(0, 22, 4):
        fx.dust(fg, t, CERTS[i][3] + 0.3, CAR5 + CERTS[i][0], GROUND - 10, n=5, seed=60 + i, life=0.4)
    if t >= 18.1:
        kc = popin(t, 18.1)
        blit(fg, fx.big('check', s=12), CAR5, 600 + 8 * math.sin(t * 6), kc, kc, anchor='center')
        fx.gsparkles(fg, t, CAR5, 800, 520, 420, n=10, seed=37)
    fx.ring(fg, t, 18.1, CAR5, 600, (60, 200, 90), life=0.4, r1=300)
    fx.stamp_at(fg, t, 18.1, 'STAYED', CAR5, GROUND - 360, -8, 11, '#3cc85a')
    P5.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM5, t)


# ================================================================== shot 6: nobody agrees
QMARKS = [(370, 560, 19.79), (720, 520, 19.95), (540, 400, 20.1)]
def red6_x(t): return 150 - 1000 * ic(prog(t, 21.6, 1.1))
def sil6_x(t): return 930 + 1000 * ic(prog(t, 21.6, 1.1))
P6 = Presenter([
    (19.6, dict(path=Fn(lambda t: (540, GROUND)), size=9, ground=GROUND, legs='stand', arms='down', expr='think', look_camera=True)),
    (20.7, dict(arms='shrug', expr='smirk', squash=True)),
    (21.6, dict(look_camera=False, look=(540, 400))),
    (22.08, dict(squash=True, look=None, look_camera=True)),
], words=WORDS, base_size=9)
CAM6 = Camera(W, H, [(19.6, (540, 760, 1.9)), (20.7, (540, 800, 1.7), 'io'), (21.5, (540, 820, 1.62)), (22.4, (540, 980, 1.0), 'io'), (23.1, (540, 980, 0.96))],
              kicks=[(20.7, 0.08, 540, 760), (21.7, 0.06, 540, 900), (22.08, 0.06, 540, 900)])


def shot_doubt(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    rx, sx = red6_x(t), sil6_x(t)
    for x, col, s, fl, d in ((rx, 'red', 5, True, 150 - rx), (sx, 'silver', 6, False, sx - 930)):
        fx.contact_shadow(fg, x, GROUND, 90 * s, s=S, alpha=130)
        draw_car(fg, col, x, s, flip=fl, dist=d, lights=t >= 21.6)
        if t >= 21.6:
            ex, ey = car_pt(x, GROUND, s, fl, EXHAUST)
            fx.puff(fg, t, 21.6, ex, ey, seed=int(s * 7), life=0.6, size=0.8, drift=(160 if fl else -160, -60))
    for qx, qy, t0 in QMARKS:
        if t0 <= t < 21.6:
            kq = popin(t, t0, 0.25)
            blit(fg, fx.big('glyph', '?', '#e0303a', s=12), qx, qy + 12 * math.sin(t * 7 + t0 * 9), kq, kq, 10 * math.sin(t * 5 + t0), anchor='center')
        fx.poof(fg, t, 21.6, qx, qy, seed=int(t0 * 10), life=0.4, scale=0.4)
    for x, t0 in ((300, 21.7), (780, 22.08)):
        if t0 <= t < 23.1:
            kx = popin(t, t0)
            blit(fg, fx.big('xmark', s=10), x, 560, kx, kx, anchor='center')
        fx.ring(fg, t, t0, x, 560, (224, 48, 58), life=0.3, r1=150)
    P6.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM6, t)


# ================================================================== shot 7: next-episode teaser
SHEET_X = 660
SIGN_AT = (560, 520)
P7 = Presenter([
    (23.0, dict(path=Track([(23.0, (-200, 500)), (23.45, (250, GROUND), 'oc')]), size=8, legs='auto', arms='fly', expr='grin', face=1, ground=None)),
    (23.45, dict(ground=GROUND, squash=True, arms='point', point=(SHEET_X, GROUND - 200), look=(SHEET_X, GROUND - 200))),
    (25.84, dict(arms=('aim', 30), expr='wow', squash=True)),
    (26.9, dict(arms='thumb', point=None, look=None, look_camera=True, expr='grin', squash=True)),
], words=WORDS, base_size=8)
CAM7 = Camera(W, H, [(23.1, (560, 900, 1.2)), (24.5, (540, 920, 1.15), 'io'), (25.84, (600, 960, 1.28), 'io'), (26.9, (560, 920, 1.18), 'io'),
                     (DUR, (560, 920, 1.22))],
              kicks=[(23.5, 0.06, *SIGN_AT), (25.84, 0.12, SHEET_X, GROUND - 200), (26.9, 0.08, 250, 900)])


def shot_teaser(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    lift = oc(prog(t, 25.84, 0.35)) * 0.85
    fx.rays(fg, t, 23.4, SHEET_X, GROUND - 200, GLOW, hold=True, r=560)
    blit(fg, up(sheet(round(lift * 20) / 20), 8).transpose(Image.FLIP_LEFT_RIGHT), SHEET_X, GROUND)
    if lift > 0.3:
        fx.sparkles(fg, t * 1.6, SHEET_X - 170, GROUND - 60, 160, 100, n=8, seed=58)
    dg.label(fg, t, 23.4, 'NEXT EPISODE', (SHEET_X, GROUND - 330), SIGN_AT, '#ffd23f', '#1a1a2e', '#e8b923', s=8)
    fx.sparkles(fg, t, *SIGN_AT, 560, 140, n=6, seed=31)
    if t >= 25.84:
        kq = popin(t, 25.84, 0.25) * (1 + 0.1 * math.sin(t * 9))
        blit(fg, fx.big('glyph', '?', '#e0303a', s=16), SHEET_X + 40, GROUND - 330, kq, kq, 8 * math.sin(t * 6), anchor='center')
        fx.burst(fg, t, 25.84, SHEET_X + 40, GROUND - 330, seed=81)
    P7.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM7, t)


# ================================================================== shots + transitions
SHOTS = [(-1.0, shot_hook), (2.97, shot_paper), (6.6, shot_street), (11.9, shot_reveal), (14.9, shot_certs),
         (19.7, shot_doubt), (23.1, shot_teaser)]
TRANS = {1: (2.97, 3.17, 'whip', dict(dx=-1)), 2: (6.6, 6.82, 'push', None), 3: (11.9, 12.12, 'iris', None),
         4: (14.9, 15.1, 'whip', dict(dx=1)), 5: (19.7, 19.9, 'whip', dict(dx=0, dy=1)), 6: (23.1, 23.3, 'whip', dict(dx=1))}


def picture(t):
    idx = max(i for i, (s, _) in enumerate(SHOTS) if t >= s)
    if idx in TRANS:
        t0, t1, kind, opt = TRANS[idx]
        if t < t1:
            e = prog(t, t0, t1 - t0)
            a, b = SHOTS[idx - 1][1](t), SHOTS[idx][1](t)
            if kind == 'whip': return T.whip(a, b, io(e), **opt)
            if kind == 'push': return T.push(a, b, io(e), dx=-1)
            if kind == 'iris': return T.iris(a, b, e, *CAM3.to_screen(11.9, *STAMP3))
    return SHOTS[idx][1](t)


# ------------------------------------------------------------------ props
@lru_cache(None)
def paper_img():
    img = Image.new('RGBA', (400, 500), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rectangle((0, 0, 399, 499), fill=(246, 244, 236, 255), outline=(40, 40, 52, 255), width=8)
    d.rectangle((24, 24, 376, 92), fill=(40, 40, 52, 255))                      # masthead
    f = font(54); d.text((200 - d.textlength('1959', font=f) / 2, 26), '1959', font=f, fill=YEL + (255,))
    for i, y in enumerate(range(130, 470, 36)):                                  # headline and body lines
        d.rectangle((30, y, 370 - 90 * (i % 3 == 2), y + 14), fill=(150, 150, 160, 255))
    return img


def paper_frame(t):
    img = paper_img().copy()
    k = prog(t, 5.37, 0.12)                                                       # crack opens on 'serious trouble'
    if k > 0:
        pts = [(200 + (14 if i % 2 else -14), 100 + i * 34) for i in range(11)]
        ImageDraw.Draw(img).line(pts[:max(2, int(len(pts) * k))], fill=(224, 48, 58, 255), width=9)
    return img


@lru_cache(None)
def suit_img():
    img = Image.new('RGBA', (220, 440), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    ink = (34, 36, 48, 255)
    d.ellipse((70, 0, 150, 84), fill=ink)                                         # head
    d.polygon([(30, 110), (190, 110), (206, 300), (14, 300)], fill=ink)          # shoulders and jacket
    d.polygon([(95, 112), (125, 112), (110, 200)], fill=(240, 240, 240, 255))    # shirt
    d.polygon([(104, 128), (116, 128), (121, 190), (110, 210), (99, 190)], fill=RED + (255,))  # tie
    d.rectangle((48, 290, 100, 440), fill=ink); d.rectangle((120, 290, 172, 440), fill=ink)     # legs
    return img


@lru_cache(None)
def cert_img():
    img = Image.new('RGBA', (150, 96), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rectangle((0, 0, 149, 95), fill=(250, 244, 222, 255), outline=(60, 150, 90, 255), width=6)
    d.rectangle((14, 14, 136, 22), fill=(60, 150, 90, 255))
    for y in range(36, 80, 10):
        d.rectangle((20, y, 130 - (y % 20) * 2, y + 3), fill=(150, 150, 160, 255))
    d.ellipse((108, 62, 134, 88), fill=(224, 190, 60, 255))                      # seal
    return img




@lru_cache(None)
def gauge_img():
    img = Image.new('RGBA', (240, 240), (0, 0, 0, 0))
    _gauge_face(ImageDraw.Draw(img), 120, 120, 110, red_from=6, label='RPM')
    return img


def gauge(t):
    img = gauge_img().copy(); d = ImageDraw.Draw(img)
    a = math.radians(rpm_deg(t))
    d.line((120, 120, 120 + 84 * math.cos(a), 120 - 84 * math.sin(a)), fill=RED + (255,), width=6)
    d.ellipse((111, 111, 129, 129), fill=(200, 204, 212, 255))
    return img



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
KEYCOL = {'almost': RED, 'trouble': YEL, 'herbert': YEL, 'quandt': YEL, 'stayed': GRN, 'nobody': RED, 'agrees': RED}


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
        nxt = WORDS[chunks[ci + 1][0]]['s'] - 0.04 if ci + 1 < len(chunks) else END_T
        out.append((st, min(nxt, WORDS[c[-1]]['e'] + 0.45), c))
    return out
CHUNKS = make_chunks()


def clean(w): return w.lower().strip('.,!')


@lru_cache(None)
def caption_img(ci):
    words = [WORDS[i]['w'] for i in CHUNKS[ci][2]]
    d0 = ImageDraw.Draw(Image.new('RGB', (1, 1)))
    space = d0.textlength(' ', font=FONT)
    widths = [d0.textlength(w, font=FONT) for w in words]
    tw = sum(widths) + space * (len(words) - 1)
    pad = 40
    img = Image.new('RGBA', (int(tw + 2 * pad), 190), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    x = pad
    for w, wd in zip(words, widths):
        col = KEYCOL.get(clean(w), WHITE)                       # one highlighted keyword per caption
        d.text((x + 6, 30 + 8), w, font=FONT, fill=NAVY, stroke_width=14, stroke_fill=NAVY)
        d.text((x, 30), w, font=FONT, fill=col, stroke_width=13, stroke_fill=(10, 10, 16))
        x += wd + space
    if img.width > 1000:
        k = 1000 / img.width
        img = img.resize((1000, int(img.height * k)), Image.LANCZOS)
    return img


def _text_img(txt, col, sz):
    f = font(sz); d0 = ImageDraw.Draw(Image.new('RGB', (1, 1)))
    w = int(d0.textlength(txt, font=f)) + 60
    img = Image.new('RGBA', (w, int(sz * 1.5)), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.text((30 + 6, 8 + 8), txt, font=f, fill=NAVY, stroke_width=14, stroke_fill=NAVY)
    d.text((30, 8), txt, font=f, fill=col, stroke_width=13, stroke_fill=(10, 10, 16))
    return img


@lru_cache(None)
def follow_img(): return _text_img('Follow', YEL, 120)


def captions(cv, t):
    if t >= END_T:
        img = follow_img(); k = 0.72 + 0.28 * ob(prog(t, END_T, 0.16))
        img = img.resize((int(img.width * k), int(img.height * k)), Image.BILINEAR)
        cv.paste(img, (int(W / 2 - img.width / 2), int(1390 - img.height / 2)), img)
        return
    for ci, (st, en, idxs) in enumerate(CHUNKS):
        if st <= t < en:
            img = caption_img(ci)
            k = 0.72 + 0.28 * ob(prog(t, st, 0.16))
            dy = 18 * (1 - ob(prog(t, st, 0.2)))
            if k != 1:
                img = img.resize((int(img.width * k), int(img.height * k)), Image.BILINEAR)
            cv.paste(img, (int(W / 2 - img.width / 2), int(1390 + dy - img.height / 2)), img)
            return


# ------------------------------------------------------------------ progress bar
SCENES = [(max(0.0, s), f) for s, f in SHOTS]   # progress-bar checkpoints at each shot start


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
    blit(cv, up(car('red', int(t * 300) % 360), 1), xp, y + 8 - S * (int(t * 8) % 2))


CONFETTI = [(26.9, 540, 700, 50, 3, 1.0)]


def frame(n):
    t = n / FPS
    cv = picture(t)
    for t0, x, y, k, seed, sp in CONFETTI:
        fx.confetti(cv, t, t0, x, y, n=k, seed=seed, spread=sp)
    GAR.vignette(cv)
    cv.paste(gauge(t), (60, 1640), gauge(t))
    captions(cv, t)
    progress(cv, t)
    return cv.tobytes()


# ------------------------------------------------------------------ audio
CUES = [
    (0.0, 'whoosh', 0.8), (0.42, 'thump', 0.9), (0.42, 'boom', 0.35), (0.45, 'pop', 0.6), (0.62, 'pop', 0.8), (0.64, 'sparkle', 0.5),
    (0.88, 'click', 0.5), (1.97, 'vroom', 0.5), (1.99, 'pop', 0.5),
    (3.1, 'slide_down', 0.6), (3.26, 'ding', 0.7), (3.42, 'thump', 0.6), (5.37, 'crash', 0.7), (5.4, 'boom', 0.35), (5.82, 'stamp', 1.0),
    (7.3, 'poof', 0.5), (7.65, 'buzzer', 0.35), (7.9, 'poof', 0.4), (8.6, 'vroom', 0.5), (9.42, 'vroom', 0.8),
    (10.3, 'thump', 0.7), (10.55, 'screech', 0.8), (10.75, 'stamp', 1.0), (10.77, 'thump', 0.5),
    (12.3, 'thump', 0.5), (12.6, 'thump', 0.6), (12.8, 'boom', 0.4), (12.82, 'sparkle', 0.8), (13.75, 'ding', 0.9), (13.78, 'pop', 0.7),
    (15.25, 'thump', 0.5), (16.3, 'vroom', 0.4), (17.33, 'coin', 0.8), (17.36, 'ding', 0.6),
    (18.1, 'stamp', 1.0), (18.12, 'cha_ching', 0.8), (18.15, 'sparkle', 0.8),
    (19.79, 'pop', 0.6), (19.95, 'pop', 0.6), (20.1, 'pop', 0.6), (20.7, 'click', 0.5),
    (21.6, 'poof', 0.5), (21.6, 'vroom', 0.9), (21.7, 'buzzer', 0.3), (22.08, 'buzzer', 0.3),
    (23.45, 'thump', 0.5), (23.5, 'pop', 0.7), (23.52, 'sparkle', 0.6), (25.84, 'creak', 0.6), (25.86, 'boom', 0.35), (25.9, 'sparkle', 0.8),
    (26.9, 'confetti', 1.0), (26.92, 'ding', 0.7),
] + [(15.0 + i * 0.1 + 0.28, 'pop', 0.35) for i in range(22)] + [(t, 'whoosh', 0.6) for t, _ in SHOTS[1:]]


def build_audio(vo_path, out_wav):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', vo_path, '-ar', str(sfx.SR), '-ac', '1', '-f', 'f32le', '-'],
                         capture_output=True, check=True).stdout
    vo = np.frombuffer(raw, np.float32).astype(np.float64)
    n = int(sfx.SR * DUR)
    mix = np.zeros(n); m = min(n, len(vo)); mix[:m] = vo[:m]
    fxa = sfx.render(CUES, DUR)
    fxa *= 0.32 * np.max(np.abs(vo)) / max(1e-9, np.max(np.abs(fxa)))
    mix += fxa
    mix /= max(1.0, np.max(np.abs(mix)) / 0.97)
    pcm = (mix * 32767).astype('<i2')
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
