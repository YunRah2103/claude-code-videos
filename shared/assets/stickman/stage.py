"""Muted grey crash-test hall (flat vector, soft light shafts) + crash barrier.

    strip = hall(w=2160, h=1920, floor=1560)      # RGB 1x strip, seamless every 1080 px (scroll with view())
    view(strip, scroll, w=1080)                   # wrapped crop for a camera scroll in px
    barrier(P, x, ground, s, crush=0..1)          # concrete block + yellow/black chevrons + honeycomb crush face
    vignette(w, h)                                # cached RGBA darkening overlay
"""
import math
from functools import lru_cache
from PIL import Image, ImageDraw, ImageFilter
from .vec import Layer, INK, hexc, shade, mix, SS, soft_ellipse

WALL = hexc('#a8acb1'); WALL_LO = hexc('#959a9f'); CEIL = hexc('#5d6167')
FLOOR = hexc('#7e8288'); FLOOR_LO = hexc('#5f6369')
GLASS = hexc('#7f98ad'); FRAME = hexc('#dfe2e5')
DOOR = hexc('#71767c')
YEL = hexc('#ffc928')


def _grad(d, box, c0, c1, steps=48):
    x0, y0, x1, y1 = box
    for i in range(steps):
        a, b = y0 + (y1 - y0) * i / steps, y0 + (y1 - y0) * (i + 1) / steps + 1
        d.rectangle((x0, a, x1, b), fill=mix(c0, c1, i / (steps - 1)))


@lru_cache(8)
def hall(w=2160, h=1920, floor=1560, dark=0.0):
    L = Layer(w, h); d = L.d; P = L.pen()
    _grad(d, (0, 0, w * SS, floor * SS), shade(WALL, -0.06 - dark), shade(WALL, 0.04 - dark))
    d.rectangle((0, 0, w * SS, 150 * SS), fill=shade(CEIL, -dark))
    for k in range(0, w, 270):                                                   # ceiling lights
        P.rrect((k + 60, 112, k + 210, 132), 8, (246, 246, 240, 255), ow=4)
    P.fillpoly([(0, 150), (w, 150), (w, 172), (0, 172)], shade(CEIL, 0.18 - dark))
    for k in range(0, w, 135):                                                   # panel seams
        P.line([(k, 172), (k, floor - 200)], 3, shade(WALL, -0.12 - dark), cap=False)
    d.rectangle((0, (floor - 200) * SS, w * SS, floor * SS), fill=shade(WALL_LO, -dark))
    P.line([(0, floor - 200), (w, floor - 200)], 6, shade(WALL, 0.2 - dark), cap=False)
    for base in range(0, w, 1080):
        # big industrial window
        x0, y0 = base + 90, 330
        P.rrect((x0 - 14, y0 - 14, x0 + 394, y0 + 404), 6, FRAME, ow=5)
        for i in range(3):
            for j in range(3):
                bx, by = x0 + 6 + i * 130, y0 + 6 + j * 130
                P.rrect((bx, by, bx + 120, by + 120), 3, shade(GLASS, 0.06 * j - dark), ow=0)
                P.fillpoly([(bx + 18, by + 120), (bx + 70, by), (bx + 92, by), (bx + 40, by + 120)], shade(GLASS, 0.22 - dark))
        # rolling door with hazard edge
        dx = base + 640
        P.rrect((dx - 12, 300, dx + 342, floor - 6), 4, shade(DOOR, 0.25 - dark), ow=5)
        P.rrect((dx, 312, dx + 330, floor - 6), 2, shade(DOOR, -dark), ow=0)
        for yy in range(330, floor - 40, 34):
            P.line([(dx + 6, yy), (dx + 324, yy)], 4, shade(DOOR, -0.18 - dark), cap=False)
        for i in range(0, 330, 44):
            P.fillpoly([(dx + i, floor - 40), (dx + i + 22, floor - 40), (dx + i + 44, floor - 6), (dx + i + 22, floor - 6)], YEL)
        # wall box (vent / panel)
        P.rrect((base + 520, 340, base + 600, 470), 8, shade(WALL, 0.12 - dark), ow=4)
        for yy in range(360, 460, 18): P.line([(base + 534, yy), (base + 586, yy)], 4, shade(WALL, -0.2 - dark))
    _grad(d, (0, floor * SS, w * SS, h * SS), shade(FLOOR, -dark), shade(FLOOR_LO, -dark))
    P.line([(0, floor), (w, floor)], 8, shade(FLOOR, 0.25 - dark), cap=False)
    for k in range(0, w, 180):                                                    # track dashes
        P.rrect((k + 20, floor + 150, k + 120, floor + 164), 6, YEL, ow=0)
    img = L.done().convert('RGB')
    # soft light shafts from the windows (screen-blended, blurred)
    sh = Image.new('L', (w, h), 0); sd = ImageDraw.Draw(sh)
    for base in range(0, w, 1080):
        x0 = base + 90
        sd.polygon([(x0, 330), (x0 + 380, 330), (x0 + 900, floor + 120), (x0 + 360, floor + 120)], fill=52)
    sh = sh.filter(ImageFilter.GaussianBlur(40))
    img = Image.composite(Image.new('RGB', (w, h), (255, 252, 240)), img, sh)
    return img


