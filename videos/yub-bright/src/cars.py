"""Bright low-poly cars, logos, props and sets for the jeep / ioniq / gm shorts. Cars point along +x (nose at +x),
wheels on y=0, driver (left-hand drive) on the -z side."""
import math
import numpy as np
from PIL import Image, ImageDraw
from lowpoly import P, cat, box, cbox, cyl, sphere, prism, quad, tiles, wall, tex, font
from models import person, face_tex
import ymodels as Y

# ---------------------------------------------------------------- logo / panel textures
def _jeep_grille(body, n=7, w=160, h=96):
    im = Image.new("RGB", (w, h), body); d = ImageDraw.Draw(im)
    for i in range(n):
        x = w / 2 + (i - (n - 1) / 2) * (w * 0.38 / n) * 1.45
        d.rounded_rectangle((x - 4, 18, x + 4, 78), 3, fill=(22, 22, 26))
    for cx in (20, w - 20):
        d.ellipse((cx - 17, 30, cx + 17, 64), fill=(40, 40, 44)); d.ellipse((cx - 14, 33, cx + 14, 61), fill=(200, 204, 212))
        d.ellipse((cx - 10, 37, cx + 10, 57), fill=(255, 252, 230))
    return tex(im)

def _logo_word(text, w, h, fg, bg, size=None, italic=False):
    im = Image.new("RGB", (w, h), bg); d = ImageDraw.Draw(im)
    d.text((w / 2, h / 2), text, font=font(size or int(h * 0.7)), fill=fg, anchor="mm")
    if italic: im = im.transform(im.size, Image.AFFINE, (1, 0.25, -h * 0.12, 0, 1, 0), fillcolor=bg)
    return tex(im)

def _star(w=64, h=64, fg=(245, 245, 240), bg=(84, 92, 52)):
    im = Image.new("RGB", (w, h), bg); d = ImageDraw.Draw(im)
    pts = [(w / 2 + (0.45 if k % 2 == 0 else 0.18) * w * math.sin(k * math.pi / 5), h / 2 - (0.45 if k % 2 == 0 else 0.18) * h * math.cos(k * math.pi / 5)) for k in range(10)]
    d.polygon(pts, fill=fg); return tex(im)

def _hyundai(w=96, h=64, bg=(30, 32, 38), fg=(214, 218, 226)):
    im = Image.new("RGB", (w * 4, h * 4), bg); d = ImageDraw.Draw(im); W_, H_ = w * 4, h * 4
    d.ellipse((12, 20, W_ - 12, H_ - 20), outline=fg, width=18)
    # slanted H
    sk = 0.32
    def q(x0, y0, x1, y1):
        d.polygon([(x0 + sk * (H_ - y0 - H_ / 2), y0), (x1 + sk * (H_ - y0 - H_ / 2), y0), (x1 + sk * (H_ - y1 - H_ / 2), y1), (x0 + sk * (H_ - y1 - H_ / 2), y1)], fill=fg)
    q(W_ * 0.3, H_ * 0.26, W_ * 0.38, H_ * 0.74); q(W_ * 0.6, H_ * 0.26, W_ * 0.68, H_ * 0.74); q(W_ * 0.33, H_ * 0.46, W_ * 0.66, H_ * 0.55)
    return tex(im.resize((w, h), Image.LANCZOS))

def _nlogo(w=64, h=64, bg=(30, 32, 38)):
    im = Image.new("RGB", (w, h), bg); d = ImageDraw.Draw(im)
    d.text((w / 2, h / 2), "N", font=font(int(h * 0.8)), fill=(240, 240, 244), anchor="mm")
    d.polygon([(w * 0.62, h * 0.12), (w * 0.86, h * 0.12), (w * 0.62, h * 0.88)], fill=(230, 40, 50))
    return tex(im)

def _bowtie(w=96, h=48, bg=(30, 30, 34)):
    im = Image.new("RGB", (w * 4, h * 4), bg); d = ImageDraw.Draw(im); W_, H_ = w * 4, h * 4
    pts = [(10, H_ * 0.34), (W_ * 0.33, H_ * 0.34), (W_ * 0.37, H_ * 0.12), (W_ * 0.63, H_ * 0.12), (W_ * 0.67, H_ * 0.34), (W_ - 10, H_ * 0.34),
           (W_ - 40, H_ * 0.66), (W_ * 0.67, H_ * 0.66), (W_ * 0.63, H_ * 0.88), (W_ * 0.37, H_ * 0.88), (W_ * 0.33, H_ * 0.66), (40, H_ * 0.66)]
    d.polygon(pts, fill=(200, 200, 206)); inner = [(x * 0.86 + W_ * 0.07, y * 0.78 + H_ * 0.11) for x, y in pts]
    d.polygon(inner, fill=(226, 180, 50))
    return tex(im.resize((w, h), Image.LANCZOS))

