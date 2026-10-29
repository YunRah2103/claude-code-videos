"""Renders 'The Trabant': no steel, a Duroplast body, a tiny two-stroke and millions built.

Template: videos/the-land-rover-from-the-sand (ac-idle shot structure on shared/episode.py). Word times come from
align.py -> words.json (the voiceover is the timing spine). Speech runs 0.2-17.1 s; the read has no 'Follow' line,
so the end card shows it. The cotton-waste recipe is hedged (REPORTEDLY). No recycling 'first' and no waiting-list
figure (not independently verified). Cars are generic pixel redraws with no badges or lettering.
Shots:
  1 cut      0.00  shears cut a steel sheet; it falls apart and a wobbly plastic panel pops in; 'No steel.'
  2 short    2.40  an empty steel rack with SHORT SUPPLY; a body panel rolls out of the press: DUROPLAST
  3 recipe   7.20  cotton bales and resin barrels roll into the factory hopper; REPORTEDLY; panel out
  4 engine   9.80  a tiny two-stroke: piston pumping, blue exhaust puffs; 500CC and 18 HP badges; photo
  5 millions 13.90 a line of small saloons stretches to the horizon; MILLIONS BUILT; SYMBOL OF A COUNTRY
  6 teaser   16.75 shared NEXT EPISODE ending
"""
import math, os, sys
from functools import lru_cache
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared'))
import episode as kit
from episode import W, H, S, GROUND, GAR, GLOW, RED, YEL, GRN, WHITE, layer, finish, photo, title
from pixanim.motion import Track, prog, lerp, clamp, oc, ic, io, wob
from pixanim.camera import Camera
from pixanim.presenter import Presenter
from pixanim import fx, diagram as dg
from pixanim.fx import blit, popin, popout
from pixanim.grid import up, outline, Grid, text_width

WORDS = kit.load_words(HERE)
DUR, END_T = 18.7, 17.15


# ------------------------------------------------------------------ episode sprites
def _wheel(d, cx, cy, r, spin, rim):
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(26, 27, 32))
    d.ellipse((cx - r + 1.5, cy - r + 1.5, cx + r - 1.5, cy + r - 1.5), fill=(40, 42, 48))
    rr = r * 0.62
    d.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), fill=rim)
    for k in range(4):
        a = math.radians(k * 90 + spin)
        d.point((cx + rr * 0.6 * math.cos(a), cy + rr * 0.6 * math.sin(a)), fill=tuple(int(c * 0.6) for c in rim))
    d.ellipse((cx - 1.2, cy - 1.2, cx + 1.2, cy + 1.2), fill=(240, 240, 244))


TCOL = {'blue': (140, 180, 210), 'cream': (232, 220, 180), 'mint': (160, 210, 180), 'beige': (204, 190, 160), 'red': (200, 90, 80)}


