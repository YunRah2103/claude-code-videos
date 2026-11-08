"""The main guy (characters/main-guy), redrawn as a smooth lit illustration with a jointed rig.

Same identity as the pixel sprite: dark messy hair with two cowlick strands, brown skin, silver square glasses, white
tee, black shorts, white-and-black trainers, friendly face. Front view, ~100 units tall (feet on y = 0).
Warm key light from the right, cool rim light on the left edges.

    g = Guy(pose='point', expr='smile', target=(x, y), mouth=0..1, look=(lx, ly), turn=-1..1, blink=0..1)
    draw_guy(P, g)                        # P: stickman.vec.Pen, local units -> px
    POSES: neutral, point, surprised, thumbs, ask, hips      EXPR: smile, talk, surprised, ask
    blend_pose(a, b, k)                   # eased transitions between poses
"""
import math
from dataclasses import dataclass, field, replace
from stickman.vec import hexc, shade, mix, arcpts, bez
from .paint import gfill, glow

NAVY = hexc('#1a1a2e')
SKIN, SKIN_DK, SKIN_HI = hexc('#c08862'), hexc('#9a6446'), hexc('#dba27a')
HAIR, HAIR_HI = hexc('#231a1c'), hexc('#4d3c3f')
GLASS = hexc('#b4bac4')
TEE, TEE_DK = hexc('#f7f7fa'), hexc('#c3cbdb')
SHORTS, SHORTS_HI = hexc('#2b2d33'), hexc('#4a4e5a')
SHOE, SOLE = hexc('#f4f4f6'), hexc('#1a1a2e')
RIM = (120, 205, 235, 255)
CHEEK = (232, 120, 110, 90)
OW = 3.2


def dvec(a): return (math.sin(a), math.cos(a))
def add(p, a, L): v = dvec(a); return (p[0] + v[0] * L, p[1] + v[1] * L)


# arm angles: absolute, 0 = down, + = towards screen right. (shoulder->elbow, elbow->wrist)
POSES = {
    'neutral':   dict(R=(0.22, -0.18), L=(-0.22, 0.18), legs=(0.07, -0.07), lean=0.0, hand=('rest', 'rest')),
    'point':     dict(R=(1.95, 0.05), L=(-0.25, 0.25), legs=(0.09, -0.06), lean=0.03, hand=('point', 'rest')),
    'surprised': dict(R=(0.9, 1.4), L=(-0.9, -1.4), legs=(0.16, -0.12), lean=-0.06, hand=('open', 'open')),
    'thumbs':    dict(R=(0.55, 2.0), L=(-0.22, 0.2), legs=(0.08, -0.07), lean=0.02, hand=('thumb', 'rest')),
    'ask':       dict(R=(0.62, 1.15), L=(-0.5, 1.25), legs=(0.08, -0.08), lean=0.0, hand=('open', 'hip')),
    'hips':      dict(R=(0.6, -1.5), L=(-0.6, 1.5), legs=(0.1, -0.1), lean=0.0, hand=('hip', 'hip')),
}


@dataclass
class Guy:
    pose: str = 'neutral'
    expr: str = 'smile'
    R: tuple = None
    L: tuple = None
    legs: tuple = None
    lean: float = None
    hand: tuple = None
    mouth: float = 0.0
    look: tuple = (0.0, 0.0)
    turn: float = 0.0
    blink: float = 0.0
    brow: float = 0.0
    bob: float = 0.0
    step: float = 0.0          # sideways step (units), e.g. stepping back in surprise

    def __post_init__(self):
        p = POSES[self.pose]
        for k in ('R', 'L', 'legs', 'lean', 'hand'):
            if getattr(self, k) is None: setattr(self, k, p[k])


def blend_pose(a, b, k):
    """Guy with pose a -> b at k (0..1), arms interpolated (hands switch at k = 0.5)."""
    pa, pb = POSES[a], POSES[b]
    lerp = lambda u, v: tuple(x + (y - x) * k for x, y in zip(u, v))
    return dict(R=lerp(pa['R'], pb['R']), L=lerp(pa['L'], pb['L']), legs=lerp(pa['legs'], pb['legs']),
                lean=pa['lean'] + (pb['lean'] - pa['lean']) * k, hand=pb['hand'] if k > 0.5 else pa['hand'])


