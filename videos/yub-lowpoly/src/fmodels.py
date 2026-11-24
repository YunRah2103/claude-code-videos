"""Ferrari 458, prancing-horse shield, rainbow-cat wrap and props for the ferrari-purrari short (PS1 low-poly)."""
import math
import numpy as np
from PIL import Image, ImageDraw
from lowpoly import P, cat, box, cbox, cyl, sphere, prism, quad, tex, font, rgb
from models import noisy, person, face_tex, CHROME

RED = (196, 14, 18)
NAVY = (22, 30, 92)
RAINBOW = [(230, 30, 40), (245, 140, 20), (250, 230, 40), (60, 200, 60), (40, 140, 240), (120, 60, 200)]

# ---------------------------------------------------------------- textures
def _horse(d, x0, y0, s, col=(12, 12, 12)):
    """Rearing horse silhouette facing left inside an s x s box at (x0, y0)."""
    P_ = lambda pts: [(x0 + x * s, y0 + y * s) for x, y in pts]
    w = max(2, int(s * 0.07))
    d.ellipse(P_([(0.36, 0.42), (0.72, 0.62)]), fill=col)                       # body
    d.polygon(P_([(0.36, 0.5), (0.28, 0.2), (0.38, 0.18), (0.48, 0.44)]), fill=col)   # neck
    d.polygon(P_([(0.2, 0.16), (0.36, 0.12), (0.38, 0.24), (0.24, 0.26)]), fill=col)  # head
    d.polygon(P_([(0.33, 0.1), (0.37, 0.02), (0.39, 0.12)]), fill=col)              # ear
    for a, b, c in (((0.4, 0.5), (0.24, 0.42), (0.2, 0.52)), ((0.42, 0.52), (0.3, 0.5), (0.3, 0.62))):   # raised front legs
        d.line(P_([a, b, c]), fill=col, width=w)
    for a, b, c in (((0.62, 0.58), (0.56, 0.76), (0.5, 0.92)), ((0.68, 0.58), (0.7, 0.78), (0.64, 0.94))):  # hind legs
        d.line(P_([a, b, c]), fill=col, width=w)
    d.line(P_([(0.7, 0.48), (0.82, 0.34), (0.8, 0.16), (0.88, 0.08)]), fill=col, width=w)  # tail up

def _shield(w=64, h=80, sf=True):
    im = Image.new("RGB", (w, h), (20, 20, 20)); d = ImageDraw.Draw(im)
    d.polygon([(2, 2), (w - 3, 2), (w - 3, h * 0.62), (w / 2, h - 2), (2, h * 0.62)], fill=(250, 206, 20))
    for i, c in enumerate([(0, 146, 70), (245, 245, 245), (206, 43, 55)]):
        d.rectangle((2 + i * (w - 4) / 3, 2, 2 + (i + 1) * (w - 4) / 3, 9), fill=c)
    _horse(d, w * 0.14, h * 0.15, w * 0.72)
    if sf: d.text((w / 2, h * 0.8), "SF", font=font(int(h * 0.15)), fill=(12, 12, 12), anchor="mm")
    return im
T_SHIELD = tex(_shield())

def _plaque(w=128, h=128):
    """Rectangular yellow badge with the black prancing horse (dealer wall / key fob)."""
    im = Image.new("RGB", (w, h), (250, 206, 20)); d = ImageDraw.Draw(im)
    d.rectangle((0, 0, w - 1, h - 1), outline=(20, 20, 20), width=5)
    _horse(d, w * 0.12, h * 0.1, w * 0.76)
    return im
T_PLAQUE = tex(_plaque())

def _word(text, w=256, h=48, fg=(250, 206, 20), bg=(16, 16, 18), size=34):
    im = Image.new("RGB", (w, h), bg); d = ImageDraw.Draw(im)
    d.text((w / 2, h / 2), text, font=font(size), fill=fg, anchor="mm"); return im
