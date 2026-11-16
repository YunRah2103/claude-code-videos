"""same-v8: Urus vs RS Q8 ASCII explainer, 1080x1920 @30 fps, 18 s loop.

Reuses the approved ASCII pipeline unchanged (videos/ascii-terminal-test/src/ascii_car.py: glyph atlas,
EMA 0.6 + hysteresis Matcher, plane_of; render.py: fonts, scanlines, vignette) and the heartbeat-v8
structure (waterfall cascade, typed code cards with leader lines, V8 drawing, post).
Cars: side views cropped from assets/sheet_src.png (user's reference sheet), same scale, same slots.
python render.py still OUTDIR 0 9 16   |   python render.py video OUT_silent.mp4
"""
import json
import math
import subprocess
import sys
import time
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'videos/ascii-terminal-test/src'))
import ascii_car as AC            # noqa: E402  (approved ASCII art pipeline, reused as-is)
import render as RD               # noqa: E402  (fonts, scanline/vignette maps)

DUR = 18.0
W, H, FPS, SUB = 1080, 1920, 30, 4
N = int(round(DUR * FPS))
VO_TRIM = 0.25                    # leading silence cut from the VO (audio.py trims the same)
WORDS = json.load(open(Path(__file__).with_name('words.json')))


def wt(word, k=0):
    """start time (video clock) of the k-th occurrence of a spoken word"""
    return [w['s'] for w in WORDS if w['w'] == word][k] - VO_TRIM


def wend(word, k=0):
    return [w['e'] for w in WORDS if w['w'] == word][k] - VO_TRIM


def sstep(a, b, x):
    u = min(max((x - a) / (b - a), 0.0), 1.0)
    return u * u * u * (u * (6 * u - 15) + 10)


def eout(u):
    u = min(max(u, 0.0), 1.0)
    return 1 - (1 - u) ** 3


# ---------------------------------------------------------------- timeline (anchored to word timings)
LAND_U = wt('thirty') + 0.10                   # Urus price lands
LAND_Q = wt('one', 2) + 0.08                   # RS Q8 price lands ("twenty-ONE thousand")
FOCUS_Q = wt('other', 0) - 0.15                # highlight moves to the RS Q8
JUMP1 = (wt('covers'), wt('fit') + 0.05)       # cover jumps Urus -> RS Q8
JUMP2 = (wt('other', 1) - 0.05, wt('other', 1) + 0.45)   # ...and back
LAND_GAP = wt('money') + 0.12
T_BADGE, T_HP, T_TUNE = wt('badge') - 0.05, wt('power') - 0.15, wt('tuning') - 0.10
HUSH = (wend('tuning') + 0.02, wt('would') - 0.02)      # near-silence before the final question
CASC = [  # (start, duration, from_scene, to_scene)
    (wt('same', 0) - 0.42, 0.50, 0, 1),       # -> two V8s
    (wt('same', 1) - 0.10, 0.48, 1, 2),       # -> platform / drivetrain
    (wt('one', 0) + 0.10, 0.50, 2, 3),        # -> prices
    (wend('dollars', 1) - 0.20, 0.55, 3, 4),  # -> engine covers
    (wend('other', 1) + 0.12, 0.55, 4, 5),    # -> the gap (pause before "So what's...")
    (wt('the', 3) - 0.30, 0.48, 5, 6),        # -> DIFFERENT
    (wend('tuning') - 0.05, 0.45, 6, 7),      # -> poll
    (DUR - 0.50, 0.50, 7, 0),                 # -> loop
]


def scene_at(t):
    for k, (T, D, a, b) in enumerate(CASC):
        if T <= t < T + D:
            return None, k
    cur = 0
    for T, D, a, b in CASC:
        if t >= T + D:
            cur = b
    if t >= CASC[-1][0] + CASC[-1][1]:
        cur = 0
    return cur, None


def scene_span(sc):
    ins = [T for T, D, a, b in CASC if b == sc]
    outs = [T + D for T, D, a, b in CASC if a == sc]
    return (ins[0] if sc else CASC[-1][0] - DUR), outs[0]


# ---------------------------------------------------------------- drawing helpers (float luminance canvases)
FB = '/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-ExtraBold.ttf'
F_DIG = ImageFont.truetype(FB, 150)
F_DIG_G = ImageFont.truetype(FB, 140)
F_CODE = ImageFont.truetype(RD.FONT, 50)
F_TAG = ImageFont.truetype(RD.FONT_THIN, 50)
SH16 = 16


def P(p):
    return (int(round(p[0] * SH16)), int(round(p[1] * SH16)))


def line(img, a, b, v, th):
    cv2.line(img, P(a), P(b), float(v), th, cv2.LINE_AA, 4)


def circle(img, c, r, v, th):
    cv2.circle(img, P(c), int(r * SH16), float(v), th, cv2.LINE_AA, 4)


def poly(img, pts, v):
    cv2.fillPoly(img, [np.round(np.array(pts) * SH16).astype(np.int32)], float(v), cv2.LINE_AA, 4)


def rrect(img, center, u, v, hl, hw, val):
    c = np.array(center); u = np.array(u); v = np.array(v)
    poly(img, [c + u * hl + v * hw, c + u * hl - v * hw, c - u * hl - v * hw, c - u * hl + v * hw], val)


def box(img, x0, y0, x1, y1, v, th):
    for a, b in (((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))):
        line(img, a, b, v, th)


