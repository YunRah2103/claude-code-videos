"""Warehouse standoff: 10 s vertical stickman animation (1080x1920, 30 fps).

Usage:
  python videos/warehouse-standoff/src/render.py OUT.mp4
  python videos/warehouse-standoff/src/render.py SHEET.png --preview      # contact sheet
  python videos/warehouse-standoff/src/render.py FRAME.png --frame N      # one full frame
"""
import math
import random
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1080, 1920
BW, BH = 1080, 720                 # scene band, letterboxed like the reference
BY = (H - BH) // 2
M = 48                             # canvas margin (camera shake / push-in)
SS = 2                             # supersampling
FPS, DUR = 30, 10.0
FLOOR = 650                        # ground line where feet stand
HORIZON = 432                      # wall/floor junction
SHOT_FRAMES = (246, 256, 267)
SHOTS = tuple(n / FPS for n in SHOT_FRAMES)

THIGH, SHIN, UARM, FARM, TORSO, HEAD_R = 92, 90, 80, 78, 128, 31
ANKLE = 15                         # ankle height above floor
RIFLE_SCALE = 0.78


# ---------------------------------------------------------------- math
def smooth(a, b, t):
    if t <= a:
        return 0.0
    if t >= b:
        return 1.0
    x = (t - a) / (b - a)
    return x * x * (3 - 2 * x)


def lerp(a, b, w):
    return a + (b - a) * w


def lerp2(p, q, w):
    return (lerp(p[0], q[0], w), lerp(p[1], q[1], w))