def view(strip, scroll, w=1080):
    x = int(scroll) % (strip.width // 2)
    return strip.crop((x, 0, x + w, strip.height))


@lru_cache(4)
def vignette(w=1080, h=1920, k=120):
    m = Image.new('L', (w // 8, h // 8), 0); d = ImageDraw.Draw(m)
    d.ellipse((-w // 16, -h // 22, w // 8 + w // 16, h // 8 + h // 22), fill=255)
    m = m.filter(ImageFilter.GaussianBlur(14)).resize((w, h), Image.BILINEAR)
    a = m.point(lambda v: int((255 - v) * k / 255))
    o = Image.new('RGBA', (w, h), (18, 20, 28, 0)); o.putalpha(a)
    return o


def barrier(P, x, ground, crush=0.0, side=-1):
    """Barrier in car units at P scale: block body x..x+24, honeycomb face on the `side` (-1 = left, facing the car)."""
    hgt = 32.0
    P.paste(soft_ellipse(int(16 * P.s), int(3 * P.s), 110), (x + 12, ground - 0.5))
    P.poly([(x, ground), (x, ground - hgt), (x + 3, ground - hgt - 2), (x + 30, ground - hgt - 2), (x + 30, ground)], hexc('#b9bcc1'), ow=6)
    P.fillpoly([(x + 3, ground - hgt - 1), (x + 29, ground - hgt - 1), (x + 29, ground - hgt + 2), (x + 3, ground - hgt + 2)], hexc('#d3d6da'))
    for i in range(5):                                                         # chevrons
        y0 = ground - hgt + 4 + i * 5.6
        P.fillpoly([(x + 4, y0), (x + 28, y0), (x + 28, y0 + 2.8), (x + 4, y0 + 2.8)], YEL if i % 2 == 0 else INK)
    w = 7.0 * (1 - 0.55 * crush)                                               # aluminium honeycomb crush element
    hx = x - w
    P.poly([(hx, ground - 4), (hx, ground - 26), (x, ground - 26), (x, ground - 4)], hexc('#d7dbe0'), ow=5)
    for r in range(6):
        for c in range(3):
            cx = hx + (c + 0.5 + 0.5 * (r % 2)) * w / 3.4; cy = ground - 6 - r * 3.6
            if cx < x - 0.6:
                P.poly([(cx + 1.0 * math.cos(a), cy + 1.0 * math.sin(a)) for a in [k * math.pi / 3 for k in range(6)]],
                       hexc('#c3c8ce'), ow=2)
