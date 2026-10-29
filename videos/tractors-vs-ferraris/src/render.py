"""Renders 'Tractors vs. Ferraris': the tractor maker who found his own clutch inside a sports car.

Template: videos/ac-idle -> jaguar-rise-fall shot structure; captions, progress bar, photo cards, mixer and the
NEXT EPISODE ending now live in shared/episode.py. Word times come from align.py -> words.json (the voiceover
is the timing spine). Speech runs 0-17.0 s; the 'Follow' card holds to 18.6 s. The rival sports car is generic.
Shots:
  1 hook    0.00  a pixel tractor rolls into a garage of sports cars; 'TRACTORS VS. FERRARIS'; 2241R photo on 'tractors'
  2 rival   3.45  whip; he buys a red sports car; it breaks: smoke, x1 x2 x3 wrench counter, BROKEN stamp on 'part'
  3 clutch  7.10  iris into the clutch; it spins and is labelled on 'clutch'; a tractor clutch slides in on 'tractors': SAME PART
  4 enzo   11.05  push; he tells the rival; the rival car's bubble answers 'STICK TO TRACTORS!' and a tractor drops in
  5 build  15.30  whip; his own sports car rolls out of the light: 350 GT photo, confetti on 'sports car'
  6 teaser 17.10  shared NEXT EPISODE ending
"""
import math, os, sys
from functools import lru_cache
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared'))
import episode as kit
from episode import W, H, S, GROUND, GAR, GLOW, RED, YEL, layer, finish, draw_car, photo, title, headlights
from pixanim.motion import Track, prog, lerp, clamp, oc, ic, io, wob
from pixanim.car import car
from pixanim.camera import Camera
from pixanim.presenter import Presenter
from pixanim import fx, diagram as dg
from pixanim.fx import blit, popin, popout
from pixanim.grid import up, outline

WORDS = kit.load_words(HERE)
DUR, END_T = 18.6, 17.1


# ------------------------------------------------------------------ episode sprites
@lru_cache(None)
def tractor(spin=0):
    """Side-view 1950s farm tractor (72x52 grid): big rear wheel, small front wheel, orange bonnet, exhaust stack."""
    img = Image.new('RGBA', (72, 52), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    body, shade, hi = (240, 140, 40), (196, 100, 26), (255, 196, 110)
    d.rectangle((50, 6, 52, 22), fill=(60, 63, 71)); d.rectangle((49, 4, 53, 6), fill=(40, 42, 48))     # exhaust stack
    d.polygon([(26, 20), (66, 22), (68, 34), (26, 36)], fill=body)                                           # bonnet
    d.line([(27, 21), (65, 23)], fill=hi); d.rectangle((26, 32, 68, 35), fill=shade)
    for x in range(56, 67, 3): d.line([(x, 25), (x, 31)], fill=shade)                                         # grille slats
    d.rectangle((14, 14, 22, 18), fill=(40, 42, 48)); d.rectangle((20, 10, 22, 22), fill=(40, 42, 48))     # seat
    d.line([(26, 20), (32, 10)], fill=(60, 63, 71), width=2); d.line([(29, 9), (36, 11)], fill=(30, 32, 38), width=2)  # wheel
    d.pieslice((0, 14, 38, 52), 180, 360, fill=body); d.pieslice((3, 17, 35, 49), 180, 360, fill=(0, 0, 0, 0))  # fender
    for cx, cy, r in ((19, 34, 16), (58, 43, 8.5)):
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(32, 33, 38))
        for k in range(14 if r > 10 else 9):
            a = math.radians(k * (360 / (14 if r > 10 else 9)) + spin)
            d.rectangle((cx + (r - 1) * math.cos(a) - 1, cy + (r - 1) * math.sin(a) - 1, cx + (r - 1) * math.cos(a) + 1,
                         cy + (r - 1) * math.sin(a) + 1), fill=(20, 21, 26))
        d.ellipse((cx - r * 0.55, cy - r * 0.55, cx + r * 0.55, cy + r * 0.55), fill=(255, 196, 60))
        d.ellipse((cx - 2, cy - 2, cx + 2, cy + 2), fill=(196, 100, 26))
    return outline(img)


