"""Warehouse standoff: 10 s vertical stickman animation (1080x1920, 30 fps).

Usage: python videos/warehouse-standoff/src/render.py OUT.mp4 [--preview SHEET.png]
"""
import math
import random
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
BW, BH = 1080, 700            # scene band (letterboxed like the reference)
BY = (H - BH) // 2
M = 24                         # margin for camera shake
SS = 2                         # supersample
FPS, DUR = 30, 10.0
FLOOR = 590
SHOTS = (246 / 30, 256 / 30, 267 / 30)

THIGH, SHIN, UARM, FARM, TORSO, HEAD_R = 50, 50, 40, 38, 75, 19


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


def ik(a, b, l1, l2, pick):
    dx, dy = b[0] - a[0], b[1] - a[1]
    d = max(1e-3, min(math.hypot(dx, dy), l1 + l2 - 0.5))
    base = math.atan2(dy, dx)
    alpha = math.acos(max(-1, min(1, (l1 * l1 + d * d - l2 * l2) / (2 * l1 * d))))
    cands = [(a[0] + l1 * math.cos(base + s * alpha), a[1] + l1 * math.sin(base + s * alpha)) for s in (1, -1)]
    return max(cands, key=pick)


# ---------------------------------------------------------------- drawing helpers
class Canvas:
    def __init__(self, img, ox=M, oy=M):
        self.img = img
        self.d = ImageDraw.Draw(img)
        self.ox, self.oy = ox, oy

    def p(self, pt):
        return ((pt[0] + self.ox) * SS, (pt[1] + self.oy) * SS)

    def poly(self, pts, fill, outline=None, width=0):
        self.d.polygon([self.p(q) for q in pts], fill=fill, outline=outline, width=width * SS)

    def rect(self, x0, y0, x1, y1, fill, outline=None, width=0):
        a, b = self.p((x0, y0)), self.p((x1, y1))
        self.d.rectangle([a, b], fill=fill, outline=outline, width=width * SS)

    def circle(self, c, r, fill):
        x, y = self.p(c)
        r *= SS
        self.d.ellipse([x - r, y - r, x + r, y + r], fill=fill)

    def line(self, pts, fill, width):
        self.d.line([self.p(q) for q in pts], fill=fill, width=int(width * SS))

    def limb(self, pts, fill, width):
        self.line(pts, fill, width)
        for q in pts:
            self.circle(q, width / 2, fill)

    def pie(self, c, r, start, end, fill):
        x, y = self.p(c)
        r *= SS
        self.d.pieslice([x - r, y - r, x + r, y + r], start, end, fill=fill)


