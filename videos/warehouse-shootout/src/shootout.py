"""Warehouse shootout: two teams, tanks, falls, blood and explosions (1080x1920, 30 fps, 10 s).

Reuses characters, rifles and springs from ../../warehouse-standoff/src/render.py.

Usage:
  python videos/warehouse-shootout/src/shootout.py OUT.mp4
  python videos/warehouse-shootout/src/shootout.py SHEET.png --preview [t1,t2,...]
  python videos/warehouse-shootout/src/shootout.py FRAME.png --frame N
"""
import math
import random
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "warehouse-standoff" / "src"))
import render as R  # noqa: E402
from render import (ANKLE, BH, BLACK, BW, BY, FLOOR, FPS, GREEN, H, M, MUZZLE, PORT, SS, TORSO,  # noqa: E402
                    W, Canvas, Spring, draw_figure, draw_rifle, held_rifle, lerp, lerp2, locomotion,
                    muzzle_flash, rgb, rifle_tf, smooth, soft_sprite, stamp)

DUR = 10.0
S = 0.66                      # actor scale: actors are posed in "actor space", drawn at S about the floor
RNG = random.Random(11)


def A(pt):
    """Actor space -> world."""
    return (pt[0] * S, FLOOR + (pt[1] - FLOOR) * S)


def ax(wx):
    return wx / S


def clamp01(x):
    return max(0.0, min(1.0, x))


def ease_out(u):
    u = clamp01(u)
    return 1 - (1 - u) ** 3


class ActorCanvas(Canvas):
    def __init__(self, img):
        super().__init__(img)

    def p(self, pt):
        return Canvas.p(A(pt))

    def circle(self, c, r, fill):
        Canvas.circle(self, c, r * S, fill)

    def line(self, pts, fill, width):
        Canvas.line(self, pts, fill, width * S)


def ellipse(cv, c, rx, ry, fill=None, outline=None, width=1):
    x, y = Canvas.p(c)
    cv.d.ellipse([x - rx * SS, y - ry * SS, x + rx * SS, y + ry * SS],
                 fill=rgb(fill) if fill else None, outline=rgb(outline) if outline else None,
                 width=max(1, int(width * SS)))


# ---------------------------------------------------------------- sprites
GLOW = soft_sprite(170 * SS, 170 * SS, (255, 190, 80), 140, 26 * SS)
FIRE_A = soft_sprite(80 * SS, 80 * SS, (255, 140, 40), 235, 9 * SS)
FIRE_B = soft_sprite(80 * SS, 80 * SS, (255, 226, 140), 245, 9 * SS)
SMOKE_D = soft_sprite(90 * SS, 90 * SS, (50, 50, 53), 210, 14 * SS)
SMOKE_L = soft_sprite(60 * SS, 60 * SS, (200, 200, 202), 160, 9 * SS)
DUST = soft_sprite(60 * SS, 44 * SS, (196, 190, 176), 190, 8 * SS)
MIST = soft_sprite(40 * SS, 40 * SS, (150, 16, 20), 190, 6 * SS)
SHADOW = soft_sprite(130 * SS, 18 * SS, (20, 20, 22), 120, 5 * SS)


# ---------------------------------------------------------------- shots and events
# (time, shooter, impact kind, world target or victim id)
RIFLE_SHOTS = [
    (2.92, "b2", "concrete", (418, 532)), (3.02, "b2", "concrete", (440, 546)),
    (3.12, "b2", "concrete", (404, 538)), (3.22, "b2", "concrete", (430, 530)),
    (3.62, "g1", "wall", (812, 318)), (3.74, "g1", "floor", (770, 640)), (3.86, "g1", "flesh", "b1"),
    (4.40, "g2", "sand", (812, 548)), (4.52, "g2", "sand", (838, 540)), (4.64, "g2", "sand", (826, 556)),
    (5.10, "g1", "sand", (846, 538)), (5.22, "g1", "sand", (820, 546)), (5.34, "g1", "sand", (856, 544)),
    (5.55, "b2", "wood", (244, 528)), (5.65, "b2", "wood", (226, 534)),
]
SHOT_T = {}
for _t, _who, _k, _tg in RIFLE_SHOTS:
    SHOT_T.setdefault(_who, []).append(_t)

B_TANK_FIRE, B_SHELL_HIT = 5.85, 5.93
G_TANK_FIRE, G_SHELL_HIT = 6.85, 6.93
SECOND_BLAST = 7.35
HIT = {"b1": 3.90, "g2": B_SHELL_HIT, "b2": G_SHELL_HIT + 0.04}
FALL_KIND = {"b1": "back", "g2": "blast_back", "b2": "forward"}


def kick_for(who, t, rate=24, window=0.22):
    k = 0.0
    for s in SHOT_T.get(who, ()):
        if -1e-6 <= t - s < window:
            k = max(k, math.exp(-(t - s) * rate))
    return k


def window_w(t, wins, fade=0.12):
    v = 0.0
    for a, b in wins:
        v = max(v, smooth(a - fade, a + 0.05, t) * (1 - smooth(b, b + 0.25, t)))
    return v


def aim_angle(sh, f, tgt):
    return math.atan2(tgt[1] - sh[1], f * (tgt[0] - sh[0]))


def shoulder(hip, lean, f):
    return (hip[0] + f * math.sin(lean) * TORSO * 0.86, hip[1] - math.cos(lean) * TORSO * 0.86)


def build(hip, lean, feet, f, r=None, hands=None, head=0.0, modes=("fwd", "fwd"), toes=(None, None)):
    sh = shoulder(hip, lean, f)
    rifle = None
    if r is not None:
        grip, ang, front = held_rifle(sh, f, *r)
        hands, rifle = [front, grip], (grip, ang)
    return dict(hip=hip, lean=lean, feet=feet, hands=hands, rifle=rifle, head_tilt=head,
                knee_modes=modes, toes=toes, sh=sh)


READY = (30, 64, 0.42)


