"""Pixel props for the six-episode 'car stuff, explained' series (limp-mode ... premium-fuel; videos/<ep>/src).

Small RGBA sprites on a pixel grid; scale with pixanim.grid.up(img, s) (nearest). Callout pills: carbits.pill();
RPM gauge: carbits.rpm_gauge(); poll sticker: overlays.poll(); presenter spot: explainbits.SPOT.
    power_meter(k, warn)          vertical POWER bar meter, k 0..1 filled; turns amber/red as it drops, warn lamp blinks
    speedo(shown, true, band)     speedometer dial: dashed amber tolerance band, green true-speed tick, red shown needle
    belt_drive(t, snap)           toothed timing belt over cam + crank pulleys (teeth move); snap 0..1 breaks and flaps it
    valve_piston(gap, hit)        one-cylinder cutaway: valve down, piston up; gap 0..1 clearance, hit flashes the contact
    blind_road(k, t, other, look, warn)  top-down road: our car, blue mirror cones, red blind-spot cone (alpha k), car in it;
                                  look 0..1 head check (green sight cone), warn blinks the amber lamp in the right mirror
    airbag_icon(on)               seated passenger + circle airbag symbol lamp (red when on); bulb(strike) crossed-out bulb
    airbag_module(t, fault)       control box with sensor + connector wires; fault blinks the broken connector
    fuel_gauge(level, col)        E..F fuel gauge with coloured pump badge
    fuel_compare(k, t)            REGULAR vs PREMIUM: two gauges + two equal power bars filling to k, '=' between
Any number on these props is decorative only (no units)."""
import math
from functools import lru_cache
from PIL import Image, ImageDraw
from pixanim.grid import outline, text_width
from pixanim.dash import _gauge_face, _text, NEEDLE, NEEDLE_HI, RED
from assets.explainbits import car_top, STEEL

YEL, GRN, AMB, BLU = (255, 210, 63), (70, 210, 110), (255, 150, 30), (80, 170, 255)
INK = (26, 26, 46)


def _img(w, h): return Image.new('RGBA', (w, h), (0, 0, 0, 0))


def _label(d, cx, y, s, col): _text(d, cx - text_width(s) // 2, y, s, col)


# ------------------------------------------------------------------ limp mode
def power_meter(k=1.0, warn=False, t=0.0):
    img = _img(30, 70); d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, 29, 69), 4, fill=(20, 21, 26), outline=(60, 64, 76))
    n = 10
    for i in range(n):
        y1 = 58 - i * 5; on = (i + 0.5) / n <= k
        col = (GRN if i >= 6 else YEL if i >= 3 else RED) if on else (44, 46, 56)
        if on and k < 0.35: col = RED if int(t * 6) % 2 else AMB
        d.rectangle((6, y1 - 3, 23, y1), fill=col)
    _label(d, 15, 62, 'PWR', (150, 156, 168))
    if warn and int(t * 4) % 2 == 0: d.rectangle((11, 2, 18, 6), fill=AMB)
    return outline(img)


