"""Original flat-vector sports hatchback (3-door, no badge), side view facing right, in car units: length 100, origin at
ground level mid-car, y down. Window mode shows the cabin through tinted glass; cutaway mode removes the door and side
glass so seat, occupant and belt are fully visible.

    draw_car(P, wheel=angle, mode='glass'|'cut', cabin=fn(Pc), crumple=0..1, paint=CORAL)
    cabin(Pc) draws the inside (seat, dummy, belt...) with the same car-unit pen.
    draw_seat(Pc), draw_wheel_col(Pc), draw_belt(Pc, chest, slack, glow), draw_retractor(Pc, spin, charge, motor)
    SEAT_DUMMY: rest joints of a seated dummy (car units)
"""
import math
from .vec import INK, hexc, shade, mix, arcpts, bez, Layer, Pen, SS, soft_ellipse
from PIL import Image, ImageDraw

CORAL = hexc('#e47c4b')
TYRE = hexc('#2b2d34')
RIM = hexc('#c9ccd2')
GLASS = hexc('#a9c0cf')
TRIM = hexc('#3a3d47')
CABIN = hexc('#55565e')
LINER = hexc('#8d8e94')
SEAT = hexc('#3e4250')
WEB = hexc('#3b404c')
YEL = hexc('#ffc928')
RED = hexc('#e8343f')

WR, WY, WX = 9.4, -9.4, 31.0                       # wheel radius, centre height, |x|
AR = 11.2
D_RING = (-21.8, -27.0)                            # belt guide on the B-pillar
RETRACTOR = (-22.6, -11.2)                         # spool at the pillar base
BUCKLE = (-5.6, -13.4)
WHEEL_C = (3.0, -21.5)

SEAT_DUMMY = dict(hip=(-9.6, -14.2), neck=(-12.3, -25.6), head=(-11.9, -29.2), sh=(-12.2, -24.4), eF=(-5.6, -19.8),
                  hF=(1.2, -23.6), kF=(2.8, -16.6), fF=(9.2, -8.9), eB=(-5.0, -20.6), hB=(2.0, -24.4), kB=(2.0, -17.4),
                  fB=(8.4, -9.4))


def _arch(cx):
    a = math.asin((6.5 + WY) / AR * -1)            # where the arch meets the sill line y = -6.5
    return arcpts((cx, WY), AR, a, -math.pi - a, 16)


def body_pts(crumple=0.0):
    pts = [(-48.5, -6.5), (-50, -12), (-50.2, -18), (-48.6, -23.2), (-46.2, -29), (-42.2, -32.6), (-34, -34.3),
           (-20, -35.1), (-8, -34.5), (0, -32.6), (11, -25.7), (24, -23.5), (38, -21.3), (46, -18.7), (49.6, -14.6),
           (50, -10), (48.5, -6.5)]
    pts += _arch(WX) + _arch(-WX)
    return [_crumple(p, crumple) for p in pts]


def _crumple(p, k):
    if k <= 0 or p[0] <= 22: return p
    x = 22 + (p[0] - 22) * (1 - 0.32 * k)
    y = p[1] + math.sin((p[0] - 22) * 0.5) * 0.9 * k * (p[0] - 22) / 28    # wrinkle the bonnet
    return (x, y)


GREEN_HOUSE = [(-41.4, -24.6), (-40, -29.1), (-34, -32.5), (-20, -33.3), (-8.5, -32.7), (-1.6, -31.0), (8.6, -25.0)]
CUT = [(-41.4, -24.6), (-40, -29.1), (-34, -32.5), (-20, -33.3), (-8.5, -32.7), (-1.6, -31.0), (8.6, -25.0), (11.5, -24.2),
       (12.5, -8.6), (-25.5, -8.6), (-25.5, -24.6)]


def wheel(P, c, ang, squash=1.0):
    P.circle(c, WR, TYRE, ow=5)
    P.circle(c, WR * 0.66, RIM, ow=3)
    P.circle(c, WR * 0.5, shade(RIM, -0.12), ow=0)
    for k in range(5):
        a = ang + k * 2 * math.pi / 5
        P.line([(c[0] + math.cos(a) * WR * 0.15, c[1] + math.sin(a) * WR * 0.15),
                (c[0] + math.cos(a) * WR * 0.6, c[1] + math.sin(a) * WR * 0.6)], max(3, 1.15 * P.s), shade(RIM, 0.2))
    P.circle(c, WR * 0.16, TRIM, ow=2)
    P.arc(c, WR * 0.84, 200, 250, max(2, 0.6 * P.s), shade(TYRE, 0.25))


