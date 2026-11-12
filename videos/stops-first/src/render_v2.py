"""Stops first v2: top-down ink line art, two lanes side by side, cold open at 400 km/h. 1080x1920 @30fps.

Red (left) and blue (right) are original top-down shapes in the spirit of the two record cars. Both are already at
about 400 km/h on frame 1 and brake from 1.2 s. Clocks and positions come from one schematic speed-vs-record-time
curve per car (0-400-0 in 41.96 s and 29.93 s), with both clocks running at the same rate so the screen order
matches the numbers. Only colour effect besides the two accents: brake discs glow orange as they heat.
Shared code: v1 render.py (word timing, audio helpers), new-car-trap sfx.py, r3d.catmull for smooth outlines.
usage: python render_v2.py still OUTDIR t1 t2 ... | python render_v2.py video OUT.mp4 | python render_v2.py scan
"""
import math, subprocess, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

import render as v1                                          # word timings, fonts, audio helpers (shared)
from render import wt, pop, ss, lerp, font, FONT, FONT_B, FONT_M, sfx, add, read_wav, lufs, write_wav
from r3d import catmull

DUR = 18.4                                                   # voiceover 17.90 s + 0.5 s
W, H, FPS, SR = 1080, 1920, 30, sfx.SR
S2 = 2                                                       # supersampling factor
OUT = v1.OUT
INK, PAPER = (20, 20, 24), (252, 252, 249)
RED, BLUE = (214, 44, 36), (30, 92, 214)
GREY = (120, 122, 130)
MINPX = 0.03 * H                                             # minimum font size (3 % of frame height)

# ---------------------------------------------------------------- timing (all anchored to the voiceover)
T_B = 1.2                                                    # both start braking
T_CH, T_42 = wt('chiron'), wt('42')
T_NE, T_30 = wt('nevera'), wt('30')                          # blue stops on "30"
T_12, T_QK = wt('twelve'), wt('quicker')                     # gap marker on "twelve", red stops on "quicker"
T_PARK = wt('parked')
T_Q, T_EL = wt('would', 1), wt('electric')
LOOP0 = DUR - 0.35
K = 0.85                                                     # record seconds per video second (both clocks)

CARS = {'red': dict(name='CHIRON', col=RED, total=41.96, stop=T_QK, cx=295),
        'blue': dict(name='NEVERA', col=BLUE, total=29.93, stop=T_30, cx=715)}
for c in CARS.values():
    c['B'] = K * (c['stop'] - T_B)                           # schematic braking time (record s)
    c['A'] = c['total'] - c['B']                             # schematic 0-400 time


def tau(c, t):
    """Record-run clock: already deep into the run on frame 1, same rate for both cars, freezes at the record."""
    return min(c['total'], c['A'] + K * (t - T_B))


def kmh(c, t):
    x = tau(c, t)
    if x < c['A']: return 400 * (1 - (1 - x / c['A']) ** 2.2)
    return max(0.0, 400 * (1 - (x - c['A']) / c['B']))


_TS = np.arange(0, DUR + 1, 1 / 240)
for c in CARS.values():
    v = np.array([kmh(c, x) for x in _TS]) / 3.6 * K            # metres per video second (record metres)
    c['d'] = np.concatenate([[0], np.cumsum(v[:-1]) / 240])
    c['kmh'] = np.array([kmh(c, x) for x in _TS])


def dist(c, t): return float(np.interp(t, _TS, c['d']))
def vnow(c, t): return float(np.interp(t, _TS, c['kmh']))


def lead(t):
    """Screen lead of red over blue (px): order from the real schematic distances, size compressed to fit."""
    return 100 * math.tanh((dist(CARS['red'], t) - dist(CARS['blue'], t)) / 30)


def heat(c, t):
    if t < T_B: return 0.0
    if t < c['stop']: return ss((t - T_B) / 2.2) * (0.55 + 0.45 * ss((t - T_B) / 6))
    return math.exp(-(t - c['stop']) / 3.0)


PXM = 26.0                                                   # road scroll px per record metre
CAR_W, CAR_L, CAR_Y = 380, 820, 940                          # car size (px) and top edge at rest


def car_top(key, t):
    c = CARS[key]; y = CAR_Y - (lead(t) if key == 'red' else 0)
    v = vnow(c, t)
    y += 1.6 * math.sin(t * 61 + (0 if key == 'red' else 2)) * v / 400        # high-speed shimmer
    if t >= c['stop']:                                                          # settle after the stop
        u = t - c['stop']; y -= 10 * math.exp(-u * 5) * math.sin(u * 14)
    elif t >= T_B: y -= 8 * ss((t - T_B) / 0.3)                                 # weight shifts forward under braking
    return y


