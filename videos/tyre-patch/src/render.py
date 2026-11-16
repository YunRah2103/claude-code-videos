"""tyre-patch: 60 fps structure-matched ASCII short. Side-view E92 (approved art) driving, top-down contact-patch schematic,
hand + A4 comparison, wheel at 14 rev/s. Everything is analytic/vector so the camera can move smoothly before ASCII matching.

python render.py still OUTDIR 1.0 7.9 ...
python render.py video OUT.mp4
"""
import importlib.util
import json
import math
import subprocess
import sys
import time
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / 'ascii-terminal-test/src'))
import ascii_car as AC   # noqa: E402  (approved glyph atlas, matcher, side-view art)
import render as RD      # noqa: E402  (fonts, scanlines, vignette)

W, H, FPS, SUB = 1080, 1920, 60, 2
DUR = 19.8
N = int(round(DUR * FPS))
AC.EMA = 0.45                       # per-step EMA at 60 fps (same time constant as 0.6 at 30 fps)
WORDS = json.load(open(HERE / 'words.json'))


def wt(word, k=0):
    return [w['s'] for w in WORDS if w['w'] == word][k]


def sstep(a, b, x):
    u = np.clip((x - a) / (b - a), 0, 1)
    return u * u * u * (u * (6 * u - 15) + 10)


GX, GY = np.meshgrid(np.arange(W, dtype=np.float32), np.arange(H, dtype=np.float32))

# ---------------------------------------------------------------- timeline (anchored to the VO words)
T_SPEED, T_BRAKE, T_TURN = wt('speeding'), wt('braking'), wt('turning')
T_FOUR, T_HAND = wt('four'), wt('hand')
T_ALL4, T_SHEET = wt('four', 1), wt('sheet')
T_HUND, T_14, T_SEC = wt('hundred'), wt('fourteen'), wt('second')
T_AND, T_ROAD = wt('and'), wt('road')
CASC = [(T_FOUR + 0.62, 0.95, 'side', 'top'),                # decompose side view -> reassemble schematic
        (T_SHEET + 0.62, 0.95, 'top', 'side')]


def scene_at(t):
    for k, (T, D, a, b) in enumerate(CASC):
        if T <= t < T + D:
            return None, k
    return ('top' if CASC[0][0] + CASC[0][1] <= t < CASC[1][0] else 'side'), None


# ---------------------------------------------------------------- side view: wheel speed (rev/s, visual) and loop-exact phases
def omega(t):
    w = 1.5
    w += 1.3 * (sstep(T_SPEED - 0.1, T_SPEED + 0.5, t) - sstep(T_BRAKE - 0.15, T_BRAKE + 0.35, t))
    w -= 0.9 * (sstep(T_BRAKE - 0.15, T_BRAKE + 0.35, t) - sstep(T_TURN + 0.1, T_TURN + 0.8, t))
    w += 12.5 * (sstep(T_14 - 1.0, T_14 + 0.35, t) - sstep(T_AND - 0.2, T_ROAD - 0.6, t))
    return w


_tt = np.linspace(0, DUR, 20001)
_cum = np.concatenate([[0], np.cumsum((omega(_tt[1:]) + omega(_tt[:-1])) / 2 * np.diff(_tt))])   # revolutions


def revs(t):
    return float(np.interp(t, _tt, _cum))


REV_END = _cum[-1]
SPOKES = 10


def wheel_angle(t):                                       # spokes repeat every 1/10 rev -> make the loop exact
    return 2 * math.pi * revs(t) * (round(REV_END * SPOKES) / SPOKES) / REV_END


def road_shift(t, sp):                                    # px; exact whole periods per loop for spacing sp
    circ = 2 * math.pi * AC.SWR
    d = revs(t) * circ
    dend = REV_END * circ
    return d * (round(dend / sp) * sp) / dend


# pitch (deg, + = nose down), body lift
def pitch(t):
    return (-1.1 * (sstep(T_SPEED - 0.1, T_SPEED + 0.35, t) - sstep(T_BRAKE - 0.2, T_BRAKE + 0.15, t))
            + 1.5 * (sstep(T_BRAKE - 0.2, T_BRAKE + 0.2, t) - sstep(T_TURN - 0.05, T_TURN + 0.5, t))
            - 0.5 * (sstep(T_14 - 0.8, T_14, t) - sstep(T_14 + 0.6, T_14 + 1.4, t)))


def sway(t):                                              # "turning": small lateral roll read as a vertical bob
    return 4.0 * math.sin(2 * math.pi * 1.6 * (t - T_TURN)) * (sstep(T_TURN - 0.1, T_TURN + 0.2, t) - sstep(T_TURN + 0.5, T_TURN + 0.9, t))