def digits(img, text, x0, cy, font, val=1.0):
    """big digits drawn into the luminance canvas (the ASCII matcher turns them into glyph art)"""
    tw = int(font.getlength(text)) + 20
    im = Image.new('L', (tw, font.size + 60), 0)
    ImageDraw.Draw(im).text((10, 10), text, font=font, fill=255)
    a = np.asarray(im, np.float32) / 255 * val
    y0 = int(cy - a.shape[0] / 2)
    img[y0:y0 + a.shape[0], x0:x0 + tw] = np.maximum(img[y0:y0 + a.shape[0], x0:x0 + tw], a[:, :W - x0])
    return x0 + tw


# ---------------------------------------------------------------- the two cars (user's sheet, right-facing side views)
SHEET = cv2.imread(str(Path(__file__).resolve().parents[1] / 'assets/sheet_src.png'), cv2.IMREAD_GRAYSCALE)
CX0S, CX1S = 1055, 1530                       # common crop width (sheet px) -> same scale for both cars
ABOVE, BELOW = 130, 44                        # crop rows above / below the wheel centre line
SC = 880 / (CX1S - CX0S)                      # sheet px -> screen px (1.853)
CXS = 20                                      # screen x of the crop's left edge (car ends before x=900)
SLOT_TOP = {'urus': 812, 'rsq8': 1182}       # both cars inside 12..80% height and the left 85% width
WHEEL_Y_SHEET = {'urus': 226.0, 'rsq8': 730.5}
WHEEL_X_SHEET = (1150.5, 1438.0)
WR = 39 * SC                                  # wheel radius on screen (72 px)
GX, GY = AC.GX, AC.GY


def _car(name):
    wy = WHEEL_Y_SHEET[name]
    crop = SHEET[int(wy - ABOVE):int(wy + BELOW), CX0S:CX1S].astype(np.float32) / 255
    hh = int(round(crop.shape[0] * SC))
    g = cv2.resize(crop, (880, hh), interpolation=cv2.INTER_CUBIC)
    m = (cv2.GaussianBlur(g, (0, 0), 2.5) > 0.075).astype(np.float32)
    m[int((ABOVE + 40) * SC):] = 0                                   # drop the floor reflection under the tyres
    n, lab, st, _ = cv2.connectedComponentsWithStats(m.astype(np.uint8))
    m = (lab == 1 + np.argmax(st[1:, cv2.CC_STAT_AREA])).astype(np.float32)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    wheels_l = [((x - CX0S) * SC, ABOVE * SC) for x in WHEEL_X_SHEET]
    yy, xx = np.mgrid[0:hh, 0:880]
    for cx, cy in wheels_l:                                          # wheels are dark: keep them in the mask
        m = np.maximum(m, (np.hypot(xx - cx, yy - cy) < WR + 2).astype(np.float32))
    # tone map: body to mid-grey, local detail (panel lines, glass, intakes, spokes) carries the drawing
    l = g / max(float(np.median(g[m > 0])), 1e-3)
    l = np.clip(l, 0, 3.0)
    base = cv2.GaussianBlur(l, (0, 0), 10)
    det = cv2.GaussianBlur(l, (0, 0), 1.0) - cv2.GaussianBlur(l, (0, 0), 3.0)
    gx, gy = cv2.Sobel(cv2.GaussianBlur(l, (0, 0), 1.2), cv2.CV_32F, 1, 0), cv2.Sobel(cv2.GaussianBlur(l, (0, 0), 1.2), cv2.CV_32F, 0, 1)
    edge = np.clip(np.hypot(gx, gy) / 1.6, 0, 1)
    s = np.clip(0.04 + 0.12 * np.clip(base, 0, 1.6) + 1.1 * np.clip(det - 0.03, 0, None) + 0.9 * edge ** 1.5, 0, 1) ** 1.4 * 0.62
    for cx, cy in wheels_l:                                          # rims: stretch contrast inside the wheel
        d = np.hypot(xx - cx, yy - cy)
        rim = np.clip(g / np.percentile(g[d < WR], 97), 0, 1) ** 0.8
        s = np.where(d < WR + 9, 0.0, s)                            # wheel drawn procedurally (spins cleanly), dark arch gap
        s = np.where((d > WR + 9) & (d < WR + 14) & (yy < cy + 10), 0.5, s)   # wheel-arch lip
    k = np.ones((5, 5), np.uint8)
    ol = cv2.dilate(m, k) - cv2.erode(m, k)                          # silhouette outline (same recipe as the E92 side view)
    s = np.clip(np.maximum(s * m, 0.95 * cv2.GaussianBlur(ol, (0, 0), 1.0)), 0, 1)
    big = np.zeros((H, W), np.float32)
    bm = np.zeros((H, W), np.float32)
    y0 = SLOT_TOP[name]
    big[y0:y0 + hh, CXS:CXS + 880] = s
    bm[y0:y0 + hh, CXS:CXS + 880] = m
    wheels = [(CXS + (x - CX0S) * SC, y0 + ABOVE * SC) for x in WHEEL_X_SHEET]
    return big, bm, wheels


CARS = {k: _car(k) for k in ('urus', 'rsq8')}
FLOOR = {k: SLOT_TOP[k] + (ABOVE * SC) + WR + 4 for k in CARS}
ROT = 6                                       # wheel turns per loop -> seamless spin + floor scroll
V_ROLL = ROT * 2 * math.pi * WR / DUR         # px/s
DOT_SP = V_ROLL * DUR / 44                    # floor dot spacing (44 per loop)