def joints(g):
    hip = (g.step, -42.0 + g.bob)
    kr = add((hip[0] + 4.6, hip[1]), g.legs[0], 20); ar = add(kr, g.legs[0] * 0.4, 19)
    kl = add((hip[0] - 4.6, hip[1]), g.legs[1], 20); al = add(kl, g.legs[1] * 0.4, 19)
    drop = max(ar[1], al[1]) + 2.4                       # keep the lower foot on the ground
    sh = lambda p: (p[0], p[1] - drop)
    hip, kr, ar, kl, al = map(sh, (hip, kr, ar, kl, al))
    neck = add(hip, math.pi + g.lean, 29)
    perp = (math.cos(g.lean), -math.sin(g.lean))
    shR = (neck[0] + perp[0] * 11.5, neck[1] + 3.5 - perp[1] * 11.5)
    shL = (neck[0] - perp[0] * 11.5, neck[1] + 3.5 + perp[1] * 11.5)
    eR = add(shR, g.R[0], 14); wR = add(eR, g.R[0] + g.R[1], 13)
    eL = add(shL, g.L[0], 14); wL = add(eL, g.L[0] + g.L[1], 13)
    head = add(neck, math.pi + g.lean * 1.4, 15.5)
    return dict(hip=hip, kR=kr, aR=ar, kL=kl, aL=al, neck=neck, shR=shR, shL=shL, eR=eR, wR=wR, eL=eL, wL=wL, head=head)


def aim(g, which, target, P_origin=(0, 0), scale=1.0):
    """Set arm `which` ('R'/'L') to point at target (local units)."""
    j = joints(g)
    s = j['sh' + which]
    a = math.atan2(target[0] - s[0], target[1] - s[1])
    setattr(g, which, (a, 0.06 if which == 'R' else -0.06))


def _limb(P, pts, w, col, dk, side=-1):
    P.limb(pts, w, col, ow=OW, oc=NAVY)
    sh = [(x + side * w * 0.22, y) for x, y in pts]          # soft shadow on the side away from the key light
    P.line(sh, w * P.s * 0.42, dk[:3] + (150,))
    hi = [(x - side * w * 0.26, y - 0.3) for x, y in pts]
    P.line(hi, max(1.5, w * P.s * 0.14), shade(col, 0.35)[:3] + (170,))


def _shoe(P, a, side):
    x, y = a
    body = [(x - 4.8, y - 2.6), (x + 4.8, y - 2.6), (x + 5.6, y + 0.6), (x + 5.2, y + 2.4), (x - 5.2, y + 2.4), (x - 5.6, y + 0.6)]
    P.poly(body, SHOE, ow=OW, oc=NAVY)
    gfill(P, body, (255, 255, 255, 0), (150, 160, 185, 140), (x + 3, y - 3), (x - 4, y + 2))
    P.fillpoly([(x - 5.4, y + 1.0), (x + 5.4, y + 1.0), (x + 5.0, y + 2.4), (x - 5.0, y + 2.4)], SOLE)
    P.line([(x - 3.4 * side, y - 1.6), (x + 0.6 * side, y - 0.4), (x + 3.6 * side, y - 1.4)], max(2, 0.8 * P.s), SOLE)   # side stripe


def _hand(P, w, e, kind, side):
    a = math.atan2(w[0] - e[0], w[1] - e[1])
    c = add(w, a, 1.6)
    if kind == 'point':
        tip = add(c, a, 6.2)
        P.limb([c, tip], 1.9, SKIN, ow=OW, oc=NAVY)
        P.circle(c, 3.0, SKIN, ow=OW, oc=NAVY)
        P.limb([add(c, a + 1.3 * side, 1.6), add(c, a + 0.9 * side, 3.4)], 1.6, SKIN_DK, ow=1.5, oc=NAVY)
    elif kind == 'thumb':
        P.circle(c, 3.2, SKIN, ow=OW, oc=NAVY)
        P.limb([(c[0], c[1] - 1.5), (c[0] + 0.4 * side, c[1] - 6.0)], 2.0, SKIN, ow=OW, oc=NAVY)
        for k in range(3): P.line([(c[0] - 2.2, c[1] - 0.8 + k * 1.4), (c[0] + 1.6, c[1] - 0.8 + k * 1.4)], max(1.5, 0.35 * P.s), SKIN_DK)
    elif kind == 'open':
        P.ellipse(c, 3.3, 3.6, SKIN, ow=OW, oc=NAVY)
        for k in (-1.2, -0.4, 0.4, 1.2):
            P.limb([add(c, a + k * 0.32, 2.4), add(c, a + k * 0.36, 5.2)], 1.3, SKIN, ow=1.6, oc=NAVY)
        P.limb([add(c, a + 1.5 * side, 2.2), add(c, a + 1.1 * side, 4.4)], 1.3, SKIN, ow=1.6, oc=NAVY)
    else:   # rest / hip: rounded fist
        P.circle(c, 3.0, SKIN, ow=OW, oc=NAVY)
        P.circle((c[0] - 0.8, c[1] - 0.9), 1.2, SKIN_HI[:3] + (160,), ow=0)


