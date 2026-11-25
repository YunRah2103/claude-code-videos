"""Smooth low-poly cars for the cinematic renderer. Bodies are lofts of superellipse cross-sections (real proportions
from the manufacturers' published dimensions, simplified), with dark wheel-arch openings, lathed tyres, textured rims,
emissive lights and drawn logos. Cars point along +x, wheels on y=0, driver (LHD) on the -z side.
Hyundai Ioniq 5 N, Chevrolet Blazer EV (GM), Jeep Wrangler (JL), Willys MB (1941), Tesla Model 3."""
import math
import numpy as np
from PIL import Image, ImageDraw
from geo import (P, cat, quad, box, cbox, bbox, cb, lathe, cyl, superellipsoid, sphere, capsule, loft, tex, word_tex, font, rgb,
                 MATTE, PAINT, GLASS, CHROME, SATIN, RUBBER, GLOW, SCREEN, T_DISC)

# ---------------------------------------------------------------- textures
def _img(w, h, bg=(0, 0, 0)): im = Image.new("RGB", (w * 4, h * 4), bg); return im, ImageDraw.Draw(im)
def _fin(im, w, h, srgb=True): return tex(im.resize((w, h), Image.LANCZOS), srgb)

def _rim(spokes=5, rim=(60, 62, 70), face=(28, 28, 32), n=128, style="split", hub=None):
    im, d = _img(n, n, face); N = n * 4; c = N / 2
    d.ellipse((4, 4, N - 4, N - 4), fill=rim); d.ellipse((N * 0.1, N * 0.1, N * 0.9, N * 0.9), fill=(10, 10, 12))
    for k in range(spokes):
        a = 2 * math.pi * k / spokes
        for off in ((-0.09, 0.0), (0.09, 0.0)) if style == "split" else ((0.0, 0.0),):
            w = 0.055 if style == "split" else 0.11
            pts = []
            for r, s in ((0.15, w * 1.3), (0.44, w)):
                for sg in (-1, 1):
                    aa = a + off[0] + sg * s
                    pts.append((c + math.cos(aa) * r * N, c + math.sin(aa) * r * N))
            d.polygon([pts[0], pts[2], pts[3], pts[1]], fill=rim)
    d.ellipse((c - N * 0.12, c - N * 0.12, c + N * 0.12, c + N * 0.12), fill=rim)
    d.ellipse((c - N * 0.06, c - N * 0.06, c + N * 0.06, c + N * 0.06), fill=hub or (20, 20, 24))
    return _fin(im, n, n)

def _tread(n=64):
    im, d = _img(n, n, (22, 22, 24))
    for i in range(8):
        y = i * n * 4 / 8; d.polygon([(0, y), (n * 2, y + 30), (n * 4, y), (n * 4, y + 40), (n * 2, y + 70), (0, y + 40)], fill=(34, 34, 38))
    return _fin(im, n, n)

def _h_logo(w=96, h=64, fg=(220, 224, 232), bg=(30, 32, 38)):
    im, d = _img(w, h, bg); W_, H_ = w * 4, h * 4
    d.ellipse((14, 22, W_ - 14, H_ - 22), outline=fg, width=20); sk = 0.32
    def q(x0, y0, x1, y1):
        d.polygon([(x0 + sk * (H_ / 2 - y0), y0), (x1 + sk * (H_ / 2 - y0), y0), (x1 + sk * (H_ / 2 - y1), y1), (x0 + sk * (H_ / 2 - y1), y1)], fill=fg)
    q(W_ * .3, H_ * .27, W_ * .38, H_ * .73); q(W_ * .6, H_ * .27, W_ * .68, H_ * .73); q(W_ * .33, H_ * .46, W_ * .66, H_ * .55)
    return _fin(im, w, h)

def _n_logo(w=64, h=64, bg=(30, 32, 38)):
    im, d = _img(w, h, bg); W_ = w * 4
    d.text((W_ / 2, W_ / 2), "N", font=font(int(W_ * 0.78)), fill=(240, 240, 244), anchor="mm")
    d.polygon([(W_ * .64, W_ * .12), (W_ * .88, W_ * .12), (W_ * .64, W_ * .86)], fill=(226, 30, 44))
    return _fin(im, w, h)

