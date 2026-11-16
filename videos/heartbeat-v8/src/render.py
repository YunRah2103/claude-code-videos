"""heartbeat-v8: hacker-terminal ASCII explainer, 1080x1920 @30 fps, ~16.5 s loop.

Reuses the approved ASCII style unchanged from videos/ascii-terminal-test/src/ascii_car.py
(structure-matched glyph atlas, EMA 0.6 + hysteresis Matcher, glyph intensity, floor dots, E92 canvases).
python render.py still OUTDIR 0 8.2 15   |   python render.py video OUT_silent.mp4
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

DUR = 16.5
W, H, FPS, SUB = 1080, 1920, 30, 4
N = int(round(DUR * FPS))
WORDS = json.load(open(Path(__file__).with_name('words.json')))
BP = DUR / 16                     # heartbeat period 1.03 s ("about once a second"), 16 beats per loop -> seamless


def wt(word, k=0):
    """start time of the k-th occurrence of a spoken word"""
    return [w['s'] for w in WORDS if w['w'] == word][k]


def sstep(a, b, x):
    u = min(max((x - a) / (b - a), 0.0), 1.0)
    return u * u * u * (u * (6 * u - 15) + 10)


def eout(u):
    u = min(max(u, 0.0), 1.0)
    return 1 - (1 - u) ** 3


# ---------------------------------------------------------------- timeline (anchored to word timings)
HIT560 = wt('sixty') + 0.08                    # counter lands on 560
HIT280 = wt('eighty') + 0.06
SCREAM = wt('scream') + 0.10
CASC = [  # (start, duration, from_scene, to_scene)
    (wt('this') - 0.41, 0.66, 0, 1),
    (wt('every') - 0.45, 0.66, 1, 2),
    (wt("it's") - 0.69, 0.66, 2, 3),
    (wt('built') - 0.65, 0.62, 3, 4),
    (wt('loud') - 0.63, 0.62, 4, 5),
    (DUR - 0.64, 0.64, 5, 0),
]


def scene_at(t):
    """(scene, None) when held, or (cascade index) during a cascade"""
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


# ---------------------------------------------------------------- drawing helpers (float luminance canvases)
F_DIG = ImageFont.truetype('/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-ExtraBold.ttf', 340)
F_DIG_M = ImageFont.truetype('/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-ExtraBold.ttf', 280)
F_DIG_R = ImageFont.truetype('/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-ExtraBold.ttf', 230)
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


def digits(img, text, cx, cy, font, val=1.0):
    """big counter digits drawn into the luminance canvas (the ASCII matcher turns them into glyph art)"""
    tw = int(font.getlength(text)) + 20
    im = Image.new('L', (tw, font.size + 60), 0)
    ImageDraw.Draw(im).text((10, 10), text, font=font, fill=255)
    a = np.asarray(im, np.float32) / 255 * val
    y0, x0 = int(cy - a.shape[0] / 2), int(cx - tw / 2)
    ys, xs = slice(max(y0, 0), y0 + a.shape[0]), slice(max(x0, 0), x0 + tw)
    img[ys, xs] = np.maximum(img[ys, xs], a[ys.start - y0:, xs.start - x0:][:img[ys, xs].shape[0], :img[ys, xs].shape[1]])
    return x0, y0, tw, a.shape[0]


# ---------------------------------------------------------------- scene 0: heartbeat line
HEADX, BASE, AMP, V0 = 800, 1130, 430, 520.0
_GRID = np.zeros((H, W), np.float32)
for _x in range(40, 861, 60):
    _GRID[640:1460:6, _x] = 0.14
for _y in range(640, 1461, 60):
    _GRID[_y, 40:861:6] = 0.14


def ecg(ph):
    g = lambda c, w, a: a * np.exp(-((ph - c) / w) ** 2)
    return g(.16, .025, .10) + g(.29, .008, -.12) + g(.31, .009, 1.0) + g(.33, .010, -.32) + g(.55, .045, .24)


def heart_pts(cx, cy, s):
    a = np.linspace(0, 2 * np.pi, 80)
    x = 16 * np.sin(a) ** 3
    y = -(13 * np.cos(a) - 5 * np.cos(2 * a) - 2 * np.cos(3 * a) - np.cos(4 * a))
    return np.stack([cx + x * s, cy + y * s], 1)


def head_y(t):
    return BASE - AMP * ecg(np.array([(t / BP) % 1.0]))[0]


def canvas0(t):
    img = _GRID.copy()
    xs = np.arange(40, HEADX + 1, 2, dtype=np.float32)
    ph = ((t - (HEADX - xs) / V0) / BP) % 1.0
    ys = BASE - AMP * ecg(ph)
    lay = np.zeros((H, W), np.float32)
    cv2.polylines(lay, [np.round(np.stack([xs, ys], 1) * SH16).astype(np.int32)], False, 1.0, 17, cv2.LINE_AA, 4)
    lay = np.maximum(lay, 0.55 * cv2.GaussianBlur(lay, (0, 0), 7))
    lay *= (0.30 + 0.70 * ((np.arange(W) - 40) / (HEADX - 40)).clip(0, 1))[None, :]
    img = np.maximum(img, lay)
    circle(img, (HEADX, head_y(t)), 20, 1.0, -1)
    dt = (((t / BP) - 0.31) % 1.0) * BP                 # time since the R spike reached the head
    s = 9.5 * (1 + 0.20 * math.exp(-dt / 0.12))
    hp = heart_pts(190, 1400, s)
    poly(img, hp, 0.55)
    cv2.polylines(img, [np.round(hp * SH16).astype(np.int32)], True, 1.0, 5, cv2.LINE_AA, 4)
    return img


# ---------------------------------------------------------------- engine phase (integrated so speed changes are smooth)
_TG = np.arange(0, DUR + 0.01, 1 / 2400)


def _omega(t):                                         # visual crank speed, rev/s
    if t < CASC[1][0] + 0.4:                           # scene 1: blur builds with the counter
        return 1.5 + 5.5 * sstep(CASC[0][0], HIT560, t)
    if t < CASC[2][0] + 0.4:                           # scene 2: slow-motion cutaway
        return 7.0 - 6.2 * sstep(CASC[1][0], CASC[1][0] + 0.6, t)
    return 3.0


_THETA = np.cumsum([_omega(x) for x in _TG]) * 2 * np.pi / 2400


def theta(t):
    return float(np.interp(t, _TG, _THETA))


def count560(t):
    return int(round(560 * eout((t - (CASC[0][0] + 0.7)) / (HIT560 - CASC[0][0] - 0.7))))


def count280(t):
    return int(round(280 * eout((t - (CASC[1][0] + 0.7)) / (HIT280 - CASC[1][0] - 0.7))))


def rpm(t):
    a, b = CASC[3][0], CASC[3][0] + CASC[3][1]
    if t < b:
        base = 1500 + 4700 * sstep(CASC[2][0] + 0.5, a + 0.1, t)
        return base + 260 * math.sin(2 * math.pi * 1.6 * t) * sstep(CASC[2][0] + 0.5, CASC[2][0] + 1.0, t)
    r = 6200 + 2200 * sstep(b - 0.05, SCREAM, t)
    r -= 160 * (0.5 + 0.5 * math.sin(2 * math.pi * 7 * t)) * sstep(SCREAM, SCREAM + 0.1, t)   # limiter bounce
    return r - 5000 * sstep(wt('car') + 0.15, CASC[4][0] + 0.3, t)


# ---------------------------------------------------------------- scene 1: V8 (8 pistons, two banks) + counter 560
VC = np.array([450.0, 1430.0])
FIRE_ORDER = [0, 1.5, 3, 0.5, 2, 3.5, 1, 2.5]       # crossplane-style spacing in multiples of 90 deg per bank slot


def v8(img, th, t, cx=VC, scale=1.0, flash=True):
    for side, sgn in ((0, -1), (1, 1)):
        u = np.array([sgn * 0.7071, -0.7071])
        v = np.array([0.7071, sgn * 0.7071])
        for i in range(4):
            k = side * 4 + i
            ti = th + FIRE_ORDER[k] * math.pi / 2
            base = cx + u * 150 * scale + v * (i - 1.5) * 76 * scale
            top = base + u * 280 * scale
            for sgn2 in (-1, 1):                                   # cylinder walls
                line(img, base + v * 36 * scale * sgn2, top + v * 36 * scale * sgn2, 0.85, 4)
            line(img, top - v * 36 * scale, top + v * 36 * scale, 0.85, 4)
            s = (95 + 115 * (1 + math.cos(ti)) / 2) * scale
            pc = base + u * (s + 28 * scale)
            rrect(img, pc, u, v, 28 * scale, 31 * scale, 0.62)
            line(img, pc - u * 10 * scale, cx + 62 * scale * np.array([math.cos(th), math.sin(th)]), 0.55, 3)
            if flash:
                f = math.exp(-((ti % (4 * math.pi)) / 0.55))
                if f > 0.05:
                    for a in range(8):
                        d = np.array([math.cos(a * math.pi / 4), math.sin(a * math.pi / 4)])
                        line(img, top - u * 20 * scale, top - u * 20 * scale + d * 46 * f * scale, f, 4)
    circle(img, cx, 95 * scale, 0.8, 4)
    circle(img, cx + 62 * scale * np.array([math.cos(th), math.sin(th)]), 16 * scale, 1.0, -1)


def canvas1(t):
    img = np.zeros((H, W), np.float32)
    th = theta(t)
    for k in range(3):                                             # inner temporal supersampling: piston blur
        tmp = np.zeros((H, W), np.float32)
        v8(tmp, th + k * _omega(t) * 2 * math.pi / (FPS * SUB * 3), t)
        img += tmp / 3
    c = count560(t)
    digits(img, f'{c:3d}', 450, 740, F_DIG)
    g = t - HIT560
    if 0 < g < 0.6:                                                # shockwave on the 560 hit
        circle(img, (450, 745), 170 + 520 * g, max(0.0, 1 - g / 0.6), 6)
    return img


# ---------------------------------------------------------------- scene 2: cutaway, pistons reversing + counter 280
CX3 = [165.0, 375.0, 585.0, 795.0]
PH3 = [0, 0.5, 1.5, 1.0]


def canvas2(t):
    img = np.zeros((H, W), np.float32)
    th = theta(t)
    yc = 1440.0
    for i, x in enumerate(CX3):
        ti = th + PH3[i] * math.pi
        for sgn in (-1, 1):                                        # cutaway walls with hatch
            wx = x + sgn * 82
            line(img, (wx, 820), (wx, 1330), 0.9, 5)
            for y in range(830, 1330, 22):
                line(img, (wx + sgn * 4, y), (wx + sgn * 22, y - 14), 0.45, 2)
        ytop = 860 + 300 * (1 - math.cos(ti)) / 2
        rrect(img, (x, ytop + 48), (0, 1), (1, 0), 48, 64, 0.55)
        for r in range(3):
            line(img, (x - 64, ytop + 14 + 12 * r), (x + 64, ytop + 14 + 12 * r), 0.15, 3)
        pin = (x + 52 * math.sin(ti), yc - 52 * math.cos(ti))
        line(img, (x, ytop + 70), pin, 0.65, 6)
        circle(img, (x, yc), 52, 0.6, 3)
        circle(img, pin, 11, 1.0, -1)
        up = math.sin(ti) > 0                                      # moving up while sin > 0 (y decreasing)
        ay = ytop + 50
        tri = [(x, ay - 34), (x - 30, ay + 18), (x + 30, ay + 18)] if up else [(x, ay + 34), (x - 30, ay - 18), (x + 30, ay - 18)]
        poly(img, tri, 1.0)
        f = math.exp(-abs(((ti + math.pi / 2) % math.pi) - math.pi / 2) / 0.22)   # flash at each reversal
        if f > 0.05:
            circle(img, (x, ay), 40 + 50 * (1 - f), f, 4)
    digits(img, f'{count280(t):3d}', 470, 650, F_DIG_M)
    g = t - HIT280
    if 0 < g < 0.5:
        circle(img, (470, 640), 130 + 420 * g, max(0.0, 1 - g / 0.5), 5)
    return img


# ---------------------------------------------------------------- scenes 3/4: the E92 (approved front + side art), revving
def canvas3(t):
    tau = 1.55 + (t - CASC[2][0]) * 1.0                            # light sweep crosses during the scene
    img = AC.car_canvas(tau).copy()
    digits(img, f'{int(rpm(t)) // 10 * 10:4d}', 345, 615, F_DIG_R)
    return img


def canvas4(t):
    img = AC.side_canvas(t % AC.DUR).copy()
    digits(img, f'{int(rpm(t)) // 10 * 10:4d}', 345, 615, F_DIG_R)
    return img


# ---------------------------------------------------------------- scene 5: poll
ICON_V8, ICON_EV = np.array([265.0, 1130.0]), np.array([715.0, 1130.0])
BOLT = np.array([(30, -150), (-70, 20), (-5, 20), (-35, 150), (75, -30), (8, -30), (45, -150)], np.float32)


def hl_v8(t):
    return sstep(wt('loud') - 0.05, wt('loud') + 0.15, t) * (1 - sstep(wt('or') - 0.05, wt('or') + 0.2, t)) + sstep(wt('pick'), wt('pick') + 0.2, t)


def hl_ev(t):
    return sstep(wt('silent') - 0.05, wt('silent') + 0.15, t) * (1 - sstep(wt('pick') - 0.3, wt('pick') - 0.05, t)) + sstep(wt('pick'), wt('pick') + 0.2, t)


def ring(img, c, r, h, t, dirn):
    circle(img, c, r, 0.30 + 0.70 * h, 4)
    for k in range(24):                                            # rotating dashes keep the frame alive
        a = dirn * t * 0.9 + k * 2 * math.pi / 24
        d = np.array([math.cos(a), math.sin(a)])
        line(img, c + d * (r + 14), c + d * (r + 30 + 12 * h), 0.35 + 0.65 * h, 4)


def canvas5(t):
    img = np.zeros((H, W), np.float32)
    hv, he = min(hl_v8(t), 1), min(hl_ev(t), 1)
    ring(img, ICON_V8, 175 * (1 + 0.06 * hv), hv, t, 1)
    ring(img, ICON_EV, 175 * (1 + 0.06 * he), he, t, -1)
    v8(img, theta(t) + t * 2 * math.pi * 2.5, t, cx=ICON_V8 + np.array([0, 95]), scale=0.38, flash=True)
    poly(img, BOLT * (1 + 0.05 * he) + ICON_EV, 0.55 + 0.45 * he)
    for k in range(6):                                             # sparks orbiting the bolt
        a = t * 3.1 + k * 1.047
        circle(img, ICON_EV + 125 * np.array([math.cos(a), math.sin(a)]), 6, 0.4 + 0.6 * he, -1)
    return img


CANVAS = [canvas0, canvas1, canvas2, canvas3, canvas4, canvas5]
FLOOR = {3: AC.CARM, 4: AC.SIDEM}

# ---------------------------------------------------------------- code cards (crisp terminal text; tag + <=29 chars per line)
CODE = [
    ('py', ['heart_bpm = 60  # about 1/sec']),
    ('py', ['fires = 8 * 8400 / 2 / 60', '# roughly 560/sec']),
    ('c++', ['int flips = 8400 / 60 * 2;', '// roughly 280/sec']),
    ('c++', ['constexpr int kRedlineRpm =', '    8400;']),
    ('c++', ['constexpr int kRedlineRpm =', '    8400;']),
    ('py', ['choice = input(', '    "V8 or electric? ")']),
]
CX0, TAGY, L0, LH = 40, 248, 330, 72
CHW = F_CODE.getlength('M')


def tok_val(s):
    s2 = s.lstrip()
    if s2.startswith('#') or s2.startswith('//'):
        return 0.55
    return 1.0


def leader_targets(sc, t):
    """(from_xy, to_xy) leader lines: code token -> what it describes"""
    if sc == 0:
        return [((CX0 + CHW * 16, L0 + 62), (HEADX, head_y(t) - 20))]
    if sc == 1:
        return [((CX0 + CHW * 10, L0 + LH + 62), (300, 640))]
    if sc == 2:
        th = theta(t)
        return [((CX0 + CHW * 10, L0 + LH + 62), (CX3[0], 910 + 300 * (1 - math.cos(th)) / 2))]
    if sc in (3, 4):
        return [((CX0 + CHW * 8, L0 + LH + 62), (200, 535))]
    return [((CX0 + CHW * 5, L0 + LH + 62), tuple(ICON_V8 - (0, 205))),
            ((CX0 + CHW * 11, L0 + LH + 62), tuple(ICON_EV - (0, 205)))]


TEXT_BOXES = []          # (scene, x0, y0, x1, y1, height) for the layout check


TYPE_RATE = 62.0                      # chars/s, terminal typing after each scene lands


def type_start(sc):
    if sc in (0, 4):
        return None                                               # loop scene / continued card: always complete
    for T, D, a, b in CASC:
        if b == sc:
            return T + 0.80 * D
    return None


def typed(sc, t):
    st = type_start(sc)
    total = sum(len(x) for x in CODE[sc][1])
    if st is None:
        return total
    return int(np.clip((t - st) * TYPE_RATE, 0, total))


def typing_events():
    """(time, scene) for every typed character: the audio adds a key click for each"""
    ev = []
    for sc in range(6):
        st = type_start(sc)
        if st is not None:
            ev += [(st + k / TYPE_RATE, sc) for k in range(sum(len(x) for x in CODE[sc][1]))]
    return ev


SCRAMBLE = '01#%&@$*<>{}'


def code_card(sc, t, img, M=None):
    tag, lines = CODE[sc]
    im = Image.new('L', (W, 560), 0)
    d = ImageDraw.Draw(im)
    tw = d.textlength(tag, font=F_TAG)
    d.rounded_rectangle((CX0 - 14, TAGY - 6, CX0 + tw + 14, TAGY + 64), 12, outline=150, width=3)
    d.text((CX0, TAGY), tag, font=F_TAG, fill=170)
    boxes = [(CX0 - 14, TAGY - 6, CX0 + tw + 14, TAGY + 64)]
    left = typed(sc, t)
    total = sum(len(x) for x in lines)
    cur = None
    for i, s_full in enumerate(lines):
        y = L0 + i * LH
        boxes.append(d.textbbox((CX0, y), s_full, font=F_CODE))
        s = s_full[:max(left, 0)]
        left -= len(s_full)
        if len(s) < len(s_full) and cur is None:
            cur = (CX0 + d.textlength(s, font=F_CODE), y)
        if not s:
            continue
        cut = s_full.find('#') if '#' in s_full and not s_full.lstrip().startswith('"') else s_full.find('//')
        if cut > 0:
            code, cmt = s[:cut], s[cut:]
        elif tok_val(s_full) < 1.0:
            code, cmt = '', s
        else:
            code, cmt = s, ''
        if code:
            d.text((CX0, y), code, font=F_CODE, fill=255)
        if cmt:
            d.text((CX0 + d.textlength(s[:len(s) - len(cmt)], font=F_CODE), y), cmt, font=F_CODE, fill=140)
    if cur is not None and typed(sc, t) > 0:                      # typing: scrambled glyph + solid cursor
        d.text(cur, SCRAMBLE[int(t * 40) % len(SCRAMBLE)], font=F_CODE, fill=200)
        d.rectangle((cur[0] + CHW + 4, cur[1] + 6, cur[0] + CHW + 30, cur[1] + 60), fill=230)
    elif cur is None and (t * 2.2) % 1 < 0.6:                     # done: blinking cursor
        last = lines[-1]
        cx = CX0 + d.textlength(last, font=F_CODE) + 8
        d.rectangle((cx, L0 + (len(lines) - 1) * LH + 6, cx + 26, L0 + (len(lines) - 1) * LH + 60), fill=230)
    a = np.asarray(im, np.float32) / 255
    img[:560] = np.maximum(img[:560], a)
    st = type_start(sc)
    la = 1.0 if st is None else sstep(st + total / TYPE_RATE, st + total / TYPE_RATE + 0.15, t)
    if la > 0:
        for (x0, y0), (x1, y1) in leader_targets(sc, t):
            if M is not None:
                x1, y1 = M[0, 0] * x1 + M[0, 2], M[1, 1] * y1 + M[1, 2]
            xm, ym = x0 + (x1 - x0) * la, y0 + (y1 - y0) * la
            line(img, (x0, y0), (x0 + 40, y0), 0.75, 2)
            line(img, (x0, y0), (xm, ym), 0.75, 2)
            if la > 0.98:
                circle(img, (x1, y1), 9, 0.9, 2)
    return boxes


# ---------------------------------------------------------------- camera: slow push-ins, heartbeat pulses, punch + shake on hits
FOCUS = {0: (600, 1080), 1: (450, 1000), 2: (480, 1000), 3: (540, 1036), 4: (540, 1110), 5: (490, 1130)}


def scene_span(sc):
    ins = [T for T, D, a, b in CASC if b == sc]
    outs = [T + D for T, D, a, b in CASC if a == sc]
    return ins[0], outs[0]


def punch(t, t0, amp, tau):
    return amp * math.exp(-(t - t0) / tau) if t >= t0 else 0.0


def camera(sc, t):
    sx = sy = 0.0
    if sc == 0:
        tau = t - DUR if t > DUR / 2 else t                       # unwrap: continuous across the loop
        z = 1.0 + 0.06 * sstep(CASC[-1][0] - DUR, CASC[0][0] + CASC[0][1], tau)
        dt = (((t / BP) - 0.31) % 1.0) * BP
        z += 0.022 * math.exp(-dt / 0.09)
    else:
        a, b = scene_span(sc)
        if sc == 3:
            z = 1.0
        elif sc == 4:
            z = 0.97 + 0.03 * sstep(a, b, t) + punch(t, SCREAM, 0.025, 0.25)
        else:
            z = 1.0 + 0.06 * sstep(a, b, t)
        if sc == 1:
            z += punch(t, HIT560, 0.09, 0.16)
            e = punch(t, HIT560, 16, 0.22)
            sx, sy = e * math.sin(2 * math.pi * 23 * t), e * 0.7 * math.cos(2 * math.pi * 19 * t)
        if sc == 2:
            z += punch(t, HIT280, 0.05, 0.16)
            e = punch(t, HIT280, 9, 0.2)
            sx, sy = e * math.sin(2 * math.pi * 23 * t), e * 0.7 * math.cos(2 * math.pi * 19 * t)
        if sc in (3, 4):
            e = 3.0 * rpm(t) / 8400 + punch(t, SCREAM, 9, 0.3)
            sx, sy = e * math.sin(2 * math.pi * 13 * t), e * 0.6 * math.sin(2 * math.pi * 17 * t + 1)
        if sc == 5:
            z += punch(t, wt('pick'), 0.04, 0.25)
    fx, fy = FOCUS[sc]
    return np.array([[z, 0, (1 - z) * fx + sx], [0, z, (1 - z) * fy + sy]], np.float32)


def flash(t):
    return punch(t, HIT560, 0.45, 0.07) + punch(t, HIT280, 0.22, 0.07) + punch(t, SCREAM, 0.18, 0.09)


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


def streaks(t):
    """'-' glyph speed streaks behind the side-view car, speed follows the rpm"""
    out = np.zeros((H, W), np.float32)
    g = AC.GLYPHS.index('-')
    v = 2600 * rpm(t) / 8400
    for k in range(14):
        y = 930 + (k * 97) % 330
        L = 6 + (k * 5) % 9
        x = (k * 233 + v * t) % (W + L * AC.CW) - L * AC.CW
        for j in range(L):
            xx = int(x - j * AC.CW)
            if 0 <= xx < W - AC.CW:
                out[y:y + AC.CH, xx:xx + AC.CW] = np.maximum(out[y:y + AC.CH, xx:xx + AC.CW], AC.ATLAS[g] * 0.7 * (1 - j / L))
    return out * (1 - AC.SIDEM)


# ---------------------------------------------------------------- scene renderer (ASCII via the approved matcher)
class Scenes:
    def __init__(self):
        self.m = {k: AC.Matcher() for k in range(6)}
        self.last = {k: -999 for k in range(6)}

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
        if sc in (3, 4):
            mot = np.zeros((H, W), np.float32)
            for k in range(SUB):
                mot += AC.motion_layer((t + (k - 1.5) / (FPS * SUB)) % AC.DUR, FLOOR[sc]) / SUB
            img = np.maximum(img, mot)
        if sc == 4:
            img = np.maximum(img, streaks(t))
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
