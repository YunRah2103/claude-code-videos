"""car_evolution world: dark cinematic studio stage, the ONE car that grows stage by stage (0 Benz 1886 -> 1 brass/crank ->
2 Ford Model T -> 3 Volvo 1959 seatbelt -> 4 Oldsmobile 1977 chip -> 5 modern Tesla), brand badges, props, the llama oddity.
Car faces +x, y up, ground y = 0. All static meshes are cached and copied per frame."""
import math
from functools import lru_cache
import _lib  # noqa: F401
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from geo import (P, cat, quad, box, bbox, cb, lathe, cyl, superellipsoid, sphere, capsule, tube, tex, word_tex, font, rgb,
                 MATTE, PAINT, GLASS, CHROME, SATIN, RUBBER, GLOW, SCREEN, CLOTH, T_DISC, T_BEAM)
from render3d import Env
import cars3d as C
import props3d as PR

def ease(u): u = min(max(u, 0.0), 1.0); return u * u * (3 - 2 * u)
def ease3(u): u = min(max(u, 0.0), 1.0); return u * u * u * (u * (6 * u - 15) + 10)          # smootherstep
def eout(u): u = min(max(u, 0.0), 1.0); return 1 - (1 - u) ** 3
def ein(u): u = min(max(u, 0.0), 1.0); return u ** 3
def back(u, s=1.6): u = min(max(u, 0.0), 1.0); u -= 1; return 1 + u * u * ((s + 1) * u + s)    # overshoot settle
def seg(t, a, b): return min(max((t - a) / max(b - a, 1e-6), 0.0), 1.0)
def lerp(a, b, u): return tuple(x + (y - x) * u for x, y in zip(a, b))
def mix(a, b, u): return a + (b - a) * u

# ---------------------------------------------------------------- environment
ACC = {0: (255, 176, 60), 1: (255, 70, 80), 2: (70, 140, 255), 3: (80, 240, 190), 4: (255, 130, 40), 5: (90, 220, 255)}
def env(acc=(90, 200, 255), **kw):
    d = dict(sky_top=(6, 9, 24), sky_hor=(26, 34, 78), ground=(14, 14, 24), sun_dir=(-0.35, 0.85, 0.4), sun=(225, 232, 255), sun_i=2.1,
             amb_i=0.9, fog=(12, 48), fog_col=(16, 22, 50), exposure=1.06, stars=0.25, bloom=0.95, sun_disc=False, sat=1.18,
             shadow_size=9.0, ao=0.9,
             points=[((-3.0, 2.2, 2.5), acc, 1.6, 3.0), ((3.6, 2.4, -3.2), (255, 80, 200), 0.45, 2.5)])
    d.update(kw); return Env(**d)

@lru_cache(None)
def _floor():
    out = [quad((-40, 0, 40), (40, 0, 40), (40, 0, -40), (-40, 0, -40), (20, 22, 34), m=PAINT)]
    return cat(out)

def floor(t=0.0, v=0.0, acc=(90, 200, 255), grid=0.22):
    """Glossy dark floor + faint glowing grid (scrolls with speed v along -x)."""
    s = [_floor().copy()]
    off = (v * t) % 1.5
    g = []
    for x in np.arange(-15, 15.01, 1.5):
        xx = x - off
        g.append(quad((xx - 0.012, 0.003, 12), (xx + 0.012, 0.003, 12), (xx + 0.012, 0.003, -14), (xx - 0.012, 0.003, -14), acc, e=grid, m=GLOW))
    for z in np.arange(-13.5, 12.01, 1.5):
        g.append(quad((-15, 0.003, z + 0.012), (15, 0.003, z + 0.012), (15, 0.003, z - 0.012), (-15, 0.003, z - 0.012), acc, e=grid, m=GLOW))
    s.append(cat(g).rot("x", 180).rot("x", 180))
    return s

@lru_cache(None)
def _turntable():
    top = lathe([(0.0, 0.1), (2.5, 0.1), (2.6, 0.07), (2.62, 0.0)], 48, (34, 36, 48), SATIN)
    rim = lathe([(2.63, 0.0), (2.63, 0.06)], 64, (255, 255, 255), GLOW)
    return top, rim

def turntable(acc, e=2.2, rot=0.0):
    top, rim = _turntable()
    r = rim.copy(); r.c[:] = rgb(acc); r.e[:] = e
    inner = lathe([(1.9, 0.102), (1.93, 0.102)], 64, acc, GLOW).glow(e * 0.5)
    return [top.copy().rot("y", rot), r, inner]

def beams(acc=(120, 180, 255), e=0.07):
    return [PR.beam((x, 9.5, z), (-0.08 * x, -1, 0.05), 11, 2.6, acc, e) for x, z in ((-3.2, -2.5), (0.2, -3.5), (3.5, -2.0))]