# ---------------------------------------------------------------- background
def draw_background(cv):
    ext = M + 4
    cv.rect(-ext, -ext, BW + ext, 512, "#8d8f90")
    for x in range(-60, BW + 80, 180):                     # wall panels
        cv.line([(x, 30), (x, 500)], "#808283", 3)
    cv.rect(-ext, -ext, BW + ext, 32, "#696b6d")            # ceiling beam
    for x in range(-40, BW + 60, 120):
        cv.rect(x, 20, x + 8, 36, "#5c5e60")
    cv.rect(-ext, 494, BW + ext, 512, "#a9abac")            # baseboard
    cv.rect(-ext, 512, BW + ext, BH + ext, "#77797b")       # floor
    for y in (548, 622, 676):
        cv.line([(-ext, y), (BW + ext, y)], "#7f8183", 2)
    cv.rect(-ext, 512, BW + ext, 518, "#6b6d6f")

    # hanging lamp
    cv.line([(330, 32), (330, 92)], "#3a3a3a", 3)
    cv.poly([(300, 108), (360, 108), (346, 90), (314, 90)], "#4a4c4e")
    cv.rect(316, 108, 344, 112, "#f2efd8")

    # mesh cabinet (left)
    cv.rect(18, 286, 150, 512, "#5c6350")
    cv.rect(26, 296, 142, 504, "#4a5040")
    x0, y0, x1, y1 = cv.p((26, 296)) + cv.p((142, 504))
    mesh = Image.new("RGB", (int(x1 - x0), int(y1 - y0)), "#4a5040")
    md = ImageDraw.Draw(mesh)
    step, mw = 12 * SS, 2 * SS
    for x in range(-mesh.height, mesh.width + mesh.height, step):
        md.line([(x, 0), (x + mesh.height, mesh.height)], fill="#5f6753", width=mw)
        md.line([(x + mesh.height, 0), (x, mesh.height)], fill="#5f6753", width=mw)
    cv.img.paste(mesh, (int(x0), int(y0)))
    cv.rect(18, 286, 150, 296, "#6b725e")
    cv.line([(84, 296), (84, 504)], "#3d4235", 4)

    # IBC tank (blue with cage)
    tx0, tx1, ty0, ty1 = 600, 790, 352, 494
    cv.rect(tx0 - 4, ty1, tx1 + 4, 512, "#3b3c3e")         # pallet
    for x in (tx0 + 6, (tx0 + tx1) // 2 - 10, tx1 - 26):
        cv.rect(x, ty1 + 4, x + 20, 512, "#2b2c2d")
    cv.rect(tx0, ty0, tx1, ty1, "#3f6fb4")
    cv.rect(tx0 + 6, ty0 + 6, tx0 + 40, ty1 - 6, "#4d7dc2")
    for x in range(tx0, tx1 + 1, 38):
        cv.line([(x, ty0), (x, ty1)], "#cdd4dc", 4)
    for y in range(ty0, ty1 + 1, 35):
        cv.line([(tx0, y), (tx1, y)], "#cdd4dc", 4)
    cv.rect(tx0 + 80, ty0 - 14, tx0 + 110, ty0, "#2f2f30")    # cap

    # vertical pipe + wall box
    cv.rect(566, 30, 576, 512, "#6a6c6e")
    cv.rect(870, 196, 960, 252, "#3e4042")
    cv.rect(880, 206, 932, 222, "#9fb3a0")
    cv.rect(880, 230, 950, 236, "#6d7072")
    cv.line([(915, 252), (915, 330)], "#3e4042", 3)

    # green crates (stacked) + long low crate
    def crate(x0, y0, x1, y1):
        cv.rect(x0, y0, x1, y1, "#5b6f45")
        cv.rect(x0, y0, x1, y0 + 8, "#6c8253")
        for x in range(x0 + 14, x1 - 6, 22):
            cv.line([(x, y0 + 12), (x, y1 - 6)], "#4e603b", 4)
        cv.rect((x0 + x1) / 2 - 14, (y0 + y1) / 2 - 4, (x0 + x1) / 2 + 14, (y0 + y1) / 2 + 4, "#2f3a26")
    crate(838, 434, 988, 512)
    crate(846, 360, 980, 434)
    crate(990, 470, 1100, 512)
    crate(-30, 470, 14, 512)


def draw_barrier(cv):
    pts = [(440, 598), (590, 598), (578, 576), (536, 542), (530, 482),
           (498, 482), (492, 542), (452, 576)]
    cv.poly([(x + 6, y) for x, y in pts], "#5f6163")        # soft shadow
    cv.poly(pts, "#e4e5e6")
    cv.poly([(536, 542), (578, 576), (590, 598), (556, 598), (530, 482)], "#cacccd")
    cv.line([(452, 576), (578, 576)], "#d3d5d6", 3)
    cv.circle((512, 566), 5, "#57595b")


# ---------------------------------------------------------------- characters
GREEN = dict(body="#6e9440", back="#55752e", vest="#4f6a2c", helmet="#48612a", head="#6e9440")
BLACK = dict(body="#1d1d1f", back="#0c0c0d", vest=None, helmet=None, head="#1d1d1f")


def gait(dist, A, stance, lift, phase0):
    """Planted-foot gait: returns (forward offset of foot from hip, lift)."""
    cycle = 2 * A / stance
    u = (dist / cycle + phase0) % 1.0
    if u < stance:
        return A - 2 * A * (u / stance), 0.0
    v = (u - stance) / (1 - stance)
    e = v * v * (3 - 2 * v)
    return -A + 2 * A * e, lift * math.sin(math.pi * v)


def locomotion(hx, dist, f, run):
    if run:
        A, st, lift, hip_h, lean, bob = 58, 0.42, 34, 92, 0.28, 6
    else:
        A, st, lift, hip_h, lean, bob = 30, 0.6, 16, 97, 0.05, 3
    cycle = 2 * A / st
    u = dist / cycle
    feet = []
    for ph in (0.0, 0.5):
        dx, ly = gait(dist, A, st, lift, ph)
        feet.append((hx + f * dx, FLOOR - ly))
    hy = FLOOR - hip_h - bob * abs(math.cos(2 * math.pi * u))
    return dict(hip=(hx, hy), lean=lean, feet=feet, u=u)


def shoulder_of(hip, lean, f):
    return (hip[0] + f * math.sin(lean) * TORSO * 0.88, hip[1] - math.cos(lean) * TORSO * 0.88)


def rifle_shape(cv, grip, ang, f):
    c, s = math.cos(ang), math.sin(ang)

    # NOTE: local x = barrel forward, y = down; mirrored by f.
    def T(pts):
        out = []
        for x, y in pts:
            wx = x * c - y * s
            wy = x * s + y * c
            out.append((grip[0] + f * wx, grip[1] + wy))
        return out
    dark, mid = "#2c2e30", "#45484b"
    cv.poly(T([(-58, -4), (-18, -6), (-18, 6), (-58, 12)]), mid)              # stock
    cv.poly(T([(-20, -9), (40, -9), (40, 4), (-20, 5)]), dark)                # receiver
    cv.poly(T([(-6, -14), (22, -14), (22, -9), (-6, -9)]), dark)              # optic rail
    cv.poly(T([(40, -6), (80, -6), (80, -2), (40, -2)]), dark)                # barrel
    cv.poly(T([(6, 4), (16, 4), (20, 26), (10, 27)]), mid)                    # magazine
    cv.poly(T([(-6, 4), (2, 4), (-1, 18), (-8, 17)]), dark)                   # grip
    return T([(36, 0)])[0], T([(82, -4)])[0]


def draw_figure(cv, pose, pal, f):
    hip, lean = pose["hip"], pose["lean"]
    sh = shoulder_of(hip, lean, f)
    neck = (hip[0] + f * math.sin(lean) * TORSO, hip[1] - math.cos(lean) * TORSO)
    hl = lean + pose.get("head_tilt", 0.0)
    head = (neck[0] + f * math.sin(hl) * (HEAD_R + 5), neck[1] - math.cos(hl) * (HEAD_R + 5))

    def knee(a, b, mode):
        if mode == "down":
            return ik(a, b, THIGH, SHIN, lambda q: q[1])
        return ik(a, b, THIGH, SHIN, lambda q: f * q[0])

    def elbow(a, b):
        return ik(a, b, UARM, FARM, lambda q: q[1] - 0.6 * f * q[0])

    modes = pose.get("knee_modes", ("fwd", "fwd"))
    feet = pose["feet"]
    hands = pose["hands"]
    out = {}

    # back leg/arm (index 1) behind body
    k = knee(hip, feet[1], modes[1])
    cv.limb([hip, k, feet[1]], pal["back"], 11)
    if hands:
        e = elbow(sh, hands[1])
        cv.limb([sh, e, hands[1]], pal["back"], 10)
    if pose.get("rifle"):
        grip, ang = pose["rifle"]
        out["front"], out["muzzle"] = rifle_shape(cv, grip, ang, f)
    k = knee(hip, feet[0], modes[0])
    cv.limb([hip, k, feet[0]], pal["body"], 11)
    cv.limb([hip, neck], pal["body"], 14)
    if pal["vest"]:
        n = (math.sin(lean) * f, -math.cos(lean))
        px = (-n[1] * 9, n[0] * 9)
        a = (hip[0] + n[0] * 22, hip[1] + n[1] * 22)
        b = (hip[0] + n[0] * 66, hip[1] + n[1] * 66)
        cv.poly([(a[0] - px[0], a[1] - px[1]), (a[0] + px[0], a[1] + px[1]),
                 (b[0] + px[0], b[1] + px[1]), (b[0] - px[0], b[1] - px[1])], pal["vest"])
    cv.circle(head, HEAD_R, pal["head"])
    if pal["helmet"]:
        hc = (head[0] - f * 1, head[1] - 3)
        cv.pie(hc, HEAD_R + 4, 180, 360, pal["helmet"])
        cv.line([(hc[0] - (HEAD_R + 6), hc[1]), (hc[0] + (HEAD_R + 6), hc[1])], pal["helmet"], 5)
        cv.line([(head[0] - f * 4, head[1] + 2), (head[0] + f * 6, head[1] + 12)], "#3d5223", 2)
    if hands:
        e = elbow(sh, hands[0])
        cv.limb([sh, e, hands[0]], pal["body"], 10)
    return out


# ---------------------------------------------------------------- green soldier
RUN_V, RUN_STOP, DECEL = 175.0, 2.35, 0.75


def green_x(t):
    if t <= RUN_STOP:
        return -90 + RUN_V * t
    s = min(t - RUN_STOP, DECEL)
    return -90 + RUN_V * RUN_STOP + RUN_V * (s - s * s / (2 * DECEL))


GX_FINAL = green_x(99)


def rifle_pose(sh, f, offx, offy, ang):
    return (sh[0] + f * offx, sh[1] + offy), ang


def green_pose(t):
    f = 1
    x = green_x(t)
    loc = locomotion(x, x + 90, f, run=True)
    w = smooth(2.45, 3.35, t)                      # run -> kneel
    a = smooth(3.7, 4.5, t)                        # ready -> aim
    breathe = math.sin(t * 2.4) * 1.5 * w

    kneel_hip = (GX_FINAL, FLOOR - 54 + breathe)
    kneel_feet = [(GX_FINAL + 42, FLOOR), (GX_FINAL - 52, FLOOR - 3)]
    kneel_lean = lerp(0.22, 0.12, a)

    hip = lerp2(loc["hip"], kneel_hip, w)
    lean = lerp(loc["lean"], kneel_lean, w)
    feet = [lerp2(loc["feet"][i], kneel_feet[i], w) for i in range(2)]
    sh = shoulder_of(hip, lean, f)

    # rifle: port-arms (run) -> low ready (kneel) -> aim
    run_r = (14, 36, -0.55)
    ready_r = (18, 34, 0.25)
    aim_r = (24, 7, -0.07)
    r = [lerp(run_r[i], ready_r[i], w) for i in range(3)]
    r = [lerp(r[i], aim_r[i], a) for i in range(3)]
    # recoil
    kick = 0.0
    for s in SHOTS:
        if 0 <= t - s < 0.18:
            kick = max(kick, math.exp(-(t - s) * 22))
    r[0] -= 6 * kick
    r[2] -= 0.08 * kick
    grip, ang = rifle_pose(sh, f, *r)
    front = (grip[0] + f * 36 * math.cos(ang), grip[1] + 36 * math.sin(ang))
    modes = ("fwd", "down") if w > 0.5 else ("fwd", "fwd")
    return dict(hip=hip, lean=lean, feet=feet, hands=[front, grip], rifle=(grip, ang),
                knee_modes=modes, head_tilt=lerp(-0.1, 0.12, a) * w)


# ---------------------------------------------------------------- black stickman
B_START, B_STOP, B_X0, B_X1 = 3.6, 7.6, 1170.0, 800.0


def black_x(t):
    # constant speed, then ease out in the last 0.8 s
    tt = max(0.0, min(t, B_STOP)) - B_START
    T, D = B_STOP - B_START, 0.8
    v = (B_X0 - B_X1) / (T - D / 2)
    if tt <= 0:
        return B_X0
    if tt <= T - D:
        return B_X0 - v * tt
    s = tt - (T - D)
    return B_X0 - v * (T - D) - v * (s - s * s / (2 * D))


def black_pose(t):
    f = -1
    x = black_x(t)
    dist = B_X0 - x
    loc = locomotion(x, dist, f, run=False)
    w = smooth(B_STOP - 0.35, B_STOP + 0.25, t)
    idle_feet = [(x - 16, FLOOR), (x + 14, FLOOR)]
    breathe = math.sin(t * 2.1) * 1.2
    hip = lerp2(loc["hip"], (x, FLOOR - 98 + breathe), w)
    feet = [lerp2(loc["feet"][i], idle_feet[i], w) for i in range(2)]
    lean = lerp(loc["lean"], 0.0, w)
    sh = shoulder_of(hip, lean, f)
    swing = 0.55 * math.sin(2 * math.pi * loc["u"]) * (1 - w)
    hands = []
    for sgn in (1, -1):
        a = math.pi / 2 - sgn * swing * f
        hands.append((sh[0] + math.cos(a) * 72 + f * 4, sh[1] + math.sin(a) * 72))
    flinch = 0.0
    for s in SHOTS:
        if 0 <= t - s < 0.3:
            flinch = max(flinch, math.exp(-(t - s) * 12))
    hip = (hip[0] + 4 * flinch, hip[1])
    return dict(hip=hip, lean=lean - 0.08 * flinch, feet=feet, hands=hands)


# ---------------------------------------------------------------- frame
def muzzle_flash(cv, muzzle, ang, k):
    c, s = math.cos(ang), math.sin(ang)

    def P(x, y):
        return (muzzle[0] + x * c - y * s, muzzle[1] + x * s + y * c)
    cv.circle(P(12, 0), 17 * k, (255, 196, 90))
    cv.poly([P(0, -7), P(46 * k, 0), P(0, 7)], "#ffb02e")
    cv.poly([P(6, -2), P(20 * k, -22 * k), P(14, 0), P(20 * k, 22 * k), P(6, 2)], "#ffb02e")
    cv.poly([P(0, -5), P(30 * k, 0), P(0, 5)], "#ffe066")
    cv.circle(P(8, 0), 7 * k, "#fff7d6")


def shake_offset(t, rng):
    amp = 0.0
    for s in SHOTS:
        if 0 <= t - s < 0.25:
            amp = max(amp, 7 * math.exp(-(t - s) * 14))
    return rng.uniform(-amp, amp), rng.uniform(-amp, amp)


def make_frame(i, bg, font):
    t = i / FPS
    img = bg.copy()
    cv = Canvas(img)
    g = draw_figure(cv, green_pose(t), GREEN, 1)
    draw_barrier(cv)
    for s in SHOTS:
        dt = t - s
        if -1e-6 <= dt < 2.5 / FPS:
            muzzle_flash(cv, g["muzzle"], green_pose(t)["rifle"][1], 1.0 if dt < 0.5 / FPS else 0.6)
    draw_figure(cv, black_pose(t), BLACK, -1)

    rng = random.Random(i * 7919)
    dx, dy = shake_offset(t, rng)
    band = img.resize(((BW + 2 * M), (BH + 2 * M)), Image.LANCZOS)
    band = band.transform((BW, BH), Image.AFFINE, (1, 0, M + dx, 0, 1, M + dy), Image.BILINEAR)
    frame = Image.new("RGB", (W, H), "black")
    frame.paste(band, (0, BY))
    d = ImageDraw.Draw(frame)
    d.text((W // 2, BY + BH - 46), "Noahh", font=font, fill="white", anchor="mm")
    return frame


def main():
    out = sys.argv[1]
    preview = sys.argv[sys.argv.index("--preview") + 1] if "--preview" in sys.argv else None
    bg = Image.new("RGB", ((BW + 2 * M) * SS, (BH + 2 * M) * SS), "#8d8f90")
    draw_background(Canvas(bg))
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf", 38)
    n = int(FPS * DUR)
    if preview:
        idx = [int(s * FPS) for s in (0.5, 1.5, 2.6, 3.2, 4.0, 5.5, 7.0, 8.2, 8.6, 9.8)] if '--full' not in sys.argv else [246]
        thumbs = [make_frame(i, bg, font).crop((0, BY, W, BY + BH)).resize((540, 350)) for i in idx]
        sheet = Image.new("RGB", (1080, 350 * 5), "black")
        for k, th in enumerate(thumbs):
            sheet.paste(th, ((k % 2) * 540, (k // 2) * 350))
        if '--full' in sys.argv:
            make_frame(idx[0], bg, font).save(preview)
            return
        sheet.save(preview)
        return
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                          "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264",
                          "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
                          "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    for i in range(n):
        p.stdin.write(make_frame(i, bg, font).tobytes())
    p.stdin.close()
    sys.exit(p.wait())


if __name__ == "__main__":
    main()
