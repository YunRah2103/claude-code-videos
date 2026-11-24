"""Low-poly models and hand-drawn textures for the rolls-royce-pinstripe style test."""
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from lowpoly import P, cat, box, cbox, cyl, sphere, prism, quad, tex, font, rgb

rng = np.random.default_rng(3)

def noisy(size, base, amt=14, seed=0):
    r = np.random.default_rng(seed)
    a = np.float32(rgb(base) * 255)[None, None] + r.normal(0, amt, (size[1], size[0], 1))
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))

# ---------------------------------------------------------------- textures
def _rr_badge(w=128, h=160, bg=(18, 18, 22), fg=(214, 214, 220)):
    im = Image.new("RGB", (w, h), (170, 170, 176)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((5, 5, w - 6, h - 6), 10, fill=bg, outline=fg, width=4)
    f = font(int(h * 0.42), serif=True); fs = font(int(h * 0.09), serif=True)
    d.text((w * 0.33, h * 0.5), "R", font=f, fill=fg, anchor="mm")
    d.text((w * 0.65, h * 0.53), "R", font=f, fill=fg, anchor="mm")
    d.text((w / 2, h * 0.16), "ROLLS", font=fs, fill=fg, anchor="mm")
    d.text((w / 2, h * 0.86), "ROYCE", font=fs, fill=fg, anchor="mm")
    return im
T_BADGE = tex(_rr_badge())

def _hub():
    im = Image.new("RGB", (96, 96), (40, 40, 44)); d = ImageDraw.Draw(im)
    for i in range(10):
        a = 2 * math.pi * i / 10
        d.line((48, 48, 48 + 44 * math.cos(a), 48 + 44 * math.sin(a)), fill=(190, 190, 198), width=6)
    d.ellipse((2, 2, 93, 93), outline=(205, 205, 212), width=5)
    d.ellipse((28, 28, 68, 68), fill=(20, 20, 24), outline=(220, 220, 226), width=3)
    f = font(24, serif=True); d.text((40, 48), "R", font=f, fill=(225, 225, 230), anchor="mm"); d.text((57, 49), "R", font=f, fill=(225, 225, 230), anchor="mm")
    return im
T_HUB = tex(_hub())

def _grille():
    im = Image.new("RGB", (64, 64), (25, 25, 28)); d = ImageDraw.Draw(im)
    for x in range(2, 64, 5): d.rectangle((x, 0, x + 2, 63), fill=(222, 222, 228))
    d.rectangle((0, 0, 63, 63), outline=(240, 240, 245), width=3)
    return im
T_GRILLE = tex(_grille())

def _tiles(c1=(156, 158, 162), c2=(120, 122, 126)):
    im = noisy((64, 64), c1, 6, 1); d = ImageDraw.Draw(im)
    d.line((0, 0, 63, 0), fill=c2, width=2); d.line((0, 0, 0, 63), fill=c2, width=2)
    return im
T_TILE = tex(_tiles((118, 118, 114), (84, 84, 80)))
T_TILE_DARK = tex(_tiles((52, 52, 58), (30, 30, 34)))

def _panel():
    im = noisy((64, 64), (150, 150, 146), 10, 2); d = ImageDraw.Draw(im); r = np.random.default_rng(9)
    for _ in range(5):          # damp stains
        x, y = r.integers(4, 60, 2); d.ellipse((x - 6, y - 3, x + 6, y + 9), fill=(126, 126, 120))
    d.rectangle((0, 0, 63, 63), outline=(96, 96, 94), width=2)
    for y in (20, 42): d.line((4, y, 59, y), fill=(132, 132, 128), width=1)
    for x in (8, 56):
        for y in (6, 58): d.point((x, y), fill=(60, 60, 60))
    return im
T_PANEL = tex(_panel())

def _brick():
    im = Image.new("RGB", (64, 64), (70, 52, 44)); d = ImageDraw.Draw(im); r = np.random.default_rng(5)
    for row in range(8):
        off = 0 if row % 2 else 8
        for c in range(-1, 5):
            x = c * 16 + off; tone = r.integers(-18, 18)
            d.rectangle((x + 1, row * 8 + 1, x + 14, row * 8 + 6), fill=(128 + tone, 58 + tone // 2, 44 + tone // 3))
    return im
T_BRICK = tex(_brick())

def _cobble():
    im = Image.new("RGB", (64, 64), (38, 38, 44)); d = ImageDraw.Draw(im); r = np.random.default_rng(6)
    for y in range(0, 64, 10):
        for x in range(-6, 64, 12):
            xx = x + (6 if (y // 10) % 2 else 0); g = int(r.integers(62, 92))
            d.rounded_rectangle((xx + 1, y + 1, xx + 10, y + 8), 3, fill=(g, g, g + 6))
    return im
T_COBBLE = tex(_cobble())

def _wood(c=(120, 78, 44)):
    im = noisy((64, 64), c, 8, 7); d = ImageDraw.Draw(im)
    for y in range(0, 64, 6): d.line((0, y, 63, y + 2), fill=tuple(max(0, v - 25) for v in c), width=1)
    return im
T_WOOD = tex(_wood())
T_WOOD_DARK = tex(_wood((70, 40, 26)))

def _pubsign():
    im = Image.new("RGB", (128, 160), (22, 48, 36)); d = ImageDraw.Draw(im)
    d.rectangle((3, 3, 124, 156), outline=(212, 176, 90), width=5)
    f = font(17, serif=True)
    d.text((64, 26), "THE", font=f, fill=(232, 200, 110), anchor="mm")
    d.text((64, 46), "SQUIRREL", font=f, fill=(232, 200, 110), anchor="mm")
    d.text((64, 136), "& BRUSH", font=f, fill=(232, 200, 110), anchor="mm")
    # painted squirrel
    d.ellipse((44, 70, 78, 116), fill=(170, 92, 40)); d.ellipse((66, 62, 86, 82), fill=(170, 92, 40))
    d.ellipse((24, 58, 54, 112), fill=(190, 110, 50)); d.ellipse((78, 68, 82, 72), fill=(10, 10, 10))
    d.polygon([(70, 64), (74, 54), (78, 64)], fill=(170, 92, 40))
    d.line((86, 90, 106, 78), fill=(220, 210, 190), width=3)
    return im
T_PUBSIGN = tex(_pubsign())
T_PUBSIGN_HALF = None

def _window(c=(255, 196, 110)):
    im = Image.new("RGB", (32, 32), c); d = ImageDraw.Draw(im)
    d.rectangle((0, 0, 31, 31), outline=(40, 30, 24), width=3); d.line((16, 0, 16, 31), fill=(40, 30, 24), width=2)
    d.line((0, 16, 31, 16), fill=(40, 30, 24), width=2)
    return im
T_WIN = tex(_window())
T_WIN_COOL = tex(_window((170, 200, 225)))

def _clock():
    im = Image.new("RGB", (96, 96), (238, 234, 220)); d = ImageDraw.Draw(im)
    d.ellipse((1, 1, 94, 94), outline=(30, 30, 30), width=5)
    for i in range(12):
        a = 2 * math.pi * i / 12; r0 = 36 if i % 3 else 30
        d.line((48 + r0 * math.cos(a), 48 + r0 * math.sin(a), 48 + 42 * math.cos(a), 48 + 42 * math.sin(a)), fill=(30, 30, 30), width=3 if i % 3 else 5)
    return im
T_CLOCK = tex(_clock())

def _calendar(month):
    im = Image.new("RGB", (64, 80), (246, 244, 238)); d = ImageDraw.Draw(im)
    d.rectangle((0, 0, 63, 16), fill=(170, 32, 40)); d.text((32, 8), month, font=font(10), fill=(255, 255, 255), anchor="mm")
    for r in range(5):
        for c in range(7): d.rectangle((3 + c * 8.4, 21 + r * 11, 9 + c * 8.4, 29 + r * 11), outline=(150, 150, 150))
    return im
MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
T_CAL = [tex(_calendar(m)) for m in MONTHS]

def _paper(stamp=False):
    im = Image.new("RGB", (64, 80), (240, 238, 230)); d = ImageDraw.Draw(im)
    d.text((32, 9), "APPLICATION", font=font(7), fill=(40, 40, 40), anchor="mm")
    for y in range(18, 74, 7): d.line((6, y, 58, y), fill=(160, 160, 160))
    if stamp:
        d.rotated = None
        s = Image.new("RGBA", (64, 30), (0, 0, 0, 0)); ds = ImageDraw.Draw(s)
        ds.rectangle((2, 2, 61, 27), outline=(200, 20, 30, 255), width=3); ds.text((32, 15), "NOT HIRED", font=font(10), fill=(200, 20, 30, 255), anchor="mm")
        s = s.rotate(14, expand=True, resample=Image.NEAREST); im.paste(s, (32 - s.width // 2, 44 - s.height // 2), s)
    return im
T_PAPER = tex(_paper()); T_PAPER_STAMP = tex(_paper(True))

def _hivis():
    im = Image.new("RGB", (32, 32), (230, 240, 40)); d = ImageDraw.Draw(im)
    d.rectangle((0, 12, 31, 16), fill=(220, 220, 220)); return im
T_HIVIS = tex(_hivis())

def _cowhide():
    im = Image.new("RGB", (64, 64), (236, 232, 226)); d = ImageDraw.Draw(im)
    for x, y, r in ((12, 14, 10), (44, 30, 13), (20, 48, 9), (54, 6, 7)): d.ellipse((x - r, y - r, x + r, y + r * 0.8), fill=(26, 24, 24))
    return im
T_COW = tex(_cowhide())

def _face(skin, hair, glasses=False, mouth="smile", brows=(30, 22, 18), beard=None, eyes_wide=False):
    """64x64 PS1-style face texture."""
    s = np.float32(skin)
    im = Image.new("RGB", (64, 64), tuple(int(v) for v in s)); d = ImageDraw.Draw(im)
    dark = tuple(int(v * 0.72) for v in s)
    d.rectangle((0, 0, 63, 9), fill=hair)                      # hairline
    d.rectangle((0, 0, 4, 30), fill=hair); d.rectangle((59, 0, 63, 30), fill=hair)
    ew = 5 if eyes_wide else 4
    for cx in (21, 43):
        d.ellipse((cx - 6, 25 - ew, cx + 6, 25 + ew), fill=(245, 245, 240))
        d.ellipse((cx - 3, 25 - 3, cx + 3, 25 + 3), fill=(40, 28, 22))
        d.point((cx + 1, 24), fill=(255, 255, 255))
        d.line((cx - 7, 16, cx + 6, 15), fill=brows, width=3)
    if glasses:
        for cx in (21, 43): d.rectangle((cx - 9, 18, cx + 9, 32), outline=(120, 124, 132), width=3)
        d.line((30, 24, 34, 24), fill=(120, 124, 132), width=3)
    d.polygon([(32, 28), (28, 40), (35, 40)], fill=dark)
    if beard: d.rectangle((6, 44, 57, 63), fill=beard); d.ellipse((14, 40, 50, 63), fill=beard)
    if mouth == "smile":
        d.chord((20, 40, 44, 56), 0, 180, fill=(120, 30, 30)); d.rectangle((23, 48, 41, 50), fill=(250, 250, 250))
    elif mouth == "open":
        d.ellipse((25, 44, 39, 57), fill=(90, 20, 20))
    else:
        d.line((24, 50, 40, 50), fill=(110, 50, 40), width=3)
    return im

def face_tex(**kw): return tex(_face(**kw))

# ---------------------------------------------------------------- Rolls-Royce Phantom (approx. 5.8 m long)
PH_BODY = (20, 26, 52)        # Midnight blue
CHROME = (205, 208, 214)
GOLD = (222, 176, 60)

def spirit_of_ecstasy():
    """Kneeling-forward figurine with swept-back wings, ~0.12 m."""
    s = (226, 228, 234)
    body = cbox(0, 0.05, 0, 0.03, 0.08, 0.02, s).rot("z", -35, (0, 0, 0))
    head = sphere(0.014, 6, 4, s).mv(0.035, 0.1, 0)
    w1 = P([(0.0, 0.07, 0.008), (-0.07, 0.11, 0.035), (-0.045, 0.05, 0.02)], s)
    w2 = P([(0.0, 0.07, -0.008), (-0.07, 0.11, -0.035), (-0.045, 0.05, -0.02)], s)
    base = cyl(0.02, 0.016, 0.02, 6, s).mv(0, -0.02, 0)
    return cat([body, head, w1, w2, base])

def wheel(x, z, spin=0.0):
    w = cyl(0.43, 0.43, 0.27, 12, (22, 22, 24), captex=T_HUB)
    w.mv(0, -0.135, 0).rot("y", 0).rot("x", 90).rot("z", spin)
    return w.mv(x, 0.43, z)

def phantom(line=1.0, line_wobble=0.0, line_side=(1, -1), spin=0.0, line_col=GOLD):
    """Car along +x (front at +x), centred at origin, wheels on y=0. line: fraction of coachline painted (0..1)."""
    body = prism([(-2.92, 0.28), (2.9, 0.28), (2.95, 0.66), (2.88, 1.02), (1.1, 1.08), (-2.1, 1.1), (-2.86, 1.0), (-2.95, 0.66)],
                 -1.0, 1.0, PH_BODY)
    def taper(v):
        k = np.clip((v[:, 1] - 1.06) / 0.56, 0, 1); v[:, 2] *= 1 - 0.18 * k; return v
    glass = prism([(-1.95, 1.06), (1.0, 1.06), (0.32, 1.6), (-1.42, 1.64)], -0.93, 0.93, (40, 52, 66)).fn(taper)
    roof = prism([(-1.4, 1.6), (0.3, 1.58), (0.34, 1.63), (-1.42, 1.66)], -0.77, 0.77, PH_BODY)
    pill = [cbox(x, 1.33, 0, 0.09, 0.56, 1.72, PH_BODY).fn(taper) for x in (-0.45,)]
    sill = box(-2.0, 0.28, -1.02, 1.9, 0.4, 1.02, (12, 14, 26))
    grille = box(2.88, 0.5, -0.38, 3.02, 1.02, 0.38, CHROME, texs={"r": T_GRILLE})
    badge = box(3.02, 0.9, -0.07, 3.04, 1.0, 0.07, CHROME, texs={"r": T_BADGE})
    lamps = [box(2.9, 0.82, s * 0.92, 2.97, 0.92, s * 0.5, (255, 250, 230), e=1.0) for s in (1, -1)]
    tail = [box(-2.97, 0.7, s * 0.95, -2.9, 0.9, s * 0.6, (200, 20, 20), e=1.0) for s in (1, -1)]
    bumper = [box(2.9, 0.3, -0.98, 3.0, 0.42, 0.98, CHROME), box(-3.0, 0.3, -0.98, -2.9, 0.42, 0.98, CHROME)]
    mirrors = [cbox(0.95, 1.12, s * 1.06, 0.18, 0.1, 0.14, PH_BODY) for s in (1, -1)]
    handles = [cbox(x, 0.95, s * 1.005, 0.14, 0.03, 0.02, CHROME) for x in (0.4, -0.95) for s in (1, -1)]
    soe = spirit_of_ecstasy().sc(1.4).mv(2.96, 1.05, 0)
    wheels = [wheel(x, z * 0.93, spin) for x in (1.8, -1.78) for z in (1, -1)]
    arches = [cyl(0.5, 0.5, 2.05, 10, (8, 8, 10), cap=False).mv(0, -1.025, 0).rot("x", 90).mv(x, 0.43, 0) for x in (1.8, -1.78)]
    parts = [body, glass, roof, sill, grille, badge, soe, *lamps, *tail, *bumper, *mirrors, *handles, *pill, *wheels]
    parts.append(coachline(line, line_wobble, line_side, line_col))
    return cat(parts)

def coachline(frac, wobble=0.0, sides=(1, -1), col=GOLD, seed=4):
    """Gold line along the shoulder, from the front wheel arch backwards. Exaggerated thickness for the low-res raster."""
    if frac <= 0: return None
    x0, x1 = 2.55, -2.7
    n = 40; out = []
    r = np.random.default_rng(seed); wob = np.cumsum(r.normal(0, 1, n + 1)); wob = (wob - wob.mean()) / (np.abs(wob).max() + 1e-6)
    xe = x0 + (x1 - x0) * frac
    for s in sides:
        for i in range(n):
            a = x0 + (xe - x0) * i / n; b = x0 + (xe - x0) * (i + 1) / n
            ya = 0.985 + wobble * 0.05 * wob[i]; yb = 0.985 + wobble * 0.05 * wob[i + 1]
            z = s * 1.012
            out.append(quad((a, ya - 0.012, z), (b, yb - 0.012, z), (b, yb + 0.012, z), (a, ya + 0.012, z), col, e=0.6))
    return cat(out)

# ---------------------------------------------------------------- people
def person(skin=(198, 150, 110), top=(40, 50, 80), legs=(40, 44, 58), shoes=(20, 20, 20), face=-1,
           hair=(30, 22, 18), hat=None, spiky=False, shirt=None, apron=None,
           la=(0, 0, 0), ra=(0, 0, 0), head=(0, 0), held=None, step=0.0, lean=0.0):
    """Faces +z, feet at y=0. la/ra = (raise forward deg, out to the side deg, elbow bend deg). head = (yaw, pitch).
    held: part placed in the right hand (hand at origin, pointing +z)."""
    parts = []
    for sx, ph in ((-0.11, step), (0.11, -step)):
        leg = box(sx - 0.085, 0.07, -0.09, sx + 0.085, 0.9, 0.09, legs).rot("x", ph, (0, 0.9, 0))
        foot = box(sx - 0.09, 0, -0.1, sx + 0.09, 0.08, 0.17, shoes).rot("x", ph, (0, 0.9, 0))
        parts += [leg, foot]
    tor = box(-0.23, 0.88, -0.13, 0.23, 1.47, 0.13, top)
    parts.append(tor)
    if shirt: parts.append(P([(-0.1, 1.46, 0.132), (0.1, 1.46, 0.132), (0, 1.15, 0.132)], shirt))
    if apron: parts.append(box(-0.2, 0.55, 0.13, 0.2, 1.3, 0.15, apron))
    hd = [box(-0.025, 1.46, -0.05, 0.025, 1.52, 0.05, skin),
          box(-0.13, 1.5, -0.13, 0.13, 1.8, 0.13, skin, faces={"t": hair, "b": hair}, texs={"f": face} if face >= 0 else None)]
    if spiky:
        for i, (x, z) in enumerate([(-0.09, -0.06), (0, -0.08), (0.09, -0.06), (-0.06, 0.05), (0.06, 0.05), (0, 0)]):
            hd.append(P([(x - 0.07, 1.79, z - 0.06), (x + 0.07, 1.79, z - 0.06), (x + (0.03 if i % 2 else -0.03), 1.98, z + 0.02),
                         (x + 0.07, 1.79, z - 0.06), (x + 0.07, 1.79, z + 0.07), (x + (0.03 if i % 2 else -0.03), 1.98, z + 0.02),
                         (x - 0.07, 1.79, z + 0.07), (x - 0.07, 1.79, z - 0.06), (x + (0.03 if i % 2 else -0.03), 1.98, z + 0.02),
                         (x + 0.07, 1.79, z + 0.07), (x - 0.07, 1.79, z + 0.07), (x + (0.03 if i % 2 else -0.03), 1.98, z + 0.02)], hair))
        hd.append(box(-0.14, 1.66, -0.14, 0.14, 1.82, -0.05, hair))
    if hat:
        hd.append(box(-0.14, 1.78, -0.14, 0.14, 1.86, 0.14, hat)); hd.append(box(-0.13, 1.78, 0.12, 0.13, 1.8, 0.24, hat))
    h = cat(hd).rot("x", head[1], (0, 1.5, 0)).rot("y", head[0], (0, 1.5, 0))
    parts.append(h)
    for side, (fw, out, bend) in ((-1, la), (1, ra)):
        up = box(-0.065, -0.32, -0.065, 0.065, 0.02, 0.065, top)
        fore = cat([box(-0.055, -0.6, -0.055, 0.055, -0.3, 0.055, top),
                    box(-0.05, -0.72, -0.045, 0.05, -0.6, 0.045, skin)])
        if side == 1 and held is not None: fore = cat([fore, held.copy().mv(0, -0.68, 0.03)])
        fore.rot("x", -bend, (0, -0.31, 0))
        arm = cat([up, fore]).rot("x", -fw).rot("z", side * out).mv(side * 0.3, 1.44, 0)
        parts.append(arm)
    return cat(parts).rot("x", lean, (0, 0.9, 0))

def brush(scale=1.0):
    """Long sword-liner: lacquered handle, ferrule, long squirrel-hair tip pointing +z."""
    handle = cyl(0.008, 0.012, 0.2, 6, (120, 20, 26)).rot("x", 90).mv(0, 0, -0.2)
    ferrule = cyl(0.012, 0.009, 0.03, 6, CHROME).rot("x", 90)
    hair = cyl(0.009, 0.0, 0.08, 6, (150, 92, 48)).rot("x", 90).mv(0, 0, 0.03)
    return cat([handle, ferrule, hair]).sc(scale)

def squirrel(tail_wag=0.0, vest=False, col=(176, 96, 42)):
    """Sits facing +z, ~0.35 m tall at scale 1."""
    light = (226, 196, 150)
    body = sphere(0.1, 8, 5, col).sc(1, 1.3, 1).mv(0, 0.13, 0)
    belly = sphere(0.06, 6, 4, light).sc(1, 1.4, 0.6).mv(0, 0.12, 0.06)
    head = sphere(0.075, 8, 5, col).mv(0, 0.3, 0.04)
    snout = sphere(0.03, 6, 4, light).mv(0, 0.29, 0.11)
    eyes = [cbox(s * 0.035, 0.32, 0.1, 0.022, 0.026, 0.01, (10, 10, 10)) for s in (1, -1)]
    ears = [P([(s * 0.02, 0.36, 0.03), (s * 0.06, 0.36, 0.03), (s * 0.045, 0.43, 0.03)], col) for s in (1, -1)]
    tail = []
    for i in range(6):
        a = math.radians(-20 + i * 32 + tail_wag * (i / 5) * 20)
        r = 0.06 + 0.02 * math.sin(i / 5 * math.pi)
        tail.append(sphere(r, 6, 4, col).mv(0, 0.08 + 0.17 * math.sin(a) + i * 0.04, -0.12 - 0.11 * math.cos(a) * (1 if i < 4 else 0.6)))
    feet = [cbox(s * 0.05, 0.015, 0.06, 0.05, 0.03, 0.08, col) for s in (1, -1)]
    parts = [body, belly, head, snout, *eyes, *ears, *tail, *feet]
    if vest: parts.append(box(-0.105, 0.06, -0.09, 0.105, 0.22, 0.09, (255, 255, 255), texs={f: T_HIVIS for f in "fblr"}))
    return cat(parts)

def forklift(col=(240, 180, 20)):
    body = box(-0.6, 0.25, -0.5, 0.6, 0.9, 0.5, col)
    cage = [box(x - 0.03, 0.9, z - 0.03, x + 0.03, 1.9, z + 0.03, (30, 30, 30)) for x in (-0.55, 0.45) for z in (-0.45, 0.45)]
    roof = box(-0.6, 1.9, -0.5, 0.5, 1.95, 0.5, (30, 30, 30))
    mast = [box(0.62, 0.1, z - 0.04, 0.7, 2.2, z + 0.04, (60, 60, 64)) for z in (-0.3, 0.3)]
    forks = [box(0.7, 0.12, z - 0.05, 1.5, 0.17, z + 0.05, (60, 60, 64)) for z in (-0.25, 0.25)]
    wh = [cyl(0.25, 0.25, 0.18, 8, (20, 20, 20)).mv(0, -0.09, 0).rot("x", 90).mv(x, 0.25, z) for x in (-0.4, 0.4) for z in (-0.5, 0.5)]
    seat = box(-0.35, 0.9, -0.25, 0.0, 1.0, 0.25, (40, 40, 40))
    return cat([body, *cage, roof, *mast, *forks, *wh, seat])

def robot(eyes=(80, 220, 255), tie=True, la=(0, 0, 0), ra=(0, 0, 0), head=0.0):
    g, d = (170, 176, 186), (90, 96, 108)
    parts = [box(-0.12, 0, -0.1, -0.03, 0.85, 0.1, d), box(0.03, 0, -0.1, 0.12, 0.85, 0.1, d),
             box(-0.24, 0.85, -0.15, 0.24, 1.45, 0.15, g)]
    hd = [box(-0.17, 1.5, -0.15, 0.17, 1.82, 0.15, g), box(-0.02, 1.45, -0.02, 0.02, 1.5, 0.02, d),
          box(-0.11, 1.64, 0.15, -0.03, 1.7, 0.16, eyes, e=1.0), box(0.03, 1.64, 0.15, 0.11, 1.7, 0.16, eyes, e=1.0),
          box(-0.08, 1.55, 0.15, 0.08, 1.57, 0.16, (30, 30, 30)), cyl(0.01, 0.01, 0.12, 4, d).mv(0, 1.82, 0),
          sphere(0.025, 6, 4, (255, 60, 40), e=1.0).mv(0, 1.95, 0)]
    parts.append(cat(hd).rot("y", head, (0, 1.6, 0)))
    if tie: parts += [P([(-0.04, 1.44, 0.152), (0.04, 1.44, 0.152), (0, 1.1, 0.152)], (170, 20, 30))]
    for side, (fw, out, bend) in ((-1, la), (1, ra)):
        up = box(-0.05, -0.3, -0.05, 0.05, 0.02, 0.05, d)
        fore = cat([box(-0.05, -0.58, -0.05, 0.05, -0.3, 0.05, g), box(-0.06, -0.68, -0.06, 0.06, -0.58, 0.06, d)]).rot("x", -bend, (0, -0.3, 0))
        parts.append(cat([up, fore]).rot("x", -fw).rot("z", side * out).mv(side * 0.3, 1.42, 0))
    return cat(parts)

def robot_arm(droop=0.0, light=(255, 40, 30)):
    o, d = (230, 110, 20), (60, 60, 64)
    base = cyl(0.35, 0.3, 0.3, 10, d)
    j1 = box(-0.12, 0.3, -0.12, 0.12, 1.3, 0.12, o)
    seg2 = box(-0.1, -0.05, -0.1, 0.1, 0.05 + 0.9, 0.1, o).rot("z", -60 - droop * 60).mv(0, 1.3, 0)
    tip_dir = math.radians(30 - droop * 60)
    tx, ty = 0.95 * math.cos(tip_dir), 1.3 + 0.95 * math.sin(tip_dir)
    head = box(tx - 0.12, ty - 0.18, -0.1, tx + 0.12, ty, 0.1, d)
    led = cbox(0, 0.2, 0.36, 0.08, 0.05, 0.02, light, e=1.0)
    return cat([base, j1, seg2, head, led])

def cow():
    body = box(-0.7, 0.7, -0.33, 0.7, 1.35, 0.33, (255, 255, 255), texs={f: T_COW for f in "fblrt"})
    head = box(0.68, 1.1, -0.18, 1.05, 1.45, 0.18, (236, 232, 226))
    nose = box(1.02, 1.1, -0.15, 1.1, 1.25, 0.15, (230, 160, 160))
    horns = [box(0.8, 1.45, s * 0.14 - 0.03, 0.84, 1.55, s * 0.14 + 0.03, (230, 220, 190)) for s in (1, -1)]
    eyes = [box(1.05, 1.32, s * 0.09 - 0.03, 1.06, 1.37, s * 0.09 + 0.03, (10, 10, 10)) for s in (1, -1)]
    legs = [box(x - 0.08, 0, z - 0.08, x + 0.08, 0.72, z + 0.08, (236, 232, 226)) for x in (-0.55, 0.55) for z in (-0.22, 0.22)]
    return cat([body, head, nose, *horns, *eyes, *legs])

def ladder(h=2.6, w=0.45):
    rails = [box(s * w / 2 - 0.03, 0, -0.03, s * w / 2 + 0.03, h, 0.03, (150, 110, 60)) for s in (1, -1)]
    rungs = [box(-w / 2, y, -0.02, w / 2, y + 0.04, 0.02, (150, 110, 60)) for y in np.arange(0.3, h, 0.3)]
    return cat(rails + rungs)

def clock(angle_min, angle_hr, r=0.5):
    face = cyl(r, r, 0.06, 16, (60, 50, 40), captex=T_CLOCK).rot("x", 90)    # face at z=+0.06 looking +z
    mh = box(-0.012, 0, 0, 0.012, r * 0.85, 0.02, (20, 20, 20)).rot("z", -angle_min).mv(0, 0, 0.065)
    hh = box(-0.02, 0, 0, 0.02, r * 0.55, 0.02, (20, 20, 20)).rot("z", -angle_hr).mv(0, 0, 0.07)
    pin = cbox(0, 0, 0.09, 0.05, 0.05, 0.02, (170, 30, 30))
    return cat([face, mh, hh, pin])

def eraser():
    return cat([box(-0.3, 0, -0.12, 0.3, 0.22, 0.12, (240, 140, 160)),
                box(-0.12, -0.005, -0.125, 0.18, 0.225, 0.125, (40, 90, 200))])

def stamp(paper_stamped=False):
    return cat([cyl(0.04, 0.05, 0.25, 8, (120, 70, 40)).mv(0, 0.1, 0), sphere(0.08, 8, 5, (120, 70, 40)).mv(0, 0.38, 0),
                box(-0.14, 0, -0.1, 0.14, 0.1, 0.1, (60, 40, 30)), box(-0.13, -0.02, -0.09, 0.13, 0.0, 0.09, (200, 20, 30))])