# ---------------------------------------------------------------- falls
def fall_pose(p0, tau, f, kind):
    if kind == "back":
        dirx, dist, lean_f, air, dur = -f, 70, -1.5, 0, 0.55
    elif kind == "blast_back":
        dirx, dist, lean_f, air, dur = -f, 210, -1.5, 95, 0.62
    else:
        dirx, dist, lean_f, air, dur = f, 120, 1.5, 55, 0.55
    h0 = p0["hip"]
    q = clamp01(tau / dur)
    qe = q * q if not air else q ** 1.4
    hip_f = (h0[0] + dirx * dist, FLOOR - 25)
    hx = lerp(h0[0], hip_f[0], ease_out(q) if not air else smooth(0, 1, q))
    hy = lerp(h0[1], hip_f[1], qe) - air * math.sin(math.pi * q)
    lean = lerp(p0["lean"], lean_f, qe if not air else smooth(0, 1, q))
    if tau > dur:
        b = tau - dur
        bounce = math.exp(-b * 8) * math.sin(b * 28)
        hy -= 9 * bounce
        lean -= 0.07 * bounce * (1 if lean_f > 0 else -1)
    hy = min(hy, FLOOR - 25)
    if lean_f < 0:
        feet_f = [(hip_f[0] + f * 150, FLOOR - ANKLE), (hip_f[0] + f * 118, FLOOR - ANKLE - 2)]
        rel = [(-f * 115, -14), (-f * 55, 22)]
        m = clamp01(q * 1.6)
        modes = [lambda p, m=m: f * p[0] * (1 - m) - p[1] * m] * 2
    else:
        feet_f = [(hip_f[0] - f * 165, FLOOR - ANKLE), (hip_f[0] - f * 148, FLOOR - ANKLE)]
        rel = [(f * 95, 12), (f * 40, 22)]
        modes = ["down", "down"] if q > 0.5 else ["fwd", "fwd"]
    wf = smooth(0.03, dur, tau)
    feet = []
    for i in range(2):
        fx, fy = lerp2(p0["feet"][i], feet_f[i], wf)
        feet.append((fx, min(FLOOR - ANKLE, fy - air * 0.7 * math.sin(math.pi * q))))
    sh_f = shoulder(hip_f, lean_f, f)
    hands_f = [(sh_f[0] + dx, min(FLOOR - 14, sh_f[1] + dy)) for dx, dy in rel]
    wh = smooth(0.0, dur * 0.9, tau)
    hands = []
    for i in range(2):
        hx_, hy_ = lerp2(p0["hands"][i], hands_f[i], wh)
        hands.append((hx_, min(FLOOR - 14, hy_ - 40 * math.sin(math.pi * q) * (1 - i * 0.5))))
    pose = build((hx, hy), lean, feet, f, hands=hands, head=lerp(0, -0.35 * (1 if lean_f < 0 else -1), q),
                 modes=tuple(modes))
    pose["landed"] = tau >= dur
    pose["fall_q"] = q
    pose["dur"] = dur
    pose["rest"] = (hip_f, sh_f)
    return pose


def dropped_rifle(p0, tau, f, dirx):
    grip, ang0 = p0["rifle"]
    vx, vy, g = dirx * 170, -280, 1700
    rest_y = FLOOR - 26
    tl = (-vy + math.sqrt(vy * vy + 2 * g * max(1.0, rest_y - grip[1]))) / g
    u = min(tau, tl)
    x = grip[0] + vx * u
    y = grip[1] + vy * u + 0.5 * g * u * u
    ang = ang0 + (2 * math.pi * dirx * f - ang0) * clamp01(tau / tl)
    if tau > tl:
        b = tau - tl
        y = rest_y - 14 * math.exp(-b * 9) * abs(math.sin(b * 18))
        ang = 2 * math.pi * dirx * f
    return (x, min(y, rest_y)), ang


# ---------------------------------------------------------------- G1: runs in, slides to the barrier
G1_X0, G1_XK, RUN_V, DEC, G1_T0 = -212.0, 455.0, 420.0, 0.6, 0.15
G1_RUN_END = G1_T0 + ((G1_XK - RUN_V * DEC / 2) - G1_X0) / RUN_V
G1_AIM0 = G1_RUN_END + 0.65
G1_DUCK = [(2.88, 3.3), (5.93, 6.35), (6.93, 7.15)]


def g1_x(t):
    if t <= G1_T0:
        return G1_X0
    if t <= G1_RUN_END:
        return G1_X0 + RUN_V * (t - G1_T0)
    s = min(t - G1_RUN_END, DEC)
    return G1_X0 + RUN_V * (G1_RUN_END - G1_T0) + RUN_V * (s - s * s / (2 * DEC))


def g1_kneel(t):
    return smooth(G1_RUN_END - 0.08, G1_RUN_END + 0.42, t)


def g1_targets(t):
    x = g1_x(t)
    loc = locomotion(x, x - G1_X0, 1, "run")
    w = g1_kneel(t)
    a = smooth(G1_AIM0, G1_AIM0 + 0.5, t)
    dip = math.sin(math.pi * smooth(G1_AIM0 - 0.25, G1_AIM0 + 0.2, t)) * (1 - a)
    dk = window_w(t, G1_DUCK)
    br = math.sin(t * 2.3)
    sh = (G1_XK + 11, FLOOR - 104 - TORSO * 0.86)
    if t < 3.95:
        bp = b1_alive(min(t, HIT["b1"]))
        tgt = (bp["hip"][0], bp["hip"][1] - TORSO * 0.6)
    else:
        tgt = (ax(860), FLOOR - 230)
    ang = max(-0.25, min(0.15, aim_angle(sh, 1, tgt)))
    run_r = (22, 60 + 8 * loc["bob"], -0.62 + 0.07 * loc["bob"])
    aim_r = (62, 20 + 1.2 * br, ang)
    r = [lerp(lerp(run_r[i], READY[i], w), aim_r[i], a) for i in range(3)]
    r = [lerp(r[i], READY[i], dk * 0.8) for i in range(3)]
    r[1] += 10 * dip
    r[2] += 0.18 * dip
    lean = lerp(loc["lean"] + 0.04 * loc["bob"], lerp(0.2, 0.1, a), w) + 0.1 * dip + 0.45 * dk
    head = lerp(-0.18 - 0.03 * loc["bob"], lerp(0.0, 0.1, a), w) + 0.35 * dk
    hipy = lerp(loc["hip"][1], FLOOR - 104 + 2 * br, w) + 30 * dk
    return dict(x=x, loc=loc, w=w, lean=lean, head=head, hipy=hipy, r=r)


