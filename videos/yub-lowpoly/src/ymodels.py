"""Cars, logos, props, sets and background oddities for the three Yub low-poly shorts (Toyota, Tesla, Bugatti).
All hand-built low-poly; logos are hand-drawn textures. Cars point along +x (nose at +x), wheels on y=0."""
import math
import numpy as np
from PIL import Image, ImageDraw
from lowpoly import P, cat, box, cbox, cyl, sphere, prism, quad, tiles, wall, tex, font, rgb, sky
from models import noisy, person, face_tex, CHROME, T_TILE_DARK, T_TILE, T_PANEL, T_BRICK, T_WOOD, T_WIN, T_WIN_COOL
import fmodels as F

TOY_RED = (235, 10, 30)
TES_RED = (227, 25, 55)
BUG_RED = (190, 16, 28)

# ---------------------------------------------------------------- logos / textures
def _toyota_emblem(d, cx, cy, s, col, width):
    """Three-ellipse Toyota emblem centred at (cx, cy), overall width s."""
    w = max(2, int(width))
    d.ellipse((cx - s / 2, cy - s * 0.34, cx + s / 2, cy + s * 0.34), outline=col, width=w)
    d.ellipse((cx - s * 0.16, cy - s * 0.34, cx + s * 0.16, cy + s * 0.34), outline=col, width=w)
    d.ellipse((cx - s * 0.36, cy - s * 0.34, cx + s * 0.36, cy - s * 0.06), outline=col, width=w)

def _toyota_badge(w=64, h=48, bg=(20, 20, 24), fg=(214, 216, 222)):
    im = Image.new("RGB", (w, h), bg); d = ImageDraw.Draw(im); _toyota_emblem(d, w / 2, h / 2, w * 0.86, fg, w * 0.06); return im
T_TOY_BADGE = tex(_toyota_badge())

def _toyota_sign(w=256, h=96):
    im = Image.new("RGB", (w, h), TOY_RED); d = ImageDraw.Draw(im)
    _toyota_emblem(d, h * 0.62, h / 2, h * 0.9, (255, 255, 255), 5)
    d.text((h * 1.2 + (w - h * 1.2) / 2, h / 2), "TOYOTA", font=font(int(h * 0.38)), fill=(255, 255, 255), anchor="mm"); return im
T_TOY_SIGN = tex(_toyota_sign())

def _tesla_t(d, cx, cy, s, col):
    """Tesla 'T': arched cap bar plus stem."""
    d.chord((cx - s * 0.5, cy - s * 0.62, cx + s * 0.5, cy - s * 0.02), 200, 340, fill=col)
    d.polygon([(cx - s * 0.5, cy - s * 0.43), (cx + s * 0.5, cy - s * 0.43), (cx + s * 0.42, cy - s * 0.34), (cx - s * 0.42, cy - s * 0.34)], fill=col)
    d.polygon([(cx - s * 0.08, cy - s * 0.3), (cx + s * 0.08, cy - s * 0.3), (cx + s * 0.03, cy + s * 0.5), (cx - s * 0.03, cy + s * 0.5)], fill=col)

def _tesla_badge(w=48, h=48, bg=(230, 232, 236), fg=(200, 200, 208)):
    im = Image.new("RGB", (w, h), bg); d = ImageDraw.Draw(im); _tesla_t(d, w / 2, h / 2 + 2, w * 0.8, fg); return im
T_TES_BADGE = tex(_tesla_badge(bg=(250, 250, 252), fg=(176, 178, 186)))
T_TES_BADGE_DARK = tex(_tesla_badge(bg=(12, 12, 14), fg=(190, 190, 198)))

def _tesla_sign(w=256, h=72):
    im = Image.new("RGB", (w, h), (14, 14, 16)); d = ImageDraw.Draw(im)
    _tesla_t(d, h * 0.55, h / 2 + 3, h * 0.75, TES_RED)
    d.text((h * 1.05 + (w - h * 1.05) / 2, h / 2), "T E S L A", font=font(int(h * 0.42)), fill=(240, 240, 244), anchor="mm"); return im
T_TES_SIGN = tex(_tesla_sign())

def _bugatti_macaron(w=96, h=64, bg=(150, 150, 156)):
    im = Image.new("RGB", (w, h), bg); d = ImageDraw.Draw(im)
    d.ellipse((2, 2, w - 3, h - 3), fill=(232, 232, 236)); d.ellipse((6, 6, w - 7, h - 7), fill=BUG_RED)
    for i in range(24):                                     # the pearl border
        a = 2 * math.pi * i / 24; x, y = w / 2 + (w / 2 - 4) * math.cos(a), h / 2 + (h / 2 - 4) * math.sin(a)
        d.ellipse((x - 1.4, y - 1.4, x + 1.4, y + 1.4), fill=(250, 250, 250))
    d.text((w / 2, h * 0.34), "EB", font=font(int(h * 0.2)), fill=(250, 250, 250), anchor="mm")
    d.text((w / 2, h * 0.6), "BUGATTI", font=font(int(h * 0.24)), fill=(250, 250, 250), anchor="mm"); return im
T_BUG_BADGE = tex(_bugatti_macaron())

