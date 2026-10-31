"""Renders 'Project One, 275 keys': Formula One engineering in a road car, over 1,000 applicants, 275 buyers.

Template: videos/the-trabant (ac-idle shot structure on shared/episode.py). Word times come from align.py ->
words.json (the voiceover is the timing spine). The reported price is left out (not hedged into the script). Cars
are generic pixel redraws (an open-wheel racer and a finned road car) with no badges or lettering.
Shots:
  1 showroom  0.00  an open-wheel racer under a spotlight behind a velvet rope; 'Formula One engineering';
                    a poof turns it into a finned road car; photo card of the real car (pixel redraw)
  2 engine    3.55  a 1.6 L V6 assembles, the hybrid motor and battery bolt on with sparks; '1,000 horsepower'
  3 applied   8.40  rows of tiny applicants fill the frame, waving forms; 1,000+ APPLIED
  4 keys     11.10  the crowd poofs down to 275 pixel keys, the counter drops 1,000 -> 275; '275 buyers'
  5 teaser   13.95  shared NEXT EPISODE ending
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
from pixanim import fx, diagram as dg
from pixanim.fx import blit, popin, popout
from pixanim.grid import up, outline

WORDS = kit.load_words(HERE, 'words_v1.json')     # first read: the shots are timed on it
NEW = kit.load_words(HERE)                          # current read (captions); WARP maps it onto WORDS
S1, S2, S3 = kit.at(NEW, 'only') - 0.13, kit.at(NEW, "it's") - 0.2, kit.at(NEW, 'a', 2) - 0.12   # section cuts follow the read
BODY_END = kit.at(NEW, 'would') - 0.12
END_T = NEW[-1]['e'] + 0.3
DUR = END_T + 1.0
SILVER, DARK = (196, 202, 212), (40, 42, 52)


# ------------------------------------------------------------------ episode sprites
def _wheel(d, cx, cy, r, spin):
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(22, 22, 28)); rr = r * 0.55
    d.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), fill=(150, 156, 170))
    for k in range(5):
        a = math.radians(spin + k * 72); d.point((cx + rr * 0.7 * math.cos(a), cy + rr * 0.7 * math.sin(a)), fill=(60, 64, 76))


@lru_cache(None)
def racer(spin=0):
    """Open-wheel racer (96x30), nose right: front and rear wings, sidepods, halo, helmet, exposed wheels."""
    img = Image.new('RGBA', (96, 30), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rectangle((2, 4, 12, 7), fill=DARK); d.rectangle((6, 7, 8, 16), fill=DARK)              # rear wing
    d.polygon([(10, 14), (30, 10), (52, 12), (86, 19), (92, 22), (92, 24), (10, 24)], fill=SILVER)
    d.line([(30, 10), (52, 12), (86, 19)], fill=(236, 240, 248))
    d.polygon([(34, 18), (60, 18), (64, 22), (30, 22)], fill=(0, 160, 150))                   # teal stripe
    d.ellipse((44, 6, 52, 13), fill=(240, 200, 60)); d.line([(40, 9), (56, 9)], fill=DARK, width=2)   # helmet + halo
    d.rectangle((84, 24, 95, 26), fill=DARK)                                                 # front wing
    for cx in (20, 76): _wheel(d, cx, 21, 8, spin)
    return outline(img)


@lru_cache(None)
def hyper(spin=0):
    """Low two-seat road car (96x34), nose right: roof scoop, shark fin, long tail, slim lamps."""
    img = Image.new('RGBA', (96, 34), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    pts = [(4, 22), (6, 14), (30, 12), (40, 4), (58, 4), (72, 14), (92, 20), (94, 26), (4, 27)]
    d.polygon(pts, fill=SILVER); d.line(pts[:-2], fill=(236, 240, 248))
    d.polygon([(10, 12), (34, 2), (38, 2), (30, 12)], fill=SILVER); d.line([(10, 12), (34, 2)], fill=(236, 240, 248))   # fin
    d.polygon([(42, 6), (56, 6), (66, 14), (40, 14)], fill=(40, 52, 70)); d.line([(43, 7), (55, 7)], fill=(120, 150, 190))
    d.rectangle((44, 1, 50, 4), fill=DARK)                                                    # roof scoop
    d.line([(6, 22), (92, 22)], fill=(150, 156, 170)); d.rectangle((84, 18, 92, 19), fill=(240, 248, 255))
    d.rectangle((4, 18, 8, 19), fill=(224, 48, 58))
    for cx in (22, 76): d.pieslice((cx - 10, 18, cx + 10, 38), 180, 360, fill=(14, 14, 20)); _wheel(d, cx, 27, 7, spin)
    return outline(img)


@lru_cache(None)
def rope():
    """Velvet rope (130x26) between two brass posts."""
    img = Image.new('RGBA', (130, 26), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    for x in (3, 124):
        d.rectangle((x, 4, x + 3, 25), fill=(214, 170, 60)); d.ellipse((x - 1, 0, x + 4, 5), fill=(240, 200, 90)); d.rectangle((x - 2, 23, x + 5, 25), fill=(180, 140, 40))
    pts = [(6 + i * 2, 6 + 7 * math.sin(math.pi * i / 59)) for i in range(60)]
    d.line(pts, fill=(170, 30, 50), width=3); d.line([(x, y - 1) for x, y in pts], fill=(220, 70, 90))
    return outline(img)


@lru_cache(None)
def v6(ph=0, hybrid=0.0):
    """V6 front-ish view (70x50): two banks of three in a V, turbo in the vee, MGU and battery when hybrid > 0."""
    img = Image.new('RGBA', (90, 54), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    cx, cy = 45, 44
    d.rounded_rectangle((25, 36, 65, 52), 4, fill=(110, 116, 128))
    for sg in (-1, 1):
        a = math.radians(sg * 45); ux, uy = math.sin(a), -math.cos(a); nx, ny = -uy, ux
        pts = [(cx + nx * 9, cy + ny * 9), (cx + ux * 34 + nx * 9, cy + uy * 34 + ny * 9), (cx + ux * 34 - nx * 9, cy + uy * 34 - ny * 9), (cx - nx * 9, cy - ny * 9)]
        d.polygon(pts, fill=(150, 156, 168)); d.line(pts[1:3], fill=(0, 160, 150), width=3)
        for k in range(3):
            r = 16 + 7 * k; px, py = cx + ux * r + nx * (k - 1) * 3, cy + uy * r + ny * (k - 1) * 3
            on = (k + (sg > 0) * 3 + ph) % 6 == 0
            d.ellipse((px - 2, py - 2, px + 2, py + 2), fill=(255, 230, 90) if on else (60, 64, 76))
    d.ellipse((40, 20, 50, 30), fill=(176, 182, 194)); d.ellipse((43, 23, 47, 27), fill=(60, 64, 76))     # turbo in the vee
    d.ellipse((cx - 5, cy - 5, cx + 5, cy + 5), fill=(70, 74, 86))
    if hybrid > 0:
        g = int(120 + 135 * hybrid)
        d.rounded_rectangle((70, 30, 88, 50), 3, fill=(60, 90, 160)); d.rectangle((74, 34, 84, 46), fill=(80, min(255, g), 255))     # MGU
        d.rectangle((0, 38, 20, 52), fill=(40, 44, 56)); d.rectangle((2, 40, 18, 50), fill=(60, 200, 90) if hybrid > 0.5 else (60, 120, 80))   # battery
        d.rectangle((6, 35, 9, 38), fill=(200, 204, 214)); d.rectangle((12, 35, 15, 38), fill=(200, 204, 214))
    return outline(img)


PCOL = [(232, 182, 140), (198, 140, 100), (150, 100, 70), (240, 206, 170)]
SHIRT = [(224, 48, 58), (61, 127, 214), (60, 200, 90), (255, 196, 40), (196, 202, 212), (150, 90, 200)]


@lru_cache(None)
def person(i, wave=0):
    """Tiny applicant (8x14) with skin/shirt variants; wave lifts a white form."""
    img = Image.new('RGBA', (10, 15), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rectangle((3, 0, 6, 1), fill=(40, 30, 26)); d.rectangle((3, 2, 6, 5), fill=PCOL[i % 4])
    d.rectangle((2, 6, 7, 10), fill=SHIRT[i % 6]); d.rectangle((3, 11, 4, 14), fill=(40, 42, 52)); d.rectangle((5, 11, 6, 14), fill=(40, 42, 52))
    if wave: d.line([(7, 7), (9, 3)], fill=SHIRT[i % 6]); d.rectangle((7, 0, 9, 2), fill=(250, 250, 250))
    return outline(img)


@lru_cache(None)
def key():
    img = Image.new('RGBA', (16, 8), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.ellipse((0, 0, 7, 7), fill=(255, 210, 63)); d.rectangle((3, 3, 4, 4), fill=(0, 0, 0, 0)); d.point((2, 1), fill=(255, 246, 200))
    d.rectangle((7, 3, 15, 4), fill=(255, 210, 63)); d.rectangle((12, 5, 13, 6), fill=(232, 170, 30)); d.rectangle((15, 5, 15, 6), fill=(232, 170, 30))
    return outline(img)


# ================================================================== shot 1: hook, the showroom
MORPH = 2.59
CX = 540
CAM1 = Camera(W, H, [(-1.0, (540, 980, 1.32)), (0.0, (540, 980, 1.32)), (0.8, (540, 960, 1.14), 'io'), (MORPH, (540, 960, 1.2), 'io'), (3.55, (540, 940, 1.24), 'io')],
              kicks=[(0.1, 0.1, CX, 1000), (1.19, 0.1, CX, 1000), (1.96, 0.12, 540, 600), (MORPH, 0.22, CX, 1000)], shakes=[(MORPH, 0.3, 12)])


def shot_showroom(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    fx.rays(fg, t, 0.0, CX, 300, (255, 240, 200), hold=True, r=900, n=8)
    ImageDraw.Draw(fg).ellipse((CX - 440, GROUND - 60, CX + 440, GROUND + 50), fill=(70, 72, 84, 255))          # turntable
    bob = 4 * math.sin(t * 3)
    if t < MORPH:
        blit(fg, up(racer(int(t * 40) % 360), 7), CX, GROUND - 10 + bob)
    else:
        k = popin(t, MORPH, 0.3)
        blit(fg, up(hyper(0), 7), CX, GROUND - 10 + bob, k, k)
        fx.poof(fg, t, MORPH, CX, GROUND - 150, seed=1, scale=1.6)
        fx.burst(fg, t, MORPH, CX, GROUND - 150, GLOW, n=18, seed=2)
    fx.contact_shadow(fg, CX, GROUND - 10, 780, s=9)
    blit(fg, up(rope(), 8), CX, GROUND + 160)
    fx.sparkles(fg, t, CX, GROUND - 200, 900, 300, n=8, seed=3)
    if t >= 1.19:
        k = popin(t, 1.19, 0.25) * popout(t, 2.5)
        blit(fg, fx.big('tag', 'ROAD CAR?', '#fff6e0', '#1a1a2e', s=8), 780, 1350 - 520, k, k, 5, anchor='center')
    GAR.reflect(img, fg)
    return finish(img, fg, CAM1, t)


def overlay(cv, t):
    title(cv, t, 0.05, S1 - 0.1, '1,000+ applied', WHITE, 480, 116, -3)
    title(cv, t, 0.3, S1 - 0.1, 'for one car', YEL, 610, 120, 2)
    to = WARP(t)
    if S2 <= t < BODY_END:
        title(cv, to, 1.96, 3.45, 'Formula One', YEL, 480, 130, -3)
        title(cv, to, 2.2, 3.45, 'engineering', YEL, 610, 120, 2)
        title(cv, to, 6.41, 8.3, '1,000 horsepower', RED, 480, 116, -2)
    title(cv, t, BODY_END + 0.05, END_T - 0.1, 'Would you', WHITE, 480, 120, -2)
    title(cv, t, BODY_END + 0.25, END_T - 0.1, 'have applied?', YEL, 610, 120, 2)


# ================================================================== shot 2: the 1.6 L V6 hybrid
EXX, EXY = 560, 1180
P2 = Presenter([
    (3.5, dict(path=Track([(3.5, (-200, 400)), (3.9, (150, GROUND), 'oc')]), size=7, legs='auto', arms='fly', expr='talk', face=1, ground=None)),
    (3.9, dict(ground=GROUND, squash=True, arms='point', point=(EXX, 900), look=(EXX, 900), expr='smile', face=None)),
    (6.41, dict(arms='cheer', point=None, expr='wow', squash=True)),
], words=WORDS, base_size=7)
CAM2 = Camera(W, H, [(3.55, (560, 900, 1.12)), (3.78, (560, 860, 1.24), 'io'), (5.31, (600, 900, 1.14), 'io'), (6.41, (560, 820, 1.22), 'io'), (8.4, (560, 840, 1.26))],
              kicks=[(3.78, 0.14, EXX, 900), (4.83, 0.12, EXX, 760), (5.31, 0.16, 800, 1000), (6.41, 0.2, 560, 620), (7.0, 0.1, 560, 620)], shakes=[(5.31, 0.3, 10), (6.41, 0.4, 8)])


def shot_engine(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    u = oc(prog(t, 3.6, 0.4)); hyb = oc(prog(t, 5.31, 0.3))
    blit(fg, up(v6(int(t * 14) % 6 if t > 4.83 else -1, hyb), 9), EXX + (2 * math.sin(t * 70) if t > 4.83 else 0), EXY - 600 * (1 - u))
    if t >= 3.78:
        k = popin(t, 3.78, 0.25) * popout(t, 6.3)
        blit(fg, fx.big('badge', '1.6 L', '#ffffff', '#1a1a2e', '#d6d9e2', s=10), 300, 700, k, k, -5, anchor='center')
    dg.label(fg, t, 4.83, 'V6', (EXX, 900), (800, 680), '#ffd23f', '#1a1a2e', '#e8b923', s=10, t1=6.3)
    if t >= 5.31:
        for x in (EXX + 360, EXX - 360):
            fx.burst(fg, t, 5.31, x, EXY - 100, (120, 200, 255), n=10, r0=60, r1=220, seed=int(x))
        k = popin(t, 5.31, 0.25) * popout(t, 6.3)
        blit(fg, fx.big('tag', 'HYBRID', '#7fd4ff', '#1a1a2e', s=9), 820, 880, k, k, 4, anchor='center')
        if int(t * 10) % 2: fx.sparkles(fg, t, EXX, EXY - 150, 800, 200, n=5, seed=20)
    if t >= 6.41:
        v = int(1000 * oc(prog(t, 6.41, 0.6)))
        k = popin(t, 6.41, 0.25)
        blit(fg, fx.big('badge', f'{v:,}+ HP' if v >= 1000 else f'{v} HP', '#e0303a', '#ffffff', '#b8222c', s=12), 560, 620, k, k, 2 * math.sin(t * 5), anchor='center')
        fx.burst(fg, t, 6.41, 560, 620, RED, n=16, seed=21)
    if t >= 7.0: fx.confetti(fg, t, 7.0, 560, 560, n=26, seed=22)
    P2.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM2, t)


# ================================================================== shots 3 + 4: applicants -> keys
COLS, ROWS = 14, 9
SPOTS = [(c, r) for r in range(ROWS) for c in range(COLS)]
KEEP = set(fx.rng(5).choice(len(SPOTS), 36, replace=False).tolist())   # ~275/1000 of the crowd survives as keys
def spot_xy(c, r): return 120 + c * 64 + (r % 2) * 30, 560 + r * 84


def crowd(fg, t, gone_t=None):
    for i, (c, r) in enumerate(SPOTS):
        t0 = 8.45 + (i % 37) * 0.012 + r * 0.04
        if t < t0: continue
        x, y = spot_xy(c, r); k = popin(t, t0, 0.2)
        if gone_t is not None and t >= gone_t + (i % 23) * 0.025:
            if i in KEEP:                              # survivors fly into a neat block of keys
                j = sorted(KEEP).index(i); kx, ky = 200 + (j % 6) * 136, 730 + (j // 6) * 80
                u = oc(prog(t, gone_t + 0.15 + j * 0.012, 0.45))
                blit(fg, up(key(), 7), lerp(x, kx, u), lerp(y + 30, ky, u), 1, 1, 6 * math.sin(t * 4 + i) * (1 - u) + 3 * math.sin(t * 3 + j), anchor='center')
            elif t < gone_t + 1.0 and i % 3 == 0: fx.poof(fg, t, gone_t + (i % 23) * 0.025, x, y, seed=i, scale=0.3)
            continue
        wave = 1 if t > 9.74 and int(t * 6 + i) % 2 else 0
        blit(fg, up(person(i, wave), 5), x, y + 40 + 4 * math.sin(t * 5 + i), k, k)


CAM3 = Camera(W, H, [(8.4, (540, 960, 1.3)), (8.94, (540, 940, 1.05), 'oc'), (11.1, (540, 940, 1.1), 'io')],
              kicks=[(8.57, 0.1, 540, 900), (9.44, 0.08, 540, 900), (9.74, 0.12, 540, 900), (10.3, 0.1, 540, 500)])


def shot_applied(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    crowd(fg, t)
    if t >= 10.0:                                  # after the series tag has shrunk away
        k = popin(t, 10.0, 0.25); v = int(1000 * oc(prog(t, 10.0, 0.6)))
        blit(fg, fx.big('badge', f'{v:,}+ APPLIED' if v >= 1000 else f'{v} APPLIED', '#ffffff', '#1a1a2e', '#d6d9e2', s=9), 520, 300, k, k, -2 + 2 * math.sin(t * 4), anchor='center')
        fx.sparkles(fg, t, 540, 300, 800, 200, n=6, seed=30)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM3, t)


GONE = 11.18
P4 = Presenter([
    (12.4, dict(path=Track([(12.4, (1300, 300)), (12.8, (880, GROUND + 160), 'oc')]), size=7, legs='auto', arms='fly', expr='grin', face=-1, ground=None)),
    (12.8, dict(ground=GROUND + 160, squash=True, arms='cheer', expr='wow', face=None, look_camera=True)),
], words=WORDS, base_size=7)
CAM4 = Camera(W, H, [(11.1, (540, 940, 1.1)), (11.44, (540, 900, 1.16), 'io'), (12.44, (540, 860, 1.24), 'io'), (13.95, (560, 880, 1.2), 'io')],
              kicks=[(GONE, 0.14, 540, 900), (11.44, 0.2, 540, 430), (12.44, 0.12, 540, 430), (13.01, 0.14, 880, 1000)], shakes=[(GONE, 0.3, 10)])


def shot_keys(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    crowd(fg, t, GONE)
    v = int(lerp(1000, 275, oc(prog(t, GONE, 0.8))))
    k = 1 + 0.15 * math.exp(-max(0, t - 11.44) * 8) * (t >= 11.44)
    green = v == 275
    blit(fg, fx.big('badge', f'{v:,}', '#7fe3a0' if green else '#ffffff', '#1a1a2e', '#3cc85a' if green else '#d6d9e2', s=12), 540, 610, k, k, -2 + 2 * math.sin(t * 4), anchor='center')
    if t >= 11.98:
        fx.burst(fg, t, 11.98, 540, 610, (60, 200, 90), n=16, seed=40); fx.gsparkles(fg, t, 540, 900, 900, 700, n=10, seed=41)
    if t >= 12.44:
        kk = popin(t, 12.44, 0.25)
        blit(fg, fx.big('tag', 'KEYS', '#fff6e0', '#1a1a2e', s=8), 860, 600, kk, kk, 6, anchor='center')
    if t >= 13.01: fx.confetti(fg, t, 13.01, 540, 500, n=36, seed=42)
    P4.draw(fg, t)
    return finish(img, fg, CAM4, t)


# ================================================================== new read, reordered: applicants, 275 keys, showroom, engine, question
def section(n0, n1, o0, o1):
    """(new, old) anchors for one stretch of the new read that replays the old span o0..o1, matched word by word."""
    nw = [w for w in NEW if n0 <= w['s'] < n1]; ow = [w for w in WORDS if o0 <= w['s'] < o1]
    return [(n0, o0)] + [p for p in kit.word_pairs(nw, ow)] + [(n1 - 0.01, o1)]
SECS = [(0.0, S1, 8.45, 11.05), (S1, S2, 11.1, 13.9), (S2, S3, -0.2, 3.5), (S3, BODY_END, 3.6, 8.38), (BODY_END, END_T + 0.2, 9.6, 11.0)]
ANCH = sum((section(*sc) for sc in SECS), [])
WARP = kit.warp(ANCH)
shot_teaser, TEASE_CUES = kit.teaser(END_T, NEW)

# ================================================================== shots + transitions
SHOTS = [(-1.0, kit.retime(shot_applied, WARP)), (S1, kit.retime(shot_keys, WARP)), (S2, kit.retime(shot_showroom, WARP)),
         (S3, kit.retime(shot_engine, WARP)), (BODY_END, kit.retime(shot_applied, WARP)), (END_T, shot_teaser)]
TRANS = {2: (S2, S2 + 0.2, 'whip', dict(dx=1)), 3: (S3, S3 + 0.2, 'whip', dict(dx=0, dy=1)), 4: (BODY_END, BODY_END + 0.2, 'iris', (560, 620)),
         5: (END_T, END_T + 0.2, 'whip', dict(dx=1))}
KEYCOL = {'thousand': YEL, 'applied': YEL, '275': GRN, 'chance': GRN, 'mercedes\'': YEL, 'project': YEL, 'formula': YEL, '1.6-litre': YEL,
          'hybrid,': GRN, '1,000': RED, 'applied?': YEL}
CUES = [
    (0.0, 'whoosh', 0.4), (0.05, 'pop', 0.5), (0.1, 'ding', 0.5), (0.3, 'pop', 0.5), (0.6, 'sparkle', 0.5), (1.19, 'pop', 0.6),
    (1.96, 'vroom', 0.6), (MORPH - 0.05, 'whoosh', 0.6), (MORPH, 'poof', 0.8), (MORPH + 0.02, 'sparkle', 0.8), (2.85, 'pop', 0.5),
    (3.6, 'slide_down', 0.6), (3.95, 'thump', 0.7), (3.78, 'pop', 0.6), (4.83, 'vroom', 0.6), (4.85, 'pop', 0.6), (5.31, 'click', 0.7),
    (5.33, 'sparkle', 0.7), (6.41, 'boom', 0.5), (6.43, 'stamp', 0.7), (7.0, 'confetti', 0.7), (7.02, 'ding', 0.6),
    (8.45, 'pop', 0.4), (8.6, 'pop', 0.4), (8.75, 'pop', 0.4), (8.94, 'whoosh', 0.5), (9.74, 'pop', 0.5), (10.3, 'ding', 0.5),
    (GONE, 'poof', 0.8), (GONE + 0.3, 'coin', 0.5), (GONE + 0.5, 'coin', 0.5), (11.44, 'stamp', 0.7), (11.98, 'ding', 0.8),
    (12.44, 'pop', 0.6), (12.8, 'thump', 0.5), (13.01, 'confetti', 0.8),
]
CUES = [(0.0, 'whoosh', 0.4), (0.05, 'pop', 0.5)] + kit.warp_cues(CUES, ANCH, END_T) + TEASE_CUES

kit.setup(HERE, NEW, DUR, END_T, SHOTS, TRANS, CUES, KEYCOL, overlay=overlay, bar_car='silver', gauge=True, loud=True, crisp=True,
          end=('car stuff, explained', 'tell me in the comments'))

if __name__ == '__main__':
    kit.main()
