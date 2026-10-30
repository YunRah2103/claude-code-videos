"""Pixel sprites for the 2025 car-record episodes: supercar, endurance racer, muscle coupe, EV saloons, V12, motor,
battery, chargers, plug and socket, drag-strip light tree, year calendar, trophy, chequered flag.

All are plain RGBA grids (nose right, no badges, logos or lettering beyond numbers): scale with grid.up(img, s).
The racer, trophy, flag and calendar come from videos/ford-vs-ferrari; battery, bolt, chargers from ioniq-18-minutes;
motor from plaid-two-seconds.
"""
import math
from functools import lru_cache
from PIL import Image, ImageDraw
from .grid import Grid, text_width, outline

NAVY = (26, 26, 46)
DARK = (34, 36, 46)
GLASS, GLASS_HI = (60, 74, 96), (150, 186, 214)
TEAL = (0, 170, 160)


def ptext(s, col, ol=False):
    g = Grid(text_width(s) + 2, 9); g.text(1, 1, s, col if isinstance(col, str) else '#%02x%02x%02x' % col)
    return g.image(outline=ol)


def _shade(c, k): return tuple(max(0, min(255, int(v * k))) for v in c)


def wheel(d, cx, cy, r, spin, rim=(200, 204, 214), spokes=6):
    """Low-profile tyre with a slotted alloy that turns with `spin`."""
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(26, 27, 32))
    d.ellipse((cx - r + 1.5, cy - r + 1.5, cx + r - 1.5, cy + r - 1.5), fill=(40, 42, 48))
    rr = r * 0.62
    d.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), fill=rim)
    d.arc((cx - rr, cy - rr, cx + rr, cy + rr), 200, 330, fill=_shade(rim, 1.25))
    for k in range(spokes):
        a = math.radians(k * 360 / spokes + spin)
        d.line([(cx + 1.2 * math.cos(a), cy + 1.2 * math.sin(a)), (cx + rr * math.cos(a), cy + rr * math.sin(a))], fill=_shade(rim, 0.6))
    d.ellipse((cx - 1.5, cy - 1.5, cx + 1.5, cy + 1.5), fill=(230, 232, 238))


def _body(d, pts, col, hi_n):
    d.polygon(pts, fill=col)
    d.line(pts[1:hi_n], fill=_shade(col, 1.45))


def _arches(d, xs, y, r):
    for cx in xs: d.pieslice((cx - r - 2, y - r - 2, cx + r + 2, y + r + 2), 180, 360, fill=(14, 14, 20))


# ------------------------------------------------------------------ cars (nose right)
SUPER = {   # body colour per supercar kind
    'wedge': (120, 200, 60),     # sharp V12 hybrid wedge (lime)
    'old': (60, 62, 74),         # its predecessor, drawn as a dark silhouette
    'rosso': (214, 36, 44),      # mid-engined plug-in hybrid (red)
}