def dust(t, n=26, seed=3, box_=(-5, 0.3, -5, 5, 4.0, 3), col=(200, 220, 255)):
    r = np.random.default_rng(seed); out = []
    for i in range(n):
        x = r.uniform(box_[0], box_[3]); y = r.uniform(box_[1], box_[4]); z = r.uniform(box_[2], box_[5]); ph = r.uniform(0, 6.28)
        out.append(((x + 0.15 * math.sin(t * 0.4 + ph), y + 0.12 * math.sin(t * 0.3 + ph * 2), z), col, 0.018, 0.5 + 0.3 * math.sin(t + ph)))
    return out

# ---------------------------------------------------------------- textures: brand badges
def _canvas(w, h, bg=(0, 0, 0)): im = Image.new("RGB", (w * 4, h * 4), bg); return im, ImageDraw.Draw(im)
def _done(im, w, h): return tex(im.resize((w, h), Image.LANCZOS))
def _f(size, path="/usr/share/fonts/opentype/inter/Inter-Black.otf"): return ImageFont.truetype(path, size)
F_IT = "/usr/share/fonts/opentype/inter/Inter-BlackItalic.otf"

def _benz():
    w, h = 160, 112; im, d = _canvas(w, h, (40, 30, 20)); W_, H_ = w * 4, h * 4
    d.ellipse((8, 8, W_ - 8, H_ - 8), fill=(236, 222, 186), outline=(150, 110, 40), width=18)
    for sg in (-1, 1):                                                       # laurel wreath
        for k in range(9):
            a = math.radians(200 - k * 16) if sg < 0 else math.radians(-20 + k * 16)
            cx = W_ / 2 + math.cos(a) * W_ * 0.36 * sg * -1 if False else W_ / 2 + math.cos(a) * W_ * 0.37
            cy = H_ / 2 + math.sin(a) * H_ * 0.33
            d.ellipse((cx - 22, cy - 11, cx + 22, cy + 11), fill=(70, 130, 60))
    d.text((W_ / 2, H_ / 2), "BENZ", font=_f(150), fill=(30, 26, 22), anchor="mm")
    return _done(im, w, h)

def _caddy():
    w, h = 128, 160; im, d = _canvas(w, h, (20, 16, 14)); W_, H_ = w * 4, h * 4
    d.ellipse((30, 20, W_ - 30, H_ * 0.66), fill=(196, 160, 70))                 # wreath
    d.ellipse((60, 50, W_ - 60, H_ * 0.62), fill=(20, 16, 14))
    sh = [(W_ * 0.28, H_ * 0.12), (W_ * 0.72, H_ * 0.12), (W_ * 0.72, H_ * 0.42), (W_ * 0.5, H_ * 0.58), (W_ * 0.28, H_ * 0.42)]
    d.polygon(sh, fill=(20, 20, 24))
    quarters = [((W_ * 0.28, H_ * 0.12, W_ * 0.5, H_ * 0.3), (230, 190, 60)), ((W_ * 0.5, H_ * 0.12, W_ * 0.72, H_ * 0.3), (20, 20, 24)),
                ((W_ * 0.28, H_ * 0.3, W_ * 0.5, H_ * 0.5), (200, 30, 40)), ((W_ * 0.5, H_ * 0.3, W_ * 0.72, H_ * 0.5), (40, 80, 200))]
    for r, c in quarters: d.rectangle(r, fill=c)
    for k in range(4): d.line((W_ * 0.3 + k * 30, H_ * 0.14, W_ * 0.3 + k * 30 + 60, H_ * 0.28), fill=(20, 20, 24), width=8)
    m = Image.new("L", im.size, 0); ImageDraw.Draw(m).polygon(sh, fill=255)
    bg = Image.new("RGB", im.size, (20, 16, 14)); ImageDraw.Draw(bg).ellipse((30, 20, W_ - 30, H_ * 0.66), fill=(196, 160, 70))
    ImageDraw.Draw(bg).ellipse((60, 50, W_ - 60, H_ * 0.62), fill=(20, 16, 14))
    im = Image.composite(im, bg, m); d = ImageDraw.Draw(im)
    d.text((W_ / 2, H_ * 0.82), "Cadillac", font=_f(96, F_IT), fill=(240, 232, 210), anchor="mm")
    return _done(im, w, h)

def _ford():
    w, h = 192, 80; im, d = _canvas(w, h, (0, 0, 0)); W_, H_ = w * 4, h * 4
    d.ellipse((6, 6, W_ - 6, H_ - 6), fill=(236, 238, 245)); d.ellipse((22, 22, W_ - 22, H_ - 22), fill=(16, 52, 150))
    d.text((W_ / 2, H_ / 2 + 6), "Ford", font=_f(210, F_IT), fill=(250, 250, 255), anchor="mm")
    return _done(im, w, h)

