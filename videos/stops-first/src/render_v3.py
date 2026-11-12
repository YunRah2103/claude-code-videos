"""Stops first v3: 3D chase-cam race (Blender lanes from blend_race.py) + 2D text/technical overlays. 1080x1920 @30fps.

Timing: everything anchored to the voiceover (words.json). Schematic speed-vs-time curves (0-400-0 in 41.96 s and
29.93 s, 75 % of each clock spent accelerating) drive clocks, speed readouts, wheel spin, lane scroll and the
on-screen order. Each lane's ground scrolls with its own car; the cars' relative position is the real schematic
distance gap, compressed (tanh) so both stay in frame.
usage: python render_v3.py states OUT.json | still OUTDIR t.. | video OUT.mp4 | scan
"""
import json, math, subprocess, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

import render as v1                                            # word timings, fonts, audio helpers
from render import wt, pop, ss, lerp, font, FONT, FONT_B, FONT_M, sfx, add, read_wav, lufs, write_wav

DUR = 18.4
W, H, FPS, SR = 1080, 1920, 30, sfx.SR
OUT = v1.OUT
FRAMES = OUT / 'v3'
INK, PAPER, GREY = (20, 20, 24), (252, 252, 249), (105, 108, 118)
RED, BLUE, ORANGE = (214, 44, 36), (30, 92, 214), (238, 110, 20)
FONT_C = '/usr/share/fonts/opentype/inter/InterDisplay-SemiBold.otf'

# ---------------------------------------------------------------- timing (voiceover anchors)
T_BRK = wt('42') + 0.2                                         # both brake once the Chiron record is named
T_30 = wt('30')                                                # Nevera stops, clock freezes at 29.93
T_12 = wt('twelve')                                            # Chiron stops at 41.96, "12 s" gap marker
T_CH, T_NE = wt('chiron'), wt('nevera')
T_Q, T_EL = wt('would', 1), wt('electric')
LOOP0 = DUR - 0.35
SPLIT = 0.75
TP = 0.3                                                       # pre-roll: frame 1 is 0.3 s into the launch
MPS = 40.0                                                     # lane scroll (m/s) at 400 km/h, stylised

CARS = {'red': dict(name='CHIRON', col=RED, total=41.96, stop=T_12, p=2.0, key='chiron'),
        'blue': dict(name='NEVERA', col=BLUE, total=29.93, stop=T_30, p=2.6, key='nevera')}


def kmh(c, t):
    if t < T_BRK: return 400 * (1 - (1 - (t + TP) / (T_BRK + TP)) ** c['p'])   # Nevera's curve rises sooner (instant torque)
    u = (t - T_BRK) / (c['stop'] - T_BRK)
    return 0.0 if u >= 1 else 400 * (1 - u)


def clock(c, t):
    a = c['total'] * SPLIT
    if t < T_BRK: return a * (t + TP) / (T_BRK + TP)
    return min(c['total'], a + (c['total'] - a) * (t - T_BRK) / (c['stop'] - T_BRK))


_TS = np.arange(0, DUR + 1, 1 / 240)
for c in CARS.values():
    c['kmh'] = np.array([kmh(c, x) for x in _TS])
    c['s'] = np.concatenate([[0], np.cumsum(c['kmh'][:-1] / 400 * MPS) / 240]) + 0.5 * MPS * TP * (1 / (1 + c['p']))


def lane(c, t): return float(np.interp(t, _TS, c['s']))
def vnow(c, t): return float(np.interp(t, _TS, c['kmh']))


def gap_m(t):
    """Red's position relative to blue (m), compressed so both stay side by side in frame; order is exact."""
    return 1.2 * math.tanh((lane(CARS['red'], t) - lane(CARS['blue'], t)) / 10.0)


def heat(c, t):
    if t < T_BRK: return 0.0
    if t < c['stop']: return ss((t - T_BRK) / 1.0)
    return math.exp(-(t - c['stop']) / 2.5)


def pitch(c, t):
    sq = -1.2 * ss(t / 0.3) * math.exp(-max(0, t - 0.3) * 0.8) if t < T_BRK else 0
    dive = 1.4 * ss((t - T_BRK) / 0.35) if T_BRK <= t < c['stop'] else 0
    reb = 1.4 * math.exp(-(t - c['stop']) * 5) * math.cos((t - c['stop']) * 16) if t >= c['stop'] else 0
    return sq + dive + reb


def brake_zone(t): return ss((t - (T_BRK - 1.6)) / 0.6) * (1 - ss((t - (T_12 + 0.4)) / 0.8))