@lru_cache(None)
def supercar(kind='wedge', spin=0, lights=False, port=0.0):
    """Low mid-engined supercar (108x36). 'wedge' and 'old' are sharp, angular wedges with Y-shaped lamp hints;
    'rosso' is curvier with a flying-buttress cabin. `port` (0..1) lights a charge flap on the front wing."""
    col = SUPER[kind]
    img = Image.new('RGBA', (108, 36), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    if kind == 'rosso':
        pts = [(3, 20), (5, 14), (22, 13), (38, 8), (56, 7), (68, 12), (88, 17), (102, 21), (105, 25), (104, 28), (3, 28)]
        win = [(41, 10), (55, 9), (64, 13), (36, 14)]
    else:
        pts = [(3, 19), (4, 14), (24, 13), (40, 8), (56, 8), (66, 12), (104, 21), (105, 25), (103, 28), (3, 28)]
        win = [(42, 10), (55, 10), (63, 13), (35, 15)]
    _body(d, pts, col, 7)
    d.rectangle((4, 23, 103, 25), fill=_shade(col, 0.72)); d.rectangle((4, 26, 103, 28), fill=_shade(col, 0.5))
    d.polygon(win, fill=GLASS); d.line([win[0], win[1]], fill=GLASS_HI)
    d.polygon([(26, 17), (36, 16), (33, 22), (24, 22)], fill=_shade(col, 0.45))                  # side intake
    d.line([(24, 22), (34, 22)], fill=(10, 10, 16))
    if kind != 'rosso':                                                                      # Y-shaped lamp hints
        for x0, c in ((96, (255, 250, 210) if lights else (220, 226, 220)), (5, (255, 70, 70) if lights else (170, 30, 36))):
            d.line([(x0, 20), (x0 + 3, 22), (x0 + 6, 20)], fill=c); d.line([(x0 + 3, 22), (x0 + 3, 24)], fill=c)
    else:
        d.polygon([(94, 19), (101, 21), (101, 23), (95, 22)], fill=(255, 250, 210) if lights else (220, 226, 220))
        d.rectangle((3, 18, 6, 20), fill=(255, 70, 70) if lights else (170, 30, 36))
    if port > 0:
        g = int(90 + 165 * port); d.rectangle((78, 17, 82, 20), fill=(40, g, min(255, g + 20)))
    d.rectangle((2, 25, 6, 28), fill=DARK); d.rectangle((99, 26, 107, 28), fill=DARK)               # diffuser + splitter
    _arches(d, (22, 86), 28, 8)
    for cx in (22, 86): wheel(d, cx, 28, 8.4, spin, (60, 62, 70) if kind == 'old' else (200, 204, 214))
    return outline(img)


RACER = ((40, 72, 150), (28, 52, 112), (98, 136, 214), (18, 32, 72), (236, 238, 244))


@lru_cache(None)
def racer(num='68', spin=0, lights=False, old=False):
    """Mid-engined endurance racer (104x36): low flat coupe, Kamm tail, twin stripes, number roundel.
    old=True is the 1960s shape (no wing, rounder tail)."""
    body, shade, hi, deep, stripe = RACER
    img = Image.new('RGBA', (104, 36), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    pts = [(2, 12), (10, 10), (34, 9), (40, 4), (60, 4), (72, 12), (88, 15), (99, 19), (102, 23), (101, 27), (2, 27)]
    d.polygon(pts, fill=body); d.line(pts[1:-3], fill=hi)
    d.rectangle((3, 22, 100, 24), fill=shade); d.rectangle((3, 25, 100, 27), fill=deep)
    win = [(42, 6), (58, 6), (67, 12), (45, 12)]
    d.polygon(win, fill=(120, 156, 186)); d.line([win[0], win[1]], fill=(200, 226, 244))
    for dy in (0, 2): d.line([(p[0], p[1] + dy) for p in pts[1:-3]], fill=stripe)
    d.line([(36, 12), (36, 24)], fill=deep); d.line([(68, 13), (68, 24)], fill=deep)
    if not old:                                                                              # rear wing on stalks
        d.rectangle((0, 3, 14, 5), fill=DARK); d.rectangle((6, 5, 8, 10), fill=DARK)
    d.ellipse((43, 13, 61, 25), fill=(244, 244, 238)); d.ellipse((43, 13, 61, 25), outline=deep)
    d.polygon([(92, 16), (98, 18), (99, 20), (93, 19)], fill=(255, 250, 210) if lights else (214, 220, 214))
    d.rectangle((2, 15, 5, 18), fill=(255, 70, 70) if lights else (180, 30, 36))
    d.rectangle((96, 25, 103, 27), fill=DARK)
    _arches(d, (20, 84), 27, 8)
    for cx in (20, 84): wheel(d, cx, 27, 8.4, spin, (200, 204, 214))
    n = ptext(num, NAVY); img.alpha_composite(n, (52 - n.width // 2, 15))
    return outline(img)


@lru_cache(None)
def muscle(spin=0, lights=False, launch=0.0):
    """Two-door muscle coupe (104x40): long bonnet with a raised scoop, upright tail, fat rear drag slicks.
    `launch` (0..1) lifts the nose for a wheelie-ish squat."""
    body, hi = (232, 120, 30), (255, 186, 110)
    img = Image.new('RGBA', (104, 42), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    pts = [(2, 16), (4, 13), (26, 12), (36, 4), (58, 4), (66, 12), (98, 14), (101, 17), (101, 29), (2, 29)]
    _body(d, pts, body, 7)
    d.rectangle((3, 24, 100, 26), fill=_shade(body, 0.72)); d.rectangle((3, 27, 100, 29), fill=_shade(body, 0.5))
    d.polygon([(38, 6), (56, 6), (63, 12), (30, 12)], fill=GLASS); d.line([(38, 6), (56, 6)], fill=GLASS_HI)
    d.line([(47, 6), (47, 12)], fill=_shade(body, 0.5))
    d.rectangle((72, 10, 84, 12), fill=DARK); d.rectangle((73, 9, 83, 10), fill=(60, 62, 74))      # bonnet scoop
    d.rectangle((2, 13, 12, 14), fill=_shade(body, 0.6))                                         # ducktail spoiler
    d.rectangle((95, 16, 100, 20), fill=(255, 250, 210) if lights else (210, 214, 210))
    d.rectangle((2, 16, 4, 20), fill=(255, 70, 70) if lights else (170, 30, 36))
    d.line([(10, 20), (96, 20)], fill=(20, 20, 26))                                              # side stripe
    _arches(d, (22, 84), 30, 10)
    wheel(d, 22, 31, 10.5, spin, (70, 72, 80), 5)                                                # fat slick
    wheel(d, 84, 31, 8.4, spin, (200, 204, 214), 5)
    img = outline(img)
    if launch: img = img.rotate(-4 * launch, resample=Image.NEAREST, center=(22, 31), expand=False)
    return img


@lru_cache(None)
def ev(kind='air', spin=0, lights=False, port=0.0):
    """Electric four-door (104x38). 'air': long sleek saloon with a full glass roof and a light-bar nose (silver);
    'sport': low four-door sports saloon with four-point lamps (white). `port` lights the charge flap."""
    img = Image.new('RGBA', (104, 38), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    if kind == 'air':
        body = (196, 202, 212)
        pts = [(3, 17), (6, 13), (20, 11), (32, 4), (66, 4), (80, 12), (98, 16), (101, 20), (101, 27), (3, 27)]
        win = [(34, 6), (64, 6), (75, 12), (26, 12)]
    else:
        body = (236, 238, 242)
        pts = [(3, 16), (6, 13), (24, 11), (36, 5), (60, 5), (74, 12), (96, 15), (101, 19), (101, 27), (3, 27)]
        win = [(38, 7), (58, 7), (68, 12), (31, 12)]
    _body(d, pts, body, 7)
    d.rectangle((4, 22, 100, 24), fill=_shade(body, 0.78)); d.rectangle((4, 25, 100, 27), fill=_shade(body, 0.55))
    d.polygon(win, fill=(40, 52, 70)); d.line([win[0], win[1]], fill=(120, 150, 190))
    mid = (win[0][0] + win[1][0]) // 2; d.line([(mid, win[0][1]), (mid, 12)], fill=_shade(body, 0.6))
    hl = (240, 248, 255) if lights else (200, 210, 220)
    if kind == 'air': d.line([(90, 17), (100, 19)], fill=hl)                                    # light bar
    else:
        for y in (16, 18): d.rectangle((94, y, 95, y), fill=hl); d.rectangle((97, y, 98, y), fill=hl)
    d.line([(3, 17), (10, 17)], fill=(255, 70, 70) if lights else (170, 30, 36))
    if port > 0 or kind == 'sport':
        g = int(70 + 185 * port); d.rectangle((84, 15, 88, 18), fill=(40, g, min(255, g + 20)))  # front-wing charge flap
    _arches(d, (21, 83), 27, 8)
    for cx in (21, 83): wheel(d, cx, 27, 8.4, spin, (170, 176, 188), 5)
    return outline(img)


# ------------------------------------------------------------------ powertrain
@lru_cache(None)
def v12(phase=-1, n=6):
    """V engine seen from above (64x42 for n=6 per bank, a V12; n=4 gives a V8): two banks either side of a long
    intake plenum with runners. The cylinder at index `phase` (0..2n-1, top bank then bottom) glows."""
    w = 10 + n * 9
    img = Image.new('RGBA', (w, 42), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rounded_rectangle((1, 3, w - 2, 39), 4, fill=(96, 100, 112)); d.line([(3, 4), (w - 4, 4)], fill=(150, 156, 170))
    for bank, y in ((0, 6), (1, 30)):
        d.rectangle((3, y - 1, w - 4, y + 7), fill=(130, 30, 34)); d.line([(4, y - 1), (w - 5, y - 1)], fill=(200, 70, 70))
        for i in range(n):
            x = 5 + i * 9; hot = i + bank * n == phase
            d.rounded_rectangle((x, y, x + 6, y + 6), 1, fill=(255, 210, 90) if hot else (176, 44, 48))
            d.point((x + 1, y + 1), fill=(255, 240, 200) if hot else (230, 110, 110))
            d.rectangle((x + 2, y + (7 if bank == 0 else -4), x + 4, y + (10 if bank == 0 else -1)), fill=(60, 64, 76))   # runner
    d.rounded_rectangle((4, 17, w - 5, 25), 3, fill=(60, 64, 76)); d.line([(6, 18), (w - 7, 18)], fill=(120, 126, 138))   # plenum
    d.rectangle((w // 2 - 6, 19, w // 2 + 5, 23), fill=(40, 42, 52))
    d.rectangle((w - 4, 14, w - 1, 28), fill=(70, 74, 86))                                   # front pulley housing
    return outline(img)


@lru_cache(None)
def motor(on=0.0):
    """Electric motor (26x22): finned can, copper windings window, glowing when `on` (0..1)."""
    img = Image.new('RGBA', (26, 22), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 2, 21, 21), 4, fill=(120, 126, 138))
    for y in range(4, 21, 3): d.line([(1, y), (20, y)], fill=(150, 156, 170))
    d.rectangle((21, 9, 25, 13), fill=(200, 204, 214))
    g = int(80 + 175 * on)
    d.rectangle((6, 7, 15, 16), fill=(min(255, 150 + g // 3), min(255, 80 + g // 2), 40))
    for x in range(7, 15, 2): d.line([(x, 8), (x, 15)], fill=(min(255, 200 + g // 5), min(255, 120 + g // 2), 60))
    if on > 0.5: d.rectangle((9, 0, 12, 2), fill=(255, 230, 90))
    return outline(img)


# ------------------------------------------------------------------ charging
@lru_cache(None)
def battery(level=0.1):
    """Upright battery (34x58); cells fill bottom-up, red/yellow/green by level."""
    img = Image.new('RGBA', (34, 58), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rectangle((11, 0, 22, 4), fill=(170, 176, 188))
    d.rounded_rectangle((0, 4, 33, 57), 4, fill=(60, 64, 76)); d.rounded_rectangle((3, 7, 30, 54), 2, fill=(20, 21, 28))
    col = (224, 48, 58) if level < 0.25 else (255, 196, 40) if level < 0.6 else (60, 200, 90)
    for i in range(round(level * 10)):
        y1 = 52 - i * 4.6; d.rectangle((5, y1 - 3, 28, y1), fill=col); d.line([(5, y1 - 3), (28, y1 - 3)], fill=_shade(col, 1.3))
    return outline(img)


@lru_cache(None)
def bolt(col='#ffd23f'):
    img = Image.new('RGBA', (12, 18), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.polygon([(7, 0), (1, 10), (5, 10), (3, 17), (11, 6), (7, 6), (9, 0)], fill=col)
    return outline(img)


@lru_cache(None)
def charger(screen=0, plate=''):
    """Tall fast charger (32x88): teal-trimmed pillar, screen with a bolt, holster, optional number plate."""
    img = Image.new('RGBA', (32, 88), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rectangle((2, 0, 29, 83), fill=(220, 224, 232)); d.rectangle((2, 0, 29, 5), fill=TEAL); d.line([(3, 6), (3, 82)], fill=(250, 250, 252))
    d.rectangle((6, 12, 25, 32), fill=(20, 21, 28)); d.rectangle((8, 14, 23, 30), fill=(30, 60, 70) if not screen else (40, 120, 110))
    d.polygon([(17, 15), (11, 23), (15, 23), (13, 29), (20, 20), (16, 20), (18, 15)], fill=(255, 210, 63) if screen else (90, 100, 90))
    d.rectangle((20, 40, 28, 52), fill=(60, 64, 76))
    d.rectangle((0, 83, 31, 87), fill=(90, 94, 106))
    img = outline(img)
    if plate:
        g = Grid(text_width(plate) + 2, 7); g.rect(0, 0, text_width(plate) + 1, 6, '#1a1a2e'); g.text(1, 1, plate, '#ffd23f')
        t = g.image(outline=False); img.paste(t, (16 - t.width // 2, 60), t)
    return img


@lru_cache(None)
def wallbox():
    """Small slow wallbox (24x60) on a post, coiled cable."""
    img = Image.new('RGBA', (24, 60), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rectangle((10, 26, 13, 59), fill=(120, 126, 138))
    d.rounded_rectangle((1, 2, 22, 26), 3, fill=(200, 204, 214)); d.rectangle((6, 8, 17, 14), fill=(40, 60, 50)); d.rectangle((8, 10, 11, 12), fill=(60, 200, 90))
    for k in range(3): d.ellipse((4 + k, 16 + k * 2, 19 - k, 24 + k), outline=(40, 42, 52))
    return outline(img)


@lru_cache(None)
def socket(lit=False):
    """Wall socket plate (22x22) with two pin holes; glows green when `lit`."""
    img = Image.new('RGBA', (22, 22), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, 21, 21), 3, fill=(236, 236, 240)); d.line([(2, 1), (19, 1)], fill=(255, 255, 255))
    d.ellipse((4, 4, 17, 17), fill=(200, 204, 214))
    for x in (7, 13): d.rectangle((x, 9, x + 1, 12), fill=NAVY)
    d.rectangle((9, 18, 12, 19), fill=(60, 220, 110) if lit else (110, 116, 126))
    return outline(img)


@lru_cache(None)
def plug():
    """Charging plug head (18x12), pins pointing right, cable stub left."""
    img = Image.new('RGBA', (18, 12), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rectangle((0, 5, 4, 7), fill=(30, 32, 40))
    d.rounded_rectangle((4, 1, 14, 11), 2, fill=(44, 46, 58)); d.line([(5, 2), (13, 2)], fill=(90, 96, 110))
    for y in (4, 7): d.rectangle((14, y, 17, y + 1), fill=(220, 190, 90))
    return outline(img)


def cable(d, a, b, sag=60, col=(30, 32, 40), w=12):
    """Draw a sagging cable (screen px) from a to b on an ImageDraw."""
    pts = [(a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u + sag * math.sin(math.pi * u)) for u in [i / 16 for i in range(17)]]
    d.line(pts, fill=col, width=w, joint='curve')


# ------------------------------------------------------------------ racing props
@lru_cache(None)
def light_tree(stage=0):
    """Drag-strip light tree (20x60): pre-stage/stage bulbs, three ambers, a green, a red. stage 0 off, 1..3 ambers,
    4 green."""
    img = Image.new('RGBA', (20, 62), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rectangle((8, 40, 11, 61), fill=(120, 126, 138)); d.rounded_rectangle((1, 0, 18, 46), 3, fill=(40, 42, 52))
    for i, y in enumerate((3, 8)): d.ellipse((5, y, 14, y + 3), fill=(255, 244, 200) if stage else (70, 70, 60))
    for i in range(3):
        d.ellipse((5, 14 + i * 7, 14, 19 + i * 7), fill=(255, 176, 30) if stage >= i + 1 and stage < 4 else (90, 70, 30))
    d.ellipse((5, 35, 14, 40), fill=(60, 230, 90) if stage >= 4 else (30, 70, 40))
    d.ellipse((5, 41, 14, 45), fill=(80, 30, 30))
    return outline(img)


@lru_cache(None)
def flag(ph):
    """Chequered flag (26x22 incl. pole) whose cloth ripples with phase ph (0..7)."""
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


@lru_cache(None)
def year_cal(year):
    """Desk calendar (56x44) showing a year in big digits under a red binder header."""
    img = Image.new('RGBA', (56, 44), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rectangle((0, 3, 55, 43), fill=(250, 250, 246)); d.rectangle((0, 3, 55, 11), fill=(214, 48, 58))
    d.rectangle((0, 40, 55, 43), fill=(222, 222, 216))
    for x in (12, 42): d.rectangle((x, 0, x + 1, 6), fill=(120, 124, 134))
    n = ptext(str(year), NAVY); n = n.resize((n.width * 2, n.height * 2), Image.NEAREST)
    img.alpha_composite(n, (28 - n.width // 2, 17))
    return outline(img)
