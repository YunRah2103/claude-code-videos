"""Renders 'Bugatti, 3,712 parts': two people, six days, one W16; every spark plug watched.

Template: videos/the-trabant (ac-idle shot structure on shared/episode.py). Word times come from align.py ->
words.json (the voiceover is the timing spine). Build time and part count are attributed ('Bugatti says'). The
spark-plug check is ion-current sensing; the knock/misfire response is a cylinder cut or less boost. Generic
pixel engine, no brand marks. One framed reference photo of the engine, redrawn in pixels.
Shots:
  1 boom      0.00  a pixel engine bursts into floating parts; '3,712 parts'
  2 build     1.70  two mechanics wrench on the block while a calendar flips day 1 -> 6; 'six days'
  3 count     4.95  parts rain onto the bench while a counter runs to 3,712; W16 photo card
  4 plugs     7.35  a big spark plug glows, a sensor scan line sweeps it, sixteen checks tick; 'watches every spark plug'
  5 problem  10.30  one cylinder flashes KNOCK, goes dark (CYL OFF), the boost gauge pulls back
  6 count    13.85  the parts snap back into one engine; PRECISION
  7 teaser   15.25  shared NEXT EPISODE ending
"""
import math, os, sys
from functools import lru_cache
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared'))
import episode as kit
from episode import W, H, S, GROUND, GAR, GLOW, RED, YEL, GRN, WHITE, layer, finish, photo, title
from pixanim.motion import Track, prog, lerp, clamp, oc, ic, io
from pixanim.camera import Camera
from pixanim.presenter import Presenter
from pixanim import fx, sprites, diagram as dg
from pixanim.fx import blit, popin, popout
from pixanim.grid import up, outline, Grid, text_width

WORDS = kit.load_words(HERE)
DUR, END_T = 17.2, 15.35


