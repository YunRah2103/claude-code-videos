"""Renders 'The rise and fall of Jaguar': from the car everyone wanted to the brand known for jokes.

Template: videos/bmw-quandt/src/render.py (itself built from videos/ac-idle). Word times come from the
aligned voiceover (align.py -> words.json). Speech runs 0-23 s; the video is 24.5 s with the 'Follow' card.
Real photos are Wikimedia Commons (see photos/CREDITS.md); pixel cars stay generic.
Shots, each with its own presenter path and camera, joined by character-driven transitions:
  1 hook    0.00  a red sports car screeches into the garage; LOVED badge; hearts on 'wanted'; XK120 photo
  2 dream   2.90  whip; a blue sports car rolls in; dream bubble with a real E-Type photo on 'dreamed'
  3 crash   5.70  push; NATIONALISED sign drops onto the car; sparks, shake; quality gauge falls into the red
  4 ford    9.40  whip; 1989 badge, XJ6 photo; cost-cut arrows slam down on 'cheaper'; car swells on 'bigger'
  5 xtype  13.80  push; X-Type photos; the silver saloon wobbles on a shared platform into a DEAD END
  6 jokes  18.50  whip down; face close-up, LOL / HA HA / LMAO bubbles, speed lines fizzle out on 'speed'
  7 teaser 21.75  whip; NEXT EPISODE label over a dust sheet; he lifts it on 'next'; confetti, 'Follow'
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
from pixanim.car import car, wheel_deg, EXHAUST
from pixanim.dash import _gauge_face
from pixanim.props import sheet
from pixanim.grid import up

W, H, FPS, S = 1080, 1920, 60, 9
GROUND = 1180
DUR = 24.5
BG = (14, 15, 18)
NAVY = (26, 26, 46)
GLOW = (255, 210, 63)
RED, YEL, GRN, WHITE = (255, 90, 90), (255, 217, 59), (90, 220, 120), (255, 255, 255)
HERE = os.path.dirname(os.path.abspath(__file__))
GAR = Garage(W, H, GROUND, S)
WORDS = json.load(open(os.path.join(HERE, 'words.json')))
END_T = 23.0               # speech ends here; the 'Follow' card takes over


def layer(): return Image.new('RGBA', (W, H), (0, 0, 0, 0))


def finish(img, fg, cam, t, rim=True):
    """Composite a foreground layer (rim-lit) over the world image, then frame it with the shot camera."""
    if rim: fg = GAR.rim(fg)
    img = img.copy(); img.alpha_composite(fg)
    return cam.apply(img.convert('RGB'), t, BG)


def draw_car(cv, col, x, s, y=GROUND, flip=False, dist=0.0, lights=False, brake=False, sx=1.0, sy=1.0, rot=0.0):
    blit(cv, up(car(col, wheel_deg(dist, s), lights, brake), s), x, y, sx, sy, rot, flip=flip)


def car_pt(x, y, s, flip, g):   # grid anchor on a car drawn centred at x with its wheels on y
    return (x + 45 * s - g[0] * s if flip else x - 45 * s + g[0] * s, y - 50 * s + g[1] * s)


def rpm_deg(t):   # needle angle on the corner gauge: 225 is zero, lower is more revs
    return springs(t, 225, [(0.0, 60, 18, 5), (0.6, 150, 12, 6), (1.62, 110, 16, 5), (3.12, 120, 14, 6), (6.32, 200, 12, 6),
                            (8.21, 220, 10, 5), (10.24, 140, 14, 6), (12.81, 100, 16, 5), (16.54, 215, 12, 6), (20.81, 225, 10, 5),
                            (22.38, 90, 16, 5), (23.6, 160, 10, 5)])


@lru_cache(None)
def asset(name): return Image.open(os.path.join(HERE, 'assets', name + '.png')).convert('RGBA')


@lru_cache(None)
def scaled(name, k):
    a = asset(name); return a.resize((int(a.width * k), int(a.height * k)), Image.NEAREST)


# ------------------------------------------------------------------ real photos (see photos/CREDITS.md)
PHOTO_DIR = os.path.join(HERE, 'photos')


@lru_cache(None)
def _src(name): return Image.open(os.path.join(PHOTO_DIR, name + '.jpg')).convert('RGB')


@lru_cache(None)
def _frame(w, h, label):
    img = Image.new('RGBA', (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, w - 1, h - 1), 12, fill=(248, 246, 238, 255), outline=NAVY + (255,), width=6)
    if label:
        f = font(34)
        while d.textlength(label, font=f) > w - 30 and f.size > 18: f = font(f.size - 2)
        tw = d.textlength(label, font=f)
        d.text((w / 2 - tw / 2, h - 54), label, font=f, fill=NAVY + (255,))
    return img


@lru_cache(None)
def _shadow(w, h):
    sh = Image.new('RGBA', (w, h), (0, 0, 0, 255))
    sh.putalpha(_frame(w, h, '').getchannel('A').point(lambda a: a * 120 // 255))
    return sh


def _cover(name, iw, ih, focus=(0.5, 0.5), zoom=0.0, k=0.0):
    src = _src(name); sw, sh = src.size
    sc = max(iw / sw, ih / sh) * (1 + zoom + 0.12 * k)
    cw, ch = iw / sc, ih / sc
    cx = min(max(focus[0] * sw, cw / 2), sw - cw / 2); cy = min(max(focus[1] * sh, ch / 2), sh - ch / 2)
    return src.crop((int(cx - cw / 2), int(cy - ch / 2), int(cx + cw / 2), int(cy + ch / 2))).resize((iw, ih), Image.BILINEAR)


def photo_card(name, w, h, label='', k=0.0, focus=(0.5, 0.5), zoom=0.0):
    """Real photo in a framed card: cover-cropped around `focus`, slow push-in as k goes 0 -> 1."""
    b = 16; iw, ih = w - 2 * b, h - b - 64
    img = _frame(w, h, label).copy(); img.paste(_cover(name, iw, ih, focus, zoom, k), (b, b))
    return img


def photo(fg, t, t0, t1, name, x, y, w, h, rot=0.0, label='', focus=(0.5, 0.5), zoom=0.0):
    """Pop a real photo card in at t0, sway and push in slowly, pop it out at t1."""
    if not (t0 <= t < t1 + 0.25): return
    k = popin(t, t0, 0.3) * popout(t, t1, 0.2)
    if k <= 0.01: return
    r = rot + 2.5 * math.sin(t * 2.2 + x)
    blit(fg, _shadow(w, h), x + 14, y + 18, k, k, r, anchor='center')
    blit(fg, photo_card(name, w, h, label, clamp((t - t0) / 3), focus, zoom), x, y, k, k, r, anchor='center')
    fx.burst(fg, t, t0, x, y, GLOW, n=8, r0=90, r1=260, seed=int(x) % 90)


def hearts(fg, t, t0, x, y, n=7, seed=5, life=1.3):
    """Pixel hearts that pop out of a point and float up, fading as they rise."""
    if not (t0 <= t < t0 + life): return
    r = np.random.default_rng(seed); p = (t - t0) / life
    for i in range(n):
        dx, sp, ph = r.uniform(-260, 260), r.uniform(260, 520), r.uniform(0, 6)
        k = ob(clamp(p * 4)) * (1 - ic(clamp((p - 0.6) / 0.4)))
        blit(fg, fx.big('heart', s=8), x + dx * oc(clamp(p * 2)) + 18 * math.sin(t * 7 + ph), y - sp * p, k, k, anchor='center')


# ================================================================== shot 1: hook, the car everyone wanted
CAR1 = 380
def car1_x(t): return lerp(1700, CAR1, oc(prog(t, 0.0, 0.55)))
P1 = Presenter([
    (-1.0, dict(path=Track([(-1.0, (1300, 200)), (0.35, (1300, 260)), (0.8, (820, GROUND), 'ic')]), size=8, legs='auto', arms='fly',
                expr='wow', ground=None, face=-1)),
    (0.8, dict(ground=GROUND, squash=True, arms='shock', expr='wow', face=None, look=(CAR1, 1000))),
    (1.62, dict(arms='cheer1', expr='grin', look=None, look_camera=True, squash=True)),
    (2.02, dict(arms='point', point=(560, 560), look=(560, 560), expr='smile')),
], words=WORDS, base_size=8)
CAM1 = Camera(W, H, [(-1.0, (700, 1000, 1.5)), (0.0, (700, 1000, 1.5)), (0.55, (480, 1000, 1.25), 'io'), (1.6, (560, 960, 1.08), 'io'),
                     (2.02, (560, 900, 1.12), 'io'), (2.9, (560, 880, 1.16))],
              kicks=[(0.0, 0.1, 700, 1000), (0.55, 0.14, CAR1, 1000), (0.94, 0.08, 540, 420), (1.62, 0.12, 540, 760), (2.02, 0.08, 560, 560)],
              shakes=[(0.0, 0.55, 18), (0.55, 0.3, 14)])


def shot_hook(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    x = car1_x(t)
    if t < 0.55: fx.speed_lines(fg, 1 - prog(t, 0.0, 0.55), 3, col=(200, 204, 214))
    fx.contact_shadow(fg, x, GROUND, 600, s=S, alpha=140)
    sr, sv = wob(t, (0.55,), 0.07)
    draw_car(fg, 'red', x, 7, flip=True, dist=1700 - x, lights=True, brake=0.3 <= t < 1.0, sx=sr, sy=sv)
    for k in range(3):
        fx.puff(fg, t, 0.3 + k * 0.07, x + 230 - k * 40, GROUND - 10, seed=20 + k, life=0.7, size=1.0, drift=(260, -90))
    fx.dust(fg, t, 0.55, x, GROUND - 10, n=14, seed=43)
    fx.burst(fg, t, 0.55, x, GROUND - 200, GLOW, n=14, seed=70)
    # LOVED badge on 'everyone', hearts on 'wanted' (rays first so the badge stays on top)
    fx.rays(fg, t, 1.62, 540, 640, (255, 120, 150), life=0.9, r=560)
    if t >= 0.94:
        kv = popin(t, 0.94) * (1 + 0.06 * math.sin(t * 9)) * popout(t, 2.0)
        blit(fg, fx.big('badge', 'LOVED', '#7fe3a0', '#1a1a2e', '#3cc85a', s=12), 540, 640, kv, kv, 5 * math.sin(t * 4), anchor='center')
    fx.burst(fg, t, 0.94, 540, 640, (60, 200, 90), seed=71)
    hearts(fg, t, 1.62, 540, 900, n=9, seed=4)
    fx.ring(fg, t, 1.62, 540, 640, (255, 77, 109), life=0.4, r1=360)
    P1.draw(fg, t)
    GAR.reflect(img, fg)
    photo(fg, t, 2.02, 2.85, 'xk120_1951', 560, 560, 520, 400, -4, 'JAGUAR XK120, 1951', focus=(0.5, 0.6))
    return finish(img, fg, CAM1, t)


# ================================================================== shot 2: the dream car
RED2, BLU2 = 260, 760
def blu2_x(t): return lerp(1600, BLU2, oc(prog(t, 2.95, 0.6)))
DREAM = (600, 520)
P2 = Presenter([
    (2.9, dict(path=Track([(2.9, (-200, 500)), (3.3, (500, GROUND), 'oc')]), size=7, legs='auto', arms='fly', expr='grin', face=1, ground=None)),
    (3.3, dict(ground=GROUND, squash=True, arms='point', point=(BLU2, 1000), look=(BLU2, 1000), expr='wow', face=None)),
    (4.05, dict(arms='think', expr='happy', point=None, look=DREAM)),
    (4.83, dict(arms='cheer2', expr='grin', look=None, look_camera=True, squash=True)),
], words=WORDS, base_size=7)
CAM2 = Camera(W, H, [(2.9, (600, 980, 1.15)), (3.6, (640, 1000, 1.22), 'io'), (4.41, (560, 760, 1.12), 'io'), (5.7, (560, 760, 1.18))],
              kicks=[(3.12, 0.1, BLU2, 1000), (3.55, 0.06, BLU2, 1000), (4.41, 0.12, *DREAM), (4.83, 0.06, 500, 900)],
              shakes=[(3.55, 0.2, 8)])


@lru_cache(None)
def dream_img():
    """Thought bubble (episode asset) holding a real E-Type photo."""
    b = scaled('bubble_dream', 1.8)
    img = b.copy()
    ph = _cover('etype_1964', 430, 226, focus=(0.5, 0.5))
    m = Image.new('L', ph.size, 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, ph.width - 1, ph.height - 1), 20, fill=255)
    img.paste(ph, (int(b.width / 2 - ph.width / 2), 36), m)
    return img


def shot_dream(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    bx = blu2_x(t)
    for x, s in ((RED2, 5), (bx, 6)):
        fx.contact_shadow(fg, x, GROUND, 90 * s, s=S, alpha=130)
    draw_car(fg, 'red', RED2, 5)
    sr, sv = wob(t, (3.55,), 0.06)
    draw_car(fg, 'blue', bx, 6, flip=True, dist=1600 - bx, lights=t < 3.6, brake=3.3 <= t < 3.8, sx=sr, sy=sv)
    fx.dust(fg, t, 3.55, BLU2, GROUND - 10, n=10, seed=44)
    fx.glint(fg, t, 3.62, BLU2 + 150, GROUND - 250, r=120)
    fx.sparkles(fg, t, BLU2, GROUND - 240, 520, 240, n=6, seed=33)
    # small thought dots rising to the dream bubble, then the bubble with the real car inside
    for i, t0 in enumerate((4.05, 4.15, 4.25)):
        if t >= t0:
            kd = popin(t, t0, 0.2)
            blit(fg, fx.big('star', '#ffffff', s=6 + 2 * i), 470 + 40 * i, 900 - 90 * i, kd, kd, anchor='center')
    fx.rays(fg, t, 4.41, *DREAM, GLOW, life=1.0, r=600)
    if t >= 4.41:
        kb = popin(t, 4.41, 0.35)
        blit(fg, dream_img(), DREAM[0], DREAM[1] + 14 * math.sin(t * 3), kb, kb, 3 * math.sin(t * 2), anchor='center')
        fx.sparkles(fg, t * 1.3, *DREAM, 600, 420, n=12, seed=52)
    fx.ring(fg, t, 4.43, *DREAM, GLOW, life=0.4, r1=380)
    hearts(fg, t, 4.83, 500, 820, n=6, seed=9, life=1.0)
    P2.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM2, t)


# ================================================================== shot 3: the sign drops, quality falls apart
CAR3 = 470
ROOF3 = GROUND - 50 * 7 + 16 * 7
def sign_y(t): return lerp(-300, ROOF3, ic(prog(t, 6.01, 0.31)))
GAUGE3 = (770, 540)
def q_deg(t):   # quality needle: high on the right, falls into the red on 'quality fell apart'
    v = springs(t, -20, [(7.74, 150, 10, 4), (8.21, 205, 18, 3), (8.49, 215, 14, 5)])
    return v + (6 * math.sin(t * 47) if t >= 8.21 else 0)
P3 = Presenter([
    (5.65, dict(path=Track([(5.65, (1300, 500)), (6.0, (830, GROUND), 'oc')]), size=7, legs='auto', arms='fly', expr='smile', face=-1, ground=None)),
    (6.0, dict(ground=GROUND, squash=True, arms='present', look=(CAR3, 900), expr='smile', face=None)),
    (6.32, dict(arms='shock', expr='shock', squash=True, look=(CAR3, 900))),
    (7.54, dict(arms='point', point=GAUGE3, look=GAUGE3, expr='think')),
    (8.21, dict(arms='shock', expr='shock', squash=True, point=None)),
    (8.9, dict(arms='down', expr='sad', look=None, look_camera=True)),
], words=WORDS, base_size=7)
CAM3 = Camera(W, H, [(5.7, (540, 980, 1.1)), (6.3, (500, 960, 1.18), 'io'), (7.6, (580, 820, 1.1), 'io'), (8.5, (560, 840, 1.18), 'io'),
                     (9.4, (560, 840, 1.2))],
              kicks=[(6.32, 0.16, CAR3, ROOF3), (6.66, 0.05, CAR3, ROOF3), (7.74, 0.06, *GAUGE3), (8.21, 0.1, 600, 760), (8.49, 0.08, CAR3, 1000)],
              shakes=[(6.32, 0.45, 22), (8.21, 0.4, 16), (8.49, 0.3, 12)])


@lru_cache(None)
def qgauge_img():
    img = Image.new('RGBA', (320, 320), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    _gauge_face(d, 160, 160, 140, label='QUALITY')
    d.arc((40, 40, 280, 280), 135, 192, fill=(224, 48, 58, 255), width=18)     # red zone at the low end
    d.arc((40, 40, 280, 280), -12, 45, fill=(60, 200, 90, 255), width=18)      # green zone at the high end
    return img


def qgauge(t):
    img = qgauge_img().copy(); d = ImageDraw.Draw(img)
    a = math.radians(q_deg(t))
    d.line((160, 160, 160 + 112 * math.cos(a), 160 - 112 * math.sin(a)), fill=RED + (255,), width=9)
    d.ellipse((146, 146, 174, 174), fill=(200, 204, 212, 255))
    return img


def shot_crash(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    fx.contact_shadow(fg, CAR3, GROUND, 620, s=S, alpha=140)
    sag = 0.07 * oc(prog(t, 8.21, 0.3))
    sr, sv = wob(t, (6.32, 8.21), 0.08)
    tilt = -3 * oc(prog(t, 8.21, 0.3)) + (1.5 * math.sin(t * 40) if 8.21 <= t < 8.8 else 0)
    draw_car(fg, 'blue', CAR3, 7, sx=sr, sy=sv - sag, rot=tilt)
    if t >= 6.01:
        land = t >= 6.32
        js, jv = wob(t, (6.32,), 0.1)
        blit(fg, scaled('sign_nationalised', 1.25), CAR3, sign_y(t) + (GROUND - ROOF3) * sag * 0.5, js, jv, -6 if land else 4, anchor='bottom')
    fx.burst(fg, t, 6.32, CAR3, ROOF3, (255, 170, 60), n=16, seed=72)           # sparks where the sign hits
    if 6.32 <= t < 7.2: fx.sparkles(fg, t * 2, CAR3, ROOF3 - 20, 520, 120, n=8, seed=34)
    fx.dust(fg, t, 6.32, CAR3, ROOF3, n=14, seed=45)
    for k in range(4):
        ex, ey = car_pt(CAR3, GROUND, 7, False, EXHAUST)
        fx.puff(fg, t, 8.21 + k * 0.12, ex - 10, ey, seed=90 + k, life=0.8, size=0.9, drift=(-160, -120), col=(90, 92, 100))
    fx.puff(fg, t, 8.3, CAR3 + 120, ROOF3 + 40, seed=99, life=0.9, size=1.2, drift=(40, -200), col=(80, 82, 90))
    # quality gauge pops in, needle crashes into the red
    if t >= 7.0:
        kg = popin(t, 7.0, 0.3)
        jx, jy = wob(t, (8.21,), 0.06)
        blit(fg, qgauge(t), GAUGE3[0], GAUGE3[1], kg * jx, kg * jy, anchor='center')
    fx.ring(fg, t, 8.21, *GAUGE3, (224, 48, 58), life=0.4, r1=300)
    fx.burst(fg, t, 8.21, *GAUGE3, (224, 48, 58), n=14, seed=76)
    if 8.49 <= t:
        kw = popin(t, 8.49)
        blit(fg, fx.big('glyph', '!', '#e0303a', s=14), CAR3 - 180, ROOF3 - 140 + 8 * math.sin(t * 9), kw, kw, anchor='center')
    fx.stamp_at(fg, t, 8.49, 'FAULTY', CAR3 + 40, GROUND - 230, -10, 11)
    P3.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM3, t)


# ================================================================== shot 4: Ford buys it, cheaper and bigger
CAR4 = 500
ARROWS = [(300, 12.06), (520, 12.14), (740, 12.22)]
def big4(t): return springs(t, 1.0, [(12.81, 1.32, 14, 5)])
P4 = Presenter([
    (9.35, dict(path=Track([(9.35, (-200, 400)), (9.75, (190, GROUND), 'oc')]), size=6, legs='auto', arms='fly', expr='grin', face=1, ground=None)),
    (9.75, dict(ground=GROUND, squash=True, arms='point', point=(560, 520), look=(560, 520), expr='smile')),
    (10.24, dict(arms='cheer1', expr='wow', squash=True, point=None)),
    (11.44, dict(arms='point', point=(CAR4, 980), look=(CAR4, 980), expr='smirk')),
    (12.81, dict(arms='shock', expr='shock', squash=True, point=None)),
], words=WORDS, base_size=6)
CAM4 = Camera(W, H, [(9.4, (560, 800, 1.2)), (10.24, (560, 720, 1.16), 'io'), (11.4, (540, 960, 1.05), 'io'), (12.06, (520, 900, 1.12), 'io'),
                     (12.81, (540, 920, 1.0), 'io'), (13.8, (540, 920, 0.98))],
              kicks=[(9.79, 0.08, 560, 520), (10.24, 0.16, 540, 380), (12.06, 0.1, 520, 700), (12.22, 0.08, 740, 700), (12.81, 0.14, CAR4, 1000)],
              shakes=[(10.24, 0.25, 10), (12.06, 0.3, 14), (12.81, 0.35, 16)])


def shot_ford(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    if t >= 11.3:
        kc = popin(t, 11.3, 0.3); b = big4(t)
        fx.contact_shadow(fg, CAR4, GROUND, int(620 * b), s=S, alpha=140)
        draw_car(fg, 'silver', CAR4, 7, sx=kc * b, sy=kc * b)
        fx.dust(fg, t, 11.3, CAR4, GROUND - 10, n=10, seed=50)
    fx.ring(fg, t, 12.81, CAR4, GROUND - 250, GLOW, life=0.45, r1=520)
    fx.burst(fg, t, 12.81, CAR4, GROUND - 250, GLOW, n=16, seed=79)
    # cost-cut arrows slam down onto the roof on 'cheaper'
    for i, (x, t0) in enumerate(ARROWS):
        if t >= t0:
            p = oc(prog(t, t0, 0.18))
            y = lerp(-200, 760 - 50 * big4(t) + 12 * math.sin(t * 8 + i), p)
            js, jv = wob(t, (t0 + 0.18,), 0.12)
            blit(fg, scaled('arrow_cost', 1.3), x, y, js, jv, anchor='center')
            fx.dust(fg, t, t0 + 0.18, x, 840, n=6, seed=61 + i, life=0.4)
    for i, t0 in enumerate((12.1, 12.25, 12.4)):                             # coins fly out of the car as costs get cut
        if t0 <= t < t0 + 0.9:
            p = (t - t0) / 0.9
            blit(fg, fx.big('badge', '$', '#ffd23f', '#1a1a2e', '#e8b923', s=9), CAR4 - 260 + 260 * i + 120 * p * (i - 1),
                 GROUND - 420 - 360 * p + 600 * p * p, 1, 1, 30 * p * (i - 1), anchor='center')
    if t >= 12.81:                                                             # price tag climbs as the car grows
        kp = popin(t, 12.81)
        blit(fg, fx.big('tag', '$$$', '#fff6e0', '#d6303a', s=10), CAR4 + 330, GROUND - 520 - 40 * oc(prog(t, 12.81, 0.6)), kp, kp,
             -8 + 4 * math.sin(t * 6), anchor='center')
    # 1989 badge in a sunburst while the XJ6 photo shows the Ford-era saloon
    if 10.1 <= t < 11.5:
        k9 = popin(t, 10.24) * popout(t, 11.3)
        fx.rays(fg, t, 10.24, 540, 380, GLOW, hold=True, r=600, n=12)
        blit(fg, fx.big('badge', '1989', '#ffd23f', '#1a1a2e', '#e8b923', s=16), 540, 380, k9, k9, 4 * math.sin(t * 5), anchor='center')
    fx.burst(fg, t, 10.24, 540, 380, seed=77)
    P4.draw(fg, t)
    GAR.reflect(img, fg)
    photo(fg, t, 9.79, 11.25, 'xj6_x300_1996', 600, 760, 560, 330, 4, 'JAGUAR XJ6, 1996 (FORD ERA)', focus=(0.5, 0.55))
    return finish(img, fg, CAM4, t)


# ================================================================== shot 5: the X-Type, no identity
SIGN5 = 210
def car5_x(t): return lerp(lerp(1500, 600, oc(prog(t, 13.8, 0.55))), 460, ic(prog(t, 16.29, 0.25)))
def wobble5(t): return 4 * math.sin(t * 9) * (1 if t < 16.54 else 0.2)
QM5 = [(300, 640, 16.83), (540, 560, 16.95), (780, 640, 17.07)]
P5 = Presenter([
    (13.75, dict(path=Track([(13.75, (1300, 400)), (14.15, (960, GROUND), 'oc')]), size=6, legs='auto', arms='fly', expr='smile', face=-1, ground=None)),
    (14.15, dict(ground=GROUND, squash=True, arms='point', point=(420, 600), look=(420, 600), expr='smirk', face=None)),
    (15.37, dict(arms='present', point=None, look=(600, 1120), expr='think')),
    (16.54, dict(arms='shock', expr='shock', squash=True, look=(SIGN5, 1000))),
    (17.38, dict(arms='shrug', expr='sad', look=None, look_camera=True, squash=True)),
], words=WORDS, base_size=6)
CAM5 = Camera(W, H, [(13.8, (540, 900, 1.12)), (14.6, (540, 820, 1.08), 'io'), (15.37, (600, 1040, 1.22), 'io'), (16.29, (440, 1000, 1.16), 'io'),
                     (17.38, (560, 860, 1.08), 'io'), (18.5, (560, 860, 1.12))],
              kicks=[(13.97, 0.08, 400, 600), (15.37, 0.1, 380, 1120), (16.54, 0.18, SIGN5, 1000), (17.38, 0.1, 540, 600)],
              shakes=[(16.54, 0.45, 22)])


def shot_xtype(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    x = car5_x(t)
    # dead-end sign on a post at the right edge of the set
    jx, jy = wob(t, (16.54,), 0.12)
    ImageDraw.Draw(fg).rectangle((SIGN5 - 9, GROUND - 330, SIGN5 + 9, GROUND), fill=(120, 124, 134, 255))
    blit(fg, scaled('sign_dead_end', 0.8), SIGN5, GROUND - 330, jx, jy, 8 * math.sin(t * 30) * math.exp(-max(0, t - 16.54) * 4) if t >= 16.54 else 0, anchor='center')
    fx.contact_shadow(fg, x, GROUND, 600, s=S, alpha=140)
    sr, sv = wob(t, (14.35, 16.54), 0.07)
    draw_car(fg, 'silver', x, 7, dist=x + 400, sx=sr, sy=sv, rot=wobble5(t), brake=t >= 16.54)
    # the shared platform: a plain chassis outline under the body
    if 15.37 <= t < 16.4:
        kp = popin(t, 15.37) * popout(t, 16.2)
        cy = GROUND - 30
        ImageDraw.Draw(fg).rectangle((x - 300 * kp, cy - 6, x + 300 * kp, cy + 6), outline=(255, 210, 63, 255), width=4)
        dg.label(fg, t, 15.37, 'SHARED PLATFORM', (x, cy), (x, cy + 190), '#ffd23f', '#1a1a2e', '#e8b923', s=6, t1=16.2)
    fx.burst(fg, t, 16.54, SIGN5 - 120, GROUND - 200, (255, 170, 60), n=16, seed=78)
    fx.dust(fg, t, 16.54, SIGN5 - 160, GROUND - 10, n=12, seed=51)
    if 16.54 <= t < 18.5:                                                     # dizzy stars over the stuck car
        for i in range(4):
            a = t * 5 + i * math.pi / 2
            blit(fg, fx.big('star', s=7), x + 150 * math.cos(a), GROUND - 520 + 30 * math.sin(a), 1, 1, anchor='center')
    for qx, qy, t0 in QM5:
        if t0 <= t < 18.2:
            kq = popin(t, t0, 0.25)
            blit(fg, fx.big('glyph', '?', '#e0303a', s=12), qx, qy + 12 * math.sin(t * 7 + t0 * 9), kq, kq, 10 * math.sin(t * 5 + t0), anchor='center')
    if t >= 17.38:
        kx = popin(t, 17.38)
        blit(fg, fx.big('xmark', s=12), 540, 440, kx, kx, anchor='center')
    fx.ring(fg, t, 17.38, 540, 440, (224, 48, 58), life=0.35, r1=220)
    P5.draw(fg, t)
    GAR.reflect(img, fg)
    photo(fg, t, 13.97, 15.3, 'xtype_x400_2006', 420, 600, 560, 320, -4, 'JAGUAR X-TYPE, 2006', focus=(0.5, 0.6))
    photo(fg, t, 15.37, 16.25, 'xtype_sw', 700, 560, 460, 290, 5, 'X-TYPE ESTATE', focus=(0.5, 0.6))
    return finish(img, fg, CAM5, t)


# ================================================================== shot 6: known for jokes
BUBBLES = [('bubble_lol', 280, 520, 19.34, -8), ('bubble_haha', 800, 460, 19.92, 6), ('bubble_lmao', 300, 330, 20.12, 5),
           ('bubble_lol', 820, 300, 20.3, -6), ('bubble_haha', 560, 220, 20.47, 3)]
P6 = Presenter([
    (18.45, dict(path=Fn(lambda t: (540, GROUND)), size=9, ground=GROUND, legs='stand', arms='down', expr='think', look_camera=True)),
    (19.34, dict(arms='shrug', expr='smirk', squash=True)),
    (20.81, dict(arms='hips', expr='sad', squash=True)),
], words=WORDS, base_size=9)
CAM6 = Camera(W, H, [(18.5, (540, 760, 1.9)), (19.3, (540, 740, 1.6), 'io'), (20.5, (540, 640, 1.2), 'io'), (21.75, (540, 700, 1.05), 'io')],
              kicks=[(18.89, 0.06, 540, 760), (19.34, 0.08, 280, 520), (19.92, 0.12, 800, 460), (20.81, 0.1, 540, 900)])


def shot_jokes(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    if 20.4 <= t < 21.2:                                                       # speed lines fizzle out on 'speed'
        fx.speed_lines(fg, 1 - prog(t, 20.81, 0.4), 7, col=(200, 204, 214))
    fx.poof(fg, t, 20.81, 540, 1000, seed=17, life=0.6, scale=1.2)
    for name, x, y, t0, rot in BUBBLES:
        if t >= t0:
            kb = popin(t, t0, 0.25)
            blit(fg, asset(name), x, y + 10 * math.sin(t * 6 + t0 * 3), kb, kb, rot + 4 * math.sin(t * 8 + t0), anchor='center')
            fx.burst(fg, t, t0, x, y, (255, 255, 255), n=8, r0=60, r1=180, seed=int(t0 * 10))
    if t >= 20.81:
        kx = popin(t, 20.81)
        blit(fg, fx.big('xmark', s=12), 540, 1500 - 600, kx, kx, anchor='center')
    fx.ring(fg, t, 20.81, 540, 900, (224, 48, 58), life=0.35, r1=260)
    P6.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM6, t)


# ================================================================== shot 7: next-episode teaser
SHEET_X = 660
SIGN_AT = (560, 520)
P7 = Presenter([
    (21.7, dict(path=Track([(21.7, (-200, 500)), (22.1, (250, GROUND), 'oc')]), size=8, legs='auto', arms='fly', expr='grin', face=1, ground=None)),
    (22.1, dict(ground=GROUND, squash=True, arms='point', point=(SHEET_X, GROUND - 200), look=(SHEET_X, GROUND - 200))),
    (22.38, dict(arms=('aim', 30), expr='wow', squash=True)),
    (23.0, dict(arms='thumb', point=None, look=None, look_camera=True, expr='grin', squash=True)),
], words=WORDS, base_size=8)
CAM7 = Camera(W, H, [(21.75, (560, 900, 1.2)), (22.38, (600, 960, 1.28), 'io'), (23.0, (560, 920, 1.18), 'io'), (DUR, (560, 920, 1.24))],
              kicks=[(21.95, 0.06, *SIGN_AT), (22.38, 0.12, SHEET_X, GROUND - 200), (23.0, 0.08, 250, 900)])


def shot_teaser(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    lift = oc(prog(t, 22.38, 0.35)) * 0.85
    fx.rays(fg, t, 21.9, SHEET_X, GROUND - 200, GLOW, hold=True, r=560)
    blit(fg, up(sheet(round(lift * 20) / 20), 8).transpose(Image.FLIP_LEFT_RIGHT), SHEET_X, GROUND)
    if lift > 0.3:
        fx.sparkles(fg, t * 1.6, SHEET_X - 170, GROUND - 60, 160, 100, n=8, seed=58)
    dg.label(fg, t, 21.9, 'NEXT EPISODE', (SHEET_X, GROUND - 330), SIGN_AT, '#ffd23f', '#1a1a2e', '#e8b923', s=8)
    fx.sparkles(fg, t, *SIGN_AT, 560, 140, n=6, seed=31)
    if t >= 22.38:
        kq = popin(t, 22.38, 0.25) * (1 + 0.1 * math.sin(t * 9))
        blit(fg, fx.big('glyph', '?', '#e0303a', s=16), SHEET_X + 40, GROUND - 330, kq, kq, 8 * math.sin(t * 6), anchor='center')
        fx.burst(fg, t, 22.38, SHEET_X + 40, GROUND - 330, seed=81)
    P7.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM7, t)


# ================================================================== shots + transitions
SHOTS = [(-1.0, shot_hook), (2.9, shot_dream), (5.7, shot_crash), (9.4, shot_ford), (13.8, shot_xtype),
         (18.5, shot_jokes), (21.75, shot_teaser)]
TRANS = {1: (2.9, 3.1, 'whip', dict(dx=-1)), 2: (5.7, 5.92, 'push', None), 3: (9.4, 9.6, 'whip', dict(dx=1)),
         4: (13.8, 14.02, 'push', None), 5: (18.5, 18.7, 'whip', dict(dx=0, dy=1)), 6: (21.75, 21.95, 'whip', dict(dx=1))}


def picture(t):
    idx = max(i for i, (s, _) in enumerate(SHOTS) if t >= s)
    if idx in TRANS:
        t0, t1, kind, opt = TRANS[idx]
        if t < t1:
            e = prog(t, t0, t1 - t0)
            a, b = SHOTS[idx - 1][1](t), SHOTS[idx][1](t)
            if kind == 'whip': return T.whip(a, b, io(e), **opt)
            if kind == 'push': return T.push(a, b, io(e), dx=-1)
    return SHOTS[idx][1](t)


# ------------------------------------------------------------------ corner gauge
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
KEYCOL = {'wanted': GRN, 'e-type': YEL, 'dreamed': YEL, 'leyland': RED, 'quality': RED, 'fell': RED, 'apart': RED, '1989': YEL,
          'cheaper': YEL, 'bigger': YEL, 'x-type': RED, 'mondeo': YEL, 'never': RED, 'identity': RED, 'jokes': RED, 'speed': YEL,
          'follow': YEL, 'next': YEL}


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
        col = KEYCOL.get(clean(w), WHITE)                       # highlighted keywords per caption
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
def follow_img(): return _text_img('Follow for the next one', YEL, 92)


@lru_cache(None)
def credit_img():
    f = font(24); txt = 'Photos: Wikimedia Commons (CC BY-SA / public domain)'
    d0 = ImageDraw.Draw(Image.new('RGB', (1, 1)))
    img = Image.new('RGBA', (int(d0.textlength(txt, font=f)) + 20, 40), (0, 0, 0, 0))
    ImageDraw.Draw(img).text((10, 6), txt, font=f, fill=(190, 194, 204, 220))
    return img


def captions(cv, t):
    if t >= END_T:
        img = follow_img(); k = 0.72 + 0.28 * ob(prog(t, END_T, 0.16)) + 0.03 * math.sin(t * 8)
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


CONFETTI = [(23.0, 540, 700, 50, 3, 1.0), (23.1, 300, 640, 36, 5, 0.9)]


def frame(n):
    t = n / FPS
    cv = picture(t)
    if t < 0.12:                                                              # white flash on frame 0 for the hook
        cv = Image.blend(cv, Image.new('RGB', (W, H), (255, 255, 255)), 0.7 * (1 - t / 0.12))
    for t0, x, y, k, seed, sp in CONFETTI:
        fx.confetti(cv, t, t0, x, y, n=k, seed=seed, spread=sp)
    GAR.vignette(cv)
    cv.paste(gauge(t), (60, 1640), gauge(t))
    captions(cv, t)
    if t >= 21.75:
        c = credit_img(); cv.paste(c, (int(W / 2 - c.width / 2), 1868), c)
    progress(cv, t)
    return cv.tobytes()


# ------------------------------------------------------------------ audio
CUES = [
    (0.0, 'vroom', 1.0), (0.0, 'whoosh', 0.8), (0.3, 'screech', 0.9), (0.55, 'thump', 0.9), (0.55, 'boom', 0.35),
    (0.8, 'thump', 0.5), (0.94, 'pop', 0.8), (0.96, 'sparkle', 0.5), (1.62, 'ding', 0.7), (1.64, 'sparkle', 0.7),
    (2.02, 'pop', 0.7),
    (3.12, 'vroom', 0.6), (3.3, 'thump', 0.5), (3.55, 'screech', 0.5), (3.62, 'sparkle', 0.5),
    (4.05, 'pop', 0.4), (4.15, 'pop', 0.4), (4.25, 'pop', 0.4), (4.41, 'ding', 0.8), (4.43, 'sparkle', 0.8), (4.83, 'sparkle', 0.5),
    (6.01, 'fall', 0.8), (6.32, 'crash', 0.9), (6.32, 'boom', 0.5), (6.0, 'thump', 0.4), (7.0, 'pop', 0.7),
    (7.74, 'slide_down', 0.6), (8.21, 'crash', 0.6), (8.21, 'buzzer', 0.5), (8.3, 'poof', 0.5), (8.49, 'stamp', 1.0),
    (9.75, 'thump', 0.5), (9.79, 'pop', 0.7), (10.24, 'boom', 0.4), (10.26, 'ding', 0.8), (11.3, 'pop', 0.6),
    (12.24, 'thump', 0.6), (12.32, 'thump', 0.6), (12.4, 'thump', 0.6), (12.1, 'coin', 0.7), (12.25, 'coin', 0.7), (12.4, 'coin', 0.7),
    (12.81, 'boom', 0.45), (12.83, 'cha_ching', 0.8),
    (13.97, 'pop', 0.7), (14.15, 'thump', 0.5), (14.35, 'creak', 0.4), (15.37, 'pop', 0.7), (15.4, 'click', 0.5),
    (16.29, 'vroom', 0.6), (16.54, 'crash', 1.0), (16.54, 'boom', 0.45), (16.83, 'pop', 0.6), (16.95, 'pop', 0.6), (17.07, 'pop', 0.6),
    (17.38, 'buzzer', 0.5),
    (19.34, 'pop', 0.8), (19.92, 'pop', 0.8), (20.12, 'pop', 0.7), (20.3, 'pop', 0.7), (20.47, 'pop', 0.7), (20.81, 'poof', 0.6),
    (20.83, 'buzzer', 0.4),
    (22.1, 'thump', 0.5), (21.95, 'pop', 0.7), (21.97, 'sparkle', 0.6), (22.38, 'creak', 0.6), (22.4, 'boom', 0.35), (22.42, 'sparkle', 0.8),
    (23.0, 'confetti', 1.0), (23.02, 'ding', 0.7),
] + [(t, 'whoosh', 0.6) for t, _ in SHOTS[1:]]


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
        mix = os.path.splitext(out)[0] + '_mix.wav'
        build_audio(vo, mix)
        F0, N = int(t0 * FPS), int(t1 * FPS)
        # capped bitrate keeps the full 24.5 s export under 30 MB (8 Mbit/s video + 160 kbit/s audio ~ 25 MB)
        ff = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS),
                               '-i', '-', '-ss', str(t0), '-t', str(t1 - t0), '-i', mix, '-c:v', 'libx264', '-preset', 'medium', '-crf', '18',
                               '-maxrate', '8M', '-bufsize', '12M', '-pix_fmt', 'yuv420p',
                               '-c:a', 'aac', '-b:a', '160k', '-movflags', '+faststart', '-shortest', out], stdin=subprocess.PIPE)
        with Pool(4) as pool:
            for i, b in enumerate(pool.imap(frame, range(F0, N), chunksize=6)):
                ff.stdin.write(b)
                if i % 300 == 0: print(f'{i}/{N}', flush=True)
        ff.stdin.close(); ff.wait()
        print('done', ff.returncode)
        raise SystemExit(ff.returncode)