SIDE = AC.SIDE
FW, RW = AC.SWHEELS                                      # front (left) and rear wheel centres
WR = AC.SWR * 1.03
FLOOR = FW[1] + AC.SWR
_wm = np.zeros((H, W), np.float32)
for cx, cy in (FW, RW):
    cv2.circle(_wm, (int(round(cx)), int(round(cy))), int(round(WR)), 1.0, -1, cv2.LINE_AA)
BODY = SIDE * (1 - _wm)
# light boost on wheels so spokes read
WHEEL_BOX = []
for cx, cy in (FW, RW):
    x0, y0 = int(cx - WR - 2), int(cy - WR - 2)
    x1, y1 = int(cx + WR + 3), int(cy + WR + 3)
    WHEEL_BOX.append((x0, y0, x1, y1, cx, cy))

ROWS_ROAD = []                                            # perspective dot rows below the floor: (y, radius, spacing, alpha)
_y = FLOOR + 22.0
for k in range(12):
    s = 1.0 + 0.30 * k
    ROWS_ROAD.append((_y, 1.2 * s, 22.0 * s, 0.50 * math.exp(-k / 8)))
    _y += 15.0 * s
STREAKS = [(int(FW[1] - 150 + (i * 53) % 260), 90 + (i * 151) % 260, 0.6 + 0.4 * ((i * 7) % 5) / 4, 0.10 + 0.04 * (i % 3))
           for i in range(10)]


def wheel_layer(out, t, shutter):
    """rotate the two wheel discs; angular motion blur over the shutter interval (exact at any speed)."""
    a0 = wheel_angle(t)
    da = 2 * math.pi * omega(t) * shutter
    K = int(np.clip(math.ceil(abs(math.degrees(da)) / 2.5), 1, 24))
    for (x0, y0, x1, y1, cx, cy) in WHEEL_BOX:
        u, v = GX[y0:y1, x0:x1] - cx, GY[y0:y1, x0:x1] - cy
        inside = (u * u + v * v < WR * WR).astype(np.float32)
        acc = np.zeros_like(u)
        for k in range(K):
            a = -(a0 + da * ((k + 0.5) / K - 0.5))          # car faces left and drives left: wheels turn counter-clockwise
            ca, sa = math.cos(a), math.sin(a)
            mx = (cx + u * ca - v * sa).astype(np.float32)
            my = (cy + u * sa + v * ca).astype(np.float32)
            acc += cv2.remap(SIDE, mx, my, cv2.INTER_LINEAR)
        gain = 1.9 if K <= 2 else 1.9 - 0.75 * min(1.0, (K - 2) / 10)
        w = np.clip(acc / K * gain, 0, 1) * inside
        out[y0:y1, x0:x1] = np.maximum(out[y0:y1, x0:x1], w)


def patch_glow(t):
    """contact-patch glow under the tyres: on at 'four patches', peak on 'road'."""
    return float(0.9 * (sstep(T_FOUR - 0.15, T_FOUR + 0.2, t) * (1 - sstep(CASC[0][0], CASC[0][0] + 0.2, t)))
                 + 1.0 * sstep(T_AND + 0.4, T_ROAD - 0.1, t) * (1 - sstep(DUR - 0.9, DUR - 0.15, t)))


# ---------------------------------------------------------------- scenery: parallax skyline + lamp posts (loop-exact)
def exact_shift(t, period, factor):
    circ = 2 * math.pi * AC.SWR
    dend = REV_END * circ * factor
    return revs(t) * circ * factor * (max(1, round(dend / period)) * period) / dend


_rs = np.random.default_rng(5)
SKY_P = 2160
SKY = np.zeros((H, SKY_P), np.float32)
SKY_BASE = int(FLOOR) - 60
_x = 0
while _x < SKY_P - 40:
    bw = int(_rs.integers(70, 170)); bh = int(_rs.integers(300, 640))
    x0, x1 = _x, min(_x + bw, SKY_P - 20)
    y0 = SKY_BASE - bh
    SKY[y0:SKY_BASE, x0:x0 + 3] = 0.55; SKY[y0:SKY_BASE, x1 - 3:x1] = 0.55; SKY[y0:y0 + 3, x0:x1] = 0.55
    for wy in range(y0 + 18, SKY_BASE - 14, 26):                   # lit windows
        for wx in range(x0 + 14, x1 - 14, 22):
            if _rs.random() < 0.45:
                SKY[wy:wy + 8, wx:wx + 6] = 0.30 + 0.35 * _rs.random()
    _x = x1 + int(_rs.integers(6, 40))
SKY = cv2.GaussianBlur(SKY, (0, 0), 0.8)
SKY_FADE = np.clip((GY[:, :1] - (SKY_BASE - 680)) / 220, 0, 1) * 0.6
POST_P, POST_F = 640.0, 0.55