# ------------------------------------------------------------------ speedometer
@lru_cache(4)
def _speed_face(r):
    n = 2 * r + 12; img = _img(n, n); _gauge_face(ImageDraw.Draw(img), n // 2, n // 2, r, label='SPEED', majors=9)
    return img


def speedo(shown=0.5, true=0.46, band=(0.46, 0.52), r=44, t=0.0):
    """Fractions of full scale. The band is drawn dashed (every other 6 deg) just inside the ticks."""
    img = _speed_face(r).copy(); d = ImageDraw.Draw(img); c = img.width // 2; ri = r - 14
    a0, a1 = 225 - 270 * band[1], 225 - 270 * band[0]
    a = a0
    while a < a1:
        d.arc((c - ri, c - ri, c + ri, c + ri), 360 - min(a + 3, a1), 360 - a, fill=YEL, width=4); a += 6
    ta = math.radians(225 - 270 * true)
    d.line((c + (ri - 6) * math.cos(ta), c - (ri - 6) * math.sin(ta), c + (r - 5) * math.cos(ta), c - (r - 5) * math.sin(ta)), fill=GRN, width=2)
    na = math.radians(225 - 270 * shown + 1.5 * math.sin(t * 9))
    tip = (c + (r - 9) * math.cos(na), c - (r - 9) * math.sin(na)); tail = (c - 6 * math.cos(na), c + 6 * math.sin(na))
    d.line((tail, tip), fill=(120, 30, 10), width=4); d.line((tail, tip), fill=NEEDLE, width=2)
    d.line(((c + tip[0]) / 2, (c + tip[1]) / 2, *tip), fill=NEEDLE_HI, width=1)
    d.ellipse((c - 5, c - 5, c + 5, c + 5), fill=(40, 42, 50)); d.ellipse((c - 3, c - 3, c + 3, c + 3), fill=(90, 96, 110))
    return img


# ------------------------------------------------------------------ timing belt
CAM, CRANK, PR = ((40, 16), (40, 84)), (40, 84), 12


def _pulley(d, cx, cy, r, rot, col):
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=col[1]); d.ellipse((cx - r + 3, cy - r + 3, cx + r - 3, cy + r - 3), fill=col[2])
    for k in range(3):
        a = math.radians(rot + 120 * k)
        d.line((cx, cy, cx + (r - 4) * math.cos(a), cy + (r - 4) * math.sin(a)), fill=col[0], width=2)
    d.ellipse((cx - 2, cy - 2, cx + 2, cy + 2), fill=INK)


def belt_drive(t=0.0, snap=0.0):
    """Two cam pulleys on top, crank pulley below, toothed belt loop. snap > 0: belt broken, loose end flaps down."""
    img = _img(96, 104); d = ImageDraw.Draw(img)
    cams = ((24, 16), (72, 16)); cr = (48, 86)
    spin = 0 if snap > 0.3 else t * 240
    pts = [(cams[0][0] - PR, cams[0][1]), (cr[0] - PR - 2, cr[1]), (cr[0], cr[1] + PR + 2), (cr[0] + PR + 2, cr[1]),
           (cams[1][0] + PR, cams[1][1]), (cams[1][0], cams[1][1] - PR - 1), (cams[0][0], cams[0][1] - PR - 1)]
    if snap <= 0:
        d.line(pts + [pts[0]], fill=(30, 30, 36), width=5, joint='curve')
        for i, (p, q) in enumerate(zip(pts, pts[1:] + [pts[0]])):      # moving teeth along each straight run
            L = math.dist(p, q); off = (t * 60) % 6
            for s in range(int(L / 6) + 1):
                u = (s * 6 + off) / max(L, 1)
                if u > 1: break
                d.point((p[0] + (q[0] - p[0]) * u, p[1] + (q[1] - p[1]) * u), fill=(120, 124, 138))
    else:
        flap = 10 * snap + 6 * math.sin(t * 18) * snap
        d.line([pts[4], pts[5], pts[6], pts[0], (pts[0][0] + 4, pts[0][1] + 30 + flap)], fill=(30, 30, 36), width=5)
        d.line([pts[1], pts[2], pts[3], (pts[3][0] + 6, pts[3][1] - 26 + flap)], fill=(30, 30, 36), width=5)
    for (x, y) in cams: _pulley(d, x, y, PR, spin, ((120, 90, 30), (190, 150, 60), (230, 196, 100)))
    _pulley(d, *cr, PR, spin * 0.5, (STEEL[0], STEEL[1], STEEL[2]))
    return outline(img)


def valve_piston(gap=1.0, hit=0.0):
    """Cylinder cutaway: head + valve from above, piston from below. gap 1 = safe clearance, 0 = touching."""
    img = _img(60, 96); d = ImageDraw.Draw(img)
    d.rectangle((6, 0, 53, 18), fill=(110, 116, 130)); d.rectangle((10, 18, 49, 92), fill=(48, 50, 60))
    d.rectangle((6, 18, 9, 92), fill=STEEL[1]); d.rectangle((50, 18, 53, 92), fill=STEEL[1])
    vy = 26 + int(18 * (1 - gap))                                     # valve head (opens down)
    d.rectangle((27, 0, 32, vy), fill=STEEL[3]); d.polygon([(16, vy + 5), (43, vy + 5), (34, vy), (25, vy)], fill=STEEL[2]); d.line((16, vy + 5, 43, vy + 5), fill=STEEL[0])
    py = 62 - int(18 * (1 - gap))                                     # piston crown rises
    d.rectangle((12, py, 47, py + 22), fill=STEEL[2]); d.rectangle((12, py + 4, 47, py + 5), fill=STEEL[0])
    d.rectangle((12, py + 9, 47, py + 10), fill=STEEL[0]); d.line((29, py + 22, 29, 96), fill=STEEL[1], width=5)
    if hit > 0:
        a = int(255 * hit)
        for k in range(8):
            ang = math.radians(k * 45); r = 6 + 6 * hit
            d.line((30, py - 2, 30 + r * math.cos(ang), py - 2 + r * math.sin(ang)), fill=(255, 220, 90, a), width=2)
    return outline(img)