def _arm(P, j, side):
    """Arm + short sleeve, drawn before the torso so the tee covers the shoulder joint."""
    s, e, w = j['sh' + side], j['e' + side], j['w' + side]
    _limb(P, [s, e, w], 4.4, SKIN, SKIN_DK, side=-1)
    sl = (s[0] + (e[0] - s[0]) * 0.55, s[1] + (e[1] - s[1]) * 0.55)
    P.limb([s, sl], 7.0, TEE, ow=OW, oc=NAVY)
    P.line([(s[0] - 1.4, s[1] + 0.6), (sl[0] - 1.4, sl[1])], 2.2 * P.s, TEE_DK[:3] + (140,))


def _face(P, c, g):
    t = g.turn * 2.2
    fx = lambda dx: c[0] + dx + t
    surprised = g.expr == 'surprised'
    # glasses frames + eyes
    for sx in (-1, 1):
        ex, ey = fx(sx * 5.4), c[1] + 0.2
        lx, ly = g.look[0] * 1.1, g.look[1] * 0.8
        if g.blink > 0.6:
            P.line([(ex - 1.8, ey + 0.3), (ex + 1.8, ey + 0.3)], max(2, 0.55 * P.s), NAVY)
        else:
            rx, ry = (2.25, 2.25) if surprised else (2.0, 1.75)
            P.ellipse((ex, ey), rx, ry * (1 - 0.8 * g.blink), (255, 255, 255, 255), ow=0)
            P.circle((ex + lx, ey + ly), 1.05 if surprised else 1.3, NAVY, ow=0)
            P.circle((ex + lx + 0.45, ey + ly - 0.5), 0.36, (255, 255, 255, 255), ow=0)
        lens = (ex - 4.3, ey - 3.3, ex + 4.3, ey + 3.1)
        P.rrect(lens, 1.3, None, ow=1.25 * P.s / 2, oc=GLASS)
        P.fillpoly([(lens[0] + 1.2, lens[3] - 0.6), (lens[0] + 3.6, lens[1] + 0.6), (lens[0] + 5.0, lens[1] + 0.6), (lens[0] + 2.6, lens[3] - 0.6)], (255, 255, 255, 70))
        by = ey - 5.3 - g.brow * 1.6 - (1.0 if surprised else 0)
        tilt = 0.5 * sx * (g.brow - 0.3)
        P.line([(ex - 2.8, by + tilt), (ex + 2.8, by - tilt)], 1.15 * P.s, HAIR)
    P.line([(fx(-1.0), c[1] - 0.3), (fx(1.0), c[1] - 0.3)], 1.0 * P.s, GLASS)         # bridge
    P.line([(fx(-9.7), c[1] - 0.8), (c[0] - 12.4, c[1] - 1.2)], 0.9 * P.s, GLASS)
    P.line([(fx(9.7), c[1] - 0.8), (c[0] + 12.4, c[1] - 1.2)], 0.9 * P.s, GLASS)
    # nose, cheeks, mouth
    P.fillpoly([(fx(-0.2), c[1] + 1.8), (fx(1.3), c[1] + 4.6), (fx(-0.9), c[1] + 4.8)], SKIN_DK[:3] + (170,))
    for sx in (-1, 1): P.ellipse((fx(sx * 7.0), c[1] + 4.6), 2.0, 1.1, CHEEK, ow=0)
    my = c[1] + 7.4
    op = max(g.mouth, 0.85 if surprised else 0.0)
    if op > 0.08:
        h = 0.6 + 2.6 * op; wdt = 2.2 + 0.6 * op if not surprised else 1.8
        P.ellipse((fx(0), my + h * 0.35), wdt, h, (110, 34, 40, 255), ow=1.1 * P.s / 2, oc=NAVY)
        P.ellipse((fx(0), my + h * 0.85), wdt * 0.6, h * 0.35, (214, 96, 96, 255), ow=0)
        P.fillpoly([(fx(-wdt * 0.7), my - h * 0.5), (fx(wdt * 0.7), my - h * 0.5), (fx(wdt * 0.6), my - h * 0.15), (fx(-wdt * 0.6), my - h * 0.15)], (255, 255, 255, 230))
    else:
        P.line(bez((fx(-3.2), my - 0.4), (fx(0), my + 2.2), (fx(3.2), my - 0.4), 10), 0.75 * P.s, (110, 34, 40, 255))