def _volvo():
    w, h = 128, 128; im, d = _canvas(w, h, (10, 12, 18)); W_, H_ = w * 4, h * 4; c = W_ / 2
    d.ellipse((60, 60, W_ - 60, H_ - 60), outline=(210, 214, 222), width=40)
    d.line((c + 130, c - 130, c + 215, c - 215), fill=(210, 214, 222), width=40)
    d.polygon([(c + 240, c - 240), (c + 120, c - 230), (c + 230, c - 120)], fill=(210, 214, 222))
    d.rectangle((0, c - 52, W_, c + 52), fill=(20, 50, 130)); d.text((c, c), "VOLVO", font=_f(92), fill=(235, 238, 245), anchor="mm")
    return _done(im, w, h)

def _olds():
    w, h = 192, 96; im, d = _canvas(w, h, (16, 14, 12)); W_, H_ = w * 4, h * 4
    d.ellipse((W_ / 2 - 120, 20, W_ / 2 + 120, 260), outline=(225, 190, 110), width=14)                   # globe ring
    d.polygon([(W_ / 2 + 110, 40), (W_ / 2 - 60, 220), (W_ / 2 - 20, 236), (W_ / 2 + 130, 60)], fill=(240, 205, 120))   # rocket
    d.polygon([(W_ / 2 - 60, 220), (W_ / 2 - 100, 236), (W_ / 2 - 20, 236)], fill=(255, 120, 40))
    d.text((W_ / 2, H_ - 70), "OLDSMOBILE", font=_f(82), fill=(240, 228, 200), anchor="mm")
    return _done(im, w, h)

def _tesla():
    w, h = 96, 96; im, d = _canvas(w, h, (230, 232, 236)); W_, H_ = w * 4, h * 4; c = W_ / 2
    d.chord((40, 40, W_ - 40, 260), 200, 340, fill=(200, 20, 30))
    d.polygon([(c - 160, 90), (c + 160, 90), (c + 120, 120), (c - 120, 120)], fill=(200, 20, 30))
    d.polygon([(c - 26, 120), (c + 26, 120), (c + 18, 340), (c, 360), (c - 18, 340)], fill=(200, 20, 30))
    return _done(im, w, h)

T_BENZ = _benz(); T_CADDY = _caddy(); T_FORD = _ford(); T_VOLVO = _volvo(); T_OLDS = _olds(); T_TESLA = _tesla()
BADGE = {0: (T_BENZ, 0.36, 0.25), 1: (T_CADDY, 0.2, 0.25), 2: (T_FORD, 0.36, 0.15), 3: (T_VOLVO, 0.24, 0.24), 4: (T_OLDS, 0.36, 0.18)}

def badge(stage, w=None):
    tid, bw, bh = BADGE[stage]
    if w: bh = bh * w / bw; bw = w
    return cat([cb(0, 0, -0.012, bw + 0.03, bh + 0.03, 0.02, (210, 180, 100), b=0.008, m=CHROME),
                quad((-bw / 2, -bh / 2, 0.0), (bw / 2, -bh / 2, 0.0), (bw / 2, bh / 2, 0.0), (-bw / 2, bh / 2, 0.0), (255, 255, 255), tid, 0.15, m=SATIN)])