def pt(name, sx, sy_from_wheel):
    """screen point on a car: sheet x, sheet y offset from the wheel line"""
    return np.array([CXS + (sx - CX0S) * SC, SLOT_TOP[name] + (ABOVE + sy_from_wheel) * SC])


ENG = {k: pt(k, 1415, -42) for k in CARS}     # under the bonnet, behind the front wheel arch
BADGE = {k: pt(k, 1492, -20) for k in CARS}   # nose
BODY = {k: pt(k, 1290, -55) for k in CARS}    # door


def car_lum(name, t, gain=1.0, sweep=None):
    img, m, wheels = CARS[name]
    out = img * gain
    a = V_ROLL * t / WR                                              # rolling to the right: clockwise on screen
    for cx, cy in wheels:
        circle(out, (cx, cy), WR - 7, 0.16 * gain, 12)               # tyre
        circle(out, (cx, cy), WR - 1, 0.55 * gain, 3)                # tyre outline
        circle(out, (cx, cy), WR - 18, 0.55 * gain, 4)               # rim lip
        for k in range(5):                                           # 5 spokes
            ang = a + k * 2 * math.pi / 5
            d = np.array([math.cos(ang), math.sin(ang)])
            line(out, (cx + d[0] * 12, cy + d[1] * 12), (cx + d[0] * (WR - 20), cy + d[1] * (WR - 20)), 0.6 * gain, 9)
        circle(out, (cx, cy), 12, 0.5 * gain, -1)                    # hub
    if sweep is not None and 0 < sweep < 1:                          # light sweep across the body
        pos = -200 + 1300 * sweep
        band = np.exp(-(((GX - pos) + 0.5 * (GY - SLOT_TOP[name])) / 60) ** 2)
        out = out + 0.5 * band * m * gain
    # perspective floor dots under the car, scrolling left (car drives right)
    fy = FLOOR[name]
    for r, (dy, rad, al) in enumerate(((0, 3.0, 0.75), (16, 3.6, 0.5), (36, 4.4, 0.32))):
        sp = DOT_SP * (1 + 0.35 * r)
        off = (V_ROLL * (1 + 0.35 * r) * t) % sp
        x = 30 - off + sp
        while x < 900:
            circle(out, (x, fy + dy), rad, al * gain, -1)
            x += sp
    return out


def sweep_at(t, t0, d=1.6):
    return (t - t0) / d


# ---------------------------------------------------------------- V8 (from heartbeat-v8)
FIRE_ORDER = [0, 1.5, 3, 0.5, 2, 3.5, 1, 2.5]


def theta(t):
    return 2 * math.pi * 3.0 * t


def v8(img, th, cx, scale=1.0, val=1.0):
    cx = np.array(cx, float)
    for side, sgn in ((0, -1), (1, 1)):
        u = np.array([sgn * 0.7071, -0.7071])
        v = np.array([0.7071, sgn * 0.7071])
        for i in range(4):
            k = side * 4 + i
            ti = th + FIRE_ORDER[k] * math.pi / 2
            base = cx + u * 150 * scale + v * (i - 1.5) * 76 * scale
            top = base + u * 280 * scale
            for sgn2 in (-1, 1):
                line(img, base + v * 36 * scale * sgn2, top + v * 36 * scale * sgn2, 0.85 * val, 4)
            line(img, top - v * 36 * scale, top + v * 36 * scale, 0.85 * val, 4)
            s = (95 + 115 * (1 + math.cos(ti)) / 2) * scale
            pc = base + u * (s + 28 * scale)
            rrect(img, pc, u, v, 28 * scale, 31 * scale, 0.62 * val)
            line(img, pc - u * 10 * scale, cx + 62 * scale * np.array([math.cos(th), math.sin(th)]), 0.55 * val, 3)
            f = math.exp(-((ti % (4 * math.pi)) / 0.55))
            if f > 0.05:
                for a in range(8):
                    d = np.array([math.cos(a * math.pi / 4), math.sin(a * math.pi / 4)])
                    line(img, top - u * 20 * scale, top - u * 20 * scale + d * 46 * f * scale, f * val, 4)
    circle(img, cx, 95 * scale, 0.8 * val, 4)
    circle(img, cx + 62 * scale * np.array([math.cos(th), math.sin(th)]), 16 * scale, val, -1)


def v8_pos(t):
    """the two V8s start in their engine bays and slide together into one (overlap) between the cars"""
    a, b = scene_span(1)
    u = sstep(a + 0.15, wend('eight') + 0.05, t)
    mid = (ENG['urus'] + ENG['rsq8']) / 2 + np.array([-250, 0])
    return ENG['urus'] + (mid - ENG['urus']) * u, ENG['rsq8'] + (mid - ENG['rsq8']) * u, u


# ---------------------------------------------------------------- prices
P_U, P_Q = 229_495, 121_096


def count(t, t_land, val, t0=0.0):
    return int(round(val * eout((t - t0) / (t_land - t0)) ** 1.0)) if t < t_land else val


def price_txt(v):
    return f'${v:,}'.rjust(8)


PRICE_Y = {'urus': 585, 'rsq8': 735}


# ---------------------------------------------------------------- scene canvases
def canvas0(t):                               # hook: both cars, prices ticking up
    img = np.maximum(car_lum('urus', t, 1.0, sweep_at(t % DUR, 0.05)), car_lum('rsq8', t, 1.0, sweep_at(t % DUR, 0.35)))
    tau = t - DUR if t > DUR / 2 else t                              # unwrapped: ticks straight through the loop seam
    digits(img, price_txt(count(tau, LAND_U, P_U, CASC[-1][0] - DUR)), 40, PRICE_Y['urus'], F_DIG)
    digits(img, price_txt(count(tau, LAND_Q, P_Q, CASC[-1][0] - DUR)), 40, PRICE_Y['rsq8'], F_DIG)
    return img