def scenery(t, shutter):
    out = np.zeros((H, W), np.float32)
    sh = exact_shift(t, SKY_P, 0.10)
    xi = ((GX[0] - sh) % SKY_P).astype(np.int32)
    out[:] = SKY[:, xi] * SKY_FADE
    # lamp posts (mid-ground), horizontally motion-blurred over the shutter
    v = 2 * math.pi * AC.SWR * omega(t) * POST_F
    d = v * shutter
    K = int(np.clip(math.ceil(d / 3), 1, 40))
    x = GX[0]
    prof = np.zeros(W, np.float32)
    head = np.zeros(W, np.float32)
    for k in range(K):
        ps = exact_shift(t + shutter * ((k + 0.5) / K - 0.5), POST_P, POST_F)
        dx = ((x - ps) % POST_P) - POST_P / 2
        prof += np.clip(4.5 - np.abs(dx), 0, 1) / K
        head += np.clip(26 - np.abs(dx + 18), 0, 1) / K
    top = int(FLOOR) - 520
    out[top:int(FLOOR) - 4] = np.maximum(out[top:int(FLOOR) - 4], 0.6 * prof[None, :])
    out[top:top + 8] = np.maximum(out[top:top + 8], 0.7 * head[None, :])
    lamp = np.exp(-((GY[top - 10:top + 60] - (top + 14)) / 18) ** 2)
    out[top - 10:top + 60] = np.maximum(out[top - 10:top + 60], 0.35 * lamp * cv2.GaussianBlur(head[None, :], (0, 0), 6)[0][None, :] * 2)
    return out


BOB_F = round(1.4 * DUR) / DUR


def light_sweep(t):
    for (a, b) in ((0.15, 1.35), (T_AND + 0.3, T_ROAD + 0.2)):
        p = float(sstep(a, b, t))
        if 0 < p < 1:
            pos = -300 + 1700 * p
            return np.exp(-(((GX - pos) + 0.5 * (GY - 1100)) / 60) ** 2)
    return None


def side_canvas(t, cam):
    out = scenery(t, 0.5 / FPS)
    # road: perspective dot rows streaming backwards (to the right) + a crisp floor line
    for (yy, r, sp, al) in ROWS_ROAD:
        sh = road_shift(t, sp)
        dx = ((GX[0] - sh) % sp) - sp / 2
        for yi in range(int(yy - r - 2), int(yy + r + 3)):
            if 0 <= yi < H:
                dd = np.sqrt(dx * dx + (yi - yy) ** 2)
                out[yi] = np.maximum(out[yi], al * np.clip(r - dd + 0.5, 0, 1))
    # speed streaks behind/above the road (scale with wheel speed)
    sp_n = np.clip((omega(t) - 1.0) / 3.0, 0, 1.0)
    if sp_n > 0.01:
        for (yy, ln, cyc, al) in STREAKS:
            span = W + 3 * ln
            head = (road_shift(t, span) * cyc * 1.7 + yy * 7.3) % span - ln
            tail = np.clip(1 - (head - GX[0]) / (ln * (0.6 + sp_n)), 0, 1) * (GX[0] <= head)
            out[yy] = np.maximum(out[yy], sp_n * al * 2.2 * tail ** 1.5)
    # body: pitch about the rear contact point, sway
    pa, lift = pitch(t), sway(t)
    M = cv2.getRotationMatrix2D((float(RW[0]), float(FLOOR)), -pa, 1.0)
    M[1, 2] += lift - 2.0 * abs(pa) + 1.3 * math.sin(2 * math.pi * BOB_F * t)
    body = cv2.warpAffine(BODY, M, (W, H), flags=cv2.INTER_LINEAR)
    ls = light_sweep(t)
    if ls is not None:
        body = np.clip(body + 0.55 * ls * (body > 0.03), 0, 1.2)
    occ = cv2.warpAffine(AC.SIDEM, M, (W, H), flags=cv2.INTER_LINEAR)
    occ = np.maximum(occ, _wm)
    out = np.maximum(out * (1 - occ), body)
    wheel_layer(out, t, 0.5 / FPS)
    # brake glow on the front disc while braking
    bg = float(sstep(T_BRAKE - 0.1, T_BRAKE + 0.2, t) - sstep(T_TURN - 0.1, T_TURN + 0.4, t))
    if bg > 0.01:
        d = np.hypot(GX - FW[0], GY - FW[1])
        out = out + 0.55 * bg * np.exp(-((d - 0.42 * AC.SWR) / 9) ** 2) * (d < WR)
    # contact patches
    g = patch_glow(t)
    if g > 0.01:
        for cx, _ in (FW, RW):
            e = np.exp(-(((GX - cx) / (0.34 * AC.SWR)) ** 6 + ((GY - FLOOR - 2) / 4.5) ** 2))
            out = out + 1.3 * g * (1.0 + 0.15 * math.sin(2 * math.pi * 2 * t)) * e
            out = out + 0.45 * g * np.exp(-(((GX - cx) / (0.7 * AC.SWR)) ** 2 + ((GY - FLOOR - 4) / 14) ** 2))
    # glossy floor reflection
    refl = cv2.flip(out[int(FLOOR) - 320:int(FLOOR)], 0)
    fade = np.linspace(0.20, 0.0, 320, dtype=np.float32)[:, None]
    seg = out[int(FLOOR):int(FLOOR) + 320]
    out[int(FLOOR):int(FLOOR) + 320] = np.maximum(seg, refl[:seg.shape[0]] * fade[:seg.shape[0]])
    return apply_cam(out, cam)