def unit(a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    d = math.hypot(dx, dy) or 1.0
    return dx / d, dy / d


def ik(a, b, l1, l2, pick):
    dx, dy = b[0] - a[0], b[1] - a[1]
    d = max(1e-3, min(math.hypot(dx, dy), l1 + l2 - 0.5))
    base = math.atan2(dy, dx)
    alpha = math.acos(max(-1, min(1, (l1 * l1 + d * d - l2 * l2) / (2 * l1 * d))))
    cands = [(a[0] + l1 * math.cos(base + s * alpha), a[1] + l1 * math.sin(base + s * alpha)) for s in (1, -1)]
    return max(cands, key=pick)


def frame_pts(o, d, fr, pts):
    """Points given as (s along d, k along fr) relative to origin o."""
    return [(o[0] + d[0] * s + fr[0] * k, o[1] + d[1] * s + fr[1] * k) for s, k in pts]


def rgb(c, k=1.0):
    if isinstance(c, str):
        c = tuple(int(c[i:i + 2], 16) for i in (1, 3, 5))
    return tuple(max(0, min(255, int(v * k))) for v in c[:3])


# ---------------------------------------------------------------- canvas
class Canvas:
    def __init__(self, img):
        self.img = img
        self.d = ImageDraw.Draw(img)

    @staticmethod
    def p(pt):
        return ((pt[0] + M) * SS, (pt[1] + M) * SS)

    def poly(self, pts, fill):
        self.d.polygon([self.p(q) for q in pts], fill=rgb(fill))

    def rect(self, x0, y0, x1, y1, fill, r=0):
        a, b = self.p((x0, y0)), self.p((x1, y1))
        if r:
            self.d.rounded_rectangle([a, b], radius=r * SS, fill=rgb(fill))
        else:
            self.d.rectangle([a, b], fill=rgb(fill))

    def circle(self, c, r, fill):
        x, y = self.p(c)
        r *= SS
        self.d.ellipse([x - r, y - r, x + r, y + r], fill=rgb(fill))

    def line(self, pts, fill, width):
        self.d.line([self.p(q) for q in pts], fill=rgb(fill), width=max(1, int(width * SS)))

    def capsule(self, a, b, w, fill):
        self.line([a, b], fill, w)
        self.circle(a, w / 2, fill)
        self.circle(b, w / 2, fill)

    def arc_poly(self, c, r, t0, t1, fill, n=28):
        pts = [(c[0] + r * math.cos(lerp(t0, t1, i / n)), c[1] + r * math.sin(lerp(t0, t1, i / n)))
               for i in range(n + 1)]
        self.poly(pts, fill)


# ---------------------------------------------------------------- sprites
def soft_sprite(w, h, color, alpha, blur):
    pad = blur * 3
    im = Image.new("RGBA", (w + 2 * pad, h + 2 * pad), color + (0,))
    a = Image.new("L", im.size, 0)
    ImageDraw.Draw(a).ellipse([pad, pad, pad + w, pad + h], fill=alpha)
    im.putalpha(a.filter(ImageFilter.GaussianBlur(blur)))
    return im


def stamp(img, sprite, center, sx=1.0, opacity=1.0, sy=None):
    sy = sx if sy is None else sy
    sp = sprite
    if sx != 1.0 or sy != 1.0:
        sp = sp.resize((max(1, int(sp.width * sx)), max(1, int(sp.height * sy))), Image.BILINEAR)
    if opacity < 1.0:
        r, g, b, a = sp.split()
        sp = Image.merge("RGBA", (r, g, b, a.point(lambda v: int(v * opacity))))
    x, y = Canvas.p(center)
    x, y = int(x - sp.width / 2), int(y - sp.height / 2)
    if x + sp.width <= 0 or y + sp.height <= 0 or x >= img.width or y >= img.height:
        return
    cx0, cy0 = max(0, -x), max(0, -y)
    cx1, cy1 = min(sp.width, img.width - x), min(sp.height, img.height - y)
    img.alpha_composite(sp.crop((cx0, cy0, cx1, cy1)), (x + cx0, y + cy0))


SHADOW = soft_sprite(190 * SS, 26 * SS, (20, 20, 22), 120, 7 * SS)
GLOW = soft_sprite(170 * SS, 170 * SS, (255, 190, 80), 130, 26 * SS)
SMOKE = soft_sprite(60 * SS, 60 * SS, (200, 202, 204), 150, 9 * SS)


# ---------------------------------------------------------------- background
def draw_background(img):
    cv = Canvas(img)
    ext = M + 4
    rng = random.Random(7)

    # wall with a soft light band near the floor
    for i in range(40):
        y0 = -ext + i * (HORIZON + ext) / 40
        y1 = y0 + (HORIZON + ext) / 40 + 1
        k = 0.97 + 0.08 * math.exp(-(((y0 + y1) / 2 - 330) / 70) ** 2)
        cv.rect(-ext, y0, BW + ext, y1, rgb("#8b8d90", k))
    for x in (-40, 250, 540, 830, 1120):
        cv.line([(x, -ext), (x, HORIZON)], "#818386", 3)
    for _ in range(170):
        x, y = rng.uniform(-ext, BW + ext), rng.uniform(-ext, HORIZON - 10)
        cv.line([(x, y), (x + rng.uniform(12, 42), y)], "#7d7f82", 2)

    # floor with gentle gradient and scuffs
    for i in range(30):
        y0 = HORIZON + i * (BH + ext - HORIZON) / 30
        y1 = y0 + (BH + ext - HORIZON) / 30 + 1
        cv.rect(-ext, y0, BW + ext, y1, rgb("#7e8083", 1.03 - 0.12 * i / 30))
    cv.rect(-ext, HORIZON - 10, BW + ext, HORIZON + 2, "#6c6e71")
    cv.rect(-ext, HORIZON + 2, BW + ext, HORIZON + 6, "#909295")
    for _ in range(150):
        x, y = rng.uniform(-ext, BW + ext), rng.uniform(HORIZON + 14, BH + ext)
        cv.line([(x, y), (x + rng.uniform(16, 60), y)], "#6f7174", 2)

    # mesh cabinet (left)
    cv.rect(-30, 36, 168, HORIZON, "#5d6552")
    cv.rect(-30, 36, 168, 48, "#6c7461")
    cv.rect(162, 36, 168, HORIZON, "#4c5343")
    mesh_window(cv, 4, 66, 140, 214)
    mesh_window(cv, 4, 240, 140, 410)
    cv.rect(146, 210, 156, 262, "#3a3f33", r=3)

    # IBC tank: blue tank in a grey cage on a pallet
    x0, x1, y0, y1 = 520, 800, 150, 398
    cv.rect(x0 + 6, y0 + 8, x1 - 6, y1 - 2, "#3d66a6", r=20)
    cv.rect(x0 + 14, y0 + 14, x0 + 56, y1 - 12, "#4a76b8", r=12)
    cv.rect(x0 + 6, y0 + 8, x1 - 6, y0 + 30, "#35598f", r=10)
    cv.rect(632, 318, 690, 396, "#2f5185", r=8)
    cv.circle((661, 362), 13, "#1d2635")
    cv.circle((661, 362), 6, "#3a4658")
    for i in range(5):
        x = lerp(x0, x1, i / 4)
        cv.rect(x - 5, y0, x + 5, y1, "#a2a6aa")
        cv.rect(x + 2, y0, x + 5, y1, "#83878b")
    for y in (y0, 232, 314, y1 - 6):
        cv.rect(x0 - 2, y - 4, x1 + 2, y + 5, "#a8acb0")
        cv.rect(x0 - 2, y + 3, x1 + 2, y + 5, "#84888c")
    cv.rect(x0 - 10, y1, x1 + 10, HORIZON, "#2a2b2d")
    cv.rect(x0 - 10, y1, x1 + 10, y1 + 7, "#3b3c3f")
    for x in (x0 + 10, 650, x1 - 50):
        cv.rect(x, y1 + 18, x + 46, y1 + 24, "#55575a")
    cv.rect(x0 - 16, HORIZON - 3, x1 + 16, HORIZON + 4, "#545659")

    # hard-case crates + radio
    crate(cv, 832, 332, 1032, HORIZON)
    crate(cv, 840, 236, 1024, 332)
    crate(cv, 1046, 372, 1180, HORIZON, latches=2)
    cv.line([(932, -ext), (932, 150)], "#c4c6c9", 2)
    cv.rect(856, 148, 1006, 236, "#babcbf", r=6)
    cv.rect(864, 156, 998, 172, "#8f9295", r=3)
    cv.rect(870, 160, 960, 168, "#2c2e31")
    cv.rect(940, 159, 950, 169, "#cfd2d4")
    cv.circle((975, 164), 7, "#55585b")
    for cy in (192, 218):
        cv.circle((976, cy), 12, "#3a3c3f")
        cv.circle((976, cy), 6, "#5b5e61")
    for k in range(5):
        cv.line([(870, 186 + k * 9), (950, 186 + k * 9)], "#9a9da0", 3)


def mesh_window(cv, x0, y0, x1, y1):
    a, b = cv.p((x0, y0)), cv.p((x1, y1))
    w, h = int(b[0] - a[0]), int(b[1] - a[1])
    mesh = Image.new("RGBA", (w, h), rgb("#4e5545") + (255,))
    md = ImageDraw.Draw(mesh)
    for x in range(-h, w + h, 24 * SS):
        md.line([(x, 0), (x + h, h)], fill=rgb("#262a22"), width=3 * SS)
        md.line([(x + h, 0), (x, h)], fill=rgb("#262a22"), width=3 * SS)
    cv.img.paste(mesh, (int(a[0]), int(a[1])))
    cv.rect(x0 - 6, y0 - 6, x1 + 6, y0, "#474e3f")
    cv.rect(x0 - 6, y1, x1 + 6, y1 + 6, "#474e3f")


def crate(cv, x0, y0, x1, y1, latches=3):
    mid = (y0 + y1) / 2
    cv.rect(x0, y0, x1, y1, "#5f6e46", r=8)
    cv.rect(x0, y0, x1, y0 + 12, "#6d7d52", r=6)
    cv.rect(x0, y1 - 12, x1, y1, "#52603c", r=4)
    cv.rect(x0, mid - 3, x1, mid + 3, "#4c5937")
    for x in np.linspace(x0 + 30, x1 - 30, 3 if x1 - x0 > 160 else 2):
        cv.rect(x - 9, y0 + 18, x + 9, mid - 8, "#56653f", r=5)
        cv.rect(x - 9, mid + 8, x + 9, y1 - 16, "#56653f", r=5)
    for x in np.linspace(x0 + 34, x1 - 34, latches):
        cv.poly([(x - 11, mid - 2), (x + 11, mid - 2), (x + 8, mid + 16), (x - 8, mid + 16)], "#2d3424")
    cv.rect(x0 - 6, y0 + 22, x0 + 2, y0 + 40, "#2d3424", r=2)
    cv.rect(x1 - 2, y0 + 22, x1 + 6, y0 + 40, "#2d3424", r=2)
    if x1 - x0 > 160:
        for k, x in enumerate((x0 + x1) / 2 + np.array([-8, 0, 6])):
            cv.rect(x, y0 + 16, x + (2 if k != 1 else 6), y0 + 26, "#c9cdc0")


BARRIER = [(326, 668), (484, 668), (484, 646), (448, 592), (442, 466), (372, 466),
           (366, 592), (326, 646)]


def draw_barrier(img):
    cv = Canvas(img)
    cv.poly(BARRIER, "#e2e3e4")
    cv.poly([(448, 592), (484, 646), (484, 668), (458, 668), (442, 466)], "#c9cbcd")
    cv.poly([(366, 592), (326, 646), (326, 668), (338, 668), (374, 594)], "#d3d5d7")
    cv.rect(372, 466, 442, 472, "#f0f1f2")
    cv.line([(404, 466), (404, 454)], "#2a2b2d", 3)
    cv.circle((396, 520), 6, "#3a3b3d")
    cv.rect(326, 662, 484, 668, "#b5b7ba")


# ---------------------------------------------------------------- rifle
RIFLE_PARTS = [  # (color key, polygon) local units: x along barrel, y down, origin = rear hand
    ("mid", [(-114, -30), (-80, -33), (-80, -14), (-62, -14), (-62, -6), (-80, -6), (-114, 2), (-118, -14)]),
    ("dark", [(-122, -31), (-114, -31), (-114, 3), (-122, 3)]),
    ("dark", [(-80, -30), (-38, -30), (-38, -20), (-80, -20)]),
    ("mid", [(-42, -24), (38, -24), (38, -8), (18, -8), (12, -2), (-42, -6)]),
    ("light", [(-42, -38), (40, -38), (40, -24), (-42, -24)]),
    ("dark", [(-40, -43), (150, -43), (150, -37), (-40, -37)]),
    ("mid", [(40, -38), (150, -38), (150, -13), (40, -13)]),
    ("dark", [(150, -30), (192, -30), (192, -23), (150, -23)]),
    ("dark", [(190, -34), (216, -34), (216, -20), (190, -20)]),
    ("dark", [(138, -52), (146, -52), (146, -42), (138, -42)]),
    ("dark", [(4, -47), (12, -47), (12, -41), (4, -41)]),
    ("dark", [(30, -47), (38, -47), (38, -41), (30, -41)]),
    ("dark", [(-14, -66), (54, -66), (54, -47), (-14, -47)]),
    ("dark", [(44, -70), (58, -70), (58, -44), (44, -44)]),
    ("lens", [(54, -66), (58, -66), (58, -48), (54, -48)]),
    ("mag", [(12, -8), (34, -8), (44, 30), (24, 36)]),
    ("dark", [(22, 33), (45, 27), (47, 33), (24, 40)]),
    ("dark", [(-12, -8), (8, -8), (2, 20), (-16, 18)]),
    ("dark", [(104, -14), (118, -14), (118, 16), (104, 16)]),
    ("port", [(0, -36), (20, -36), (20, -29), (0, -29)]),
]
RIFLE_SLOTS = [(x, -31, x + 14, -24) for x in (52, 76, 100, 124)]
HAND_FRONT = (111, 4)
MUZZLE = (218, -27)
PORT = (10, -32)


def rifle_tf(grip, ang, f):
    c, s = math.cos(ang), math.sin(ang)
    k = RIFLE_SCALE

    def T(x, y):
        x, y = x * k, y * k
        return (grip[0] + f * (x * c - y * s), grip[1] + x * s + y * c)
    return T


def draw_rifle(cv, grip, ang, f, pal):
    T = rifle_tf(grip, ang, f)
    for key, pts in RIFLE_PARTS:
        cv.poly([T(*q) for q in pts], pal[key])
    for x0, y0, x1, y1 in RIFLE_SLOTS:
        cv.poly([T(x0, y0), T(x1, y0), T(x1, y1), T(x0, y1)], pal["dark"])
    for x in range(-36, 150, 9):
        cv.line([T(x, -43), T(x, -40)], pal["light"], 1.5)


RIFLE_GREEN = dict(dark="#26282b", mid="#3b3e42", light="#5a5e63", lens="#7fa8bf", mag="#8b7b56", port="#83888d")
RIFLE_BLACK = dict(dark="#18191b", mid="#2a2c2f", light="#45484c", lens="#6c8796", mag="#2a2c2f", port="#6a6e72")


# ---------------------------------------------------------------- characters
GREEN = dict(body="#7d994b", gear="#5d7139", gear_d="#4a5a2d", boots="#57502f",
             gloves="#4b5a2d", head="#5b6248", helmet="#6c8141", helmet_d="#55672f", goggle="#1f2326",
             lens="#6d8794", rifle=RIFLE_GREEN, helmet_on=True)
BLACK = dict(body="#25262a", gear="#383a3e", gear_d="#1b1c1e", boots="#111213",
             gloves="#1a1b1c", head="#1f2023", helmet="#2c2d30", helmet_d="#38393d", goggle="#0d0e0f",
             lens="#5d6f7e", rifle=RIFLE_BLACK, helmet_on=False)


def draw_leg(cv, hip, ankle, mode, f, pal, back, toe=None):
    k = 0.8 if back else 1.0
    body, gear_d, boots = rgb(pal["body"], k), rgb(pal["gear_d"], k), rgb(pal["boots"], k)
    if mode == "down":
        knee = ik(hip, ankle, THIGH, SHIN, lambda q: q[1])
    else:
        knee = ik(hip, ankle, THIGH, SHIN, lambda q: f * q[0])
    cv.capsule(hip, knee, 36, body)
    cv.capsule(knee, ankle, 32, body)
    d = unit(hip, knee)
    cv.poly(frame_pts(hip, d, (-d[1], d[0]), [(28, -13), (66, -13), (66, 13), (28, 13)]), gear_d)
    toe = toe or (f * 30, 4)
    tip = (ankle[0] + toe[0], ankle[1] + toe[1])
    cv.capsule(ankle, tip, 30, boots)
    cv.capsule((ankle[0], ankle[1] + 9), (tip[0], tip[1] + 9), 12, rgb(boots, 0.7))
    cv.circle(knee, 19, gear_d)
    cv.circle((knee[0] + f * 3, knee[1] - 4), 8, rgb(gear_d, 1.25))


def draw_arm(cv, sh, hand, f, pal, back):
    k = 0.8 if back else 1.0
    elbow = ik(sh, hand, UARM, FARM, lambda q: q[1] - 0.6 * f * q[0])
    cv.capsule(sh, elbow, 30, rgb(pal["body"], k))
    cv.capsule(elbow, hand, 27, rgb(pal["body"], k))
    cv.circle(hand, 16, rgb(pal["gloves"], k))


def draw_figure(cv, pose, pal, f):
    hip, lean = pose["hip"], pose["lean"]
    d = (f * math.sin(lean), -math.cos(lean))
    fr = (f * math.cos(lean), math.sin(lean))
    neck = (hip[0] + d[0] * TORSO, hip[1] + d[1] * TORSO)
    sh = (hip[0] + d[0] * TORSO * 0.86, hip[1] + d[1] * TORSO * 0.86)
    hl = lean + pose.get("head_tilt", 0.0)
    hd = (f * math.sin(hl), -math.cos(hl))
    hf = (f * math.cos(hl), math.sin(hl))
    head = (neck[0] + hd[0] * (HEAD_R + 10), neck[1] + hd[1] * (HEAD_R + 10))
    modes = pose.get("knee_modes", ("fwd", "fwd"))
    toes = pose.get("toes", (None, None))
    feet, hands = pose["feet"], pose["hands"]

    draw_arm(cv, sh, hands[1], f, pal, True)
    draw_leg(cv, hip, feet[1], modes[1], f, pal, True, toes[1])
    draw_leg(cv, hip, feet[0], modes[0], f, pal, False, toes[0])

    # torso + plate carrier
    L = TORSO

    def P(pts):
        return frame_pts(hip, d, fr, [(s * L, k) for s, k in pts])
    cv.poly(P([(0.42, -27), (0.42, -44), (0.9, -44), (0.95, -27)]), pal["gear_d"])
    cv.capsule(hip, neck, 50, pal["body"])
    cv.poly(P([(0.30, -27), (0.30, 28), (0.86, 30), (0.96, 22), (0.96, -20), (0.86, -28)]), pal["gear"])
    for s in (0.46, 0.56, 0.66):
        cv.line(P([(s, -18), (s, 22)]), pal["gear_d"], 3)
    cv.poly(P([(0.70, -6), (0.70, 12), (0.80, 12), (0.80, -6)]), rgb(pal["gear"], 1.2))
    cv.poly(P([(0.34, 27), (0.34, 41), (0.54, 41), (0.54, 27)]), pal["gear_d"])
    cv.poly(P([(0.57, 28), (0.57, 39), (0.72, 39), (0.72, 28)]), pal["gear_d"])
    cv.poly(P([(0.04, -27), (0.04, 27), (0.17, 27), (0.17, -27)]), pal["gear_d"])
    cv.poly(P([(0.06, 6), (0.06, 16), (0.15, 16), (0.15, 6)]), "#8a8d90")
    cv.poly(P([(-0.04, -24), (-0.04, -36), (0.16, -36), (0.16, -24)]), pal["gear_d"])

    # head, goggles, helmet / beanie
    cv.capsule(neck, head, 22, pal["head"])
    cv.circle(head, HEAD_R, pal["head"])
    cv.poly(frame_pts(head, hd, hf, [(-7, 9), (-7, HEAD_R + 2), (10, HEAD_R + 2), (10, 6)]), pal["goggle"])
    cv.poly(frame_pts(head, hd, hf, [(0, 19), (0, HEAD_R - 2), (6, HEAD_R - 2), (6, 19)]), pal["lens"])
    tu = math.atan2(hd[1], hd[0])
    hc = (head[0] + hd[0] * 4, head[1] + hd[1] * 4)

    def on_arc(a, r):
        return (hc[0] + r * math.cos(a), hc[1] + r * math.sin(a))
    if pal["helmet_on"]:
        a0, a1 = sorted((tu + f * 1.3, tu - f * 1.9))
        cv.arc_poly(hc, HEAD_R + 6, a0, a1, pal["helmet"])
        for da, rr in ((0.2, 14), (-0.6, 20), (0.7, 22)):
            cv.circle(on_arc(tu + f * da, rr), 5, rgb(pal["helmet"], 0.9))
        cv.line([on_arc(a, HEAD_R + 1) for a in np.linspace(a0 + 0.12, a1 - 0.12, 16)], pal["helmet_d"], 4)
        cv.circle(on_arc(tu + f * 0.85, HEAD_R + 6), 8, "#2b2e29")
        ear = (head[0] - hf[0] * 5 - hd[0] * 3, head[1] - hf[1] * 5 - hd[1] * 3)
        cv.circle(ear, 14, "#2c302a")
        cv.circle(ear, 7, "#40453c")
    else:
        a0, a1 = sorted((tu + f * 1.15, tu - f * 1.45))
        cv.arc_poly(hc, HEAD_R + 3, a0, a1, pal["helmet"])
        cv.line([on_arc(a, HEAD_R - 2) for a in np.linspace(a0 + 0.1, a1 - 0.1, 16)], pal["helmet_d"], 5)

    out = {}
    grip, ang = pose["rifle"]
    draw_rifle(cv, grip, ang, f, pal["rifle"])
    T = rifle_tf(grip, ang, f)
    out["muzzle"], out["port"] = T(*MUZZLE), T(*PORT)
    draw_arm(cv, sh, hands[0], f, pal, False)
    return out


# ---------------------------------------------------------------- locomotion
def gait(dist, A, stance, lift, phase0):
    """Planted-foot gait: (forward offset of the ankle from the hip, lift)."""
    u = (dist / (2 * A / stance) + phase0) % 1.0
    if u < stance:
        return A - 2 * A * (u / stance), 0.0
    v = (u - stance) / (1 - stance)
    e = v * v * (3 - 2 * v)
    return -A + 2 * A * e, lift * math.sin(math.pi * v)


GAITS = {  # A, stance, lift, hip height, lean, bob
    "run": (68, 0.4, 66, 168, 0.27, 10),
    "walk": (56, 0.6, 28, 185, 0.04, 4),
}


def locomotion(hx, dist, f, kind):
    A, st, lift, hip_h, lean, bob = GAITS[kind]
    u = dist / (2 * A / st)
    feet = []
    for ph in (0.0, 0.5):
        dx, ly = gait(dist, A, st, lift, ph)
        feet.append((hx + f * dx, FLOOR - ANKLE - ly))
    # hip is lowest just after each foot plants (weight acceptance)
    step = (2 * u) % 1.0
    dip = 0.5 * (1 + math.cos(2 * math.pi * (step - 0.12)))
    hy = FLOOR - hip_h - bob * (1 - dip)
    return dict(hip=(hx, hy), lean=lean, feet=feet, u=u, step=step,
                bob=math.cos(2 * math.pi * step), sway=math.sin(2 * math.pi * u))


def footfalls(xfn, f, kind, t0, t1, dist0):
    """Times/positions where each foot plants (for dust puffs)."""
    A, st = GAITS[kind][:2]
    cycle = 2 * A / st
    ev, prev = [], None
    for t in np.arange(t0, t1, 1 / 240):
        x = xfn(t)
        u = abs(x - dist0) / cycle
        cur = (int(u), int(u + 0.5))
        if prev is not None:
            for i in range(2):
                if cur[i] != prev[i]:
                    ev.append((t, x + f * A))
        prev = cur
    return ev


def held_rifle(sh, f, offx, offy, ang):
    grip = (sh[0] + f * offx, sh[1] + offy)
    return grip, ang, rifle_tf(grip, ang, f)(*HAND_FRONT)


def kick(t, rate, window):
    k = 0.0
    for s in SHOTS:
        if -1e-6 <= t - s < window:
            k = max(k, math.exp(-(t - s) * rate))
    return k


class Spring:
    """Damped spring following a target signal; precomputed so any t can be sampled."""
    def __init__(self, target, omega, zeta, t0=-0.5, t1=DUR + 0.5, dt=1 / 600):
        ts = np.arange(t0, t1, dt)
        x = np.array(target(t0), dtype=float)
        v = np.zeros_like(x)
        out = np.empty((len(ts), len(x)))
        for i, t in enumerate(ts):
            g = np.array(target(t), dtype=float)
            v += (omega * omega * (g - x) - 2 * zeta * omega * v) * dt
            x += v * dt
            out[i] = x
        self.ts, self.out = ts, out

    def __call__(self, t):
        return [float(np.interp(t, self.ts, self.out[:, j])) for j in range(self.out.shape[1])]


# ---------------------------------------------------------------- green soldier
G_START, G_X0, G_XK, RUN_V, DECEL = 0.7, -270.0, 245.0, 420.0, 0.6
G_RUN_END = G_START + ((G_XK - RUN_V * DECEL / 2) - G_X0) / RUN_V
AIM_T0, AIM_T1 = G_RUN_END + 0.95, G_RUN_END + 1.5


def green_x(t):
    if t <= G_START:
        return G_X0
    if t <= G_RUN_END:
        return G_X0 + RUN_V * (t - G_START)
    s = min(t - G_RUN_END, DECEL)
    return G_X0 + RUN_V * (G_RUN_END - G_START) + RUN_V * (s - s * s / (2 * DECEL))


def kneel_w(t):
    """Knee slide into cover: starts while still moving, so the body skids down."""
    return smooth(G_RUN_END - 0.08, G_RUN_END + 0.42, t)


def green_targets(t):
    x = green_x(t)
    loc = locomotion(x, x - G_X0, 1, "run")
    w = kneel_w(t)
    a = smooth(AIM_T0, AIM_T1, t)
    dip = math.sin(math.pi * smooth(AIM_T0 - 0.25, AIM_T0 + 0.2, t)) * (1 - a)   # anticipation
    breathe = math.sin(t * 2.3)
    # aim tracks the black stickman's chest
    if t > 4.6:
        bx, by = black_x(t - 0.2), FLOOR - 189 - TORSO * 0.75
    else:
        bx, by = 900, FLOOR - 300
    sh_y = FLOOR - 104 - TORSO * 0.86
    aim_ang = max(-0.25, min(0.12, math.atan2(by - sh_y, bx - (G_XK + 70))))
    run_r = (22, 60 + 8 * loc["bob"], -0.62 + 0.07 * loc["bob"])
    ready_r = (30, 64, 0.42)
    aim_r = (62, 20 + 1.2 * breathe, aim_ang + 0.012 * math.sin(t * 1.7))
    r = [lerp(lerp(run_r[i], ready_r[i], w), aim_r[i], a) for i in range(3)]
    r[1] += 10 * dip
    r[2] += 0.18 * dip
    lean = lerp(loc["lean"] + 0.04 * loc["bob"], lerp(0.2, 0.1, a), w) + 0.1 * dip
    head = lerp(-0.18 - 0.03 * loc["bob"], lerp(0.0, 0.1, a), w)
    return dict(loc=loc, w=w, hipy=lerp(loc["hip"][1], FLOOR - 104 + 2 * breathe, w),
                lean=lean, head=head, r=r, x=x)


def green_pose(t):
    g = green_targets(t)
    loc, w, x = g["loc"], g["w"], g["x"]
    lean, = G_LEAN(t)
    head, = G_HEAD(t)
    hipy, = G_HIPY(t)
    r = G_RIFLE(t)
    k = kick(t, 26, 0.2)
    lean -= 0.05 * k
    head -= 0.1 * k
    r = [r[0] - 13 * k, r[1] + 2 * k, r[2] - 0.11 * k]

    hip = (x, hipy)
    kneel_feet = [(x + 88, FLOOR - ANKLE), (x - 80, FLOOR - 26)]
    feet = [lerp2(loc["feet"][i], kneel_feet[i], smooth(0.0, 0.7, w)) for i in range(2)]
    sh = (hip[0] + math.sin(lean) * TORSO * 0.86, hip[1] - math.cos(lean) * TORSO * 0.86)
    grip, ang, front = held_rifle(sh, 1, *r)
    return dict(hip=hip, lean=lean, feet=feet, hands=[front, grip], rifle=(grip, ang),
                toes=(None, (lerp(30, -14, w), lerp(4, 12, w))), head_tilt=head)


G_LEAN = G_HEAD = G_HIPY = G_RIFLE = None


# ---------------------------------------------------------------- black stickman
B_START, B_STOP, B_X0, B_X1 = 4.3, 7.25, 1270.0, 830.0


def black_x(t):
    tt = max(0.0, min(t, B_STOP)) - B_START
    T, D = B_STOP - B_START, 0.9
    v = (B_X0 - B_X1) / (T - D / 2)
    if tt <= 0:
        return B_X0
    if tt <= T - D:
        return B_X0 - v * tt
    s = tt - (T - D)
    return B_X0 - v * (T - D) - v * (s - s * s / (2 * D))


def black_targets(t):
    x = black_x(t)
    loc = locomotion(x, B_X0 - x, -1, "walk")
    w = smooth(B_STOP - 0.3, B_STOP + 0.2, t)
    k = kick(t, 7, 0.6)
    look = smooth(B_STOP - 0.2, B_STOP + 0.6, t)
    lean = lerp(loc["lean"] + 0.02 * loc["bob"], 0.0, w) - 0.2 * k + 0.05 * look
    head = lerp(-0.04 * loc["bob"], 0.12 * look, w) - 0.25 * k
    ang = 0.62 + 0.06 * loc["sway"] * (1 - w) - 0.25 * k
    return dict(loc=loc, w=w, x=x, lean=lean, head=head, ang=ang,
                hipy=lerp(loc["hip"][1], FLOOR - 191 + 1.6 * math.sin(t * 2.0), w) + 10 * k)


def black_pose(t):
    b = black_targets(t)
    loc, w, x = b["loc"], b["w"], b["x"]
    lean, head, ang = B_SPR(t)
    hipy, = B_HIPY(t)
    k = kick(t, 14, 0.4)
    hip = (x + 10 * k, hipy)
    stop_feet = B_STOP_FEET
    feet = [lerp2(loc["feet"][i], stop_feet[i], w) for i in range(2)]
    sh = (hip[0] - math.sin(lean) * TORSO * 0.86, hip[1] - math.cos(lean) * TORSO * 0.86)
    grip, ang, front = held_rifle(sh, -1, 24, 70 + 4 * loc["bob"] * (1 - w), ang)
    return dict(hip=hip, lean=lean, feet=feet, hands=[front, grip], rifle=(grip, ang), head_tilt=head)


B_SPR = B_HIPY = None
B_STOP_FEET = None


def init_motion():
    global G_LEAN, G_HEAD, G_HIPY, G_RIFLE, B_SPR, B_HIPY, B_STOP_FEET, FOOTFALLS
    G_LEAN = Spring(lambda t: [green_targets(t)["lean"]], 13, 0.42)
    G_HEAD = Spring(lambda t: [green_targets(t)["head"]], 9, 0.45)
    G_HIPY = Spring(lambda t: [green_targets(t)["hipy"]], 22, 0.5)
    G_RIFLE = Spring(lambda t: green_targets(t)["r"], 15, 0.5)
    B_SPR = Spring(lambda t: [black_targets(t)[k] for k in ("lean", "head", "ang")], 11, 0.32)
    B_HIPY = Spring(lambda t: [black_targets(t)["hipy"]], 20, 0.45)
    loc = locomotion(B_X1, B_X0 - B_X1, -1, "walk")
    B_STOP_FEET = [(B_X1 + 0.6 * (fx - B_X1), FLOOR - ANKLE) for fx, _ in loc["feet"]]
    FOOTFALLS = footfalls(green_x, 1, "run", G_START, G_RUN_END + 0.1, G_X0)


FOOTFALLS = []


# ---------------------------------------------------------------- effects
def muzzle_flash(cv, muzzle, ang, f, k):
    c, s = math.cos(ang), math.sin(ang)

    def P(x, y):
        return (muzzle[0] + f * (x * c - y * s), muzzle[1] + x * s + y * c)
    cv.poly([P(0, -9), P(70 * k, 0), P(0, 9)], "#ffa62b")
    cv.poly([P(4, -3), P(26 * k, -30 * k), P(18, 0), P(26 * k, 30 * k), P(4, 3)], "#ffa62b")
    cv.poly([P(0, -6), P(44 * k, 0), P(0, 6)], "#ffd75a")
    cv.circle(P(10, 0), 12 * k, "#ffe68a")
    cv.circle(P(8, 0), 7 * k, "#fffbe8")


CASING_SPAWN = []      # ejection-port positions at each shot (filled in setup)


def draw_casings(cv, t):
    for i, s in enumerate(SHOTS):
        dt = t - s
        if dt < 0:
            continue
        px, py = CASING_SPAWN[i]
        vx, vy, g = -(150 + 25 * i), -330, 1500
        y_floor = FLOOR - 2 + 6 * i
        t_hit = (-vy + math.sqrt(vy * vy + 2 * g * (y_floor - py))) / g
        if dt < t_hit:
            x, y, rot = px + vx * dt, py + vy * dt + 0.5 * g * dt * dt, dt * 22
        else:
            b = dt - t_hit
            hop = max(0.0, 90 * b - 0.5 * g * b * b)
            sl = min(b, 0.35)
            x = px + vx * t_hit + vx * 0.35 * (sl - sl * sl / 0.7)
            y, rot = y_floor - hop, t_hit * 22 + min(b, 0.25) * 10
        c, sn = math.cos(rot), math.sin(rot)
        cv.poly([(x + dx * c - dy * sn, y + dx * sn + dy * c)
                 for dx, dy in ((-6, -2.5), (6, -2.5), (6, 2.5), (-6, 2.5))], "#c9a046")
        cv.circle((x + 5 * c, y + 5 * sn), 2.2, "#8a6a26")


def draw_fx_overlays(img, t, muzzle):
    for s in SHOTS:
        dt = t - s
        if -1e-6 <= dt < 2.5 / FPS:
            stamp(img, GLOW, muzzle, 1.0, 0.9 if dt < 0.5 / FPS else 0.45)
        if 0 < dt < 1.2:
            life = dt / 1.2
            for j in range(4):
                px = muzzle[0] + 18 + j * 16 + dt * (40 + 12 * j)
                py = muzzle[1] - dt * (34 + 10 * j) + (j - 1.5) * 4
                stamp(img, SMOKE, (px, py), 0.45 + 1.1 * life + 0.1 * j, 0.55 * (1 - life) ** 1.6)


DUST = soft_sprite(56 * SS, 40 * SS, (196, 192, 182), 190, 8 * SS)
SLIDE_DUST = []


def draw_dust(img, t):
    for te, x in FOOTFALLS:
        dt = t - te
        if 0 <= dt < 0.55:
            life = dt / 0.55
            stamp(img, DUST, (x - 30 * dt, FLOOR - 6 - 26 * dt), 0.3 + 0.7 * life, 0.45 * (1 - life) ** 1.5)
    for te, x, big in SLIDE_DUST:
        dt = t - te
        if 0 <= dt < 0.9:
            life = dt / 0.9
            stamp(img, DUST, (x - 40 * dt, FLOOR - 8 - 40 * dt), (0.4 + 1.2 * life) * big,
                  0.5 * (1 - life) ** 1.4)


# ---------------------------------------------------------------- frame assembly
def render_scene(t, bg):
    img = bg.copy()
    cv = Canvas(img)
    gp, bp = green_pose(t), black_pose(t)
    stamp(img, SHADOW, (gp["hip"][0] + 10, FLOOR + 2), 0.85 + 0.35 * kneel_w(t), 1.0, 1.0)
    stamp(img, SHADOW, (bp["hip"][0], FLOOR + 2), 0.8, 1.0, 1.0)
    g = draw_figure(cv, gp, GREEN, 1)
    draw_barrier(img)
    for s in SHOTS:
        dt = t - s
        if -1e-6 <= dt < 2.5 / FPS:
            muzzle_flash(cv, g["muzzle"], gp["rifle"][1], 1, 1.0 if dt < 0.5 / FPS else 0.6)
    draw_dust(img, t)
    draw_figure(cv, bp, BLACK, -1)
    draw_casings(cv, t)
    draw_fx_overlays(img, t, g["muzzle"])
    return img


def camera(t, i):
    z = 1.03 + 0.05 * smooth(0.0, DUR, t) + 0.012 * kick(t, 6, 0.6)
    pan = lerp(-55, -25, smooth(0.6, 2.6, t)) + 65 * smooth(4.0, 7.8, t)
    amp = 9 * kick(t, 13, 0.3)
    rng = random.Random(i * 7919)
    return z, pan + rng.uniform(-amp, amp), rng.uniform(-amp, amp)


def vignette():
    yy, xx = np.mgrid[0:BH, 0:BW]
    r = np.sqrt(((xx - BW / 2) / (BW / 2)) ** 2 + ((yy - BH / 2) / (BH / 2)) ** 2)
    return (1.0 - 0.16 * np.clip(r - 0.55, 0, 1) ** 1.5)[..., None].astype(np.float32)


def make_frame(i, bg, font, vig):
    t = i / FPS
    moving = G_START - 0.1 < t < G_RUN_END + 0.6 or B_START < t < B_STOP
    img = None
    for k, off in enumerate((-1 / 3, 0.0, 1 / 3) if moving else (0.0,)):   # motion blur
        sc = render_scene(t + off / FPS, bg)
        img = sc if img is None else Image.blend(img, sc, 1 / (k + 1))
    z, dx, dy = camera(t, i)
    cx, cy = BW / 2, 430
    coeffs = (1 / z, 0, SS * (cx + M + dx) - SS * cx / z,
              0, 1 / z, SS * (cy + M + dy) - SS * cy / z)
    band = img.transform((BW * SS, BH * SS), Image.AFFINE, coeffs, Image.BICUBIC).reduce(SS).convert("RGB")
    arr = (np.asarray(band, dtype=np.float32) * vig).clip(0, 255).astype(np.uint8)
    frame = Image.new("RGB", (W, H), "black")
    frame.paste(Image.fromarray(arr), (0, BY))
    d = ImageDraw.Draw(frame)
    pos = (W // 2, BY + BH - 64)
    d.text((pos[0] + 2, pos[1] + 3), "Noahh", font=font, fill=(40, 40, 40), anchor="mm")
    d.text(pos, "Noahh", font=font, fill="white", anchor="mm")
    return frame


def setup():
    bg = Image.new("RGBA", ((BW + 2 * M) * SS, (BH + 2 * M) * SS), "#8b8d90")
    draw_background(bg)
    stamp(bg, soft_sprite(200 * SS, 22 * SS, (20, 20, 22), 110, 6 * SS), (405, 668))
    stamp(bg, soft_sprite(320 * SS, 18 * SS, (20, 20, 22), 90, 5 * SS), (660, HORIZON + 4))
    stamp(bg, soft_sprite(230 * SS, 18 * SS, (20, 20, 22), 90, 5 * SS), (932, HORIZON + 4))
    init_motion()
    for te in np.arange(G_RUN_END - 0.05, G_RUN_END + 0.45, 0.05):
        SLIDE_DUST.append((te, green_x(te) - 15, 1.0))
        SLIDE_DUST.append((te, green_x(te) + 85, 0.7))
    SLIDE_DUST.append((G_RUN_END + 0.5, G_XK + 100, 1.6))
    for s in SHOTS:
        grip, ang = green_pose(s)["rifle"]
        CASING_SPAWN.append(rifle_tf(grip, ang, 1)(*PORT))
    font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf", 68)
    return bg, font, vignette()


def main():
    out = sys.argv[1]
    bg, font, vig = setup()
    if "--frame" in sys.argv:
        make_frame(int(sys.argv[sys.argv.index("--frame") + 1]), bg, font, vig).save(out)
        return
    if "--preview" in sys.argv:
        times = [float(v) for v in sys.argv[sys.argv.index("--preview") + 1].split(",")] \
            if len(sys.argv) > 3 else (0.9, 1.3, 1.8, 2.4, 3.6, 5.2, 6.4, 8.0, 8.2, 9.9)
        idx = [int(round(s * FPS)) for s in times]
        sheet = Image.new("RGB", (1080, 360 * 5), "black")
        for k, i in enumerate(idx):
            th = make_frame(i, bg, font, vig).crop((0, BY, W, BY + BH)).resize((540, 360))
            sheet.paste(th, ((k % 2) * 540, (k // 2) * 360))
        sheet.save(out)
        return
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                          "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264",
                          "-preset", "slow", "-crf", "14", "-pix_fmt", "yuv420p",
                          "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    for i in range(int(FPS * DUR)):
        p.stdin.write(make_frame(i, bg, font, vig).tobytes())
    p.stdin.close()
    sys.exit(p.wait())


if __name__ == "__main__":
    main()