@lru_cache(None)
def clutch(tint=0):
    """Clutch disc face-on (44x44): friction ring, steel plate, damper springs, splined hub."""
    img = Image.new('RGBA', (44, 44), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    ring = [(120, 104, 92), (150, 120, 70)][tint]
    d.ellipse((1, 1, 42, 42), fill=ring)
    for k in range(24):
        a = math.radians(k * 15); d.point((21.5 + 18 * math.cos(a), 21.5 + 18 * math.sin(a)), fill=(80, 70, 62))
    d.ellipse((8, 8, 35, 35), fill=(176, 182, 192)); d.arc((8, 8, 35, 35), 200, 320, fill=(222, 228, 236))
    for k in range(6):
        a = math.radians(k * 60 + 30); x, y = 21.5 + 9 * math.cos(a), 21.5 + 9 * math.sin(a)
        d.rectangle((x - 2, y - 2, x + 2, y + 2), fill=(70, 120, 200)); d.line([(x - 2, y), (x + 2, y)], fill=(150, 190, 240))
    d.ellipse((16, 16, 27, 27), fill=(96, 100, 110)); d.ellipse((19, 19, 24, 24), fill=(30, 32, 38))
    for k in range(8):
        a = math.radians(k * 45); d.point((21.5 + 4 * math.cos(a), 21.5 + 4 * math.sin(a)), fill=(150, 156, 168))
    return outline(img)


@lru_cache(None)
def flywheel():
    """Flywheel face-on (50x50): ring gear teeth, heavy grey disc, bolt circle."""
    img = Image.new('RGBA', (50, 50), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.ellipse((1, 1, 48, 48), fill=(110, 114, 124))
    for k in range(36):
        a = math.radians(k * 10); d.point((24.5 + 23.5 * math.cos(a), 24.5 + 23.5 * math.sin(a)), fill=(60, 63, 71))
    d.ellipse((5, 5, 44, 44), fill=(150, 156, 168)); d.arc((5, 5, 44, 44), 200, 320, fill=(200, 206, 216))
    for k in range(6):
        a = math.radians(k * 60); d.rectangle((24 + 10 * math.cos(a) - 1, 24 + 10 * math.sin(a) - 1, 24 + 10 * math.cos(a) + 1, 24 + 10 * math.sin(a) + 1), fill=(40, 42, 48))
    d.ellipse((19, 19, 30, 30), fill=(70, 74, 84))
    return outline(img)


@lru_cache(None)
def pressure_plate():
    """Pressure plate face-on (46x46): cover with diaphragm-spring fingers."""
    img = Image.new('RGBA', (46, 46), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.ellipse((1, 1, 44, 44), fill=(176, 182, 192)); d.ellipse((6, 6, 39, 39), fill=(130, 136, 148))
    for k in range(12):
        a = math.radians(k * 30)
        d.line([(22.5 + 6 * math.cos(a), 22.5 + 6 * math.sin(a)), (22.5 + 15 * math.cos(a), 22.5 + 15 * math.sin(a))], fill=(214, 220, 228), width=2)
    d.ellipse((17, 17, 28, 28), fill=(40, 42, 48))
    for a in (45, 165, 285):
        r = math.radians(a); d.rectangle((22 + 19 * math.cos(r) - 2, 22 + 19 * math.sin(r) - 2, 22 + 19 * math.cos(r) + 2, 22 + 19 * math.sin(r) + 2), fill=(96, 100, 110))
    return outline(img)


def wrench(n): return fx.big('badge', f'FIX X{n}', '#ffffff', '#e0303a', '#d6d9e2', s=7)


# ================================================================== shot 1: hook, a tractor among sports cars
TR1 = 640
def tr1_x(t): return lerp(1500, TR1, oc(prog(t, 0.0, 1.0)))
P1 = Presenter([
    (-1.0, dict(path=Track([(-1.0, (-200, 300)), (0.5, (-200, 300)), (1.0, (230, GROUND), 'ic')]), size=7, legs='auto', arms='fly',
                expr='wow', ground=None, face=1)),
    (1.0, dict(ground=GROUND, squash=True, arms='present', look=(TR1, 1000), expr='grin', face=None)),
    (1.81, dict(arms='point', point=(540, 560), look=(540, 560), expr='smile')),
], words=WORDS, base_size=7)
CAM1 = Camera(W, H, [(-1.0, (760, 1000, 1.45)), (0.0, (760, 1000, 1.45)), (1.0, (560, 980, 1.1), 'io'), (2.1, (540, 860, 1.12), 'io'),
                     (3.45, (540, 860, 1.16))],
              kicks=[(0.0, 0.1, 760, 1000), (1.0, 0.12, TR1, 1000), (2.08, 0.1, 540, 560)], shakes=[(0.0, 1.0, 6), (1.0, 0.25, 12)])


def shot_hook(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    for x, col, s in ((180, 'red', 4), (900, 'silver', 4)):                      # parked sports cars in the back
        fx.contact_shadow(fg, x, GROUND - 120, 360, s=S, alpha=90)
        draw_car(fg, col, x, s, y=GROUND - 120, sy=0.85, flip=x > 540)
    x = tr1_x(t)
    fx.contact_shadow(fg, x, GROUND, 560, s=S, alpha=140)
    sr, sv = wob(t, (1.0,), 0.06)
    blit(fg, up(tractor(int((1500 - x) * 0.4) % 360), 8), x + 4 * math.sin(t * 40) * (t < 1.0), GROUND, sr, sv)
    for k in range(4):
        fx.puff(fg, t, 0.1 + k * 0.25, x + 30, GROUND - 430, seed=20 + k, life=0.9, size=0.8, drift=(140, -220), col=(90, 92, 100))
    fx.dust(fg, t, 1.0, x, GROUND - 10, n=14, seed=43)
    fx.burst(fg, t, 1.0, x, GROUND - 220, GLOW, n=12, seed=70)
    P1.draw(fg, t)
    GAR.reflect(img, fg)
    photo(fg, t, 1.81, 3.35, 'tractor_2241r', 540, 560, 440, 500, -4, 'LAMBORGHINI TRACTOR, 1960', focus=(0.55, 0.62), zoom=0.35)
    return finish(img, fg, CAM1, t)


def overlay(cv, t):
    title(cv, t, 0.05, 1.75, 'Tractors vs. Ferraris', YEL, 470, 104, -3)
    if 0.05 <= t < 0.4: fx.ring(cv, t, 0.05, 540, 470, GLOW, life=0.35, r1=520)


# ================================================================== shot 2: he buys the sports car (night street)
def scroll2(t): return 700 * (t - 3.45)
CAR2S = 520
P2S = Presenter([
    (3.45, dict(path=Track([(3.45, (470, 975)), (3.6, (470, 975))]), size=5, legs='sit', arms='cheer1', expr='grin', face=1, ground=None)),
    (4.36, dict(arms='cheer2', expr='wow', squash=True)),
], words=WORDS, base_size=5)
CAM2S = Camera(W, H, [(3.45, (540, 1000, 1.25)), (4.36, (520, 960, 1.35), 'io'), (5.1, (520, 960, 1.4))],
               kicks=[(4.13, 0.08, 540, 640), (4.36, 0.14, CAR2S, 1050)], shakes=[(3.45, 1.7, 3)])


def shot_buy(t):
    sc = scroll2(t)
    img = kit.street(t, sc); cars = layer()
    bounce = 4 * math.sin(t * 22)
    headlights(cars, CAR2S + 290, kit.ROAD_Y - 90, 420)
    fx.contact_shadow(cars, CAR2S, kit.ROAD_Y, 600, s=S, alpha=150)
    draw_car(cars, 'red', CAR2S, 7, y=kit.ROAD_Y + bounce * 0.3, dist=sc, lights=True, sx=1.06, sy=0.86)
    for k in range(5):
        fx.puff(cars, t, 3.5 + k * 0.3, CAR2S - 330, kit.ROAD_Y - 30, seed=30 + k, life=0.7, size=0.7, drift=(-260, -60))
    fx.speed_lines(cars, 0.6, int(t * 10) % 5, col=(200, 204, 214))
    kit.ROAD.reflect(img, cars, depth=160, strength=0.3)
    img.alpha_composite(cars)
    fg = layer()
    if t >= 4.13:                                                                 # 'bought': SOLD tag and coins
        k = popin(t, 4.13, 0.25)
        blit(fg, fx.big('tag', 'SOLD!', '#fff6e0', '#d6303a', s=9), 640, 540, k, k, -8 + 4 * math.sin(t * 6), anchor='center')
        for i in range(6):
            u = clamp((t - 4.13 - 0.05 * i) / 0.7)
            if 0 < u < 1:
                blit(fg, fx.big('glyph', '$', '#ffd23f', s=9), 640 + (i - 2.5) * 70 * u * 3, 560 - 300 * u + 520 * u * u, 1, 1, 20 * math.sin(t * 9 + i), anchor='center')
    fx.glint(fg, t, 4.36, CAR2S + 150, kit.ROAD_Y - 230, r=150)
    fx.burst(fg, t, 4.36, CAR2S, kit.ROAD_Y - 200, RED, n=12, seed=61)
    if t >= 4.36: fx.sparkles(fg, t * 1.4, CAR2S, kit.ROAD_Y - 200, 600, 260, n=8, seed=62)
    P2S.draw(fg, t)
    return finish(img, fg, CAM2S, t, rim=False)


# ================================================================== shot 3: it keeps breaking (garage)
CAR2 = 470
P2 = Presenter([
    (5.05, dict(path=Track([(5.05, (1300, 400)), (5.4, (880, GROUND), 'oc')]), size=7, legs='auto', arms='fly', expr='smile', face=-1, ground=None)),
    (5.4, dict(ground=GROUND, squash=True, arms='point', point=(CAR2 + 200, 950), face=None, look=(CAR2, 1000), expr='think')),
    (5.64, dict(arms='shock', expr='shock', squash=True, point=None)),
    (6.31, dict(arms='shrug', expr='sad', look=None, look_camera=True)),
], words=WORDS, base_size=7)
CAM2 = Camera(W, H, [(5.1, (520, 960, 1.15)), (5.64, (500, 930, 1.22), 'io'), (7.1, (520, 900, 1.3))],
              kicks=[(5.39, 0.08, CAR2, 900), (5.64, 0.1, CAR2, 900), (6.05, 0.08, CAR2, 900), (6.31, 0.14, CAR2, 820)],
              shakes=[(5.64, 0.3, 12), (6.31, 0.3, 16)])


def shot_rival(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    x = CAR2
    fx.contact_shadow(fg, x, GROUND, 640, s=S, alpha=140)
    shake = 5 * math.sin(t * 50) if t >= 5.64 else 0
    sr, sv = wob(t, (5.39, 5.64, 6.05), 0.07)
    hood = 0.0 if t < 5.39 else min(1.0, (t - 5.39) / 0.25)
    blit(fg, up(car('red', 0, False, False, hood), 7), x + shake, GROUND, 1.06 * sr, 0.86 * sv)
    for k in range(8):                                                            # smoke from the open bonnet as it breaks
        fx.puff(fg, t, 5.45 + k * 0.2, CAR2 + 200, GROUND - 260, seed=40 + k, life=0.9, size=1.0 + 0.1 * k, drift=(60, -300), col=(150, 152, 160))
    for k in range(3):
        fx.burst(fg, t, (5.39, 5.64, 6.05)[k], CAR2 + 200, GROUND - 240, (255, 210, 63), n=10, r0=40, r1=200, seed=50 + k)
    for i, t0 in enumerate((5.39, 5.64, 6.05)):                                   # repair counter: FIX X1, X2, X3
        if t0 <= t < 7.3:
            k = popin(t, t0, 0.22)
            blit(fg, wrench(i + 1), 330 + 210 * i, 640 - 90 * i, k, k, (-6, 4, -3)[i] + 3 * math.sin(t * 7), anchor='center')
            fx.burst(fg, t, t0, 330 + 210 * i, 640 - 90 * i, RED, n=8, r0=70, r1=200, seed=60 + i)
    fx.stamp_at(fg, t, 6.31, 'BROKEN', CAR2, GROUND - 260, rot=-10, s=13)
    P2.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM2, t)


# ================================================================== shot 4: opened up, the clutch (exploded view)
CL = (540, 780)
def spread(t): return oc(prog(t, 7.39, 0.6))
def front(t): return io(prog(t, 8.89, 0.35))          # clutch comes forward, turns face-on
P3 = Presenter([
    (7.05, dict(path=Track([(7.05, (-200, 600)), (7.5, (170, GROUND), 'oc')]), size=6, legs='auto', arms='fly', expr='think', face=1, ground=None)),
    (7.5, dict(ground=GROUND, squash=True, arms='think', look=CL, expr='think', face=None)),
    (8.28, dict(arms='point', point=CL, look=CL, expr='wow', squash=True)),
], words=WORDS, base_size=6)
CAM3 = Camera(W, H, [(7.1, (540, 820, 1.3)), (8.28, (540, 800, 1.2), 'io'), (8.89, (540, 780, 1.45), 'io'), (9.6, (540, 780, 1.5))],
              kicks=[(7.39, 0.1, *CL), (8.28, 0.06, *CL), (8.89, 0.16, *CL)])


def shot_clutch(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    sp, fr = spread(t), front(t)
    fx.rays(fg, t, 8.89, *CL, GLOW, life=1.0, r=520)
    d = ImageDraw.Draw(fg)                                                        # the shaft they share
    d.line([(CL[0] - 380 * sp - 40, CL[1] + 100 * sp), (CL[0] + 380 * sp + 40, CL[1] - 100 * sp)], fill=(26, 26, 46), width=26)
    d.line([(CL[0] - 380 * sp - 40, CL[1] + 100 * sp), (CL[0] + 380 * sp + 40, CL[1] - 100 * sp)], fill=(150, 156, 168), width=12)
    spin = t * 200 * (1 - 0.8 * prog(t, 8.89, 0.5))
    parts = [(flywheel(), -1, 1 - fr), (clutch(0), 0, 1.0), (pressure_plate(), 1, 1 - fr)]
    for img_p, i, a in parts:
        if a <= 0.02: continue
        x = CL[0] + i * 230 * sp + (i * 260 * fr)
        y = CL[1] - i * 70 * sp
        sx = 0.42 + (0.58 * fr if i == 0 else 0)
        k = popin(t, 7.2 + 0.08 * (i + 1), 0.3) * a
        blit(fg, up(img_p, 8), x, y, sx * k * (1 + 0.25 * fr * (i == 0)), k * (1 + 0.25 * fr * (i == 0)), spin if i == 0 and fr > 0.5 else 0,
             anchor='center')
    for i, (txt, t0) in enumerate((('FLYWHEEL', 7.6), ('PRESSURE PLATE', 7.8))):
        if t0 <= t < 8.85:
            k = popin(t, t0, 0.25) * popout(t, 8.7)
            blit(fg, fx.big('badge', txt, '#ffffff', '#1a1a2e', '#d6d9e2', s=5), CL[0] + (i * 2 - 1) * 170, CL[1] + (200 if i == 0 else -250), k, k,
                 anchor='center')
    fx.ring(fg, t, 8.89, *CL, GLOW, life=0.4, r1=330)
    dg.label(fg, t, 8.95, 'CLUTCH', (CL[0], CL[1] - 160), (CL[0], 470), '#ffd23f', '#1a1a2e', '#e8b923', s=9)
    if t >= 8.9: fx.sparkles(fg, t, *CL, 520, 400, n=8, seed=63)
    P3.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM3, t)


# ================================================================== shot 5: split screen, same part in both
PANELS = ((40, 236, 1040, 752), (40, 786, 1040, 1302))


def _pan_car(p, t):
    blit(p, up(car('red'), 4), 330, 420, 1.06, 0.86)
    blit(p, up(clutch(0), 6), 780, 260 + 6 * math.sin(t * 3), 1, 1, t * 120, anchor='center')


def _pan_tractor(p, t):
    blit(p, up(tractor(int(t * 200) % 360), 5), 300, 440)
    blit(p, up(clutch(0), 6), 780, 260 + 6 * math.sin(t * 3 + 1), 1, 1, t * 120, anchor='center')


def shot_split(t):
    img = Image.blend(GAR.frame(t), Image.new('RGB', (W, H), (8, 8, 10)), 0.55).convert('RGBA')
    fg = layer()
    kit.split_panel(fg, t, 9.62, PANELS[0], _pan_car, 'SPORTS CAR', ('#e0303a', '#ffffff', '#b5222c'))
    kit.split_panel(fg, t, 9.96, PANELS[1], _pan_tractor, 'HIS TRACTOR', ('#ff8a3d', '#1a1a2e', '#c8662a'))
    if t >= 10.3:
        k = popin(t, 10.3, 0.3) * (1 + 0.05 * math.sin(t * 9))
        blit(fg, fx.big('badge', 'SAME PART', '#ffd23f', '#d6303a', '#e8b923', s=9), 760, 770, k, k, 4 * math.sin(t * 4), anchor='center')
        fx.burst(fg, t, 10.3, 760, 770, GLOW, seed=90)
        for i, y in enumerate((500, 1040)):
            kc = popin(t, 10.45 + 0.1 * i)
            blit(fg, fx.big('check', s=8), 940, y, kc, kc, anchor='center')
            fx.ring(fg, t, 10.45 + 0.1 * i, 940, y, (60, 200, 90), life=0.3, r1=140)
    img.alpha_composite(fg)
    return img.convert('RGB')


# ================================================================== shot 6: 'stick to tractors'
CAR4 = 700
P4 = Presenter([
    (11.0, dict(path=Track([(11.0, (-200, 500)), (11.4, (230, GROUND), 'oc')]), size=7, legs='auto', arms='fly', expr='talk', face=1, ground=None)),
    (11.4, dict(ground=GROUND, squash=True, arms='point', point=(CAR4, 1000), look=(CAR4, 1000), expr='smile', face=None)),
    (12.95, dict(arms='hips', expr='smirk', point=None, look=(CAR4, 700))),
    (14.02, dict(arms='shock', expr='shock', squash=True)),
    (14.6, dict(arms='hips', expr='sad', look=None, look_camera=True)),
], words=WORDS, base_size=7)
CAM4 = Camera(W, H, [(11.05, (520, 960, 1.15)), (12.5, (500, 960, 1.18), 'io'), (12.95, (700, 820, 1.6), 'io'), (14.2, (680, 760, 1.5)),
                     (14.39, (560, 900, 1.12), 'io'), (15.3, (540, 880, 1.16))],
              kicks=[(11.85, 0.08, CAR4, 1000), (13.35, 0.12, 700, 560), (14.02, 0.1, 700, 560), (14.39, 0.14, 540, 520)],
              shakes=[(14.39, 0.3, 14)])


def shot_enzo(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    fx.contact_shadow(fg, CAR4, GROUND, 620, s=S, alpha=140)
    hop = 30 * abs(math.sin((t - 12.95) * 14)) * (12.95 <= t < 14.7)                 # the rival car 'talks' back
    draw_car(fg, 'red', CAR4, 7, y=GROUND - hop, flip=True, sx=1.06, sy=0.86, lights=True)
    if t >= 11.27 and t < 12.9:                                                    # his complaint: a clutch in a bubble
        kb = popin(t, 11.27, 0.25) * popout(t, 12.7)
        blit(fg, fx.big('bubble', 3, s=10), 330, 760, kb, kb, anchor='center')
        blit(fg, up(clutch(0), 4), 330, 740, kb, kb, t * 90, anchor='center')
    if t >= 13.35:
        ks = popin(t, 13.35, 0.3) * (1 + 0.05 * math.sin(t * 10))
        blit(fg, fx.big('tag', 'STICK TO TRACTORS!', '#ffffff', '#d6303a', s=6), 700, 600, ks, ks, -4 + 3 * math.sin(t * 6), anchor='center')
        fx.burst(fg, t, 13.35, 640, 560, RED, seed=95)
    for k in range(6):                                                            # it fumes
        fx.puff(fg, t, 13.0 + k * 0.18, CAR4 - 220, GROUND - 260, seed=80 + k, life=0.8, size=0.9, drift=(-80, -280), col=(220, 224, 232))
    if 12.95 <= t < 14.3:
        ka = popin(t, 12.95, 0.2)
        blit(fg, fx.big('glyph', '!', '#e0303a', s=14), CAR4 + 160, GROUND - 470 + 10 * math.sin(t * 12), ka, ka, 10 * math.sin(t * 9), anchor='center')
    fx.ring(fg, t, 13.35, 640, 560, (224, 48, 58), life=0.35, r1=360)
    if t >= 14.39:                                                                 # a tractor drops in on 'tractors'
        ty = lerp(-200, GROUND - 330, ic(prog(t, 14.39, 0.25)))
        sr, sv = wob(t, (14.64,), 0.08)
        blit(fg, up(tractor(0), 4), 520, ty, sr, sv)
        fx.dust(fg, t, 14.64, 520, GROUND - 330, n=12, seed=96)
    P4.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM4, t)


# ================================================================== shot 5: he builds his own
CAR5 = 560
P5 = Presenter([
    (15.25, dict(path=Track([(15.25, (540, -200)), (15.6, (200, GROUND), 'oc')]), size=7, legs='auto', arms='fly', expr='grin', face=1, ground=None)),
    (15.6, dict(ground=GROUND, squash=True, arms='present', look=(CAR5, 1000), expr='grin', face=None)),
    (16.28, dict(arms='cheer2', expr='grin', look=None, look_camera=True, squash=True)),
], words=WORDS, base_size=7)
CAM5 = Camera(W, H, [(15.3, (560, 860, 1.25)), (16.3, (560, 900, 1.12), 'io'), (17.1, (560, 880, 1.16))],
              kicks=[(15.71, 0.08, CAR5, 1000), (16.28, 0.16, CAR5, 1000), (16.63, 0.08, 540, 520)], shakes=[(16.28, 0.2, 10)])


def shot_build(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    x = CAR5
    fx.rays(fg, t, 16.28, CAR5, GROUND - 200, GLOW, life=1.0, r=600)
    fx.contact_shadow(fg, x, GROUND, 620, s=S, alpha=140)
    sr, sv = wob(t, (15.71, 16.31), 0.07)
    spr = up(car('silver', 0, t >= 16.28), 7)
    if t < 16.28:                                                                 # bare primer shell while he builds it
        prim = Image.new('RGBA', spr.size, (96, 100, 110, 255)); prim.putalpha(spr.getchannel('A'))
        spr = Image.blend(spr, prim, 0.7 * (1 - prog(t, 16.1, 0.18)))
    blit(fg, spr, x, GROUND - 120 * (1 - oc(prog(t, 15.4, 0.3))), 1.08 * sr, 0.84 * sv, flip=True)
    for i, (t0, wx) in enumerate(((15.43, -200), (15.58, 120), (15.71, -40), (15.9, 220))):   # welding sparks
        fx.burst(fg, t, t0, x + wx, GROUND - 160, (255, 230, 120), n=14, r0=20, r1=220, seed=110 + i)
        fx.ring(fg, t, t0, x + wx, GROUND - 160, (255, 255, 255), life=0.2, r1=90)
    fx.glint(fg, t, 16.4, CAR5 + 100, GROUND - 230, r=140)
    fx.sparkles(fg, t * 1.3, CAR5, GROUND - 240, 620, 260, n=10, seed=52)
    dg.label(fg, t, 16.28, 'HIS OWN', (CAR5, GROUND - 260), (CAR5 + 120, GROUND - 520), '#7fe3a0', '#1a1a2e', '#3cc85a', s=9)
    fx.confetti(fg, t, 16.28, 560, 700, n=40, seed=5)
    P5.draw(fg, t)
    GAR.reflect(img, fg)
    photo(fg, t, 15.45, 17.05, 'lambo_350gt', 560, 520, 520, 390, 4, 'HIS FIRST CAR: 350 GT, 1964', focus=(0.3, 0.62), zoom=0.4)
    return finish(img, fg, CAM5, t)


shot_teaser, TEASE_CUES = kit.teaser(17.1, WORDS)

# ================================================================== shots + transitions
SHOTS = [(-1.0, shot_hook), (3.45, shot_buy), (5.1, shot_rival), (7.1, shot_clutch), (9.6, shot_split), (11.05, shot_enzo), (15.3, shot_build),
         (17.1, shot_teaser)]
TRANS = {1: (3.45, 3.65, 'whip', dict(dx=-1)), 2: (5.1, 5.3, 'push', None), 3: (7.1, 7.34, 'iris', (CAR2 + 200, 950)),
         4: (9.6, 9.8, 'whip', dict(dx=0, dy=1)), 5: (11.05, 11.27, 'push', None), 6: (15.3, 15.5, 'whip', dict(dx=0, dy=1)),
         7: (17.1, 17.3, 'whip', dict(dx=1))}
KEYCOL = {'tractors': YEL, 'ferrari': RED, 'breaking': RED, 'part': RED, 'clutch': YEL, 'enzo': RED, 'stick': RED, 'sports': YEL,
          'car': YEL, 'built': kit.GRN, 'own': kit.GRN}
CUES = [
    (0.0, 'vroom', 0.7), (0.05, 'stamp', 0.8), (0.07, 'sparkle', 0.6), (0.3, 'thump', 0.4), (0.6, 'thump', 0.4), (1.0, 'thump', 0.9),
    (1.0, 'boom', 0.35), (1.81, 'pop', 0.8), (1.83, 'sparkle', 0.5),
    (3.5, 'vroom', 0.8), (4.13, 'cha_ching', 0.7), (4.36, 'ding', 0.6), (4.4, 'sparkle', 0.5), (5.39, 'click', 0.6), (5.41, 'poof', 0.4), (5.64, 'crash', 0.6),
    (5.66, 'buzzer', 0.4), (5.7, 'poof', 0.5), (6.05, 'buzzer', 0.4), (6.31, 'stamp', 1.0), (6.33, 'boom', 0.35),
    (7.3, 'pop', 0.5), (7.39, 'slide_down', 0.6), (7.6, 'pop', 0.5), (7.8, 'pop', 0.5), (8.89, 'ding', 0.8), (8.91, 'sparkle', 0.7),
    (9.62, 'pop', 0.7), (9.96, 'pop', 0.7), (10.3, 'cha_ching', 0.8), (10.45, 'click', 0.5), (10.55, 'click', 0.5),
    (11.27, 'pop', 0.6), (12.95, 'whoosh', 0.6), (13.0, 'poof', 0.4), (13.35, 'buzzer', 0.6), (13.37, 'pop', 0.8), (14.39, 'fall', 0.7), (14.64, 'crash', 0.6), (14.66, 'boom', 0.4),
    (15.4, 'thump', 0.6), (15.43, 'click', 0.7), (15.58, 'click', 0.7), (15.71, 'stamp', 0.5), (15.9, 'click', 0.7), (16.28, 'vroom', 0.8), (16.28, 'confetti', 0.8), (16.3, 'ding', 0.8), (16.32, 'sparkle', 0.7),
] + TEASE_CUES

kit.setup(HERE, WORDS, DUR, END_T, SHOTS, TRANS, CUES, KEYCOL, overlay=overlay)

if __name__ == '__main__':
    kit.main()