def apply_cam(img, cam):
    z, (px, py), (sx, sy) = cam                          # zoom z about world point (px,py) placed at screen (sx,sy)
    if abs(z - 1) < 1e-4 and abs(px - sx) < 1e-3 and abs(py - sy) < 1e-3:
        return img
    M = np.float32([[z, 0, sx - z * px], [0, z, sy - z * py]])
    return cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR)


def side_cam(t):
    """A: slow push-in. C: push into the front wheel for the 14 rev/s beat. D: back out to the full car (loop-exact)."""
    home = (W / 2, FLOOR - 140)
    if t < CASC[0][0] + CASC[0][1]:
        return 1.0 + 0.10 * float(sstep(0.0, CASC[0][0], t)), home, home
    zin = float(sstep(T_HUND - 0.6, T_14 - 0.1, t) - sstep(T_SEC + 0.3, T_ROAD - 0.4, t))
    target = (FW[0] + 30, FW[1] - 30)
    p = (home[0] + (target[0] - home[0]) * zin, home[1] + (target[1] - home[1]) * zin)
    return 1.0 + 1.55 * zin, p, home


# ---------------------------------------------------------------- top-down schematic (world units: cm; y forward = up)
PATCH = (14.85, 10.5)                                     # one patch: a quarter of A4 (156 cm^2 ~ an adult hand)
WHEELS_T = [(-86.0, -138.0), (86.0, -138.0), (-86.0, 138.0), (86.0, 138.0)]
FOCUS = 2                                                 # rear-left patch is the one we zoom into
SHEET_C = (WHEELS_T[FOCUS][0] + PATCH[0] / 2, WHEELS_T[FOCUS][1] - PATCH[1] / 2)
QUAD = {2: (-1, 1), 3: (1, 1), 0: (-1, -1), 1: (1, -1)}   # where each patch lands in the 2x2 sheet
CY_T = 1180.0


def top_cam(t):
    z_fit, z_close = 2.05, 26.0
    a = sstep(T_FOUR + 1.9, T_HAND - 0.35, t)            # zoom into one patch
    b = sstep(T_ALL4 - 0.1, T_SHEET - 0.3, t)             # recentre on the sheet, slightly wider
    lz = math.log(z_fit) + (math.log(z_close) - math.log(z_fit)) * a + (math.log(22.0) - math.log(z_close)) * b
    z = math.exp(lz)
    # keep the focus patch's screen position on a straight path while zooming (zoom about it)
    f = np.array(WHEELS_T[FOCUS]); c0 = np.array([0.0, 0.0])
    w = (1 / z_fit - 1 / z) / (1 / z_fit - 1 / z_close) if a < 1 else 1.0
    c = c0 + (f - c0) * min(max(w, 0.0), 1.0)
    c = c + (np.array(SHEET_C) - f) * b
    return z, c


def to_px(p, z, c):
    return (W / 2 + (p[0] - c[0]) * z, CY_T + (p[1] - c[1]) * z)


def rrect_pts(cx, cy, w, h, r, n=8):
    pts = []
    for (qx, qy, a0) in ((cx + w / 2 - r, cy - h / 2 + r, -90), (cx + w / 2 - r, cy + h / 2 - r, 0),
                         (cx - w / 2 + r, cy + h / 2 - r, 90), (cx - w / 2 + r, cy - h / 2 + r, 180)):
        for k in range(n + 1):
            a = math.radians(a0 + 90 * k / n)
            pts.append((qx + r * math.cos(a), qy + r * math.sin(a)))
    return pts


def poly_px(img, pts, z, c, val, th, closed=True, fill=False):
    P = np.array([to_px(p, z, c) for p in pts]) * 16
    P = P.round().astype(np.int32).reshape(-1, 1, 2)
    if fill:
        cv2.fillPoly(img, [P], val, cv2.LINE_AA, shift=4)
    else:
        cv2.polylines(img, [P], closed, val, max(1, int(round(th))), cv2.LINE_AA, shift=4)