def draw_seat(P, lean=0.0):
    P.poly([(-17.4, -11.5), (-3.4, -12.4), (-2.2, -14.6), (-15.0, -15.6)], SEAT, ow=4)                 # cushion
    P.poly([(-15.6, -12.0), (-20.4, -29.6), (-17.8, -30.6), (-13.0, -14.6)], SEAT, ow=4)                 # backrest
    P.poly([(-20.0, -30.4), (-20.8, -33.0), (-17.4, -33.4), (-17.0, -30.6)], shade(SEAT, 0.12), ow=4)    # headrest
    P.line([(-18.8, -28.6), (-15.6, -16.0)], max(2, 0.5 * P.s), shade(SEAT, 0.25))
    P.poly([(-15.0, -11.6), (-6.0, -11.8), (-6.4, -8.8), (-14.6, -8.8)], TRIM, ow=3)                    # rail


def draw_wheel_col(P):
    P.poly([(5.6, -25.4), (12.5, -25.8), (12.5, -14.6), (7.6, -14.0), (6.0, -18.4)], shade(CABIN, -0.25), ow=4)   # dash
    P.line([(9.0, -19.6), WHEEL_C], max(3, 1.3 * P.s), TRIM)
    P.limb([(1.2, -25.2), (4.6, -17.6)], 1.3, TRIM, ow=3)


def draw_retractor(P, spin=0.0, charge=0.0, motor=0.0, scale=1.0):
    c = RETRACTOR; r = 2.5 * scale
    P.rrect((c[0] - 2.2 * scale, c[1] - 3.2 * scale, c[0] + 2.2 * scale, c[1] + 3.0 * scale), 0.8, hexc('#6d717c'), ow=3)
    P.circle(c, r, hexc('#252831'), ow=3)
    P.circle(c, r * 0.62, WEB, ow=0)
    for k in range(3):
        a = spin + k * 2 * math.pi / 3
        P.line([c, (c[0] + math.cos(a) * r * 0.85, c[1] + math.sin(a) * r * 0.85)], max(2, 0.35 * P.s * scale), shade(WEB, 0.4))
    P.circle(c, r * 0.22, hexc('#9aa0ab'), ow=2)
    if charge > 0:                                     # small pyrotechnic cartridge under the spool
        k = charge
        P.rrect((c[0] - 1.4 * k * scale, c[1] + 3.6 * scale, c[0] + 1.4 * k * scale, c[1] + 6.4 * scale), 0.5, RED, ow=3)
        P.fillpoly([(c[0] - 0.5 * k * scale, c[1] + 4.2 * scale), (c[0] + 0.5 * k * scale, c[1] + 4.2 * scale),
                    (c[0] + 0.1 * k * scale, c[1] + 5.0 * scale), (c[0] + 0.6 * k * scale, c[1] + 5.0 * scale),
                    (c[0] - 0.4 * k * scale, c[1] + 6.0 * scale), (c[0] - 0.1 * k * scale, c[1] + 5.2 * scale),
                    (c[0] - 0.6 * k * scale, c[1] + 5.2 * scale)], YEL)
    if motor > 0:                                      # or a small electric motor beside it
        k = motor; m = (c[0] + 4.6 * scale, c[1] + 1.2 * scale)
        P.rrect((m[0] - 1.9 * k * scale, m[1] - 1.5 * k * scale, m[0] + 1.9 * k * scale, m[1] + 1.5 * k * scale), 0.6, hexc('#9aa0ab'), ow=3)
        for dx in (-0.9, 0, 0.9): P.line([(m[0] + dx * k * scale, m[1] - 1.2 * k * scale), (m[0] + dx * k * scale, m[1] + 1.2 * k * scale)],
                                         max(2, 0.18 * P.s * scale), shade(INK, 0.2))
        P.circle((m[0] + 2.3 * k * scale, m[1]), 0.55 * k * scale, YEL, ow=2)