# ---------------------------------------------------------------- wheels
@lru_cache(None)
def _spoke_wheel(R, n, wd, style):
    """Wheel in the XY plane, axle along z, centred on origin. style 'wire' (Benz), 'wood' (artillery), 'steel' (disc)."""
    if style == "wire":
        rim = lathe([(R - 0.03, -wd / 2), (R, -wd / 2), (R, wd / 2), (R - 0.03, wd / 2), (R - 0.03, -wd / 2)], 40, (30, 30, 34), RUBBER).rot("x", 90)
        felloe = lathe([(R - 0.05, -0.012), (R - 0.03, -0.012), (R - 0.03, 0.012), (R - 0.05, 0.012)], 40, (190, 150, 70), CHROME).rot("x", 90)
        hub = cyl(0.05, 0.05, wd * 1.6, 14, (190, 150, 70), CHROME).rot("x", 90).mv(0, 0, wd * 0.8)
        sp = [capsule((0, 0, sg * 0.03), ((R - 0.05) * math.cos(a), (R - 0.05) * math.sin(a), 0), 0.007, 5, (200, 200, 205), CHROME)
              for k, a in enumerate(np.linspace(0, 2 * math.pi, n, endpoint=False)) for sg in ((1,) if k % 2 else (-1,))]
        return cat([rim, felloe, hub] + sp)
    if style == "wood":
        tyre = lathe([(R - 0.06, -wd / 2), (R - 0.01, -wd / 2), (R, 0), (R - 0.01, wd / 2), (R - 0.06, wd / 2)], 40, (26, 26, 28), RUBBER, angle=70).rot("x", 90)
        felloe = lathe([(R - 0.1, -0.03), (R - 0.06, -0.03), (R - 0.06, 0.03), (R - 0.1, 0.03), (R - 0.1, -0.03)], 40, (176, 120, 60), SATIN).rot("x", 90)
        hub = cyl(0.08, 0.08, 0.12, 16, (200, 170, 90), CHROME).rot("x", 90).mv(0, 0, 0.06)
        sp = [capsule((0.06 * math.cos(a), 0.06 * math.sin(a), 0), ((R - 0.09) * math.cos(a), (R - 0.09) * math.sin(a), 0), 0.022, 6, (186, 128, 64), SATIN, r1=0.016)
              for a in np.linspace(0, 2 * math.pi, n, endpoint=False)]
        return cat([tyre, felloe, hub] + sp)
    # steel disc wheel with whitewall
    tyre = lathe([(R * 0.68, -wd / 2), (R - 0.03, -wd / 2), (R, 0), (R - 0.03, wd / 2), (R * 0.68, wd / 2)], 36, (26, 26, 28), RUBBER, angle=70).rot("x", 90)
    ww = lathe([(R * 0.7, wd / 2 + 0.002), (R * 0.86, wd / 2 + 0.002)], 36, (240, 240, 236), SATIN).rot("x", 90)
    disc = cyl(R * 0.68, R * 0.68, 0.02, 32, (255, 255, 255), CHROME, captex=C.T_RIM_TES).rot("x", 90).mv(0, 0, wd / 2 - 0.01)
    return cat([tyre, ww, disc])

def wheel(x, y, z, R, n=12, wd=0.07, style="wire", spin=0.0, side=1):
    w = _spoke_wheel(round(R, 3), n, round(wd, 3), style).copy().rot("z", spin)
    if side < 0: w.rot("y", 180)
    return w.mv(x, y, z)

# ---------------------------------------------------------------- the car
BLACK = (20, 20, 24); BRASS = (214, 168, 74); WOOD = (122, 70, 38); LEATHER = (46, 30, 26)
PAINTS = {0: (28, 26, 30), 1: (130, 14, 30), 2: (18, 18, 22), 3: (120, 206, 178), 4: (178, 86, 28)}
SEAT_Y = 0.98; YUB_X = -0.5

def seat_yub(y, x=YUB_X): return y.rot("y", 90).mv(x, SEAT_Y - 0.5, 0)