def canvas1(t):                               # two V8s overlapping into one
    img = np.maximum(car_lum('urus', t, 0.16), car_lum('rsq8', t, 0.16))
    pa, pb, u = v8_pos(t)
    sc = 0.36 + 0.18 * u
    for k in range(3):                                               # piston blur
        tmp = np.zeros((H, W), np.float32)
        th = theta(t + k / (FPS * SUB * 3))
        v8(tmp, th, pa, sc, 1.0)
        v8(tmp, th, pb, sc, 0.8 if u < 0.98 else 1.0)
        acc = tmp / 3 if k == 0 else acc + tmp / 3
    img = np.maximum(img, acc)
    g = t - (wend('eight') + 0.05)
    if 0 < g < 0.6:                                                  # match flash ring when they lock together
        circle(img, pa, 140 + 420 * g, max(0.0, 1 - g / 0.6), 6)
    return img


def chassis(img, name, t, val):
    (rx, ry), (fx, fy) = CARS[name][2]
    for cx, cy in ((rx, ry), (fx, fy)):
        circle(img, (cx, cy), WR + 6, val, 4)
        line(img, (cx, cy - 30), (cx, cy + 30), val * 0.7, 3)        # axle stub
    line(img, (rx + 70, ry - 18), (fx - 70, fy - 18), val, 5)        # floor rails (MLB Evo)
    line(img, (rx + 70, ry + 6), (fx - 70, fy + 6), val * 0.8, 3)
    for x in np.linspace(rx + 110, fx - 110, 5):
        line(img, (x, ry - 18), (x, ry + 6), val * 0.6, 3)
    e = ENG[name]
    box(img, e[0] - 70, e[1] - 34, e[0] + 70, e[1] + 34, val, 4)     # V8 block
    gb = (e[0] - 140, e[1] + 20)
    box(img, gb[0] - 50, gb[1] - 18, gb[0] + 50, gb[1] + 18, val * 0.9, 3)
    ph = (t * 6) % 1.0                                               # torque pulses to BOTH axles (AWD)
    line(img, (gb[0] - 50, gb[1]), (rx, ry), val * 0.9, 4)
    line(img, (gb[0] + 50, gb[1]), (fx, fy), val * 0.9, 4)
    for s in (ph, (ph + 0.5) % 1):
        circle(img, (gb[0] - 50 + (rx - gb[0] + 50) * s, gb[1] + (ry - gb[1]) * s), 8, val, -1)
        circle(img, (gb[0] + 50 + (fx - gb[0] - 50) * s, gb[1] + (fy - gb[1]) * s), 8, val, -1)


def canvas2(t):                               # shared platform + drivetrain, x-ray
    img = np.maximum(car_lum('urus', t, 0.28), car_lum('rsq8', t, 0.28))
    a, b = scene_span(2)
    for k, name in enumerate(('urus', 'rsq8')):
        chassis(img, name, t, 0.95)
    y = 800 + 730 * ((t - a) / 1.2 % 1.0)                            # scan beam sweeping both
    img[int(y) - 3:int(y) + 3, 20:900] = np.maximum(img[int(y) - 3:int(y) + 3, 20:900], 0.8)
    return img


def canvas3(t):                               # prices land: Urus, then RS Q8
    fq = sstep(FOCUS_Q - 0.1, FOCUS_Q + 0.25, t)
    img = np.maximum(car_lum('urus', t, 1.0 - 0.55 * fq, sweep_at(t, LAND_U - 0.2)),
                     car_lum('rsq8', t, 0.45 + 0.55 * fq, sweep_at(t, LAND_Q - 0.2)))
    digits(img, price_txt(count(t, LAND_U, P_U, CASC[-1][0] - DUR)), 40, PRICE_Y['urus'], F_DIG, 1.0 - 0.45 * fq)
    digits(img, price_txt(count(t, LAND_Q, P_Q, CASC[-1][0] - DUR)), 40, PRICE_Y['rsq8'], F_DIG, 0.55 + 0.45 * fq)
    for tl, name in ((LAND_U, 'urus'), (LAND_Q, 'rsq8')):
        g = t - tl
        if 0 < g < 0.55:
            circle(img, (450, PRICE_Y[name]), 120 + 520 * g, max(0.0, 1 - g / 0.55), 6)
    return img


def cover(img, c, val, tilt=0.0):
    c = np.array(c, float)
    u = np.array([math.cos(tilt), math.sin(tilt)])
    v = np.array([-u[1], u[0]])
    rrect(img, c, u, v, 105, 34, 0.22 * val)
    for k in range(-4, 5):                                           # ribs
        line(img, c + u * k * 20 - v * 24, c + u * k * 20 + v * 24, val, 3)
    for s in (-1, 1):
        line(img, c - u * 108 + v * 36 * s, c + u * 108 + v * 36 * s, val, 4)


def cover_pos(t):
    a, b = ENG['urus'] + np.array([0, -60]), ENG['rsq8'] + np.array([0, -60])

    def arc(p, q, u):
        m = (p + q) / 2 + np.array([-330, 0])
        return (1 - u) ** 2 * p + 2 * u * (1 - u) * m + u ** 2 * q

    u1 = sstep(*JUMP1, t)
    if t < JUMP2[0]:
        return arc(a, b, u1), math.sin(math.pi * u1) * 0.9
    u2 = sstep(*JUMP2, t)
    return arc(b, a, u2), -math.sin(math.pi * u2) * 0.9