def g1_pose(t):
    g = g1_targets(t)
    loc, w, x = g["loc"], g["w"], g["x"]
    lean, head, hipy = SPR["g1"](t)
    r = SPR["g1r"](t)
    k = kick_for("g1", t)
    r = [r[0] - 13 * k, r[1] + 2 * k, r[2] - 0.1 * k]
    kneel_feet = [(x + 88, FLOOR - ANKLE), (x - 80, FLOOR - 26)]
    feet = [lerp2(loc["feet"][i], kneel_feet[i], smooth(0, 0.7, w)) for i in range(2)]
    return build((x, hipy), lean - 0.05 * k, feet, 1, r, head=head - 0.1 * k,
                 toes=(None, (lerp(30, -14, w), lerp(4, 12, w))))


# ---------------------------------------------------------------- G2: standing behind crates
G2_X = ax(150)


def g2_alive(t):
    br = math.sin(t * 2.1 + 1)
    dk = window_w(t, [(5.55, 5.75)])
    hip = (G2_X, FLOOR - 191 + 1.5 * br + 22 * dk)
    lean = 0.07 + 0.25 * dk
    sh = shoulder(hip, lean, 1)
    b1 = b1_alive(min(t, HIT["b1"]))
    t1 = (b1["hip"][0], b1["hip"][1] - TORSO * 0.6)
    t2 = (ax(830), FLOOR - 160)
    m = smooth(3.9, 4.25, t)
    tgt = lerp2(t1, t2, m)
    ang = max(-0.3, min(0.2, aim_angle(sh, 1, tgt)))
    k = kick_for("g2", t)
    r = (62 - 13 * k, 20 + 2 * k, ang - 0.1 * k)
    r = tuple(lerp(r[i], READY[i], dk * 0.6) for i in range(3))
    feet = [(G2_X + 30, FLOOR - ANKLE), (G2_X - 34, FLOOR - ANKLE)]
    return build(hip, lean - 0.05 * k, feet, 1, r, head=0.05 + 0.3 * dk)


# ---------------------------------------------------------------- B1: walks in, aims, is shot
B1_X0, B1_X1, B1_T0, B1_STOP = ax(1190), ax(700), 1.15, 3.3


def b1_x(t):
    tt = max(0.0, min(t, B1_STOP)) - B1_T0
    T, D = B1_STOP - B1_T0, 0.7
    v = (B1_X0 - B1_X1) / (T - D / 2)
    if tt <= 0:
        return B1_X0
    if tt <= T - D:
        return B1_X0 - v * tt
    s = tt - (T - D)
    return B1_X0 - v * (T - D) - v * (s - s * s / (2 * D))


def b1_alive(t):
    f = -1
    x = b1_x(t)
    loc = locomotion(x, B1_X0 - x, f, "walk")
    w = smooth(B1_STOP - 0.3, B1_STOP + 0.2, t)
    stop = locomotion(B1_X1, B1_X0 - B1_X1, f, "walk")["feet"]
    stop = [(B1_X1 + 0.6 * (fx - B1_X1), FLOOR - ANKLE) for fx, _ in stop]
    feet = [lerp2(loc["feet"][i], stop[i], w) for i in range(2)]
    hip = (x, lerp(loc["hip"][1], FLOOR - 191 + 1.5 * math.sin(t * 2), w))
    lean = lerp(loc["lean"] + 0.02 * loc["bob"], 0.04, w)
    a = smooth(B1_STOP - 0.05, B1_STOP + 0.4, t)
    sh = shoulder(hip, lean, f)
    ang = max(-0.2, min(0.3, aim_angle(sh, f, (G1_XK + 30, FLOOR - 250))))
    low = (24, 70 + 4 * loc["bob"] * (1 - w), 0.62 + 0.06 * loc["sway"] * (1 - w))
    r = tuple(lerp(low[i], (62, 20, ang)[i], a) for i in range(3))
    return build(hip, lean, feet, f, r, head=-0.04 * loc["bob"] * (1 - w))


# ---------------------------------------------------------------- B2: kneeling behind sandbags
B2_X = ax(905)
B2_DUCK = [(4.38, 4.9), (5.08, 5.45)]


def b2_targets(t):
    f = -1
    br = math.sin(t * 2.4 + 2)
    dk = window_w(t, B2_DUCK)
    hipy = FLOOR - 104 + 2 * br + 48 * dk
    lean = 0.1 + 0.5 * dk
    sh = (B2_X - 11, FLOOR - 104 - TORSO * 0.86)
    t_g1 = (G1_XK + 40, FLOOR - 245)
    t_g2 = (ax(240), FLOOR - 190)
    tgt = lerp2(t_g1, t_g2, smooth(5.35, 5.5, t))
    ang = max(-0.25, min(0.3, aim_angle(sh, f, tgt)))
    a = smooth(2.5, 2.85, t)
    r = [lerp(READY[i], (62, 20, ang)[i], a) for i in range(3)]
    r = [lerp(r[i], READY[i], dk) for i in range(3)]
    return dict(lean=lean, head=0.4 * dk - 0.05, hipy=hipy, r=r)


def b2_pose(t):
    f = -1
    lean, head, hipy = SPR["b2"](t)
    r = SPR["b2r"](t)
    k = kick_for("b2", t)
    r = [r[0] - 13 * k, r[1] + 2 * k, r[2] - 0.1 * k]
    feet = [(B2_X - 88, FLOOR - ANKLE), (B2_X + 80, FLOOR - 26)]
    return build((B2_X, hipy), lean - 0.05 * k, feet, f, r, head=head - 0.1 * k, toes=(None, (14, 12)))


# ---------------------------------------------------------------- actor dispatch (alive or falling)
ALIVE = {"g1": g1_pose, "g2": g2_alive, "b1": b1_alive, "b2": b2_pose}
FACING = {"g1": 1, "g2": 1, "b1": -1, "b2": -1}
BASE = {}


def actor_pose(who, t):
    if who in HIT and t >= HIT[who]:
        f = FACING[who]
        p = fall_pose(BASE[who], t - HIT[who], f, FALL_KIND[who])
        return p
    return ALIVE[who](t)


SPR = {}


def init_motion():
    SPR["g1"] = Spring(lambda t: [g1_targets(t)[k] for k in ("lean", "head", "hipy")], 13, 0.45)
    SPR["g1r"] = Spring(lambda t: g1_targets(t)["r"], 15, 0.5)
    SPR["b2"] = Spring(lambda t: [b2_targets(t)[k] for k in ("lean", "head", "hipy")], 14, 0.5)
    SPR["b2r"] = Spring(lambda t: b2_targets(t)["r"], 15, 0.5)
    for who, th in HIT.items():
        BASE[who] = ALIVE[who](th)