def belt_path(chest, slack=0.0):
    """D-ring -> chest -> buckle, plus the lap belt; slack bows the shoulder belt forward/down."""
    mid = ((D_RING[0] + chest[0]) / 2, (D_RING[1] + chest[1]) / 2)
    bow = (mid[0] + 2.2 * slack, mid[1] + 1.6 * slack)
    sh = bez(D_RING, bow, chest, 14)
    lo = bez(chest, ((chest[0] + BUCKLE[0]) / 2 + 1.6 * slack, (chest[1] + BUCKLE[1]) / 2 + 0.6 * slack), BUCKLE, 10)
    return sh + lo[1:]


def draw_belt(P, chest, slack=0.0, glow=0.0, hip=None):
    path = belt_path(chest, slack)
    hip = hip or SEAT_DUMMY['hip']
    lap = [RETRACTOR, (RETRACTOR[0] + 3, RETRACTOR[1] - 1.2), (hip[0] - 0.4, hip[1] + 0.2), BUCKLE]
    if glow > 0:
        g = mix(YEL, (255, 255, 255, 255), 0.15)
        for pts in (path, lap): P.line(pts, (1.25 + 1.6 * glow) * P.s, g[:3] + (int(170 * glow),))
    P.line([RETRACTOR, D_RING], 1.05 * P.s + 6, INK)
    P.line([RETRACTOR, D_RING], 1.05 * P.s, WEB)
    for pts in (lap, path):
        P.line(pts, 1.25 * P.s + 6, INK)
        P.line(pts, 1.25 * P.s, WEB)
        P.line([(x - 0.15, y - 0.25) for x, y in pts], max(2, 0.22 * P.s), shade(WEB, 0.35))
    P.rrect((BUCKLE[0] - 1.1, BUCKLE[1] - 0.9, BUCKLE[0] + 1.3, BUCKLE[1] + 1.4), 0.4, hexc('#c4c8cf'), ow=3)
    P.rrect((D_RING[0] - 0.9, D_RING[1] - 0.9, D_RING[0] + 0.9, D_RING[1] + 1.0), 0.3, hexc('#9aa0ab'), ow=3)


def _clip_draw(P, poly, fn, under=None):
    """Draw fn(pen) clipped to the car-unit polygon `poly` (only its bounding box is allocated)."""
    q = [P.p(t) for t in poly]
    x0 = int(min(a for a, _ in q)) - 4; y0 = int(min(b for _, b in q)) - 4
    x1 = int(max(a for a, _ in q)) + 4; y1 = int(max(b for _, b in q)) + 4
    W2, H2 = P.L.img.size
    x0, y0, x1, y1 = max(0, x0), max(0, y0), min(W2, x1), min(H2, y1)
    if x1 <= x0 or y1 <= y0: return
    tmp = Layer.__new__(Layer)
    tmp.w, tmp.h = (x1 - x0) // SS + 1, (y1 - y0) // SS + 1
    tmp.img = Image.new('RGBA', (x1 - x0, y1 - y0), (0, 0, 0, 0)); tmp.d = ImageDraw.Draw(tmp.img, 'RGBA')
    pen = Pen(tmp, P.ox - x0 / SS, P.oy - y0 / SS, P.s, P.rot, P.piv, P.kx, P.ky)
    fn(pen)
    mask = Image.new('L', tmp.img.size, 0)
    ImageDraw.Draw(mask).polygon([(a - x0, b - y0) for a, b in q], fill=255)
    a = tmp.img.getchannel('A'); from PIL import ImageChops
    tmp.img.putalpha(ImageChops.multiply(a, mask))
    P.L.img.alpha_composite(tmp.img, (x0, y0))


def interior_bg(P):
    P.fillpoly([(-52, -40), (20, -40), (20, -5), (-52, -5)], CABIN)
    P.fillpoly([(-52, -40), (20, -40), (20, -31.2), (-52, -31.2)], LINER)
    P.fillpoly([(-52, -12.6), (20, -12.6), (20, -5), (-52, -5)], shade(CABIN, -0.25))
    P.fillpoly([(-25.2, -34), (-20.6, -34), (-20.6, -8), (-25.2, -8)], shade(CORAL, -0.32))                 # B-pillar inside
    P.fillpoly([(-24.6, -33), (-23.6, -33), (-23.6, -9), (-24.6, -9)], shade(CORAL, -0.15))


