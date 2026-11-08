"""Stickman rig: forward kinematics + flat-vector drawing for an original presenter ('Capper': round cream head, dot eyes,
red cap, thick charcoal limbs) and a crash-test dummy (sand limbs, joint discs, yellow/black crash markers).

Angles are absolute screen radians with 0 = straight down, +pi/2 = pointing right (dir = (sin a, cos a)).
    pose = Pose(lean=0.05, armF=(a1, a2), ...)           # front/back arm and leg (upper, lower), head tilt, look, blink
    j = presenter_joints(pose)                           # dict of joint positions, feet on y=0, ~100 units tall
    draw_presenter(P, j, pose)                           # P: vec.Pen (local units -> px)
    point_angle(j_shoulder, target)                      # helper for pointing at a world point
    draw_dummy(P, joints, w=3.4)                         # seated/standing crash dummy from any joint dict
    marker(P, c, r, spin)                                # yellow/black crash-test target
"""
import math
from dataclasses import dataclass, field
from .vec import INK, hexc, shade, arcpts

LIMB = hexc('#30333d')
LIMB_HI = hexc('#4a4e5a')
SKIN = hexc('#f4e4cf')
CHEEK = hexc('#f0b9a6')
CAP = hexc('#e5413b')
CAP_DK = hexc('#b42d2c')
SAND = hexc('#e7c77e')
SAND_DK = hexc('#b8955a')
YEL = hexc('#ffc928')
WHITE = (255, 255, 255, 255)

# proportions (units)
TORSO, NECK, HEAD_R = 30.0, 4.0, 12.5
THIGH, SHIN, UARM, FARM = 22.0, 22.0, 17.0, 16.0


def d(a): return (math.sin(a), math.cos(a))


def add(p, a, L): v = d(a); return (p[0] + v[0] * L, p[1] + v[1] * L)


@dataclass
class Pose:
    lean: float = 0.0                         # torso tilt, + leans right
    head: float = 0.0                         # head tilt
    armF: tuple = (0.35, -0.2)                # front arm (upper, lower relative)
    armB: tuple = (-0.35, 0.2)
    legF: tuple = (0.12, -0.05)
    legB: tuple = (-0.12, 0.05)
    look: tuple = (0.0, 0.0)                  # eye offset, -1..1
    blink: float = 0.0                        # 0 open .. 1 shut
    talk: float = 0.0                         # mouth open 0..1
    brow: float = 0.0                         # +1 raised (asking)
    face: int = 1                             # cap brim side: +1 right, -1 left
    hip_y: float = 0.0                        # bob / crouch offset
    squash: float = 1.0                       # 1 = normal; <1 squash, >1 stretch (about the feet)


def presenter_joints(p: Pose):
    # legs solved from the hip down; hip height adapts so the lower foot stays on y = 0
    hip0 = (0.0, 0.0)
    kF = add(hip0, p.legF[0], THIGH); fF = add(kF, p.legF[0] + p.legF[1], SHIN)
    kB = add(hip0, p.legB[0], THIGH); fB = add(kB, p.legB[0] + p.legB[1], SHIN)
    drop = max(fF[1], fB[1])
    sh = lambda q: (q[0], q[1] - drop + p.hip_y)
    hip, kF, fF, kB, fB = map(sh, (hip0, kF, fF, kB, fB))
    neck = add(hip, math.pi + p.lean, TORSO)
    shoulder = add(neck, p.lean, 3.0)
    head = add(neck, math.pi + p.lean + p.head * 0.5, NECK + HEAD_R)
    eF = add(shoulder, p.armF[0], UARM); hF = add(eF, p.armF[0] + p.armF[1], FARM)
    eB = add(shoulder, p.armB[0], UARM); hB = add(eB, p.armB[0] + p.armB[1], FARM)
    j = dict(hip=hip, neck=neck, sh=shoulder, head=head, eF=eF, hF=hF, eB=eB, hB=hB, kF=kF, fF=fF, kB=kB, fB=fB)
    if p.squash != 1.0:
        sx, sy = 1 / math.sqrt(p.squash), p.squash
        j = {k: (v[0] * sx, v[1] * sy) for k, v in j.items()}
    return j


def point_angle(frm, target):
    return math.atan2(target[0] - frm[0], target[1] - frm[1])


def _limb(P, pts, w, col, hi=True):
    P.limb(pts, w, col, ow=4)
    if hi:   # soft key light from the upper left: a thin lighter line along each limb
        off = [(x - w * 0.18, y - w * 0.12) for x, y in pts]
        P.line(off, max(2, w * P.s * 0.22), LIMB_HI)


def _shoe(P, foot, side, col):
    P.poly([(foot[0] - 3.5 * side, foot[1] - 4.2), (foot[0] + 6.5 * side, foot[1] - 3.2), (foot[0] + 8 * side, foot[1] - 0.6),
            (foot[0] + 7 * side, foot[1] + 0.8), (foot[0] - 4 * side, foot[1] + 0.8)], col, ow=4)
    P.line([(foot[0] - 3.4 * side, foot[1] - 0.2), (foot[0] + 7 * side, foot[1] - 0.2)], max(2, 1.2 * P.s), WHITE)