# ---------------------------------------------------------------- tanks
TANK_G = dict(main="#5d7140", dark="#45542e", light="#71874e", track="#26272a", wheel="#4b4d50")
TANK_B = dict(main="#34363a", dark="#222326", light="#4a4d52", track="#18191a", wheel="#3c3e41")
TANK_GY, TANK_K = 508, 1.28
TB_X = 1010


def tank_g_x(t):
    return lerp(-520, 50, ease_out(t / 2.4))


def tank_b_x(t):
    return lerp(1580, TB_X, ease_out((t - 0.6) / 2.5))


def rock_of(t, stop, fire, hit=None):
    r = 0.0
    if t > stop:
        b = t - stop
        r += -0.035 * math.exp(-b * 4) * math.sin(b * 11)
    if t > fire:
        b = t - fire
        r += 0.05 * math.exp(-b * 5) * math.sin(b * 14 + 0.6)
    if hit and t > hit:
        b = t - hit
        r += -0.09 * math.exp(-b * 4) * math.sin(b * 12 + 0.4)
    return r


def draw_tank(cv, x0, f, pal, dist, elev, recoil, rock, t, damaged=0.0):
    k = TANK_K
    c, s = math.cos(rock), math.sin(rock)
    dk = 1 - 0.55 * damaged

    def T(px, py):
        xr, yr = px * c + py * s, -px * s + py * c
        return (x0 + f * xr * k, TANK_GY + yr * k)

    def P(pts, col, kk=1.0):
        cv.poly([T(*q) for q in pts], rgb(pal[col] if col in pal else col, dk * kk))

    def C(px, py, r, col, kk=1.0):
        cv.circle(T(px, py), r * k, rgb(pal[col] if col in pal else col, dk * kk))

    def L(a, b, col, w, kk=1.0):
        cv.line([T(*a), T(*b)], rgb(pal[col] if col in pal else col, dk * kk), w * k)

    P([(-170, -6), (-188, -34), (-172, -62), (168, -62), (186, -34), (168, -6), (150, 0), (-152, 0)], "track")
    spin = dist / (21 * k)
    for i in range(6):
        cx = -125 + 50 * i
        C(cx, -30, 21, "wheel")
        C(cx, -30, 8, "track")
        for j in range(3):
            a = spin + j * 2 * math.pi / 3
            L((cx + 9 * math.cos(a), -30 + 9 * math.sin(a)), (cx + 18 * math.cos(a), -30 + 18 * math.sin(a)),
              "track", 3)
    for cx in (-156, 156):
        C(cx, -36, 16, "wheel", 0.9)
        C(cx, -36, 6, "track")
    for i in range(22):
        xx = -165 + ((i * 16 - dist / k) % 336)
        L((xx, -62), (xx, -57), "wheel", 3)
        xb = -150 + ((i * 15 + dist / k) % 300)
        L((xb, -1), (xb, -6), "wheel", 3)
    P([(-184, -54), (176, -54), (182, -78), (-190, -78)], "main", 0.92)
    for xx in range(-150, 170, 60):
        L((xx, -76), (xx, -56), "dark", 2)
    P([(-190, -78), (182, -78), (210, -100), (182, -122), (-172, -122), (-192, -100)], "main")
    P([(-172, -122), (182, -122), (190, -116), (-178, -116)], "light")
    P([(-160, -114), (-108, -114), (-108, -100), (-160, -100)], "dark")
    C(200, -100, 5, "#d9d2a0")
    P([(-196, -96), (-208, -96), (-208, -84), (-196, -84)], "dark")
    P([(-72, -130), (62, -130), (62, -122), (-72, -122)], "dark")
    # barrel (behind turret front)
    e = elev
    pv = (84, -154)
    d = (math.cos(e), math.sin(e))
    b0 = (pv[0] + d[0] * (6 - recoil), pv[1] + d[1] * (6 - recoil))
    b1 = (pv[0] + d[0] * (205 - recoil), pv[1] + d[1] * (205 - recoil))
    L(b0, b1, "dark", 12)
    m0 = (pv[0] + d[0] * (110 - recoil), pv[1] + d[1] * (110 - recoil))
    m1 = (pv[0] + d[0] * (140 - recoil), pv[1] + d[1] * (140 - recoil))
    L(m0, m1, "dark", 17)
    L((b1[0] - d[0] * 22, b1[1] - d[1] * 22), b1, "track", 19)
    P([(-112, -130), (72, -130), (104, -152), (80, -180), (-82, -184), (-114, -162)], "main", 1.05)
    P([(-82, -184), (80, -180), (88, -172), (-90, -176)], "light")
    L((-100, -150), (60, -150), "dark", 2)
    P([(70, -146), (98, -146), (98, -162), (70, -162)], "dark")
    C(-40, -186, 17, "dark")
    C(-40, -190, 11, "main")
    sway = 0.25 * rock + 0.05 * math.sin(t * 3.1)
    base = (-96, -180)
    tip = (base[0] + 140 * math.sin(sway), base[1] - 140 * math.cos(sway))
    L(base, tip, "track", 2.5)
    if damaged:
        for (px, py, r) in ((-60, -150, 26), (20, -100, 34), (-120, -95, 22), (110, -105, 18)):
            C(px, py, r * damaged, "#151515")
    return T(*b1), (f * d[0], d[1])


# ---------------------------------------------------------------- particles and effects
class Part:
    __slots__ = ("t0", "x", "y", "vx", "vy", "g", "floor", "kind", "size", "col", "life", "spin")

    def __init__(self, t0, x, y, vx, vy, g, floor, kind, size, col, life=9.0, spin=0.0):
        self.t0, self.x, self.y, self.vx, self.vy, self.g = t0, x, y, vx, vy, g
        self.floor, self.kind, self.size, self.col, self.life, self.spin = floor, kind, size, col, life, spin

    def state(self, t):
        dt = t - self.t0
        if dt < 0 or dt > self.life:
            return None
        if self.g > 0:
            disc = self.vy * self.vy + 2 * self.g * max(0.0, self.floor - self.y)
            tl = (-self.vy + math.sqrt(disc)) / self.g
        else:
            tl = 1e9
        u = min(dt, tl)
        x = self.x + self.vx * u
        y = self.y + self.vy * u + 0.5 * self.g * u * u
        return x, y, dt >= tl, dt