def _gm(n=96):
    im = Image.new("RGB", (n * 4, n * 4), (255, 255, 255)); d = ImageDraw.Draw(im); N4 = n * 4
    for y in range(N4):
        c = (int(40 + 30 * y / N4), int(120 + 60 * y / N4), 235)
        d.line((0, y, N4, y), fill=c)
    mask = Image.new("L", (N4, N4), 0); ImageDraw.Draw(mask).rounded_rectangle((0, 0, N4 - 1, N4 - 1), N4 // 5, fill=255)
    bgw = Image.new("RGB", (N4, N4), (255, 255, 255)); im = Image.composite(im, bgw, mask); d = ImageDraw.Draw(im)
    d.text((N4 / 2, N4 * 0.44), "gm", font=font(int(N4 * 0.5)), fill=(255, 255, 255), anchor="mm")
    d.rectangle((N4 * 0.52, N4 * 0.7, N4 * 0.8, N4 * 0.74), fill=(255, 255, 255))
    return tex(im.resize((n, n), Image.LANCZOS))

def _pixel_lights(w=128, h=24, on=(255, 255, 250), bg=(20, 20, 24)):
    im = Image.new("RGB", (w, h), bg); d = ImageDraw.Draw(im)
    for side in (0, 1):
        x0 = 6 if side == 0 else w - 6 - 36
        for i in range(6):
            for j in range(2):
                d.rectangle((x0 + i * 6, 5 + j * 8, x0 + i * 6 + 4, 5 + j * 8 + 5), fill=on)
    return tex(im)

T_JEEP_WORD = _logo_word("Jeep", 128, 48, (250, 250, 250), (20, 20, 24))
T_JEEP_WORD_SIGN = _logo_word("Jeep", 256, 96, (255, 255, 255), (20, 20, 24))
T_HYUNDAI = _hyundai()
T_HYUNDAI_SIGN = _logo_word("HYUNDAI", 256, 64, (255, 255, 255), (0, 44, 95), 36)
T_N = _nlogo()
T_BOWTIE = _bowtie()
T_GM = _gm()
T_STAR = _star()
T_PIX_F = _pixel_lights()
T_PIX_R = _pixel_lights(on=(255, 40, 40))

# ---------------------------------------------------------------- wheels
def wheel(x, z, r=0.42, wd=0.3, hub=None, spin=0.0, tyre=(26, 26, 28)):
    return Y.wheel(x, z, hub if hub is not None else Y.T_HUB_TES, r, wd, spin)

# ---------------------------------------------------------------- Jeep Wrangler (JL, two-door, top off)
JEEP_YELLOW = (255, 196, 20)
def wrangler(col=JEEP_YELLOW, spin=0.0, driver=None, plate=None):
    hw = 0.82; G = _GRILLE.setdefault(col, _jeep_grille(col))
    tub = cat([box(-1.95, 0.55, -hw, 1.2, 0.68, hw, col), box(-1.95, 0.55, -hw, 1.2, 1.18, -hw + 0.07, col), box(-1.95, 0.55, hw - 0.07, 1.2, 1.18, hw, col),
               box(-1.95, 0.55, -hw, -1.86, 1.18, hw, col)])
    hood = prism([(1.15, 0.62), (2.0, 0.62), (2.02, 1.12), (1.15, 1.2)], -0.66, 0.66, col)
    grille = box(2.0, 0.6, -0.68, 2.06, 1.14, 0.68, (255, 255, 255), texs={"r": G})
    fend = [box(1.15, 0.78, s * 0.66, 2.06, 0.94, s * 0.98, (28, 28, 30)) for s in (1, -1)] + \
           [box(-1.85, 0.78, s * 0.8, -0.9, 0.92, s * 0.98, (28, 28, 30)) for s in (1, -1)]
    word = [box(1.4, 0.9, s * 0.665, 1.9, 1.08, s * 0.67, (255, 255, 255), texs={"f" if s > 0 else "b": T_JEEP_WORD}) for s in (1, -1)]
    shield = cat([box(1.1, 1.16, s * hw - 0.07 * (s > 0), 1.2, 1.95, s * hw + 0.07 * (s < 0), (28, 28, 30)) for s in (1, -1)] +
                 [box(1.1, 1.86, -hw, 1.2, 1.95, hw, (28, 28, 30)), box(1.1, 1.14, -hw, 1.22, 1.24, hw, (28, 28, 30))]).fn(lambda v: _lean(v, 1.2, 1.2, 0.28))
    glass = None                        # frame only, so the drivers stay visible
    rollbar = [box(-0.5, 1.15, s * hw - 0.08, -0.38, 1.95, s * hw, (28, 28, 30)) for s in (1, -1)] + [box(-0.5, 1.88, -hw, -0.38, 1.98, hw, (28, 28, 30)),
               box(-0.42, 1.88, -hw, 1.0, 1.95, -hw + 0.07, (28, 28, 30)), box(-0.42, 1.88, hw - 0.07, 1.0, 1.95, hw, (28, 28, 30))]
    seats = [cat([box(-0.85, 0.75, z - 0.24, -0.4, 0.9, z + 0.24, (40, 40, 44)), box(-0.9, 0.9, z - 0.24, -0.78, 1.55, z + 0.24, (40, 40, 44))]) for z in (-0.42, 0.42)]
    dash = box(0.85, 0.95, -hw + 0.02, 1.12, 1.25, hw - 0.02, (34, 34, 38))
    swheel = cyl(0.19, 0.19, 0.04, 10, (24, 24, 26), cap=False).rot("z", 70).mv(0.16, 1.16, -0.42)
    bump = [box(2.04, 0.42, -0.95, 2.28, 0.6, 0.95, (30, 30, 32)), box(-2.12, 0.42, -0.9, -1.92, 0.6, 0.9, (30, 30, 32))]
    spare = cyl(0.4, 0.4, 0.26, 12, (26, 26, 28), captex=Y.T_HUB_TES).mv(0, -0.13, 0).rot("z", 90).mv(-2.1, 1.05, 0)
    tails = [box(-1.97, 0.78, s * 0.72 - 0.1, -1.94, 1.0, s * 0.72 + 0.1, (230, 30, 30), e=0.5) for s in (1, -1)]
    steps = [box(-1.0, 0.42, s * hw, 1.0, 0.5, s * (hw + 0.12), (30, 30, 32)) for s in (1, -1)]
    wheels = [wheel(x, z * 0.84, 0.46, 0.34, Y.T_HUB_TES, spin) for x in (1.48, -1.35) for z in (1, -1)]
    mirrors = [cbox(1.05, 1.22, s * 0.95, 0.08, 0.14, 0.18, (28, 28, 30)) for s in (1, -1)]
    parts = [tub, hood, grille, *fend, *word, shield, glass, *rollbar, *seats, dash, swheel, *bump, spare, *tails, *steps, *wheels, *mirrors]
    if driver is not None: parts.append(driver)
    return cat(parts)
_GRILLE = {}

def _lean(v, x0, y0, k):
    v[:, 0] -= np.clip(v[:, 1] - y0, 0, None) * k; return v

# ---------------------------------------------------------------- Willys MB (1940s)
OD = (96, 108, 58)
def willys(spin=0.0, driver=None):
    hw = 0.68
    tub = cat([box(-1.55, 0.5, -hw, 0.6, 0.62, hw, OD), box(-1.55, 0.5, -hw, 0.6, 1.0, -hw + 0.06, OD), box(-1.55, 0.5, hw - 0.06, 0.6, 1.0, hw, OD),
               box(-1.55, 0.5, -hw, -1.48, 1.0, hw, OD)])
    hood = box(0.6, 0.62, -0.52, 1.6, 1.05, 0.52, OD, texs={"t": T_STAR})
    grille = box(1.6, 0.55, -0.5, 1.64, 1.05, 0.5, (255, 255, 255), texs={"r": _GRILLE_W})
    fend = [box(0.6, 0.78, s * 0.52, 1.62, 0.84, s * 0.86, OD) for s in (1, -1)] + [box(-1.4, 0.8, s * hw, -0.6, 0.86, s * 0.86, OD) for s in (1, -1)]
    shield = cat([box(0.62, 1.0, s * hw - 0.06 * (s > 0), 0.68, 1.55, s * hw + 0.06 * (s < 0), OD) for s in (1, -1)] +
                 [box(0.62, 1.49, -hw, 0.68, 1.55, hw, OD)]).fn(lambda v: _lean(v, 0.62, 1.0, 0.2))
    seats = [box(-0.9, 0.7, z - 0.22, -0.45, 0.85, z + 0.22, (70, 74, 46)) for z in (-0.32, 0.32)]
    side_star = [box(-1.1, 0.62, s * hw, -0.7, 0.96, s * (hw + 0.005), (255, 255, 255), texs={"f" if s > 0 else "b": T_STAR}) for s in (1, -1)]
    bump = box(1.62, 0.38, -0.8, 1.72, 0.52, 0.8, OD)
    spare = cyl(0.36, 0.36, 0.22, 10, (26, 26, 28), captex=Y.T_HUB_TOY).mv(0, -0.11, 0).rot("z", 90).mv(-1.7, 0.85, 0)
    wheels = [wheel(x, z * 0.7, 0.38, 0.24, Y.T_HUB_TOY, spin) for x in (1.15, -1.0) for z in (1, -1)]
    swheel = cyl(0.17, 0.17, 0.04, 10, (24, 24, 26), cap=False).rot("z", 60).mv(0.02, 1.08, -0.32)
    parts = [tub, hood, grille, *fend, shield, *seats, *side_star, bump, spare, *wheels, swheel]
    if driver is not None: parts.append(driver)
    return cat(parts)
_GRILLE_W = _jeep_grille(OD, 9)

# ---------------------------------------------------------------- Hyundai Ioniq 5 N
N_BLUE = (70, 132, 200); N_RED = (226, 34, 46)
def ioniq5n(col=N_BLUE, spin=0.0, driver=None, lights=True, open_door=0.0):
    hw = 0.95
    body = prism([(-2.3, 0.3), (2.25, 0.3), (2.32, 0.62), (2.2, 0.92), (1.2, 1.04), (-2.0, 1.06), (-2.32, 0.95)], -hw, hw, col).fn(Y._taper(0.04))
    glass = prism([(1.15, 1.02), (0.25, 1.58), (-1.85, 1.6), (-2.25, 1.02)], -hw * 0.88, hw * 0.88, (30, 40, 56)).fn(Y._taper(0.12, 1.0, 0.6))
    roof = prism([(0.25, 1.58), (-1.85, 1.6), (-1.85, 1.65), (0.2, 1.63)], -hw * 0.78, hw * 0.78, (22, 22, 26))
    pillar = box(-0.62, 1.03, -hw * 0.885, -0.5, 1.6, hw * 0.885, col)
    skirt = [box(-1.8, 0.22, s * hw - 0.02, 1.7, 0.32, s * hw + 0.03, N_RED) for s in (1, -1)]
    lip = box(2.1, 0.24, -0.9, 2.36, 0.3, 0.9, N_RED)
    clad = box(-2.34, 0.26, -hw - 0.01, 2.34, 0.42, hw + 0.01, (24, 24, 28))
    arches = [box(x - 0.55, 0.3, s * hw - 0.03, x + 0.55, 0.78, s * hw + 0.03, (24, 24, 28)) for x in (1.5, -1.45) for s in (1, -1)]
    lamps = box(2.3, 0.66, -0.88, 2.34, 0.8, 0.88, (255, 255, 255), texs={"r": T_PIX_F}, e=1.0 if lights else 0.3)
    tail = box(-2.36, 0.82, -0.9, -2.32, 0.96, 0.9, (255, 255, 255), texs={"l": T_PIX_R}, e=0.8)
    badge = box(2.33, 0.86, -0.14, 2.38, 0.96, 0.14, (255, 255, 255), texs={"r": T_HYUNDAI})
    nbadge = box(2.33, 0.46, -0.4, 2.37, 0.58, -0.22, (255, 255, 255), texs={"r": T_N})
    rbadge = box(-2.38, 0.6, 0.3, -2.34, 0.72, 0.48, (255, 255, 255), texs={"l": T_N})
    wing = box(-2.1, 1.6, -0.75, -1.8, 1.65, 0.75, (24, 24, 28))
    mirrors = [cbox(0.95, 1.08, s * 1.02, 0.18, 0.1, 0.16, (24, 24, 28)) for s in (1, -1)]
    wheels = [wheel(x, z * 0.82, 0.39, 0.28, Y.T_HUB_TES, spin) for x in (1.5, -1.45) for z in (1, -1)]
    calipers = [box(x - 0.1, 0.38, s * 0.98, x + 0.1, 0.55, s * 1.0, N_RED) for x in (1.5, -1.45) for s in (1, -1)]
    parts = [body, glass, roof, pillar, *skirt, lip, clad, *arches, lamps, tail, badge, nbadge, rbadge, wing, *mirrors, *wheels]
    if driver is not None: parts.append(driver)
    return cat(parts)

# ---------------------------------------------------------------- Chevrolet Equinox EV (GM)
EQ_RED = (210, 30, 40)
def equinox(col=EQ_RED, spin=0.0, lights=True):
    hw = 0.95
    body = prism([(-2.35, 0.34), (2.3, 0.34), (2.38, 0.7), (2.25, 1.0), (1.2, 1.1), (-2.15, 1.12), (-2.36, 1.0)], -hw, hw, col).fn(Y._taper(0.05))
    glass = prism([(1.15, 1.08), (0.3, 1.62), (-1.95, 1.64), (-2.25, 1.1)], -hw * 0.88, hw * 0.88, (28, 34, 46)).fn(Y._taper(0.12, 1.0, 0.6))
    roof = prism([(0.3, 1.62), (-1.95, 1.64), (-1.95, 1.7), (0.25, 1.68)], -hw * 0.78, hw * 0.78, (20, 20, 24))
    clad = box(-2.38, 0.24, -hw - 0.01, 2.38, 0.44, hw + 0.01, (24, 24, 28))
    arches = [box(x - 0.58, 0.3, s * hw - 0.03, x + 0.58, 0.84, s * hw + 0.03, (24, 24, 28)) for x in (1.5, -1.45) for s in (1, -1)]
    bar = box(2.32, 0.92, -0.92, 2.38, 0.96, 0.92, (255, 255, 240), e=1.0 if lights else 0.3)
    panel = box(2.33, 0.48, -0.75, 2.39, 0.88, 0.75, (20, 20, 24))
    badge = box(2.37, 0.62, -0.2, 2.42, 0.76, 0.2, (255, 255, 255), texs={"r": T_BOWTIE})
    rbadge = box(-2.42, 0.86, -0.18, -2.37, 0.98, 0.18, (255, 255, 255), texs={"l": T_BOWTIE})
    tail = box(-2.4, 1.0, -0.92, -2.36, 1.05, 0.92, (230, 30, 30), e=0.8)
    mirrors = [cbox(0.95, 1.14, s * 1.02, 0.18, 0.1, 0.16, (24, 24, 28)) for s in (1, -1)]
    wheels = [wheel(x, z * 0.82, 0.4, 0.28, Y.T_HUB_TOY, spin) for x in (1.5, -1.45) for z in (1, -1)]
    return cat([body, glass, roof, clad, *arches, bar, panel, badge, rbadge, tail, *mirrors, *wheels])

# ---------------------------------------------------------------- people in cars
_DRV = {}
def driver(kind="beard", **kw):
    """Seated generic driver for other cars (faces +x after rotation). kinds: beard, cap, granny, tesla."""
    if kind not in _DRV:
        spec = dict(beard=dict(skin=(230, 186, 150), hair=(120, 70, 30), beard=(120, 70, 30)),
                    granny=dict(skin=(236, 196, 170), hair=(220, 220, 226)),
                    tesla=dict(skin=(210, 170, 140), hair=(30, 30, 34), glasses=True),
                    cap=dict(skin=(150, 100, 70), hair=(20, 20, 20)),
                    soldier=dict(skin=(226, 180, 140), hair=(60, 40, 24)))[kind]
        _DRV[kind] = (face_tex(mouth="smile", **spec), spec)
    fid, spec = _DRV[kind]
    top = dict(beard=(200, 50, 50), granny=(150, 90, 200), tesla=(30, 30, 36), cap=(40, 150, 90), soldier=(104, 112, 64))[kind]
    hat = dict(cap=(220, 60, 40), soldier=(84, 94, 52)).get(kind)
    p = person(skin=spec["skin"], top=top, hair=spec["hair"], face=fid, hat=hat, **kw)
    return p

def seat(p, x=-0.62, y=0.75, z=-0.42, floor=0.68):
    """Put a standing-pose figure into a car seat: hips (y=0.9) at seat height y, legs below the tub floor removed."""
    p = p.rot("y", 90).mv(x, y - 0.9, z)
    keep = p.t[:, :, 1].min(1) > floor
    q = P.__new__(P); q.t, q.c, q.k, q.uv, q.e = p.t[keep], p.c[keep], p.k[keep], p.uv[keep], p.e[keep]; return q

def hero_seat(h, x=-0.62, y=0.75, z=-0.42):
    """hero(sit=True) has its seat at y=0.5 and faces +z; turn it to face +x and lift it into the seat."""
    return h.rot("y", 90).mv(x, y - 0.5, z)

# ---------------------------------------------------------------- props
def steering(r=0.2, col=(24, 24, 28), spokes=True):
    s = [cyl(r, r, 0.04, 14, col, cap=False)]
    if spokes: s += [cbox(0, 0.02, 0, 2 * r, 0.03, 0.04, col), cbox(0, 0.02, -r / 2, 0.04, 0.03, r, col)]
    s.append(cyl(0.06, 0.06, 0.05, 8, col, capcol=(60, 60, 66)))
    return cat(s)

def cactus(h=1.6, col=(60, 160, 70)):
    return cat([cbox(0, h / 2, 0, 0.22, h, 0.22, col), cbox(0.25, h * 0.55, 0, 0.3, 0.14, 0.14, col), cbox(0.36, h * 0.72, 0, 0.14, 0.4, 0.14, col),
                cbox(-0.22, h * 0.45, 0, 0.24, 0.12, 0.12, col), cbox(-0.3, h * 0.6, 0, 0.12, 0.32, 0.12, col)])

def mesa(w, h, d, col=(222, 110, 60)):
    return cat([box(-w / 2, 0, -d / 2, w / 2, h * 0.75, d / 2, col), box(-w * 0.35, h * 0.75, -d * 0.4, w * 0.35, h, d * 0.4, tuple(int(c * 0.92) for c in col)),
                box(-w / 2 - 0.01, h * 0.3, d / 2, w / 2 + 0.01, h * 0.38, d / 2 + 0.01, (250, 170, 110))])

def tree(h=3.0, col=(60, 170, 70)):
    return cat([cyl(0.12, 0.1, h * 0.45, 6, (120, 80, 50)), cyl(0.9, 0.0, h * 0.75, 7, col).mv(0, h * 0.3, 0)])

def palm(h=3.6):
    lv = [P([(0, h, 0), (1.4 * math.cos(a), h - 0.6, 1.4 * math.sin(a)), (1.0 * math.cos(a + 0.35), h - 0.3, 1.0 * math.sin(a + 0.35))], (60, 170, 70)) for a in np.linspace(0, 2 * math.pi, 7)[:-1]]
    return cat([cyl(0.12, 0.08, h, 6, (160, 120, 80))] + lv)

def cloud(s=1.0):
    return cat([sphere(0.9 * s, 7, 4, (255, 255, 255), e=0.6), sphere(0.7 * s, 7, 4, (255, 255, 255), e=0.6).mv(0.9 * s, -0.1, 0), sphere(0.6 * s, 7, 4, (255, 255, 255), e=0.6).mv(-0.9 * s, -0.15, 0)])

def lawn_chair_cow(t):
    """Oddity: a cow lounging in a lawn chair under a beach umbrella, reading a newspaper."""
    from models import cow
    c = cow().rot("z", 35, (0, 0.7, 0)).sc(0.8).mv(0, 0.1, 0)
    chair = cat([box(-0.7, 0.3, -0.45, 0.5, 0.36, 0.45, (40, 140, 230)), box(-0.85, 0.3, -0.45, -0.75, 1.1, 0.45, (40, 140, 230)).rot("z", -20, (-0.8, 0.3, 0)),
                 *[box(x - 0.03, 0, z - 0.03, x + 0.03, 0.32, z + 0.03, (200, 200, 206)) for x in (-0.6, 0.4) for z in (-0.42, 0.42)]])
    paper = box(0.35, 1.1, -0.3, 0.37, 1.5, 0.3, (240, 240, 232)).rot("z", -10 + 4 * math.sin(t * 2), (0.35, 1.1, 0))
    umb = cat([cyl(0.03, 0.03, 2.2, 5, (230, 230, 230)).mv(-0.9, 0, 0)] +
              [P([(-0.9, 2.3, 0), (-0.9 + 1.2 * math.cos(a0), 1.95, 1.2 * math.sin(a0)), (-0.9 + 1.2 * math.cos(a1), 1.95, 1.2 * math.sin(a1))],
                 (240, 60, 80) if i % 2 else (255, 240, 120)) for i, (a0, a1) in enumerate((2 * math.pi * k / 8, 2 * math.pi * (k + 1) / 8) for k in range(8))])
    return cat([chair, c, paper, umb])

def snowman_lounger(t):
    """Oddity: a snowman in sunglasses on a sun lounger, sipping a drink, perfectly un-melted."""
    w = (250, 250, 255)
    lounger = cat([box(-0.9, 0.3, -0.35, 0.8, 0.36, 0.35, (255, 120, 40)), box(-1.0, 0.3, -0.35, -0.9, 1.0, 0.35, (255, 120, 40)).rot("z", -30, (-0.95, 0.3, 0)),
                   *[box(x - 0.03, 0, z - 0.03, x + 0.03, 0.32, z + 0.03, (200, 200, 206)) for x in (-0.8, 0.7) for z in (-0.32, 0.32)]])
    body = cat([sphere(0.38, 8, 5, w).mv(0.1, 0.7, 0), sphere(0.28, 8, 5, w).mv(-0.35, 0.95, 0), sphere(0.2, 8, 5, w).mv(-0.6, 1.3, 0)])
    shades = cat([box(-0.47, 1.33, -0.16, -0.43, 1.4, 0.16, (10, 10, 12))])
    nose = cyl(0.04, 0.0, 0.2, 5, (255, 120, 20)).rot("z", -90).mv(-0.42, 1.28, 0)
    hat = cat([cyl(0.2, 0.2, 0.03, 8, (20, 20, 24)), cyl(0.13, 0.13, 0.22, 8, (20, 20, 24))]).rot("z", 20).mv(-0.66, 1.46, 0)
    cup = cat([cyl(0.05, 0.06, 0.16, 6, (80, 200, 230)), box(-0.005, 0.12, -0.005, 0.005, 0.3, 0.005, (255, 80, 160))]).mv(0.05, 1.0 + 0.03 * math.sin(t * 2), 0.32)
    return cat([lounger, body, shades, nose, hat, cup])

def wave_marks(t, col=(255, 230, 60)):
    """Little 'motion' tick marks next to a waving hand (in the XY plane)."""
    a = 0.5 + 0.5 * math.sin(t * 18)
    return cat([box(0.1, 0.05 + 0.08 * i, -0.01, 0.22 + 0.04 * a, 0.08 + 0.08 * i, 0.01, col, e=1.0).rot("z", 20 * (i - 1)) for i in range(3)])

def road(x0, x1, z0=-2.2, z1=2.2, line=(255, 220, 60), step=4.0, col=(70, 72, 80)):
    s = [tiles(x0, z0, x1, z1, 0.0, step, -1, col)]
    s += [box(x, 0.004, -0.06, x + 1.8, 0.01, 0.06, line) for x in np.arange(x0, x1, 4.0)]
    s += [box(x0, 0.004, z0 + 0.1, x1, 0.01, z0 + 0.22, (245, 245, 245)), box(x0, 0.004, z1 - 0.22, x1, 0.01, z1 - 0.1, (245, 245, 245))]
    return s

def screen_tex(lines, w=192, h=112, bg=(20, 28, 44), fg=(240, 244, 250), accent=None, logo=None, big=False):
    im = Image.new("RGB", (w, h), bg); d = ImageDraw.Draw(im)
    d.rectangle((0, 0, w, 14), fill=(36, 48, 70))
    n = len(lines)
    for i, ln in enumerate(lines):
        col = accent if (accent and i == n - 1) else fg
        d.text((w / 2, 14 + (h - 14) * (i + 0.5) / n), ln, font=font(int(min(40 if big else 24, (h - 14) / (n + 0.6)))), fill=col, anchor="mm")
    return tex(im)