CAR_BODY = rrect_pts(0, 0, 182, 461, 46)
CABIN = rrect_pts(0, 18, 150, 190, 34)
HOOD = [(-62, -205), (-48, -100), (48, -100), (62, -205)]
REAR = [(-60, 200), (-50, 140), (50, 140), (60, 200)]
MIRRORS = [rrect_pts(-100, -78, 22, 12, 5), rrect_pts(100, -78, 22, 12, 5)]


HAND_SHAPES = None


def hand_mask(z, c, centre, reveal):
    """right hand, palm down, fingers pointing right (+x), laid over the patch; world cm -> screen (fill, outline)."""
    m = np.zeros((H, W), np.uint8)
    hx, hy = centre
    S = 16

    def L(x, y):                                       # local hand coords (fingers toward -y) -> world, rotated 90 deg
        return (hx - (y + 0.8), hy + x)

    def P(x, y):
        return tuple(int(round(v * S)) for v in to_px(L(x, y), z, c))

    def fill_local(pts):
        PP = (np.array([to_px(L(*p), z, c) for p in pts]) * S).round().astype(np.int32)
        cv2.fillPoly(m, [PP], 255, cv2.LINE_AA, shift=4)

    fill_local(rrect_pts(0, 2.0, 8.8, 10.0, 2.6))
    for (x, y0, L_, ang, wdt) in ((-3.6, -2.2, 5.9, -17, 1.6), (-1.2, -2.8, 7.3, -6, 1.7), (1.2, -2.8, 7.9, 4, 1.7),
                                  (3.5, -2.3, 7.0, 14, 1.65)):
        a = math.radians(ang)
        x1, y1 = x + 1.15 * L_ * math.sin(a), y0 - 1.15 * L_ * math.cos(a)
        cv2.line(m, P(x, y0), P(x1, y1), 255, max(1, int(round(wdt * z))), cv2.LINE_AA, shift=4)
    cv2.line(m, P(-3.9, 4.6), P(-8.6, 0.2), 255, max(1, int(round(2.0 * z))), cv2.LINE_AA, shift=4)     # thumb
    f = cv2.GaussianBlur(m.astype(np.float32) / 255, (0, 0), 1.0)
    k = max(3, int(0.36 * z)) | 1
    fb = (f > 0.5).astype(np.uint8)
    o = (cv2.dilate(fb, np.ones((k, k), np.uint8)) - cv2.erode(fb, np.ones((k, k), np.uint8))).astype(np.float32)
    halo = cv2.dilate(o, np.ones((2 * k + 1, 2 * k + 1), np.uint8))
    x_w = to_px(L(0, 8.0), z, c)[0]                    # reveal sweeps from the wrist to the fingertips (+x)
    x_t = to_px(L(0, -11.0), z, c)[0]
    edge = x_w + (x_t - x_w) * reveal
    rv = np.clip((edge - GX) / 40.0, 0, 1)
    return f * rv, o * rv, halo * rv


def patch_pos(i, t):
    """world centre of patch i: on its tyre, then flying into the 2x2 sheet (staggered, ease-out, overshoot-free)."""
    home = np.array(WHEELS_T[i], float)
    qx, qy = QUAD[i]
    goal = np.array([SHEET_C[0] + qx * PATCH[0] / 2, SHEET_C[1] + qy * PATCH[1] / 2])
    order = {2: 0, 3: 1, 0: 2, 1: 3}[i]
    t0 = T_ALL4 - 0.25 + 0.17 * order
    u = float(np.clip((t - t0) / 0.75, 0, 1))
    e = 1 - (1 - u) ** 4
    return home + (goal - home) * e