PARTS, PUFFS, TRACERS, HOLES, EXPLOSIONS, SHELLS, SHAKES, CASINGS = [], [], [], [], [], [], [], []


def spawn_blood(t0, pos, dirx, n=18, power=1.0):
    for _ in range(n):
        sp = RNG.uniform(90, 330) * power
        a = RNG.uniform(-1.0, 0.35)
        PARTS.append(Part(t0, pos[0], pos[1], dirx * sp * math.cos(a), sp * math.sin(a) - RNG.uniform(40, 160),
                          1300, FLOOR + RNG.uniform(-4, 16), "blood", RNG.uniform(1.8, 4.2),
                          RNG.choice(("#8e1013", "#a5171b", "#6f0a0d"))))
    PUFFS.append((t0, pos, MIST, 0.32, 0.4, 1.3 * power, 10, 0.95))


def spawn_impact(t0, pos, kind, dirx):
    if kind in ("concrete", "wall", "floor"):
        for _ in range(7):
            sp = RNG.uniform(120, 340)
            a = RNG.uniform(-2.2, -0.6)
            PARTS.append(Part(t0, pos[0], pos[1], -dirx * abs(sp * math.cos(a)), sp * math.sin(a), 900,
                              FLOOR + 10, "spark", 1.5, "#ffd36b", life=RNG.uniform(0.12, 0.28)))
        for _ in range(5):
            PARTS.append(Part(t0, pos[0], pos[1], -dirx * RNG.uniform(30, 160), -RNG.uniform(60, 220), 1200,
                              FLOOR + RNG.uniform(-2, 14), "chip", RNG.uniform(1.5, 3.2),
                              "#d9dadb" if kind != "floor" else "#8d8f92"))
        PUFFS.append((t0, pos, SMOKE_L, 0.6, 0.3, 1.0, 26, 0.8))
        if kind != "floor":
            HOLES.append((t0, pos))
    elif kind == "sand":
        for _ in range(12):
            PARTS.append(Part(t0, pos[0], pos[1], -dirx * RNG.uniform(20, 170), -RNG.uniform(80, 260), 1200,
                              FLOOR + RNG.uniform(0, 14), "sand", RNG.uniform(1.4, 2.6), "#b9a679", life=1.2))
        PUFFS.append((t0, pos, DUST, 0.8, 0.4, 1.3, 20, 0.9))
    elif kind == "wood":
        for _ in range(6):
            PARTS.append(Part(t0, pos[0], pos[1], -dirx * RNG.uniform(40, 200), -RNG.uniform(100, 260), 1200,
                              FLOOR + RNG.uniform(0, 14), "chip", RNG.uniform(1.8, 3.4), "#4f5d39"))
        for _ in range(4):
            PARTS.append(Part(t0, pos[0], pos[1], -dirx * RNG.uniform(120, 300), -RNG.uniform(60, 250), 900,
                              FLOOR + 10, "spark", 1.5, "#ffd36b", life=0.2))
        PUFFS.append((t0, pos, DUST, 0.6, 0.3, 1.0, 20, 0.7))


def spawn_explosion(t0, pos, size, gy):
    rng = random.Random(int(t0 * 1000))
    fire = [(rng.uniform(-math.pi, 0.2), rng.uniform(20, 120), rng.uniform(0.8, 1.6), rng.uniform(0, 0.08))
            for _ in range(14)]
    smoke = [(rng.uniform(-math.pi, 0), rng.uniform(10, 110), rng.uniform(0.9, 1.6), rng.uniform(0.08, 0.5))
             for _ in range(16)]
    EXPLOSIONS.append(dict(t0=t0, pos=pos, s=size, gy=gy, fire=fire, smoke=smoke))
    for _ in range(int(26 * size)):
        sp = rng.uniform(180, 620) * size
        a = rng.uniform(-math.pi + 0.15, -0.15)
        PARTS.append(Part(t0, pos[0], pos[1], sp * math.cos(a), sp * math.sin(a), 1300,
                          gy + rng.uniform(-6, 26), "debris", rng.uniform(2.5, 6.5) * size ** 0.5,
                          rng.choice(("#2b2b2c", "#3d3e40", "#4b4c4f", "#57502f")), spin=rng.uniform(-12, 12)))
    for _ in range(int(30 * size)):
        sp = rng.uniform(250, 800) * size
        a = rng.uniform(-math.pi, 0)
        PARTS.append(Part(t0, pos[0], pos[1], sp * math.cos(a), sp * math.sin(a), 700, gy + 20, "spark", 2.0,
                          rng.choice(("#ffd36b", "#ffae3b", "#fff2b0")), life=rng.uniform(0.25, 0.7)))
    for _ in range(int(10 * size)):
        PARTS.append(Part(t0 + rng.uniform(0, 0.3), pos[0] + rng.uniform(-40, 40), pos[1] - rng.uniform(0, 40),
                          rng.uniform(-60, 60), -rng.uniform(80, 200), -40, -1e9, "ember", rng.uniform(1.5, 2.6),
                          "#ffb347", life=rng.uniform(0.8, 1.8)))
    SHAKES.append((t0, 26 * size, 6.0))


def spawn_casing(t0, port, f):
    CASINGS.append(Part(t0, port[0], port[1], -f * RNG.uniform(80, 120), -RNG.uniform(200, 250), 1000,
                        FLOOR + RNG.uniform(-2, 10), "casing", 1.0, "#c9a046", spin=RNG.uniform(16, 24)))