def _bugatti_sign(w=256, h=96):
    im = Image.new("RGB", (w, h), (18, 18, 22)); d = ImageDraw.Draw(im)
    im.paste(_bugatti_macaron(int(h * 1.3), int(h * 0.86), (18, 18, 22)), (int(w / 2 - h * 0.65), int(h * 0.07))); return im
T_BUG_SIGN = tex(_bugatti_sign())

def _horseshoe(w=64, h=72):
    im = Image.new("RGB", (w, h), (12, 12, 14)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((3, 3, w - 4, h - 4), radius=w // 2 - 4, outline=(214, 216, 222), width=5)
    for x in range(10, w - 8, 6): d.line((x, 8, x, h - 8), fill=(60, 60, 66), width=2)
    return im
T_HORSESHOE = tex(_horseshoe())

def word(text, w=256, h=64, fg=(255, 255, 255), bg=(16, 16, 18), size=None, border=None):
    im = Image.new("RGB", (w, h), bg); d = ImageDraw.Draw(im)
    lines = text.split("\n"); size = size or int(h * 0.62 / len(lines))
    for i, ln in enumerate(lines):
        d.text((w / 2, h * (i + 0.5) / len(lines)), ln, font=font(size), fill=fg, anchor="mm")
    if border: d.rectangle((0, 0, w - 1, h - 1), outline=border, width=max(2, h // 16))
    return tex(im)

def screen(lines, w=160, h=96, bg=(14, 22, 34), fg=(230, 236, 244), accent=None, bar=None, logo=None):
    """A car infotainment screen: dark UI, a few text lines; optional red/green accent line and progress bar."""
    im = Image.new("RGB", (w, h), bg); d = ImageDraw.Draw(im)
    d.rectangle((0, 0, w, 12), fill=(30, 40, 56))
    if logo == "toyota": _toyota_emblem(d, 12, 6, 14, (220, 220, 230), 1)
    if logo == "tesla": _tesla_t(d, 10, 7, 10, (230, 230, 236))
    n = len(lines)
    for i, ln in enumerate(lines):
        col = accent if (accent and i == n - 1) else fg
        d.text((w / 2, 14 + (h - 14) * (i + 0.5) / (n + (1 if bar is not None else 0))), ln, font=font(int(min(22, (h - 14) / (n + 1.2)))),
               fill=col, anchor="mm")
    if bar is not None:
        d.rectangle((14, h - 18, w - 14, h - 10), outline=(120, 140, 170)); d.rectangle((16, h - 16, 16 + (w - 32) * bar, h - 12), fill=(60, 170, 255))
    return tex(im)

def tag(text, w=96, h=56, bg=(250, 236, 120), fg=(20, 20, 20)):
    im = Image.new("RGB", (w, h), bg); d = ImageDraw.Draw(im)
    d.ellipse((6, h / 2 - 5, 16, h / 2 + 5), fill=(60, 60, 60))
    d.text((w / 2 + 6, h / 2), text, font=font(int(h * 0.44) if len(text) < 7 else int(h * 0.34)), fill=fg, anchor="mm"); return tex(im)

def _hub(spokes=5, rim=(190, 192, 200), dark=(30, 30, 34), centre=None, n=96):
    im = Image.new("RGB", (n, n), dark); d = ImageDraw.Draw(im)
    d.ellipse((2, 2, n - 3, n - 3), outline=rim, width=6)
    for i in range(spokes):
        a = 2 * math.pi * i / spokes
        d.line((n / 2, n / 2, n / 2 + 42 * math.cos(a), n / 2 + 42 * math.sin(a)), fill=rim, width=10)
    d.ellipse((n / 2 - 11, n / 2 - 11, n / 2 + 11, n / 2 + 11), fill=centre or rim); return im
T_HUB_TOY = tex(_hub(5, (176, 178, 184)))
T_HUB_TES = tex(_hub(5, (90, 92, 98), (20, 20, 22)))
def _veyron_hub(n=96, big=False):
    im = Image.fromarray(np.asarray(_hub(10, (206, 208, 214), (26, 26, 30), BUG_RED, n)))
    if big:
        d = ImageDraw.Draw(im); d.ellipse((1, 1, n - 2, n - 2), outline=(240, 240, 246), width=3)
    return im
T_HUB_BUG = tex(_veyron_hub())
T_HUB_BUG_NEW = tex(_veyron_hub(big=True))

def _tread(w=64, h=64, brand=None):
    im = Image.new("RGB", (w, h), (24, 24, 26)); d = ImageDraw.Draw(im)
    for y in range(0, h, 8): d.line((0, y, w, y + 4), fill=(44, 44, 48), width=2)
    return im
T_TREAD = tex(_tread())

def _sidewall(n=128, label="MICHELIN", sub="PAX"):
    im = Image.new("RGB", (n, n), (22, 22, 24)); d = ImageDraw.Draw(im)
    d.ellipse((4, 4, n - 5, n - 5), outline=(40, 40, 44), width=3)
    d.ellipse((n * 0.24, n * 0.24, n * 0.76, n * 0.76), fill=(150, 152, 158))
    d.text((n / 2, n * 0.13), label, font=font(int(n * 0.1)), fill=(210, 210, 214), anchor="mm")
    if sub: d.text((n / 2, n * 0.88), sub, font=font(int(n * 0.1)), fill=(210, 210, 214), anchor="mm")
    return tex(im)
T_SIDE_PAX = _sidewall()
T_SIDE_NEW = _sidewall(sub=None)

def _calendar(top, big, sub=""):
    im = Image.new("RGB", (64, 80), (244, 244, 238)); d = ImageDraw.Draw(im)
    d.rectangle((0, 0, 64, 20), fill=(196, 30, 36)); d.text((32, 10), top, font=font(13), fill=(255, 255, 255), anchor="mm")
    d.text((32, 46), big, font=font(22 if len(big) > 2 else 30), fill=(20, 20, 20), anchor="mm")
    if sub: d.text((32, 70), sub, font=font(10), fill=(90, 90, 90), anchor="mm")
    return tex(im)

def _cash(w=48, h=24):
    im = Image.new("RGB", (w, h), (120, 170, 110)); d = ImageDraw.Draw(im)
    d.rectangle((1, 1, w - 2, h - 2), outline=(60, 100, 60), width=2); d.ellipse((w / 2 - 7, 4, w / 2 + 7, h - 4), fill=(170, 210, 160))
    d.text((8, h / 2), "$", font=font(12), fill=(40, 80, 40), anchor="mm"); return tex(im)
T_CASH = _cash()

def _plate(text, bg=(244, 244, 236), fg=(30, 40, 120)):
    return word(text, 96, 32, fg, bg, 18, border=(30, 40, 120))

def _star_sky():
    a = sky((6, 8, 26), (34, 30, 60)); r = np.random.default_rng(5)
    for x, y in r.integers(0, (270, 300), (70, 2)): a[y, x] = 0.85
    return a
NIGHT_BG = _star_sky()
DUSK_BG = sky((40, 34, 80), (240, 130, 90))
SHOP_BG = sky((22, 22, 26), (40, 38, 40))

# ---------------------------------------------------------------- car builder
def wheel(x, z, hub, r=0.36, wd=0.26, spin=0.0, seg=12, tyre=(18, 18, 20)):
    w = cyl(r, r, wd, seg, tyre, captex=hub)
    return w.mv(0, -wd / 2, 0).rot("x", 90).rot("z", spin).mv(x, r, z)

def _taper(k=0.16, y0=0.55, span=0.7):
    def f(v):
        q = np.clip((v[:, 1] - y0) / span, 0, 1); v[:, 2] *= 1 - k * q; return v
    return f

def rav4(col=(70, 76, 84), spin=0.0, lights=False, plate=None, dash=None):
    """Toyota RAV4 (5th gen): boxy SUV, chunky arches, black lower cladding, Toyota emblem front and back."""
    hw = 0.93
    body = prism([(-2.3, 0.32), (2.3, 0.32), (2.36, 0.72), (2.2, 0.98), (1.25, 1.08), (-2.15, 1.1), (-2.32, 0.98)], -hw, hw, col).fn(_taper(0.05))
    glass = prism([(1.2, 1.06), (0.45, 1.6), (-1.95, 1.62), (-2.22, 1.08)], -hw * 0.9, hw * 0.9, (24, 28, 36)).fn(_taper(0.12, 1.0, 0.6))
    roof = prism([(0.45, 1.6), (-1.95, 1.62), (-1.95, 1.68), (0.4, 1.66)], -hw * 0.82, hw * 0.82, col)
    rails = [box(-1.8, 1.68, s * 0.62 - 0.03, 0.3, 1.72, s * 0.62 + 0.03, (20, 20, 22)) for s in (1, -1)]
    pillars = [box(x - 0.08, 1.06, -hw * 0.905, x + 0.08, 1.6, hw * 0.905, col) for x in (-0.55,)]
    clad = [box(-2.34, 0.2, -hw - 0.01, 2.36, 0.42, hw + 0.01, (22, 22, 24))]
    arches = [box(x - 0.55, 0.3, s * hw - 0.03, x + 0.55, 0.82, s * hw + 0.03, (22, 22, 24)) for x in (1.45, -1.4) for s in (1, -1)]
    grille = box(2.33, 0.38, -0.62, 2.39, 0.72, 0.62, (14, 14, 16))
    badge = box(2.37, 0.76, -0.14, 2.42, 0.9, 0.14, (255, 255, 255), texs={"r": T_TOY_BADGE})
    rbadge = box(-2.37, 0.82, -0.12, -2.32, 0.94, 0.12, (255, 255, 255), texs={"l": T_TOY_BADGE})
    hl = (255, 250, 230) if lights else (120, 124, 130)
    heads = [box(2.2, 0.8, s * 0.7 - 0.2, 2.36, 0.9, s * 0.7 + 0.2, hl, e=1.0 if lights else 0.0) for s in (1, -1)]
    tails = [box(-2.37, 0.86, s * 0.74 - 0.16, -2.3, 1.0, s * 0.74 + 0.16, (200, 20, 20), e=1.0 if lights else 0.3) for s in (1, -1)]
    mirrors = [cbox(0.95, 1.12, s * 1.0, 0.18, 0.12, 0.16, (22, 22, 24)) for s in (1, -1)]
    wheels = [wheel(x, z * 0.8, T_HUB_TOY, 0.37, 0.26, spin) for x in (1.45, -1.4) for z in (1, -1)]
    parts = [body, glass, roof, *rails, *pillars, *clad, *arches, grille, badge, rbadge, *heads, *tails, *mirrors, *wheels]
    if plate: parts.append(box(2.38, 0.46, -0.26, 2.42, 0.62, 0.26, (255, 255, 255), texs={"r": plate}))
    if dash is not None:   # a screen on the dashboard, seen through the windscreen
        parts.append(box(0.62, 1.02, -0.28, 0.68, 1.26, 0.28, (255, 255, 255), texs={"r": dash}, e=1.0).rot("z", 25, (0.65, 1.1, 0)))
    if lights:
        parts.append(box(2.36, 0.83, -0.95, 2.37, 0.86, 0.95, (255, 255, 240), e=1.0))
    return cat(parts)

TES_WHITE = (232, 234, 238)
def model3(col=TES_WHITE, spin=0.0, glow=False, plate=None, dual=False, xray=0.0, giftbox=None):
    """Tesla Model 3: smooth fastback, no grille, glass roof, T badge on the nose."""
    hw = 0.92
    body = prism([(-2.33, 0.28), (2.3, 0.28), (2.36, 0.5), (2.16, 0.7), (1.0, 0.84), (-1.9, 0.94), (-2.36, 0.88), (-2.4, 0.56)], -hw, hw, col).fn(_taper(0.1, 0.6, 0.4))
    glass = prism([(1.0, 0.83), (0.15, 1.3), (-0.9, 1.33), (-1.95, 0.95)], -hw * 0.82, hw * 0.82, (18, 20, 26)).fn(_taper(0.14, 0.85, 0.5))
    lower = box(-2.38, 0.2, -hw - 0.005, 2.3, 0.3, hw + 0.005, (40, 40, 44))
    badge = box(2.29, 0.6, -0.08, 2.35, 0.7, 0.08, (255, 255, 255), texs={"r": T_TES_BADGE if col[0] > 128 else T_TES_BADGE_DARK})
    heads = [box(2.0, 0.58, s * 0.7 - 0.22, 2.3, 0.64, s * 0.7 + 0.22, (240, 246, 255), e=1.0 if glow else 0.0).rot("y", s * 12, (2.15, 0, s * 0.7)) for s in (1, -1)]
    tails = [box(-2.42, 0.7, s * 0.66 - 0.2, -2.36, 0.78, s * 0.66 + 0.2, (190, 16, 24), e=0.7) for s in (1, -1)]
    mirrors = [cbox(0.85, 0.92, s * 0.98, 0.16, 0.08, 0.14, (20, 20, 22)) for s in (1, -1)]
    handles = [box(x - 0.15, 0.78, s * (hw + 0.005) - 0.005, x + 0.15, 0.8, s * (hw + 0.005) + 0.005, (190, 190, 196)) for x in (0.4, -0.7) for s in (1, -1)]
    wheels = [wheel(x, z * 0.8, T_HUB_TES, 0.34, 0.24, spin) for x in (1.45, -1.45) for z in (1, -1)]
    parts = [body, glass, lower, badge, *heads, *tails, *mirrors, *handles, *wheels]
    if xray > 0:   # x-ray: glowing outline of the body, battery floor and the two motors (front and rear axle)
        prof = [(-2.33, 0.28), (2.3, 0.28), (2.36, 0.5), (2.16, 0.7), (1.0, 0.84), (0.15, 1.3), (-0.9, 1.33), (-1.9, 0.94), (-2.36, 0.88), (-2.4, 0.56)]
        cy = (90, 200, 255); out = []
        for z in (-hw, hw):
            for (x0, y0), (x1, y1) in zip(prof, prof[1:] + prof[:1]):
                L = math.hypot(x1 - x0, y1 - y0); ang = math.degrees(math.atan2(y1 - y0, x1 - x0))
                out.append(box(0, -0.02, -0.02, L, 0.02, 0.02, cy, e=0.8).rot("z", ang).mv(x0, y0, z))
        for x, y in prof: out.append(box(x - 0.02, y - 0.02, -hw, x + 0.02, y + 0.02, hw, cy, e=0.8))
        out.append(box(-1.6, 0.22, -0.7, 1.2, 0.32, 0.7, (40, 60, 90)))
        for x in (1.45, -1.45):
            out.append(cyl(0.2, 0.2, 0.6, 10, (255, 200, 60), e=xray).mv(0, -0.3, 0).rot("x", 90).mv(x, 0.36, 0))
        parts = [*wheels, *out, badge]
    if dual: parts.append(box(-2.42, 0.5, -0.38, -2.4, 0.58, 0.02, (255, 255, 255), texs={"l": T_DUAL}))
    if plate: parts.append(box(-2.44, 0.38, -0.25, -2.4, 0.52, 0.25, (255, 255, 255), texs={"l": plate}))
    if xray > 0:   # two glowing motors, front and rear axle
        for x in (1.45, -1.45):
            parts.append(cyl(0.18, 0.18, 0.5, 10, (80, 220, 255), e=xray).mv(0, -0.25, 0).rot("x", 90).mv(x, 0.36, 0))
    if giftbox is not None:
        parts.append(gift(giftbox).mv(-0.4, 1.32, 0))
    return cat(parts)

T_DUAL = word("DUAL MOTOR", 128, 20, (40, 40, 44), (232, 234, 238), 13)

VEY_DARK = (24, 30, 62)
VEY_LIGHT = (120, 150, 200)
def veyron(spin=0.0, dusty=0.0, new_wheels=False, lift=0.0, wheels_on=True):
    """Bugatti Veyron 16.4: low rounded body, two-tone (dark blue top and rear, lighter blue nose and flanks),
    horseshoe grille with the red EB macaron, roof air scoops."""
    hw = 0.99
    lo = VEY_LIGHT if dusty < 0.5 else (150, 150, 150)
    hi = VEY_DARK if dusty < 0.5 else (110, 110, 112)
    nose = prism([(0.2, 0.18), (2.2, 0.18), (2.26, 0.4), (2.1, 0.62), (1.2, 0.8), (0.2, 0.86)], -hw, hw, lo).fn(_taper(0.12, 0.4, 0.45))
    tail = prism([(-2.2, 0.18), (0.2, 0.18), (0.2, 0.86), (-1.7, 0.96), (-2.22, 0.86), (-2.26, 0.5)], -hw, hw, hi).fn(_taper(0.1, 0.4, 0.55))
    glass = prism([(1.2, 0.79), (0.2, 1.16), (-0.75, 1.17), (-1.5, 0.96)], -hw * 0.76, hw * 0.76, (16, 18, 26)).fn(_taper(0.15, 0.8, 0.4))
    cabin_side = [box(-1.0, 0.8, s * 0.76 - 0.01, 0.6, 1.1, s * 0.76 + 0.01, hi) for s in (1, -1)]
    scoops = [box(-1.15, 1.08, s * 0.32 - 0.15, -0.55, 1.26, s * 0.32 + 0.15, hi) for s in (1, -1)]
    scoop_holes = [box(-0.56, 1.11, s * 0.32 - 0.12, -0.54, 1.23, s * 0.32 + 0.12, (8, 8, 10)) for s in (1, -1)]
    grille = box(2.23, 0.2, -0.17, 2.29, 0.58, 0.17, (255, 255, 255), texs={"r": T_HORSESHOE})
    badge = box(2.24, 0.6, -0.1, 2.3, 0.68, 0.1, (255, 255, 255), texs={"r": T_BUG_BADGE})
    intakes = [box(2.2, 0.22, s * 0.6 - 0.25, 2.27, 0.42, s * 0.6 + 0.25, (10, 10, 12)) for s in (1, -1)]
    heads = [box(1.75, 0.56, s * 0.72 - 0.16, 2.15, 0.62, s * 0.72 + 0.16, (240, 240, 250), e=0.6) for s in (1, -1)]
    tails = [box(-2.28, 0.68, -0.8, -2.22, 0.72, 0.8, (210, 20, 20), e=0.8)]
    side_c = [box(-0.9, 0.3, s * hw - 0.02, 0.15, 0.7, s * hw + 0.02, (34, 36, 44)) for s in (1, -1)]
    rbadge = box(-2.3, 0.52, -0.12, -2.24, 0.62, 0.12, (255, 255, 255), texs={"l": T_BUG_BADGE})
    parts = [nose, tail, glass, *cabin_side, *scoops, *scoop_holes, grille, badge, *intakes, *heads, *tails, *side_c, rbadge]
    if wheels_on:
        r = 0.37 if not new_wheels else 0.39
        hub = T_HUB_BUG_NEW if new_wheels else T_HUB_BUG
        parts += [wheel(x, z * 0.86, hub, r, 0.3, spin) for x in (1.4, -1.35) for z in (1, -1)]
    if dusty > 0:   # cobwebs / dust sheet hint: grey strands on the roof
        parts += [box(-0.9 + 0.4 * i, 1.17, -0.5, -0.88 + 0.4 * i, 1.18, 0.5, (200, 200, 200)) for i in range(4)]
    car = cat(parts)
    return car.mv(0, lift, 0)

# ---------------------------------------------------------------- props
def fob_toyota(press=0.0, lit=False):
    """Toyota smart key: black rounded slab, 4 buttons, emblem; held upright (buttons face +z)."""
    shell = cbox(0, 0, 0, 0.16, 0.26, 0.05, (18, 18, 20))
    em = box(-0.05, 0.075, 0.024, 0.05, 0.115, 0.03, (255, 255, 255), texs={"f": T_TOY_BADGE})
    btns = []
    for i, (lab, y) in enumerate((("lock", 0.03), ("unlock", -0.015), ("trunk", -0.06), ("start", -0.105))):
        d = 0.012 * (press if lab == "start" else 0)
        col = (60, 200, 255) if (lab == "start" and lit) else (60, 60, 64)
        btns.append(box(-0.045, y - 0.018, 0.025 - d, 0.045, y + 0.018, 0.035 - d, col, texs={"f": T_KEYB[i]}, e=1.0 if (lab == "start" and lit) else 0.0))
    ring = cyl(0.03, 0.03, 0.01, 8, CHROME, cap=False).rot("x", 90).mv(0, 0.15, 0)
    return cat([shell, em, *btns, ring])

def _keyb(sym):
    im = Image.new("RGB", (32, 16), (54, 54, 58)); d = ImageDraw.Draw(im)
    d.text((16, 8), sym, font=font(11), fill=(220, 220, 224), anchor="mm"); return tex(im)
T_KEYB = [_keyb(s) for s in ("LOCK", "OPEN", "TRUNK", "START")]

def hand(skin=(206, 164, 128), sleeve=(40, 50, 80)):
    """Right hand holding something at the origin: palm + thumb + sleeve going down/back (-y, -z)."""
    palm = cbox(0, -0.08, -0.03, 0.17, 0.14, 0.07, skin)
    fingers = [cbox(-0.06 + 0.04 * i, -0.01, -0.035, 0.035, 0.08, 0.06, skin).mv(0, 0, 0) for i in range(4)]
    sl = cbox(0, -0.3, -0.06, 0.2, 0.32, 0.14, sleeve)
    return cat([palm, *fingers, sl])

def thumb(skin=(206, 164, 128), press=0.0):
    return cbox(0, 0, 0, 0.045, 0.09, 0.045, skin).rot("x", -30 + 25 * press).mv(0.06, -0.09, 0.04 + 0.02 * (1 - press))

def waves(t, n=4, spacing=0.45, speed=1.4, col=(80, 220, 255), r0=0.1, rng=None):
    """Expanding radio rings in the XY plane (facing +z), centred at the origin."""
    out = []
    for i in range(n):
        r = r0 + ((t * speed + i * spacing) % (n * spacing))
        seg = 14; th = 0.025
        for k in range(seg):
            a0, a1 = 2 * math.pi * k / seg, 2 * math.pi * (k + 1) / seg
            out.append(quad((r * math.cos(a0), r * math.sin(a0), 0), (r * math.cos(a1), r * math.sin(a1), 0),
                            ((r + th) * math.cos(a1), (r + th) * math.sin(a1), 0), ((r + th) * math.cos(a0), (r + th) * math.sin(a0), 0), col, e=1.0))
    return cat(out)

def padlock(col=(250, 200, 40)):
    return cat([cbox(0, 0, 0, 0.24, 0.2, 0.1, col), box(-0.1, 0.1, -0.02, -0.06, 0.25, 0.02, CHROME), box(0.06, 0.1, -0.02, 0.1, 0.25, 0.02, CHROME),
                box(-0.1, 0.22, -0.02, 0.1, 0.26, 0.02, CHROME), cbox(0, 0.0, 0.051, 0.04, 0.07, 0.01, (30, 30, 30))])

def coin(col=(230, 190, 60)):
    return cyl(0.12, 0.12, 0.025, 12, col, capcol=(250, 214, 90))

def meter(tid):
    """A coin-op parking meter head on a pole."""
    return cat([cyl(0.03, 0.03, 1.0, 6, (70, 70, 76)), cbox(0, 1.13, 0, 0.22, 0.28, 0.16, (110, 112, 118)),
                box(-0.08, 1.12, 0.081, 0.08, 1.22, 0.085, (255, 255, 255), texs={"f": tid}, e=0.6),
                cbox(0, 1.04, 0.081, 0.02, 0.05, 0.01, (20, 20, 20)), sphere(0.11, 8, 3, (110, 112, 118)).mv(0, 1.27, 0)])

def gift(open_=0.0, col=(220, 30, 50), ribbon=(250, 220, 60), s=0.5):
    base = cbox(0, s * 0.4, 0, s, s * 0.8, s, col)
    rb = [cbox(0, s * 0.4, 0, s * 0.16, s * 0.81, s * 1.01, ribbon), cbox(0, s * 0.4, 0, s * 1.01, s * 0.81, s * 0.16, ribbon)]
    lid = cat([cbox(0, 0, 0, s * 1.08, s * 0.16, s * 1.08, col), cbox(0, 0, 0, s * 0.17, s * 0.17, s * 1.09, ribbon),
               cbox(0, 0.1 * s, 0, s * 0.4, s * 0.2, s * 0.1, ribbon).rot("y", 45)])
    lid = lid.rot("z", -110 * open_, (s * 0.54, 0, 0)).mv(0, s * 0.88 + 0.4 * s * open_, 0)
    return cat([base, *rb, lid])

def stopwatch(tid, hand_a=0.0):
    face = cyl(0.3, 0.3, 0.06, 16, (230, 230, 234), captex=tid).mv(0, -0.03, 0).rot("x", -90)
    rim = cyl(0.33, 0.33, 0.05, 16, CHROME, cap=False).mv(0, -0.025, 0).rot("x", 90)
    crown = cat([cbox(0, 0.36, 0, 0.06, 0.08, 0.06, CHROME), cbox(0, 0.42, 0, 0.14, 0.04, 0.06, CHROME)])
    needle = box(-0.008, 0, 0.035, 0.008, 0.24, 0.045, (220, 20, 30)).rot("z", -hand_a)
    return cat([face, rim, crown, needle])

def _watchface(txt):
    im = Image.new("RGB", (96, 96), (236, 236, 240)); d = ImageDraw.Draw(im)
    for i in range(60):
        a = 2 * math.pi * i / 60; r0 = 40 if i % 5 else 36
        d.line((48 + r0 * math.sin(a), 48 - r0 * math.cos(a), 48 + 45 * math.sin(a), 48 - 45 * math.cos(a)), fill=(30, 30, 30), width=1 if i % 5 else 2)
    d.text((48, 66), txt, font=font(16), fill=(200, 20, 30), anchor="mm"); return tex(im)

def tire(tid_side=None, r=0.37, w=0.3, rim=None):
    """A loose tyre lying flat (axis y)."""
    t = cyl(r, r, w, 14, (20, 20, 22), captex=tid_side if tid_side is not None else -1, capcol=(20, 20, 22))
    return t.rot("x", 180).mv(0, w, 0)          # unmirrored cap on top

def tire_stack(n=4, tid=None, r=0.37, w=0.28):
    return cat([tire(tid, r, w).mv(0, i * (w + 0.005), 0) for i in range(n)])

def cash_stack(n=6):
    return cat([box(-0.2, 0.06 * i, -0.09, 0.2, 0.06 * i + 0.055, 0.09, (255, 255, 255), texs={"t": T_CASH, "f": T_CASH, "r": T_CASH}).rot("y", 7 * math.sin(i * 1.7))
                for i in range(n)])

def sign_board(tid, w=1.2, h=0.8, pole=1.4, col=(240, 240, 240)):
    return cat([cyl(0.025, 0.025, pole, 5, (120, 90, 60)), box(-w / 2, pole, -0.02, w / 2, pole + h, 0.02, col, texs={"f": tid, "b": tid})])

def paper(tid, w=0.42, h=0.56):
    return box(-w / 2, 0, -h / 2, w / 2, 0.005, h / 2, (255, 255, 255), texs={"t": tid})

def magnifier():
    return cat([cyl(0.2, 0.2, 0.03, 14, (170, 210, 255), capcol=(170, 210, 255)).mv(0, -0.015, 0).rot("x", 90),
                cyl(0.22, 0.22, 0.04, 14, (30, 30, 34), cap=False).mv(0, -0.02, 0).rot("x", 90),
                box(-0.025, -0.6, -0.025, 0.025, -0.21, 0.025, (90, 50, 30))])

def lift_post(h=2.0):
    return cat([box(-0.12, 0, -0.12, 0.12, h, 0.12, (210, 40, 30)), box(-0.18, 0, -0.18, 0.18, 0.04, 0.18, (60, 60, 64))])

# ---------------------------------------------------------------- oddities (comment bait; never mentioned)
def penguin(t, cart=True):
    """A penguin waddling while pushing a shopping cart (faces +x)."""
    wob = 8 * math.sin(t * 9)
    body = cat([sphere(0.22, 8, 5, (20, 20, 26)).sc(1, 1.5, 1).mv(0, 0.36, 0),
                sphere(0.17, 8, 5, (240, 240, 240)).sc(0.8, 1.4, 1).mv(0.07, 0.34, 0),
                sphere(0.13, 8, 4, (20, 20, 26)).mv(0, 0.72, 0),
                cbox(0.15, 0.72, 0, 0.1, 0.04, 0.06, (250, 150, 30)),
                cbox(0.1, 0.76, 0.06, 0.03, 0.03, 0.02, (255, 255, 255)), cbox(0.1, 0.76, -0.06, 0.03, 0.03, 0.02, (255, 255, 255)),
                cbox(0.04, 0.02, 0.08, 0.14, 0.03, 0.08, (250, 150, 30)), cbox(0.04, 0.02, -0.08, 0.14, 0.03, 0.08, (250, 150, 30)),
                cbox(0.12, 0.45, 0.2, 0.22, 0.05, 0.05, (20, 20, 26)).rot("z", -20), cbox(0.12, 0.45, -0.2, 0.22, 0.05, 0.05, (20, 20, 26)).rot("z", -20)])
    hat = cat([cyl(0.12, 0.05, 0.16, 8, (220, 30, 40)).mv(0, 0.8, 0), sphere(0.045, 6, 3, (250, 250, 250)).mv(0, 0.97, 0),
               cyl(0.15, 0.15, 0.06, 8, (220, 30, 40)).mv(0, 0.58, 0)])
    body = cat([body, hat]).rot("x", wob)
    parts = [body]
    if cart:
        c = (190, 194, 200)
        bask = [box(0.35, 0.35, -0.25, 0.95, 0.37, 0.25, c), box(0.35, 0.35, -0.25, 0.37, 0.75, 0.25, c), box(0.93, 0.35, -0.25, 0.95, 0.75, 0.25, c),
                box(0.35, 0.35, -0.25, 0.95, 0.75, -0.23, c), box(0.35, 0.35, 0.23, 0.95, 0.75, 0.25, c),
                box(0.28, 0.72, -0.28, 0.32, 0.76, 0.28, (220, 30, 30)), box(0.45, 0.1, -0.22, 0.9, 0.13, 0.22, c),
                cbox(0.8, 0.86, 0.0, 0.18, 0.2, 0.18, (240, 120, 30)), cbox(0.55, 0.82, 0.05, 0.16, 0.12, 0.12, (60, 140, 220))]  # a fish box + a crate
        for x in (0.45, 0.9):
            for z in (-0.2, 0.2): bask.append(cyl(0.05, 0.05, 0.03, 6, (30, 30, 30)).rot("x", 90).mv(x, 0.05, z))
        bask.append(sphere(0.05, 6, 3, (255, 160, 40), e=1.0 if int(t * 3) % 2 else 0.3).mv(0.95, 0.8, 0))
        parts += bask
    return cat(parts)

def astronaut_chair(t):
    """An astronaut in a full white suit lounging on a striped deck chair under a beach umbrella, sipping a drink."""
    chair = cat([box(-0.5, 0.25, -0.3, 0.3, 0.3, 0.3, (240, 120, 40)).rot("z", 8), box(-0.85, 0.3, -0.3, -0.45, 0.33, 0.3, (240, 240, 240)).rot("z", 55, (-0.5, 0.3, 0)),
                 box(-0.5, 0, -0.32, -0.46, 0.3, -0.28, (180, 180, 180)), box(0.25, 0, -0.32, 0.29, 0.28, -0.28, (180, 180, 180)),
                 box(-0.5, 0, 0.28, -0.46, 0.3, 0.32, (180, 180, 180)), box(0.25, 0, 0.28, 0.29, 0.28, 0.32, (180, 180, 180))])
    suit = (236, 236, 240)
    astro = cat([cbox(-0.2, 0.45, 0, 0.5, 0.3, 0.42, suit).rot("z", 30, (-0.2, 0.4, 0)), cbox(0.2, 0.38, 0.1, 0.5, 0.16, 0.16, suit), cbox(0.2, 0.38, -0.1, 0.5, 0.16, 0.16, suit),
                 cbox(0.48, 0.32, 0.1, 0.12, 0.16, 0.18, (200, 200, 206)), cbox(0.48, 0.32, -0.1, 0.12, 0.16, 0.18, (200, 200, 206)),
                 sphere(0.19, 8, 5, suit).mv(-0.45, 0.82, 0), box(-0.3, 0.72, -0.12, -0.28, 0.9, 0.12, (230, 170, 40), e=0.4),
                 cbox(-0.62, 0.6, 0, 0.16, 0.3, 0.3, (210, 210, 214)),
                 cbox(-0.05, 0.62 + 0.04 * math.sin(t * 2), 0.28, 0.12, 0.3, 0.12, suit).rot("x", -30),
                 cyl(0.04, 0.05, 0.12, 6, (250, 120, 160)).mv(-0.05, 0.78 + 0.04 * math.sin(t * 2), 0.38)]).mv(0, 0.05, 0)
    umb = cat([cyl(0.025, 0.025, 1.9, 5, (220, 220, 220)).mv(-0.9, 0, 0)] +
              [P([(-0.9, 2.0, 0), (-0.9 + 1.0 * math.cos(a0), 1.7, 1.0 * math.sin(a0)), (-0.9 + 1.0 * math.cos(a1), 1.7, 1.0 * math.sin(a1))],
                 (240, 60, 60) if i % 2 else (250, 240, 230)) for i, (a0, a1) in enumerate((2 * math.pi * k / 8, 2 * math.pi * (k + 1) / 8) for k in range(8))])
    return cat([chair, astro, umb])

def flamingo(t):
    """A pink flamingo standing on one leg (faces +x)."""
    pk = (250, 130, 170)
    bob = 0.03 * math.sin(t * 3)
    return cat([cyl(0.015, 0.015, 0.75, 4, (230, 110, 140)), box(-0.02, 0.38, -0.012, 0.18, 0.41, 0.012, (230, 110, 140)).rot("z", -40, (0, 0.4, 0)),
                sphere(0.2, 8, 5, pk).sc(1.4, 0.8, 0.8).mv(-0.05, 0.85, 0),
                box(-0.32, 0.82, -0.1, -0.1, 0.95, 0.1, (230, 90, 140)).rot("z", 15),
                box(0.15, 0.88, -0.03, 0.2, 1.35, 0.03, pk).rot("z", -10 + 4 * math.sin(t * 3)),
                sphere(0.08, 6, 4, pk).mv(0.25, 1.38 + bob, 0), box(0.3, 1.32 + bob, -0.025, 0.42, 1.38 + bob, 0.025, (30, 30, 30)).rot("z", -30, (0.3, 1.36 + bob, 0)),
                cbox(0.27, 1.42 + bob, 0.06, 0.03, 0.03, 0.02, (10, 10, 10)), cbox(0.27, 1.42 + bob, -0.06, 0.03, 0.03, 0.02, (10, 10, 10))])

# ---------------------------------------------------------------- people
def guy(top=(40, 50, 80), skin=(206, 164, 128), hair=(40, 30, 22), mouth="flat", **kw):
    return person(skin=skin, top=top, hair=hair, face=face_tex(skin=skin, hair=hair, mouth=mouth), **kw)
F_ANGRY = [face_tex(skin=s, hair=h, mouth="open", brows=(20, 16, 14)) for s, h in (((220, 180, 150), (90, 60, 30)), ((150, 100, 70), (20, 20, 20)),
                                                                                 ((200, 160, 120), (200, 190, 160)), ((120, 80, 56), (30, 26, 22)), ((230, 190, 160), (160, 60, 30)))]