def top_canvas(t, shutter):
    z, c = top_cam(t)
    out = np.zeros((H, W), np.float32)
    # faint grid floor (helps the zoom read as motion)
    g = 50.0
    gx0, gx1 = c[0] - W / 2 / z, c[0] + W / 2 / z
    gy0, gy1 = c[1] - CY_T / z, c[1] + (H - CY_T) / z
    step = g * 2 ** round(math.log2(max(1e-3, 60 / (g * z))))
    for xv in np.arange(math.floor(gx0 / step) * step, gx1 + step, step):
        for yv in np.arange(math.floor(gy0 / step) * step, gy1 + step, step):
            x, y = to_px((xv, yv), z, c)
            if 0 <= x < W and 0 <= y < H:
                cv2.circle(out, (int(x * 16), int(y * 16)), 2 * 16, 0.28, -1, cv2.LINE_AA, shift=4)
    carf = 1 - sstep(T_ALL4 - 0.3, T_ALL4 + 0.6, t)
    if carf > 0.01:
        lay = np.zeros((H, W), np.float32)
        th = max(2.0, 1.4 * z)
        poly_px(lay, CAR_BODY, z, c, 0.18, 0, fill=True)
        poly_px(lay, CAR_BODY, z, c, 0.95, th)
        poly_px(lay, CABIN, z, c, 0.75, th * 0.8)
        poly_px(lay, HOOD, z, c, 0.45, th * 0.6, closed=False)
        poly_px(lay, REAR, z, c, 0.45, th * 0.6, closed=False)
        for mr in MIRRORS:
            poly_px(lay, mr, z, c, 0.8, th * 0.8, fill=True)
        for (wx, wy) in WHEELS_T:
            poly_px(lay, rrect_pts(wx, wy, 22.5, 64, 5), z, c, 0.12, 0, fill=True)
            poly_px(lay, rrect_pts(wx, wy, 22.5, 64, 5), z, c, 0.8, th)
        out = np.maximum(out, lay * carf)
    # hand (around the focus patch)
    hv = float(sstep(T_HAND - 0.55, T_HAND + 0.25, t) * (1 - sstep(T_ALL4 - 0.35, T_ALL4 + 0.1, t)))
    # sheet of A4 (landscape) drawn around the 2x2
    sv = sstep(T_SHEET - 0.45, T_SHEET + 0.15, t)
    if sv > 0.01:
        pts = rrect_pts(SHEET_C[0], SHEET_C[1], 29.7 + 1.6, 21.0 + 1.6, 0.6, 2)
        n = len(pts)
        k = max(2, int(n * sv))
        poly_px(out, pts[:k] + ([pts[0]] if sv > 0.98 else []), z, c, 0.95, max(2, 0.32 * z), closed=False)
    # patches (with motion blur along their flight)
    pulse = 1.0 + 0.12 * math.sin(2 * math.pi * 1.6 * t)
    lay = np.zeros((H, W), np.float32)
    K = 6
    for i in range(4):
        for k in range(K):
            p = patch_pos(i, t + shutter * ((k + 0.5) / K - 0.5))
            one = np.zeros((H, W), np.float32)
            poly_px(one, rrect_pts(p[0], p[1], PATCH[0] - 0.5, PATCH[1] - 0.5, 1.2, 3), z, c, 1.0, 0, fill=True)
            lay += one / K
    on = sstep(T_FOUR - 0.6, T_FOUR + 0.6, t)               # (scene starts after the cascade; already lit)
    glow = cv2.GaussianBlur(lay, (0, 0), max(9.0, 0.9 * z))
    # radar pings from each patch as the schematic lands
    pg = float(sstep(CASC[0][0] + 0.5, CASC[0][0] + 1.0, t) * (1 - sstep(T_FOUR + 2.0, T_FOUR + 2.4, t)))
    if pg > 0.01:
        for i in range(4):
            px_, py_ = to_px(patch_pos(i, t), z, c)
            for k in range(2):
                ph = ((t - CASC[0][0]) * 0.9 + 0.5 * k) % 1.0
                r = 14 + 120 * ph
                cv2.circle(out, (int(px_ * 16), int(py_ * 16)), int(r * 16), pg * 0.9 * (1 - ph) ** 1.2, 7, cv2.LINE_AA, shift=4)
    dim = 1 - 0.8 * hv                                 # while the hand is shown the patch becomes an outline
    out = np.maximum(out, np.clip(on * pulse * dim * (0.95 * lay + 0.9 * glow), 0, 1.3))
    if hv > 0.01:
        pf = WHEELS_T[FOCUS]
        poly_px(out, rrect_pts(pf[0], pf[1], PATCH[0], PATCH[1], 1.2, 3), z, c, 0.95 * hv, max(3, 0.3 * z))
        hf, ho, halo = hand_mask(z, c, pf, min(1.0, hv * 1.25))
        hand = np.clip(hf - 0.9 * ho, 0, 1)            # filled silhouette, dark edge separates fingers
        out = out * (1 - 0.9 * np.clip(hf + ho, 0, 1) * hv) + hv * 0.95 * hand
    return out