def cam(t):
    """One fluid 360-degree orbit (yaw 0 = straight behind, 90 = red side, 180 = front, 270 = blue side); loops to frame 1."""
    yaw = 360 * (t / DUR) + 6 * math.sin(2 * math.pi * t / DUR)
    s2 = math.sin(math.radians(yaw)) ** 2
    return yaw % 360, 11 + 17 * s2 + 3 * math.sin(math.radians(yaw / 2)) ** 2, 11.6 + 1.2 * s2


def states():
    out = []
    u0 = {k: lane(c, T_BRK) + 2.0 for k, c in CARS.items()}      # brake zone starts just ahead of each car at T_BRK
    for i in range(int(DUR * FPS)):
        t = i / FPS; r, b = CARS['red'], CARS['blue']
        out.append(dict(t=t, xr=gap_m(t), xb=0.0, sr=lane(r, t), sb=lane(b, t), pr=pitch(r, t), pb=pitch(b, t),
                        hr=heat(r, t), hb=heat(b, t), bz=brake_zone(t), u0r=u0['red'], u0b=u0['blue'],
                        vr=vnow(r, t), vb=vnow(b, t), yaw=cam(t)[0], el=cam(t)[1], cd=cam(t)[2]))
    return out


# ---------------------------------------------------------------- 2D layer (text + technical overlays)
BOXES = []


def text(d, xy, s, f, col=INK, anchor='la', sc=1.0, halo=True):
    if sc <= 0: return None
    f2 = font(f.path, max(4, int(f.size * sc)))
    d.text(xy, s, font=f2, fill=col, anchor=anchor, stroke_width=4 if halo else 0, stroke_fill=PAPER)
    bb = d.textbbox(xy, s, font=f2, anchor=anchor); BOXES.append((s, f.size, bb)); return bb


def car_block(d, key, t):
    """Name tag, ONE large clock, thin speed readout; STOPPED badge when the car plants."""
    c = CARS[key]; right = key == 'blue'; x = 905 if right else 60; an = 'r' if right else 'l'
    hi = T_CH if key == 'red' else T_NE
    text(d, (x, 598), c['name'], font(FONT, 62), c['col'], an + 's', 1 + 0.12 * math.sin(math.pi * min(1, max(0, (t - hi) / 0.4))))
    s = f'{clock(c, t):05.2f} s'; f = font(FONT_M, 80)
    if t >= c['stop']:
        p = 1 + 0.15 * math.sin(math.pi * min(1, (t - c['stop']) / 0.3))
        bb = d.textbbox((x, 694), s, font=font(FONT_M, int(80 * p)), anchor=an + 's')
        d.rounded_rectangle([bb[0] - 14, bb[1] - 10, bb[2] + 14, bb[3] + 12], 12, fill=c['col'])
        text(d, (x, 694), s, f, PAPER, an + 's', p, halo=False)
        sp = pop(t, c['stop'] + 0.15, 0.25)                               # STOPPED tag
        if sp > 0:
            bb = d.textbbox((x, 770), 'STOPPED', font=font(FONT, int(58 * sp)), anchor=an + 's')
            d.rounded_rectangle([bb[0] - 12, bb[1] - 8, bb[2] + 12, bb[3] + 10], 10, fill=INK)
            text(d, (x, 770), 'STOPPED', font(FONT, 58), PAPER, an + 's', sp, halo=False)
    else:
        text(d, (x, 694), s, f, INK, an + 's')
        text(d, (x, 770), f'{int(round(vnow(c, t))):3d} km/h', font(FONT_M, 58), GREY, an + 's')


def traces(d, t):
    """Technical layer, braking only: thin speed-vs-time trace per car (record time on x)."""
    a = ss((t - (T_BRK - 0.3)) / 0.5) * (1 - ss((t - (T_12 + 0.8)) / 0.6))
    if a <= 0.01: return
    x0, x1, y0, y1 = 300, 660, 805, 935; sx = (x1 - x0) / 44; sy = (y1 - y0) / 400
    g = tuple(int(lerp(252, v, a)) for v in (150, 155, 165))
    d.line([x0, y1, x1, y1], fill=g, width=2); d.line([x0, y0, x0, y1], fill=g, width=2)
    for key in ('red', 'blue'):
        c = CARS[key]; ts = np.linspace(0, min(t, c['stop']), 120)
        pts = [(x0 + clock(c, u) * sx, y1 - kmh(c, u) * sy) for u in ts]
        col = tuple(int(lerp(252, v, a)) for v in c['col'])
        d.line(pts, fill=col, width=4, joint='curve')
        d.ellipse([pts[-1][0] - 6, pts[-1][1] - 6, pts[-1][0] + 6, pts[-1][1] + 6], fill=col)