def build_events():
    for t0, who, kind, tgt in RIFLE_SHOTS:
        p = actor_pose(who, t0)
        f = FACING[who]
        T = rifle_tf(p["rifle"][0], p["rifle"][1], f)
        mz, port = A(T(*MUZZLE)), A(T(*PORT))
        if tgt == "b1":
            b = BASE["b1"]
            hit = A(((b["hip"][0] + b["sh"][0]) / 2, (b["hip"][1] + b["sh"][1]) / 2 - 10))
        else:
            hit = tgt
        travel = 0.045
        TRACERS.append((t0, mz, hit, travel))
        spawn_casing(t0, port, f)
        if kind == "flesh":
            spawn_blood(t0 + travel, hit, f, 22, 1.1)
        else:
            spawn_impact(t0 + travel, hit, kind, f)
        SHAKES.append((t0, 3.0, 22.0))
    # tank shells
    SHELLS.append(("b", B_TANK_FIRE, B_SHELL_HIT, (232, FLOOR - 30)))
    SHELLS.append(("g", G_TANK_FIRE, G_SHELL_HIT, (TB_X - 20, 400)))
    spawn_explosion(B_SHELL_HIT, (232, FLOOR - 30), 1.0, FLOOR)
    spawn_explosion(G_SHELL_HIT, (TB_X - 20, 400), 1.2, TANK_GY + 4)
    spawn_explosion(SECOND_BLAST, (TB_X + 20, 340), 0.75, TANK_GY + 4)
    SHAKES.append((B_TANK_FIRE, 7.0, 8.0))
    SHAKES.append((G_TANK_FIRE, 7.0, 8.0))
    # people hit by blasts
    g2 = BASE["g2"]
    spawn_blood(B_SHELL_HIT + 0.02, A(g2["sh"]), -1, 16, 1.0)
    b2 = BASE["b2"]
    spawn_blood(HIT["b2"] + 0.02, A(b2["sh"]), -1, 16, 1.0)
    # burning tank smoke column
    for i, te in enumerate(np.arange(G_SHELL_HIT + 0.3, DUR, 0.07)):
        PUFFS.append((te, (TB_X + RNG.uniform(-30, 30), 330 + RNG.uniform(-8, 8)), SMOKE_D, 3.0,
                      0.5, 1.7, 70, 0.55))
    # slide dust
    for te in np.arange(G1_RUN_END - 0.05, G1_RUN_END + 0.45, 0.05):
        PUFFS.append((te, A((g1_x(te) - 15, FLOOR - 8)), DUST, 0.9, 0.3, 1.0, 30, 0.6))


def draw_particles(cv, t, landed_pass):
    for p in PARTS + CASINGS:
        st = p.state(t)
        if st is None:
            continue
        x, y, landed, dt = st
        if landed != landed_pass and p.kind not in ("spark", "ember"):
            continue
        if p.kind in ("spark", "ember") and landed_pass:
            continue
        k = p.kind
        if k == "blood":
            if landed:
                ellipse(cv, (x, y), p.size * 1.8, p.size * 0.6, p.col)
            else:
                cv.circle((x, y), p.size, p.col)
        elif k == "spark":
            vx, vy = p.vx, p.vy + p.g * dt
            sp = math.hypot(vx, vy) or 1
            cv.line([(x, y), (x - vx / sp * 12, y - vy / sp * 12)], p.col, 2)
        elif k == "ember":
            cv.circle((x, y), p.size * (1 - dt / p.life), p.col)
        elif k in ("chip", "sand"):
            if p.kind == "sand" and landed:
                continue
            cv.circle((x, y), p.size, p.col)
        elif k == "debris":
            rot = p.spin * (dt if not landed else 0.4)
            pts = [(x + p.size * math.cos(rot + a), y + p.size * 0.7 * math.sin(rot + a))
                   for a in (0, 1.9, 3.3, 4.6)]
            cv.poly(pts, p.col)
        elif k == "casing":
            rot = p.spin * min(dt, 0.6)
            c, s = math.cos(rot), math.sin(rot)
            cv.poly([(x + dx * c - dy * s, y + dx * s + dy * c)
                     for dx, dy in ((-4, -1.7), (4, -1.7), (4, 1.7), (-4, 1.7))], p.col)


def draw_puffs(img, t):
    for t0, pos, spr, life, s0, s1, rise, op in PUFFS:
        dt = t - t0
        if 0 <= dt < life:
            u = dt / life
            fade = min(1.0, u / 0.08) * (1 - u) ** 1.4
            stamp(img, spr, (pos[0] + 14 * dt, pos[1] - rise * dt), lerp(s0, s1, 1 - (1 - u) ** 2), op * fade)


def draw_tracers(cv, t):
    for t0, a, b, tr in TRACERS:
        u = (t - t0) / tr
        if 0 <= u <= 1.4:
            p1 = lerp2(a, b, min(1.0, u))
            p0 = lerp2(a, b, max(0.0, u - 0.45))
            cv.line([p0, p1], "#ffcf6a", 4)
            cv.line([p0, p1], "#fff6d2", 1.6)
    for who, tf, th, tgt in SHELLS:
        u = (t - tf) / (th - tf)
        if 0 <= u <= 1.0:
            m = TANK_MUZZLE[who]
            p1 = lerp2(m, tgt, u)
            p0 = lerp2(m, tgt, max(0.0, u - 0.35))
            cv.line([p0, p1], "#ffb347", 8)
            cv.line([p0, p1], "#fff3c4", 3)


def draw_explosions(img, cv, t):
    for e in EXPLOSIONS:
        dt = t - e["t0"]
        if dt < 0 or dt > 4.5:
            continue
        x, y = e["pos"]
        s = e["s"]
        for ang, spd, sz, dl in e["smoke"]:
            d = dt - dl
            if 0 <= d < 4.0:
                u = d / 4.0
                px = x + math.cos(ang) * spd * s * min(1.0, d * 2) ** 0.5 + 10 * d
                py = y + math.sin(ang) * spd * s * 0.6 * min(1.0, d * 2) ** 0.5 - 45 * d
                op = 0.8 * min(1.0, d / 0.15) * (1 - u) ** 1.3
                stamp(img, SMOKE_D, (px, py), sz * s * (0.7 + 1.4 * u), op)
        if dt < 0.3:
            ellipse(cv, (x, e["gy"]), 40 + 900 * s * dt, (40 + 900 * s * dt) * 0.13, None,
                    outline="#e6e4dc", width=4 * (1 - dt / 0.3))
        for ang, spd, sz, dl in e["fire"]:
            d = dt - dl
            if 0 <= d < 0.8:
                u = d / 0.8
                r = spd * s * ease_out(d / 0.3)
                px, py = x + math.cos(ang) * r, y + math.sin(ang) * r * 0.75 - 50 * s * d
                stamp(img, FIRE_B if u < 0.3 else FIRE_A, (px, py), sz * s * (0.6 + 0.9 * u), (1 - u) ** 1.2)
        if dt < 0.1:
            cv.circle((x, y), 60 * s * (0.6 + dt / 0.1 * 0.5), "#fff4c8")
        if dt < 0.4:
            stamp(img, GLOW, (x, y), 2.6 * s, 1 - dt / 0.4)