def canvas4(t):                               # engine covers reportedly swap
    img = np.maximum(car_lum('urus', t, 0.42), car_lum('rsq8', t, 0.42))
    for name in CARS:
        v8(img, theta(t), ENG[name] + np.array([0, 10]), 0.22, 0.9)
    p, tilt = cover_pos(t)
    for k in range(1, 4):                                            # motion trail
        q, tl = cover_pos(t - 0.035 * k)
        cover(img, q, 0.35 / k, tl)
    cover(img, p, 1.0, tilt)
    for tl, name in ((JUMP1[1], 'rsq8'), (JUMP2[1], 'urus')):
        g = t - tl
        if 0 < g < 0.45:
            circle(img, ENG[name] + np.array([0, -60]), 90 + 380 * g, max(0.0, 1 - g / 0.45), 5)
    return img


GAP = P_U - P_Q                               # 108,399 (shown as "about 108k")
BAR_X0, BAR_W = 40, 840


def canvas5(t):                               # the gap
    a, b = scene_span(5)
    img = np.maximum(car_lum('urus', t, 0.9, sweep_at(t, a + 0.2)), car_lum('rsq8', t, 0.6))
    v = count(t, LAND_GAP, GAP, a + 0.2)
    digits(img, f'+${v:,}', 40, 610, F_DIG_G)
    u = sstep(a + 0.1, a + 0.7, t)
    yu, yq = 708, 760                                                # price bars, to scale
    wu, wq = BAR_W * u, BAR_W * P_Q / P_U * u
    img[yu:yu + 34, BAR_X0:BAR_X0 + int(wu)] = np.maximum(img[yu:yu + 34, BAR_X0:BAR_X0 + int(wu)], 0.9)
    img[yq:yq + 34, BAR_X0:BAR_X0 + int(wq)] = np.maximum(img[yq:yq + 34, BAR_X0:BAR_X0 + int(wq)], 0.55)
    if u > 0.99:                                                     # the extra part blinks
        x0 = BAR_X0 + int(BAR_W * P_Q / P_U)
        f = 0.5 + 0.5 * math.cos(2 * math.pi * 3 * (t - a))
        box(img, x0, yu - 8, BAR_X0 + BAR_W, yq + 42, 0.5 + 0.5 * f, 4)
    g = t - LAND_GAP
    if 0 < g < 0.55:
        circle(img, (470, 610), 150 + 520 * g, max(0.0, 1 - g / 0.55), 6)
    return img


def canvas6(t):                               # DIFFERENT: badge, power, tune
    img = np.maximum(car_lum('urus', t, 1.0), car_lum('rsq8', t, 0.4))
    for tt, c, r in ((T_BADGE, BADGE['urus'], 36), (T_HP, ENG['urus'], 80), (T_TUNE, CARS['urus'][2][1], WR + 18)):
        u = sstep(tt, tt + 0.25, t)
        if u > 0:
            ring = r * (1.6 - 0.6 * u)
            circle(img, c, ring, u, 5)
            for k in range(12):                                      # rotating ticks
                ang = t * 2.2 + k * math.pi / 6
                d = np.array([math.cos(ang), math.sin(ang)])
                line(img, c + d * (ring + 8), c + d * (ring + 22), u * 0.8, 3)
    return img


def canvas7(t):                               # poll
    a, b = scene_span(7)
    img = np.maximum(car_lum('urus', t, 1.0, sweep_at(t, a + 0.1, 1.3)), car_lum('rsq8', t, 1.0, sweep_at(t, a + 0.1, 1.3)))
    q = 1 + 0.06 * math.sin(2 * math.pi * 1.5 * (t - a))
    f = ImageFont.truetype(FB, int(200 * q))
    digits(img, '?', 760, 650, f)
    return img


CANVAS = [canvas0, canvas1, canvas2, canvas3, canvas4, canvas5, canvas6, canvas7]

# ---------------------------------------------------------------- code cards (crisp terminal text; tag + <=28 chars per line)
CODE = [
    ('py', ['urus = 229_495  # USD, about', 'rsq8 = 121_096  # USD, about'], []),
    ('c++', ['auto urus = "4.0 TT V8";', 'auto rsq8 = "4.0 TT V8";', 'puts(!strcmp(urus, rsq8)', '  ? "engine SAME" : "DIFF");'],
     ['engine SAME']),
    ('py', ['same = ["MLB Evo", "AWD",', '        "4.0 TT V8"]', 'for p in same:', '    print(p, "SAME")'],
     ['MLB Evo SAME', 'AWD SAME', '4.0 TT V8 SAME']),
    ('py', ['urus = 229_495  # USD, about', 'rsq8 = 121_096  # USD, about'], []),
    ('c++', ['// engine cover: reportedly', 'Cover c = urus.cover();', 'rsq8.fit(c);  // fits'], ['cover fits']),
    ('py', ['print(urus - rsq8)', '# about 108k'], ['108399']),
    ('c++', ['puts("badge DIFFERENT");', 'int hp = 641 - 591; // 50', 'printf("hp +%d\\n", hp);', 'puts("tune  DIFFERENT");'],
     ['badge DIFFERENT', 'hp +50', 'tune  DIFFERENT']),
    ('py', ['pay = input(', '    "Pay $108k extra? ")'], ['Pay $108k extra? ']),
]
CX0, TAGY, L0, LH = 40, 248, 330, 64
CHW = F_CODE.getlength('M')
TYPE_RATE = 125.0