def _bowtie(w=96, h=48, bg=(24, 24, 28)):
    im, d = _img(w, h, bg); W_, H_ = w * 4, h * 4
    pts = [(10, H_ * .34), (W_ * .33, H_ * .34), (W_ * .37, H_ * .12), (W_ * .63, H_ * .12), (W_ * .67, H_ * .34), (W_ - 10, H_ * .34),
           (W_ - 40, H_ * .66), (W_ * .67, H_ * .66), (W_ * .63, H_ * .88), (W_ * .37, H_ * .88), (W_ * .33, H_ * .66), (40, H_ * .66)]
    d.polygon(pts, fill=(200, 200, 206)); d.polygon([(x * .86 + W_ * .07, y * .76 + H_ * .12) for x, y in pts], fill=(226, 176, 46))
    return _fin(im, w, h)

def _gm(n=128):
    N4 = n * 4; im = Image.new("RGB", (N4, N4)); d = ImageDraw.Draw(im)
    for y in range(N4): d.line((0, y, N4, y), fill=(int(30 + 40 * y / N4), int(110 + 90 * y / N4), 240))
    mask = Image.new("L", (N4, N4), 0); ImageDraw.Draw(mask).rounded_rectangle((0, 0, N4 - 1, N4 - 1), N4 // 5, fill=255)
    im = Image.composite(im, Image.new("RGB", (N4, N4), (255, 255, 255)), mask); d = ImageDraw.Draw(im)
    d.text((N4 / 2, N4 * 0.45), "gm", font=font(int(N4 * 0.52), "bold"), fill=(255, 255, 255), anchor="mm")
    d.rectangle((N4 * 0.53, N4 * 0.72, N4 * 0.8, N4 * 0.76), fill=(255, 255, 255))
    return _fin(im, n, n)

def _jeep_grille(body, n=7, w=192, h=112):
    im, d = _img(w, h, body); W_, H_ = w * 4, h * 4
    for i in range(n):
        x = W_ / 2 + (i - (n - 1) / 2) * W_ * 0.055
        d.rounded_rectangle((x - W_ * 0.016, H_ * 0.16, x + W_ * 0.016, H_ * 0.84), 18, fill=(18, 18, 22))
    return _fin(im, w, h)

def _tesla_t(w=48, h=48, fg=(60, 60, 66), bg=(240, 240, 244)):
    im, d = _img(w, h, bg); W_ = w * 4
    d.polygon([(W_ * .14, W_ * .2), (W_ * .86, W_ * .2), (W_ * .8, W_ * .3), (W_ * .56, W_ * .28), (W_ * .53, W_ * .86), (W_ * .47, W_ * .86), (W_ * .44, W_ * .28), (W_ * .2, W_ * .3)], fill=fg)
    d.arc((W_ * .1, W_ * .1, W_ * .9, W_ * .5), 200, 340, fill=fg, width=10)
    return _fin(im, w, h)

def _pixels(w=128, h=32, on=(255, 255, 255), bg=(22, 22, 26), cols=8, rows=2):
    im, d = _img(w, h, bg); W_, H_ = w * 4, h * 4; cw = W_ / cols; ch = H_ / rows
    for i in range(cols):
        for j in range(rows): d.rectangle((i * cw + 6, j * ch + 6, (i + 1) * cw - 6, (j + 1) * ch - 6), fill=on)
    return _fin(im, w, h)

T_RIM_N = _rim(5, (40, 40, 46), (16, 16, 18), style="split"); T_RIM_CHEVY = _rim(6, (150, 154, 162), (30, 30, 34), style="solid")
T_RIM_JEEP = _rim(5, (40, 40, 44), (20, 20, 22), style="solid"); T_RIM_TES = _rim(5, (190, 194, 200), (60, 62, 66), style="solid")
T_RIM_WILLYS = _rim(5, (96, 108, 58), (80, 90, 48), style="solid")
T_TREAD = _tread(); T_H = _h_logo(); T_N = _n_logo(); T_BOWTIE = _bowtie(); T_GM = _gm(); T_TESLA = _tesla_t()
T_JEEP = word_tex("Jeep", 160, 64, (240, 240, 240), (24, 24, 26), 46, weight="bold")
T_PIX = _pixels(); T_PIX_R = _pixels(on=(255, 40, 50), cols=16, rows=2)

# ---------------------------------------------------------------- wheels
def wheel(x, z, R=0.36, wd=0.26, rim_tex=T_RIM_N, spin=0.0, caliper=None, side=1, knobby=False):
    """Tyre + rim facing outwards on side `side` (+1 => +z)."""
    rr = R * 0.72
    prof = [(rr * 0.98, -wd / 2), (R - 0.035, -wd / 2), (R, -wd / 2 + 0.04), (R, wd / 2 - 0.04), (R - 0.035, wd / 2), (rr * 0.98, wd / 2)]
    tyre = lathe(prof, 28, (30, 30, 32), RUBBER, angle=70)
    if knobby:
        tyre = cat([tyre] + [cb(R * math.cos(a), 0, R * math.sin(a), 0.035, wd * 0.92, 0.04, (36, 36, 40), b=0.01, m=RUBBER).rot("y", -math.degrees(a))
                             for a in np.linspace(0, 2 * math.pi, 30, endpoint=False)])
    rim = cyl(rr, rr, 0.02, 28, (255, 255, 255), CHROME, captex=rim_tex).mv(0, wd / 2 - 0.04, 0)
    barrel = lathe([(rr, -wd / 2 + 0.02), (rr * 0.98, wd / 2 - 0.03)], 24, (20, 20, 22), MATTE)
    parts = [tyre, rim, barrel]
    if caliper:
        parts.append(cb(rr * 0.45, wd / 2 - 0.09, rr * 0.35, 0.1, 0.06, 0.16, caliper, b=0.015, m=PAINT).rot("y", 30))
    w = cat(parts).rot("y", spin)                       # spin about the axle (local y)
    w = w.rot("x", 90 if side > 0 else -90)            # axle -> z
    return w.mv(x, R, z)

def arch(x, z, R, side, h0=0.18, square=False):
    """Dark wheel-arch opening drawn on the body side (round, or squared-off like the Ioniq 5's)."""
    tr = []
    for i in range(16):
        a0, a1 = math.pi * i / 16, math.pi * (i + 1) / 16
        def pt(a):
            r = R + 0.07
            if square: r = r / max(abs(math.cos(a)) ** 4 + abs(math.sin(a)) ** 4, 1e-6) ** 0.25 * 0.97
            return (x + r * math.cos(a), R + r * math.sin(a), z)
        tr.append([(x, R, z), pt(a0), pt(a1)])
    tr.append([(x - R - 0.07, R, z), (x + R + 0.07, R, z), (x + R + 0.07, h0, z)]); tr.append([(x - R - 0.07, R, z), (x + R + 0.07, h0, z), (x - R - 0.07, h0, z)])
    return P(tr, (10, 10, 12), m=MATTE)

def _sides(fn):
    return [fn(1), fn(-1)]

def _wheels(xs, zw, R, wd, rim, spin, caliper=None, knobby=False, body_w=None, arch_h=0.18, square=False):
    out = []
    for x in xs:
        for s in (1, -1):
            out.append(wheel(x, s * zw, R, wd, rim, spin, caliper, s, knobby))
            if body_w: out.append(arch(x, s * (body_w + 0.004), R, s, arch_h, square))
    return out

def _glow_disc(x, y, z, r, col, e=2.0, axis="x"):
    """Additive soft disc (lamp halo) facing +axis."""
    q = quad((-r, -r, 0), (r, -r, 0), (r, r, 0), (-r, r, 0), col, T_DISC, e, m=GLOW)
    if axis == "x": q.rot("y", 90)
    elif axis == "-x": q.rot("y", -90)
    return q.mv(x, y, z)

# ---------------------------------------------------------------- Hyundai Ioniq 5 N
N_BLUE = (96, 132, 172); N_RED = (220, 30, 44)
def ioniq5n(col=N_BLUE, spin=0.0, lights=1.0, interior=False):
    w = 0.965
    body = loft([(2.37, 0.86, 0.3, 0.74, 6, 0.1), (2.3, 0.94, 0.24, 0.82, 8, 0.06), (1.9, 0.965, 0.22, 0.9, 10, 0.04),
                 (1.2, w, 0.22, 0.97, 11, 0.04), (-1.5, w, 0.22, 1.0, 11, 0.04), (-2.2, 0.955, 0.24, 1.0, 10, 0.05), (-2.35, 0.9, 0.3, 0.99, 7, 0.08)],
                28, col, SATIN, angle=26)
    gh = loft([(1.22, 0.86, 0.9, 0.99, 4, 0.3), (0.95, 0.85, 0.9, 1.2, 4, 0.3), (0.35, 0.82, 0.9, 1.56, 4, 0.32), (-1.9, 0.8, 0.9, 1.58, 4, 0.3),
               (-2.22, 0.78, 0.9, 1.5, 4, 0.3)], 22, (22, 28, 36), GLASS, angle=40)
    roof = loft([(0.3, 0.6, 1.53, 1.59, 6, 0.0), (-1.92, 0.6, 1.55, 1.61, 6, 0.0)], 16, (20, 20, 24), PAINT)
    cpil = [cb(-1.72, 1.28, s * 0.82, 0.32, 0.56, 0.04, col, b=0.015, m=SATIN).rot("x", s * 8, (-1.72, 1.0, s * 0.82)) for s in (1, -1)]
    apil = []
    crease = [cb(0.2, 0.62, s * (w + 0.004), 2.4, 0.012, 0.01, (40, 56, 76), b=0.004).rot("z", -9, (0.2, 0.62, 0)) for s in (1, -1)]
    skirt = [cb(-0.05, 0.27, s * (w - 0.02), 3.3, 0.06, 0.06, N_RED, b=0.012, m=PAINT) for s in (1, -1)]
    lip = cb(2.27, 0.3, 0, 0.18, 0.05, 1.7, N_RED, b=0.015, m=PAINT)
    grille = cat([cb(2.34, 0.42, 0, 0.06, 0.16, 1.3, (16, 16, 18), b=0.02), cb(2.36, 0.64, 0, 0.03, 0.12, 1.78, (14, 14, 16), b=0.01)])
    plamps = [box(2.375, 0.6, s * 0.68 - 0.19, 2.39, 0.68, s * 0.68 + 0.19, (255, 255, 255), texs={"r": T_PIX}, e=2.5 * lights) for s in (1, -1)]
    tail = box(-2.37, 0.86, -0.85, -2.34, 0.93, 0.85, (255, 255, 255), texs={"l": T_PIX_R}, e=1.8)
    badge = box(2.33, 0.74, -0.11, 2.37, 0.81, 0.11, (255, 255, 255), texs={"r": T_H}, m=CHROME)
    nb = box(2.335, 0.43, -0.4, 2.37, 0.51, -0.32, (255, 255, 255), texs={"r": T_N})
    rnb = box(-2.38, 0.66, 0.28, -2.34, 0.74, 0.36, (255, 255, 255), texs={"l": T_N})
    wing = cat([cb(-2.08, 1.62, 0, 0.32, 0.04, 1.5, (20, 20, 24), b=0.012, m=PAINT), cb(-2.18, 1.6, 0, 0.12, 0.05, 1.52, N_RED, b=0.01, m=PAINT)])
    mirrors = [cb(1.02, 1.04, s * 1.03, 0.2, 0.11, 0.14, (20, 20, 24), b=0.035, m=PAINT) for s in (1, -1)]
    handles = [cb(x, 0.88, s * (w + 0.005), 0.18, 0.025, 0.012, (30, 30, 34), b=0.004) for x in (0.35, -0.75) for s in (1, -1)]
    wheels = _wheels((1.5, -1.5), 0.86, 0.36, 0.27, T_RIM_N, spin, N_RED, body_w=w, square=True)
    halo = []
    if lights > 0:
        halo = [_glow_disc(2.4, 0.64, s * 0.7, 0.28, (210, 230, 255), 0.6 * lights) for s in (1, -1)]
    return cat([body, gh, roof, *cpil, *apil, *crease, *skirt, lip, grille, *plamps, tail, badge, nb, rnb, wing, *mirrors, *handles, *wheels, *halo])

# ---------------------------------------------------------------- Chevrolet Blazer EV (GM)
CHEVY_RED = (170, 18, 28)
def blazer_ev(col=CHEVY_RED, spin=0.0, lights=1.0):
    w = 0.99
    body = loft([(2.44, 0.84, 0.4, 0.78, 3.0, 0.15), (2.32, 0.95, 0.3, 0.88, 4, 0.1), (1.6, w, 0.26, 0.98, 6, 0.06), (0.9, w, 0.26, 1.02, 7, 0.06),
                 (-1.6, w, 0.26, 1.05, 7, 0.07), (-2.2, 0.96, 0.3, 1.04, 6, 0.1), (-2.42, 0.86, 0.42, 1.0, 4, 0.15)], 24, col, PAINT, angle=38)
    gh = loft([(0.95, 0.88, 0.95, 1.04, 4, 0.3), (0.2, 0.84, 0.95, 1.6, 4, 0.32), (-1.2, 0.82, 0.95, 1.62, 4, 0.32), (-2.1, 0.78, 0.95, 1.32, 4, 0.3),
               (-2.3, 0.74, 0.95, 1.12, 4, 0.3)], 22, (20, 24, 30), GLASS, angle=40)
    roof = loft([(0.12, 0.62, 1.57, 1.63, 6, 0.0), (-1.25, 0.62, 1.59, 1.65, 6, 0.0), (-1.95, 0.58, 1.37, 1.42, 6, 0.0)], 16, (18, 18, 20), PAINT)
    clad = [cb(0, 0.36, s * (w - 0.01), 4.4, 0.2, 0.05, (22, 22, 24), b=0.02) for s in (1, -1)]
    grille = cb(2.42, 0.56, 0, 0.06, 0.28, 1.3, (14, 14, 16), b=0.03)
    bar = box(2.36, 0.8, -0.9, 2.42, 0.83, 0.9, (255, 255, 255), e=3.0 * lights)
    lamp = [cb(2.38, 0.6, s * 0.72, 0.05, 0.12, 0.3, (30, 30, 36), b=0.02, m=GLASS) for s in (1, -1)]
    badge = box(2.43, 0.62, -0.14, 2.46, 0.7, 0.14, (255, 255, 255), texs={"r": T_BOWTIE}, m=CHROME)
    rbadge = box(-2.46, 0.9, -0.12, -2.42, 0.96, 0.12, (255, 255, 255), texs={"l": T_BOWTIE}, m=CHROME)
    tail = box(-2.44, 1.0, -0.9, -2.4, 1.03, 0.9, (255, 30, 40), e=2.0)
    mirrors = [cb(0.98, 1.08, s * 1.06, 0.2, 0.11, 0.14, (18, 18, 20), b=0.035, m=PAINT) for s in (1, -1)]
    wheels = _wheels((1.5, -1.45), 0.88, 0.39, 0.27, T_RIM_CHEVY, spin, None, body_w=w, arch_h=0.22)
    halo = [_glow_disc(2.46, 0.81, z, 0.22, (230, 240, 255), 0.5 * lights) for z in (-0.6, 0, 0.6)] if lights else []
    return cat([body, gh, roof, *clad, grille, bar, *lamp, badge, rbadge, tail, *mirrors, *wheels, *halo])

# ---------------------------------------------------------------- Tesla Model 3
TES_WHITE = (222, 225, 230)
def model3(col=TES_WHITE, spin=0.0):
    w = 0.93
    body = loft([(2.36, 0.78, 0.36, 0.62, 2.6, 0.2), (2.15, 0.9, 0.28, 0.76, 3.5, 0.15), (1.3, w, 0.24, 0.86, 5, 0.12),
                 (-1.4, w, 0.26, 0.92, 5, 0.12), (-2.1, 0.9, 0.32, 0.95, 4, 0.15), (-2.34, 0.8, 0.44, 0.92, 3, 0.2)], 24, col, PAINT, angle=40)
    gh = loft([(1.3, 0.84, 0.82, 0.88, 3, 0.35), (0.5, 0.8, 0.82, 1.4, 3, 0.4), (-0.6, 0.78, 0.82, 1.43, 3, 0.4), (-1.9, 0.72, 0.82, 1.02, 3, 0.4),
               (-2.1, 0.7, 0.82, 0.96, 3, 0.4)], 22, (18, 22, 28), GLASS, angle=45)
    lamps = [cb(2.2, 0.66, s * 0.66, 0.12, 0.05, 0.26, (240, 245, 255), b=0.015, e=1.6) for s in (1, -1)]
    tail = [cb(-2.3, 0.86, s * 0.66, 0.08, 0.06, 0.3, (255, 30, 40), b=0.015, e=1.4) for s in (1, -1)]
    badge = box(2.32, 0.6, -0.06, 2.36, 0.66, 0.06, (255, 255, 255), texs={"r": T_TESLA})
    mirrors = [cb(1.0, 0.95, s * 1.0, 0.18, 0.1, 0.12, col, b=0.035, m=PAINT) for s in (1, -1)]
    wheels = _wheels((1.45, -1.42), 0.83, 0.34, 0.24, T_RIM_TES, spin, None, body_w=w)
    return cat([body, gh, *lamps, *tail, badge, *mirrors, *wheels])

# ---------------------------------------------------------------- Jeep Wrangler (JL two-door, top off, doors on)
JEEP_YELLOW = (255, 190, 0); JEEP_RED = (200, 24, 20); JEEP_BLUE = (0, 120, 190)
_GR = {}
def wrangler(col=JEEP_YELLOW, spin=0.0, driver=None, lights=0.0):
    hw = 0.86
    G = _GR.setdefault(col, _jeep_grille(col))
    tub = cat([bbox(-1.95, 0.55, -hw, 1.15, 0.7, hw, col, b=0.04, m=PAINT), bbox(-1.95, 0.55, -hw, 1.15, 1.2, -hw + 0.07, col, b=0.03, m=PAINT),
               bbox(-1.95, 0.55, hw - 0.07, 1.15, 1.2, hw, col, b=0.03, m=PAINT), bbox(-1.95, 0.55, -hw, -1.86, 1.2, hw, col, b=0.03, m=PAINT)])
    hood = bbox(1.1, 0.62, -0.72, 2.02, 1.18, 0.72, col, b=0.07, m=PAINT).fn(lambda v: _crown(v)).smooth(45)
    grille = box(2.0, 0.64, -0.68, 2.05, 1.12, 0.68, (255, 255, 255), texs={"r": G}, m=PAINT)
    lamps = []
    for s in (1, -1):
        lamps += [cyl(0.115, 0.115, 0.04, 24, (210, 214, 222), CHROME).rot("z", -90).mv(2.06, 0.9, s * 0.55),
                  cyl(0.09, 0.09, 0.045, 24, (255, 252, 240), GLASS, e=2.2 * max(lights, 0.25)).rot("z", -90).mv(2.065, 0.9, s * 0.55),
                  lathe([(0.1, 0), (0.11, 0.0)], 24, (255, 255, 255), MATTE, e=3.0).rot("z", -90).mv(2.09, 0.9, s * 0.55)]
    flares = []
    for x0, x1 in ((1.05, 2.05), (-1.9, -0.82)):
        for s in (1, -1):
            flares.append(P([(x0, 0.55, s * hw), (x1, 0.55, s * hw), (x1 - 0.18, 0.98, s * (hw + 0.13)), (x0 + 0.18, 0.98, s * (hw + 0.13)),
                             (x0, 0.55, s * (hw + 0.13)), (x1, 0.55, s * (hw + 0.13))][:0] or
                            [(x0, 0.6, s * (hw + 0.14)), (x1, 0.6, s * (hw + 0.14)), (x1 - 0.2, 0.96, s * (hw + 0.14)),
                             (x0, 0.6, s * (hw + 0.14)), (x1 - 0.2, 0.96, s * (hw + 0.14)), (x0 + 0.2, 0.96, s * (hw + 0.14)),
                             (x0 + 0.2, 0.96, s * (hw + 0.14)), (x1 - 0.2, 0.96, s * (hw + 0.14)), (x1 - 0.2, 0.98, s * hw),
                             (x0 + 0.2, 0.96, s * (hw + 0.14)), (x1 - 0.2, 0.98, s * hw), (x0 + 0.2, 0.98, s * hw)], (28, 28, 30), m=MATTE))
    word = [box(1.45, 0.92, s * 0.725, 1.9, 1.08, s * 0.73, (255, 255, 255), texs={"f" if s > 0 else "b": T_JEEP}) for s in (1, -1)]
    shield = cat([bbox(1.1, 1.16, s * hw - 0.06 * (s > 0), 1.2, 1.95, s * hw + 0.06 * (s < 0), (26, 26, 28), b=0.02, m=PAINT) for s in (1, -1)] +
                 [bbox(1.1, 1.87, -hw, 1.2, 1.96, hw, (26, 26, 28), b=0.02, m=PAINT), bbox(1.1, 1.14, -hw, 1.22, 1.24, hw, (26, 26, 28), b=0.02, m=PAINT)]).fn(lambda v: _lean(v, 1.2, 1.2, 0.28)).smooth(45)
    bar = cat([capsule((-0.45, 1.15, s * (hw - 0.05)), (-0.45, 1.92, s * (hw - 0.05)), 0.045, 10, (26, 26, 28), PAINT) for s in (1, -1)] +
              [capsule((-0.45, 1.92, -hw + 0.05), (-0.45, 1.92, hw - 0.05), 0.045, 10, (26, 26, 28), PAINT)] +
              [capsule((-0.45, 1.92, s * (hw - 0.05)), (1.1, 1.92, s * (hw - 0.05)), 0.04, 10, (26, 26, 28), PAINT) for s in (1, -1)] +
              [capsule((-0.45, 1.6, s * (hw - 0.05)), (-1.85, 1.2, s * (hw - 0.05)), 0.04, 10, (26, 26, 28), PAINT) for s in (1, -1)])
    seats = [cat([bbox(-0.85, 0.72, z - 0.24, -0.38, 0.9, z + 0.24, (36, 36, 40), b=0.05), bbox(-0.92, 0.9, z - 0.24, -0.78, 1.58, z + 0.24, (36, 36, 40), b=0.05)]) for z in (-0.42, 0.42)]
    dash = bbox(0.82, 0.92, -hw + 0.04, 1.12, 1.22, hw - 0.04, (30, 30, 34), b=0.04)
    swheel = lathe([(0.17, -0.015), (0.19, 0.0), (0.17, 0.015)], 20, (22, 22, 24), RUBBER).rot("z", 70).mv(0.2, 1.16, -0.42)
    bump = [bbox(2.04, 0.4, -0.98, 2.3, 0.6, 0.98, (32, 32, 34), b=0.03), bbox(-2.12, 0.4, -0.92, -1.92, 0.6, 0.92, (32, 32, 34), b=0.03)]
    hooks = [cb(2.3, 0.5, s * 0.45, 0.05, 0.08, 0.04, (220, 30, 30), b=0.01, m=PAINT) for s in (1, -1)]
    spare = cat([wheel(0, 0, 0.42, 0.3, T_RIM_JEEP, 0, None, 1, knobby=True)]).rot("y", 90).mv(-2.15, 0.62, 0)
    tails = [cb(-1.97, 0.86, s * 0.74, 0.03, 0.22, 0.12, (240, 30, 30), b=0.01, e=1.2) for s in (1, -1)]
    steps = [bbox(-0.95, 0.42, s * hw, 0.95, 0.5, s * (hw + 0.1), (30, 30, 32), b=0.02) for s in (1, -1)]
    mirrors = [cb(1.0, 1.22, s * 0.98, 0.08, 0.16, 0.2, (26, 26, 28), b=0.03) for s in (1, -1)]
    hinges = [cb(x, 0.82 + 0.22 * i, s * (hw + 0.005), 0.08, 0.04, 0.012, (24, 24, 26), b=0.004) for x in (0.95,) for i in range(2) for s in (1, -1)]
    wheels = _wheels((1.48, -1.38), 0.84, 0.44, 0.33, T_RIM_JEEP, spin, None, knobby=True)
    halo = [_glow_disc(2.12, 0.9, s * 0.55, 0.32, (240, 245, 255), 0.8 * lights) for s in (1, -1)] if lights else []
    parts = [tub, hood, grille, *lamps, *flares, *word, shield, bar, *seats, dash, swheel, *bump, *hooks, spare, *tails, *steps, *mirrors, *hinges, *wheels, *halo]
    if driver is not None: parts.append(driver)
    return cat(parts)

def _crown(v):
    k = np.clip(1 - (v[:, 2] / 0.72) ** 2, 0, 1); top = v[:, 1] > 1.1; v[top, 1] += 0.03 * k[top]; return v
def _lean(v, x0, y0, k):
    v[:, 0] -= np.clip(v[:, 1] - y0, 0, None) * k; return v

# ---------------------------------------------------------------- Willys MB (1941)
OD = (88, 98, 54)
_GW = None
def willys(spin=0.0, driver=None):
    global _GW
    if _GW is None: _GW = _jeep_grille(OD, 9)
    hw = 0.68
    tub = cat([bbox(-1.55, 0.5, -hw, 0.6, 0.62, hw, OD, b=0.03), bbox(-1.55, 0.5, -hw, 0.6, 1.0, -hw + 0.06, OD, b=0.02),
               bbox(-1.55, 0.5, hw - 0.06, 0.6, 1.0, hw, OD, b=0.02), bbox(-1.55, 0.5, -hw, -1.48, 1.0, hw, OD, b=0.02)])
    star = word_tex("★", 64, 64, (240, 240, 232), OD, 52)
    hood = bbox(0.6, 0.62, -0.52, 1.6, 1.05, 0.52, OD, b=0.05)
    hstar = box(0.85, 1.051, -0.2, 1.3, 1.053, 0.2, (255, 255, 255), texs={"t": star})
    grille = box(1.6, 0.55, -0.5, 1.64, 1.05, 0.5, (255, 255, 255), texs={"r": _GW})
    lamps = [cyl(0.075, 0.075, 0.04, 20, (220, 220, 210), GLASS, e=0.4).rot("z", -90).mv(1.64, 0.86, s * 0.34) for s in (1, -1)]
    fend = [bbox(0.6, 0.78, s * 0.52, 1.62, 0.84, s * 0.86, OD, b=0.015) for s in (1, -1)] + [bbox(-1.4, 0.8, s * hw, -0.6, 0.86, s * 0.86, OD, b=0.015) for s in (1, -1)]
    shield = cat([bbox(0.62, 1.0, s * hw - 0.05 * (s > 0), 0.68, 1.55, s * hw + 0.05 * (s < 0), OD, b=0.012) for s in (1, -1)] +
                 [bbox(0.62, 1.49, -hw, 0.68, 1.55, hw, OD, b=0.012)]).fn(lambda v: _lean(v, 0.62, 1.0, 0.2)).smooth(45)
    sstar = [box(-1.1, 0.62, s * hw, -0.7, 0.96, s * (hw + 0.004), (255, 255, 255), texs={"f" if s > 0 else "b": star}) for s in (1, -1)]
    seats = [bbox(-0.9, 0.7, z - 0.22, -0.45, 0.85, z + 0.22, (64, 70, 42), b=0.04) for z in (-0.32, 0.32)]
    can = cb(-1.62, 0.8, 0.4, 0.12, 0.4, 0.28, (70, 80, 44), b=0.02)
    spare = wheel(0, 0, 0.36, 0.22, T_RIM_WILLYS, 0, None, 1, knobby=True).rot("y", 90).mv(-1.66, 0.5, -0.2)
    swheel = lathe([(0.15, -0.012), (0.17, 0.0), (0.15, 0.012)], 18, (22, 22, 24), RUBBER).rot("z", 60).mv(0.02, 1.08, -0.32)
    wheels = _wheels((1.15, -1.0), 0.7, 0.37, 0.22, T_RIM_WILLYS, spin, None, knobby=True)
    parts = [tub, hood, hstar, grille, *lamps, *fend, shield, *sstar, *seats, can, spare, swheel, *wheels]
    if driver is not None: parts.append(driver)
    return cat(parts)
