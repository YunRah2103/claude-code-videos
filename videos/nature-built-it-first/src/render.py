"""Renders 'Nature built it first': the yellow boxfish and the 2005 Mercedes-Benz Bionic concept car.

Template: videos/ac-idle -> jaguar-rise-fall shot structure; shared/episode.py holds captions, progress bar, photo
cards, mixer and the NEXT EPISODE ending. Word times: align.py -> words.json. Speech runs 0-16.95 s; 'Follow' to 18.6 s.
Shots:
  1 hook    0.00  'Nature built it first' in yellow; a car pushes through air streamlines; ring on 'nothing else'
  2 sea     3.60  whip down; the garage floods blue, bubbles, waves; kick on 'sea'
  3 fish    5.55  a pixel boxfish swims across; YELLOW BOXFISH label; real photo; streamlines on 'shaped'
  4 morph   9.20  push; 2005 badge; the fish morphs into the Bionic car shape; label; real Bionic photo
  5 fish   14.15  whip; the fish in a hard hat, ENGINEER badge, he gives a thumbs up
  6 teaser 17.10  shared NEXT EPISODE ending
"""
import math, os, sys
from functools import lru_cache
import numpy as np
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared'))
import episode as kit
from episode import W, H, S, GROUND, GAR, GLOW, RED, YEL, layer, finish, draw_car, photo, title
from pixanim.motion import Track, prog, lerp, clamp, oc, ic, io, wob
from pixanim.camera import Camera
from pixanim.presenter import Presenter
from pixanim import fx, diagram as dg
from pixanim.fx import blit, popin, popout
from pixanim.grid import up, outline

WORDS = kit.load_words(HERE)
DUR, END_T = 18.6, 17.1
NAVY = (26, 26, 46)
SEA = (40, 120, 200)