def gap_marker(d, t):
    s = pop(t, T_12, 0.3)
    if s <= 0 or t >= T_Q: return
    f = font(FONT, int(64 * s)); bb = d.textbbox((482, 750), '12 s', font=f, anchor='mm')
    d.rounded_rectangle([bb[0] - 14, bb[1] - 12, bb[2] + 14, bb[3] + 12], 14, fill=INK)
    text(d, (482, 750), '12 s', font(FONT, 64), PAPER, 'mm', s, halo=False)


def panel(d, t):
    if t < T_Q:
        text(d, (60, 232), 'WHICH STOPS', font(FONT, 98)); text(d, (60, 336), 'FIRST?', font(FONT, 98))
        text(d, (60, 452), 'separate record runs, schematic', font(FONT_C, 58), GREY)
    else:
        text(d, (60, 236), 'WOULD YOU TAKE', font(FONT, 76), sc=pop(t, T_Q, 0.25))
        text(d, (60, 334), 'THE ELECTRIC ONE?', font(FONT, 76), BLUE, sc=pop(t, T_EL, 0.25))
        for k, (lab, x, col) in enumerate((('YES', 60, BLUE), ('NO', 410, RED))):
            s = pop(t, T_EL + 0.15 + 0.12 * k, 0.25)
            if s <= 0: continue
            w, h = 300 * s, 104 * s; cx, cy = x + 150, 486
            d.rounded_rectangle([cx - w / 2 + 7, cy - h / 2 + 9, cx + w / 2 + 7, cy + h / 2 + 9], 18, fill=INK)
            d.rounded_rectangle([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2], 18, fill=PAPER, outline=INK, width=6)
            text(d, (cx, cy), lab, font(FONT, 64), col, 'mm', s, halo=False)
    text(d, (905, 236), 'Yub', font(FONT_B, 58), (150, 150, 158), 'ra')


VP = (540, 650)                                                    # vanishing point of the track


def speedlines(d, t):
    v = max(vnow(CARS['red'], t), vnow(CARS['blue'], t)) / 400
    if t > 3.0: return                                                # only while the camera is still behind the cars
    k = max(v, 0.6 * (1 - ss(t / 0.8))) * (1 - ss((t - 2.2) / 0.8))   # launch burst on frame 1
    rng = np.random.default_rng(int(t * FPS))
    for _ in range(int(26 * k)):
        a = rng.uniform(0, 2 * math.pi); r0 = rng.uniform(560, 900); ln = rng.uniform(120, 320) * k
        ca, sa = math.cos(a), math.sin(a)
        p0 = (VP[0] + ca * r0, VP[1] + sa * r0 * 1.3); p1 = (VP[0] + ca * (r0 + ln), VP[1] + sa * (r0 + ln) * 1.3)
        if p0[1] < 1000: continue                                     # streaks only on the lower ground, clear of text
        gcol = int(lerp(235, 160, k)); d.line([p0, p1], fill=(gcol, gcol, gcol + 6), width=3)


def shake(t):
    s = 7 * math.exp(-t * 3) * math.sin(t * 90)                      # launch
    for c in CARS.values():
        if c['stop'] <= t < c['stop'] + 0.4: s += 6 * math.exp(-(t - c['stop']) * 10) * math.sin(t * 110)
    if T_BRK <= t < T_BRK + 0.4: s += 4 * math.exp(-(t - T_BRK) * 10) * math.sin(t * 100)
    v = max(vnow(CARS['red'], t), vnow(CARS['blue'], t)) / 400
    return int(round(s + 1.5 * v * math.sin(t * 57)))


def render(t):
    BOXES.clear()
    i = min(int(round(t * FPS)), int(DUR * FPS) - 1)
    im = Image.open(FRAMES / f'f_{i:04d}.png').convert('RGB')
    sh = shake(t)
    if sh: im = Image.fromarray(np.roll(np.asarray(im), sh, 0))
    d = ImageDraw.Draw(im)
    speedlines(d, t); traces(d, t); panel(d, t)
    car_block(d, 'red', t); car_block(d, 'blue', t); gap_marker(d, t)
    return im


F0 = None


def frame(t):
    global F0
    a = np.asarray(render(t))
    if t >= LOOP0:
        if F0 is None: F0 = np.asarray(render(0.0)).astype(np.float32)
        k = ss((t - LOOP0) / (DUR - 1 / FPS - LOOP0))
        a = (a.astype(np.float32) * (1 - k) + F0 * k).astype(np.uint8)
    return a


def main():
    mode = sys.argv[1]
    if mode == 'still':
        out = Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
        for x in sys.argv[3:]: Image.fromarray(frame(float(x))).save(out / f'v3_{x}.png')
        return
    if mode == 'states':
        json.dump(states(), open(sys.argv[2], 'w')); print('frames', int(DUR * FPS), 'brake', round(T_BRK, 2),
                                                           'stops', round(T_30, 2), round(T_12, 2)); return


if __name__ == '__main__':
    main()