# ---------------------------------------------------------------- ASCII state per scene
class Scene:
    def __init__(self, name):
        self.name, self.m, self.last = name, AC.Matcher(), -999

    def canvas(self, t):
        if self.name == 'side':
            return side_canvas(t, side_cam(t))
        return top_canvas(t, 0.5 / FPS)

    def step(self, i):
        t = i / FPS
        acc = np.zeros((H, W), np.float32)
        for k in range(SUB):
            acc += self.canvas(t + (k - (SUB - 1) / 2) / (FPS * SUB))
        prevP = None if self.m.P is None else self.m.P.copy()
        ch = self.m.step(acc / SUB)
        lit = (self.m.gid > 0) | ch
        self.m.last_change = float(ch[lit].mean()) if lit.any() else 0.0
        self.m.flicker = None
        if prevP is not None:
            still = np.abs(self.m.P - prevP).mean(2) < 0.01
            self.m.flicker = float((ch & still)[lit].mean()) if lit.any() else 0.0
        self.last = i

    def image(self, i):
        if self.last not in (i - 1, i):
            for j in range(i - 10, i):
                self.step(j % N if j >= 0 else j + N)
                self.last = j
        if self.last != i:
            self.step(i)
        img = np.zeros((H, W), np.float32)
        P = np.clip(self.m.P.mean(2), 0, 1)
        img[AC.Y0:AC.Y0 + AC.ROWS * AC.CH, :AC.COLS * AC.CW] = AC.plane_of(self.m.gid, 0.62 + 0.45 * np.sqrt(P))
        return img


# ---------------------------------------------------------------- waterfall cascade (decompose -> reassemble), tiles kept 1:1
R_, C_ = AC.ROWS, AC.COLS
_cc = np.arange(C_)
_JIT = 0.5 + 0.25 * np.sin(0.37 * _cc + 1.3) + 0.25 * np.sin(1.71 * _cc)
TRAV, CSUB = 0.40, 4


def tiles(img):
    return img[AC.Y0:AC.Y0 + R_ * AC.CH, :C_ * AC.CW].reshape(R_, AC.CH, C_, AC.CW).transpose(0, 2, 1, 3)


def offsets(t, T, D):
    rr = np.arange(R_)[:, None] / R_
    lag = 0.16 * D * _JIT[None, :] + 0.14 * D * (1 - rr)
    uo = np.clip((t - T - lag) / (TRAV * D), 0, 1)
    ui = np.clip((t - T - 0.30 * D - lag) / (TRAV * D), 0, 1)
    fall = 1.12 * H
    return fall * uo ** 2.4, -fall * (1 - ui) ** 2.4


def scatter(out, tl, dy):
    live = tl.max((2, 3)) > 0.02
    r, c = np.nonzero(live)
    y0 = AC.Y0 + r * AC.CH + np.round(dy[r, c]).astype(int)
    ok = (y0 > -AC.CH) & (y0 < H)
    r, c, y0 = r[ok], c[ok], y0[ok]
    yy = y0[:, None, None] + np.arange(AC.CH)[None, :, None]
    xx = (c * AC.CW)[:, None, None] + np.arange(AC.CW)[None, None, :]
    yy, xx = np.broadcast_arrays(yy, xx)
    vals = tl[r, c]
    m = (yy >= 0) & (yy < H)
    np.maximum.at(out, (yy[m], xx[m]), vals[m])


def cascade(img_a, img_b, t, T, D):
    ta, tb = tiles(img_a), tiles(img_b)
    acc = np.zeros((H, W), np.float32)
    for k in range(CSUB):
        do, di = offsets(t + (k - (CSUB - 1) / 2) / (FPS * CSUB), T, D)
        out = np.zeros((H, W), np.float32)
        scatter(out, ta, do)
        scatter(out, tb, di)
        acc += out
    return acc / CSUB


# ---------------------------------------------------------------- crisp typed captions (inside 12-62 % height, left 85 %)
F_BIG = ImageFont.truetype(RD.FONT, 92)
F_MID = ImageFont.truetype(RD.FONT, 64)
F_SM = ImageFont.truetype(RD.FONT_THIN, 52)
CX = 64
TYPE = 34.0                                               # chars / s


def captions(t):
    """list of (text, font, x, y, t_start, t_end, emphasis)"""
    L = []
    e1 = CASC[0][0] + 0.1
    L.append(('everything a car does', F_SM, CX, 300, 0.05, e1, 0.75))
    for k, (w, T) in enumerate((('speeding up', T_SPEED), ('braking', T_BRAKE), ('turning', T_TURN))):
        L.append(('> ' + w, F_BIG, CX, 380 + 112 * k, T - 0.12, e1, 1.0))
    L.append(('= 4 patches of rubber', F_MID, CX, 760, T_FOUR - 0.1, e1, 1.0))
    e2 = CASC[1][0] + 0.1
    L.append(('1 patch', F_BIG, CX, 300, CASC[0][0] + 0.6, T_ALL4 - 0.3, 1.0))
    L.append(('= size of a hand', F_MID, CX, 410, T_HAND - 0.25, T_ALL4 - 0.3, 1.0))
    L.append(('all 4 patches', F_BIG, CX, 300, T_ALL4 - 0.15, e2, 1.0))
    L.append(('= 1 sheet of A4 paper', F_MID, CX, 410, T_SHEET - 0.2, e2, 1.0))
    e3 = T_AND - 0.1
    L.append(('100 km/h', F_BIG, CX, 300, T_HUND - 0.25, e3, 1.0))
    L.append(('each tyre spins', F_SM, CX, 430, T_HUND + 1.4, e3, 0.75))
    L.append(('14 times a second', F_MID, CX, 500, T_14 - 0.1, e3, 1.0))
    L.append(("that's all that holds", F_MID, CX, 330, T_AND + 0.25, DUR - 0.45, 1.0))
    L.append(('you to the road.', F_MID, CX, 420, T_AND + 1.0, DUR - 0.45, 1.0))
    return L