# ------------------------------------------------------------------ episode sprites
@lru_cache(None)
def block(lit=-1, off=-1, ph=0):
    """Engine block side view (96x56): sump, cam covers, eight visible coil packs (lamps), intake runners.
    Lamp `lit` glows yellow, lamp `off` is red-dark (cut)."""
    img = Image.new('RGBA', (96, 56), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rectangle((6, 18, 89, 44), fill=(130, 136, 148)); d.line([(6, 18), (89, 18)], fill=(176, 182, 194))
    d.rectangle((10, 44, 85, 54), fill=(96, 100, 112))
    d.rectangle((4, 8, 91, 18), fill=(60, 64, 76)); d.line([(4, 8), (91, 8)], fill=(110, 116, 128))
    for i in range(8):
        x = 10 + i * 10
        col = (255, 230, 90) if i == lit else (90, 30, 34) if i == off else (40, 42, 52)
        d.rectangle((x, 2, x + 5, 8), fill=(200, 204, 214)); d.rectangle((x + 1, 3, x + 4, 6), fill=col)
    for i in range(6): d.rectangle((14 + i * 12, 24, 20 + i * 12, 38), fill=(110, 116, 128))
    d.ellipse((0, 26, 14, 40), fill=(80, 84, 96)); a = math.radians(ph * 45)
    d.line([(7, 33), (7 + 5 * math.cos(a), 33 + 5 * math.sin(a))], fill=(220, 224, 232), width=2)
    return outline(img)


def _part(kind, rot):
    img = Image.new('RGBA', (14, 14), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    if kind == 0:   # bolt
        d.rectangle((5, 1, 8, 4), fill=(200, 204, 214)); d.rectangle((6, 4, 7, 12), fill=(170, 176, 188))
        for y in range(5, 12, 2): d.point((8, y), fill=(120, 126, 138))
    elif kind == 1:   # gear
        d.ellipse((2, 2, 11, 11), fill=(180, 186, 198)); d.ellipse((5, 5, 8, 8), fill=(60, 64, 76))
        for k in range(8):
            a = math.radians(k * 45); d.point((6.5 + 6 * math.cos(a), 6.5 + 6 * math.sin(a)), fill=(180, 186, 198))
    elif kind == 2:   # piston
        d.rectangle((3, 2, 10, 8), fill=(214, 220, 230)); d.line([(3, 4), (10, 4)], fill=(120, 126, 138))
        d.rectangle((6, 8, 7, 12), fill=(150, 156, 170))
    elif kind == 3:   # spring
        for y in range(2, 12, 2): d.line([(4, y), (9, y + 1)], fill=(120, 200, 255))
    elif kind == 4:   # spark plug
        d.rectangle((6, 1, 7, 3), fill=(200, 204, 214)); d.rectangle((5, 3, 8, 7), fill=(248, 248, 244)); d.rectangle((5, 8, 8, 11), fill=(170, 176, 188))
    else:   # valve
        d.line([(6, 1), (6, 10)], fill=(200, 204, 214)); d.polygon([(3, 12), (9, 12), (6, 9)], fill=(200, 204, 214))
    return outline(img).rotate(rot, Image.NEAREST)


@lru_cache(None)
def part(kind, rot): return up(_part(kind, rot), 6)


@lru_cache(None)
def mechanic(ph=0, flip=False):
    """Small mechanic (18x30): cap, blue overalls, wrench arm on a 2-frame swing. No logos."""
    img = Image.new('RGBA', (22, 30), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rectangle((6, 1, 14, 3), fill=(214, 48, 58)); d.rectangle((13, 3, 17, 4), fill=(214, 48, 58))
    d.rectangle((6, 4, 14, 10), fill=(232, 182, 140)); d.point((12, 6), fill=(26, 26, 46))
    d.rectangle((5, 11, 15, 22), fill=(60, 110, 190)); d.rectangle((8, 12, 12, 15), fill=(80, 130, 210))
    d.rectangle((5, 22, 9, 29), fill=(50, 90, 160)); d.rectangle((11, 22, 15, 29), fill=(50, 90, 160))
    d.rectangle((4, 28, 9, 29), fill=(30, 30, 40)); d.rectangle((11, 28, 16, 29), fill=(30, 30, 40))
    ay = 12 if ph else 15
    d.line([(15, 13), (19, ay)], fill=(60, 110, 190), width=2); d.line([(19, ay), (21, ay - 3)], fill=(200, 204, 214), width=2)
    img = outline(img)
    return img.transpose(Image.FLIP_LEFT_RIGHT) if flip else img


@lru_cache(None)
def calendar(day):
    img = Image.new('RGBA', (34, 36), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rectangle((0, 3, 33, 35), fill=(248, 248, 244)); d.rectangle((0, 3, 33, 11), fill=(214, 48, 58))
    for x in (7, 26): d.rectangle((x, 0, x + 1, 5), fill=(90, 94, 106))
    img = outline(img)
    g = Grid(text_width(str(day)), 7); g.text(0, 0, str(day), '#1a1a2e'); lab = up(g.image(outline=False), 3)
    img.paste(lab, (17 - lab.width // 2, 24 - lab.height // 2 + 2), lab)
    return img


@lru_cache(None)
def plug(glow=0.0):
    """Big spark plug (20x56): terminal, white ceramic ribs, hex, thread, electrode; sparks when glow > 0.5."""
    img = Image.new('RGBA', (20, 60), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rectangle((7, 0, 12, 5), fill=(200, 204, 214))
    d.rectangle((5, 5, 14, 26), fill=(248, 248, 244))
    for y in range(8, 26, 4): d.line([(4, y), (15, y)], fill=(222, 222, 216))
    d.rectangle((3, 27, 16, 34), fill=(176, 182, 194)); d.line([(3, 27), (16, 27)], fill=(230, 234, 242))
    d.rectangle((6, 35, 13, 48), fill=(150, 156, 170))
    for y in range(36, 48, 2): d.line([(6, y), (13, y + 1)], fill=(120, 126, 138))
    d.line([(9, 48), (9, 52)], fill=(200, 204, 214)); d.line([(9, 54), (12, 54), (12, 52)], fill=(200, 204, 214))
    if glow > 0.5:
        d.point((9, 53), fill=(255, 255, 255)); d.point((10, 53), fill=(150, 220, 255)); d.point((8, 52), fill=(150, 220, 255))
    return outline(img)


@lru_cache(None)
def boost_gauge(v):
    img = Image.new('RGBA', (40, 40), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.ellipse((0, 0, 39, 39), fill=(150, 156, 170)); d.ellipse((3, 3, 36, 36), fill=(20, 21, 28))
    d.arc((5, 5, 34, 34), -40, 40, fill=(224, 48, 58))
    for k in range(9):
        a = math.radians(225 - k * 33.75); d.point((19.5 + 14 * math.cos(a), 19.5 - 14 * math.sin(a)), fill=(226, 230, 238))
    a = math.radians(225 - 270 * v)
    d.line([(19.5, 19.5), (19.5 + 13 * math.cos(a), 19.5 - 13 * math.sin(a))], fill=(255, 96, 40), width=2)
    d.ellipse((17, 17, 22, 22), fill=(176, 182, 192))
    return outline(img)


# ------------------------------------------------------------------ floating parts (shared by shots 1 and 6)
R = fx.rng(7)
PARTS = [(int(R.integers(0, 6)), R.uniform(-1, 1), R.uniform(-1, 1), R.uniform(0, 6.28), R.uniform(-90, 90)) for _ in range(46)]
BX, BY = 540, 980


def float_parts(fg, t, u, t_scatter):
    """u: 0 = packed in the block, 1 = scattered round the frame; parts spin and bob while out."""
    for i, (kind, ax, ay, ph, spin) in enumerate(PARTS):
        x = BX + ax * 160 * (1 - u) + ax * 440 * u + 14 * math.sin(t * 2 + ph) * u
        y = BY - 100 + ay * 90 * (1 - u) + ay * 560 * u + 16 * math.cos(t * 1.7 + ph) * u
        rot = int((spin * (t - t_scatter) * u) % 360) // 30 * 30
        blit(fg, part(kind, rot), x, y, 1, 1, 0, anchor='center')


# ================================================================== shot 1: hook, the engine bursts apart
BOOM = 0.3
CAM1 = Camera(W, H, [(-1.0, (540, 960, 1.3)), (0.0, (540, 960, 1.3)), (BOOM, (540, 960, 1.3)), (0.9, (540, 920, 1.05), 'oc'), (1.7, (540, 920, 1.1), 'io')],
              kicks=[(BOOM, 0.26, BX, BY), (1.0, 0.08, 540, 560)], shakes=[(BOOM, 0.45, 18)])


def shot_boom(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    if t < BOOM:
        sh = 6 * math.sin(t * 90) * prog(t, -0.4, 0.7)
        blit(fg, up(block(int(t * 30) % 8, -1, int(t * 20) % 8), 7), BX + sh, BY + 140)
    else:
        u = oc(prog(t, BOOM, 0.7))
        fx.burst(fg, t, BOOM, BX, BY - 100, GLOW, n=20, r0=100, r1=600, seed=1); fx.ring(fg, t, BOOM, BX, BY - 100, GLOW, r1=700)
        for k in range(5): fx.puff(fg, t, BOOM + k * 0.04, BX, BY - 100, seed=2 + k, life=0.8, size=1.4, drift=((k - 2) * 160, -120))
        float_parts(fg, t, u, BOOM)
        fx.sparkles(fg, t, 540, 900, 900, 900, n=9, seed=3)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM1, t)


def overlay(cv, t):
    title(cv, t, 0.05, 1.65, '3,712', RED, 400, 190, -3)
    title(cv, t, 0.3, 1.65, 'parts', WHITE, 570, 140, 3)
    title(cv, t, 1.85, 4.9, 'six days', YEL, 420, 130, -2)
    title(cv, t, 7.88, 10.25, 'watches every', GRN, 420, 110, -2)
    title(cv, t, 8.1, 10.25, 'spark plug', GRN, 550, 120, 2)


# ================================================================== shot 2: two people, six days
def day(t): return 1 + min(5, int(clamp((t - 1.85) / 2.5) * 6))
CAM2 = Camera(W, H, [(1.7, (540, 900, 1.12)), (2.22, (600, 820, 1.24), 'io'), (3.56, (540, 940, 1.16), 'io'), (4.95, (540, 940, 1.2))],
              kicks=[(1.01, 0.1, 540, 900), (1.85, 0.12, 820, 700), (2.75, 0.08, 540, 1000), (3.56, 0.14, 540, 980)])


def shot_build(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    blit(fg, up(block(-1, -1, 0), 8), 540, GROUND - 40)
    ImageDraw.Draw(fg).rectangle((140, GROUND - 40, 940, GROUND - 20), fill=(60, 120, 90, 255))
    for i, (x, fl) in enumerate(((180, False), (900, True))):
        k = popin(t, 1.75 + i * 0.12, 0.25)
        blit(fg, up(mechanic(int(t * 6 + i) % 2, fl), 9), x, GROUND, k, k)
        if int(t * 6 + i) % 2 == 0 and t > 2.0: fx.sparkles(fg, t, x + (150 if not fl else -150), GROUND - 200, 120, 80, n=2, seed=10 + int(t * 6))
    if t >= 1.01:
        k = popin(t, 1.01, 0.25) * popout(t, 1.75)
        blit(fg, fx.big('badge', '2 PEOPLE', '#ffffff', '#1a1a2e', '#d6d9e2', s=10), 540, 620, k, k, -3, anchor='center')
    if t >= 1.85:
        dd = day(t); k = popin(t, 1.85, 0.25) * (1 + 0.15 * math.exp(-((t - 1.85) % (2.5 / 6)) * 12))
        blit(fg, up(calendar(dd), 9), 820, 760, k, k, 4, anchor='center')
        if dd == 6: fx.burst(fg, t, 1.85 + 2.5 * 5 / 6, 820, 760, GLOW, n=12, seed=11)
    if t >= 3.56:
        k = popin(t, 3.56, 0.25)
        blit(fg, fx.big('tag', 'ONE W16', '#fff6e0', '#1a1a2e', s=8), 330, 760, k, k, -5, anchor='center')
    fx.sparkles(fg, t, 540, 900, 800, 300, n=5, seed=12)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM2, t)


# ================================================================== shot 3: counting 3,712 parts
def count(t): return int(3712 * oc(prog(t, 5.2, 1.6)))
P3 = Presenter([
    (4.9, dict(path=Track([(4.9, (1300, 300)), (5.3, (900, GROUND), 'oc')]), size=7, legs='auto', arms='fly', expr='talk', face=-1, ground=None)),
    (5.3, dict(ground=GROUND, squash=True, arms='point', point=(480, 560), look=(480, 560), expr='wow', face=None)),
    (6.86, dict(arms='cheer', point=None, expr='grin', squash=True)),
], words=WORDS, base_size=7)
CAM3 = Camera(W, H, [(4.95, (540, 900, 1.12)), (5.41, (500, 820, 1.22), 'io'), (6.86, (520, 860, 1.16), 'io'), (7.35, (520, 860, 1.2))],
              kicks=[(5.41, 0.14, 480, 560), (6.86, 0.2, 480, 560)], shakes=[(6.86, 0.3, 10)])


def shot_count(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    r = fx.rng(30)
    for i in range(70):                                     # parts rain onto a growing pile
        t0 = 5.0 + i * 0.026; x = 480 + r.uniform(-280, 280); kind = int(r.integers(0, 6)); rot = int(r.integers(0, 12)) * 30
        if t < t0: continue
        u = prog(t, t0, 0.45); y = lerp(-80, GROUND - 30 - r.uniform(0, 140) * (i / 70), ic(u))
        blit(fg, part(kind, rot), x, y, 1, 1, 0, anchor='center')
    if t >= 5.2:
        k = popin(t, 5.2, 0.25); v = count(t)
        blit(fg, fx.big('badge', f'{v:,}', '#e0303a' if v == 3712 else '#ffffff', '#1a1a2e' if v < 3712 else '#ffffff', '#b8222c' if v == 3712 else '#d6d9e2', s=13),
             480, 560, k, k, -2 + 2 * math.sin(t * 5), anchor='center')
        fx.sparkles(fg, t, 480, 560, 700, 220, n=6, seed=31)
    if t >= 6.86: fx.burst(fg, t, 6.86, 480, 560, RED, n=18, seed=32); fx.confetti(fg, t, 6.86, 480, 500, n=30, seed=33)
    photo(fg, t, 6.0, 6.8, 'w16', 500, 900, 600, 420, -3, 'A W16 ON DISPLAY', pix=4)
    P3.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM3, t)


# ================================================================== shot 4: watching every spark plug
SCAN0 = 8.31
def scan_y(t): return 620 + 560 * ((t - SCAN0) / 0.8 % 1)
CAM4 = Camera(W, H, [(7.35, (540, 900, 1.15)), (8.55, (420, 860, 1.26), 'io'), (9.69, (540, 900, 1.12), 'io'), (10.3, (540, 900, 1.16))],
              kicks=[(7.5, 0.1, 420, 860), (8.55, 0.14, 400, 900), (9.25, 0.1, 760, 700), (9.69, 0.12, 540, 1180)])


def shot_plugs(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    k = popin(t, 7.4, 0.3)
    spark = int(t * 8) % 2 and t >= 7.5
    blit(fg, up(plug(1.0 if spark else 0.0), 10), 400, 1170, k, k, 0)
    if spark:
        fx.rays(fg, t, 7.5, 400, 1110, (150, 220, 255), hold=True, r=130, n=8)
    if t >= SCAN0:                                         # sensor scan line sweeping the plug
        d = ImageDraw.Draw(fg); y = scan_y(t)
        d.rectangle((240, y - 6, 560, y + 6), fill=(90, 220, 120, 200)); d.rectangle((240, y - 20, 560, y - 6), fill=(90, 220, 120, 60))
    dg.label(fg, t, 8.55, 'ION SENSOR', (470, 900), (760, 700), '#7fe3a0', '#1a1a2e', '#3cc85a', s=7)
    for i in range(16):                                    # sixteen plugs, each ticks green
        t0 = 9.25 + i * 0.03; x, y = 640 + (i % 4) * 90, 950 + (i // 4) * 90
        blit(fg, fx.big('check', s=5) if t >= t0 + 0.2 else up(_part(4, 0), 5), x, y, popin(t, 9.0, 0.25), popin(t, 9.0, 0.25), 0, anchor='center')
    if t >= 9.69:
        k = popin(t, 9.69, 0.25)
        blit(fg, fx.big('tag', 'CHECKING', '#fff6e0', '#1a1a2e', s=8), 760, 1300, k, k, 4, anchor='center')
    fx.gsparkles(fg, t, 760, 1100, 400, 400, n=6, seed=40)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM4, t)


# ================================================================== shot 5: knock -> cut a cylinder, pull the boost
BAD = 4
def boost(t): return 0.78 - 0.4 * oc(prog(t, 12.87, 0.5)) + 0.01 * math.sin(t * 30)
P5 = Presenter([
    (10.25, dict(path=Track([(10.25, (-200, 400)), (10.65, (160, GROUND), 'oc')]), size=7, legs='auto', arms='fly', expr='shock', face=1, ground=None)),
    (10.65, dict(ground=GROUND, squash=True, arms='shock', look=(540, 760), expr='shock', face=None)),
    (11.65, dict(arms='point', point=(380, 760), look=(380, 760), expr='talk')),
    (12.87, dict(arms='point', point=(820, 560), look=(820, 560), expr='smirk')),
], words=WORDS, base_size=7)
CAM5 = Camera(W, H, [(10.3, (540, 900, 1.14)), (10.64, (440, 840, 1.3), 'io'), (11.89, (500, 880, 1.16), 'io'), (12.87, (700, 760, 1.24), 'io'), (13.85, (640, 820, 1.2), 'io')],
              kicks=[(10.64, 0.2, 380, 760), (11.65, 0.14, 380, 760), (12.87, 0.14, 820, 560)], shakes=[(10.64, 0.4, 14)])


def shot_problem(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    bad = 10.64 <= t < 11.65; off = BAD if t >= 11.65 else -1
    lit = BAD if bad and int(t * 10) % 2 else (int(t * 14) % 8 if not bad else -1)
    if lit == off: lit = -1
    sh = 6 * math.sin(t * 80) if bad else 2 * math.sin(t * 60)
    blit(fg, up(block(lit, off, int(t * 16) % 8), 7), 540 + sh, 1180)
    px = 540 - 48 * 7 + (10 + BAD * 10 + 2.5) * 7; py = 1180 - 56 * 7 + 5 * 7
    if bad:
        fx.ring(fg, t, 10.64, px, py, RED, r1=260); fx.burst(fg, t, 10.64, px, py, RED, n=12, seed=50)
        k = popin(t, 10.64, 0.2)
        blit(fg, fx.big('badge', 'KNOCK!', '#e0303a', '#ffffff', '#b8222c', s=10), px, 560, k, k, -6 + 4 * math.sin(t * 20), anchor='center')
    if t >= 11.65:
        fx.poof(fg, t, 11.65, px, py, seed=51)
        k = popin(t, 11.89, 0.25) * popout(t, 12.8)
        blit(fg, fx.big('tag', 'CYLINDER OFF', '#fff6e0', '#d6303a', s=8), px, 600, k, k, 4, anchor='center')
    if t >= 12.74:
        k = popin(t, 12.74, 0.25)
        blit(fg, up(boost_gauge(boost(t)), 8), 820, 560, k, k, 0, anchor='center')
        blit(fg, fx.big('tag', 'LESS BOOST', '#fff6e0', '#1a1a2e', s=7), 820, 800, k, k, -4, anchor='center')
    P5.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM5, t)


# ================================================================== shot 6: precision you can count
SNAP = 14.2
CAM6 = Camera(W, H, [(13.85, (540, 920, 1.06)), (SNAP + 0.35, (540, 940, 1.2), 'io'), (15.25, (540, 940, 1.26))],
              kicks=[(13.99, 0.08, 540, 900), (SNAP + 0.35, 0.22, BX, BY), (14.76, 0.12, 540, 560)], shakes=[(SNAP + 0.35, 0.25, 12)])


def shot_snap(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    if t < SNAP + 0.35:
        float_parts(fg, t, 1 - io(prog(t, SNAP, 0.35)), 0.3)
    else:
        blit(fg, up(block(int(t * 14) % 8, -1, int(t * 16) % 8), 7), BX, BY + 140)
        fx.burst(fg, t, SNAP + 0.35, BX, BY - 100, GLOW, n=18, seed=60); fx.ring(fg, t, SNAP + 0.35, BX, BY - 100, GLOW, r1=600)
        fx.sparkles(fg, t, BX, BY - 100, 900, 500, n=9, seed=61)
    if t >= 13.99:
        k = popin(t, 13.99, 0.25)
        blit(fg, fx.big('badge', 'PRECISION', '#ffd23f', '#1a1a2e', '#e8b923', s=11), 540, 620, k, k, -3 + 2 * math.sin(t * 5), anchor='center')
    GAR.reflect(img, fg)
    return finish(img, fg, CAM6, t)


shot_teaser, TEASE_CUES = kit.teaser(15.25, WORDS)

# ================================================================== shots + transitions
SHOTS = [(-1.0, shot_boom), (1.7, shot_build), (4.95, shot_count), (7.35, shot_plugs), (10.3, shot_problem), (13.85, shot_snap), (15.25, shot_teaser)]
TRANS = {1: (1.7, 1.9, 'whip', dict(dx=1)), 2: (4.95, 5.15, 'push', None), 3: (7.35, 7.55, 'iris', (480, 560)), 4: (10.3, 10.5, 'whip', dict(dx=0, dy=1)),
         5: (13.85, 14.05, 'push', None), 6: (15.25, 15.45, 'whip', dict(dx=1))}
KEYCOL = {'bugatti': YEL, 'six': YEL, 'w16': YEL, '3,712': RED, 'spark': GRN, 'problems.': RED, 'spots': RED, 'cylinder': YEL,
          'boost.': YEL, 'precision': GRN}
CUES = [
    (0.0, 'whoosh', 0.4), (0.05, 'pop', 0.5), (BOOM, 'boom', 1.0), (BOOM + 0.02, 'crash', 0.5), (BOOM + 0.05, 'sparkle', 0.8), (0.6, 'poof', 0.4),
    (1.01, 'pop', 0.6), (1.75, 'thump', 0.5), (1.87, 'thump', 0.5)] + [(1.85 + k * 2.5 / 6, 'click', 0.6) for k in range(6)] + [
    (1.85 + 2.5 * 5 / 6, 'ding', 0.7), (3.56, 'pop', 0.6),
    (5.0, 'slide_down', 0.5)] + [(5.2 + k * 0.2, 'coin', 0.35) for k in range(8)] + [(6.0, 'pop', 0.5), (6.86, 'cha_ching', 0.8), (6.88, 'confetti', 0.6),
    (7.5, 'click', 0.6), (8.31, 'whoosh', 0.6), (8.55, 'pop', 0.6), (9.25, 'ding', 0.5), (9.69, 'pop', 0.6),
    (10.64, 'buzzer', 0.7), (10.66, 'thump', 0.6), (11.65, 'poof', 0.7), (11.89, 'stamp', 0.6), (12.74, 'pop', 0.6), (12.87, 'slide_down', 0.5),
    (13.99, 'pop', 0.6), (SNAP, 'whoosh', 0.7), (SNAP + 0.35, 'thump', 0.9), (SNAP + 0.37, 'sparkle', 0.8), (14.76, 'ding', 0.7),
] + TEASE_CUES

kit.setup(HERE, WORDS, DUR, END_T, SHOTS, TRANS, CUES, KEYCOL, overlay=overlay, bar_car='blue', gauge=True, loud=True)

if __name__ == '__main__':
    kit.main()