def _head(P, c, g):
    # ears
    for sx in (-1, 1):
        P.ellipse((c[0] + sx * 12.3, c[1] + 1.2), 2.3, 3.2, SKIN, ow=OW, oc=NAVY)
        P.ellipse((c[0] + sx * 12.4, c[1] + 1.3), 1.0, 1.8, SKIN_DK, ow=0)
    face = [(c[0] + 12.0 * math.copysign(abs(math.cos(a)) ** 0.75, math.cos(a)),
             c[1] + (13.8 if math.sin(a) > 0 else 12.4) * math.copysign(abs(math.sin(a)) ** 0.85, math.sin(a)))
            for a in [i * 2 * math.pi / 40 for i in range(40)]]
    P.poly(face, SKIN, ow=OW, oc=NAVY)
    gfill(P, face, SKIN_HI[:3] + (120,), SKIN_DK[:3] + (150,), (c[0] + 9, c[1] - 6), (c[0] - 11, c[1] + 9))   # warm key from right
    P.line([(c[0] - 11.2, c[1] - 4), (c[0] - 11.6, c[1] + 4), (c[0] - 8.5, c[1] + 11)], max(2, 0.5 * P.s), RIM[:3] + (150,), cap=False)
    _face(P, c, g)
    # hair: messy mass + fringe + two cowlick strands
    top = arcpts((c[0], c[1] - 3.0), 13.6, math.pi + 0.05, 2 * math.pi - 0.05, 20)
    hair = [(c[0] - 13.4, c[1] + 0.5), (c[0] - 13.0, c[1] - 5.2)] + top + [(c[0] + 13.0, c[1] - 5.2), (c[0] + 13.4, c[1] + 0.5),
            (c[0] + 11.6, c[1] - 2.8), (c[0] + 9.0, c[1] - 6.4), (c[0] + 4.0, c[1] - 7.2), (c[0] - 1.0, c[1] - 6.0),
            (c[0] - 3.4, c[1] - 7.6), (c[0] - 8.6, c[1] - 6.6), (c[0] - 11.4, c[1] - 3.0)]
    P.poly(hair, HAIR, ow=OW, oc=NAVY)
    gfill(P, hair, (90, 70, 74, 150), (20, 14, 18, 0), (c[0] + 8, c[1] - 15), (c[0] - 2, c[1] - 4))
    P.line(bez((c[0] - 7, c[1] - 12.5), (c[0] - 1, c[1] - 15.5), (c[0] + 5.5, c[1] - 13.5), 10), 1.4 * P.s, HAIR_HI)
    P.line(bez((c[0] + 7.5, c[1] - 12.8), (c[0] + 10, c[1] - 13.6), (c[0] + 11.4, c[1] - 11.0), 6), 0.9 * P.s, HAIR_HI)
    for dx, h in ((-2.2, 4.4), (1.6, 3.6)):                                          # cowlicks
        P.limb([(c[0] + dx, c[1] - 15.6), (c[0] + dx + 0.8, c[1] - 15.6 - h), (c[0] + dx + 2.4, c[1] - 15.6 - h - 0.6)], 1.3, HAIR, ow=OW * 0.8, oc=NAVY)
    P.line(arcpts((c[0], c[1] - 3.0), 13.9, math.pi + 0.4, math.pi + 1.2, 8), max(2, 0.45 * P.s), RIM[:3] + (170,), cap=False)