@lru_cache(None)
def _static(stage):
    """Everything on the stage-`stage` car that does not move (wheels / crank / flywheel are added per frame)."""
    p = PAINTS[stage]; s = []
    # chassis rails (always)
    for z in (-0.4, 0.4):
        s.append(tube([(-1.12, 0.5, z), (0.3, 0.5, z), (0.75, 0.58, z * (0.3 if stage == 0 else 1)), (0.98 if stage == 0 else 1.18, 0.62, z * (0.12 if stage == 0 else 0.85))], 0.028, 8, (30, 30, 34), SATIN))
    s.append(capsule((-0.55, 0.46, -0.6), (-0.55, 0.46, 0.6), 0.03, 8, (40, 40, 44), SATIN))                    # rear axle
    # seat box (wood on the Benz, painted later)
    box_col = WOOD if stage == 0 else p
    s.append(bbox(-0.9, 0.52, -0.42, -0.12, SEAT_Y - 0.1, 0.42, box_col, b=0.03, m=SATIN if stage == 0 else PAINT))
    s.append(bbox(-0.86, SEAT_Y - 0.12, -0.4, -0.18, SEAT_Y, 0.4, LEATHER, b=0.05, m=SATIN))                       # cushion
    s.append(bbox(-0.94, SEAT_Y - 0.08, -0.42, -0.82, SEAT_Y + 0.42, 0.42, LEATHER, b=0.05, m=SATIN).rot("z", 8, (-0.88, SEAT_Y, 0)))
    s.append(bbox(-0.16, 0.44, -0.34, 0.42, 0.48, 0.34, WOOD if stage < 2 else (40, 40, 44), b=0.015, m=SATIN))      # footboard
    # side badge on the seat box
    s.append(badge(min(stage, 4), 0.3).mv(-0.5, 0.74, 0.425))
    s.append(badge(min(stage, 4), 0.3).rot("y", 180).mv(-0.5, 0.74, -0.425))
    # rear engine (Benz layout kept: it is the same car) + brass evaporator + chains
    s.append(cyl(0.11, 0.11, 0.36, 18, (60, 60, 66), CHROME).rot("z", -90).mv(-1.2, 0.72, 0.1))               # cylinder
    s.append(cb(-0.98, 0.72, 0.1, 0.12, 0.26, 0.26, (70, 70, 76), b=0.03, m=SATIN))                           # crankcase
    s.append(cyl(0.1, 0.1, 0.3, 18, BRASS, CHROME).mv(-1.05, 0.86, -0.2))                                       # evaporator
    for k in range(5): s.append(lathe([(0.115, 0.0), (0.115, 0.015)], 18, BRASS, CHROME).rot("z", -90).mv(-1.18 + 0.07 * k, 0.72, 0.1))
    for z in (-0.52, 0.52):
        s.append(cyl(0.07, 0.07, 0.02, 14, (60, 60, 64), CHROME).rot("x", 90).mv(-0.2, 0.56, z))
        s.append(capsule((-0.2, 0.63, z), (-0.55, 0.6, z), 0.012, 5, (44, 44, 48), SATIN))
        s.append(capsule((-0.2, 0.49, z), (-0.55, 0.33, z), 0.012, 5, (44, 44, 48), SATIN))
    if stage == 0:
        s += [capsule((0.98, 0.3, sg * 0.06), (0.8, 0.78, sg * 0.05), 0.02, 8, (30, 30, 34), SATIN) for sg in (-1, 1)]      # fork
        s.append(capsule((0.8, 0.78, 0), (0.12, 0.7, 0), 0.018, 6, (30, 30, 34), SATIN))                                       # linkage
    else:
        s.append(capsule((1.05, 0.38, -0.56), (1.05, 0.38, 0.56), 0.03, 8, (40, 40, 44), SATIN))                               # front axle
        s += [capsule((1.05, 0.38, sg * 0.4), (1.05, 0.55, sg * 0.4), 0.025, 6, (40, 40, 44), SATIN) for sg in (-1, 1)]
        # bonnet + radiator
        hood = p if stage != 3 else (240, 232, 210)
        s.append(bbox(0.3, 0.52, -0.3, 1.1, 0.98, 0.3, hood, b=0.06, m=PAINT))
        for k in range(5): s += [cb(0.62 + 0.08 * k, 0.78, sg * 0.302, 0.03, 0.18, 0.006, (20, 20, 22), b=0.004) for sg in (-1, 1)]
        rad = BRASS if stage < 3 else (210, 214, 222)
        s.append(bbox(1.1, 0.46, -0.34, 1.2, 1.04, 0.34, rad, b=0.03, m=CHROME))
        s.append(box(1.2, 0.52, -0.28, 1.203, 0.98, 0.28, (16, 16, 18), m=SATIN))
        for k in range(7): s.append(box(1.203, 0.55 + 0.06 * k, -0.27, 1.206, 0.565 + 0.06 * k, 0.27, (70, 70, 74), m=CHROME))
        s.append(badge(min(stage, 4), 0.22).rot("y", 90).mv(1.215, 0.9, 0))
        # firewall / dash
        s.append(bbox(0.26, 0.5, -0.4, 0.32, 1.1, 0.4, p if stage >= 2 else WOOD, b=0.02, m=PAINT))
    if stage <= 1:
        s.append(capsule((0.14, 0.52, 0), (0.06, 1.24, 0), 0.02, 8, (30, 30, 34), SATIN))                         # tiller column
        s.append(capsule((0.06, 1.24, 0), (-0.12, 1.22, 0), 0.016, 8, (30, 30, 34), SATIN))                       # tiller arm
        s.append(capsule((-0.12, 1.22, -0.06), (-0.12, 1.22, 0.06), 0.022, 8, (20, 20, 20), RUBBER))             # grip
    if stage >= 2:
        # fenders + running boards + windscreen + steering wheel + headlamps
        for x, R, yc in ((-0.55, 0.47, 0.47), (1.05, 0.39, 0.38)):
            for sg in (-1, 1):
                arcpts = [(x - (R + 0.06) * math.cos(math.radians(a)), yc + (R + 0.06) * math.sin(math.radians(a)), sg * 0.64)
                          for a in np.linspace(5, 175, 12)]
                for a_, b_ in zip(arcpts, arcpts[1:]):
                    d_ = np.float32(b_) - np.float32(a_); L_ = float(np.linalg.norm(d_)); ang = math.degrees(math.atan2(d_[1], d_[0]))
                    s.append(cb(0, 0, 0, L_ + 0.02, 0.025, 0.2, p, b=0.01, m=PAINT).rot("z", ang).mv(*((np.float32(a_) + np.float32(b_)) / 2)))
        s.append(bbox(-0.12, 0.42, 0.42, 0.68, 0.46, 0.74, (30, 30, 34), b=0.012))
        s.append(bbox(-0.12, 0.42, -0.74, 0.68, 0.46, -0.42, (30, 30, 34), b=0.012))
        s += [capsule((0.3, 1.1, sg * 0.4), (0.24, 1.6, sg * 0.4), 0.014, 6, BRASS if stage == 2 else (210, 214, 222), CHROME) for sg in (-1, 1)]
        s.append(capsule((0.24, 1.6, -0.4), (0.24, 1.6, 0.4), 0.014, 6, BRASS if stage == 2 else (210, 214, 222), CHROME))
        s.append(quad((0.3, 1.1, 0.39), (0.3, 1.1, -0.39), (0.245, 1.59, -0.39), (0.245, 1.59, 0.39), (150, 200, 255), e=0.07, m=GLOW))
        s.append(capsule((0.27, 0.95, 0), (0.02, 1.14, 0), 0.016, 8, (24, 24, 26), SATIN))                         # steering column
        s.append(lathe([(0.15, -0.012), (0.165, 0.0), (0.15, 0.012), (0.135, 0.0), (0.15, -0.012)], 24, (30, 22, 18), SATIN).rot("z", 56).mv(0.0, 1.16, 0))
        for sg in (-1, 1):
            s.append(lathe([(0.0, 0.0), (0.09, 0.02), (0.1, 0.1)], 18, BRASS if stage == 2 else (210, 214, 222), CHROME).rot("z", -90).mv(1.18, 0.96, sg * 0.42))
            s.append(capsule((1.12, 0.62, sg * 0.36), (1.14, 0.96, sg * 0.42), 0.012, 5, (30, 30, 34), SATIN))
    if stage >= 3:
        # chrome bumpers, belt pillar (B-post) behind the seat
        s.append(bbox(1.3, 0.36, -0.62, 1.36, 0.44, 0.62, (220, 224, 232), b=0.02, m=CHROME))
        s.append(bbox(-1.36, 0.36, -0.62, -1.3, 0.44, 0.62, (220, 224, 232), b=0.02, m=CHROME))
        s.append(bbox(-0.98, 0.52, 0.43, -0.9, 1.62, 0.5, p, b=0.02, m=PAINT))
    if stage >= 4:
        s.append(bbox(0.05, 0.98, -0.36, 0.28, 1.12, 0.36, (24, 24, 28), b=0.03, m=SATIN))                      # dash pod
    return cat([q for q in s if q is not None])

