"""Renders 'Ford vs Ferrari': the 1963 buyout that failed, the GT40, and Le Mans.

Template: videos/the-land-rover-from-the-sand (ac-idle shot structure on shared/episode.py). Word times come from
align.py -> words.json (the voiceover is the timing spine). Speech runs 0-17.1 s; 'Follow' plays over the end card.
Cars are generic pixel race cars with plain number roundels: no badges, logos or lettering.
Shots:
  1 faceoff  0.00  a blue and a red car nose to nose across a dotted line; '1963'; 'Ford wanted Ferrari.'
  2 deal     3.20  desk: a contract and a calendar that flips to 22 DAYS; money stacks grow, REPORTEDLY tag
  3 walk     6.70  the contract tears; ENZO FERRARI label; the red car turns and drives off; the GT40 is built
  4 race    11.70  Le Mans at night: the GT40 hunts the red car down, flag, sparkles, pixel photo of the real car
  5 win     13.60  '1966' banner drops, victory lap under it, a row of four LE MANS WINS tags
  6 teaser  16.00  shared NEXT EPISODE ending
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
DUR, END_T = 17.9, 16.0


# ------------------------------------------------------------------ episode sprites
def ptext(s, col, ol=False):
    g = Grid(text_width(s) + 2, 9); g.text(1, 1, s, col if isinstance(col, str) else '#%02x%02x%02x' % col)
    return g.image(outline=ol)


def _wheel(d, cx, cy, r, spin, rim):
    """Low-profile racing tyre with a slotted alloy that turns with `spin`."""
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(26, 27, 32))
    d.ellipse((cx - r + 1.5, cy - r + 1.5, cx + r - 1.5, cy + r - 1.5), fill=(40, 42, 48))
    rr = r * 0.62
    d.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), fill=rim)
    d.arc((cx - rr, cy - rr, cx + rr, cy + rr), 200, 330, fill=tuple(min(255, c + 60) for c in rim))
    for k in range(6):
        a = math.radians(k * 60 + spin)
        d.line([(cx + 1.2 * math.cos(a), cy + 1.2 * math.sin(a)), (cx + rr * math.cos(a), cy + rr * math.sin(a))], fill=tuple(int(c * 0.6) for c in rim))
    d.ellipse((cx - 1.5, cy - 1.5, cx + 1.5, cy + 1.5), fill=(230, 232, 238))


RACERS = {   # body, shade, hi, deep, stripe, number
    'gt': ((40, 72, 150), (28, 52, 112), (98, 136, 214), (18, 32, 72), (236, 238, 244), '2'),
    'p3': ((220, 40, 46), (168, 26, 34), (255, 120, 122), (120, 18, 24), None, '3'),
}


@lru_cache(None)
def racer(kind='gt', spin=0, lights=False, flip=False):
    """Mid-engined endurance racer in side view (104x36 grid), nose right. 'gt' is a low, flat coupe with a Kamm
    tail and twin stripes; 'p3' is a curvier rival with bulging wings and a bubble cabin. Plain number roundels."""
    body, shade, hi, deep, stripe, num = RACERS[kind]
    img = Image.new('RGBA', (104, 36), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    if kind == 'gt':
        pts = [(2, 12), (10, 10), (34, 9), (40, 4), (60, 4), (72, 12), (88, 15), (99, 19), (102, 23), (101, 27), (2, 27)]
        win = [(42, 6), (58, 6), (67, 12), (45, 12)]
    else:
        pts = [(2, 14), (8, 11), (22, 8), (31, 10), (39, 5), (56, 4), (65, 10), (76, 8), (88, 10), (98, 15), (102, 22), (100, 27), (2, 27)]
        win = [(41, 7), (55, 6), (62, 11), (43, 12)]
    d.polygon(pts, fill=body)
    d.line(pts[1:-3], fill=hi)
    d.rectangle((3, 22, 100, 24), fill=shade); d.rectangle((3, 25, 100, 27), fill=deep)
    d.polygon(win, fill=(120, 156, 186)); d.line([win[0], win[1]], fill=(200, 226, 244))
    d.line([(win[0][0] + 4, 11), (win[0][0] + 8, 7)], fill=(196, 222, 240))
    if stripe:                                                                         # twin stripes over the roof
        for dy in (0, 2): d.line([(p[0], p[1] + dy) for p in pts[1:-3]], fill=stripe)
    d.line([(36, 12), (36, 24)], fill=deep); d.line([(68, 13), (68, 24)], fill=deep)   # door shut lines
    d.rectangle((28, 13, 33, 16), fill=deep); d.line([(28, 13), (33, 13)], fill=(10, 10, 16))   # side intake
    d.ellipse((46, 13, 58, 25), fill=(244, 244, 238)); d.ellipse((46, 13, 58, 25), outline=deep)  # number roundel
    hl = (255, 250, 210) if lights else (214, 220, 214)
    d.polygon([(92, 16), (98, 18), (99, 20), (93, 19)], fill=hl)
    d.rectangle((2, 15, 5, 18), fill=(255, 70, 70) if lights else (180, 30, 36))
    d.rectangle((1, 24, 5, 27), fill=(40, 42, 48)); d.rectangle((96, 25, 103, 27), fill=(40, 42, 48))   # splitter + diffuser
    for cx in (20, 84): d.pieslice((cx - 10, 17, cx + 10, 37), 180, 360, fill=(14, 14, 20))
    for cx in (20, 84): _wheel(d, cx, 27, 8.4, spin, (200, 204, 214))
    if flip: img = img.transpose(Image.FLIP_LEFT_RIGHT)
    n = ptext(num, (26, 26, 46)); img.alpha_composite(n, (52 - n.width // 2, 15))   # roundel is centred: number stays readable
    return outline(img)


def rc(kind, dist=0, lights=False, flip=False): return racer(kind, int(dist * 0.5) % 360 // 15 * 15, lights, flip)


@lru_cache(None)
def saloon(spin=0):
    """Plain 1960s family saloon in blue (96x40 grid), nose right: the company before it went racing."""
    body, shade, hi, deep = (60, 104, 190), (44, 78, 150), (126, 168, 236), (28, 48, 96)
    img = Image.new('RGBA', (96, 40), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.polygon([(4, 14), (24, 13), (32, 4), (60, 4), (70, 13), (92, 15), (94, 26), (3, 26)], fill=body)
    d.line([(4, 14), (24, 13), (32, 4), (60, 4), (70, 13), (92, 15)], fill=hi)
    d.rectangle((3, 21, 94, 23), fill=shade); d.rectangle((3, 24, 94, 26), fill=deep)
    d.polygon([(26, 12), (33, 6), (45, 6), (45, 12)], fill=(126, 158, 184)); d.polygon([(48, 12), (48, 6), (59, 6), (66, 12)], fill=(126, 158, 184))
    d.line([(34, 7), (44, 7)], fill=(196, 222, 240)); d.line([(46, 5), (46, 13)], fill=deep)
    d.line([(3, 17), (94, 17)], fill=(220, 224, 232))                                   # chrome strip
    d.rectangle((90, 15, 95, 19), fill=(255, 244, 200)); d.rectangle((1, 22, 95, 23), fill=(200, 204, 214))
    for cx in (20, 76): d.pieslice((cx - 10, 17, cx + 10, 37), 180, 360, fill=(14, 14, 20))
    for cx in (20, 76): _wheel(d, cx, 29, 8.4, spin, (210, 214, 222))
    return outline(img)


@lru_cache(None)
def contract(torn=False):
    """A deal document (40x52): title bar, ruled clauses, a blank signature line and a seal."""
    img = Image.new('RGBA', (40, 52), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rectangle((0, 0, 39, 51), fill=(250, 246, 232)); d.rectangle((0, 46, 39, 51), fill=(226, 220, 200))
    t = ptext('DEAL', (26, 26, 46)); img.alpha_composite(t, (20 - t.width // 2, 2))
    for y in range(13, 38, 3): d.line([(4, y), (35 - (y * 7) % 9, y)], fill=(150, 150, 160))
    d.line([(4, 43), (22, 43)], fill=(26, 26, 46)); d.ellipse((27, 37, 35, 45), fill=(214, 48, 58)); d.ellipse((29, 39, 33, 43), fill=(240, 120, 120))
    return outline(img)


def calendar(day):
    """Desk calendar (36x40): red header with binder rings, big day number, 'DAYS' under it."""
    img = Image.new('RGBA', (36, 40), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rectangle((0, 3, 35, 39), fill=(250, 250, 246)); d.rectangle((0, 3, 35, 11), fill=(214, 48, 58))
    for x in (8, 27): d.rectangle((x, 0, x + 1, 6), fill=(120, 124, 134))
    n = ptext(str(day), (26, 26, 46)); n = n.resize((n.width * 2, n.height * 2), Image.NEAREST)
    img.alpha_composite(n, (18 - n.width // 2, 12))
    t = ptext('DAYS', (214, 48, 58)); img.alpha_composite(t, (18 - t.width // 2, 30))
    return outline(img)


@lru_cache(None)
def money():
    """A banded stack of bills (30x10)."""
    img = Image.new('RGBA', (30, 10), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    for y in (0, 3, 6): d.rectangle((0, y, 29, y + 3), fill=(110, 176, 110)); d.line([(0, y), (29, y)], fill=(170, 220, 160))
    d.rectangle((12, 0, 17, 9), fill=(240, 236, 200))
    return outline(img)


@lru_cache(None)
def flag(ph):
    """Chequered flag (26x18 incl. pole) whose cloth ripples with phase ph (0..7)."""
    img = Image.new('RGBA', (26, 22), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rectangle((0, 0, 1, 21), fill=(200, 204, 214))
    for i in range(6):
        for j in range(4):
            off = round(1.5 * math.sin((i + ph) * 0.9))
            d.rectangle((2 + i * 4, 1 + j * 3 + off, 5 + i * 4, 3 + j * 3 + off), fill=(244, 244, 244) if (i + j) % 2 else (26, 26, 34))
    return outline(img)


@lru_cache(None)
def trophy():
    img = Image.new('RGBA', (24, 30), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    gold, sh, hi = (255, 200, 60), (210, 150, 30), (255, 240, 160)
    d.pieslice((2, -8, 21, 16), 0, 180, fill=gold); d.rectangle((2, 0, 21, 4), fill=gold)
    d.arc((-3, 1, 6, 11), 90, 270, fill=gold); d.arc((17, 1, 26, 11), 270, 90, fill=gold)
    d.rectangle((10, 15, 13, 21), fill=sh); d.rectangle((5, 22, 18, 25), fill=gold); d.rectangle((3, 26, 20, 29), fill=(90, 60, 40))
    d.line([(6, 2), (6, 9)], fill=hi)
    return outline(img)


# ------------------------------------------------------------------ night circuit world (3 px grid, parallax)
TS = 6
TRACK_Y = 1240


@lru_cache(None)
def circuit_layers():
    """Sky (static), grandstand with floodlights (slow), pit wall with boards (fast), track with kerbs (fast)."""
    sky = Image.new('RGB', (W // TS, H // TS)); d = ImageDraw.Draw(sky)
    for y in range(sky.height):
        u = min(1, y / 170); d.line([(0, y), (sky.width, y)], fill=tuple(int(a + (b - a) * u) for a, b in zip((10, 12, 30), (40, 34, 70))))
    r = fx.rng(4)
    for _ in range(70): d.point((int(r.uniform(0, sky.width)), int(r.uniform(0, 140))), fill=(200, 210, 240))
    d.ellipse((140, 30, 156, 46), fill=(240, 236, 210)); d.ellipse((146, 28, 160, 42), fill=(16, 16, 36))
    stand = Image.new('RGBA', (2 * W // TS, H // TS), (0, 0, 0, 0)); d = ImageDraw.Draw(stand)
    gy = TRACK_Y // TS - 40
    for x0 in range(0, stand.width, 120):
        d.polygon([(x0 + 6, gy), (x0 + 20, gy - 40), (x0 + 104, gy - 40), (x0 + 114, gy)], fill=(34, 36, 50))
        for y in range(gy - 36, gy, 4):
            for x in range(x0 + 20, x0 + 104, 3):
                d.point((x + (y % 8) // 4, y), fill=(60 + (x * 7 + y) % 40, 52, 70))
        d.rectangle((x0 + 14, gy - 46, x0 + 110, gy - 42), fill=(54, 58, 74))
        for lx in (x0 + 30, x0 + 90):                                                    # floodlight towers
            d.rectangle((lx, gy - 78, lx + 1, gy - 40), fill=(70, 74, 90)); d.rectangle((lx - 4, gy - 84, lx + 5, gy - 78), fill=(255, 246, 200))
    wall = Image.new('RGBA', (2 * W // TS, H // TS), (0, 0, 0, 0)); d = ImageDraw.Draw(wall)
    wy = TRACK_Y // TS - 22
    d.rectangle((0, wy, wall.width, wy + 8), fill=(170, 174, 186)); d.line([(0, wy), (wall.width, wy)], fill=(220, 224, 232))
    for x in range(0, wall.width, 60):
        d.rectangle((x + 10, wy - 14, x + 34, wy - 2), fill=(250, 250, 244)); d.rectangle((x + 10, wy - 14, x + 34, wy - 2), outline=(26, 26, 46))
        bd = ptext(str(24 if (x // 60) % 2 else 'H').replace('H', 'LAP'), (214, 48, 58)); wall.alpha_composite(bd, (x + 22 - bd.width // 2, wy - 12))
    track = Image.new('RGBA', (2 * W // TS, H // TS), (0, 0, 0, 0)); d = ImageDraw.Draw(track)
    ty = TRACK_Y // TS - 14
    d.rectangle((0, ty, track.width, track.height), fill=(44, 46, 54))
    for x in range(0, track.width, 16): d.rectangle((x, ty, x + 7, ty + 3), fill=(214, 48, 58)); d.rectangle((x + 8, ty, x + 15, ty + 3), fill=(240, 240, 240))
    for x in range(0, track.width, 24): d.rectangle((x, ty + 30, x + 12, ty + 31), fill=(220, 220, 214))
    for x in range(0, track.width, 5):
        for y in range(ty + 5, track.height, 4): d.point((x + (y * 3) % 5, y), fill=(52, 54, 64))
    d.rectangle((0, ty + 60, track.width, track.height), fill=(30, 50, 34))
    return up(sky, TS), up(stand, TS), up(wall, TS), up(track, TS)


def circuit(t, scroll):
    sky, stand, wall, track = circuit_layers()
    img = sky.convert('RGBA')
    for lay, k in ((stand, 0.25), (wall, 0.8), (track, 1.0)):
        x = -int(scroll * k) % lay.width
        img.alpha_composite(lay, (x - lay.width, 0)); img.alpha_composite(lay, (x, 0))
    d = ImageDraw.Draw(img)                                                           # flicker of camera flashes in the stand
    r = fx.rng(int(t * 12))
    for _ in range(3):
        x, y = r.uniform(0, W), r.uniform(TRACK_Y - 470, TRACK_Y - 300)
        d.rectangle((x, y, x + 6, y + 6), fill=(255, 255, 240))
    return img


def beam(cv, x, y, length=420, flip=False, a=46):
    d = ImageDraw.Draw(cv); sg = -1 if flip else 1
    d.polygon([(x, y - 10), (x + sg * length, y - 70), (x + sg * length, y + 50), (x, y + 6)], fill=(255, 248, 210, a))


# ================================================================== shot 1: the face-off
LINE_X = 540
CS = 5
def blue_x(t): return lerp(-500, LINE_X - 265, oc(prog(t, 0.0, 0.45))) + (8 * math.sin(t * 50) if 1.6 <= t < 2.1 else 0)
def red_x(t): return lerp(1580, LINE_X + 265, oc(prog(t, 0.08, 0.45))) + (8 * math.sin(t * 50) if 2.67 <= t < 3.1 else 0)
CAM1 = Camera(W, H, [(-1.0, (540, 1000, 1.25)), (0.0, (540, 1000, 1.25)), (0.6, (540, 1000, 1.06), 'io'), (1.6, (360, 1000, 1.18), 'io'),
                     (2.4, (720, 1000, 1.18), 'io'), (3.2, (540, 1000, 1.1))],
              kicks=[(0.0, 0.08, 540, 1000), (0.45, 0.12, LINE_X, 1000), (1.6, 0.08, 300, 1000), (2.67, 0.12, 800, 1000)],
              shakes=[(0.45, 0.25, 12)])


def shot_faceoff(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    d = ImageDraw.Draw(fg)
    for y in range(GROUND - 300, GROUND + 160, 36): d.rectangle((LINE_X - 6, y, LINE_X + 6, y + 18), fill=(255, 255, 255, 220))   # dotted line
    fx.rays(fg, t, 0.45, LINE_X, GROUND - 160, GLOW, life=0.9, r=520)
    bx, rx = blue_x(t), red_x(t)
    for x in (bx, rx): fx.contact_shadow(fg, x, GROUND, 520, s=S, alpha=140)
    sb = wob(t, (0.45, 1.6), 0.07); sr = wob(t, (0.53, 2.67), 0.07)
    blit(fg, up(saloon(int(bx) % 360 // 15 * 15), CS), bx, GROUND, *sb)
    blit(fg, up(rc('p3', rx, flip=True), CS), rx, GROUND, *sr)
    for k in range(4):
        fx.puff(fg, t, 1.6 + k * 0.1, bx - 250, GROUND - 40, seed=10 + k, life=0.6, size=0.7, drift=(-160, -60))
        fx.puff(fg, t, 2.67 + k * 0.1, rx + 250, GROUND - 40, seed=20 + k, life=0.6, size=0.7, drift=(160, -60))
    fx.burst(fg, t, 0.45, LINE_X, GROUND - 120, GLOW, n=14, seed=2)
    if t >= 0.45:
        k = popin(t, 0.45, 0.25) * (1 + 0.05 * math.sin(t * 9))
        blit(fg, fx.big('badge', 'VS', '#ffd23f', '#1a1a2e', '#e8b923', s=10), LINE_X, GROUND - 205, k, k, -4, anchor='center')
    if t >= 0.24:
        k = popin(t, 0.24, 0.25)
        blit(fg, fx.big('tag', '1963', '#fff6e0', '#1a1a2e', s=9), LINE_X, 790, k, k, 3 * math.sin(t * 4), anchor='center')
    if t >= 2.36:                                                                       # 'buy': a dollar sign over the red car
        k = popin(t, 2.36, 0.22)
        blit(fg, fx.big('glyph', '$', '#3cc85a', s=14), rx, GROUND - 330, k, k, 8 * math.sin(t * 7), anchor='center')
        fx.ring(fg, t, 2.36, rx, GROUND - 330, (60, 200, 90), life=0.3, r1=200)
    fx.sparkles(fg, t, LINE_X, GROUND - 200, 900, 300, n=7, seed=3) if t > 0.45 else None
    GAR.reflect(img, fg)
    return finish(img, fg, CAM1, t)


def overlay(cv, t):
    title(cv, t, 0.05, 2.5, 'Ford wanted', WHITE, 470, 104, -2)
    title(cv, t, 0.3, 2.5, 'Ferrari.', RED, 600, 136, 3)


# ================================================================== shot 2: 22 days of talks, a huge offer
DESK = GROUND - 150
def cal_day(t): return max(1, min(22, int(1 + 21 * io(prog(t, 3.35, 0.74)))))
P2 = Presenter([
    (3.15, dict(path=Track([(3.15, (1300, 300)), (3.55, (900, GROUND), 'oc')]), size=7, legs='auto', arms='fly', expr='talk', face=-1, ground=None)),
    (3.55, dict(ground=GROUND, squash=True, arms='point', point=(330, DESK - 260), look=(330, DESK - 260), expr='smile', face=None)),
    (5.19, dict(arms='present', point=None, look=(640, DESK - 120), expr='grin')),
    (6.17, dict(arms='shock', expr='wow', squash=True)),
], words=WORDS, base_size=7)
CAM2 = Camera(W, H, [(3.2, (520, 900, 1.12)), (4.09, (380, 820, 1.32), 'io'), (5.0, (540, 880, 1.14), 'io'), (6.17, (600, 900, 1.2), 'io'), (6.7, (600, 900, 1.22))],
              kicks=[(3.55, 0.06, 900, 900), (4.09, 0.14, 330, 760), (4.49, 0.08, 330, 760), (5.68, 0.1, 640, 560), (6.17, 0.14, 640, DESK - 100)],
              shakes=[(6.17, 0.3, 10)])


def money_rows(t):
    return 0 if t < 5.19 else min(6, 1 + int(5 * oc(prog(t, 5.19, 0.9))))


def shot_deal(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    d = ImageDraw.Draw(fg)
    d.rectangle((120, DESK, 960, DESK + 30), fill=(120, 80, 52)); d.rectangle((120, DESK, 960, DESK + 6), fill=(170, 120, 80))
    for x in (150, 910): d.rectangle((x, DESK + 30, x + 24, GROUND), fill=(90, 60, 40))
    kc = popin(t, 3.25, 0.3)
    blit(fg, up(contract(), 8), 800, DESK, kc, kc, -4)
    if t >= 3.3:                                                                         # calendar flips to 22
        day = cal_day(t); k = popin(t, 3.3, 0.3) * (1 + 0.1 * math.exp(-(t - 4.09) * 8) * (t >= 4.09))
        blit(fg, up(calendar(day), 9), 330, DESK, k, k, 3 * math.sin(t * 3))
        if 3.35 <= t < 4.09 and int(t * 30) % 2: fx.dust(fg, t, t - 0.05, 330, DESK - 360, n=3, seed=int(t * 30), col=(250, 250, 246))
        fx.burst(fg, t, 4.09, 330, DESK - 190, GLOW, n=12, seed=4); fx.ring(fg, t, 4.09, 330, DESK - 190, GLOW, life=0.35, r1=300)
    if t >= 4.49:
        k = popin(t, 4.49, 0.25) * popout(t, 5.5)
        blit(fg, fx.big('tag', 'TALKS: 22 DAYS', '#fff6e0', '#1a1a2e', s=7), 400, 560, k, k, -4 + 2 * math.sin(t * 5), anchor='center')
    for i in range(money_rows(t)):                                                       # the offer piles up
        ti = 5.19 + i * 0.12
        blit(fg, up(money(), 8), 570 + 6 * ((i % 2) * 2 - 1), DESK - 70 * i - 300 * (1 - oc(prog(t, ti, 0.2))), 1, 1, 2 * ((i % 3) - 1))
        fx.dust(fg, t, ti + 0.2, 570, DESK - 70 * i, n=4, seed=40 + i, col=(170, 220, 160))
    if t >= 5.4: fx.sparkles(fg, t, 570, DESK - 260, 300, 340, n=6, seed=41)
    if t >= 5.68:                                                                         # hedge
        k = popin(t, 5.68, 0.25)
        blit(fg, fx.big('tag', 'REPORTEDLY', '#fff6e0', '#d6303a', s=8), 640, 440, k, k, 4 + 2 * math.sin(t * 6), anchor='center')
        fx.burst(fg, t, 5.68, 640, 440, RED, n=10, seed=42)
    if t >= 6.17:
        k = popin(t, 6.17, 0.25)
        blit(fg, fx.big('badge', '8 FIGURES', '#7fe3a0', '#1a1a2e', '#3cc85a', s=8), 480, 560, k, k, -3, anchor='center')
        fx.confetti(fg, t, 6.17, 560, 600, n=24, seed=43)
    P2.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM2, t)


# ================================================================== shot 3: he walks away; Ford builds the GT40
def red3_x(t):                                                                           # waits, turns at 'walked', drives off left
    return 760 if t < 8.35 else 760 - 1600 * ic(prog(t, 8.35, 0.9))
def gt_drop(t): return oc(prog(t, 9.7, 0.4))
P3 = Presenter([
    (6.65, dict(path=Track([(6.65, (-200, 500)), (7.05, (170, GROUND), 'oc')]), size=7, legs='auto', arms='fly', expr='talk', face=1, ground=None)),
    (7.05, dict(ground=GROUND, squash=True, arms='point', point=(760, GROUND - 200), look=(760, GROUND - 200), expr='think', face=None)),
    (8.23, dict(arms='shrug', point=None, expr='shock', squash=True)),
    (9.7, dict(arms='cheer', look=(620, GROUND - 200), expr='grin', squash=True)),
    (11.01, dict(arms='thumb', look=None, look_camera=True, expr='grin')),
], words=WORDS, base_size=7)
CAM3 = Camera(W, H, [(6.7, (600, 900, 1.16)), (7.47, (700, 960, 1.28), 'io'), (8.35, (560, 940, 1.12), 'io'), (9.6, (600, 920, 1.12)), (10.3, (620, 960, 1.24), 'io'), (11.7, (620, 940, 1.18))],
              kicks=[(6.8, 0.12, 700, 800), (7.47, 0.08, 760, 820), (8.23, 0.1, 760, 1000), (9.7, 0.16, 620, 1000), (10.26, 0.08, 620, 900), (11.01, 0.14, 620, 700)],
              shakes=[(6.8, 0.25, 10), (9.95, 0.3, 14)])


def shot_walk(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    if t < 7.3:                                                                          # the deal tears in two
        u = oc(prog(t, 6.8, 0.5)); half = up(contract(), 8)
        hw = half.width // 2
        lft, rgt = half.crop((0, 0, hw, half.height)), half.crop((hw, 0, half.width, half.height))
        a = 1 - prog(t, 6.95, 0.35)
        if a > 0:
            for piece, sg in ((lft, -1), (rgt, 1)):
                p = piece.copy(); p.putalpha(p.getchannel('A').point(lambda v: int(v * a)))
                blit(fg, p, 640 + sg * (hw / 2 + 120 * u), 700 + 260 * u * u, 1, 1, sg * -30 * u, anchor='center')
        fx.burst(fg, t, 6.8, 640, 600, RED, n=12, seed=50)
    x = red3_x(t)
    if x > -600:
        fx.contact_shadow(fg, x, GROUND, 620, s=S, alpha=130)
        flip = t >= 8.35
        jump = 30 * math.sin(math.pi * prog(t, 8.23, 0.25))
        blit(fg, up(rc('p3', x if flip else 0, flip=flip), 6), x, GROUND - jump)
        if t >= 8.35:
            for k in range(6): fx.puff(fg, t, 8.4 + k * 0.1, x + 320, GROUND - 30, seed=51 + k, life=0.6, size=0.8, drift=(220, -80))
    dg.label(fg, t, 7.47, 'ENZO FERRARI', (760, GROUND - 260), (720, 560), '#ffffff', '#d6303a', '#d6d9e2', s=7, t1=8.4)
    if t >= 8.4:
        k = popin(t, 8.4, 0.25) * popout(t, 9.5)
        blit(fg, fx.big('tag', 'NO DEAL', '#fff6e0', '#d6303a', True, s=9), 600, 560, k, k, -6, anchor='center')
    if t >= 9.13:                                                                       # the GT40 drops into the bay
        u = gt_drop(t)
        gx, gy = 620, lerp(-200, GROUND, u)
        if u >= 1: fx.contact_shadow(fg, gx, GROUND, 680, s=S, alpha=150)
        fx.rays(fg, t, 10.1, gx, GROUND - 150, GLOW, life=0.45, r=440)
        s = wob(t, (10.1,), 0.09)
        blit(fg, up(rc('gt', 0), 6), gx, gy, *s)
        fx.dust(fg, t, 10.1, gx, GROUND - 10, n=14, seed=55)
        fx.ring(fg, t, 10.1, gx, GROUND - 120, (255, 255, 255), life=0.3, r1=420)
        if 9.13 <= t < 9.75:                                                            # welding sparks while it is built
            fx.burst(fg, t, 9.13 + int((t - 9.13) * 10) / 10, 620, 600, GLOW, n=8, r0=40, r1=200, seed=int(t * 10))
    photo(fg, t, 8.62, 9.12, 'p3', 560, 940, 600, 420, 3, 'THE RIVAL: FERRARI 330 P3', focus=(0.5, 0.55), pix=3)
    dg.label(fg, t, 10.26, 'RACE CAR', (420, GROUND - 160), (460, 640), '#ffffff', '#1a1a2e', '#d6d9e2', s=7, t1=11.0)
    if t >= 11.01:
        k = popin(t, 11.01, 0.25)
        blit(fg, fx.big('badge', 'GT40', '#ffd23f', '#1a1a2e', '#e8b923', s=12), 620, 600, k, k, -3 + 2 * math.sin(t * 5), anchor='center')
        fx.burst(fg, t, 11.01, 620, 600, GLOW, n=14, seed=56); fx.sparkles(fg, t, 620, GROUND - 160, 700, 220, n=8, seed=57)
    P3.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM3, t)


# ================================================================== shot 4: Le Mans at night
RACE_Y = TRACK_Y + 40
def scroll4(t): return (t - 11.7) * 2600
def gt4_x(t): return lerp(240, 720, io(prog(t, 12.0, 1.2)))
def p34_x(t): return lerp(620, 380, io(prog(t, 12.0, 1.2)))
CAM4 = Camera(W, H, [(11.7, (540, 1000, 1.18)), (12.37, (560, 1080, 1.3), 'io'), (13.0, (620, 1060, 1.22), 'io'), (13.6, (620, 1040, 1.26))],
              kicks=[(12.0, 0.1, 540, 1100), (12.37, 0.12, 560, 1100), (12.93, 0.14, 720, 1100)], shakes=[(11.7, 1.9, 5)])


def shot_race(t):
    sc = scroll4(t)
    img = circuit(t, sc); fg = layer()
    blit(fg, fx.big('tag', 'LE MANS', '#fff6e0', '#1a1a2e', s=7), 540 - (sc * 0.25) % 2400 + 1200, TRACK_Y - 520, anchor='center')
    for kind, x, y, dist in (('p3', p34_x(t), RACE_Y - 70, sc), ('gt', gt4_x(t), RACE_Y + 40, sc * 1.05)):
        fx.contact_shadow(fg, x, y, 560, s=S, alpha=150)
        bob = 3 * math.sin(t * 40 + x)
        beam(fg, x + 250, y - 70)
        blit(fg, up(rc(kind, dist, lights=True), 5), x, y + bob)
        fx.puff(fg, t, t - 0.1, x - 270, y - 30, seed=int(t * 20) % 50 + (0 if kind == 'gt' else 50), life=0.5, size=0.5, drift=(-500, -20), col=(120, 120, 130))
    fx.speed_lines(fg, 0.55, int(t * 12) % 5, col=(200, 204, 220))
    if t >= 12.0:                                                                         # chequered flag on the pit wall
        k = popin(t, 12.0, 0.25)
        blit(fg, up(flag(int(t * 14) % 8), 9), 140, TRACK_Y - 140, k, k, -8)
    dg.label(fg, t, 12.37, 'TAKES ON FERRARI', (gt4_x(t) + 100, RACE_Y - 200), (620, 760), '#7fe3a0', '#1a1a2e', '#3cc85a', s=7)
    if t >= 12.93: fx.sparkles(fg, t, gt4_x(t), RACE_Y - 160, 600, 200, n=8, seed=60)
    fx.burst(fg, t, 12.93, gt4_x(t) + 200, RACE_Y - 120, GLOW, n=12, seed=61)
    photo(fg, t, 12.95, 13.55, 'race2', 540, 820, 620, 440, -3, 'LE MANS 1966: THE WINNING CAR', focus=(0.48, 0.62), zoom=1.6, pix=4)
    return finish(img, fg, CAM4, t, rim=False)


# ================================================================== shot 5: 1966, the victory lap
def lap_x(t): return -500 + ((t - 13.6) * 1250) % 2100
P5 = Presenter([
    (13.55, dict(path=Track([(13.55, (1300, 400)), (13.95, (880, GROUND), 'oc')]), size=7, legs='auto', arms='fly', expr='grin', face=-1, ground=None)),
    (13.95, dict(ground=GROUND, squash=True, arms='cheer', look=(540, 420), expr='grin', face=None)),
    (14.88, dict(arms='thumb', look=None, look_camera=True, squash=True)),
], words=WORDS, base_size=7)
CAM5 = Camera(W, H, [(13.6, (540, 860, 1.12)), (14.88, (540, 820, 1.08), 'io'), (16.0, (540, 840, 1.14))],
              kicks=[(13.8, 0.14, 540, 420), (14.88, 0.1, 540, 700), (15.49, 0.12, 540, 700)])
YEARS = [('1966', 14.88), ('1967', 15.06), ('1968', 15.24), ('1969', 15.42)]


def shot_win(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    fx.rays(fg, t, 13.8, 540, 420, GLOW, hold=True, r=600)
    if t >= 13.7:                                                                        # banner drops
        y = lerp(-200, 430, oc(prog(t, 13.7, 0.35)))
        blit(fg, fx.big('badge', '1966', '#ffd23f', '#1a1a2e', '#e8b923', s=16), 540, y, 1, 1, -2 + 2 * math.sin(t * 3), anchor='center')
        fx.burst(fg, t, 13.8, 540, 430, GLOW, n=16, seed=70)
    blit(fg, up(trophy(), 9), 200, GROUND - 40, 1, 1, 0) if t >= 14.2 else None
    fx.ring(fg, t, 14.2, 200, GROUND - 170, GLOW, life=0.3, r1=200)
    x = lap_x(t)
    fx.contact_shadow(fg, x, GROUND + 60, 560, s=S, alpha=140)
    blit(fg, up(rc('gt', (t - 13.6) * 1250, lights=True), 5), x, GROUND + 60)
    fx.puff(fg, t, t - 0.1, x - 270, GROUND + 20, seed=int(t * 20) % 40, life=0.5, size=0.6, drift=(-400, -40))
    for i, (yr, ts) in enumerate(YEARS):                                                 # four Le Mans wins in a row
        if t >= ts:
            k = popin(t, ts, 0.22)
            blit(fg, fx.big('tag', yr, '#fff6e0', '#3cc85a', s=8), 290 + (i % 2) * 360, 690 + (i // 2) * 125, k, k, 3 * math.sin(t * 5 + i), anchor='center')
            fx.burst(fg, t, ts, 290 + (i % 2) * 360, 690 + (i // 2) * 125, (60, 200, 90), n=8, r0=60, r1=180, seed=71 + i)
    dg.label(fg, t, 15.5, 'LE MANS WINS', (460, 800), (460, 960), '#7fe3a0', '#1a1a2e', '#3cc85a', s=7) if t >= 15.5 else None
    fx.confetti(fg, t, 13.8, 540, 500, n=40, seed=72)
    fx.sparkles(fg, t, 540, 600, 900, 300, n=8, seed=73)
    P5.draw(fg, t)
    GAR.reflect(img, fg)
    photo(fg, t, 14.0, 14.85, 'gt40', 560, 1000, 600, 430, -4, 'A 1966 LE MANS GT40 MK II', focus=(0.27, 0.32), zoom=0.3, pix=6)
    return finish(img, fg, CAM5, t)


shot_teaser, TEASE_CUES = kit.teaser(16.0, WORDS)

# ================================================================== shots + transitions
SHOTS = [(-1.0, shot_faceoff), (3.2, shot_deal), (6.7, shot_walk), (11.7, shot_race), (13.6, shot_win), (16.0, shot_teaser)]
TRANS = {1: (3.2, 3.4, 'whip', dict(dx=1)), 2: (6.7, 6.9, 'push', None), 3: (11.7, 11.9, 'whip', dict(dx=-1)),
         4: (13.6, 13.8, 'iris', (gt4_x(13.6), RACE_Y - 100)), 5: (16.0, 16.2, 'whip', dict(dx=1))}
KEYCOL = {'1963': YEL, 'ferrari': RED, '22': YEL, 'days': YEL, 'reportedly': YEL, 'huge': GRN, 'walked': RED, 'away': RED,
          'gt40': YEL, 'took': GRN, 'mans': GRN, '1966': YEL, 'winning': YEL}
CUES = [
    (0.0, 'whoosh', 0.5), (0.05, 'vroom', 0.5), (0.24, 'pop', 0.7), (0.45, 'crash', 0.35), (0.46, 'stamp', 0.7), (0.5, 'sparkle', 0.6),
    (1.6, 'vroom', 0.8), (2.36, 'cha_ching', 0.6), (2.67, 'vroom', 0.8),
    (3.3, 'pop', 0.6), (3.55, 'thump', 0.5)] + [(3.35 + i * 0.075, 'click', 0.25) for i in range(10)] + [
    (4.09, 'ding', 0.8), (4.11, 'sparkle', 0.5), (4.49, 'pop', 0.6), (5.19, 'coin', 0.6), (5.5, 'coin', 0.5), (5.68, 'stamp', 0.6),
    (6.17, 'cha_ching', 0.8), (6.19, 'confetti', 0.5),
    (6.8, 'crash', 0.45), (6.82, 'whoosh', 0.5), (7.47, 'pop', 0.6), (8.23, 'screech', 0.7), (8.4, 'vroom', 0.9), (8.42, 'buzzer', 0.4),
    (9.13, 'click', 0.5), (9.3, 'click', 0.5), (9.5, 'click', 0.5), (9.7, 'fall', 0.5), (10.1, 'boom', 0.5), (10.12, 'sparkle', 0.6),
    (10.26, 'pop', 0.6), (11.01, 'ding', 0.8), (11.03, 'sparkle', 0.7),
    (11.75, 'vroom', 0.9), (12.0, 'pop', 0.5), (12.37, 'vroom', 0.7), (12.93, 'whoosh', 0.7), (12.95, 'sparkle', 0.7),
    (13.7, 'fall', 0.5), (13.8, 'stamp', 0.8), (13.82, 'confetti', 0.8), (14.0, 'pop', 0.6), (14.2, 'ding', 0.6),
] + [(ts, 'pop', 0.7) for _, ts in YEARS] + [(15.49, 'ding', 0.8), (15.5, 'sparkle', 0.7)] + TEASE_CUES

kit.setup(HERE, WORDS, DUR, END_T, SHOTS, TRANS, CUES, KEYCOL, overlay=overlay, bar_car='blue', gauge=True, loud=True)

if __name__ == '__main__':
    kit.main()
