"""Pixel props for the 'car stuff, explained' dashboard episodes (red-zone, fuel-cap-light, windscreen-glass).

Every sprite is drawn on a small pixel grid and returned as RGBA; scale it with pixanim.grid.up(img, s) (nearest).
    rpm_gauge(deg, ring)        rev counter with a red zone; ring 0..1 lights a red glow over the red section
    warn_lamp(on)               engine warning light (amber when on)
    fuel_cap(rot, door)         car rear quarter, fuel flap open, cap face-on (CAP_XY), turned by rot degrees
    glass_layers(crack, stop, shards)  glass / plastic / glass cutaway; crack stops at the plastic, pieces stay stuck
    windscreen(crack, clear, wiper)  windscreen front view: stone chip, star crack -> spiderweb, see-through glass, wipers
    fuel_cut()                  fuel pump icon with a red slash
    tick(on)                    small green tick in a box ('drive' marks)
    pill(cv, t, t0, t1, ...)    pixel callout pill with a leader line (pixanim.diagram.label), registered for the safe-zone check
Needle angles are maths degrees: 225 = zero, sweeping clockwise to -45 (same as pixanim.dash).
"""
import math, random
from functools import lru_cache
from PIL import Image, ImageDraw
from pixanim.dash import _gauge_face, _text, NEEDLE, NEEDLE_HI, RED
from pixanim.grid import text_width
from pixanim.fx import big
from pixanim import diagram as dg
from . import overlays as ov

AMBER, AMBER_DIM = (255, 150, 30), (70, 52, 30)
RED_FROM = 6.5                                   # red zone starts at 6.5 of 8 majors (same dial as the dashboard)
RED_DEG = 225 - 270 * RED_FROM / 8               # needle angle at the start of the red zone


def rpm_deg(frac): return 225 - 270 * frac        # 0..1 of full scale -> needle angle