def draw_head(P, c, r, p: Pose, tilt=0.0):
    P.circle(c, r, SKIN, ow=5)
    P.ellipse((c[0] - r * 0.22, c[1] - r * 0.32), r * 0.5, r * 0.3, shade(SKIN, 0.35))            # soft top light
    lx, ly = p.look
    for sx in (-1, 1):
        ex, ey = c[0] + sx * r * 0.36 + lx * r * 0.16 + p.face * r * 0.1, c[1] - r * 0.02 + ly * r * 0.12
        h = r * 0.17 * max(0.12, 1 - p.blink)
        P.ellipse((ex, ey), r * 0.15, h, INK)
        if p.blink < 0.5: P.circle((ex + r * 0.05, ey - h * 0.45), r * 0.05, WHITE, ow=0)
        by = ey - r * (0.36 + 0.12 * p.brow)
        P.line([(ex - r * 0.17, by + sx * r * 0.03 * (1 - p.brow)), (ex + r * 0.17, by - sx * r * 0.03 * (1 - p.brow))],
               max(2, r * P.s * 0.11), INK)
        P.circle((ex - sx * 0 + sx * r * 0.08, c[1] + r * 0.32), r * 0.13, CHEEK, ow=0)
    mx, my = c[0] + lx * r * 0.12 + p.face * r * 0.08, c[1] + r * 0.42
    if p.talk > 0.08:
        P.ellipse((mx, my + r * 0.03), r * 0.16, r * (0.05 + 0.17 * p.talk), hexc('#7a2b2b'), ow=3)
    else:
        P.arc((mx, my - r * 0.18), r * 0.24, 25, 155, max(2, r * P.s * 0.1), INK)
    # signature red cap: dome + brim towards the facing side + white top button
    top = arcpts(c, r + 1.2, math.pi + 0.12, 2 * math.pi - 0.12, 18)
    dome = top + [(c[0] + r * 0.98, c[1] - r * 0.3), (c[0] - r * 0.98, c[1] - r * 0.3)]
    P.poly(dome, CAP, ow=5)
    P.fillpoly([(c[0] - r * 0.95, c[1] - r * 0.42), (c[0] + r * 0.95, c[1] - r * 0.42), (c[0] + r * 0.98, c[1] - r * 0.3),
                (c[0] - r * 0.98, c[1] - r * 0.3)], CAP_DK)
    P.ellipse((c[0] - r * 0.35, c[1] - r * 0.86), r * 0.32, r * 0.13, shade(CAP, 0.3))
    f = p.face
    P.poly([(c[0] + f * r * 0.5, c[1] - r * 0.42), (c[0] + f * r * 1.62, c[1] - r * 0.36), (c[0] + f * r * 1.6, c[1] - r * 0.2),
            (c[0] + f * r * 0.5, c[1] - r * 0.24)], CAP_DK, ow=5)
    P.circle((c[0], c[1] - r - 1.6), r * 0.13, WHITE, ow=3)


def draw_presenter(P, j, p: Pose):
    w = 6.4
    _limb(P, [j['hip'], j['kB'], j['fB']], w, shade(LIMB, -0.25), hi=False)
    _shoe(P, j['fB'], p.face, shade(LIMB, -0.1))
    _limb(P, [j['sh'], j['eB'], j['hB']], w * 0.92, shade(LIMB, -0.25), hi=False)
    P.circle(j['hB'], 4.2, shade(SKIN, -0.08), ow=4)
    _limb(P, [j['hip'], j['neck']], w * 1.55, LIMB)
    _limb(P, [j['hip'], j['kF'], j['fF']], w, LIMB)
    _shoe(P, j['fF'], p.face, LIMB)
    draw_head(P, j['head'], HEAD_R, p)
    _limb(P, [j['sh'], j['eF'], j['hF']], w * 0.92, LIMB)
    P.circle(j['hF'], 4.4, SKIN, ow=4)


def marker(P, c, r, spin=0.0, ow=3):
    P.circle(c, r, YEL, ow=ow)
    for k in (0, 2):
        a0 = spin + k * math.pi / 2
        P.fillpoly([c] + arcpts(c, r, a0, a0 + math.pi / 2, 8), INK)
    P.circle(c, r * 0.16, YEL, ow=0)


def draw_dummy(P, j, w=3.4, far_alpha=True):
    """j needs: hip, neck, head, sh, eF, hF, kF, fF (optional eB, hB, kB, fB for the far side)."""
    far = shade(SAND, -0.28)
    if 'kB' in j: P.limb([j['hip'], j['kB'], j['fB']], w, far, ow=3)
    if 'eB' in j: P.limb([j['sh'], j['eB'], j['hB']], w * 0.9, far, ow=3)
    P.limb([j['hip'], j['kF'], j['fF']], w, SAND, ow=3)
    P.limb([j['hip'], j['neck']], w * 1.7, SAND, ow=3)
    P.line([(j['hip'][0] - w * 0.3, j['hip'][1] - w * 0.2), (j['neck'][0] - w * 0.35, j['neck'][1] + w * 0.4)],
           max(2, w * P.s * 0.28), shade(SAND, 0.35))
    for k in ('kF', 'hip'): P.circle(j[k], w * 0.42, SAND_DK, ow=2)
    hr = w * 0.95
    chest = (j['neck'][0] * 0.7 + j['hip'][0] * 0.3, j['neck'][1] * 0.7 + j['hip'][1] * 0.3)
    marker(P, chest, w * 0.5, 0.3, ow=2)
    P.limb([j['neck'], j['head']], w * 0.7, SAND_DK, ow=3)
    P.circle(j['head'], hr, SAND, ow=3)
    P.ellipse((j['head'][0] - hr * 0.25, j['head'][1] - hr * 0.35), hr * 0.45, hr * 0.25, shade(SAND, 0.35))
    marker(P, (j['head'][0] - hr * 0.1, j['head'][1] - hr * 0.05), hr * 0.5, 0.0, ow=2)
    P.limb([j['sh'], j['eF'], j['hF']], w * 0.9, SAND, ow=3)
    P.circle(j['eF'], w * 0.38, SAND_DK, ow=2)
    return chest
