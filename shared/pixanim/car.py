"""Detailed side-view pixel car (facing right), 90x50 grid (top 12 rows are headroom for the open bonnet).

car(color, wheel_deg, lights, brake, bonnet) -> RGBA sprite
  wheel_deg  spoke rotation (animate for rolling wheels)
  lights     headlights on (scenes can add a beam), brake: tail lights bright
  bonnet     0..1 opens the bonnet about its hinge at the windscreen, revealing the engine bay
Anchors (grid units, for scenes): WHEELS, HEADLIGHT, EXHAUST, BAY (engine bay centre), ROOF (top centre).
"""
import math
from functools import lru_cache
import numpy as np
from PIL import Image, ImageDraw
from .grid import outline

GW, GH, TOP = 90, 38, 12
WHEELS = ((21, 41), (69, 41))
HEADLIGHT, EXHAUST, BAY, ROOF = (84, 30), (3, 37), (72, 29), (41, 16)

PAL = {
    'red':    ((232, 52, 63), (181, 34, 44), (255, 122, 128), (140, 24, 32)),
    'blue':   ((61, 127, 214), (43, 95, 168), (122, 176, 240), (30, 66, 120)),
    'silver': ((176, 182, 192), (130, 136, 148), (222, 228, 236), (96, 100, 110)),
    'used':   ((168, 88, 92), (132, 66, 70), (196, 122, 125), (98, 48, 52)),
    'yellow': ((255, 196, 40), (214, 150, 20), (255, 232, 130), (160, 106, 10)),
}
GLASS, GLASS_HI, GLASS_SH = (126, 158, 184), (196, 222, 240), (84, 108, 132)
TYRE, TREAD, RIM, RIM_SH, RIM_HI = (26, 27, 32), (44, 46, 52), (172, 178, 190), (118, 124, 136), (226, 230, 238)
TRIM, TRIM_HI = (46, 48, 56), (84, 88, 98)

BODY = [(3, 26), (3, 19), (5, 16), (15, 15), (22, 14), (61, 14), (75, 16), (84, 18), (87, 21), (87, 26)]
CABIN = [(19, 14), (27, 5), (31, 4), (53, 4), (57, 5), (65, 14)]
WIN_R = [(23, 13), (29, 6), (39, 6), (39, 13)]
WIN_F = [(42, 13), (42, 6), (54, 6), (61, 13)]
HINGE = (62, 14)
BONNET = [(62, 14), (75, 16), (84, 18), (84, 21), (75, 19), (62, 17)]


def _rot(pts, c, deg):
    a = math.radians(deg); ca, sa = math.cos(a), math.sin(a)
    return [(c[0] + (x - c[0]) * ca + (y - c[1]) * sa, c[1] - (x - c[0]) * sa + (y - c[1]) * ca) for x, y in pts]