def lamps_glow(stage, k=1.0):
    if stage < 2 or k <= 0: return [], []
    g = [C._glow_disc(1.27, 0.96, sg * 0.42, 0.22, (255, 236, 190), 0.9 * k, "x") for sg in (-1, 1)]
    sp = [((1.29, 0.96, sg * 0.42), (255, 230, 180), 0.05, 0.9 * k) for sg in (-1, 1)]
    return g, sp

def flywheel(spin):
    """Big horizontal Benz flywheel at the rear (axis vertical)."""
    fw = _fly().copy().rot("y", spin)
    return fw.mv(-1.05, 0.5, 0.1)
@lru_cache(None)
def _fly():
    return cat([cyl(0.27, 0.27, 0.05, 32, (255, 255, 255), CHROME, captex=C._rim(4, (190, 150, 70), (40, 40, 44), style="solid")),
                lathe([(0.27, 0.0), (0.29, 0.01), (0.29, 0.04), (0.27, 0.05)], 32, BRASS, CHROME)])

def crank(angle=0.0):
    """Hand crank in front of the radiator, rotating about x."""
    return cat([capsule((0, 0, 0), (0.14, 0, 0), 0.016, 8, (60, 60, 64), CHROME), capsule((0.14, 0, 0), (0.14, 0.17, 0), 0.016, 8, (60, 60, 64), CHROME),
                capsule((0.14, 0.17, 0), (0.24, 0.17, 0), 0.026, 8, (30, 22, 18), SATIN)]).rot("x", angle)

def starter(glow=1.0):
    body = cyl(0.075, 0.075, 0.3, 20, (190, 100, 50), CHROME).rot("z", -90)
    bands = [lathe([(0.078, 0), (0.078, 0.02)], 20, (90, 200, 255), GLOW).glow(2.2 * glow).rot("z", -90).mv(0.06 + 0.09 * k, 0, 0) for k in range(3)]
    cap = cb(-0.03, 0, 0, 0.06, 0.12, 0.12, (60, 60, 66), b=0.02, m=SATIN)
    return cat([body, cap] + bands)