@lru_cache(64)
def _face(r):
    n = 2 * r + 12
    img = Image.new('RGBA', (n, n), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    _gauge_face(d, n // 2, n // 2, r, red_from=RED_FROM, label='RPM', majors=9)
    return img


def rpm_gauge(deg, ring=0.0, r=44):
    img = _face(r).copy(); d = ImageDraw.Draw(img); c = img.width // 2
    if ring > 0.01:                               # pulsing red glow over the red section, outside and inside the bezel
        a = int(80 + 175 * ring)
        for w, rr in ((3, r + 4), (2, r - 9)):
            d.arc((c - rr, c - rr, c + rr, c + rr), 360 - RED_DEG - 4, 405 + 4, fill=RED + (a,), width=w)
    a = math.radians(deg)
    tip = (c + (r - 9) * math.cos(a), c - (r - 9) * math.sin(a)); tail = (c - 6 * math.cos(a), c + 6 * math.sin(a))
    d.line((tail, tip), fill=(120, 30, 10), width=4); d.line((tail, tip), fill=NEEDLE, width=2)
    d.line(((c + tip[0]) / 2, (c + tip[1]) / 2, *tip), fill=NEEDLE_HI, width=1)
    d.ellipse((c - 5, c - 5, c + 5, c + 5), fill=(40, 42, 50)); d.ellipse((c - 3, c - 3, c + 3, c + 3), fill=(90, 96, 110))
    for k in range(118, 152, 3):                  # glass glare
        b = math.radians(k); d.point((c + (r - 7) * math.cos(b), c - (r - 7) * math.sin(b)), fill=(255, 255, 255, 70))
    return img


ENGINE_ICON = ["000111100000", "000010000000", "011111110100", "110000011100", "100000010100",
               "100000010100", "110000011100", "011111110000"]


@lru_cache(4)
def warn_lamp(on):
    img = Image.new('RGBA', (18, 14), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, 17, 13), 3, fill=(20, 21, 26), outline=(48, 50, 58))
    for j, row in enumerate(ENGINE_ICON):
        for i, b in enumerate(row):
            if b == '1': d.point((3 + i, 3 + j), fill=AMBER if on else AMBER_DIM)
    if on: d.point((4, 3), fill=(255, 220, 150))
    return img


def fuel_cap(rot=0.0, door=1.0, paint=(196, 40, 50)):
    """Car rear quarter (side window, trim, crease, wheel arch) with the filler flap swung open (door 0..1) and the cap
    face-on; rot turns the cap (knurled rim + grip bar). Cap centre at grid (CAP_XY)."""
    img = Image.new('RGBA', (96, 70), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    hi = tuple(min(255, c + 60) for c in paint); sh = tuple(c * 2 // 3 for c in paint); dk = tuple(c // 2 for c in paint)
    d.polygon([(0, 14), (10, 2), (80, 2), (95, 14)], fill=(30, 34, 44))                        # side window
    d.line((10, 3, 80, 3), fill=(26, 26, 46)); d.line((28, 4, 20, 13), fill=(90, 110, 130)); d.line((31, 4, 23, 13), fill=(60, 74, 90))
    d.rectangle((0, 14, 95, 15), fill=(150, 156, 168))                                         # chrome trim
    d.rectangle((0, 16, 95, 69), fill=paint)
    d.line((0, 17, 95, 17), fill=hi); d.line((0, 38, 95, 38), fill=hi); d.line((0, 39, 95, 39), fill=sh)  # crease
    d.ellipse((58, 48, 100, 90), fill=(16, 16, 20)); d.arc((56, 46, 102, 92), 180, 270, fill=sh, width=2)  # wheel arch + tyre
    d.ellipse((64, 54, 94, 84), fill=(36, 37, 43)); d.ellipse((72, 62, 86, 76), fill=(120, 126, 138))
    d.line((0, 68, 58, 68), fill=dk)
    cx, cy = CAP_XY
    d.ellipse((cx - 15, cy - 15, cx + 15, cy + 15), fill=(18, 19, 24), outline=dk)            # recess
    d.ellipse((cx - 12, cy - 12, cx + 12, cy + 12), fill=(60, 62, 70))                        # cap rim
    d.ellipse((cx - 10, cy - 10, cx + 10, cy + 10), fill=(34, 35, 41))
    for k in range(12):                                                                        # knurled edge turns with the cap
        b = math.radians(rot + k * 30)
        d.point((cx + 11 * math.cos(b), cy - 11 * math.sin(b)), fill=(130, 134, 146))
    b = math.radians(rot)
    for w in (-2, -1, 0, 1, 2):                                                                # grip bar
        ox, oy = -math.sin(b) * w * 0.8, -math.cos(b) * w * 0.8
        d.line((cx - 8 * math.cos(b) + ox, cy + 8 * math.sin(b) + oy, cx + 8 * math.cos(b) + ox, cy - 8 * math.sin(b) + oy),
               fill=(96, 100, 112) if abs(w) < 2 else (24, 25, 30))
    d.line((cx - 6 * math.cos(b), cy + 6 * math.sin(b), cx + 6 * math.cos(b), cy - 6 * math.sin(b)), fill=(170, 176, 188))
    fw = int(7 * door)                                                                         # flap swung open on its hinge (left)
    if fw > 1:
        d.polygon([(cx - 16, cy - 15), (cx - 16 - fw, cy - 18), (cx - 16 - fw, cy + 18), (cx - 16, cy + 15)], fill=hi, outline=sh)
        d.line((cx - 16, cy - 15, cx - 16, cy + 15), fill=(40, 40, 46))
    return img


CAP_XY = (34, 42)


GLASS, GLASS_HI, GLASS_SH = (150, 205, 230), (215, 240, 252), (96, 150, 180)
PVB, PVB_HI = (255, 196, 70), (255, 226, 140)


def _crack_path(seed, x0, y0, y1, jag=3):
    rnd = random.Random(seed); pts = [(x0, y0)]; x = x0
    for y in range(y0 + 2, y1 + 1, 2):
        x += rnd.choice((-1, 0, 1)) * (jag > 2) + rnd.choice((-1, 0, 0, 1)); pts.append((x, y))
    return pts


def glass_layers(crack=0.0, stop=0.0, t=0.0, w=140, layer_h=(16, 8, 16), shards=0.0):
    """Side cutaway of laminated glass. crack 0..1 runs a crack down through the top glass; stop 0..1 flashes the
    plastic where the crack is caught and fans the crack out sideways (it spreads, it does not go through)."""
    g1, p, g2 = layer_h; h = g1 + p + g2 + 4
    img = Image.new('RGBA', (w + 4, h), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    y = 2
    for hh, col, hi, sh in ((g1, GLASS, GLASS_HI, GLASS_SH), (p, PVB, PVB_HI, (200, 140, 40)), (g2, GLASS, GLASS_HI, GLASS_SH)):
        d.rectangle((2, y, w + 1, y + hh - 1), fill=col + (230,))
        d.line((2, y, w + 1, y), fill=hi); d.line((2, y + hh - 1, w + 1, y + hh - 1), fill=sh)
        if col == GLASS:                                                              # diagonal glints
            for gx in range(10 + int(t * 20) % 40, w, 40): d.line((gx, y + 2, gx + 4, y + hh - 3), fill=GLASS_HI + (160,))
        y += hh
    d.rectangle((0, 0, w + 3, h - 1), outline=(26, 26, 46))
    if stop > 0.01:                                                                    # plastic layer catches it: glow
        a = int(120 * stop * (0.7 + 0.3 * math.sin(t * 12)))
        d.rectangle((2, 2 + g1, w + 1, 2 + g1 + p - 1), outline=(255, 255, 255, a))
    if crack > 0.01:
        cx = w // 2; depth = int((g1 - 1) * min(1, crack))
        path = _crack_path(7, cx, 2, 2 + depth)
        d.line(path, fill=(30, 40, 52), width=1)
        for k in (1, 2):                                                               # side branches as it grows
            if crack > 0.4 * k:
                br = _crack_path(11 + k, cx + (-1) ** k * 3, 2 + 4 * k, 2 + min(depth, 4 * k + 6))
                d.line([(x + (-1) ** k * (i // 2), yy) for i, (x, yy) in enumerate(br)], fill=(52, 64, 78))
        if stop > 0.01:                                                                # spreads along the plastic boundary
            sp = int(22 * min(1, stop)); yb = 2 + g1 - 1
            d.line((cx - sp, yb, cx + sp, yb), fill=(30, 40, 52))
    if shards > 0.01:                                       # top glass broken into pieces that rattle but stay stuck to the plastic
        cx = w // 2; xs = [2, cx - 34, cx - 17, cx, cx + 15, cx + 33, w + 2]
        for i, (xa, xb) in enumerate(zip(xs, xs[1:])):
            dy = -round(shards * max(0, math.sin(t * 24 + i * 2.1)))
            if dy:
                piece = img.crop((xa, 2, xb, 2 + g1)); img.paste((0, 0, 0, 0), (xa, 2, xb, 2 + g1)); img.alpha_composite(piece, (xa, 2 + dy))
        d = ImageDraw.Draw(img)
        for i, x in enumerate(xs[1:-1]):
            if abs(x - cx) > 2: d.line(_crack_path(30 + i, x, 2, 2 + g1 - 1), fill=(30, 40, 52))
    return img


@lru_cache(4)
def _spokes(n=9, steps=46, seed=5):
    """Fixed star-crack spoke paths (so a growing crack keeps its shape frame to frame)."""
    rnd = random.Random(seed); out = []
    for k in range(n):
        a = k * 2 * math.pi / n + rnd.uniform(-0.3, 0.3); x = y = 0.0; pts = [(0.0, 0.0)]
        reach = rnd.uniform(0.55, 1.0)
        for _ in range(steps):
            a += rnd.uniform(-0.12, 0.12); x += math.cos(a); y += math.sin(a) * 0.8; pts.append((x, y))
        out.append((reach, pts))
    return out


def windscreen(crack=0.0, chip=True, t=0.0, clear=False, wiper=0.0):
    """Front view through a windscreen with a stone chip on the passenger side and a growing star crack.
    crack 0..1 grows the star, 1..2 spreads it into a long spiderweb (still in one piece); clear=True leaves the glass
    see-through (lightly tinted) so a world drawn behind shows; wiper 0..1 sweeps both wiper arms up."""
    W_, H_ = 120, 76
    img = Image.new('RGBA', (W_, H_), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.polygon([(14, 6), (106, 6), (118, 70), (2, 70)], fill=(40, 42, 50))                 # frame
    inner = [(18, 10), (102, 10), (112, 66), (8, 66)]
    if clear:
        d.polygon(inner, fill=(0, 0, 0, 0)); d.polygon(inner, fill=(120, 170, 210, 46))
        d.line((18, 10, 102, 10), fill=(150, 156, 168)); d.line((8, 66, 112, 66), fill=(20, 21, 26))
    else:
        d.polygon(inner, fill=(92, 140, 176))
        for yy in range(10, 40): d.line((18 - (yy - 10) * 10 // 56, yy, 102 + (yy - 10) * 10 // 56, yy), fill=(92 + yy, 140 + yy // 2, 176))
        d.polygon([(8, 52), (40, 44), (70, 48), (112, 46), (112, 66), (8, 66)], fill=(54, 66, 80))  # horizon hills
    for gx in (30, 64):                                                                 # glare stripes
        d.line((gx, 12, gx - 12, 64), fill=(220, 236, 248, 90)); d.line((gx + 3, 12, gx - 9, 64), fill=(220, 236, 248, 50))
    for px, ln in ((24, 32), (66, 32)):                                                 # wiper arms, pivot at the bottom
        a = math.radians(170 - 9 - 115 * wiper)
        d.line((px, 64, px - ln * math.cos(a), 64 - ln * math.sin(a) * 0.9), fill=(26, 26, 32), width=2)
    cx, cy = 76, 40
    if chip:
        d.point((cx, cy), fill=(250, 252, 255)); d.point((cx + 1, cy), fill=(200, 210, 220)); d.point((cx, cy + 1), fill=(200, 210, 220))
    if crack > 0.01:
        for reach, pts in _spokes():
            n = int(len(pts) * reach * (0.45 * min(1, crack) + 0.55 * min(1, max(0, crack - 1))))   # star by 1, web by 2
            seg = [(cx + x, cy + y) for x, y in pts[:max(2, n)]]
            d.line(seg, fill=(236, 244, 252))
        if crack > 1.05:                                                                # spiderweb rings between spokes
            for rr in (7, 13, 20):
                k = min(1, (crack - 1) * 2 - rr / 40)
                if k > 0: d.arc((cx - rr, cy - rr * 0.8, cx + rr, cy + rr * 0.8), 200, 200 + 300 * k, fill=(214, 228, 240))
        rr = 4 * min(1, crack)
        if rr > 1: d.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), outline=(210, 226, 240))
    return img


PUMP = ["0111110000", "0100010110", "0100010101", "0111110101", "0111110101",
        "0111110101", "0111110110", "0111110000", "1111111000"]


@lru_cache(2)
def fuel_cut():
    img = Image.new('RGBA', (18, 18), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.ellipse((0, 0, 17, 17), fill=(240, 242, 248), outline=(26, 26, 46))
    for j, row in enumerate(PUMP):
        for i, b in enumerate(row):
            if b == '1': d.point((4 + i, 4 + j), fill=(40, 42, 50))
    d.line((3, 14, 14, 3), fill=RED, width=2)
    return img


@lru_cache(2)
def tick(on=True):
    img = Image.new('RGBA', (13, 13), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, 12, 12), 3, fill=(240, 242, 248), outline=(26, 26, 46))
    if on: d.line([(3, 6), (5, 9), (10, 3)], fill=(40, 170, 80), width=2)
    return img


def pill(cv, t, t0, t1, text, anchor, at, body='#ffffff', ink='#1a1a2e', shade='#d6d9e2', s=6):
    """Callout pill (ac-idle 'A/C' style badge) with a leader line; text box recorded for the safe-zone check."""
    if not (t0 <= t < t1 + 0.2): return
    dg.label(cv, t, t0, text, anchor, at, body, ink, shade, s=s, t1=t1)
    if t >= t0 + 0.14:
        b = big('badge', text, body, ink, shade, s=s); bx, by = at(t) if callable(at) else at
        ov.BOXES.append(('pill:' + text, (bx - b.width / 2, by - b.height / 2, bx + b.width / 2, by + b.height / 2)))