@lru_cache(512)
def car(color='red', wheel_deg=0, lights=False, brake=False, bonnet=0.0):
    body, shade, hi, deep = PAL[color]
    img = Image.new('RGBA', (GW, GH), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.polygon(CABIN, fill=body)
    d.polygon(BODY, fill=body)
    # shading bands: shoulder highlight, crease, lower shade, sill
    d.line([(6, 16), (15, 15), (22, 14), (61, 14), (75, 16), (83, 18)], fill=hi)
    d.line([(4, 20), (86, 20)], fill=hi); d.line([(4, 21), (86, 21)], fill=shade)
    d.rectangle((4, 23, 86, 24), fill=shade); d.rectangle((6, 25, 85, 26), fill=deep)
    d.line([(28, 5), (31, 4), (53, 4), (56, 5)], fill=hi)
    # glass with a diagonal reflection
    for win in (WIN_R, WIN_F):
        d.polygon(win, fill=GLASS)
        xs = [p[0] for p in win]; x0, x1 = min(xs), max(xs)
        d.line([(x0, 12), (x1, 12)], fill=GLASS_SH)
    for x in (31, 46, 47):
        d.line([(x, 12), (x + 5, 7)], fill=GLASS_HI)
    d.line([(30, 6), (38, 6)], fill=GLASS_HI)
    d.rectangle((39, 6, 41, 13), fill=deep)                       # B-pillar
    # door shut lines, handles, mirror
    for x in (23, 40, 60):
        d.line([(x, 14), (x, 24)], fill=deep)
    d.rectangle((33, 17, 35, 17), fill=TRIM_HI); d.rectangle((52, 17, 54, 17), fill=TRIM_HI)
    d.rectangle((58, 11, 62, 13), fill=body); d.line([(58, 11), (61, 11)], fill=hi)
    # bumpers, grille, lights
    d.rectangle((83, 21, 88, 26), fill=TRIM); d.line([(83, 21), (88, 21)], fill=TRIM_HI)
    d.rectangle((85, 23, 88, 24), fill=(20, 21, 26))
    d.rectangle((1, 20, 4, 26), fill=TRIM); d.line([(1, 20), (4, 20)], fill=TRIM_HI)
    d.rectangle((2, 25, 5, 26), fill=(70, 72, 80))               # exhaust tip
    hl = (255, 250, 205) if lights else (214, 216, 206)
    d.polygon([(80, 17), (85, 18), (86, 20), (80, 19)], fill=hl)
    if lights: d.point((84, 18), fill=(255, 255, 255))
    tl = (255, 60, 70) if brake else (186, 28, 38)
    d.rectangle((3, 17, 6, 19), fill=tl); d.point((4, 17), fill=(255, 150, 150) if brake else (230, 90, 96))
    # bonnet opens about its hinge, revealing the bay
    if bonnet > 0.01:
        d.polygon([(62, 14), (75, 16), (84, 18), (84, 21), (62, 19)], fill=(22, 23, 28))
        d.rectangle((66, 17, 74, 19), fill=(181, 34, 44)); d.rectangle((67, 17, 73, 17), fill=(255, 122, 128))
        d.rectangle((76, 18, 80, 20), fill=(92, 97, 108)); d.rectangle((63, 18, 65, 20), fill=(60, 63, 71))
    # wheel arches
    a = np.array(img)
    Y, X = np.mgrid[0:GH, 0:GW]
    for cx, cy in ((x, y - TOP) for x, y in WHEELS):
        r = np.hypot(X - cx, Y - cy)
        a[(r < 9.2) & (Y > 16)] = 0
        a[(r >= 8.2) & (r < 9.2) & (Y > 17) & (Y < cy + 2)] = (20, 21, 26, 255)
    img = Image.fromarray(a, 'RGBA'); d = ImageDraw.Draw(img)
    d.rectangle((30, 26, 60, 27), fill=(20, 21, 26))              # chassis shadow between the wheels
    for cx, cy in ((x, y - TOP) for x, y in WHEELS):
        d.ellipse((cx - 7.5, cy - 7.5, cx + 7.5, cy + 7.5), fill=TYRE)
        for k in range(12):
            t = math.radians(k * 30 + wheel_deg * 0.5)
            d.point((cx + 6.6 * math.cos(t), cy + 6.6 * math.sin(t)), fill=TREAD)
        d.ellipse((cx - 4.6, cy - 4.6, cx + 4.6, cy + 4.6), fill=RIM_SH)
        d.ellipse((cx - 4, cy - 4, cx + 4, cy + 4), fill=RIM)
        for k in range(5):
            t = math.radians(k * 72 + wheel_deg)
            d.line([(cx + 1.4 * math.cos(t), cy + 1.4 * math.sin(t)), (cx + 4 * math.cos(t), cy + 4 * math.sin(t))], fill=RIM_SH)
        d.ellipse((cx - 1.5, cy - 1.5, cx + 1.5, cy + 1.5), fill=RIM_HI)
        d.point((cx - 2, cy - 3), fill=RIM_HI)
    out = Image.new('RGBA', (GW, GH + TOP), (0, 0, 0, 0)); out.paste(img, (0, TOP))
    if bonnet > 0.01:
        d = ImageDraw.Draw(out)
        lid = [(x, y + TOP) for x, y in _rot(BONNET, HINGE, 58 * bonnet)]
        d.polygon(lid, fill=body)
        d.line(lid[3:], fill=deep); d.line(lid[:3], fill=hi)
    return outline(out)


def wheel_deg(distance_px, s):
    """Spoke angle for a car that has rolled distance_px at pixel size s (tyre radius 7.5 grid)."""
    return int(math.degrees(distance_px / (7.5 * s))) // 12 * 12 % 360