def line_starts(sc):
    """per-line typing start times (None = always complete)"""
    lines = CODE[sc][1]
    if sc == 0:
        return [None] * len(lines)
    if sc == 3:                                                      # same card as the hook, already typed
        return [None] * len(lines)
    if sc == 6:                                                      # each line lands on its spoken word
        return [T_BADGE - 0.25, T_HP - 0.3, T_HP + 0.05, T_TUNE - 0.3]
    T = [T for T, D, a, b in CASC if b == sc][0]
    D = [D for T, D, a, b in CASC if b == sc][0]
    st, out = T + 0.75 * D, []
    for s in lines:
        out.append(st)
        st += len(s) / TYPE_RATE
    return out


def typed_line(sc, i, t):
    st = line_starts(sc)[i]
    n = len(CODE[sc][1][i])
    return n if st is None else int(np.clip((t - st) * TYPE_RATE, 0, n))


def code_done(sc):
    st = line_starts(sc)
    if st[-1] is None:
        return -99.0
    return st[-1] + len(CODE[sc][1][-1]) / TYPE_RATE


def out_times(sc):
    if sc == 6:
        return [T_BADGE + 0.05, T_HP + 0.35, T_TUNE + 0.05]
    d = code_done(sc) + 0.08
    return [d + 0.12 * k for k in range(len(CODE[sc][2]))]


def typing_events():
    ev = []
    for sc in range(len(CODE)):
        for i, st in enumerate(line_starts(sc)):
            if st is not None:
                ev += [(st + k / TYPE_RATE, sc) for k in range(len(CODE[sc][1][i]))]
    return ev


def tok_x(sc, i, tok):
    return CX0 + F_CODE.getlength(CODE[sc][1][i][:CODE[sc][1][i].index(tok)]) + F_CODE.getlength(tok) / 2


def leader_targets(sc, t):
    """(line, token, target_xy, start_time): code token -> the part it describes"""
    L = []
    if sc in (0, 3):
        L = [(0, 'urus', BODY['urus'], None), (1, 'rsq8', BODY['rsq8'], None)]
    elif sc == 1:
        pa, pb, _ = v8_pos(t)
        L = [(0, 'urus', pa - (0, 60), None), (1, 'rsq8', pb - (0, 60), None)]
    elif sc == 2:
        (rx, ry), (fx, fy) = CARS['urus'][2]
        L = [(0, 'MLB Evo', ((rx + fx) / 2, ry - 18), None), (0, 'AWD', (fx, fy), None), (1, '4.0 TT V8', ENG['urus'], None)]
    elif sc == 4:
        L = [(1, 'cover', cover_pos(t)[0], None), (2, 'rsq8', ENG['rsq8'] - (0, 30), None)]
    elif sc == 5:
        L = [(0, 'urus', (BAR_X0 + BAR_W - 20, 725), None), (0, 'rsq8', (BAR_X0 + BAR_W * P_Q / P_U - 20, 777), None)]
    elif sc == 6:
        L = [(0, 'badge', BADGE['urus'], T_BADGE), (1, 'hp', ENG['urus'], T_HP), (3, 'tune', CARS['urus'][2][1], T_TUNE)]
    elif sc == 7:
        L = [(1, 'Pay', BODY['urus'], None)]
    return L


SCRAMBLE = '01#%&@$*<>{}'