T_FERRARI_SIGN = tex(_word("FERRARI", fg=(255, 220, 40)))
T_FERRARI_REAR = tex(_word("FERRARI", 160, 24, (220, 220, 226), RED, 18))
T_PLATE = tex(_word("PURRARI", 96, 24, (20, 20, 20), (238, 238, 232), 16))

def _hub():
    im = Image.new("RGB", (96, 96), (20, 20, 22)); d = ImageDraw.Draw(im)
    for i in range(5):
        a = 2 * math.pi * i / 5
        for o in (-0.12, 0.12):
            d.line((48, 48, 48 + 44 * math.cos(a + o), 48 + 44 * math.sin(a + o)), fill=(196, 198, 204), width=6)
    d.ellipse((2, 2, 93, 93), outline=(210, 210, 216), width=5)
    d.ellipse((36, 36, 60, 60), fill=(250, 206, 20)); _horse(d, 38, 38, 20)
    return im
T_HUB = tex(_hub())

def _wrap_art(w=256, h=64):
    """Generic rainbow-trail cat livery: navy with stars, a rainbow band, a grey cartoon cat near the front (+u)."""
    im = Image.new("RGB", (w, h), NAVY); d = ImageDraw.Draw(im); r = np.random.default_rng(5)
    for x, y in r.integers(0, (w, h), (40, 2)): d.rectangle((x, y, x + 1, y + 1), fill=(255, 255, 255))
    for i, c in enumerate(RAINBOW):
        y = 24 + i * 4
        for x in range(0, int(w * 0.62), 16):              # stepped "wavy" trail
            d.rectangle((x, y + (2 if (x // 16) % 2 else 0), x + 15, y + 3 + (2 if (x // 16) % 2 else 0)), fill=c)
    cx = int(w * 0.72)
    d.rectangle((cx - 22, 22, cx + 14, 50), fill=(150, 150, 160))               # body
    d.rectangle((cx + 8, 18, cx + 34, 44), fill=(160, 160, 170))                # head
    d.polygon([(cx + 9, 18), (cx + 13, 10), (cx + 18, 18)], fill=(160, 160, 170))
    d.polygon([(cx + 24, 18), (cx + 29, 10), (cx + 33, 18)], fill=(160, 160, 170))
    for ex in (cx + 15, cx + 27): d.rectangle((ex - 2, 26, ex + 1, 29), fill=(10, 10, 10))
    d.rectangle((cx + 12, 33, cx + 15, 35), fill=(255, 120, 160)); d.rectangle((cx + 26, 33, cx + 29, 35), fill=(255, 120, 160))
    d.line((cx + 17, 37, cx + 21, 39, cx + 25, 37), fill=(10, 10, 10), width=1)
    for lx in (cx - 18, cx - 8, cx + 2, cx + 10): d.rectangle((lx, 50, lx + 5, 56), fill=(150, 150, 160))
    d.rectangle((cx - 30, 30, cx - 22, 34), fill=(150, 150, 160))               # tail
    return im
_WRAP = _wrap_art()

def _wrap_progress(p, w=256, h=64):
    """Side texture with the wrap applied from the front (u=1) back to 1-p; the rest stays Rosso red."""
    im = Image.new("RGB", (w, h), RED); x = int(w * (1 - p))
    if p > 0: im.paste(_WRAP.crop((x, 0, w, h)), (x, 0))
    if 0 < p < 1:
        d = ImageDraw.Draw(im); d.rectangle((x - 2, 0, x, h), fill=(235, 235, 240))   # the vinyl's edge
    return im
WRAP_STEPS = 12
T_WRAP = [tex(_wrap_progress(i / WRAP_STEPS)) for i in range(WRAP_STEPS + 1)]
T_WRAP_ROLL = tex(_WRAP.resize((64, 16)))

def _bill():
    im = Image.new("RGB", (64, 28), (120, 170, 120)); d = ImageDraw.Draw(im)
    d.rectangle((1, 1, 62, 26), outline=(40, 90, 50), width=2); d.ellipse((24, 5, 40, 23), fill=(90, 140, 96))
    d.ellipse((28, 8, 36, 16), fill=(60, 110, 70))
    return im
T_BILL = tex(_bill())

def _doc(title, lines=7, stamp=None, sign=0.0, sub=None, empty=False):
    im = Image.new("RGB", (64, 84), (240, 238, 230)); d = ImageDraw.Draw(im)
    d.text((32, 8), title, font=font(7), fill=(30, 30, 30), anchor="mm")
    if sub: d.text((32, 17), sub, font=font(5), fill=(150, 20, 20), anchor="mm")
    for i, y in enumerate(range(24, 24 + 7 * lines, 7)):
        d.line((6, y, 58 if not empty else 58, y), fill=(170, 170, 170) if empty else (120, 120, 120))
        if not empty: d.line((6, y - 2, 6 + (37 * (i + 3)) % 46 + 8, y - 2), fill=(60, 60, 60))
    if sign > 0:                      # handwritten signature growing left to right
        pts = [(8 + i * 2, 76 + 3 * math.sin(i * 1.3)) for i in range(int(22 * sign))]
        if len(pts) > 1: d.line(pts, fill=(20, 30, 120), width=2)
    if stamp:
        s = Image.new("RGBA", (64, 30), (0, 0, 0, 0)); ds = ImageDraw.Draw(s)
        ds.rectangle((2, 2, 61, 27), outline=(200, 20, 30, 255), width=3)
        ds.text((32, 15), stamp, font=font(9), fill=(200, 20, 30, 255), anchor="mm")
        s = s.rotate(14, expand=True, resample=Image.NEAREST); im.paste(s, (32 - s.width // 2, 48 - s.height // 2), s)
    return im
T_CONTRACT = [tex(_doc("SALES CONTRACT", sub="NO RESALE - FIRST YEAR", sign=k / 6)) for k in range(7)]
T_LETTER = tex(_doc("CEASE AND DESIST", lines=6))
T_BLACKLIST = tex(_doc("BLACKLIST", lines=8, empty=True))

def _envelope():
    im = Image.new("RGB", (64, 40), (232, 224, 200)); d = ImageDraw.Draw(im)
    d.line((0, 0, 32, 22, 63, 0), fill=(180, 170, 150), width=2)
    d.ellipse((25, 15, 39, 29), fill=(170, 16, 20)); _horse(d, 27, 17, 10, (240, 200, 60))
    return im
T_ENVELOPE = tex(_envelope())

def _sign(text, bg, fg, w=96, h=48, size=20):
    im = Image.new("RGB", (w, h), bg); d = ImageDraw.Draw(im)
    d.rectangle((0, 0, w - 1, h - 1), outline=fg, width=3); d.text((w / 2, h / 2), text, font=font(size), fill=fg, anchor="mm")
    return im
T_FORSALE = tex(_sign("FOR SALE", (250, 250, 245), (200, 20, 30), size=17))
T_NO = tex(_sign("NO", (200, 20, 30), (255, 255, 255), 64, 40, 26))
T_YES_BTN = tex(_sign("YES", (40, 170, 70), (255, 255, 255), 64, 64, 22))
T_NO_BTN = tex(_sign("NO", (200, 30, 36), (255, 255, 255), 64, 64, 22))

def _stars(w=270, h=480):
    a = np.zeros((h, w, 3), np.float32); g = np.linspace(0, 1, h)[:, None, None]
    a[:] = np.float32([8, 10, 40]) / 255 * (1 - g) + np.float32([40, 26, 80]) / 255 * g
    r = np.random.default_rng(8)
    for x, y in r.integers(0, (w, int(h * 0.75)), (90, 2)): a[y, x] = 0.9
    return a
STAR_BG = _stars()

# ---------------------------------------------------------------- the car
def wheel(x, z, spin=0.0):
    w = cyl(0.34, 0.34, 0.25, 12, (18, 18, 20), captex=T_HUB)
    return w.mv(0, -0.125, 0).rot("x", 90).rot("z", spin).mv(x, 0.34, z)

def f458(wrap=0.0, spin=0.0, plate=False, sale=False, body=RED, no=None):
    """Ferrari 458 along +x (front at +x), centred, wheels on y=0. wrap 0..1 = how much of the cat livery is on."""
    k = int(round(wrap * WRAP_STEPS)); col = body if wrap < 0.55 else NAVY
    side = (255, 255, 255)
    def taper(v):
        q = np.clip((v[:, 1] - 0.55) / 0.7, 0, 1); v[:, 2] *= 1 - 0.16 * q; return v
    pts = [(-2.25, 0.18), (2.25, 0.18), (2.3, 0.42), (1.9, 0.62), (1.0, 0.76), (0.55, 0.83), (-1.65, 0.93), (-2.25, 0.92), (-2.3, 0.55)]
    bod = prism(pts, -0.97, 0.97, col, captex=T_WRAP[k] if k else -1).fn(taper)
    if not k: bod.c[:] = rgb(col)
    glass = prism([(0.62, 0.8), (-0.1, 1.2), (-0.85, 1.19), (-1.5, 0.9)], -0.74, 0.74, (26, 30, 38)).fn(taper)
    roof = prism([(-0.12, 1.19), (-0.86, 1.18), (-0.86, 1.215), (-0.12, 1.225)], -0.6, 0.6, col)
    louvre = box(-2.0, 0.92, -0.42, -1.4, 0.95, 0.42, (18, 18, 20))
    intakes = [box(-1.25, 0.4, s * 0.94 - 0.03, -0.72, 0.68, s * 0.94 + 0.03, (14, 14, 16)) for s in (1, -1)]
    grille = box(2.24, 0.22, -0.78, 2.31, 0.4, 0.78, (14, 14, 16))
    heads = [box(1.72, 0.58, s * 0.88 - 0.17, 2.16, 0.65, s * 0.88 + 0.17, (255, 250, 235), e=1.0) for s in (1, -1)]
    tails = [cyl(0.1, 0.1, 0.04, 8, (235, 30, 20), e=1.0).rot("z", 90).mv(-2.27, 0.72, s * 0.68) for s in (1, -1)]
    pipes = [cyl(0.05, 0.05, 0.06, 6, (60, 60, 64), capcol=(10, 10, 10)).rot("z", 90).mv(-2.27, 0.32, z) for z in (-0.12, 0, 0.12)]
    shields = [box(1.48, 0.55, 0.88, 1.6, 0.71, 0.9, side, texs={"f": T_SHIELD}).mv(0, 0, 0.02),
               box(1.48, 0.55, -0.9, 1.6, 0.71, -0.88, side, texs={"b": T_SHIELD}).mv(0, 0, -0.02)]
    nose = box(2.25, 0.44, -0.07, 2.33, 0.56, 0.07, side, texs={"r": T_PLAQUE})
    rear = box(-2.32, 0.55, -0.4, -2.28, 0.62, 0.4, side, texs={"l": T_FERRARI_REAR})
    mirrors = [cbox(0.42, 0.9, s * 0.97, 0.16, 0.08, 0.14, col) for s in (1, -1)]
    wheels = [wheel(x, z * 0.86, spin) for x in (1.35, -1.3) for z in (1, -1)]
    parts = [bod, glass, roof, louvre, grille, nose, rear, *intakes, *heads, *tails, *pipes, *shields, *mirrors, *wheels]
    if plate: parts.append(box(2.31, 0.24, -0.25, 2.34, 0.36, 0.25, side, texs={"r": T_PLATE}))
    if sale: parts.append(box(0.2, 0.92, -0.25, 0.24, 1.08, 0.25, side, texs={"r": T_FORSALE}).rot("z", 40, (0.22, 0.95, 0)))
    if no is not None:   # red NO card dropping onto the FOR SALE sign (no = remaining drop, 0 = landed)
        parts.append(box(0.27, 0.95, -0.17, 0.29, 1.07, 0.17, side, texs={"r": T_NO}).rot("z", 40, (0.22, 0.95, 0)).mv(0.9 * no, 0.9 * no, 0))
    return cat(parts)

def trail(length=6.0, wave=0.0, y0=0.35, h=0.42, z=0.0, n=12):
    """Rainbow ribbon behind something travelling +x (ends at x=0), stepped like a pixel trail."""
    out = []
    for i in range(n):
        x0, x1 = -length * (i + 1) / n, -length * i / n
        off = 0.06 * (1 if (i + int(wave)) % 2 else -1)
        for j, c in enumerate(RAINBOW):
            ya = y0 + off + h * (len(RAINBOW) - 1 - j) / len(RAINBOW); yb = ya + h / len(RAINBOW)
            out.append(quad((x0, ya, z), (x1, ya, z), (x1, yb, z), (x0, yb, z), c, e=1.0))
    return cat(out)

def rcat(t=0.0):
    """Generic grey cartoon cat, faces +x, ~0.5 m long at scale 1; legs paddle with t."""
    g, gd = (156, 156, 166), (120, 120, 130)
    parts = [cbox(0, 0.3, 0, 0.46, 0.26, 0.3, g),
             cbox(0.3, 0.38, 0, 0.24, 0.22, 0.26, g, texs={"r": T_CATFACE}),
             P([(0.24, 0.49, 0.06), (0.24, 0.49, 0.12), (0.27, 0.58, 0.09)], g), P([(0.24, 0.49, -0.06), (0.24, 0.49, -0.12), (0.27, 0.58, -0.09)], g),
             cbox(-0.28, 0.36, 0, 0.14, 0.05, 0.05, gd)]
    for i, (x, z) in enumerate(((0.16, 0.1), (0.16, -0.1), (-0.16, 0.1), (-0.16, -0.1))):
        parts.append(cbox(x + 0.04 * math.sin(t * 14 + i * 1.6), 0.13, z, 0.07, 0.12, 0.07, gd))
    return cat(parts)

def _catface():
    im = Image.new("RGB", (32, 32), (160, 160, 170)); d = ImageDraw.Draw(im)
    for x in (9, 21): d.rectangle((x - 2, 11, x + 2, 15), fill=(10, 10, 10)); d.point((x, 12), fill=(255, 255, 255))
    for x in (5, 25): d.rectangle((x - 2, 18, x + 2, 20), fill=(255, 120, 160))
    d.line((12, 21, 16, 24, 20, 21), fill=(10, 10, 10)); return im
T_CATFACE = tex(_catface())

def flying_cat(t=0.0, length=3.0):
    return cat([rcat(t), trail(length, t * 10, 0.18, 0.28, 0.0, 8)])

# ---------------------------------------------------------------- props
def desk(w=2.4, d=1.0):
    from models import T_WOOD_DARK
    return cat([box(-w / 2, 0.72, -d / 2, w / 2, 0.78, d / 2, (255, 255, 255), texs={"t": T_WOOD_DARK, "f": T_WOOD_DARK}),
                box(-w / 2 + 0.05, 0, -d / 2 + 0.05, -w / 2 + 0.12, 0.72, d / 2 - 0.05, (40, 30, 24)),
                box(w / 2 - 0.12, 0, -d / 2 + 0.05, w / 2 - 0.05, 0.72, d / 2 - 0.05, (40, 30, 24))])

def briefcase(open_=1.0):
    """Lies on its back, hinge at -z. Lid opens up to 100 degrees; the base is full of bill stacks."""
    base = box(-0.3, 0, -0.2, 0.3, 0.1, 0.2, (30, 24, 20))
    lid = box(-0.3, 0, -0.2, 0.3, 0.03, 0.2, (36, 28, 22)).rot("x", -100 * open_, (0, 0.03, -0.2)).mv(0, 0.1, 0)
    stacks = [box(x - 0.12, 0.1, z - 0.07, x + 0.12, 0.13, z + 0.07, (255, 255, 255), texs={"t": T_BILL, "f": T_BILL})
              for x in (-0.14, 0.14) for z in (-0.09, 0.09)]
    handle = box(-0.08, 0.04, 0.2, 0.08, 0.07, 0.24, (20, 16, 14))
    return cat([base, lid, handle, *stacks])

def velvet_rope(sag=0.0, x0=-1.2, x1=1.2):
    posts = [cat([cyl(0.18, 0.18, 0.04, 8, CHROME), cyl(0.035, 0.035, 0.95, 6, CHROME).mv(0, 0.04, 0),
                  sphere(0.06, 6, 4, CHROME).mv(0, 1.0, 0)]).mv(x, 0, 0) for x in (x0, x1)]
    n = 10; rope = []
    for i in range(n):
        a, b = i / n, (i + 1) / n
        ya = 0.92 - (0.28 + sag) * math.sin(math.pi * a); yb = 0.92 - (0.28 + sag) * math.sin(math.pi * b)
        xa, xb = x0 + (x1 - x0) * a, x0 + (x1 - x0) * b
        rope.append(box(min(xa, xb), min(ya, yb) - 0.03, -0.03, max(xa, xb), max(ya, yb) + 0.03, 0.03, (150, 16, 30)))
    return cat(posts + rope)

def key_fob():
    return cat([box(-0.05, -0.08, -0.015, 0.05, 0.08, 0.015, (255, 255, 255), texs={"f": T_PLAQUE, "b": T_PLAQUE}),
                cyl(0.035, 0.035, 0.01, 8, CHROME, cap=False).rot("x", 90).mv(0, 0.11, 0),
                box(-0.012, 0.13, -0.006, 0.012, 0.25, 0.006, CHROME)])

def cover_sheet(lift=0.0):
    """Silk cover over a car-sized shape; lift 0..1 raises and slides it off backwards."""
    c = (214, 210, 200)
    sh = prism([(-2.4, 0.0), (2.4, 0.0), (2.4, 0.6), (0.6, 1.0), (-0.9, 1.3), (-2.4, 1.0)], -1.05, 1.05, c)
    return sh.rot("z", -25 * lift, (-2.4, 0, 0)).mv(-3.0 * lift, 2.2 * lift, 0)

def button(tid, press=0.0):
    return cat([cyl(0.42, 0.42, 0.12, 12, (40, 40, 44)), cyl(0.34, 0.34, 0.1 - 0.06 * press, 12, (255, 255, 255), captex=tid).mv(0, 0.12, 0)])

SUIT = dict(top=(22, 22, 26), legs=(22, 22, 26), shirt=(240, 240, 240))
F_SALES = face_tex(skin=(220, 180, 150), hair=(40, 30, 24), mouth="flat")
F_EXEC = face_tex(skin=(205, 165, 130), hair=(150, 150, 150), mouth="flat", brows=(60, 60, 60))
F_BUYERS = [face_tex(skin=s, hair=h, mouth=m) for s, h, m in (((230, 190, 160), (90, 60, 30), "smile"), ((150, 100, 70), (20, 20, 20), "flat"),
                                                              ((200, 160, 120), (200, 190, 160), "open"), ((120, 80, 56), (30, 26, 22), "smile"))]
def salesman(**kw):
    a = dict(SUIT, skin=(220, 180, 150), face=F_SALES, hair=(40, 30, 24)); a.update(kw); return person(**a)