def draw_guy(P, g, shadow=True):
    j = joints(g)
    if shadow:
        glow(P, ((j['aR'][0] + j['aL'][0]) / 2, 0.6), 22, (5, 10, 25), 0.75)
    # legs: skin shins, black shorts, socks + trainers
    for side, sg in (('L', -1), ('R', 1)):
        hipj = (j['hip'][0] + sg * 4.6, j['hip'][1])
        _limb(P, [j['k' + side], j['a' + side]], 4.6, SKIN, SKIN_DK)
        P.limb([(j['a' + side][0], j['a' + side][1] - 2.6), (j['a' + side][0], j['a' + side][1] - 0.6)], 4.4, TEE, ow=OW * 0.7, oc=NAVY)
        _shoe(P, (j['a' + side][0] + sg * 0.6, j['a' + side][1] + 0.4), sg)
        knee_up = (j['k' + side][0] + (hipj[0] - j['k' + side][0]) * 0.12, j['k' + side][1] + (hipj[1] - j['k' + side][1]) * 0.12)
        P.limb([hipj, knee_up], 9.0, SHORTS, ow=OW, oc=NAVY)
    waist = [(j['hip'][0] - 10.2, j['hip'][1] - 3.4), (j['hip'][0] + 10.2, j['hip'][1] - 3.4), (j['hip'][0] + 9.6, j['hip'][1] + 4.6), (j['hip'][0] - 9.6, j['hip'][1] + 4.6)]
    P.poly(waist, SHORTS, ow=OW, oc=NAVY)
    for side, sg in (('L', -1), ('R', 1)):
        hipj = (j['hip'][0] + sg * 4.6, j['hip'][1])
        P.line([(hipj[0] + 2.2, hipj[1] + 1), (j['k' + side][0] + 1.6, j['k' + side][1] - 4)], max(2, 0.5 * P.s), SHORTS_HI)
    for side in ('L', 'R'): _arm(P, j, side)
    # torso (tee)
    n, h = j['neck'], j['hip']
    tee = [(j['shL'][0] - 1.2, j['shL'][1] - 1.0), (n[0] - 4.2, n[1] + 0.6), (n[0] + 4.2, n[1] + 0.6), (j['shR'][0] + 1.2, j['shR'][1] - 1.0),
           (j['shR'][0] + 1.8, j['shR'][1] + 4.0), (h[0] + 10.6, h[1] - 1.0), (h[0] + 10.2, h[1] + 1.6), (h[0] - 10.2, h[1] + 1.6),
           (h[0] - 10.6, h[1] - 1.0), (j['shL'][0] - 1.8, j['shL'][1] + 4.0)]
    # neck first (under the collar)
    P.limb([(n[0], n[1] + 1), (n[0], n[1] - 6)], 7.4, SKIN, ow=OW, oc=NAVY)
    P.fillpoly([(n[0] - 3.6, n[1] - 1.5), (n[0] + 3.6, n[1] - 1.5), (n[0] + 3.0, n[1] + 1.0), (n[0] - 3.0, n[1] + 1.0)], SKIN_DK[:3] + (200,))
    P.poly(tee, TEE, ow=OW, oc=NAVY)
    gfill(P, tee, (255, 250, 240, 0), TEE_DK[:3] + (210,), (h[0] + 6, n[1] + 2), (h[0] - 11, h[1]))
    P.arc((n[0], n[1] - 0.5), 4.4, 20, 160, max(2, 0.7 * P.s), TEE_DK)               # collar
    P.line([(h[0] - 3, h[1] - 8), (h[0] + 2.5, h[1] - 12)], max(1.5, 0.35 * P.s), TEE_DK[:3] + (180,))   # cloth folds
    P.line([(h[0] + 4, h[1] - 3), (h[0] + 8, h[1] - 6)], max(1.5, 0.35 * P.s), TEE_DK[:3] + (160,))
    P.line([tee[-1], tee[0]], max(2, 0.45 * P.s), RIM[:3] + (130,))
    for side, sg in (('L', -1), ('R', 1)):
        _hand(P, j['w' + side], j['e' + side], g.hand[0 if side == 'R' else 1], sg)
    _head(P, j['head'], g)
    return j