@lru_cache(None)
def trabi(col='blue', spin=0):
    """Small two-door 1960s saloon (84x36 grid), nose right: upright glasshouse with thin pillars, white roof,
    short flat bonnet, round lamps, chrome bumpers, skinny tyres with painted hubcaps. No emblem."""
    body = TCOL[col]; shade = tuple(int(c * 0.78) for c in body); hi = tuple(min(255, c + 30) for c in body); deep = tuple(int(c * 0.55) for c in body)
    img = Image.new('RGBA', (84, 36), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    pts = [(3, 14), (14, 12), (22, 3), (52, 3), (60, 12), (78, 14), (81, 17), (81, 26), (3, 26)]
    d.polygon(pts, fill=body); d.line(pts[:-2], fill=hi)
    d.polygon([(22, 3), (52, 3), (53, 4), (21, 4)], fill=(246, 246, 240))                         # white roof
    d.rectangle((3, 21, 81, 23), fill=shade); d.rectangle((3, 24, 81, 26), fill=deep)
    d.polygon([(17, 12), (24, 5), (36, 5), (36, 12)], fill=(130, 162, 190)); d.polygon([(39, 12), (39, 5), (50, 5), (57, 12)], fill=(130, 162, 190))
    d.line([(25, 6), (35, 6)], fill=(200, 226, 244)); d.line([(37, 4), (37, 21)], fill=deep); d.line([(58, 13), (58, 21)], fill=deep)
    d.rectangle((44, 15, 46, 15), fill=(220, 224, 232))
    d.line([(3, 17), (81, 17)], fill=hi)
    d.ellipse((76, 14, 81, 19), fill=(250, 248, 220)); d.point((77, 15), fill=(255, 255, 255))
    d.rectangle((1, 22, 6, 24), fill=(214, 218, 226)); d.rectangle((78, 22, 83, 24), fill=(214, 218, 226))   # chrome bumpers
    d.rectangle((3, 15, 5, 18), fill=(200, 50, 50))
    for cx in (17, 67): d.pieslice((cx - 9, 17, cx + 9, 35), 180, 360, fill=(14, 14, 20))
    for cx in (17, 67): _wheel(d, cx, 28, 7, spin, (236, 236, 230))
    return outline(img)


def ts(col, dist=0): return trabi(col, int(dist * 0.6) % 360 // 15 * 15)


@lru_cache(None)
def steel(part=0):
    """Steel sheet (44x30) with a cold sheen; part -1/1 returns the left/right half after the cut."""
    img = Image.new('RGBA', (44, 30), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rectangle((0, 0, 43, 29), fill=(150, 158, 172)); d.line([(0, 0), (43, 0)], fill=(214, 222, 234))
    for x in range(-30, 44, 9): d.line([(x, 29), (x + 29, 0)], fill=(176, 184, 198))
    for x in range(2, 44, 6): d.point((x, 2), fill=(110, 116, 128)); d.point((x, 27), fill=(110, 116, 128))
    img = outline(img)
    if part: img = img.crop((0, 0, 22, 30)) if part < 0 else img.crop((22, 0, 44, 30))
    return img


@lru_cache(None)
def panel(wav=0):
    """Duroplast door panel (40x30): beige-green, fibrous speckle, a little bendy (wav shears the rows)."""
    img = Image.new('RGBA', (48, 32), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    r = fx.rng(5)
    for y in range(30):
        off = round(2 * math.sin(y * 0.3 + wav * 0.8))
        d.line([(4 + off, y + 1), (43 + off, y + 1)], fill=(200, 196, 160))
    for _ in range(80):
        x, y = int(r.uniform(5, 42)), int(r.uniform(2, 30)); off = round(2 * math.sin(y * 0.3 + wav * 0.8))
        d.point((x + off, y), fill=(176, 170, 132) if _ % 2 else (222, 218, 190))
    d.rectangle((30 + round(2 * math.sin(4.5 + wav * 0.8)), 14, 35 + round(2 * math.sin(4.5 + wav * 0.8)), 15), fill=(214, 218, 226))   # handle
    return outline(img)


@lru_cache(None)
def shears(open_=1.0):
    img = Image.new('RGBA', (40, 24), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    a = 14 * open_
    for sg in (-1, 1):
        ang = math.radians(sg * a)
        x1, y1 = 20 + 19 * math.cos(ang), 12 + 19 * math.sin(ang)
        d.line([(20, 12), (x1, y1)], fill=(214, 220, 230), width=3)
        hx, hy = 20 - 12 * math.cos(ang), 12 - 12 * math.sin(ang)
        d.ellipse((hx - 5, hy - 4, hx + 4, hy + 4), outline=(214, 48, 58), width=2)
    d.ellipse((18, 10, 22, 14), fill=(90, 94, 106))
    return outline(img)


@lru_cache(None)
def bale(rot=0):
    img = Image.new('RGBA', (30, 24), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, 29, 23), 4, fill=(244, 244, 236))
    r = fx.rng(7)
    for _ in range(40): d.point((int(r.uniform(2, 28)), int(r.uniform(2, 22))), fill=(220, 220, 210))
    for x in (8, 21): d.rectangle((x, 0, x + 1, 23), fill=(150, 112, 70))
    img = outline(img)
    return img.rotate(rot, Image.NEAREST, expand=True)


@lru_cache(None)
def barrel(rot=0):
    img = Image.new('RGBA', (22, 28), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, 21, 27), 3, fill=(196, 120, 40)); d.line([(4, 1), (4, 26)], fill=(236, 170, 90))
    for y in (6, 20): d.rectangle((0, y, 21, y + 1), fill=(120, 70, 20))
    d.rectangle((6, 10, 15, 16), fill=(250, 220, 140))
    img = outline(img)
    return img.rotate(rot, Image.NEAREST, expand=True)


@lru_cache(None)
def press(down=0.0):
    """Hydraulic press (60x70): frame, ram that moves down by `down` (0..1), die bed."""
    img = Image.new('RGBA', (60, 70), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rectangle((0, 0, 59, 8), fill=(60, 120, 90)); d.rectangle((0, 0, 6, 69), fill=(60, 120, 90)); d.rectangle((53, 0, 59, 69), fill=(60, 120, 90))
    d.line([(0, 0), (59, 0)], fill=(110, 170, 130))
    y = 9 + int(26 * down)
    d.rectangle((26, 8, 33, y), fill=(190, 196, 208)); d.rectangle((10, y, 49, y + 8), fill=(90, 94, 106))
    d.rectangle((10, 56, 49, 62), fill=(90, 94, 106)); d.rectangle((0, 62, 59, 69), fill=(50, 90, 70))
    for x in range(10, 50, 6): d.line([(x, 62), (x + 3, 69)], fill=(255, 200, 40))
    return outline(img)


@lru_cache(None)
def two_stroke(ph=0):
    """Tiny two-cylinder two-stroke (60x44): finned air-cooled barrels, a window showing a piston at phase ph
    (0..7), cooling fan housing, carburettor and a downpipe to the exhaust."""
    img = Image.new('RGBA', (64, 46), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rectangle((10, 26, 52, 42), fill=(120, 126, 138)); d.line([(10, 26), (52, 26)], fill=(176, 182, 194))  # crankcase
    for i, cx in enumerate((22, 40)):                                                     # finned barrels
        d.rectangle((cx - 7, 4, cx + 7, 26), fill=(150, 156, 168))
        for y in range(5, 26, 3): d.line([(cx - 9, y), (cx + 9, y)], fill=(176, 182, 194))
        py = 12 + round(5 * math.sin((ph + i * 4) * math.pi / 4))
        d.rectangle((cx - 4, 8, cx + 4, 22), fill=(40, 42, 52))
        d.rectangle((cx - 4, py, cx + 4, py + 5), fill=(214, 220, 230)); d.line([(cx, py + 5), (cx, 22)], fill=(170, 176, 188))
        d.ellipse((cx - 3, 1, cx + 3, 5), fill=(240, 200, 60))                             # plug
    d.rounded_rectangle((0, 14, 12, 40), 4, fill=(60, 120, 90)); d.ellipse((2, 20, 10, 34), fill=(40, 80, 60))   # fan housing
    for k in range(4):
        a = math.radians(k * 45 + ph * 30); d.line([(6, 27), (6 + 4 * math.cos(a), 27 + 4 * math.sin(a))], fill=(140, 200, 160))
    d.rectangle((52, 30, 58, 34), fill=(90, 94, 106)); d.rectangle((56, 34, 63, 38), fill=(70, 72, 82))        # exhaust
    d.rectangle((27, 0, 35, 4), fill=(200, 160, 60))                                        # carb
    return outline(img)


# ------------------------------------------------------------------ factory world (9 px grid)
@lru_cache(None)
def factory():
    img = Image.new('RGB', (120, 214)); d = ImageDraw.Draw(img)
    d.rectangle((0, 0, 119, 131), fill=(70, 74, 70))
    for x in range(0, 120, 30):                                                        # saw-tooth roof lights
        d.polygon([(x, 18), (x + 20, 4), (x + 22, 4), (x + 22, 18)], fill=(170, 186, 170))
    d.rectangle((0, 18, 119, 21), fill=(50, 52, 50))
    for x in range(0, 120, 16): d.rectangle((x, 22, x + 2, 131), fill=(84, 88, 84))
    d.rectangle((0, 60, 119, 62), fill=(200, 160, 60))
    for x in range(0, 120, 8):
        for y in range(70, 128, 8): d.point((x + 3, y), fill=(80, 84, 80))
    d.rectangle((0, 132, 119, 213), fill=(96, 92, 84))
    for x in range(0, 120, 12): d.line([(x, 132), (x - 10, 213)], fill=(88, 84, 76))
    return up(img, S).crop((0, 0, W, H)).convert('RGBA')


# ================================================================== shot 1: hook, no steel
CUT_T = 0.45
PANEL_T = 1.0
CAM1 = Camera(W, H, [(-1.0, (540, 980, 1.3)), (0.0, (540, 980, 1.3)), (0.6, (540, 980, 1.1), 'io'), (1.98, (540, 960, 1.16), 'io'), (2.4, (540, 960, 1.2))],
              kicks=[(CUT_T, 0.16, 540, 1000), (PANEL_T, 0.14, 540, 1000), (1.98, 0.1, 760, 760)], shakes=[(CUT_T, 0.25, 12)])


def shot_cut(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    cx, cy = 540, 1040
    if t < CUT_T:
        blit(fg, up(steel(), 14), cx, cy, 1, 1, 0, anchor='center')
        so = clamp(1 - (t + 0.6) / (CUT_T + 0.6))
        blit(fg, up(shears(so), 12), cx, lerp(700, cy - 60, prog(t, -0.5, CUT_T + 0.5)), 1, 1, -90, anchor='center')
    else:
        u = ic(prog(t, CUT_T, 0.55))
        for part, sg in ((-1, -1), (1, 1)):
            if u < 1: blit(fg, up(steel(part), 14), cx + sg * (160 + 260 * u), cy + 700 * u * u, 1, 1, sg * 40 * u, anchor='center')
        fx.burst(fg, t, CUT_T, cx, cy, GLOW, n=14, r0=60, r1=420, seed=1)
        fx.stamp_at(fg, t, CUT_T + 0.05, 'NO STEEL', cx, 1260, rot=-8, s=9) if t < PANEL_T else None
    if t >= PANEL_T:
        k = popin(t, PANEL_T, 0.3)
        blit(fg, up(panel(int(t * 10) % 16), 13), cx, cy, k, k * (1 + 0.04 * math.sin(t * 16)), 3 * math.sin(t * 7), anchor='center')
        fx.ring(fg, t, PANEL_T, cx, cy, (200, 196, 160), life=0.3, r1=460)
        fx.sparkles(fg, t, cx, cy, 700, 500, n=7, seed=2)
    if t >= 1.62:
        k = popin(t, 1.62, 0.25)
        blit(fg, fx.big('badge', 'EAST GERMANY', '#ffffff', '#1a1a2e', '#d6d9e2', s=7), 760, 760, k, k, 4, anchor='center')
    GAR.reflect(img, fg)
    return finish(img, fg, CAM1, t)


def overlay(cv, t):
    title(cv, t, 0.05, 2.3, 'No', RED, 430, 170, -3)
    title(cv, t, 0.3, 2.3, 'steel.', WHITE, 590, 130, 3)


# ================================================================== shot 2: short supply, Duroplast
RACK_X, PRESS_X = 270, 790
def ingots(t): return 5 if t < 2.7 else max(0, 5 - int(5 * prog(t, 2.7, 0.75)))
def press_down(t):
    for t0 in (4.6, 5.9):
        if t0 <= t < t0 + 0.5: return math.sin(math.pi * prog(t, t0, 0.5))
    return 0.0
P2 = Presenter([
    (2.35, dict(path=Track([(2.35, (1300, 300)), (2.75, (960, GROUND), 'oc')]), size=6, legs='auto', arms='fly', expr='talk', face=-1, ground=None)),
    (2.75, dict(ground=GROUND, squash=True, arms='point', point=(RACK_X, GROUND - 200), look=(RACK_X, GROUND - 200), expr='sad', face=None)),
    (4.35, dict(arms='point', point=(PRESS_X, GROUND - 260), look=(PRESS_X, GROUND - 260), expr='smile')),
    (6.53, dict(arms='cheer', point=None, expr='wow', squash=True)),
], words=WORDS, base_size=6)
CAM2 = Camera(W, H, [(2.4, (540, 920, 1.14)), (3.22, (360, 900, 1.26), 'io'), (4.35, (600, 900, 1.16), 'io'), (6.53, (640, 900, 1.24), 'io'), (7.2, (640, 900, 1.26))],
              kicks=[(2.67, 0.1, RACK_X, 900), (3.45, 0.14, RACK_X, 800), (4.78, 0.12, PRESS_X, 1000), (6.1, 0.12, PRESS_X, 1000), (6.53, 0.14, PRESS_X, 600)],
              shakes=[(4.85, 0.2, 10), (6.15, 0.2, 10)])


def shot_short(t):
    img = factory().copy(); fg = layer()
    d = ImageDraw.Draw(fg)
    d.rectangle((RACK_X - 170, GROUND - 330, RACK_X + 170, GROUND - 320), fill=(90, 94, 106, 255))        # steel rack
    d.rectangle((RACK_X - 170, GROUND - 170, RACK_X + 170, GROUND - 160), fill=(90, 94, 106, 255))
    for x in (RACK_X - 170, RACK_X + 160): d.rectangle((x, GROUND - 330, x + 10, GROUND), fill=(90, 94, 106, 255))
    blit(fg, up(press(press_down(t)), 8), PRESS_X, GROUND)
    n = ingots(t)
    for i in range(5):
        if i < n: blit(fg, up(steel(), 3), RACK_X - 120 + i * 60, GROUND - 170, 1, 1, 0)
        elif t < 3.6: fx.poof(fg, t, 2.7 + (4 - i) * 0.15, RACK_X - 120 + i * 60, GROUND - 220, seed=10 + i, scale=0.4)
    if t >= 3.22:
        k = popin(t, 3.22, 0.25) * popout(t, 4.3)
        blit(fg, fx.big('tag', 'SHORT SUPPLY', '#fff6e0', '#d6303a', s=7), RACK_X + 60, 700, k, k, -5, anchor='center')
        fx.burst(fg, t, 3.22, RACK_X + 60, 700, RED, n=10, seed=11)
    for t0 in (4.6, 5.9):                                                               # panels come out of the press
        if t >= t0 + 0.3:
            u = oc(prog(t, t0 + 0.3, 0.5))
            blit(fg, up(panel(int(t * 8) % 16), 5), lerp(PRESS_X, PRESS_X - 330 + (t0 > 5) * 60, u), GROUND - 80 - 20 * (t0 > 5), 1, 1, 0)
            fx.dust(fg, t, t0 + 0.25, PRESS_X, GROUND - 90, n=8, seed=int(t0 * 10), col=(222, 218, 190))
    if t >= 5.14:
        k = popin(t, 5.14, 0.25) * popout(t, 6.4)
        blit(fg, fx.big('tag', 'PLASTIC-LIKE', '#fff6e0', '#1a1a2e', s=7), PRESS_X - 40, 470, k, k, 3, anchor='center')
    if t >= 6.53:
        k = popin(t, 6.53, 0.25)
        blit(fg, fx.big('badge', 'DUROPLAST', '#7fe3a0', '#1a1a2e', '#3cc85a', s=10), PRESS_X - 60, 520, k, k, -3 + 2 * math.sin(t * 5), anchor='center')
        fx.burst(fg, t, 6.53, PRESS_X - 60, 520, (60, 200, 90), n=14, seed=12); fx.sparkles(fg, t, PRESS_X, 600, 500, 300, n=6, seed=13)
    P2.draw(fg, t)
    photo(fg, t, 5.3, 6.1, 'duroplast', 420, 760, 560, 400, -3, 'DUROPLAST PRODUCTION LINE', pix=4)
    return finish(img, fg, CAM2, t, rim=False)


# ================================================================== shot 3: cotton waste and resin
HOP_X = 760
ITEMS = [(7.6, 'bale'), (7.85, 'barrel'), (8.3, 'bale'), (8.6, 'bale'), (9.0, 'barrel'), (9.2, 'barrel')]
CAM3 = Camera(W, H, [(7.2, (540, 900, 1.14)), (8.3, (480, 960, 1.2), 'io'), (9.2, (600, 940, 1.18), 'io'), (9.8, (600, 940, 1.2))],
              kicks=[(7.52, 0.1, 540, 480), (8.3, 0.12, 300, 1000), (9.2, 0.12, 640, 1000)])


def shot_recipe(t):
    img = factory().copy(); fg = layer()
    d = ImageDraw.Draw(fg)
    d.polygon([(HOP_X - 170, GROUND - 420), (HOP_X + 170, GROUND - 420), (HOP_X + 60, GROUND - 230), (HOP_X - 60, GROUND - 230)], fill=(60, 120, 90, 255))   # hopper
    d.line([(HOP_X - 170, GROUND - 420), (HOP_X + 170, GROUND - 420)], fill=(110, 170, 130, 255), width=9)
    d.rectangle((HOP_X - 60, GROUND - 230, HOP_X + 60, GROUND), fill=(50, 90, 70, 255))
    d.rectangle((0, GROUND - 20, HOP_X - 60, GROUND - 6), fill=(40, 42, 50, 255))          # conveyor
    for x in range(0, HOP_X - 60, 36): d.rectangle((x + int(t * 200) % 36, GROUND - 18, x + 8 + int(t * 200) % 36, GROUND - 8), fill=(90, 94, 106, 255))
    for t0, kind in ITEMS:                                                               # roll along, then hop into the hopper
        if t < t0: continue
        u = prog(t, t0, 0.8)
        if u >= 1: continue
        x = lerp(-120, HOP_X, min(1, u / 0.75)); jump = 0 if u < 0.75 else 420 * math.sin(math.pi * (u - 0.75) / 0.25 * 0.5)
        y = GROUND - 20 - jump + (0 if u < 0.95 else 200 * (u - 0.95) / 0.05)
        spr = bale(int(x) % 360 // 30 * 30 if kind == 'bale' else 0) if kind == 'bale' else barrel(-int(x * 0.5) % 360 // 30 * 30)
        blit(fg, up(spr, 7), x, y)
    for t0, _ in ITEMS: fx.dust(fg, t, t0 + 0.8, HOP_X, GROUND - 420, n=5, seed=int(t0 * 10), col=(244, 244, 236))
    if t >= 9.3:                                                                         # a finished panel slides out below
        u = oc(prog(t, 9.3, 0.4)); blit(fg, up(panel(int(t * 8) % 16), 6), lerp(HOP_X, HOP_X + 200, u), GROUND, 1, 1, 0)
        fx.sparkles(fg, t, HOP_X + 200, GROUND - 100, 300, 200, n=5, seed=20)
    if t >= 7.52:
        k = popin(t, 7.52, 0.25)
        blit(fg, fx.big('tag', 'REPORTEDLY', '#fff6e0', '#e8a000', s=8), 430, 470, k, k, -4 + 2 * math.sin(t * 5), anchor='center')
    dg.label(fg, t, 8.3, 'COTTON WASTE', (200, GROUND - 120), (300, 640), '#ffffff', '#1a1a2e', '#d6d9e2', s=7)
    dg.label(fg, t, 9.2, 'RESIN', (HOP_X - 160, GROUND - 120), (800, 600), '#ffd23f', '#1a1a2e', '#e8b923', s=7)
    return finish(img, fg, CAM3, t, rim=False)


# ================================================================== shot 4: the tiny two-stroke
EX, EY = 540, 1000
def ph4(t): return int(t * 24) % 8
P4 = Presenter([
    (9.75, dict(path=Track([(9.75, (-200, 400)), (10.15, (150, GROUND), 'oc')]), size=7, legs='auto', arms='fly', expr='talk', face=1, ground=None)),
    (10.15, dict(ground=GROUND, squash=True, arms='point', point=(EX, EY - 100), look=(EX, EY - 100), expr='smile', face=None)),
    (10.69, dict(arms=('aim', 60), expr='smirk')),
    (13.11, dict(arms='thumb', point=None, look=None, look_camera=True, expr='grin', squash=True)),
], words=WORDS, base_size=7)
CAM4 = Camera(W, H, [(9.8, (560, 900, 1.12)), (10.69, (560, 960, 1.3), 'io'), (11.09, (560, 960, 1.34)), (12.01, (600, 900, 1.16), 'io'), (13.9, (600, 900, 1.2))],
              kicks=[(10.17, 0.08, EX, EY), (10.69, 0.1, EX, EY), (11.09, 0.14, EX, EY - 100), (12.01, 0.12, 760, 560), (13.11, 0.16, 360, 520)])


def shot_engine(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    sc = 0.6 + 0.4 * oc(prog(t, 9.9, 0.4)) - 0.15 * oc(prog(t, 10.69, 0.3)) + 0.15 * oc(prog(t, 12.0, 0.4))
    sh = 3 * math.sin(t * 60)
    blit(fg, up(two_stroke(ph4(t)), 10), EX + sh, EY + 160, sc, sc, 0)
    for k in range(12):                                                                 # blue two-stroke puffs
        tk = 10.2 + k * 0.3
        fx.puff(fg, t, tk, EX + 300 * sc, EY + 150, seed=30 + k, life=0.9, size=0.9, drift=(260, -200), col=(140, 160, 200))
    fx.contact_shadow(fg, EX, EY + 160, 600 * sc, s=S, alpha=120)
    if t >= 10.69:
        k = popin(t, 10.69, 0.25) * popout(t, 11.9)
        blit(fg, fx.big('tag', 'TINY', '#fff6e0', '#1a1a2e', s=8), 330, 640, k, k, -6, anchor='center')
    dg.label(fg, t, 11.09, 'TWO-STROKE', (EX, EY - 160), (580, 600), '#ffffff', '#1a1a2e', '#d6d9e2', s=7, t1=11.95)
    if t >= 12.01:
        k = popin(t, 12.01, 0.25)
        blit(fg, fx.big('badge', '500CC', '#ffd23f', '#1a1a2e', '#e8b923', s=10), 760, 620, k, k, 4, anchor='center')
        fx.burst(fg, t, 12.01, 760, 620, GLOW, n=12, seed=40)
    if t >= 13.11:
        k = popin(t, 13.11, 0.25)
        blit(fg, fx.big('badge', '18 HP', '#7fe3a0', '#1a1a2e', '#3cc85a', s=12), 380, 520, k, k, -4 + 2 * math.sin(t * 6), anchor='center')
        fx.burst(fg, t, 13.11, 380, 520, (60, 200, 90), n=14, seed=41); fx.sparkles(fg, t, 540, 600, 700, 300, n=6, seed=42)
    P4.draw(fg, t)
    GAR.reflect(img, fg)
    photo(fg, t, 12.4, 13.0, 'trabant', 560, 980, 600, 420, -3, 'A LATER TRABANT 601', focus=(0.6, 0.6), zoom=0.25, pix=4)
    return finish(img, fg, CAM4, t)


# ================================================================== shot 5: millions, to the horizon
HZ_Y, VX = 640, 540
COLS = ['blue', 'cream', 'mint', 'beige', 'red']
@lru_cache(None)
def plain():
    img = Image.new('RGB', (120, 214)); d = ImageDraw.Draw(img)
    for y in range(72):
        u = y / 72; d.line([(0, y), (119, y)], fill=tuple(int(a + (b - a) * u) for a, b in zip((240, 150, 90), (250, 214, 160))))
    d.ellipse((50, 56, 70, 76), fill=(255, 236, 170))
    d.rectangle((0, 71, 119, 213), fill=(120, 130, 110))
    d.polygon([(48, 71), (72, 71), (119, 213), (0, 213)], fill=(84, 86, 96))
    for k in range(10):
        y0 = 72 + (k ** 1.6) * 3; y1 = y0 + 1 + k * 0.4
        d.rectangle((59, y0, 60, min(213, y1)), fill=(230, 230, 220))
    return up(img, S).crop((0, 0, W, H)).convert('RGBA')


def shot_millions(t):
    img = plain().copy(); fg = layer()
    adv = (t - 13.9) * 0.6
    n = 1 + int(14 * oc(prog(t, 14.0, 0.6)))
    for row in (-1, 1):
        for i in reversed(range(n)):
            z = i + 1 - adv % 1                                                         # depth; scrolls toward camera
            if z <= 0.95: continue
            sc = 7.5 / z
            x = VX + row * 260 * sc / 7.5 * 1.6
            y = HZ_Y + (GROUND + 300 - HZ_Y) / z
            if sc < 0.6: continue
            spr = up(ts(COLS[(i + (row > 0) * 2 + int(adv)) % 5], t * 300), max(1, int(round(sc))))
            blit(fg, spr, x, y, sc / max(1, int(round(sc))), sc / max(1, int(round(sc))), flip=row > 0)
    if t >= 14.22:
        k = popin(t, 14.22, 0.25)
        blit(fg, fx.big('badge', 'MILLIONS BUILT', '#ffd23f', '#1a1a2e', '#e8b923', s=9), 540, 420, k, k, -3 + 2 * math.sin(t * 4), anchor='center')
        fx.burst(fg, t, 14.22, 540, 420, GLOW, n=16, seed=50)
    if t >= 15.58:
        k = popin(t, 15.58, 0.25)
        blit(fg, fx.big('tag', 'SYMBOL OF A COUNTRY', '#fff6e0', '#1a1a2e', s=6), 540, 560, k, k, 3, anchor='center')
        fx.confetti(fg, t, 15.58, 540, 500, n=36, seed=51)
    fx.sparkles(fg, t, 540, 700, 900, 300, n=6, seed=52)
    return finish(img, fg, CAM5, t, rim=False)


CAM5 = Camera(W, H, [(13.9, (540, 900, 1.2)), (14.69, (540, 920, 1.08), 'io'), (16.75, (540, 900, 1.16), 'io')],
              kicks=[(14.22, 0.12, 540, 420), (15.58, 0.12, 540, 560), (16.69, 0.08, 540, 900)])

shot_teaser, TEASE_CUES = kit.teaser(16.75, WORDS)

# ================================================================== shots + transitions
SHOTS = [(-1.0, shot_cut), (2.4, shot_short), (7.2, shot_recipe), (9.8, shot_engine), (13.9, shot_millions), (16.75, shot_teaser)]
TRANS = {1: (2.4, 2.6, 'whip', dict(dx=1)), 2: (7.2, 7.4, 'push', None), 3: (9.8, 10.0, 'whip', dict(dx=0, dy=1)),
         4: (13.9, 14.1, 'iris', (EX, EY)), 5: (16.75, 16.95, 'whip', dict(dx=1))}
KEYCOL = {'trabant': YEL, 'germany': YEL, 'steel': RED, 'short': RED, 'body': YEL, 'plastic-like': YEL, 'duroplast': GRN,
          'reportedly': YEL, 'cotton': YEL, 'waste': YEL, 'resin': YEL, 'two-stroke': YEL, '500cc': YEL, '18': GRN, 'horsepower': GRN,
          'millions': YEL, 'symbol': GRN}
CUES = [
    (0.0, 'whoosh', 0.4), (0.05, 'pop', 0.5), (0.3, 'pop', 0.5), (CUT_T - 0.05, 'click', 0.8), (CUT_T, 'crash', 0.6), (CUT_T + 0.05, 'stamp', 0.7),
    (PANEL_T, 'pop', 0.9), (PANEL_T + 0.02, 'sparkle', 0.6), (1.62, 'pop', 0.6),
    (2.7, 'poof', 0.5), (3.0, 'poof', 0.4), (3.22, 'buzzer', 0.5), (4.6, 'thump', 0.7), (4.9, 'slide_down', 0.4), (5.14, 'pop', 0.6),
    (5.9, 'thump', 0.7), (6.2, 'slide_down', 0.4), (6.53, 'ding', 0.8), (6.55, 'sparkle', 0.6),
    (7.52, 'stamp', 0.6)] + [(t0, 'thump', 0.35) for t0, _ in ITEMS] + [(8.3, 'pop', 0.6), (9.2, 'pop', 0.6), (9.3, 'slide_down', 0.4),
    (10.0, 'vroom', 0.5), (10.69, 'pop', 0.6), (11.09, 'pop', 0.6), (12.01, 'stamp', 0.7), (12.4, 'pop', 0.5), (13.11, 'ding', 0.8),
    (13.13, 'sparkle', 0.7),
    (14.0, 'whoosh', 0.5), (14.22, 'stamp', 0.8), (14.69, 'vroom', 0.4), (15.58, 'confetti', 0.8), (15.6, 'ding', 0.7),
] + TEASE_CUES

kit.setup(HERE, WORDS, DUR, END_T, SHOTS, TRANS, CUES, KEYCOL, overlay=overlay, bar_car='silver', gauge=True, loud=True)

if __name__ == '__main__':
    kit.main()