def count_text(txt, t, t0):
    """numbers roll up while typing in (100 km/h, 14)."""
    if txt.startswith('100 km/h'):
        v = int(round(100 * sstep(t0, t0 + 0.75, t)))
        return f'{v} km/h'
    if txt.startswith('14 times'):
        v = int(round(14 * sstep(t0, t0 + 0.8, t)))
        return f'{v} times a second'
    return txt


def draw_captions(img, t):
    boxes = []
    pil = Image.new('L', (W, H), 0)
    d = ImageDraw.Draw(pil)
    for txt, f, x, y, t0, t1, em in captions(t):
        if not (t0 <= t < t1):
            continue
        full = count_text(txt, t, t0)
        n = len(full) if txt.startswith(('100', '14 ')) else int(min(len(full), (t - t0) * TYPE))
        a = em * float(sstep(t0, t0 + 0.08, t) * (1 - sstep(t1 - 0.22, t1, t)))
        s = full[:n]
        if s:
            d.text((x, y), s, font=f, fill=int(255 * a))
            bb = d.textbbox((x, y), full, font=f)
            boxes.append(bb)
        if n < len(full) or (t - t0) < 0.6:                      # block cursor while typing
            cx = x + d.textlength(s, font=f) + 4
            asc, desc = f.getmetrics()
            if int(t * 4) % 2 == 0 or n < len(full):
                d.rectangle([cx, y + 0.18 * asc, cx + 0.5 * f.size, y + asc + 0.1 * desc], fill=int(200 * a))
    return np.maximum(img, np.asarray(pil, np.float32) / 255), boxes


# ---------------------------------------------------------------- post: bloom, scanlines, vignette
def post(img):
    small = cv2.resize(img, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
    bloom = cv2.resize(0.40 * cv2.GaussianBlur(small, (0, 0), 2.0) + 0.30 * cv2.GaussianBlur(small, (0, 0), 9.0),
                       (W, H), interpolation=cv2.INTER_LINEAR)
    out = (img + bloom)[..., None] * RD.SCAN * RD.VIG
    return np.repeat((np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8), 3, 2)


def frames(indices, want):
    S = {'side': Scene('side'), 'top': Scene('top')}
    for i in indices:
        t = i / FPS
        sc, k = scene_at(t)
        if i not in want:
            continue
        if k is None:
            img = S[sc].image(i)
            m = S[sc].m
        else:
            T, D, a, b = CASC[k]
            img = cascade(S[a].image(i), S[b].image(i), t, T, D)
            m = None
        img, boxes = draw_captions(img, t)
        yield i, post(img), dict(i=int(i), t=round(t, 4), scene=sc or f'{CASC[k][2]}->{CASC[k][3]}',
                                 boxes=[list(map(float, b)) for b in boxes],
                                 glyph_change=None if m is None else m.last_change,
                                 flicker=None if m is None else m.flicker)


def main():
    mode = sys.argv[1]
    if mode == 'still':
        out = Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
        for stamp in sys.argv[3:]:
            fi = int(round(float(stamp) * FPS)) % N
            for _, rgb, _ in frames(range(fi, fi + 1), {fi}):
                Image.fromarray(rgb).save(out / f'f_{stamp}.png')
        return
    dst = Path(sys.argv[2]).resolve(); dst.parent.mkdir(parents=True, exist_ok=True)
    ff = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS),
                           '-i', '-', '-c:v', 'libx264', '-preset', 'slow', '-crf', '15', '-maxrate', '14M', '-bufsize', '28M',
                           '-pix_fmt', 'yuv420p', '-g', '60', str(dst)], stdin=subprocess.PIPE)
    metas, t0 = [], time.time()
    for i, rgb, meta in frames(range(N), set(range(N))):
        ff.stdin.write(rgb.tobytes()); metas.append(meta)
        if i % 60 == 0:
            print(f'frame {i}/{N} {time.time() - t0:.0f}s', flush=True)
    ff.stdin.close(); assert ff.wait() == 0
    json.dump(metas, open(dst.with_suffix('.frames.json'), 'w'))
    print('wrote', dst, f'{time.time() - t0:.0f}s')


if __name__ == '__main__':
    main()