# ---------------------------------------------------------------- car artwork (top-down, ink line art)
def mirror(half):
    """Half outline (x >= 0, nose y=0 to tail y=1) -> closed outline."""
    h = list(half)
    return h + [(-x, y) for x, y in reversed(h) if x > 0]


def smooth(P, n=400): return catmull(np.asarray(P, float), n)


DESIGN = {
    'red': dict(   # wide and low: bulging front fenders, pinched waist, big rear haunches, flat tail
        body=[(0, 0), (0.30, 0.004), (0.56, 0.02), (0.74, 0.05), (0.88, 0.10), (0.96, 0.17), (0.97, 0.25), (0.86, 0.34),
              (0.80, 0.44), (0.82, 0.54), (0.93, 0.63), (1.0, 0.72), (1.0, 0.82), (0.94, 0.91), (0.80, 0.97), (0.50, 0.995), (0, 1.0)],
        canopy=[(0, 0.33), (0.30, 0.345), (0.45, 0.42), (0.47, 0.52), (0.42, 0.62), (0.26, 0.69), (0, 0.705)],
        roof=[(0, 0.43), (0.30, 0.44), (0.36, 0.50), (0.33, 0.585), (0.20, 0.615), (0, 0.62)],
        shuts=(0.33, 0.56), mirror=0.355, screen=0.40, wheels=(0.205, 0.80), wx=0.84),
    'blue': dict(  # smooth rounded cab-forward teardrop, long sloping tail
        body=[(0, 0), (0.36, 0.006), (0.62, 0.03), (0.80, 0.075), (0.91, 0.14), (0.95, 0.22), (0.92, 0.33), (0.86, 0.45),
              (0.88, 0.58), (0.94, 0.70), (0.94, 0.82), (0.87, 0.92), (0.70, 0.98), (0.40, 0.997), (0, 1.0)],
        canopy=[(0, 0.21), (0.33, 0.235), (0.49, 0.32), (0.51, 0.42), (0.44, 0.54), (0.30, 0.66), (0.13, 0.77), (0, 0.80)],
        roof=[(0, 0.33), (0.30, 0.345), (0.38, 0.42), (0.33, 0.52), (0.20, 0.60), (0, 0.63)],
        shuts=(0.25, 0.52), mirror=0.27, screen=0.30, wheels=(0.20, 0.80), wx=0.82),
}
PAD = 60


Q = 4                                                        # sprite drawing scale (downsampled to S2 for clean lines)
TONE, GLASS = (238, 240, 244), (226, 233, 242)


def to_px(P, q=None):
    q = q or Q; P = np.asarray(P, float)
    return [((PAD + (CAR_W / 2) * (1 + x)) * q, (PAD + CAR_L * y) * q) for x, y in P]


def line(d, P, col, w, closed=False):
    pts = to_px(P)
    if closed: pts = pts + pts[:1]
    d.line(pts, fill=col, width=max(1, int(w * Q)), joint='curve')


def scaled(P, sx, sy=1.0, cy=0.5):
    return [(x * sx, cy + (y - cy) * sy) for x, y in P]