def code_card(sc, t, img, M=None):
    tag, lines, outs = CODE[sc]
    im = Image.new('L', (W, 860), 0)
    d = ImageDraw.Draw(im)
    tw = d.textlength(tag, font=F_TAG)
    d.rounded_rectangle((CX0 - 14, TAGY - 6, CX0 + tw + 14, TAGY + 64), 12, outline=150, width=3)
    d.text((CX0, TAGY), tag, font=F_TAG, fill=170)
    boxes = [(CX0 - 14, TAGY - 6, CX0 + tw + 14, TAGY + 64)]
    cur = None
    cmt_mark = '#' if tag == 'py' else '//'
    for i, s_full in enumerate(lines):
        y = L0 + i * LH
        boxes.append(d.textbbox((CX0, y), s_full, font=F_CODE))
        n = typed_line(sc, i, t)
        s = s_full[:n]
        if 0 < n < len(s_full) or (n == 0 and line_starts(sc)[i] is not None and t >= line_starts(sc)[i] and cur is None):
            cur = (CX0 + d.textlength(s, font=F_CODE), y)
        if not s:
            continue
        cut = s_full.find(cmt_mark)
        if '"' in s_full[:max(cut, 0)] and s_full[:max(cut, 0)].count('"') % 2:
            cut = -1
        if cut == 0:
            d.text((CX0, y), s, font=F_CODE, fill=140)
        elif cut > 0 and len(s) > cut:
            d.text((CX0, y), s[:cut], font=F_CODE, fill=255)
            d.text((CX0 + d.textlength(s[:cut], font=F_CODE), y), s[cut:], font=F_CODE, fill=140)
        else:
            d.text((CX0, y), s, font=F_CODE, fill=255)
    yo = L0 + len(lines) * LH + 10
    ot = out_times(sc)
    last_out = None
    for k, o in enumerate(outs):
        if t >= ot[k]:
            y = yo + k * LH
            d.text((CX0, y), '> ' + o, font=F_CODE, fill=205)
            boxes.append(d.textbbox((CX0, y), '> ' + o, font=F_CODE))
            last_out = (CX0 + d.textlength('> ' + o, font=F_CODE), y)
    if cur is not None:                                              # typing: scrambled glyph + solid cursor
        d.text(cur, SCRAMBLE[int(t * 40) % len(SCRAMBLE)], font=F_CODE, fill=200)
        d.rectangle((cur[0] + CHW + 4, cur[1] + 6, cur[0] + CHW + 30, cur[1] + 60), fill=230)
    elif (t * 2.2) % 1 < 0.6:                                        # done: blinking cursor (after the last output)
        if last_out is not None:
            cx, cy = last_out[0] + (0 if sc == 7 else 8), last_out[1]
        else:
            cx, cy = CX0 + d.textlength(lines[-1], font=F_CODE) + 8, L0 + (len(lines) - 1) * LH
        d.rectangle((cx, cy + 6, cx + 26, cy + 60), fill=230)
    a = np.asarray(im, np.float32) / 255
    img[:860] = np.maximum(img[:860], a)
    for li, (i, tok, (x1, y1), t0) in enumerate(leader_targets(sc, t)):
        if t0 is None:
            st = line_starts(sc)[i]
            t0 = -99 if st is None else st + len(lines[i]) / TYPE_RATE
        la = sstep(t0, t0 + 0.30, t)
        if la <= 0:
            continue
        if M is not None:
            x1, y1 = M[0, 0] * x1 + M[0, 2], M[1, 1] * y1 + M[1, 2]
        x0 = tok_x(sc, i, tok)
        y0 = L0 + i * LH + 58
        gx = 905 - 13 * li                                           # right gutter, one lane per leader
        if y1 > 640:                                                 # elbow: under token -> gutter -> down -> into the part
            pts = [(x0, y0), (x0, y0 + 6 + 4 * li), (gx, y0 + 6 + 4 * li), (gx, y1), (x1, y1)]
        else:
            pts = [(x0, y0), (x1, y1)]
        seg = [math.dist(pts[k], pts[k + 1]) for k in range(len(pts) - 1)]
        left = la * sum(seg)
        for k, L in enumerate(seg):
            if left <= 0:
                break
            u = min(1.0, left / max(L, 1e-6))
            p, q = np.array(pts[k]), np.array(pts[k + 1])
            line(img, p, p + (q - p) * u, 0.6, 2)
            left -= L
        line(img, (x0 - 18, y0), (x0 + 18, y0), 0.75, 2)
        if la > 0.98:
            circle(img, (x1, y1), 9, 0.9, 2)
    return boxes


# ---------------------------------------------------------------- camera: slow push-ins + punch on reveals
FOCUS = {0: (460, 1000), 1: (500, 1150), 2: (460, 1150), 3: (460, 900), 4: (600, 1150), 5: (460, 700), 6: (700, 1000), 7: (460, 1000)}
HITS = [(LAND_U, 0.05, 10), (LAND_Q, 0.05, 10), (LAND_GAP, 0.07, 14), (JUMP1[1], 0.03, 6), (wend('eight') + 0.05, 0.04, 8)]


def punch(t, t0, amp, tau):
    return amp * math.exp(-(t - t0) / tau) if t >= t0 else 0.0


def camera(sc, t):
    a, b = scene_span(sc)
    tau = t - DUR if (sc == 0 and t > DUR / 2) else t
    z = 1.0 + 0.04 * sstep(a, b, tau)
    sx = sy = 0.0
    for t0, za, ea in HITS:
        z += punch(t, t0, za, 0.16)
        e = punch(t, t0, ea, 0.2)
        sx += e * math.sin(2 * math.pi * 23 * t)
        sy += e * 0.7 * math.cos(2 * math.pi * 19 * t)
    fx, fy = FOCUS[sc]
    return np.array([[z, 0, (1 - z) * fx + sx], [0, z, (1 - z) * fy + sy]], np.float32)


def flash(t):
    return 0.0


# ---------------------------------------------------------------- dim data-rain background (looping, adds depth)
_rr = np.random.default_rng(3)
RAIN = [(c, int(_rr.integers(3, 8)), int(_rr.integers(8, 20)), float(_rr.random()), _rr.integers(2, len(AC.GLYPHS), 40))
        for c in range(AC.COLS) if _rr.random() < 0.26]


def rain(t):
    out = np.zeros((H, W), np.float32)
    for c, k, L, ph, gl in RAIN:
        span = H + L * AC.CH
        head = (k * span * t / DUR + ph * span) % span                # k whole passes per loop -> seamless
        for j in range(L):
            y = int(head - j * AC.CH)
            if 0 <= y < H - AC.CH:
                a = 0.24 if j == 0 else 0.11 * (1 - j / L)
                out[y:y + AC.CH, c * AC.CW:(c + 1) * AC.CW] = np.maximum(out[y:y + AC.CH, c * AC.CW:(c + 1) * AC.CW],
                                                                       AC.ATLAS[gl[j % 40]] * a)
    return out