def car(stage, t=0.0, spin=0.0, driver=None, crank_on=None, starter_k=0.0, lamps=0.0, lod=False):
    """The one car. stage 0-4 (5 = Tesla, see modern()). Returns (mesh, glow list, sprites)."""
    s = [_static(stage).copy()]
    style = "wire" if stage <= 1 else ("wood" if stage == 2 else "steel")
    Rr = 0.46 if stage < 2 else 0.47; Rf = 0.3 if stage == 0 else 0.38
    nsp = 16 if stage <= 1 else 12
    for sg in (-1, 1):
        s.append(wheel(-0.55, Rr, sg * 0.64, Rr, nsp * (2 if stage <= 1 else 1), 0.06 if stage <= 1 else 0.1, style, spin, sg))
    if stage == 0: s.append(wheel(0.98, Rf, 0, Rf, 24, 0.05, "wire", spin * Rr / Rf, 1))
    else:
        for sg in (-1, 1): s.append(wheel(1.05, Rf, sg * 0.6, Rf, nsp * (2 if stage <= 1 else 1), 0.06 if stage <= 1 else 0.1, style, spin * Rr / Rf, sg))
    s.append(flywheel(spin * 3.0))
    if crank_on is not None: s.append(crank(crank_on).mv(1.22, 0.56, 0))
    if starter_k > 0: s.append(starter(starter_k).mv(0.45, 0.6, 0.36))
    if stage >= 1 and starter_k <= 0 and stage >= 2: s.append(starter(0.6).mv(0.45, 0.6, 0.36))
    if driver is not None: s.append(driver)
    g, sp = lamps_glow(stage, lamps)
    return cat(s), g, sp

def modern(spin=0.0, col=(196, 18, 30)):
    return C.model3(col, spin)

def wipe(old, new, xs, keep_old_dir=-1):
    """Scan upgrade: new geometry in front of the scan plane (x > xs), old geometry behind it."""
    a = old.copy(); a.keep(a.t.mean(1)[:, 0] < xs)
    b = new.copy(); b.keep(b.t.mean(1)[:, 0] >= xs)
    return cat([a, b])

def scan_fx(xs, acc, h=2.0, w=1.9, k=1.0, t=0.0):
    """Glowing scan plane (YZ) at x = xs with a bright edge frame."""
    if k <= 0: return [], []
    pl = PR.glow_quad(w * 1.4, h * 1.5, acc, 0.55 * k, T_DISC).rot("y", 90).mv(xs, h * 0.5, 0)
    edge = cat([capsule((xs, 0.02, -w / 2), (xs, 0.02, w / 2), 0.012, 6, acc), capsule((xs, h, -w / 2), (xs, h, w / 2), 0.012, 6, acc),
                capsule((xs, 0.02, -w / 2), (xs, h, -w / 2), 0.012, 6, acc), capsule((xs, 0.02, w / 2), (xs, h, w / 2), 0.012, 6, acc)]).glow(3.5 * k)
    r = np.random.default_rng(int(t * 30))
    sp = [((xs + r.uniform(-0.05, 0.05), r.uniform(0.1, h), r.uniform(-w / 2, w / 2)), acc, 0.02, 1.2 * k) for _ in range(10)]
    return [pl, edge], sp

# ---------------------------------------------------------------- props
def hologram(mesh, col, e=0.18):
    h = mesh.copy(); h.m[:] = GLOW; h.c[:] = rgb(col); h.e[:] = e; return h

@lru_cache(None)
def _horse():
    c = (255, 255, 255)
    parts = [superellipsoid(0.62, 0.3, 0.24, 0.7, 0.8, 20, 10, c).mv(0, 1.3, 0),
             capsule((0.5, 1.45, 0), (0.82, 1.95, 0), 0.15, 10, c, r1=0.1),
             superellipsoid(0.26, 0.12, 0.1, 0.8, 0.8, 14, 8, c).rot("z", -35).mv(0.98, 1.92, 0),
             capsule((0.78, 2.12, 0.05), (0.76, 2.25, 0.07), 0.03, 6, c), capsule((0.78, 2.12, -0.05), (0.76, 2.25, -0.07), 0.03, 6, c),
             capsule((0.6, 1.75, 0), (0.76, 2.05, 0), 0.05, 6, c)]
    for x in (0.42, -0.45):
        for z in (0.13, -0.13):
            parts += [capsule((x, 1.15, z), (x + 0.04, 0.6, z), 0.065, 8, c, r1=0.05), capsule((x + 0.04, 0.6, z), (x, 0.06, z), 0.045, 8, c, r1=0.04)]
    parts.append(capsule((-0.6, 1.4, 0), (-0.85, 0.85, 0), 0.06, 8, c, r1=0.03))
    return cat(parts)

def horse(col, e=0.22, cut=None, gallop=0.0):
    h = _horse().copy()
    if cut is not None: h.keep(h.t.mean(1)[:, 0] > cut)
    h.mv(0, 0.05 * math.sin(gallop), 0)
    return hologram(h, col, e)