# ------------------------------------------------------------------ blind spot
def blind_road(k=1.0, t=0.0, other=True, look=0.0, warn=False):
    """Top-down road, 140x200 grid. Our car centre-left lane heading up; the blind-spot cone sits behind its right mirror."""
    img = _img(140, 200); d = ImageDraw.Draw(img)
    d.rectangle((0, 0, 139, 199), fill=(44, 46, 54))
    for x in (4, 135): d.rectangle((x, 0, x + 1, 199), fill=(220, 220, 220))
    off = int(t * 60) % 24
    for y in range(-24, 200, 24): d.rectangle((69, y + off, 70, y + off + 12), fill=(230, 230, 230))
    over = _img(140, 200); o = ImageDraw.Draw(over)
    o.polygon([(18, 84), (2, 200), (24, 200)], fill=BLU + (90,))                     # left mirror view
    o.polygon([(54, 84), (60, 200), (80, 200)], fill=BLU + (90,))                    # right mirror view (narrow)
    a = int(150 * k)
    o.polygon([(58, 86), (136, 92), (136, 178), (78, 178)], fill=RED + (a,))         # blind spot, outside the mirror view
    for y in range(96, 176, 8): o.line((60 + (y - 86) // 5, y, 136, y), fill=(255, 120, 120, a // 2))
    img.alpha_composite(over)
    if other: img.alpha_composite(car_top(0, (60, 120, 220)), (88, 100 + int(3 * math.sin(t * 2))))
    img.alpha_composite(car_top(0, (196, 40, 50)), (16, 60))
    hx, hy = 30, 92                                                                  # driver's head (left-hand seat)
    if look > 0.01:                                                                  # head check: green sight cone sweeps over the gap
        a = math.radians(-90 + 118 * look); sc = _img(140, 200); o = ImageDraw.Draw(sc)
        o.polygon([(hx, hy), (hx + 110 * math.cos(a - 0.28), hy + 110 * math.sin(a - 0.28)),
                   (hx + 110 * math.cos(a + 0.28), hy + 110 * math.sin(a + 0.28))], fill=GRN + (120,))
        img.alpha_composite(sc)
    d = ImageDraw.Draw(img); a = math.radians(-90 + 118 * look)
    d.ellipse((hx - 5, hy - 5, hx + 5, hy + 5), fill=(60, 40, 30), outline=INK)
    d.ellipse((hx + 4 * math.cos(a) - 2, hy + 4 * math.sin(a) - 2, hx + 4 * math.cos(a) + 2, hy + 4 * math.sin(a) + 2), fill=(214, 160, 120))
    d.rounded_rectangle((52, 76, 62, 86), 2, fill=(150, 156, 168), outline=INK)              # right door mirror
    if warn and int(t * 4) % 2 == 0: d.polygon([(54, 85), (60, 85), (57, 78)], fill=AMB)
    return img


# ------------------------------------------------------------------ airbag
def airbag_icon(on=True):
    """Generic seated-passenger + inflated-bag symbol (person faces right, bag circle in front of the head)."""
    img = _img(24, 20); d = ImageDraw.Draw(img); col = RED if on else (70, 40, 44)
    d.rounded_rectangle((0, 0, 23, 19), 3, fill=(20, 21, 26), outline=(48, 50, 58))
    d.ellipse((4, 3, 8, 7), fill=col); d.line((6, 8, 8, 13), fill=col, width=2); d.line((8, 13, 13, 13), fill=col, width=2)
    d.line((13, 13, 13, 17), fill=col, width=2); d.line((7, 10, 11, 10), fill=col); d.line((4, 9, 6, 16), fill=col)
    d.ellipse((12, 2, 20, 10), outline=col, width=2)
    if on: d.point((13, 3), fill=(255, 200, 200))
    return img


def bulb(strike=0.0):
    """Pixel light bulb; strike 0..1 draws the red diagonal 'not just a bulb' line."""
    img = _img(30, 34); d = ImageDraw.Draw(img)
    d.ellipse((5, 1, 25, 21), fill=(255, 236, 140)); d.ellipse((9, 4, 15, 10), fill=(255, 250, 220))
    d.rectangle((10, 20, 20, 23), fill=(255, 236, 140)); d.rectangle((10, 24, 20, 30), fill=STEEL[1])
    for y in (25, 27, 29): d.line((10, y, 20, y), fill=STEEL[0])
    img = outline(img)
    if strike > 0: ImageDraw.Draw(img).line((2, 2, 2 + 26 * strike, 2 + 30 * strike), fill=RED, width=3)
    return img


def airbag_module(t=0.0, fault=1.0):
    """Control unit box with three wires: sensor (left), connector (centre, broken + blinking when fault), airbag (right)."""
    img = _img(110, 70); d = ImageDraw.Draw(img)
    d.rounded_rectangle((34, 4, 76, 34), 4, fill=(60, 64, 80)); d.rectangle((38, 8, 72, 14), fill=(30, 32, 40))
    _label(d, 55, 20, 'SRS', YEL)
    d.line((40, 34, 12, 56), fill=(200, 60, 60), width=3); d.rectangle((2, 54, 18, 66), fill=STEEL[1]); _label(d, 10, 57, 'S', INK)
    bad = fault > 0 and int(t * 5) % 2 == 0
    d.line((55, 34, 55, 46), fill=(60, 180, 90), width=3); d.line((55, 54, 55, 62), fill=(60, 180, 90), width=3)
    d.rectangle((49, 46, 61, 50), fill=YEL if not bad else AMB); d.rectangle((49, 51 + int(2 * fault), 61, 54 + int(2 * fault)), fill=(230, 230, 230))
    d.line((70, 34, 96, 52), fill=(60, 120, 230), width=3); d.ellipse((88, 46, 108, 66), fill=(236, 238, 244)); d.ellipse((92, 50, 104, 62), fill=(200, 204, 214))
    if bad: d.rectangle((44, 42, 66, 60), outline=RED, width=1)
    return outline(img)


# ------------------------------------------------------------------ fuel
def fuel_gauge(level=0.8, col=GRN, r=24):
    n = 2 * r + 8; img = _img(n, n // 2 + 14); d = ImageDraw.Draw(img); c = n // 2
    d.pieslice((4, 4, n - 4, n - 4), 180, 360, fill=(30, 32, 40), outline=STEEL[1])
    for i in range(5):
        a = math.radians(180 - 45 * i); d.line((c + (r - 8) * math.cos(a), c - (r - 8) * math.sin(a), c + (r - 3) * math.cos(a), c - (r - 3) * math.sin(a)), fill=RED if i == 0 else (236, 240, 248))
    _text(d, 8, c + 2, 'E', RED); _text(d, n - 12, c + 2, 'F', (236, 240, 248))
    a = math.radians(180 - 180 * level); d.line((c, c, c + (r - 6) * math.cos(a), c - (r - 6) * math.sin(a)), fill=NEEDLE, width=2)
    d.ellipse((c - 3, c - 3, c + 3, c + 3), fill=col)
    return outline(img)


def fuel_compare(k=1.0, t=0.0):
    img = _img(130, 90); d = ImageDraw.Draw(img)
    for i, (name, col) in enumerate((('REG', GRN), ('PREM', YEL))):
        x = 4 + i * 70
        img.alpha_composite(fuel_gauge(0.75 + 0.03 * math.sin(t * 2 + i), col), (x, 0))
        _label(d, x + 28, 46, name, col)
        d.rectangle((x + 4, 58, x + 52, 70), fill=(30, 32, 40), outline=STEEL[0])
        d.rectangle((x + 6, 60, x + 6 + int(44 * k), 68), fill=col)
        _label(d, x + 28, 76, 'POWER', (150, 156, 168))
    if k > 0.95: _label(d, 65, 60, '=', (255, 255, 255))
    return img