def draw_car(P, wheel_ang=0.0, mode='glass', cabin=None, crumple=0.0, paint=CORAL, shadow=True, lights=1.0):
    if shadow: P.paste(soft_ellipse(int(54 * P.s), int(4.2 * P.s), 110), (0, -1.0))
    body = body_pts(crumple)
    under = [(x, max(y, -7.5)) for x, y in body]
    P.poly(body, paint, ow=6)
    # lighting: lighter upper flank, darker rocker, crisp beltline highlight
    P.fillpoly([_crumple(p, crumple) for p in [(-46.4, -28.5), (-42.2, -32.0), (-34, -33.7), (-20, -34.5), (-8, -33.9), (0, -32.1), (11, -25.2),
                (24, -23.0), (38, -20.8), (46, -18.2), (48, -16.6), (-49, -21.6)]], shade(paint, 0.16))
    P.fillpoly([(-41.8, -9.2), (41.8, -9.2), (41.0, -6.6), (-41, -6.6)], shade(paint, -0.32))
    P.line([_crumple(p, crumple) for p in [(-48.4, -22.2), (-20, -22.8), (20, -21.6), (47.6, -17.2)]], max(2, 0.45 * P.s), shade(paint, 0.4))
    for a in (_arch(WX), _arch(-WX)):
        P.line(a, max(3, 0.7 * P.s), shade(paint, -0.4), cap=False)
    # side skirt + diffuser + spoiler + mirror
    P.poly([(-49.2, -7.8), (-44.0, -7.8), (-44.6, -5.8), (-48.8, -5.8)], TRIM, ow=3)
    P.poly([(-43.6, -32.6), (-36, -34.6), (-35.4, -33.2), (-43.2, -31.4)], TRIM, ow=3)
    wheel(P, (-WX, WY), wheel_ang); wheel(P, _crumple((WX, WY), crumple * 0.4), wheel_ang)
    # lights
    P.poly([_crumple(p, crumple) for p in [(43.4, -18.6), (48.6, -16.4), (49.4, -14.6), (44.0, -15.8)]], mix(hexc('#fff1c8'), hexc('#ffffff'), lights * 0.5), ow=3)
    P.poly([(-50.0, -22.8), (-47.6, -22.6), (-47.8, -18.6), (-50.2, -18.8)], RED, ow=3)
    if mode == 'glass':
        _clip_draw(P, GREEN_HOUSE, lambda Q: (interior_bg(Q), cabin and cabin(Q)))
        P.fillpoly(GREEN_HOUSE, GLASS[:3] + (96,))
        P.fillpoly([(-30, -32.8), (-25.5, -33.1), (-33.5, -24.6), (-38, -24.6)], (255, 255, 255, 70))
        P.fillpoly([(-6, -32.6), (-3.4, -32.0), (-11.5, -24.6), (-14.4, -24.6)], (255, 255, 255, 55))
        P.line(GREEN_HOUSE + [GREEN_HOUSE[0]], max(3, 0.7 * P.s), TRIM, cap=False)
        P.fillpoly([(-25.0, -33.1), (-21.8, -33.3), (-21.8, -24.6), (-25.0, -24.6)], TRIM)          # B-pillar
        P.line([(-25.4, -24.4), (-25.4, -8.8), (12.2, -8.8), (11.2, -24.2)], max(2, 0.4 * P.s), shade(paint, -0.35), cap=False)
        P.line([(-21, -20.6), (-17.6, -20.6)], max(3, 0.7 * P.s), shade(paint, -0.4))
        P.poly([(8.0, -25.0), (12.6, -26.2), (13.2, -23.8), (9.0, -23.4)], TRIM, ow=3)                 # mirror
    else:
        _clip_draw(P, CUT, lambda Q: (interior_bg(Q), cabin and cabin(Q)))
        P.line(CUT + [CUT[0]], max(4, 0.9 * P.s), hexc('#fbe7d3'), cap=False)       # cut edge (sectioned panel)
        P.line(CUT + [CUT[0]], max(2, 0.3 * P.s), INK, cap=False)
        P.poly([(8.0, -25.0), (12.6, -26.2), (13.2, -23.8), (9.0, -23.4)], TRIM, ow=3)