def neon(text, w, h, col, e=2.4, frame=True): return PR.neon_sign(text, w, h, col, e, frame)

@lru_cache(None)
def _llama():
    wool = (238, 230, 214); s = []
    s.append(superellipsoid(0.42, 0.24, 0.2, 0.8, 0.8, 18, 10, wool, CLOTH).mv(0, 1.0, 0))
    s.append(capsule((0.33, 1.08, 0), (0.42, 1.62, 0), 0.1, 10, wool, CLOTH, r1=0.085))
    s.append(superellipsoid(0.15, 0.1, 0.09, 0.8, 0.8, 14, 8, wool, CLOTH).mv(0.5, 1.68, 0))
    s += [capsule((0.42, 1.74, sg * 0.05), (0.38, 1.88, sg * 0.07), 0.025, 6, wool, CLOTH) for sg in (-1, 1)]
    s.append(cb(0.55, 1.71, 0, 0.06, 0.05, 0.2, (16, 16, 20), b=0.01, m=GLASS))                 # sunglasses
    s.append(sphere(0.025, 8, 5, (60, 40, 40)).mv(0.64, 1.64, 0))
    for x in (0.28, -0.28):
        for z in (0.1, -0.1): s.append(capsule((x, 0.9, z), (x, 0.16, z), 0.045, 8, wool, CLOTH, r1=0.035))
    s.append(capsule((-0.4, 1.08, 0), (-0.48, 0.98, 0), 0.06, 8, wool, CLOTH))
    board = cat([bbox(-0.5, 0.06, -0.2, 0.5, 0.14, 0.2, (40, 40, 48), b=0.04, m=SATIN),
                 box(-0.42, 0.04, -0.16, 0.42, 0.05, 0.16, (80, 230, 255), e=3.0, m=GLOW)])
    return cat(s + [board])

def llama(t, x, z, face=1):
    """Oddity: a llama in sunglasses gliding on a hoverboard. Never mentioned."""
    l = _llama().copy()
    if face < 0: l.rot("y", 180)
    l.mv(x, 0.08 + 0.05 * math.sin(t * 3.1), z)
    return l, ((x, 0.1, z), (80, 230, 255), 0.25, 0.6)

def paper(lines, w=1.0, h=1.3, stamp=None):
    im = Image.new("RGB", (400, 520), (240, 226, 190)); d = ImageDraw.Draw(im)
    d.rectangle((10, 10, 389, 509), outline=(150, 110, 60), width=6)
    y = 60
    for i, (txt, sz) in enumerate(lines):
        d.text((200, y), txt, font=_f(sz), fill=(50, 36, 24), anchor="mm"); y += sz + 26
    for k in range(6): d.line((50, 330 + k * 24, 350, 330 + k * 24), fill=(170, 150, 120), width=4)
    if stamp:
        txt, colr = stamp; st = Image.new("RGBA", (400, 520)); sd = ImageDraw.Draw(st)
        sd.rounded_rectangle((70, 300, 330, 420), 16, outline=colr, width=12); sd.text((200, 360), txt, font=_f(84), fill=colr, anchor="mm")
        st = st.rotate(14, center=(200, 360)); im.paste(st, (0, 0), st)
    tid = tex(im)
    return cat([cb(0, 0, -0.006, w + 0.02, h + 0.02, 0.01, (200, 186, 150), b=0.004),
                quad((-w / 2, -h / 2, 0), (w / 2, -h / 2, 0), (w / 2, h / 2, 0), (-w / 2, h / 2, 0), (255, 255, 255), tid, 0.12, m=SATIN)])

def code_tex(seed, w=256, h=320, col=(120, 255, 200)):
    r = np.random.default_rng(seed); im = Image.new("RGB", (w * 2, h * 2), (0, 0, 0)); d = ImageDraw.Draw(im)
    f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 22)
    toks = ["if", "for", "brake()", "torque", "0x3F", "{", "}", "=>", "while", "rpm", "can.tx", "abs", "return", "lane", "ecu", "pwm", "&&", "++i"]
    for i in range(int(h * 2 / 30)):
        x = 16 + 26 * int(r.integers(0, 4)); line = " ".join(r.choice(toks, int(r.integers(2, 6))))
        d.text((x, 10 + i * 30), line, font=f, fill=tuple(int(c * r.uniform(0.6, 1)) for c in col))
    return tex(im.resize((w, h), Image.LANCZOS))
T_CODE = [code_tex(i) for i in range(4)]

def code_panel(i, w=0.7, h=0.9, col=(120, 255, 200), e=1.2):
    return quad((-w / 2, -h / 2, 0), (w / 2, -h / 2, 0), (w / 2, h / 2, 0), (-w / 2, h / 2, 0), col, T_CODE[i % 4], e, m=GLOW)