def clip_lines(size, mask_poly, draw_fn):
    """Draw with draw_fn onto a layer, keep only what falls inside mask_poly."""
    lay = Image.new('RGBA', size, (0, 0, 0, 0)); draw_fn(ImageDraw.Draw(lay))
    m = Image.new('L', size, 0); ImageDraw.Draw(m).polygon(to_px(mask_poly), fill=255)
    a = np.asarray(lay).copy(); a[..., 3] = (a[..., 3].astype(np.uint16) * np.asarray(m) // 255).astype(np.uint8)
    return Image.fromarray(a)


def build_car(key):
    """Static sprite (RGBA, S2 scale): technical top-view illustration with a line-weight hierarchy."""
    D = DESIGN[key]; col = CARS[key]['col']
    size = ((CAR_W + 2 * PAD) * Q, (CAR_L + 2 * PAD) * Q)
    body = smooth(mirror(D['body']), 900)
    im = Image.new('RGBA', size, (0, 0, 0, 0))
    sh = Image.new('L', size, 0)                                                   # soft ground shadow
    ImageDraw.Draw(sh).polygon([(x + 10 * Q, y + 16 * Q) for x, y in to_px(scaled(D['body_full'], 1.02, 1.0))], fill=70)
    sh = sh.filter(ImageFilter.GaussianBlur(14 * Q))
    im.paste(Image.new('RGBA', size, (40, 44, 54, 255)), (0, 0), sh)
    d = ImageDraw.Draw(im)
    d.polygon(to_px(body), fill=PAPER + (255,))
    shoulder = smooth(mirror(scaled(D['body'], 0.86, 0.965)), 700)                 # where the top surface rolls over
    side = Image.new('L', size, 0); sd = ImageDraw.Draw(side)
    sd.polygon(to_px(body), fill=255); sd.polygon(to_px(shoulder), fill=0)
    im.paste(Image.new('RGBA', size, TONE + (255,)), (0, 0), side)                 # light tone on the flanks only
    d = ImageDraw.Draw(im)
    line(d, shoulder, (120, 124, 134), 1.3, True)
    can = smooth(mirror(D['canopy']), 500)
    d.polygon(to_px(can), fill=GLASS + (255,))
    roof = smooth(mirror(D['roof']), 300)
    d.polygon(to_px(roof), fill=PAPER + (255,))
    im.alpha_composite(clip_lines(size, can, lambda dd: [dd.line(to_px([(-0.6 + 0.16 * k, D['canopy'][0][1] - 0.02),
                                                                        (-0.25 + 0.16 * k, D['canopy'][-1][1] + 0.02)]),
                                                                fill=(255, 255, 255, 230), width=int(7 * Q)) for k in range(3)]))
    d = ImageDraw.Draw(im)
    line(d, roof, INK, 1.8, True)
    line(d, can, INK, 2.6, True)
    for wy in D['wheels']:                                                         # fender arches
        for sg in (1, -1):
            line(d, smooth([(sg * 0.88, wy - 0.12), (sg * 0.72, wy - 0.065), (sg * 0.67, wy), (sg * 0.72, wy + 0.065),
                            (sg * 0.88, wy + 0.12)], 60), INK, 1.6)
    for y in D['shuts']:                                                           # door / bonnet shut lines on the flanks
        for sg in (1, -1):
            xo = float(np.interp(y, [p[1] for p in D['body']], [p[0] for p in D['body']]))
            line(d, [(sg * xo * 0.985, y), (sg * xo * 0.86, y + 0.004)], INK, 1.2)
    for sg in (1, -1):                                                             # mirrors on stalks
        my = D['mirror']; xo = float(np.interp(my, [p[1] for p in D['body']], [p[0] for p in D['body']]))
        line(d, [(sg * xo * 0.9, my + 0.01), (sg * (xo + 0.06), my + 0.012)], INK, 2.6)
        m = smooth([(sg * (xo + 0.04), my - 0.012), (sg * (xo + 0.15), my - 0.008), (sg * (xo + 0.17), my + 0.012),
                    (sg * (xo + 0.13), my + 0.03), (sg * (xo + 0.04), my + 0.028)], 60)
        d.polygon(to_px(np.vstack([m, m[:1]])), fill=PAPER + (255,)); line(d, m, INK, 2, True)
    if key == 'red':
        for sg in (1, -1):
            cr = smooth([(sg * 0.80, 0.11), (sg * 0.74, 0.27), (sg * 0.63, 0.40), (sg * 0.65, 0.55), (sg * 0.79, 0.66),
                         (sg * 0.90, 0.745)], 160)                                 # signature sabre crease (own design)
            line(d, cr, col, 3.2); line(d, scaled(cr, 0.955, 1.0), INK, 0.9)
            line(d, smooth([(sg * 0.42, 0.032), (sg * 0.70, 0.05), (sg * 0.80, 0.085)], 50), INK, 4.2)   # slim lamp
            line(d, smooth([(sg * 0.48, 0.045), (sg * 0.70, 0.06)], 30), col, 1.4)                       # DRL
            for k in range(2):                                                                           # hood vents
                x0 = 0.11 + 0.17 * k
                v = [(sg * x0, 0.10), (sg * (x0 + 0.12), 0.11), (sg * (x0 + 0.12), 0.20), (sg * x0, 0.19)]
                line(d, v, INK, 1.6, True)
                for j in range(1, 5): line(d, [(sg * (x0 + 0.01), 0.10 + 0.018 * j), (sg * (x0 + 0.11), 0.102 + 0.018 * j)], INK, 0.8)
            line(d, smooth([(sg * 0.84, 0.53), (sg * 0.70, 0.57), (sg * 0.68, 0.62), (sg * 0.77, 0.645)], 40), INK, 2)  # haunch intake
            line(d, [(sg * 0.30, 0.968), (sg * 0.70, 0.946)], col, 5)                                    # tail lamps
            line(d, [(sg * 0.84, 0.875), (sg * 0.84, 0.935)], INK, 2.4)                                  # wing end plates
        line(d, smooth([(-0.60, 0.03), (-0.3, 0.008), (0, 0.004), (0.3, 0.008), (0.60, 0.03)], 60), INK, 1.4)  # splitter
        line(d, [(0, 0.03), (0, 0.33)], INK, 0.9)                                                      # bonnet centre line
        eng = [(-0.30, 0.715), (0.30, 0.715), (0.25, 0.86), (-0.25, 0.86)]                               # engine glass + louvres
        d.polygon(to_px(eng), fill=GLASS + (255,)); line(d, eng, INK, 1.6, True)
        for k in range(1, 7):
            y = 0.715 + 0.0206 * k; w = 0.30 - 0.05 * (k / 7)
            line(d, [(-w + 0.02, y), (w - 0.02, y)], INK, 0.9)
        wing = [(-0.84, 0.885), (0.84, 0.885), (0.84, 0.925), (-0.84, 0.925)]
        d.polygon(to_px(wing), fill=PAPER + (255,)); line(d, wing, INK, 2.4, True)
        line(d, [(-0.82, 0.905), (0.82, 0.905)], INK, 0.8)
        for k in range(-3, 4): line(d, [(0.09 * k, 0.978), (0.09 * k, 0.997)], INK, 1.4)               # diffuser fins
    else:
        for sg in (1, -1):
            line(d, smooth([(sg * 0.38, 0.026), (sg * 0.66, 0.045), (sg * 0.86, 0.10)], 50), INK, 3.6)  # lamp blade
            line(d, smooth([(sg * 0.42, 0.036), (sg * 0.66, 0.052)], 30), col, 1.3)
            line(d, [(sg * 0.30, 0.022), (sg * 0.52, 0.042)], INK, 1.6)                                   # front intake slit
            line(d, smooth([(sg * 0.14, 0.76), (sg * 0.30, 0.87), (sg * 0.46, 0.965)], 60), INK, 1.8)    # flying buttress
            line(d, smooth([(sg * 0.90, 0.47), (sg * 0.74, 0.52), (sg * 0.70, 0.60)], 40), INK, 2)       # side scoop
            line(d, smooth([(sg * 0.22, 0.05), (sg * 0.30, 0.16), (sg * 0.36, 0.22)], 40), INK, 1.0)     # bonnet creases
        line(d, smooth(mirror([(0, 0.085), (0.16, 0.09), (0.20, 0.13), (0.14, 0.17), (0, 0.175)]), 80), INK, 1.6, True)
        line(d, [(0, 0.80), (0, 0.965)], INK, 1.0)
        for k in range(-4, 5): line(d, [(0.08 * k, 0.982), (0.08 * k, 0.998)], INK, 1.2)              # diffuser
        lb = [(x, 0.972 - 0.03 * x * x) for x in np.linspace(-0.86, 0.86, 80)]                         # full-width light bar
        line(d, lb, col, 6.5); line(d, [(x, y + 0.008) for x, y in lb], INK, 0.8)
    line(d, body, INK, 3.6, True)                                                  # silhouette last, heaviest
    out = im.resize(((CAR_W + 2 * PAD) * S2, (CAR_L + 2 * PAD) * S2), Image.LANCZOS)
    wheels = []
    for wy in D['wheels']:
        for sg in (1, -1):
            wheels.append((PAD + (CAR_W / 2) * (1 + sg * D['wx']), PAD + CAR_L * wy, sg))
    return out, wheels


WH_W, WH_L = 58, 146                                          # tyre footprint (px)


def draw_wheels(d, key, ox, oy, t):
    """Tyres poke out under the body; tread lines roll with the car; inner disc edge glows when hot."""
    c = CARS[key]; ph = (dist(c, t) * PXM * 0.6) % 24
    for cx, cy, sg in WHEELS[key]:
        x0, y0 = (ox + cx - WH_W / 2 + sg * 6) * S2, (oy + cy - WH_L / 2) * S2
        x1, y1 = x0 + WH_W * S2, y0 + WH_L * S2
        d.rounded_rectangle([x0, y0, x1, y1], 10 * S2, fill=PAPER, outline=INK, width=4 * S2)
        for k in range(8):
            y = y0 + ((k * 24 + ph) % (WH_L - 12) + 6) * S2
            d.line([x0 + 8 * S2, y, x1 - 8 * S2, y], fill=INK, width=2 * S2)


def glow_layer(key, ox, oy, h):
    """Orange glow at the inside of each wheel (brake disc), strength = heat."""
    if h < 0.02: return None
    g = Image.new('RGBA', (W * S2, H * S2), (0, 0, 0, 0)); d = ImageDraw.Draw(g)
    for cx, cy, sg in WHEELS[key]:
        x = (ox + cx + sg * 20) * S2; y = (oy + cy) * S2
        for r, a in ((80, 55), (60, 110), (42, 185)):
            rr = r * S2 * (0.7 + 0.3 * h)
            d.ellipse([x - rr * 0.6, y - rr, x + rr * 0.6, y + rr], fill=(255, int(150 - 90 * h), 20, int(a * h)))
    return g.filter(ImageFilter.GaussianBlur(10 * S2))


for _d in DESIGN.values(): _d['body_full'] = smooth(mirror(_d['body']), 500)
SPRITES, WHEELS = {}, {}
for _k in CARS: SPRITES[_k], WHEELS[_k] = build_car(_k)


# ---------------------------------------------------------------- track (lane lines, kerbs, 4 faint outlines)
X_L, X_R, X_MID = 90, 910, 505


def scroll(key, t): return dist(CARS[key], t) * PXM


def draw_track(d, t):
    d.line([X_L * S2, 0, X_L * S2, H * S2], fill=INK, width=3 * S2)
    d.line([X_R * S2, 0, X_R * S2, H * S2], fill=INK, width=3 * S2)
    for key, x, kx in (('red', X_MID - 13, X_L - 30), ('blue', X_MID + 13, X_R)):
        s = scroll(key, t); col = CARS[key]['col']
        for k in range(-1, H // 160 + 2):                                        # lane dashes (one set per lane)
            y = (k * 160 + s) % (H + 160) - 160
            d.line([x * S2, y * S2, x * S2, (y + 80) * S2], fill=INK, width=4 * S2)
        for k in range(-1, H // 60 + 2):                                         # kerb stripes
            y = (k * 60 + s) % (H + 120) - 60
            d.rectangle([kx * S2, y * S2, (kx + 30) * S2, (y + 30) * S2], fill=col)
            d.rectangle([kx * S2, (y + 30) * S2, (kx + 30) * S2, (y + 60) * S2], fill=PAPER, outline=None)
        d.rectangle([kx * S2, 0, (kx + 30) * S2, H * S2], outline=INK, width=2 * S2)


def ghost_layer(t):
    """Four faint outlines at the edges (grandstand left, three trees right), 20 % opacity, scrolling with the lanes."""
    g = Image.new('RGBA', (W * S2, H * S2), (0, 0, 0, 0)); d = ImageDraw.Draw(g)
    sr, sb = scroll('red', t), scroll('blue', t); P = 2600
    y = (sr * 0.9) % P - 700                                                      # grandstand: tiers of seats, top-down
    d.rectangle([-40 * S2, y * S2, 52 * S2, (y + 560) * S2], outline=INK, width=3 * S2)
    for k in range(1, 7): d.line([-40 * S2, (y + 80 * k) * S2, 52 * S2, (y + 80 * k) * S2], fill=INK, width=2 * S2)
    for i, off in enumerate((0, 870, 1730)):                                      # trees: scalloped crowns
        y = (sb * 0.9 + off) % P - 300; cx = 1010 + 24 * (i % 2); r = 66
        pts = []
        for a in np.linspace(0, 2 * math.pi, 120):
            rr = r * (1 + 0.09 * math.cos(9 * a))
            pts.append(((cx + rr * math.cos(a)) * S2, (y + rr * math.sin(a)) * S2))
        d.line(pts + pts[:1], fill=INK, width=3 * S2)
        d.ellipse([(cx - 10) * S2, (y - 10) * S2, (cx + 10) * S2, (y + 10) * S2], outline=INK, width=2 * S2)
    a = np.asarray(g).copy(); a[..., 3] = (a[..., 3] * 0.2).astype(np.uint8)
    return Image.fromarray(a)


def draw_speedlines(d, t):
    """Speed streaks beside each car while fast (cold open), fading with speed."""
    rng = np.random.default_rng(3)
    for key in CARS:
        c = CARS[key]; v = vnow(c, t) / 400
        if v < 0.08: continue
        s = scroll(key, t) * 1.4; x0 = c['cx'] - CAR_W / 2 - 20
        for k in range(9):
            x = x0 + rng.uniform(-30, CAR_W + 40); ln = 120 + 260 * v
            y = (rng.uniform(0, 2400) + s) % 2400 - 300
            g = int(lerp(250, 150, v))
            d.line([x * S2, y * S2, x * S2, (y + ln) * S2], fill=(g, g, g + 4), width=int(3 * S2))


# ---------------------------------------------------------------- text (readable on a phone)
BOXES = []


def text(d, xy, s, f, col=INK, anchor='la', sc=1.0, box=True):
    if sc <= 0: return None
    f2 = font(f.path, max(4, int(f.size * sc * S2)))
    d.text((xy[0] * S2, xy[1] * S2), s, font=f2, fill=col, anchor=anchor, stroke_width=(5 * S2 if col != PAPER else 0), stroke_fill=PAPER)
    bb = d.textbbox((xy[0] * S2, xy[1] * S2), s, font=f2, anchor=anchor); bb = tuple(v / S2 for v in bb)
    if box: BOXES.append((s, f.size, bb))
    return bb


def zoom(t): return 1 + 0.08 * ss((t - T_QK - 0.3) / 3.0)                     # slow push-in once both have stopped


def clock_block(d, key, t):
    c = CARS[key]; right = key == 'blue'; z = zoom(t)
    top = 1300 + (car_top(key, t) - 1300) * z                                     # tags follow the zoomed cars
    x = c['cx'] + CAR_W / 2 if right else c['cx'] - CAR_W / 2; an = 'r' if right else 'l'
    x = min(905, max(60, 540 + (x - 540) * z))
    hi = T_CH if key == 'red' else T_NE
    sc = 1 + 0.12 * math.sin(math.pi * min(1, max(0, (t - hi) / 0.4)))           # name pulses when the voice says it
    if key == 'blue': sc += 0.12 * math.sin(math.pi * min(1, max(0, (t - T_PARK) / 0.4)))   # "already parked"
    text(d, (x, top - 100), c['name'], font(FONT, 62), c['col'], an + 's', sc)
    cl = tau(c, t); s = f'{cl:05.2f} s'; f = font(FONT_M, 72)
    if t >= c['stop']:
        p = 1 + 0.15 * math.sin(math.pi * min(1, (t - c['stop']) / 0.3))
        f2 = font(FONT_M, int(72 * p * S2))
        bb = d.textbbox((x * S2, (top - 26) * S2), s, font=f2, anchor=an + 's')
        d.rounded_rectangle([bb[0] - 14 * S2, bb[1] - 10 * S2, bb[2] + 14 * S2, bb[3] + 12 * S2], 10 * S2, fill=c['col'])
        text(d, (x, top - 26), s, f, PAPER, an + 's', p)
    else:
        text(d, (x, top - 26), s, f, INK, an + 's')
    return top - 26


def gap_marker(d, t, yr, yb):
    """'12 s' between the two clocks on the word 'twelve'."""
    s = pop(t, T_12, 0.3)
    if s <= 0: return
    xa, xb = CARS['red']['cx'] - CAR_W / 2 + 312, CARS['blue']['cx'] + CAR_W / 2 - 312
    ym = (yr + yb) / 2 - 30; cx = (xa + xb) / 2
    d.line([xa * S2, (yr - 30) * S2, cx * S2, ym * S2, xb * S2, (yb - 30) * S2], fill=INK, width=3 * S2, joint='curve')
    f = font(FONT, 58); f2 = font(FONT, int(58 * s * S2))
    bb = d.textbbox((cx * S2, ym * S2), '12 s', font=f2, anchor='mm')
    d.rounded_rectangle([bb[0] - 10 * S2, bb[1] - 10 * S2, bb[2] + 10 * S2, bb[3] + 10 * S2], 12 * S2, fill=INK)
    text(d, (cx, ym), '12 s', f, PAPER, 'mm', s)


def panel(d, t):
    q = t >= T_Q
    if not q:
        text(d, (108, 230), 'WHICH STOPS', font(FONT, 104))
        text(d, (108, 342), 'FIRST?', font(FONT, 104))
        d.line([112 * S2, 458 * S2, 112 * S2 + 400 * S2 * ss(t / 0.6 + 0.4), 458 * S2], fill=INK, width=8 * S2)
        a = pop(t, wt('same'), 0.3)                                             # caption on "same test"
        text(d, (108, 480), 'separate record runs', font(FONT_B, 60), GREY, sc=a)
        text(d, (108, 548), 'side by side = schematic', font(FONT_B, 60), GREY, sc=a)
    else:
        text(d, (108, 236), 'WOULD YOU TAKE', font(FONT, 74), sc=pop(t, T_Q, 0.25))
        text(d, (108, 336), 'THE ELECTRIC ONE?', font(FONT, 74), BLUE, sc=pop(t, T_EL, 0.25))
        for k, (lab, x, col) in enumerate((('YES', 108, BLUE), ('NO', 462, RED))):
            s = pop(t, T_EL + 0.15 + 0.12 * k, 0.25)
            if s <= 0: continue
            w, h = 300 * s, 112 * s; cx, cy = x + 150, 520
            d.rounded_rectangle([(cx - w / 2 + 8) * S2, (cy - h / 2 + 10) * S2, (cx + w / 2 + 8) * S2, (cy + h / 2 + 10) * S2], 18 * S2, fill=INK)
            d.rounded_rectangle([(cx - w / 2) * S2, (cy - h / 2) * S2, (cx + w / 2) * S2, (cy + h / 2) * S2], 18 * S2, fill=PAPER, outline=INK, width=6 * S2)
            text(d, (cx, cy), lab, font(FONT, 66), col, 'mm', s)
    text(d, (905, 472), 'Yub', font(FONT_B, 58), (150, 150, 158), 'ra')


# ---------------------------------------------------------------- frame
def render(t):
    BOXES.clear()
    img = Image.new('RGBA', (W * S2, H * S2), PAPER + (255,)); d = ImageDraw.Draw(img)
    draw_track(d, t)
    img.alpha_composite(ghost_layer(t)); d = ImageDraw.Draw(img)
    draw_speedlines(d, t)
    for key in CARS:
        c = CARS[key]; ox, oy = c['cx'] - CAR_W / 2 - PAD, car_top(key, t) - PAD
        draw_wheels(d, key, ox, oy, t)
        g = glow_layer(key, ox, oy, heat(c, t))                               # under the body: spills round the tyres
        if g is not None: img.alpha_composite(g)
        img.alpha_composite(SPRITES[key], (int(ox * S2), int(oy * S2)))
        d = ImageDraw.Draw(img)
    z = zoom(t)
    if z > 1.0005:
        cx, cy = 540 * S2, 1300 * S2
        img = img.transform(img.size, Image.AFFINE, (1 / z, 0, cx - cx / z, 0, 1 / z, cy - cy / z), Image.BICUBIC)
    d = ImageDraw.Draw(img)
    panel(d, t)
    yr = clock_block(d, 'red', t); yb = clock_block(d, 'blue', t)
    if t < T_Q: gap_marker(d, t, yr, yb)
    return img.convert('RGB').reduce(S2)


F0 = None


def frame(t):
    global F0
    a = np.asarray(render(t))
    if t >= LOOP0:                                                               # dissolve back into frame 1
        if F0 is None: F0 = np.asarray(render(0.0)).astype(np.float32)
        k = ss((t - LOOP0) / (DUR - 1 / FPS - LOOP0))
        a = (a.astype(np.float32) * (1 - k) + F0 * k).astype(np.uint8)
    return a


# ---------------------------------------------------------------- audio: VO + music 18 dB under, layered SFX, -14 LUFS
def _v(key, n): return np.interp(np.arange(n) / SR, _TS, CARS[key]['kmh'])


def audio(path):
    n = int(DUR * SR); t = np.arange(n) / SR
    vo = np.zeros(n); add(vo, 0, read_wav(v1.VO_WAV))
    mus = np.zeros(n); add(mus, 0, read_wav(v1.MUSIC_WAV))
    L_vo, L_mu = lufs(vo), lufs(mus)
    mus *= 10 ** ((L_vo - 18 - L_mu) / 20)
    fo = np.clip((DUR - t) / 1.6, 0, 1); mus *= fo * fo * np.clip(t / 0.05, 0, 1)
    vr, vb = _v('red', n), _v('blue', n)
    g = np.clip(np.searchsorted(v1.GEARS, vr, side='right') - 1, 0, 4)          # red: growl, blips down the gears
    lo, hi = np.take(v1.GEARS, g), np.take(v1.GEARS, g + 1)
    fr = np.clip((vr - lo) / (hi - lo), 0, 1)
    ph = np.cumsum(np.where(vr < 1, 34.0, 52 + 70 * fr + 7 * g)) / SR
    eng = (sfx.lp(2 * (ph % 1) - 1, 8) * (1 + 0.35 * np.sin(np.pi * ph)) + 0.6 * np.sin(np.pi * ph)) * sfx.lp(np.where(vr < 1, 0.2, 0.5), 2400)
    ph = np.cumsum(160 + 2400 * (vb / 400) ** 0.9) / SR                          # blue: inverter whine
    ev = (np.sin(2 * np.pi * ph) + 0.35 * np.sin(4 * np.pi * ph)) * sfx.lp(np.where(vb < 1, 0, 0.1 + 0.2 * np.sqrt(vb / 400)), 2400)
    wind = v1.bp_noise(n, 24, 260) * 1.6 * (np.maximum(vr, vb) / 400) ** 2
    hiss = sum(v1.bp_noise(n, 6, 30) * 0.35 * ((t >= T_B) & (v > 1)) * np.sqrt(v / 400) for v in (vr, vb))
    bed = eng + 0.8 * ev + 0.9 * wind + 0.8 * hiss
    duck = 1 - 0.65 * np.clip(sfx.lp(np.abs(vo), 4800) / (np.percentile(sfx.lp(np.abs(vo), 4800), 90) + 1e-9), 0, 1)
    bed *= sfx.lp(duck, 2400)
    fx = np.zeros(n)
    evs = [(T_B - 0.05, sfx.screech(0.5) * 0.8), (T_B, sfx.whoosh(0.5, 10) * .5),
           (T_30 - 0.45, sfx.screech(0.5) * 1.4), (T_30, sfx.thump() * .9), (T_30, sfx.ding(1568, 0.5) * .5),
           (T_12 - 1.0, v1.riser(1.0) * .5), (T_12, sfx.stamp() * .6), (T_12, sfx.boom(1.0) * .4),
           (T_QK - 0.45, sfx.screech(0.5) * 1.4), (T_QK, sfx.thump() * 1.0), (T_QK, sfx.ding(1175, 0.6) * .5),
           (wt('same'), v1.blip(1800) * .4), (T_CH, v1.blip(2200) * .3), (T_NE, v1.blip(2600) * .3),
           (T_Q, sfx.pop() * .4), (T_EL + 0.15, sfx.pop() * .5), (T_EL + 0.27, sfx.pop() * .5), (LOOP0, sfx.whoosh(0.5, 16) * .4)]
    for t0, s in evs: add(fx, int(t0 * SR), s)
    fx *= 10 ** ((L_vo - 12 - lufs(fx)) / 20)
    bed *= 10 ** ((L_vo - 11 - lufs(bed)) / 20)
    mix = vo + mus + fx + bed
    gn = 10 ** ((-13.4 - lufs(mix)) / 20); mix *= gn
    if np.abs(mix).max() > 0.89: mix = np.tanh(mix / 0.89) * 0.89
    write_wav(path, mix)
    print(f'audio: vo {L_vo:.1f} LUFS, music {L_vo - 18 - L_mu:+.1f} dB, mix gain {20 * math.log10(gn):+.1f} dB')


# ---------------------------------------------------------------- checks + main
def scan():
    """Layout: every text inside 12-62 % height and the left 85 % width, font >= 3 % of height; element count."""
    bad, small, counts = [], set(), {}
    for i in range(int(DUR * FPS)):
        t = i / FPS; BOXES.clear()
        img = Image.new('RGBA', (W * S2, H * S2)); d = ImageDraw.Draw(img)
        panel(d, t); yr = clock_block(d, 'red', t); yb = clock_block(d, 'blue', t)
        if t < T_Q: gap_marker(d, t, yr, yb)
        for s, size, b in BOXES:
            if b[1] < 0.12 * H - 1 or b[3] > 0.62 * H or b[0] < 0 or b[2] > 0.85 * W: bad.append((round(t, 2), s, [int(v) for v in b]))
            if size < MINPX: small.add((s, size))
        names = {s for s, _, _ in BOXES}
        n = 2 + (('WHICH STOPS' in names) + ('separate record runs' in names) + ('Yub' in names) + 2 + 2
                 + (t >= T_12 and t < T_Q) + ('WOULD YOU TAKE' in names) + ('YES' in names) + ('NO' in names))
        counts[n] = counts.get(n, 0) + 1
    print('anchors', dict(brake=T_B, blue_stop=round(T_30, 2), gap=round(T_12, 2), red_stop=round(T_QK, 2), q=round(T_Q, 2)))
    print('schematic split (record s)', {k: (round(c['A'], 2), round(c['B'], 2)) for k, c in CARS.items()})
    print('clocks on frame 1', {k: round(tau(c, 0), 2) for k, c in CARS.items()}, 'km/h', {k: round(kmh(c, 0)) for k, c in CARS.items()})
    print('layout violations:', len(bad), bad[:4]); print('fonts under 3 %:', sorted(small))
    print('elements per frame (count: frames):', dict(sorted(counts.items())))


def main():
    mode = sys.argv[1]
    if mode == 'scan': return scan()
    if mode == 'still':
        out = Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
        for s in sys.argv[3:]: Image.fromarray(frame(float(s))).save(out / f'f_{s}.png')
        return
    dst = Path(sys.argv[2]); dst.parent.mkdir(parents=True, exist_ok=True)
    t_end = float(sys.argv[3]) if len(sys.argv) > 3 else DUR
    wav = dst.with_suffix('.wav'); audio(wav)
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS),
                          '-i', '-', '-i', str(wav), '-t', str(t_end), '-c:v', 'libx264', '-crf', '18', '-pix_fmt', 'yuv420p',
                          '-ar', '48000', '-c:a', 'aac', '-b:a', '192k', '-shortest', str(dst)], stdin=subprocess.PIPE)
    for i in range(int(round(t_end * FPS))): p.stdin.write(frame(i / FPS).tobytes())
    p.stdin.close(); sys.exit(p.wait())


if __name__ == '__main__':
    main()