def draw_fire(img, t):
    if t < G_SHELL_HIT + 0.15:
        return
    on = smooth(G_SHELL_HIT + 0.1, G_SHELL_HIT + 0.5, t)
    for i, (dx, dy) in enumerate(((-30, 412), (10, 404), (40, 418), (-60, 426), (70, 430))):
        fl = 0.75 + 0.25 * math.sin(t * 17 + i * 2.1) + 0.12 * math.sin(t * 31 + i)
        stamp(img, FIRE_A, (TB_X + dx, dy - 50 - 10 * fl), 0.9 * fl, 0.9 * on)
        stamp(img, FIRE_B, (TB_X + dx, dy - 44), 0.5 * fl, 0.85 * on)
    stamp(img, GLOW, (TB_X, 370), 1.6, 0.35 * on * (0.85 + 0.15 * math.sin(t * 13)))


# ---------------------------------------------------------------- scene props
SAND = [(x0 + i * 44, row) for row, x0, n in ((0, 772, 3), (1, 784, 3), (2, 792, 2), (3, 804, 2))
        for i in range(n)]


def draw_sandbags(cv):
    for (x, row) in SAND:
        y = FLOOR + 2 - row * 27
        ellipse(cv, (x + 22, y - 12), 26, 15, "#8b7e5a")
        ellipse(cv, (x + 22, y - 15), 23, 11, "#a79a72")
        cv.line([(x + 4, y - 14), (x + 40, y - 14)], "#968a64", 2)


def draw_barrier(acv):
    dx = 222
    pts = [(x + dx, y) for x, y in R.BARRIER]
    acv.poly(pts, "#e2e3e4")
    acv.poly([(448 + dx, 592), (484 + dx, 646), (484 + dx, 668), (458 + dx, 668), (442 + dx, 466)], "#c9cbcd")
    acv.poly([(366 + dx, 592), (326 + dx, 646), (326 + dx, 668), (338 + dx, 668), (374 + dx, 594)], "#d3d5d7")
    acv.poly([(372 + dx, 466), (442 + dx, 466), (442 + dx, 472), (372 + dx, 472)], "#f0f1f2")
    acv.circle((396 + dx, 520), 6, "#3a3b3d")


def draw_holes(cv, t):
    for t0, pos in HOLES:
        if t >= t0:
            cv.circle(pos, 2.6, "#3b3c3e")
            cv.circle((pos[0] + 0.8, pos[1] + 0.8), 1.2, "#1f2021")


def draw_cover_crates(cv):
    R.crate(cv, 178, FLOOR - 58, 280, FLOOR + 8, latches=2)
    R.crate(cv, 186, FLOOR - 122, 272, FLOOR - 58, latches=2)


# ---------------------------------------------------------------- frame
TANK_MUZZLE = {}


def tank_state(who, t):
    if who == "g":
        x = tank_g_x(t)
        return dict(x=x, dist=x + 520, f=1, pal=TANK_G,
                    elev=lerp(-0.02, -0.1, smooth(6.2, 6.7, t)),
                    recoil=36 * math.exp(-(t - G_TANK_FIRE) * 6) if t >= G_TANK_FIRE else 0,
                    rock=rock_of(t, 2.4, G_TANK_FIRE), dmg=0.0)
    x = tank_b_x(t)
    hit = t >= G_SHELL_HIT
    return dict(x=x, dist=-(1580 - x), f=-1, pal=TANK_B,
                elev=lerp(0.0, 0.05, smooth(5.2, 5.7, t)) + (0.3 * smooth(G_SHELL_HIT, G_SHELL_HIT + 0.5, t)),
                recoil=36 * math.exp(-(t - B_TANK_FIRE) * 6) if t >= B_TANK_FIRE else 0,
                rock=rock_of(t, 3.1, B_TANK_FIRE, G_SHELL_HIT), dmg=1.0 if hit else 0.0)


def tank_blast(img, cv, t, fire_t, mz, d):
    dt = t - fire_t
    if -1e-6 <= dt < 3 / FPS:
        k = 1.0 if dt < 1 / FPS else 0.6
        c, s = d
        px, py = -s, c
        pts = [(mz[0] + c * a + px * b, mz[1] + s * a + py * b)
               for a, b in ((0, -16 * k), (90 * k, 0), (0, 16 * k))]
        cv.poly(pts, "#ffa62b")
        cv.poly([(mz[0] + c * a + px * b, mz[1] + s * a + py * b)
                 for a, b in ((0, -9), (55 * k, 0), (0, 9))], "#fff1b8")
        stamp(img, GLOW, mz, 1.6, 0.9 * k)
    if 0 <= dt < 1.6:
        u = dt / 1.6
        for j in range(5):
            stamp(img, SMOKE_L, (mz[0] + d[0] * (10 + 18 * j) * (0.3 + u), mz[1] - 30 * dt + (j - 2) * 6),
                  0.8 + 1.6 * u, 0.7 * (1 - u) ** 1.5)


