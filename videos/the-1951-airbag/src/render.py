"""Renders 'The 1951 airbag': series production in 1981, the crash and sled tests, and the 1951 German patent.

Template: videos/the-land-rover-from-the-sand (ac-idle shot structure on shared/episode.py). Word times come from
align.py -> words.json (the voiceover is the timing spine). Speech runs 0-17.1 s; 'Follow' plays over the end card.
Cars are generic pixel saloons: no badges, logos or lettering. No lives-saved figure is shown (not attributed).
Shots:
  1 hook     0.00  cockpit close-up: the steering wheel fires an airbag; 'It existed before 1981.'; AIRBAG label
  2 line     3.10  a production line: saloons roll out, 100+ CARS counter and a 2 MONTHS calendar; pixel photo
  3 lab      5.80  crash lab: the saloon hits the barrier, counter ticks to 250; the dummy sled shoots past 2,500
  4 patent   10.10 a 1951 patent document slides in and gets stamped; GERMANY label
  5 tech     13.70 a crash sensor and a gas canister click into place; the bag fires in a clean burst; photo
  6 teaser   16.30 shared NEXT EPISODE ending
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
from pixanim.dash import Dashboard
from pixanim import fx, diagram as dg
from pixanim.fx import blit, popin, popout
from pixanim.grid import up, outline, Grid, text_width

WORDS = kit.load_words(HERE)
DUR, END_T = 18.2, 16.3
DASH = Dashboard(outside=GAR.base())


# ------------------------------------------------------------------ episode sprites
def ptext(s, col, ol=False):
    g = Grid(text_width(s) + 2, 9); g.text(1, 1, s, col if isinstance(col, str) else '#%02x%02x%02x' % col)
    return g.image(outline=ol)


def _wheel(d, cx, cy, r, spin, rim):
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(26, 27, 32))
    d.ellipse((cx - r + 1.5, cy - r + 1.5, cx + r - 1.5, cy + r - 1.5), fill=(40, 42, 48))
    rr = r * 0.6
    d.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), fill=rim)
    d.arc((cx - rr, cy - rr, cx + rr, cy + rr), 200, 330, fill=tuple(min(255, c + 50) for c in rim))
    for k in range(8):
        a = math.radians(k * 45 + spin)
        d.point((cx + rr * 0.7 * math.cos(a), cy + rr * 0.7 * math.sin(a)), fill=tuple(int(c * 0.65) for c in rim))
    d.ellipse((cx - 1.5, cy - 1.5, cx + 1.5, cy + 1.5), fill=(230, 232, 238))


@lru_cache(None)
def saloon(spin=0, dummy=False, crushed=0):
    """Long, upright early-80s luxury saloon (104x38 grid), nose right, in champagne silver: tall glasshouse,
    upright plain grille (no emblem), ribbed lower cladding. `crushed` folds the nose in by that many columns."""
    body, shade, hi, deep = (198, 190, 170), (156, 148, 128), (236, 230, 214), (110, 104, 90)
    img = Image.new('RGBA', (104, 38), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    nose = 100 - crushed
    d.polygon([(3, 15), (22, 13), (30, 3), (64, 3), (74, 13), (nose - 4, 15), (nose, 17), (nose, 27), (3, 27)], fill=body)
    d.line([(3, 15), (22, 13), (30, 3), (64, 3), (74, 13), (nose - 4, 15)], fill=hi)
    d.rectangle((3, 21, nose, 27), fill=(150, 152, 156))                                     # ribbed cladding
    for y in (22, 24, 26): d.line([(4, y), (nose - 1, y)], fill=(126, 128, 134))
    d.line([(3, 20), (nose, 20)], fill=deep)
    d.polygon([(24, 12), (31, 5), (45, 5), (45, 12)], fill=(120, 152, 180)); d.polygon([(48, 12), (48, 5), (63, 5), (71, 12)], fill=(120, 152, 180))
    d.line([(32, 6), (44, 6)], fill=(196, 222, 240)); d.line([(46, 4), (46, 13)], fill=deep)
    if dummy:                                                                                # crash dummy at the wheel
        d.ellipse((53, 5, 60, 12), fill=(250, 210, 40)); d.line([(56, 5), (56, 12)], fill=(26, 26, 46)); d.line([(53, 8), (60, 8)], fill=(26, 26, 46))
        d.pieslice((53, 5, 60, 12), 270, 360, fill=(26, 26, 46)); d.pieslice((53, 5, 60, 12), 90, 180, fill=(26, 26, 46))
    d.line([(46, 14), (46, 20)], fill=deep); d.line([(74, 14), (74, 20)], fill=deep)
    d.rectangle((nose - 3, 15, nose, 20), fill=(220, 224, 232))                              # plain grille + lamp
    for y in (16, 18): d.line([(nose - 3, y), (nose, y)], fill=(120, 124, 134))
    d.rectangle((nose - 8, 15, nose - 4, 18), fill=(255, 244, 200))
    d.rectangle((2, 15, 5, 19), fill=(190, 40, 40))
    if crushed:
        for k in range(3): d.line([(nose - 8 - k * 4, 14), (nose - 6 - k * 4, 26)], fill=deep)
    for cx in (20, 82): d.pieslice((cx - 10, 18, cx + 10, 38), 180, 360, fill=(14, 14, 20))
    for cx in (20, min(82, nose - 14)): _wheel(d, cx, 29, 8.4, spin, (210, 214, 222))
    return outline(img)


@lru_cache(None)
def wheel_front(bag=0.0):
    """Steering wheel seen from the driver's seat (70x70): rim with grips, three spokes, padded hub; `bag` 0..1
    swells the airbag out of the hub (white cushion with fold shading and vent)."""
    img = Image.new('RGBA', (70, 70), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    c = 35
    d.ellipse((2, 2, 67, 67), fill=(36, 38, 46)); d.ellipse((8, 8, 61, 61), fill=(0, 0, 0, 0))
    d.arc((2, 2, 67, 67), 200, 320, fill=(76, 80, 94)); d.arc((4, 4, 65, 65), 200, 320, fill=(60, 63, 74))
    for a in (200, 340): d.arc((2, 2, 67, 67), a - 12, a + 12, fill=(52, 46, 40))               # leather grips
    for a in (180, 0, 270 + 180):
        x, y = c + 28 * math.cos(math.radians(a)), c + 28 * math.sin(math.radians(a))
        d.line([(c, c), (x, y)], fill=(48, 50, 60), width=5)
    d.rounded_rectangle((c - 11, c - 9, c + 11, c + 10), 4, fill=(54, 56, 66)); d.line([(c - 9, c - 8), (c + 9, c - 8)], fill=(84, 88, 100))
    d.line([(c - 6, c + 2), (c + 6, c + 2)], fill=(36, 38, 46))                                  # tear seam
    if bag > 0:
        r = 4 + 22 * bag
        d.ellipse((c - r, c - r * 0.9, c + r, c + r * 0.9), fill=(238, 240, 244))
        d.ellipse((c - r * 0.8, c - r * 0.8, c + r * 0.55, c + r * 0.5), fill=(250, 251, 253))
        d.arc((c - r, c - r * 0.9, c + r, c + r * 0.9), 20, 160, fill=(196, 200, 210))
        for k in range(3):
            a = math.radians(30 + k * 50)
            d.line([(c + r * 0.3 * math.cos(a), c + r * 0.3 * math.sin(a)), (c + r * 0.8 * math.cos(a), c + r * 0.8 * math.sin(a))], fill=(206, 210, 220))
    return outline(img)


@lru_cache(None)
def barrier():
    img = Image.new('RGBA', (22, 44), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rectangle((0, 0, 21, 43), fill=(150, 152, 160)); d.line([(0, 0), (21, 0)], fill=(200, 204, 212))
    for y in range(4, 40, 8):
        d.polygon([(0, y), (10, y + 4), (21, y), (21, y + 3), (10, y + 7), (0, y + 3)], fill=(255, 200, 40))
    d.rectangle((0, 40, 21, 43), fill=(90, 92, 100))
    return outline(img)


@lru_cache(None)
def sled(lean=0):
    """Sled-test rig (44x30): a seat on a rail carriage with a crash dummy strapped in; `lean` tips him forward."""
    img = Image.new('RGBA', (44, 30), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rectangle((0, 24, 43, 29), fill=(90, 94, 104)); d.line([(0, 24), (43, 24)], fill=(150, 156, 168))
    for x in (6, 36): d.ellipse((x - 3, 25, x + 3, 31), fill=(40, 42, 48))
    d.rectangle((8, 8, 12, 23), fill=(60, 62, 74)); d.rectangle((8, 18, 26, 23), fill=(70, 72, 86))   # seat
    hx = 16 + lean
    d.rectangle((13 + lean // 2, 10, 20 + lean // 2, 18), fill=(250, 210, 40))                         # torso
    d.rectangle((18, 16, 30, 19), fill=(240, 196, 40)); d.rectangle((28, 16, 31, 23), fill=(240, 196, 40))
    d.ellipse((hx - 3, 2, hx + 4, 9), fill=(250, 210, 40))
    d.pieslice((hx - 3, 2, hx + 4, 9), 270, 360, fill=(26, 26, 46)); d.pieslice((hx - 3, 2, hx + 4, 9), 90, 180, fill=(26, 26, 46))
    d.line([(13, 10), (20, 18)], fill=(40, 40, 50))                                                    # belt
    return outline(img)


@lru_cache(None)
def patent(stamped=False):
    """A 1951 patent document (50x64): header, title lines, a drawing of a folded cushion that inflates, date."""
    img = Image.new('RGBA', (50, 64), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rectangle((0, 0, 49, 63), fill=(244, 236, 208)); d.rectangle((0, 58, 49, 63), fill=(222, 210, 176))
    t = ptext('PATENT', (26, 26, 46)); img.alpha_composite(t, (25 - t.width // 2, 2))
    for y in (12, 15): d.line([(5, y), (44, y)], fill=(140, 130, 110))
    d.rectangle((6, 19, 43, 44), outline=(120, 110, 90))                                      # technical drawing
    d.rectangle((9, 34, 18, 40), outline=(40, 40, 60)); d.ellipse((18, 24, 38, 42), outline=(40, 40, 60))
    d.line([(14, 34), (22, 30)], fill=(40, 40, 60)); d.line([(30, 42), (36, 47)], fill=(40, 40, 60))
    for y in (24, 28): d.point((40, y), fill=(40, 40, 60))
    t = ptext('1951', (26, 26, 46)); img.alpha_composite(t, (25 - t.width // 2, 48))
    return outline(img)


@lru_cache(None)
def sensor(blink=False):
    img = Image.new('RGBA', (18, 12), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rectangle((0, 1, 17, 11), fill=(60, 64, 76)); d.line([(0, 1), (17, 1)], fill=(110, 116, 130))
    d.rectangle((3, 4, 8, 8), fill=(30, 32, 40)); d.rectangle((11, 4, 14, 6), fill=(255, 70, 70) if blink else (120, 30, 30))
    for x in (2, 6, 10, 14): d.point((x, 11), fill=(200, 170, 80))
    return outline(img)


@lru_cache(None)
def canister():
    img = Image.new('RGBA', (16, 26), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rounded_rectangle((1, 3, 14, 25), 4, fill=(176, 182, 194)); d.line([(4, 5), (4, 22)], fill=(226, 230, 238))
    d.rectangle((5, 0, 10, 3), fill=(120, 124, 134)); d.rectangle((1, 12, 14, 15), fill=(214, 48, 58))
    t = ptext('GAS', (255, 255, 255)); img.alpha_composite(t.crop((0, 0, t.width, 9)), (8 - t.width // 2, 14))
    return outline(img)


def counter(n, col='#ffd23f'):
    return fx.big('badge', f'{n:,}'.replace(',', ' '), '#1a1a2e', col, '#3c3f47', s=11)


# ------------------------------------------------------------------ crash lab world (9 px grid)
@lru_cache(None)
def lab():
    img = Image.new('RGB', (120, 214)); d = ImageDraw.Draw(img)
    d.rectangle((0, 0, 119, 131), fill=(206, 210, 218))
    for y in range(0, 131, 10): d.line([(0, y), (119, y)], fill=(190, 194, 204))
    for x in range(0, 120, 10): d.line([(x, 0), (x, 131)], fill=(190, 194, 204))
    for x in range(0, 120, 20): d.rectangle((x, 100, x + 9, 109), fill=(26, 26, 34)); d.rectangle((x + 10, 110, x + 19, 119), fill=(26, 26, 34))
    d.rectangle((0, 122, 119, 131), fill=(255, 200, 40))
    for x in range(0, 120, 8): d.polygon([(x, 131), (x + 4, 122), (x + 8, 122), (x + 4, 131)], fill=(26, 26, 34))
    for x in (20, 60, 100): d.rectangle((x - 8, 0, x + 8, 5), fill=(90, 94, 104)); d.rectangle((x - 6, 5, x + 6, 7), fill=(255, 252, 230))
    d.rectangle((0, 132, 119, 213), fill=(120, 124, 134))
    for x in range(0, 120, 6): d.line([(x, 140), (x + 3, 213)], fill=(110, 114, 124))
    d.rectangle((0, 150, 119, 151), fill=(255, 255, 255))
    return up(img, S).crop((0, 0, W, H)).convert('RGBA')


@lru_cache(None)
def factory():
    img = Image.new('RGB', (120, 214)); d = ImageDraw.Draw(img)
    d.rectangle((0, 0, 119, 131), fill=(54, 58, 72))
    for x in range(0, 120, 24):
        d.rectangle((x + 2, 10, x + 20, 40), fill=(80, 96, 124)); d.rectangle((x + 4, 12, x + 18, 38), fill=(120, 150, 190))
        d.line([(x + 11, 12), (x + 11, 38)], fill=(80, 96, 124)); d.line([(x + 4, 25), (x + 18, 25)], fill=(80, 96, 124))
    d.rectangle((0, 50, 119, 53), fill=(255, 200, 40))
    for x in range(0, 120, 12): d.rectangle((x, 54, x + 1, 120), fill=(76, 80, 96))
    d.rectangle((0, 132, 119, 213), fill=(70, 72, 84))
    d.rectangle((0, 128, 119, 135), fill=(40, 42, 50))
    for x in range(0, 120, 6): d.rectangle((x, 129, x + 3, 130), fill=(100, 104, 116))
    return up(img, S).crop((0, 0, W, H)).convert('RGBA')


# ================================================================== shot 1: hook, the wheel fires
BAG_T = 0.35
def bag(t): return 0 if t < BAG_T else (oc(prog(t, BAG_T, 0.16)) if t < 1.3 else 1 - 0.25 * io(prog(t, 1.3, 1.0)))
CAM1 = Camera(W, H, [(-1.0, (540, 980, 1.3)), (0.0, (540, 980, 1.3)), (0.5, (540, 1000, 1.08), 'io'), (2.0, (540, 980, 1.14), 'io'), (3.1, (560, 960, 1.2))],
              kicks=[(BAG_T, 0.18, 540, 1050), (1.0, 0.06, 540, 900), (2.07, 0.1, 540, 1050), (2.56, 0.12, 760, 800)],
              shakes=[(BAG_T, 0.35, 18)])


def shot_hook(t):
    img = DASH.frame(t, rpm_deg=200 + 6 * math.sin(t * 3), speed_deg=150); fg = layer()
    b = bag(t)
    blit(fg, up(wheel_front(round(b * 24) / 24), 10), 540, 1120, 1, 1, 0, anchor='center')
    fx.ring(fg, t, BAG_T, 540, 1120, (255, 255, 255), life=0.3, r1=520)
    fx.burst(fg, t, BAG_T, 540, 1120, GLOW, n=16, r0=200, r1=560, seed=1)
    fx.poof(fg, t, BAG_T + 0.05, 540, 1120, seed=2, scale=0.6)
    if t >= 1.4: fx.sparkles(fg, t, 540, 1000, 700, 400, n=7, seed=3)
    dg.label(fg, t, 2.07, 'AIRBAG', (640, 980), (820, 720), '#ffffff', '#1a1a2e', '#d6d9e2', s=8)
    if t >= 2.56: fx.stamp_at(fg, t, 2.56, 'IN PRODUCTION', 540, 1430 - 200, rot=-6, s=8, col='#3cc85a')
    return finish(img.convert('RGBA'), fg, CAM1, t, rim=False)


def overlay(cv, t):
    title(cv, t, 0.05, 2.4, 'It existed', WHITE, 430, 100, -2)
    title(cv, t, 0.25, 2.4, 'before', YEL, 560, 140, 3)
    title(cv, t, 0.45, 2.4, '1981.', WHITE, 690, 110, -2)


# ================================================================== shot 2: the production line, 100+ cars
LINE_Y = GROUND + 40
def line_scroll(t): return (t - 3.1) * 420
def cars_n(t): return 0 if t < 3.38 else int(100 * oc(prog(t, 3.38, 0.8)))
CAM2 = Camera(W, H, [(3.1, (540, 940, 1.14)), (3.81, (540, 960, 1.22), 'io'), (5.14, (600, 920, 1.12), 'io'), (5.8, (600, 920, 1.16))],
              kicks=[(3.38, 0.08, 540, 500), (3.81, 0.12, 540, 1000), (4.17, 0.06, 540, 1000), (5.14, 0.12, 820, 560)])


def shot_line(t):
    img = factory().copy(); fg = layer()
    sc = line_scroll(t)
    for i in range(-1, 3):                                                            # saloons glide along the line
        x = (i * 720 + sc) % 2160 - 540
        fx.contact_shadow(fg, x, LINE_Y, 600, s=S, alpha=120)
        blit(fg, up(saloon(int(sc) % 360 // 30 * 30), 6), x, LINE_Y)
        blit(fg, fx.big('check', s=7), x + 40, LINE_Y - 260, 1, 1) if x > 300 else None
    if t >= 3.38:
        k = popin(t, 3.38, 0.25) * (1 + 0.05 * math.sin(t * 10))
        blit(fg, counter(cars_n(t)), 330, 520, k, k, -3, anchor='center')
        blit(fg, fx.big('label', 'CARS', '#ffffff', s=8), 330, 640, k, k, anchor='center')
        fx.burst(fg, t, 4.17, 330, 520, GLOW, n=12, seed=20)
        if t >= 4.17:
            kp = popin(t, 4.17, 0.2); blit(fg, fx.big('glyph', '+', '#ffd23f', s=12), 500, 500, kp, kp, anchor='center')
    dg.label(fg, t, 3.81, 'S-CLASS', (700, LINE_Y - 200), (720, 760), '#ffffff', '#1a1a2e', '#d6d9e2', s=8, t1=5.0)
    if t >= 5.14:
        k = popin(t, 5.14, 0.25)
        blit(fg, fx.big('badge', '2 MONTHS', '#ffd23f', '#1a1a2e', '#e8b923', s=8), 760, 540, k, k, 4, anchor='center')
        fx.burst(fg, t, 5.14, 760, 540, GLOW, n=10, seed=21)
    photo(fg, t, 4.25, 5.1, 's_class', 540, 1000, 620, 440, -3, 'AN EARLY-80s S-CLASS', focus=(0.75, 0.62), zoom=0.6, pix=4)
    return finish(img, fg, CAM2, t, rim=False)


# ================================================================== shot 3: the crash lab
BX = 900
def crash_x(t):                                                                       # three runs into the barrier
    for t0 in (6.0, 6.55, 7.1):
        if t0 <= t < t0 + 0.55: return lerp(-400, BX - 330, ic(prog(t, t0, 0.3))) if t < t0 + 0.3 else BX - 330
    return BX - 330
def crash_n(t): return 0 if t < 6.3 else min(250, int(250 * io(prog(t, 6.3, 0.69))))
def sled_n(t): return 0 if t < 8.3 else min(2500, int(2500 * io(prog(t, 8.3, 0.34))))
def sled_x(t): return lerp(-300, 1400, prog(t, 8.9, 0.5)) if t < 9.4 else lerp(-300, 520, oc(prog(t, 9.4, 0.3)))
P3 = Presenter([
    (5.75, dict(path=Track([(5.75, (-200, 400)), (6.15, (140, GROUND + 60), 'oc')]), size=6, legs='auto', arms='fly', expr='talk', face=1, ground=None)),
    (6.15, dict(ground=GROUND + 60, squash=True, arms='point', point=(BX, GROUND - 200), look=(BX, GROUND - 200), expr='smile', face=None)),
    (7.6, dict(arms='shock', expr='shock', point=None, squash=True)),
    (8.64, dict(arms='cheer', look=(540, 600), expr='wow')),
], words=WORDS, base_size=6)
CAM3 = Camera(W, H, [(5.8, (560, 1110, 1.12)), (6.99, (600, 1060, 1.16), 'io'), (8.2, (560, 1090, 1.12), 'io'), (9.5, (560, 1120, 1.2), 'io'), (10.1, (560, 1120, 1.22))],
              kicks=[(6.3, 0.12, BX - 100, 1000), (6.85, 0.12, BX - 100, 1000), (7.4, 0.12, BX - 100, 1000), (6.99, 0.1, 540, 520), (8.64, 0.14, 540, 520), (9.5, 0.12, 540, 1000)],
              shakes=[(6.3, 0.2, 14), (6.85, 0.2, 14), (7.4, 0.2, 14), (9.7, 0.2, 10)])


def shot_lab(t):
    img = lab().copy(); fg = layer()
    blit(fg, up(barrier(), 9), BX, GROUND + 60)
    if t < 8.3:
        x = crash_x(t); hit = any(t0 + 0.3 <= t < t0 + 0.55 for t0 in (6.0, 6.55, 7.1))
        fx.contact_shadow(fg, x, GROUND + 60, 620, s=S, alpha=130)
        blit(fg, up(saloon(int(x) % 360 // 30 * 30, True, 5 if hit else 0), 6), x, GROUND + 60, 0.96 if hit else 1, 1.04 if hit else 1)
        for t0 in (6.0, 6.55, 7.1):
            fx.burst(fg, t, t0 + 0.3, BX - 90, GROUND - 60, GLOW, n=12, r0=60, r1=260, seed=int(t0 * 10))
            fx.dust(fg, t, t0 + 0.3, BX - 120, GROUND, n=10, seed=int(t0 * 10) + 1)
            fx.poof(fg, t, t0 + 0.32, BX - 230, GROUND - 60, seed=int(t0 * 10) + 2, scale=0.4)
        k = popin(t, 6.3, 0.25)
        if k > 0:
            blit(fg, counter(crash_n(t), '#ff5a5a'), 470, 520, k, k, -3, anchor='center')
            blit(fg, fx.big('label', 'CRASH TESTS', '#ffffff', s=7), 470, 640, k, k, anchor='center')
        fx.ring(fg, t, 6.99, 470, 520, RED, life=0.3, r1=300)
    else:                                                                             # sled tests
        if t >= 8.3:
            k = popin(t, 8.3, 0.25)
            blit(fg, counter(sled_n(t), '#7fe3a0'), 560, 520, k, k, 3, anchor='center')
            blit(fg, fx.big('label', 'SLED TESTS', '#ffffff', s=7), 560, 640, k, k, anchor='center')
            fx.burst(fg, t, 8.64, 560, 520, (60, 200, 90), n=14, seed=30)
        d = ImageDraw.Draw(fg); d.rectangle((0, GROUND + 50, W, GROUND + 64), fill=(80, 84, 96, 255))
        for k in range(4):                                                            # sled shots, repeated
            u = prog(t, 8.5 + k * 0.12, 0.25)
            if 0 < u < 1: fx.speed_lines(fg, 0.4, k, col=(140, 146, 160))
        x = sled_x(t)
        blit(fg, up(sled(4 if 9.4 <= t < 9.8 else 0), 12), x, GROUND + 60)
        fx.dust(fg, t, 9.7, x + 100, GROUND + 40, n=8, seed=31)
        if t >= 9.74: fx.sparkles(fg, t, 560, 560, 600, 300, n=6, seed=32)
    P3.draw(fg, t)
    return finish(img, fg, CAM3, t, rim=False)


# ================================================================== shot 4: the 1951 patent
P4 = Presenter([
    (10.05, dict(path=Track([(10.05, (1300, 400)), (10.45, (880, GROUND), 'oc')]), size=7, legs='auto', arms='fly', expr='talk', face=-1, ground=None)),
    (10.45, dict(ground=GROUND, squash=True, arms='think' if False else 'hips', look=(470, 700), expr='think', face=None)),
    (11.77, dict(arms='point', point=(470, 760), look=(470, 760), expr='smile')),
    (12.71, dict(arms='cheer', point=None, expr='wow', squash=True)),
], words=WORDS, base_size=7)
CAM4 = Camera(W, H, [(10.1, (540, 900, 1.12)), (11.77, (480, 820, 1.3), 'io'), (12.71, (480, 820, 1.34)), (13.7, (520, 860, 1.22), 'io')],
              kicks=[(10.42, 0.08, 470, 800), (11.46, 0.1, 300, 520), (11.77, 0.1, 470, 760), (12.71, 0.18, 470, 900)], shakes=[(12.71, 0.3, 12)])


def shot_patent(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    fx.rays(fg, t, 10.42, 470, 800, GLOW, hold=True, r=560)
    y = lerp(-500, GROUND - 40, oc(prog(t, 10.2, 0.45)))
    sr, sv = wob(t, (10.65,), 0.08)
    blit(fg, up(patent(), 10), 470, y, sr, sv, -3 + 1.5 * math.sin(t * 2))
    fx.dust(fg, t, 10.65, 470, GROUND - 40, n=12, seed=40, col=(244, 236, 208))
    if t >= 10.42:
        k = popin(t, 10.42, 0.25) * popout(t, 11.4)
        blit(fg, fx.big('tag', 'THE IDEA WAS OLDER', '#fff6e0', '#1a1a2e', s=6), 470, 280, k, k, -3, anchor='center')
    if t >= 11.46:
        k = popin(t, 11.46, 0.25)
        blit(fg, fx.big('badge', 'GERMANY', '#ffffff', '#1a1a2e', '#d6d9e2', s=7), 290, 320, k, k, -5, anchor='center')
    dg.label(fg, t, 11.77, 'INFLATABLE', (470, 640), (660, 440), '#7fe3a0', '#1a1a2e', '#3cc85a', s=6)
    if t >= 12.71:
        fx.stamp_at(fg, t, 12.71, 'FILED 1951', 470, 1000, rot=-12, s=10, col='#3cc85a')
        fx.sparkles(fg, t, 470, 800, 600, 500, n=8, seed=41)
    fx.confetti(fg, t, 12.75, 470, 700, n=24, seed=42)
    P4.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM4, t)


# ================================================================== shot 5: sensors, gas, fast enough
WX, WY = 640, 900
def sensor_y(t): return lerp(-200, 1060, oc(prog(t, 14.3, 0.3)))
def can_x(t): return lerp(1400, WX, oc(prog(t, 14.95, 0.3)))
def bag5(t): return 0 if t < 15.55 else oc(prog(t, 15.55, 0.12))
P5 = Presenter([
    (13.65, dict(path=Track([(13.65, (-200, 400)), (14.05, (150, GROUND), 'oc')]), size=7, legs='auto', arms='fly', expr='talk', face=1, ground=None)),
    (14.05, dict(ground=GROUND, squash=True, arms='point', point=(260, 1040), look=(260, 1040), expr='smile', face=None)),
    (15.04, dict(point=(WX, WY), look=(WX, WY), expr='grin')),
    (15.6, dict(arms='shock', point=None, expr='wow', squash=True)),
], words=WORDS, base_size=7)
CAM5 = Camera(W, H, [(13.7, (560, 900, 1.12)), (14.34, (400, 980, 1.24), 'io'), (15.04, (600, 900, 1.2), 'io'), (15.6, (600, 900, 1.14), 'io'), (16.3, (600, 900, 1.16))],
              kicks=[(14.6, 0.1, 300, 1060), (15.25, 0.12, WX, WY), (15.6, 0.22, WX, WY)], shakes=[(15.6, 0.35, 16)])


def shot_tech(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    d = ImageDraw.Draw(fg)
    if t >= 14.6:                                                                     # wire from sensor to the wheel, signal pulse
        d.line([(300, 1040), (300, 1100), (WX, 1100), (WX, WY + 200)], fill=(214, 48, 58, 255), width=9)
        if t >= 15.4:
            u = prog(t, 15.4, 0.15); px = lerp(300, WX, u)
            d.ellipse((px - 18, 1082, px + 18, 1118), fill=(255, 230, 120, 255))
    d.rectangle((WX - 18, WY + 200, WX + 18, GROUND), fill=(60, 63, 74, 255))         # column
    blit(fg, up(wheel_front(round(bag5(t) * 20) / 20), 8), WX, WY, 1, 1, 0, anchor='center')
    sy = sensor_y(t)
    blit(fg, up(sensor(int(t * 6) % 2 == 0 and t > 14.6), 10), 300, sy, 1, 1, 0, anchor='center')
    fx.ring(fg, t, 14.6, 300, 1060, (60, 200, 90), life=0.3, r1=200)
    dg.label(fg, t, 14.62, 'SENSOR', (300, 1000), (300, 780), '#ffffff', '#1a1a2e', '#d6d9e2', s=7, t1=15.5)
    if t >= 14.95:
        blit(fg, up(canister(), 9), can_x(t), WY + 30, 1, 1, 0, anchor='center') if t < 15.3 else None
        fx.ring(fg, t, 15.25, WX, WY, (60, 200, 90), life=0.3, r1=240)
        if 15.25 <= t < 15.6: blit(fg, fx.big('check', s=8), WX + 200, WY - 200, 1, 1)
    dg.label(fg, t, 15.04, 'GAS', (WX + 120, WY), (900, 720), '#7fe3a0', '#1a1a2e', '#3cc85a', s=7, t1=15.55)
    if t >= 15.55:
        fx.poof(fg, t, 15.56, WX, WY, seed=50, scale=0.6)
        fx.burst(fg, t, 15.56, WX, WY, GLOW, n=18, r0=200, r1=620, seed=51)
        fx.ring(fg, t, 15.56, WX, WY, (255, 255, 255), life=0.3, r1=560)
        k = popin(t, 15.61, 0.2)
        blit(fg, fx.big('badge', 'FAST ENOUGH', '#ffd23f', '#1a1a2e', '#e8b923', s=8), 560, 460, k, k, -4 + 2 * math.sin(t * 6), anchor='center')
        fx.sparkles(fg, t, WX, WY, 700, 500, n=8, seed=52)
    P5.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM5, t)


shot_teaser, TEASE_CUES = kit.teaser(16.3, WORDS)

# ================================================================== shots + transitions
SHOTS = [(-1.0, shot_hook), (3.1, shot_line), (5.8, shot_lab), (10.1, shot_patent), (13.7, shot_tech), (16.3, shot_teaser)]
TRANS = {1: (3.1, 3.3, 'whip', dict(dx=1)), 2: (5.8, 6.0, 'push', None), 3: (10.1, 10.3, 'whip', dict(dx=0, dy=1)),
         4: (13.7, 13.9, 'iris', (470, 800)), 5: (16.3, 16.5, 'whip', dict(dx=1))}
KEYCOL = {'1981': YEL, 'airbag': YEL, '100': GRN, 'months': YEL, '250': RED, 'crash': RED, '2,500': GRN, 'older': YEL,
          'patent': GRN, '1951': GRN, 'sensors': YEL, 'fast': YEL}
CUES = [
    (0.0, 'whoosh', 0.4), (0.05, 'pop', 0.5), (0.25, 'pop', 0.6), (BAG_T, 'boom', 0.9), (BAG_T + 0.01, 'poof', 0.9), (0.45, 'pop', 0.6),
    (1.4, 'sparkle', 0.5), (2.07, 'pop', 0.6), (2.56, 'stamp', 0.8),
    (3.3, 'click', 0.4), (3.38, 'pop', 0.7)] + [(3.4 + i * 0.1, 'click', 0.25) for i in range(8)] + [
    (4.17, 'ding', 0.7), (3.81, 'pop', 0.5), (4.25, 'pop', 0.6), (5.14, 'stamp', 0.7),
    (6.0, 'vroom', 0.5), (6.3, 'crash', 0.7), (6.85, 'crash', 0.6), (7.4, 'crash', 0.7), (6.99, 'ding', 0.6),
    (8.3, 'pop', 0.6), (8.64, 'ding', 0.8), (8.9, 'whoosh', 0.8), (9.4, 'whoosh', 0.6), (9.7, 'thump', 0.6),
    (10.2, 'fall', 0.5), (10.65, 'thump', 0.6), (10.42, 'pop', 0.5), (11.46, 'pop', 0.6), (11.77, 'pop', 0.5), (12.71, 'stamp', 0.9),
    (12.75, 'confetti', 0.6),
    (14.3, 'whoosh', 0.4), (14.6, 'click', 0.8), (14.62, 'pop', 0.5), (15.0, 'whoosh', 0.5), (15.25, 'click', 0.9), (15.27, 'ding', 0.5),
    (15.56, 'boom', 0.8), (15.57, 'poof', 0.9), (15.62, 'sparkle', 0.8),
] + TEASE_CUES

kit.setup(HERE, WORDS, DUR, END_T, SHOTS, TRANS, CUES, KEYCOL, overlay=overlay, bar_car='silver', gauge=True, loud=True)

if __name__ == '__main__':
    kit.main()