# ------------------------------------------------------------------ episode sprites
@lru_cache(None)
def boxfish(fin=0, hat=False):
    """Yellow boxfish (46x32) facing right: boxy body, dark spots, fluttering fins, small tail."""
    img = Image.new('RGBA', (46, 32), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    body, shade, hi = (255, 210, 50), (226, 170, 30), (255, 238, 140)
    d.polygon([(0, 10 + fin), (7, 15), (0, 22 - fin)], fill=shade)                        # tail
    d.rounded_rectangle((6, 6, 40, 28), 7, fill=body)
    d.polygon([(34, 8), (44, 15), (44, 20), (34, 27)], fill=body)                        # snout
    d.line([(9, 8), (36, 8)], fill=hi); d.rectangle((8, 24, 38, 27), fill=shade)
    for x, y in ((12, 12), (18, 18), (24, 11), (28, 20), (14, 22), (31, 14)):
        d.rectangle((x, y, x + 1, y + 1), fill=(30, 32, 38))
    d.ellipse((34, 11, 39, 16), fill=(255, 255, 255)); d.rectangle((36, 12, 37, 14), fill=(20, 20, 26))
    d.point((43, 19), fill=(140, 60, 40))
    d.polygon([(22, 16), (28 - fin, 22), (20, 22)], fill=shade)                          # pectoral fin
    if hat:
        d.pieslice((18, 0, 36, 14), 180, 360, fill=(255, 138, 61)); d.rectangle((16, 6, 38, 8), fill=(255, 138, 61))
        d.rectangle((26, 1, 28, 7), fill=(255, 196, 120))
    return outline(img)


@lru_cache(None)
def bionic(spin=0):
    """Bionic-style concept car (92x38): tall, rounded box profile with a tapered tail, covered rear wheel."""
    img = Image.new('RGBA', (92, 38), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    body, shade, hi = (214, 220, 228), (168, 174, 186), (244, 248, 252)
    d.rounded_rectangle((8, 5, 86, 30), 10, fill=body)
    d.polygon([(10, 7), (1, 16), (2, 26), (12, 30)], fill=body)
    d.polygon([(30, 7), (38, 4), (62, 4), (74, 12), (30, 13)], fill=(70, 100, 140))      # glasshouse
    d.line([(36, 12), (42, 6)], fill=(170, 200, 230)); d.line([(56, 12), (60, 7)], fill=(170, 200, 230))
    d.line([(10, 8), (80, 8)], fill=hi); d.rectangle((6, 26, 86, 30), fill=shade)
    d.rectangle((82, 14, 87, 17), fill=(255, 246, 200)); d.rectangle((2, 16, 4, 19), fill=(200, 40, 40))
    for cx, cover in ((22, True), (70, False)):
        d.ellipse((cx - 8, 22, cx + 8, 38), fill=(22, 23, 28)); d.ellipse((cx - 4, 26, cx + 4, 34), fill=(190, 194, 204))
        a = math.radians(spin); d.line([(cx, 30), (cx + 4 * math.cos(a), 30 + 4 * math.sin(a))], fill=(110, 114, 124))
        if cover: d.rectangle((cx - 9, 22, cx + 9, 30), fill=body); d.line([(cx - 9, 30), (cx + 9, 30)], fill=shade)
    return outline(img)


@lru_cache(None)
def fish_outline():
    """Boxfish silhouette stretched to the Bionic's size, as a glowing yellow outline."""
    a = np.array(boxfish(0).resize((92 * 7, 34 * 7), Image.NEAREST))[..., 3] > 0
    e = a & ~(np.roll(a, 6, 0) & np.roll(a, -6, 0) & np.roll(a, 6, 1) & np.roll(a, -6, 1))
    out = np.zeros(a.shape + (4,), np.uint8); out[e] = (255, 217, 59, 230)
    return Image.fromarray(out, 'RGBA')


def streamlines(fg, t, t0, cx, cy, w, h, n=7, col=(220, 236, 255), bulge=1.0):
    """Air/water flow lines that bend smoothly around a shape centred at (cx, cy)."""
    if t < t0: return
    d = ImageDraw.Draw(fg); k = clamp((t - t0) / 0.4)
    for i in range(n):
        y = cy + (i - (n - 1) / 2) * (h / (n - 1))
        pts = []
        for j in range(40):
            x = cx - w / 2 + w * j / 39
            u = (x - cx) / (w * 0.3); off = bulge * (h * 0.35) * math.exp(-u * u) * (1 if y > cy else -1) * (1 - abs(y - cy) / h)
            pts.append((x, y + off))
        head = (t * 1.2 + i * 0.13) % 1.0
        seg = pts[int(head * 30):int(head * 30) + 10]
        if len(seg) > 1:
            d.line(pts[:int(40 * k)], fill=col + (70,), width=4)
            d.line(seg, fill=col + (230,), width=8)


@lru_cache(None)
def _ocean_base():
    """Static part of the reef (360x640 grid, 3 px): depth gradient, sand, rocks and corals."""
    img = Image.new('RGBA', (360, 640), (0, 0, 0, 255)); d = ImageDraw.Draw(img)
    for y in range(640):
        k = y / 640; d.line((0, y, 360, y), fill=(int(30 - 18 * k), int(110 - 60 * k), int(190 - 90 * k)))
    r = np.random.default_rng(8)
    d.polygon([(0, 560)] + [(x, 548 + 8 * math.sin(x / 23)) for x in range(0, 361, 12)] + [(360, 640), (0, 640)], fill=(196, 170, 120))
    for i in range(7):                                                            # rocks
        x, w = r.uniform(0, 360), r.uniform(26, 60)
        d.ellipse((x - w, 520 + r.uniform(0, 20), x + w, 590), fill=(70, 74, 92)); d.ellipse((x - w * 0.6, 526, x + w * 0.2, 548), fill=(96, 100, 120))
    for i, col in enumerate(((255, 110, 140), (255, 160, 70), (180, 120, 255), (255, 110, 140), (120, 220, 200))):   # corals
        x = 30 + i * 75 + r.uniform(-10, 10)
        for b in range(5):
            a = math.radians(-150 + b * 30); L = r.uniform(20, 38)
            d.line((x, 545, x + L * math.cos(a), 545 + L * math.sin(a)), fill=col, width=4)
            d.ellipse((x + L * math.cos(a) - 3, 545 + L * math.sin(a) - 3, x + L * math.cos(a) + 3, 545 + L * math.sin(a) + 3), fill=col)
    return img


def ocean(t):
    """Animated reef world (RGBA 1080x1920): light shafts, swaying kelp, a far fish school, bubbles."""
    img = _ocean_base().copy(); ov = Image.new('RGBA', img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    for i in range(5):                                                            # light shafts from the surface
        x = 40 + i * 80 + 20 * math.sin(t * 0.6 + i)
        d.polygon([(x, 0), (x + 24, 0), (x + 70, 560), (x + 10, 560)], fill=(200, 236, 255, 22 + 8 * int(math.sin(t * 1.3 + i) > 0)))
    img.alpha_composite(ov); d = ImageDraw.Draw(img)
    for i in range(9):                                                            # kelp
        x0 = 12 + i * 42; h = 160 + (i * 37) % 110
        pts = [(x0 + 10 * math.sin(t * 1.6 + i + j * 0.35) * j / 12, 560 - h * j / 12) for j in range(13)]
        d.line(pts, fill=(40, 140, 80), width=5); d.line(pts, fill=(80, 190, 110), width=2)
    for i in range(14):                                                           # a far school of fish drifting by
        fx_, fy = (i * 37 + t * 40) % 420 - 30, 150 + (i * 23) % 90 + 4 * math.sin(t * 3 + i)
        d.polygon([(fx_, fy), (fx_ + 7, fy - 3), (fx_ + 7, fy + 3)], fill=(150, 200, 230)); d.polygon([(fx_ + 7, fy), (fx_ + 10, fy - 2), (fx_ + 10, fy + 2)], fill=(120, 170, 210))
    for i in range(16):                                                           # bubbles
        bx = (i * 53) % 360 + 4 * math.sin(t * 2 + i); by = 640 - ((t * (30 + i * 3) + i * 97) % 640)
        d.ellipse((bx - 2, by - 2, bx + 2, by + 2), outline=(210, 240, 255))
    return up(img, 3)


def flood(t, k):
    """Garage world with the sea rising through it (k 0..1 = water level); above the waterline stays garage."""
    g = GAR.frame(t).convert('RGBA')
    if k <= 0: return g
    o = ocean(t); lvl = int(H - (H + 60) * k)
    m = Image.new('L', (W, H), 0); md = ImageDraw.Draw(m)
    pts = [(x, lvl + 18 * math.sin(x / 70 + t * 4)) for x in range(0, W + 30, 30)]
    md.polygon(pts + [(W, H), (0, H)], fill=255)
    g.paste(o, (0, 0), m)
    ImageDraw.Draw(g).line(pts, fill=(200, 236, 255), width=10)
    return g


def tunnel(t):
    """Wind-tunnel version of the garage: darker, with a turning fan on the left wall."""
    img = Image.blend(GAR.frame(t), Image.new('RGB', (W, H), (10, 14, 26)), 0.45).convert('RGBA')
    d = ImageDraw.Draw(img); cx, cy, R = 40, GROUND - 240, 230
    d.ellipse((cx - R - 14, cy - R - 14, cx + R + 14, cy + R + 14), fill=(60, 64, 78), outline=(26, 26, 46), width=10)
    d.ellipse((cx - R, cy - R, cx + R, cy + R), fill=(22, 24, 32))
    for b in range(5):
        a = t * 14 + b * 2 * math.pi / 5
        d.pieslice((cx - R + 10, cy - R + 10, cx + R - 10, cy + R - 10), math.degrees(a), math.degrees(a) + 34, fill=(150, 156, 170))
    d.ellipse((cx - 30, cy - 30, cx + 30, cy + 30), fill=(200, 206, 216), outline=(26, 26, 46), width=6)
    return img


def water(img, t, k):
    """Flood the garage frame: blue tint, waves at the top, rising bubbles. k 0..1 is the water level."""
    if k <= 0: return img
    lvl = int(H - (H + 120) * k)
    ov = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    pts = [(x, lvl + 18 * math.sin(x / 70 + t * 4)) for x in range(0, W + 30, 30)]
    d.polygon(pts + [(W, H), (0, H)], fill=SEA + (150,))
    d.line(pts, fill=(170, 220, 255, 220), width=10)
    r = np.random.default_rng(3)
    for i in range(26):
        bx = r.uniform(40, W - 40) + 20 * math.sin(t * 2 + i); by = H - ((t * r.uniform(150, 320) + r.uniform(0, H)) % H)
        if by > lvl + 20:
            rr = r.uniform(8, 22); d.ellipse((bx - rr, by - rr, bx + rr, by + rr), outline=(200, 236, 255, 200), width=4)
    img = img.copy(); img.alpha_composite(ov)
    return img


def hearts_fish(fg, t):
    """Little fish dart past him as the water arrives."""
    for i in range(6):
        u = (t - 4.72 - 0.08 * i) * 1.3
        if 0 < u < 1:
            y = 500 + 110 * i + 30 * math.sin(u * 9 + i)
            blit(fg, up(boxfish(int(t * 8) % 2 * 2), 3), lerp(-100, 1180, u) if i % 2 else lerp(1180, -100, u), y, 1, 1, flip=i % 2 == 0, anchor='center')


# ================================================================== shot 1: hook, cut through the air
CAR1 = 560
def car1_x(t): return lerp(-500, CAR1, oc(prog(t, 0.0, 0.8)))
P1 = Presenter([
    (-1.0, dict(path=Track([(-1.0, (1300, 300)), (0.5, (1300, 300)), (1.0, (900, GROUND), 'ic')]), size=6, legs='auto', arms='fly',
                expr='wow', ground=None, face=-1)),
    (1.0, dict(ground=GROUND, squash=True, arms='present', look=(CAR1, 1000), expr='smile', face=None)),
    (2.6, dict(arms='point', point=(CAR1 - 200, 900), look=(CAR1, 900), expr='think')),
], words=WORDS, base_size=6)
CAM1 = Camera(W, H, [(-1.0, (540, 1000, 1.4)), (0.0, (540, 1000, 1.4)), (0.8, (540, 940, 1.12), 'io'), (2.03, (520, 960, 1.22), 'io'),
                     (3.6, (520, 960, 1.26))],
              kicks=[(0.0, 0.1, 540, 1000), (0.8, 0.1, CAR1, 1000), (1.47, 0.1, CAR1, 950), (2.6, 0.12, CAR1, 950)], shakes=[(0.8, 0.2, 8)])


def shot_hook(t):
    img = tunnel(t); fg = layer()
    x = car1_x(t)
    if t < 0.8: fx.speed_lines(fg, 1 - prog(t, 0.0, 0.8), 3, col=(200, 204, 214))
    streamlines(fg, t, 0.3, CAR1, GROUND - 200, 1000, 420, n=5, col=(150, 170, 200), bulge=0.4)
    streamlines(fg, t, 1.47, CAR1, GROUND - 200, 1000, 520, n=9, bulge=1.0)
    fx.contact_shadow(fg, x, GROUND, 620, s=S, alpha=140)
    sr, sv = wob(t, (0.8,), 0.06)
    draw_car(fg, 'silver', x, 7, dist=x + 500, lights=True, sx=sr, sy=sv)
    if t >= 2.6:
        k = popin(t, 2.6, 0.3)
        blit(fg, fx.big('badge', 'LOW DRAG?', '#ffffff', '#1a1a2e', '#d6d9e2', s=10), 540, 640, k, k, -3 + 2 * math.sin(t * 3), anchor='center')
        fx.burst(fg, t, 2.6, 540, 640, GLOW, seed=70)
    P1.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM1, t)


def overlay(cv, t):
    title(cv, t, 0.05, 1.45, 'Nature built it first', YEL, 470, 104, -3)
    fx.ring(cv, t, 0.05, 540, 470, GLOW, life=0.35, r1=520)


# ================================================================== shot 2: they looked to the sea
P2 = Presenter([
    (3.55, dict(path=Track([(3.55, (540, -200)), (3.95, (540, GROUND), 'oc')]), size=8, legs='auto', arms='fly', expr='smile', face=1, ground=None)),
    (3.95, dict(ground=GROUND, squash=True, arms='pointup', expr='smile', look=(540, 500), face=None)),
    (4.72, dict(arms='cheer1', expr='wow', look=None, look_camera=True, squash=True)),
], words=WORDS, base_size=8)
CAM2 = Camera(W, H, [(3.6, (540, 900, 1.15)), (4.72, (540, 960, 1.3), 'io'), (5.55, (540, 940, 1.2), 'io')],
              kicks=[(4.07, 0.08, 540, 600), (4.72, 0.16, 540, 900)], shakes=[(4.72, 0.4, 8)])


def shot_sea(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    if t >= 4.72:
        hearts_fish(fg, t)
    if t >= 4.07:
        k = popin(t, 4.07, 0.3) * popout(t, 4.7)
        blit(fg, fx.big('arrow', s=12).rotate(90, expand=True), 760, 600 + 20 * math.sin(t * 8), k, k, anchor='center')
    P2.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(flood(t, oc(prog(t, 4.45, 0.55))), fg, CAM2, t)


# ================================================================== shot 3: the yellow boxfish
FISH = (560, 760)
def fish_x(t): return lerp(-300, FISH[0], oc(prog(t, 5.55, 0.9)))
P3 = Presenter([
    (5.5, dict(path=Track([(5.5, (1250, 1000)), (6.0, (900, 1060), 'oc'), (9.2, (860, 1000))]), size=6, legs='fly', arms='point', point=FISH,
               look=FISH, expr='wow', ground=None, face=-1, hover=12)),
    (7.47, dict(arms='present', expr='grin', squash=True)),
], words=WORDS, base_size=6)
CAM3 = Camera(W, H, [(5.55, (540, 900, 1.25)), (6.05, (560, 800, 1.3), 'io'), (7.47, (560, 840, 1.12), 'io'), (9.2, (560, 840, 1.16))],
              kicks=[(6.05, 0.14, *FISH), (7.47, 0.12, *FISH), (8.45, 0.06, *FISH)])


def shot_fish(t):
    img = ocean(t); fg = layer()
    fy = FISH[1] + 20 * math.sin(t * 3)
    streamlines(fg, t, 7.47, FISH[0], fy, 980, 360, n=7, col=(200, 236, 255), bulge=0.8)
    blit(fg, up(boxfish(int(t * 8) % 2 * 2), 10), fish_x(t), fy, 1, 1, 3 * math.sin(t * 4), anchor='center')
    fx.ring(fg, t, 6.05, FISH[0], fy, GLOW, life=0.35, r1=300)
    dg.label(fg, t, 6.05, 'YELLOW BOXFISH', (FISH[0] + 20, fy + 110), (520, 1000), '#ffd23f', '#1a1a2e', '#e8b923', s=7, t1=7.3)
    if t >= 7.47:
        k = popin(t, 7.47, 0.3)
        blit(fg, fx.big('badge', 'SLIPPERY SHAPE', '#7fe3a0', '#1a1a2e', '#3cc85a', s=7), 520, 1010, k, k, 2 * math.sin(t * 3), anchor='center')
    P3.draw(fg, t)
    photo(fg, t, 6.6, 7.4, 'boxfish', 560, 470, 520, 400, 4, 'YELLOW BOXFISH (OSTRACION CUBICUS)', focus=(0.5, 0.5))
    return finish(img, fg, CAM3, t, rim=False)


# ================================================================== shot 4: 2005, the Bionic concept car
MORPH = (560, GROUND)
def mk(t): return io(prog(t, 10.65, 0.75))          # 0 fish -> 1 car
P4 = Presenter([
    (9.15, dict(path=Track([(9.15, (-200, 500)), (9.55, (170, GROUND), 'oc')]), size=6, legs='auto', arms='fly', expr='smile', face=1, ground=None)),
    (9.55, dict(ground=GROUND, squash=True, arms='point', point=(MORPH[0], 900), look=(MORPH[0], 900), expr='wow', face=None)),
    (11.49, dict(arms='cheer2', expr='grin', point=None, look=None, look_camera=True, squash=True)),
    (12.43, dict(arms='present', expr='smile', look=(MORPH[0], 900))),
], words=WORDS, base_size=6)
CAM4 = Camera(W, H, [(9.2, (540, 820, 1.2)), (10.65, (560, 960, 1.18), 'io'), (11.49, (560, 940, 1.1), 'io'), (14.15, (560, 900, 1.16))],
              kicks=[(9.49, 0.14, 540, 400), (11.1, 0.16, MORPH[0], 980), (11.49, 0.1, MORPH[0], 980), (13.42, 0.08, 560, 560)],
              shakes=[(11.0, 0.3, 10)])


def shot_morph(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    if 9.49 <= t < 10.6:
        k = popin(t, 9.49, 0.3) * popout(t, 10.45)
        blit(fg, fx.big('badge', '2005', '#ffd23f', '#1a1a2e', '#e8b923', s=14), 540, 400, k, k, 3 * math.sin(t * 3), anchor='center')
        fx.burst(fg, t, 9.49, 540, 400, GLOW, seed=71)
    m = mk(t)
    fx.rays(fg, t, 11.05, MORPH[0], GROUND - 180, GLOW, life=1.0, r=600)
    fx.contact_shadow(fg, MORPH[0], GROUND, 640 * max(0.3, m), s=S, alpha=140)
    if m < 0.55:                                                                   # fish swells and squares off
        kf = 1 - ic(clamp((m - 0.3) / 0.25))
        sx = 10 + 4 * m
        blit(fg, up(boxfish(int(t * 8) % 2 * 2), 10), MORPH[0], GROUND - 40 - 120 * (1 - m), kf * sx / 10, kf * (1 + 0.3 * m),
             2 * math.sin(t * 5), anchor='bottom')
    if m > 0.35:
        kc = clamp((m - 0.35) / 0.4); sr, sv = wob(t, (11.4,), 0.06)
        blit(fg, up(bionic(0), 7), MORPH[0], GROUND, kc * sr, kc * sv)
    fx.poof(fg, t, 11.0, MORPH[0], GROUND - 150, seed=14, life=0.5, scale=1.3)
    fx.sparkles(fg, t, MORPH[0], GROUND - 180, 640, 260, n=10, seed=34)
    dg.label(fg, t, 11.49, 'BIONIC CONCEPT', (MORPH[0] + 60, GROUND - 260), (MORPH[0], 640), '#ffffff', '#1a1a2e', '#d6d9e2', s=8, t1=12.25)
    if t >= 13.05:                                                                 # same shape: fish outline over the car
        ko = clamp((t - 13.05) / 0.3) * (0.75 + 0.25 * math.sin(t * 8))
        o = fish_outline().copy(); o.putalpha(o.getchannel('A').point(lambda a: int(a * ko)))
        blit(fg, o, MORPH[0] + 10, GROUND - 30, anchor='bottom')
        k = popin(t, 13.05, 0.3)
        blit(fg, fx.big('badge', 'SAME SHAPE', '#ffd23f', '#1a1a2e', '#e8b923', s=7), 560, 620, k, k, -2, anchor='center')
    P4.draw(fg, t)
    GAR.reflect(img, fg)
    photo(fg, t, 11.95, 12.95, 'bionic', 560, 560, 560, 420, -3, 'MERCEDES-BENZ BIONIC, 2005', focus=(0.5, 0.55), zoom=0.1)
    return finish(img, fg, CAM4, t)


# ================================================================== shot 5: the best engineers are fish
FISH5 = (600, 700)
P5 = Presenter([
    (14.1, dict(path=Track([(14.1, (1300, 500)), (14.5, (230, GROUND), 'oc')]), size=7, legs='auto', arms='fly', expr='grin', face=-1, ground=None)),
    (14.5, dict(ground=GROUND, squash=True, arms='point', point=FISH5, look=FISH5, expr='smile', face=None)),
    (16.53, dict(arms='thumb', point=None, look=None, look_camera=True, expr='grin', squash=True)),
], words=WORDS, base_size=7)
CAM5 = Camera(W, H, [(14.15, (560, 760, 1.3)), (15.63, (580, 720, 1.4), 'io'), (16.53, (560, 820, 1.15), 'io'), (17.1, (560, 820, 1.18))],
              kicks=[(14.34, 0.08, *FISH5), (15.63, 0.14, *FISH5), (16.53, 0.14, *FISH5)])


def shot_engineer(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    fx.rays(fg, t, 15.63, *FISH5, GLOW, life=1.2, r=600)
    kf = popin(t, 14.2, 0.35)
    blit(fg, up(boxfish(int(t * 8) % 2 * 2, hat=t >= 15.63), 10), FISH5[0], FISH5[1] + 20 * math.sin(t * 3), kf, kf, 4 * math.sin(t * 3),
         anchor='center')
    fx.burst(fg, t, 15.63, FISH5[0], FISH5[1] - 120, GLOW, seed=72)
    if t >= 15.63:
        k = popin(t, 15.63, 0.3) * (1 + 0.05 * math.sin(t * 9))
        blit(fg, fx.big('badge', 'ENGINEER', '#ffd23f', '#1a1a2e', '#e8b923', s=11), 600, 420, k, k, 4 * math.sin(t * 4), anchor='center')
    fx.sparkles(fg, t, *FISH5, 600, 360, n=10, seed=36)
    fx.confetti(fg, t, 16.53, 600, 600, n=36, seed=6)
    P5.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM5, t)


shot_teaser, TEASE_CUES = kit.teaser(END_T, WORDS)

# ================================================================== shots + transitions
SHOTS = [(-1.0, shot_hook), (3.6, shot_sea), (5.55, shot_fish), (9.2, shot_morph), (14.15, shot_engineer), (END_T, shot_teaser)]
TRANS = {1: (3.6, 3.8, 'whip', dict(dx=0, dy=1)), 2: (5.55, 5.75, 'whip', dict(dx=-1)), 3: (9.2, 9.42, 'push', None),
         4: (14.15, 14.35, 'whip', dict(dx=1)), 5: (END_T, END_T + 0.2, 'whip', dict(dx=1))}
KEYCOL = {'mercedes': YEL, 'air': (170, 220, 255), 'nothing': YEL, 'sea': (90, 180, 255), 'yellow': YEL, 'boxfish': YEL,
          'perfectly': kit.GRN, 'shaped': kit.GRN, 'water': (90, 180, 255), '2005': YEL, 'bionic': YEL, 'shape': YEL,
          'engineers': YEL, 'fish': YEL}
CUES = [
    (0.0, 'vroom', 0.8), (0.05, 'stamp', 0.7), (0.07, 'sparkle', 0.6), (0.8, 'thump', 0.6), (1.47, 'whoosh', 0.7), (2.6, 'pop', 0.8),
    (2.62, 'ding', 0.5),
    (3.95, 'thump', 0.5), (4.07, 'pop', 0.6), (4.5, 'slide_down', 0.6), (4.72, 'boom', 0.4), (4.74, 'sparkle', 0.6),
    (5.6, 'whoosh', 0.5), (6.05, 'pop', 0.8), (6.07, 'ding', 0.6), (6.6, 'pop', 0.6), (7.47, 'sparkle', 0.7), (7.5, 'pop', 0.6),
    (9.49, 'pop', 0.8), (9.51, 'ding', 0.6), (10.65, 'creak', 0.6), (11.0, 'poof', 0.7), (11.05, 'boom', 0.4), (11.1, 'sparkle', 0.8),
    (11.49, 'pop', 0.7), (12.25, 'pop', 0.6), (13.05, 'ding', 0.6),
    (14.2, 'pop', 0.6), (15.63, 'ding', 0.8), (15.65, 'sparkle', 0.8), (16.53, 'confetti', 0.8),
] + TEASE_CUES

kit.setup(HERE, WORDS, DUR, END_T, SHOTS, TRANS, CUES, KEYCOL, overlay=overlay)

if __name__ == '__main__':
    kit.main()
