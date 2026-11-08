"""Glossy lit version of the original hatchback (geometry, cutaway and interior from stickman.car).

    draw_car(P, wheel, mode='glass'|'cut', cabin=fn, crumple=0..1, blur=0..1, lights=1.0, glow_ret=0..1)
Adds: body gradient (warm key from the right), teal sky reflection band, specular streaks, cool rim light on the roof,
wheel motion blur, headlight glow + beam, tail-light glow, warm ground bounce, retractor glow.
"""
import math
from stickman import car as C
from stickman.vec import hexc, shade
from .paint import gfill, glow

ORANGE = hexc('#ef7a32')


def wheel_blur(P, c, k):
    if k <= 0.05: return
    P.circle(c, C.WR * 0.66, (190, 195, 205, int(235 * k)), ow=0)
    for r in (0.5, 0.36):
        P.arc(c, C.WR * r, 0, 360, max(2, 0.5 * P.s), (120, 126, 140, int(200 * k)))
    P.circle(c, C.WR * 0.16, C.TRIM, ow=2)


def draw_car(P, wheel=0.0, mode='glass', cabin=None, crumple=0.0, blur=0.0, lights=1.0, glow_ret=0.0, paint=ORANGE):
    s = P.s
    glow(P, (0, 0.5), 60, (255, 140, 60), 0.32 * lights)                     # warm bounce on the asphalt
    glow(P, (-6, -0.5), 52, (5, 8, 18), 0.85)                                # contact shadow
    C.draw_car(P, wheel, mode, cabin, crumple, paint, shadow=False)
    body = C.body_pts(crumple)
    upper = [p for p in body]

    def shading(Q):
        gfill(Q, [(-55, -40), (55, -40), (55, 0), (-55, 0)], (255, 200, 150, 0), (40, 10, 30, 120), (0, -24), (0, -6))
        gfill(Q, [(-55, -40), (55, -40), (55, 0), (-55, 0)], (255, 236, 200, 110), (255, 200, 150, 0), (52, -20), (10, -20))
        Q.fillpoly([(-49, -24.2), (-20, -25.4), (20, -23.9), (48, -19.6), (48, -18.2), (20, -22.4), (-20, -23.6), (-49, -22.6)], (70, 170, 200, 70))
        Q.fillpoly([(-30, -21.4), (24, -20.6), (24, -19.8), (-30, -20.5)], (255, 250, 235, 150))   # crisp shoulder highlight
        Q.fillpoly([(14, -24.2), (38, -21.6), (38, -20.8), (14, -23.2)], (255, 245, 225, 120))     # bonnet glint
        hole = C.CUT if mode == 'cut' else C.GREEN_HOUSE
        Q.d.polygon([Q.p(p) for p in hole], fill=(0, 0, 0, 0))     # paint gloss stays off the cabin (plain draw = erase)
    C._clip_draw(P, upper, shading)
    P.line([(-42, -33.0), (-34, -34.7), (-20, -35.5), (-8, -34.9), (0, -33.0)], max(2, 0.55 * s), (130, 215, 245, 200), cap=False)  # cool rim
    for x in (-C.WX, C.WX): wheel_blur(P, C._crumple((x, C.WY), crumple * 0.4) if x > 0 else (x, C.WY), blur)
    hl = C._crumple((46.5, -16.4), crumple)
    if lights > 0:
        P.fillpoly([hl, (hl[0] + 60, hl[1] - 7), (hl[0] + 64, hl[1] + 14), (hl[0], hl[1] + 1.6)], (255, 214, 150, int(55 * lights)))
        glow(P, hl, 9, (255, 220, 160), 0.95 * lights)
        glow(P, hl, 3.2, (255, 255, 240), lights)
        glow(P, (-49.6, -20.8), 6, (255, 50, 50), 0.7 * lights)
    if glow_ret > 0:
        glow(P, C.RETRACTOR, 9, (255, 190, 70), 0.85 * glow_ret)