# ---------------------------------------------------------------- scene renderer (ASCII via the approved matcher)
class Scenes:
    def __init__(self):
        self.m = {k: AC.Matcher() for k in range(len(CANVAS))}
        self.last = {k: -999 for k in range(len(CANVAS))}

    def _step(self, sc, i):
        t = (i % N) / FPS
        acc = np.zeros((H, W), np.float32)
        for k in range(SUB):
            acc += CANVAS[sc](t + (k - (SUB - 1) / 2) / (FPS * SUB))
        prevP = None if self.m[sc].P is None else self.m[sc].P.copy()
        ch = self.m[sc].step(acc / SUB)
        lit = (self.m[sc].gid > 0) | ch
        self.m[sc].last_change = float(ch[lit].mean()) if lit.any() else 0.0
        if prevP is not None:                                      # flicker = glyph swaps where the image did not change
            still = np.abs(self.m[sc].P - prevP).mean(2) < 0.01
            self.m[sc].flicker = float((ch & still)[lit].mean()) if lit.any() else 0.0
        self.last[sc] = i

    def image(self, sc, i):
        if self.last[sc] != i - 1 and self.last[sc] != i:
            for j in range(i - 8, i):                              # pre-roll EMA/hysteresis before it appears
                self._step(sc, j)
        if self.last[sc] != i:
            self._step(sc, i)
        t = (i % N) / FPS
        m = self.m[sc]
        img = np.zeros((H, W), np.float32)
        img[AC.Y0:AC.Y0 + AC.ROWS * AC.CH, :AC.COLS * AC.CW] = AC.plane_of(m.gid, 0.62 + 0.45 * np.sqrt(np.clip(m.P.mean(2), 0, 1)))
        M = camera(sc, t)
        img = cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR)
        img = np.maximum(img, rain(t))
        boxes = code_card(sc, t, img, M)
        return img, boxes



# ---------------------------------------------------------------- waterfall cascade: decompose (fall) -> reassemble (rain in)
R_, C_ = AC.ROWS, AC.COLS
_cc = np.arange(C_)
_JIT = 0.5 + 0.25 * np.sin(0.37 * _cc + 1.3) + 0.25 * np.sin(1.71 * _cc)
TRAV = 0.40


def tiles(img):
    return img[AC.Y0:AC.Y0 + R_ * AC.CH, :C_ * AC.CW].reshape(R_, AC.CH, C_, AC.CW).transpose(0, 2, 1, 3)


def offsets(t, T, D):
    rr = np.arange(R_)[:, None] / R_
    lag = 0.16 * D * _JIT[None, :] + 0.14 * D * (1 - rr)          # streams per column; bottom rows lead
    uo = np.clip((t - T - lag) / (TRAV * D), 0, 1)
    ui = np.clip((t - T - 0.30 * D - lag) / (TRAV * D), 0, 1)
    fall = 1.12 * H
    return fall * uo ** 2.4, -fall * (1 - ui) ** 2.4, uo, ui


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
    for k in range(SUB):                                           # 4 sub-frame positions -> motion blur
        do, di, _, _ = offsets(t + (k - 1.5) / (FPS * SUB), T, D)
        out = np.zeros((H, W), np.float32)
        scatter(out, ta, do)
        scatter(out, tb, di)
        acc += out
    return acc / SUB


# ---------------------------------------------------------------- post (same look as the approved ASCII video: bloom, scanlines, vignette)
def post(img):
    small = cv2.resize(img, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
    bloom = cv2.resize(0.40 * cv2.GaussianBlur(small, (0, 0), 2.0) + 0.30 * cv2.GaussianBlur(small, (0, 0), 9.0),
                       (W, H), interpolation=cv2.INTER_LINEAR)
    out = (img + bloom)[..., None] * RD.SCAN * RD.VIG
    return np.repeat((np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8), 3, 2)


def frames(indices, want):
    S = Scenes()
    for i in indices:
        t = (i % N) / FPS
        sc, k = scene_at(t)
        if i not in want:
            continue
        if k is None:
            img, boxes = S.image(sc, i)
            meta_sc = sc
        else:
            T, D, a, b = CASC[k]
            ia, _ = S.image(a, i)
            ib, boxes = S.image(b, i)
            img = cascade(ia, ib, t, T, D)
            meta_sc = f'{a}->{b}'
        m = S.m[sc] if k is None else None
        img = img + flash(t)
        yield i, post(img), dict(i=int(i), t=round(t, 4), scene=meta_sc, boxes=[list(map(float, b)) for b in boxes],
                                 glyph_change=float(m.last_change) if m is not None and hasattr(m, 'last_change') else None,
                                 flicker=float(m.flicker) if m is not None and hasattr(m, 'flicker') else None)


def main():
    mode = sys.argv[1]
    if mode == 'still':
        out = Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
        for stamp in sys.argv[3:]:
            fi = int(round(float(stamp) * FPS)) % N
            for _, rgb, _ in frames(range(fi, fi + 1), {fi}):
                Image.fromarray(rgb).save(out / f'f_{stamp}.png')
                print('still', stamp)
        return
    dst = Path(sys.argv[2]).resolve(); dst.parent.mkdir(parents=True, exist_ok=True)
    ff = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS),
                           '-i', '-', '-c:v', 'libx264', '-preset', 'slow', '-crf', '14', '-maxrate', '12M', '-bufsize', '24M',
                           '-pix_fmt', 'yuv420p', '-g', '30', str(dst)], stdin=subprocess.PIPE)
    metas, t0 = [], time.time()
    for i, rgb, meta in frames(range(N), set(range(N))):
        ff.stdin.write(rgb.tobytes()); metas.append(meta)
        if i % 30 == 0:
            print(f'frame {i}/{N} {time.time() - t0:.0f}s', flush=True)
    ff.stdin.close(); assert ff.wait() == 0
    json.dump(metas, open(dst.with_suffix('.frames.json'), 'w'))
    print('wrote', dst, f'{time.time() - t0:.0f}s')


if __name__ == '__main__':
    main()