def render_scene(t, bg):
    img = bg.copy()
    cv = Canvas(img)
    acv = ActorCanvas(img)
    # tanks (back lane)
    for who in ("g", "b"):
        st = tank_state(who, t)
        stamp(img, SHADOW, (st["x"], TANK_GY + 2), 3.8, 0.9, 1.6)
        mz, d = draw_tank(cv, st["x"], st["f"], st["pal"], st["dist"], st["elev"], st["recoil"], st["rock"], t,
                          st["dmg"])
        tank_blast(img, cv, t, G_TANK_FIRE if who == "g" else B_TANK_FIRE, mz, d)
    draw_fire(img, t)
    # floor marks: scorch, blood pools, landed particles
    if t >= B_SHELL_HIT:
        ellipse(cv, (232, FLOOR + 4), 70, 11, "#4a4b4d")
    poses = {who: actor_pose(who, t) for who in ("g2", "g1", "b1", "b2")}
    for who, p in poses.items():
        if "dur" in p and t >= HIT[who] + p["dur"] - 0.05:
            g = smooth(0, 2.5, t - HIT[who] - p["dur"])
            hip_f, sh_f = p["rest"]
            c = A(((hip_f[0] + sh_f[0]) / 2, FLOOR - 4))
            ellipse(cv, c, 8 + 58 * g, 2 + 9 * g, "#5a0a0d")
            ellipse(cv, (c[0] - 4, c[1] - 1), 4 + 40 * g, 1 + 5 * g, "#76121a")
    draw_particles(cv, t, True)
    # shadows
    for who, p in poses.items():
        up = 1 - p.get("fall_q", 0)
        stamp(img, SHADOW, A((p["hip"][0], FLOOR)), 1.0 + 0.6 * (1 - up), 0.9, 1.0)
    # actors, back to front
    order = (("g2", GREEN), ("g1", GREEN), ("b1", BLACK), ("b2", BLACK))
    for who, pal in order:
        p, f = poses[who], FACING[who]
        if who in HIT and t >= HIT[who]:
            pos, ang = dropped_rifle(BASE[who], t - HIT[who], f, -f if FALL_KIND[who] != "forward" else f)
            draw_rifle(acv, pos, ang, f, pal["rifle"])
        out = draw_figure(acv, p, pal, f)
        for s in SHOT_T.get(who, ()):
            dt = t - s
            if -1e-6 <= dt < 2.5 / FPS and "muzzle" in out:
                muzzle_flash(acv, out["muzzle"], p["rifle"][1], f, 1.0 if dt < 0.5 / FPS else 0.6)
                stamp(img, GLOW, A(out["muzzle"]), 0.7, 0.8 if dt < 0.5 / FPS else 0.4)
        if who == "g2":
            draw_cover_crates(cv)
        if who == "g1":
            draw_barrier(acv)
        if who == "b2":
            draw_sandbags(cv)
    draw_holes(cv, t)
    draw_particles(cv, t, False)
    draw_tracers(cv, t)
    draw_puffs(img, t)
    draw_explosions(img, cv, t)
    return img


def camera(t, i):
    z = 1.02 + 0.04 * smooth(0, DUR, t)
    flash = 0.0
    for e in EXPLOSIONS:
        if t >= e["t0"]:
            z += 0.02 * e["s"] * math.exp(-(t - e["t0"]) * 3)
            flash = max(flash, e["s"] * math.exp(-(t - e["t0"]) * 12))
    pan = lerp(-45, 0, smooth(0.2, 3.0, t)) + lerp(0, -20, smooth(5.6, 6.2, t)) + 35 * smooth(6.5, 7.6, t)
    amp = 0.0
    for t0, a, rate in SHAKES:
        if t >= t0:
            amp += a * math.exp(-(t - t0) * rate)
    amp = min(amp, 30)
    rng = random.Random(i * 7919)
    return z, pan + rng.uniform(-amp, amp), rng.uniform(-amp, amp) * 0.8, flash


def make_frame(i, bg, vig):
    t = i / FPS
    fast = (G1_T0 < t < G1_RUN_END + 0.6 or any(0 <= t - HIT[w] < 0.8 for w in HIT)
            or B1_T0 < t < B1_STOP)
    img = None
    for k, off in enumerate((-1 / 3, 0.0, 1 / 3) if fast else (0.0,)):
        sc = render_scene(t + off / FPS, bg)
        img = sc if img is None else Image.blend(img, sc, 1 / (k + 1))
    z, dx, dy, flash = camera(t, i)
    cx, cy = BW / 2, 430
    coeffs = (1 / z, 0, SS * (cx + M + dx) - SS * cx / z, 0, 1 / z, SS * (cy + M + dy) - SS * cy / z)
    band = img.transform((BW * SS, BH * SS), Image.AFFINE, coeffs, Image.BICUBIC).reduce(SS).convert("RGB")
    arr = np.asarray(band, dtype=np.float32) * vig
    if flash > 0.01:
        arr = arr + np.array([38, 30, 16], dtype=np.float32) * flash
    frame = Image.new("RGB", (W, H), "black")
    frame.paste(Image.fromarray(arr.clip(0, 255).astype(np.uint8)), (0, BY))
    return frame


def setup():
    bg = Image.new("RGBA", ((BW + 2 * M) * SS, (BH + 2 * M) * SS), "#8b8d90")
    R.draw_background(bg)
    # skylights with light shafts
    cv = Canvas(bg)
    for x in (300, 640):
        cv.rect(x, -10, x + 120, 40, "#c9d3da")
        cv.rect(x + 58, -10, x + 62, 40, "#8b9196")
    shafts = Image.new("RGBA", bg.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(shafts)
    for x in (300, 640):
        pts = [(x, 40), (x + 120, 40), (x + 290, FLOOR), (x + 120, FLOOR)]
        sd.polygon([Canvas.p(q) for q in pts], fill=(255, 250, 235, 26))
    bg.alpha_composite(shafts)
    init_motion()
    for who in ("g", "b"):
        ft = G_TANK_FIRE if who == "g" else B_TANK_FIRE
        st = tank_state(who, ft)
        tmp = Image.new("RGBA", (8, 8))
        TANK_MUZZLE[who] = draw_tank(Canvas(tmp), st["x"], st["f"], st["pal"], st["dist"], st["elev"], 0,
                                     st["rock"], ft)[0]
    build_events()
    return bg, R.vignette()


def main():
    out = sys.argv[1]
    bg, vig = setup()
    if "--frame" in sys.argv:
        make_frame(int(sys.argv[sys.argv.index("--frame") + 1]), bg, vig).save(out)
        return
    if "--preview" in sys.argv:
        j = sys.argv.index("--preview")
        times = [float(v) for v in sys.argv[j + 1].split(",")] if len(sys.argv) > j + 1 else \
            (1.0, 1.9, 3.0, 3.9, 4.3, 5.0, 5.97, 6.4, 6.97, 7.5, 8.5, 9.9)
        rows = (len(times) + 1) // 2
        sheet = Image.new("RGB", (1080, 360 * rows), "black")
        for k, tt in enumerate(times):
            th = make_frame(int(round(tt * FPS)), bg, vig).crop((0, BY, W, BY + BH)).resize((540, 360))
            sheet.paste(th, ((k % 2) * 540, (k // 2) * 360))
        sheet.save(out)
        return
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                          "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264",
                          "-preset", "slow", "-crf", "14", "-pix_fmt", "yuv420p",
                          "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    for i in range(int(FPS * DUR)):
        p.stdin.write(make_frame(i, bg, vig).tobytes())
    p.stdin.close()
    sys.exit(p.wait())


if __name__ == "__main__":
    main()
