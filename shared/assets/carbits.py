"""Pixel props for the 'car stuff, explained' dashboard episodes (red-zone, fuel-cap-light, windscreen-glass).

Every sprite is drawn on a small pixel grid and returned as RGBA; scale it with pixanim.grid.up(img, s) (nearest).
    rpm_gauge(deg, ring)        rev counter with a red zone; ring 0..1 lights a red glow over the red section
    warn_lamp(on)               engine warning light (amber when on)
    fuel_cap(rot, door)         car rear quarter, fuel flap open, cap face-on (CAP_XY), turned by rot degrees
    glass_layers(crack, stop)   three-layer windscreen cutaway (glass / plastic / glass) with a crack that stops at the plastic
    windscreen(crack)           a windscreen seen from the front with a stone chip and spreading crack
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


def glass_layers(crack=0.0, stop=0.0, t=0.0, w=140, layer_h=(16, 8, 16)):
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
    return img


def windscreen(crack=0.0, chip=True, t=0.0):
    """Front view through a windscreen (sky + horizon) with a stone chip low on the passenger side and a growing crack."""
    W_, H_ = 120, 76
    img = Image.new('RGBA', (W_, H_), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    poly = [(14, 6), (106, 6), (118, 70), (2, 70)]
    d.polygon(poly, fill=(40, 42, 50))                                                 # frame
    inner = [(18, 10), (102, 10), (112, 66), (8, 66)]
    d.polygon(inner, fill=(92, 140, 176))
    for yy in range(10, 40): d.line((18 - (yy - 10) * 10 // 56, yy, 102 + (yy - 10) * 10 // 56, yy), fill=(92 + yy, 140 + yy // 2, 176))
    d.polygon([(8, 52), (40, 44), (70, 48), (112, 46), (112, 66), (8, 66)], fill=(54, 66, 80))  # horizon hills
    for gx in (30, 64):                                                                 # glare stripes
        d.line((gx, 12, gx - 12, 64), fill=(220, 236, 248, 90)); d.line((gx + 3, 12, gx - 9, 64), fill=(220, 236, 248, 50))
    d.line((24, 64, 56, 58), fill=(26, 26, 32), width=2); d.line((66, 64, 98, 58), fill=(26, 26, 32), width=2)  # wipers
    cx, cy = 76, 40
    if chip:
        d.point((cx, cy), fill=(250, 252, 255)); d.point((cx + 1, cy), fill=(200, 210, 220)); d.point((cx, cy + 1), fill=(200, 210, 220))
    if crack > 0.01:
        rnd = random.Random(5)
        for k in range(7):                                                              # star crack, spreads in steps
            a = k * 2 * math.pi / 7 + rnd.uniform(-0.3, 0.3); L = (6 + rnd.uniform(0, 12)) * min(1, crack)
            x, y = cx, cy; pts = [(x, y)]
            for s in range(int(L)):
                x += math.cos(a) + rnd.uniform(-0.5, 0.5); y += math.sin(a) + rnd.uniform(-0.5, 0.5); pts.append((x, y))
            if len(pts) > 1: d.line(pts, fill=(236, 244, 252))
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
