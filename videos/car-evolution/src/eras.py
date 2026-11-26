"""Era environments around the one car (car at the origin, facing +x; cameras mostly on the +z side).
0 1886 German cobblestone street at dusk · 1 brass-era garage (hand crank / 1912) · 2 1910s American town (Model T)
3 1959 Swedish coast road · 4 1977 city at night · 5 today's city at blue hour.
world(st, t, v, far) -> (meshes, glow, sprites, env_kwargs). world_wipe() sweeps one era into the next with the scan plane."""
import math
from functools import lru_cache
import _lib  # noqa: F401
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from geo import (P, cat, quad, box, bbox, cb, lathe, cyl, superellipsoid, sphere, capsule, tiles, tex, word_tex, rgb,
                 MATTE, PAINT, GLASS, CHROME, SATIN, RUBBER, GLOW, CLOTH)
import props3d as PR
import world as W

L = 48.0                                      # street repeat length for scrolling (driving shots)
def wrap(x, t, v): return ((x - v * t + L / 2) % L) - L / 2

# ---------------------------------------------------------------- textures
def _noise(w, h, seed, s=1.0):
    r = np.random.default_rng(seed); a = r.random((h // 8 + 2, w // 8 + 2))
    im = Image.fromarray((a * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC)
    return np.asarray(im, np.float32) / 255 * s

def _img(arr): return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))

def _cobble():
    n = 256; im = Image.new("RGB", (n, n), (40, 36, 34)); d = ImageDraw.Draw(im); r = np.random.default_rng(2)
    for j in range(8):
        for i in range(8):
            x = i * 32 + (16 if j % 2 else 0) + r.uniform(-2, 2); y = j * 32 + r.uniform(-2, 2); c = int(r.uniform(90, 140))
            d.rounded_rectangle((x + 2, y + 2, x + 30, y + 30), 9, fill=(c, int(c * 0.92), int(c * 0.85)))
            d.rounded_rectangle((x + 2 - n, y + 2, x + 30 - n, y + 30), 9, fill=(c, int(c * 0.92), int(c * 0.85)))
    a = np.asarray(im, np.float32) * (0.85 + 0.3 * _noise(n, n, 3))[..., None]
    return tex(_img(a))

def _planks():
    n = 256; a = np.zeros((n, n, 3), np.float32); r = np.random.default_rng(4)
    for i in range(8):
        c = np.float32([120, 78, 46]) * r.uniform(0.8, 1.1)
        a[:, i * 32:(i + 1) * 32] = c
        a[:, i * 32:i * 32 + 2] = (50, 32, 20)
    a *= (0.8 + 0.35 * _noise(n, n, 5))[..., None]
    for k in range(40): y = r.integers(0, n); x = r.integers(0, 8) * 32; a[y:y + 2, x:x + 32] *= 0.7
    return tex(_img(a))

def _brick(base=(150, 62, 44)):
    n = 256; im = Image.new("RGB", (n, n), (70, 62, 58)); d = ImageDraw.Draw(im); r = np.random.default_rng(6)
    for j in range(16):
        for i in range(-1, 5):
            x = i * 64 + (32 if j % 2 else 0); y = j * 16; f = r.uniform(0.8, 1.15)
            d.rectangle((x + 2, y + 2, x + 62, y + 14), fill=tuple(int(c * f) for c in base))
    return tex(_img(np.asarray(im, np.float32) * (0.85 + 0.25 * _noise(n, n, 7))[..., None]))

def _dirt():
    n = 256; a = np.ones((n, n, 3), np.float32) * np.float32([168, 132, 92])
    a *= (0.78 + 0.35 * _noise(n, n, 8))[..., None]
    return tex(_img(a))

def _grass():
    n = 256; a = np.ones((n, n, 3), np.float32) * np.float32([52, 128, 40])
    a *= (0.7 + 0.5 * _noise(n, n, 9))[..., None]
    return tex(_img(a))

def _asphalt(c=(52, 52, 58), line=None):
    n = 256; a = np.ones((n, n, 3), np.float32) * np.float32(c)
    a *= (0.85 + 0.3 * _noise(n, n, 10))[..., None]
    return tex(_img(a))

def _concrete():
    n = 256; im = Image.new("RGB", (n, n), (150, 152, 160)); d = ImageDraw.Draw(im)
    d.line((0, 0, n, 0), fill=(110, 112, 120), width=4); d.line((0, 0, 0, n), fill=(110, 112, 120), width=4)
    return tex(_img(np.asarray(im, np.float32) * (0.9 + 0.15 * _noise(n, n, 11))[..., None]))

def _timber(seed):
    """German half-timbered facade: cream plaster, dark beams, two rows of lit windows."""
    w, h = 256, 320; im = Image.new("RGB", (w, h), (232, 220, 190)); d = ImageDraw.Draw(im); r = np.random.default_rng(seed)
    B = (70, 44, 30)
    for y in (0, 150, 310): d.rectangle((0, y, w, y + 10), fill=B)
    for x in (0, 84, 168, 246): d.rectangle((x, 0, x + 10, h), fill=B)
    for x0 in (0, 84, 168):
        d.line((x0 + 10, 160, x0 + 84, 300), fill=B, width=8); d.line((x0 + 84, 160, x0 + 10, 300), fill=B, width=8)
    for x0 in (20, 104, 188):
        lit = r.random() < 0.7
        d.rectangle((x0, 40, x0 + 46, 110), fill=(255, 200, 110) if lit else (40, 40, 60)); d.line((x0 + 23, 40, x0 + 23, 110), fill=B, width=4)
    return tex(im)

def _store(name, col):
    w, h = 256, 320; im = Image.new("RGB", (w, h), col); d = ImageDraw.Draw(im)
    for y in range(0, h, 12): d.line((0, y, w, y), fill=tuple(int(c * 0.82) for c in col), width=2)
    d.rectangle((14, 20, w - 14, 80), fill=(240, 230, 200)); d.text((w / 2, 50), name, font=W._f(30 if len(name) < 10 else 22), fill=(60, 30, 20), anchor="mm")
    d.rectangle((24, 150, 110, 300), fill=(255, 210, 140)); d.rectangle((146, 150, 232, 300), fill=(60, 40, 30))
    d.rectangle((24, 150, 110, 300), outline=(60, 40, 30), width=6)
    return tex(im)

def _window_grid(seed, w=256, h=512, base=(30, 26, 30), lit=(255, 190, 110), cols=4, rows=8, p=0.45, glass=False):
    im = Image.new("RGB", (w, h), base); d = ImageDraw.Draw(im); r = np.random.default_rng(seed)
    cw, rh = w / cols, h / rows
    for j in range(rows):
        for i in range(cols):
            on = r.random() < p
            c = tuple(int(x * r.uniform(0.7, 1.0)) for x in lit) if on else tuple(int(x * 1.4) + 8 for x in base)
            m = 3 if glass else 10
            d.rectangle((i * cw + m, j * rh + m, (i + 1) * cw - m, (j + 1) * rh - m), fill=c)
    return tex(im)

@lru_cache(None)
def T(): return dict(cobble=_cobble(), planks=_planks(), brick=_brick(), dirt=_dirt(), grass=_grass(), asphalt=_asphalt(),
                     wet=_asphalt((34, 34, 42)), concrete=_concrete(), timber=[_timber(i) for i in range(3)],
                     stores=[_store(n, c) for n, c in (("GENERAL STORE", (150, 70, 50)), ("HARDWARE", (60, 100, 130)), ("BANK", (180, 170, 140)),
                                                         ("BARBER", (120, 140, 90)), ("DRY GOODS", (160, 120, 60)))],
                     win70=[_window_grid(20 + i, base=(46, 30, 26), lit=(255, 170, 80), p=0.5) for i in range(3)],
                     glassw=[_window_grid(30 + i, w=256, h=1024, base=(14, 22, 40), lit=(150, 205, 255), cols=10, rows=46, p=0.32, glass=True) for i in range(3)],
                     poster=word_tex("GARAGE\nREPAIRS", 256, 128, (240, 220, 160), (110, 30, 26), 40),
                     cal=word_tex("1912", 128, 160, (30, 30, 30), (236, 228, 205), 54),
                     bill=word_tex("EV\nCHARGING", 512, 256, (140, 255, 190), (6, 10, 24), 96))

def ground(kind, t=0.0, v=0.0, x0=-24, x1=24, z0=-16, z1=18, step=2.0, m=MATTE, col=(255, 255, 255), y=0.0):
    off = (v * t) % step
    g = tiles(x0 - off, z0, x1 - off + step, z1, y, step, T()[kind], col, rep=step / 2, m=m)
    return g

# ---------------------------------------------------------------- props
def roof(x0, x1, z0, z1, y, h, col):
    zm = (z0 + z1) / 2
    tr = [[(x0, y, z0), (x1, y, z0), (x1, y + h, zm)], [(x0, y, z0), (x1, y + h, zm), (x0, y + h, zm)],
          [(x1, y, z1), (x0, y, z1), (x0, y + h, zm)], [(x1, y, z1), (x0, y + h, zm), (x1, y + h, zm)],
          [(x0, y, z0), (x0, y + h, zm), (x0, y, z1)], [(x1, y, z1), (x1, y + h, zm), (x1, y, z0)]]
    return P(tr, col, m=SATIN)

def facade_box(x, z, w, d, h, tid, face=1, col=(200, 200, 200), e=0.0):
    """Building block whose street face (+z if face>0) carries texture tid."""
    z0, z1 = (z - d, z) if face > 0 else (z, z + d)
    f = "f" if face > 0 else "b"
    return box(x - w / 2, 0, z0, x + w / 2, h, z1, col, texs={f: tid}, e=e)

def gas_lamp(x, z, t):
    m = cat([cyl(0.05, 0.04, 3.0, 8, (30, 30, 34), SATIN), cb(0, 3.15, 0, 0.26, 0.34, 0.26, (40, 36, 30), b=0.03),
             cb(0, 3.12, 0, 0.2, 0.26, 0.2, (255, 210, 130), b=0.02, e=2.6)]).mv(x, 0, z)
    return m, ((x, 3.12, z), (255, 190, 110), 0.18, 1.2 + 0.08 * math.sin(t * 7 + x))

@lru_cache(None)
def _cart():
    horse = W._horse().copy(); horse.c[:] = rgb((96, 60, 36)); horse.m[:] = SATIN
    horse.sc(0.8).mv(1.4, 0, 0)
    cart = cat([bbox(-1.1, 0.6, -0.55, 0.4, 0.95, 0.55, (110, 70, 40), b=0.03, m=SATIN), bbox(-1.1, 0.95, -0.55, -0.9, 1.4, 0.55, (110, 70, 40), b=0.03, m=SATIN),
                capsule((0.3, 0.75, -0.3), (1.2, 0.95, -0.3), 0.025, 6, (80, 50, 30)), capsule((0.3, 0.75, 0.3), (1.2, 0.95, 0.3), 0.025, 6, (80, 50, 30))])
    wh = [W._spoke_wheel(0.45, 12, 0.08, "wood").copy().rot("y", 180 if s < 0 else 0).mv(-0.4, 0.45, s * 0.6) for s in (1, -1)]
    return cat([horse, cart] + wh)

def pine(h=4.0):
    g = (34, 78, 52)
    return cat([cyl(0.12, 0.1, h * 0.3, 8, (80, 56, 40), SATIN)] +
               [lathe([(h * 0.24 * (1 - k * 0.22), 0.0), (0.0, h * 0.42)], 10, g, SATIN).mv(0, h * (0.25 + 0.2 * k), 0) for k in range(3)])

def birch_tree(h=3.0):
    return cat([cyl(0.1, 0.08, h * 0.55, 8, (110, 80, 60), SATIN), sphere(h * 0.32, 10, 7, (90, 150, 80), SATIN).sc(1, 1.1, 1).mv(0, h * 0.7, 0)])

def cottage(x, z, w=4.0, d=3.0, h=2.6, face=1):
    red = (150, 34, 28); white = (240, 238, 230)
    zf = z if face > 0 else z
    s = [bbox(x - w / 2, 0, z - d / 2, x + w / 2, h, z + d / 2, red, b=0.04, m=SATIN), roof(x - w / 2 - 0.15, x + w / 2 + 0.15, z - d / 2 - 0.2, z + d / 2 + 0.2, h, 1.4, (46, 46, 52))]
    s += [cb(x + sx * (w / 2 - 0.05), h / 2, z + sz * (d / 2 - 0.05), 0.14, h, 0.14, white, b=0.02) for sx in (-1, 1) for sz in (-1, 1)]
    zw = z + d / 2 + 0.01
    for wx in (-w * 0.25, w * 0.25):
        s += [box(x + wx - 0.35, 0.9, zw, x + wx + 0.35, 1.7, zw + 0.02, (255, 210, 140), e=0.7), cb(x + wx, 1.3, zw + 0.02, 0.86, 0.96, 0.02, white, b=0.005)]
    return cat(s)

def pump50(x, z):
    red = (210, 30, 34)
    return cat([bbox(x - 0.32, 0, z - 0.25, x + 0.32, 1.5, z + 0.25, red, b=0.1, m=PAINT), sphere(0.24, 16, 10, (255, 250, 230), MATTE, e=1.6).mv(x, 1.75, z),
                box(x - 0.2, 0.9, z + 0.251, x + 0.2, 1.25, z + 0.26, (240, 240, 230), e=0.3), capsule((x + 0.33, 1.1, z), (x + 0.5, 0.5, z + 0.3), 0.03, 6, (20, 20, 20))])

def streetlight(x, z, t, col=(255, 160, 60), h=4.8, face=1):
    arm = face * 0.9
    m = cat([cyl(0.07, 0.05, h, 8, (60, 60, 66), SATIN).mv(x, 0, z), capsule((x, h, z), (x, h + 0.1, z + arm), 0.04, 6, (60, 60, 66)),
             cb(x, h, z + arm, 0.24, 0.08, 0.5, (40, 40, 44), b=0.02), cb(x, h - 0.05, z + arm, 0.18, 0.03, 0.4, col, b=0.01, e=3.0)])
    return m, ((x, h - 0.1, z + arm), col, 0.25, 1.2), PR.beam((x, h - 0.08, z + arm), (0, -1, 0), h - 0.1, 1.6, col, 0.06)

def charger(x, z):
    return cat([bbox(x - 0.22, 0, z - 0.16, x + 0.22, 1.7, z + 0.16, (236, 238, 242), b=0.08, m=PAINT),
                box(x - 0.14, 1.0, z + 0.161, x + 0.14, 1.45, z + 0.17, (90, 220, 255), e=1.6), cb(x, 0.55, z + 0.17, 0.3, 0.04, 0.02, (90, 220, 255), b=0.005, e=2.5),
                capsule((x + 0.2, 1.0, z + 0.1), (x + 0.5, 0.3, z + 0.5), 0.03, 6, (20, 20, 24))])

# ---------------------------------------------------------------- eras
def _env(**kw): return kw

def era0(t, v, far):
    """1886: cobblestone street in a German town at dusk, timber-framed houses, gas lamps, a horse and cart."""
    s = [ground("cobble", t, v)]
    zb = -6.5 - (6 if far else 0); zf = 13.0
    sp = []; glow = []
    for i, x in enumerate(np.arange(-24, 24, 4.2)):
        xx = wrap(x, t, v); h = 5.0 + (i * 37 % 5) * 0.5
        s.append(facade_box(xx, zb, 4.1, 5, h, T()["timber"][i % 3], 1, (232, 220, 190)))
        s.append(roof(xx - 2.05, xx + 2.05, zb - 5, zb + 0.4, h, 2.2, (150, 52, 40)))
        xx2 = wrap(x + 2, t, v)
        s.append(facade_box(xx2, zf, 4.1, 5, h, T()["timber"][(i + 1) % 3], -1, (232, 220, 190)))
        s.append(roof(xx2 - 2.05, xx2 + 2.05, zf - 0.4, zf + 5, h, 2.2, (150, 52, 40)))
    for x in (-9.0, -1.0, 7.0):
        xx = wrap(x, t, v); m, spr = gas_lamp(xx, zb + 1.0, t); s.append(m); sp.append(spr)
    cx = wrap(-14 + 1.1 * t, t, v)
    s.append(_cart().copy().mv(cx, 0, zb + 2.4))
    env = _env(sky_top=(36, 34, 86), sky_hor=(255, 150, 110), ground=(60, 50, 50), sun_dir=(-0.8, 0.22, -0.55), sun=(255, 170, 120), sun_i=1.7,
               amb_i=0.85, fog=(10, 55), fog_col=(150, 100, 110), exposure=1.05, stars=0.15, bloom=0.85, sun_disc=True, sat=1.15, shadow_size=10,
               points=[((-1.0, 3.0, zb + 1.3), (255, 190, 110), 1.4, 4.0)])
    return s, glow, sp, env

def era1(t, v, far):
    """Brass-era garage: plank floor, brick walls, workbench and tools, oil drums, hanging bulbs, light shafts from a window."""
    s = [ground("planks", t, 0, -8, 8, -5, 14)]
    s.append(box(-8, 0, -5.2, 8, 5, -5.0, (255, 255, 255), texs={"f": T()["brick"]}))
    s.append(box(-8.2, 0, -5.2, -8.0, 5, 14, (255, 255, 255), texs={"r": T()["brick"]}))
    s.append(box(8.0, 0, -5.2, 8.2, 5, 2, (255, 255, 255), texs={"l": T()["brick"]}))
    s.append(box(-1.2, 2.2, -5.0, 1.2, 3.8, -4.98, (190, 220, 255), e=1.2))                           # window
    s += [cb(0, 3.0, -4.97, 0.06, 1.6, 0.04, (40, 36, 30), b=0.01), cb(0, 3.0, -4.97, 2.4, 0.06, 0.04, (40, 36, 30), b=0.01)]
    s.append(box(-5.6, 2.0, -4.99, -3.6, 3.0, -4.97, (255, 255, 255), texs={"f": T()["poster"]}))
    s.append(box(3.2, 2.0, -4.99, 3.9, 2.9, -4.97, (255, 255, 255), texs={"f": T()["cal"]}))
    # workbench + pegboard tools
    s += [bbox(-6.5, 0.85, -4.9, -3.0, 0.95, -4.1, (120, 78, 46), b=0.02, m=SATIN)] + [cb(x, 0.42, z, 0.08, 0.85, 0.08, (90, 60, 36)) for x in (-6.4, -3.1) for z in (-4.8, -4.2)]
    s.append(box(-6.3, 1.2, -4.99, -3.3, 2.0, -4.97, (150, 120, 80)))
    for k in range(7): s.append(capsule((-6.0 + 0.4 * k, 1.35, -4.95), (-6.0 + 0.4 * k, 1.8, -4.95), 0.025, 5, (150, 150, 160), CHROME))
    s += [cyl(0.3, 0.3, 0.9, 16, c, PAINT).mv(x, 0, z) for x, z, c in ((5.0, -4.3, (170, 30, 30)), (5.7, -3.8, (30, 70, 150)), (6.2, -4.5, (170, 30, 30)))]
    s += [lathe([(0.25, 0), (0.42, 0.04), (0.42, 0.18), (0.25, 0.22)], 18, (30, 30, 32), RUBBER).mv(-6.8, 0.22 * k, 1.5) for k in range(4)]
    sp = []; glow = []
    for x in (-2.5, 2.5):
        s += [capsule((x, 5.0, -1.0), (x, 3.3, -1.0), 0.01, 4, (20, 20, 20)), lathe([(0.0, 0.0), (0.25, -0.12)], 14, (40, 60, 40), SATIN).mv(x, 3.3, -1.0),
              sphere(0.07, 10, 6, (255, 220, 150), MATTE, e=4.0).mv(x, 3.2, -1.0)]
        sp.append(((x, 3.2, -1.0), (255, 200, 120), 0.12, 1.3))
    glow.append(PR.beam((0, 3.0, -5.0), (0.15, -0.6, 1), 7.5, 2.2, (200, 220, 255), 0.09))
    env = _env(sky_top=(20, 16, 18), sky_hor=(40, 30, 28), ground=(50, 40, 34), sun_dir=(0.15, 0.6, 1.0), sun=(210, 225, 255), sun_i=1.2,
               amb_i=0.85, fog=(14, 40), fog_col=(40, 30, 26), exposure=1.08, stars=0.0, bloom=0.9, sun_disc=False, sat=1.12, shadow_size=10,
               points=[((-2.5, 3.1, -1.0), (255, 200, 120), 1.6, 3.5), ((2.5, 3.1, -1.0), (255, 200, 120), 1.6, 3.5)])
    return s, glow, sp, env

def era2(t, v, far):
    """1910s American town: dirt road, false-front wooden storefronts on a boardwalk, telegraph poles, afternoon sun."""
    s = [ground("dirt", t, v)]
    zb = -6.0 - (8 if far else 0)
    for i, x in enumerate(np.arange(-24, 24, 4.6)):
        xx = wrap(x, t, v); h = 4.2 + (i * 13 % 3) * 0.6
        s.append(facade_box(xx, zb, 4.5, 6, h, T()["stores"][i % 5], 1, (150, 120, 90)))
    s.append(box(-24, 0.2, zb, 24, 0.3, zb + 1.6, (255, 255, 255), texs={"t": T()["planks"]}))
    for i, x in enumerate(np.arange(-22, 24, 4.6)):
        s.append(facade_box(wrap(x, t, v), 12.0, 4.5, 6, 4.4 + (i * 7 % 3) * 0.5, T()["stores"][(i + 2) % 5], -1, (150, 120, 90)))
    poles = [wrap(x, t, v) for x in np.arange(-24, 24, 8.0)]
    for x in poles: s += [cyl(0.09, 0.07, 6.5, 8, (90, 66, 44), SATIN).mv(x, 0, zb + 2.3), cb(x, 6.2, zb + 2.3, 0.08, 0.08, 1.4, (90, 66, 44))]
    ps = sorted(poles)
    for a, b in zip(ps, ps[1:]):
        if b - a < 9: s += [capsule((a, 6.25, zb + 2.3 + dz), (b, 6.25, zb + 2.3 + dz), 0.008, 3, (20, 20, 20)) for dz in (-0.5, 0.5)]
    s.append(cat([cyl(1.4, 1.4, 2.2, 16, (120, 90, 60), SATIN).mv(0, 9, 0)] + [capsule((sx, 0, sz), (sx * 0.8, 9, sz * 0.8), 0.08, 6, (80, 60, 40)) for sx in (-1.2, 1.2) for sz in (-1.2, 1.2)]).mv(14, 0, zb - 14))
    env = _env(sky_top=(70, 130, 210), sky_hor=(250, 215, 170), ground=(120, 100, 80), sun_dir=(-0.45, 0.7, 0.55), sun=(255, 230, 190), sun_i=2.3,
               amb_i=0.9, fog=(16, 70), fog_col=(230, 205, 170), exposure=0.98, stars=0.0, bloom=0.6, sun_disc=False, sat=1.12, shadow_size=10, points=[])
    return s, [], [], env

def era3(t, v, far):
    """1959 Swedish coast road: asphalt through grass, Falu-red cottages, pines and birches, the sea, a 1950s petrol pump; golden hour."""
    s = [ground("grass", t, v, z0=-24), ground("asphalt", t, v, z0=-2.6, z1=2.6, y=0.004)]
    s += [box(-24, 0.008, z - 0.06, 24, 0.01, z + 0.06, (240, 240, 230)) for z in (-2.4, 2.4)]
    s.append(quad((-80, -0.02, -24), (80, -0.02, -24), (80, -0.02, -90), (-80, -0.02, -90), (40, 90, 150), m=PAINT))
    r = np.random.default_rng(12)
    for i, x in enumerate(np.arange(-22, 22, 7.5)):
        s.append(cottage(wrap(x, t, v), -9.0 - 2 * (i % 2), 4.2, 3.2, 2.6))
    for k in range(26):
        x = r.uniform(-24, 24); z = r.uniform(-20, -6) if k % 3 else r.uniform(8, 16)
        s.append((pine(r.uniform(3.5, 6)) if k % 2 else birch_tree(r.uniform(2.5, 4))).mv(wrap(x, t, v), 0, z))
    for i, x in enumerate(np.arange(-20, 22, 9.0)):
        s.append(cottage(wrap(x + 3, t, v), 10.5 + 2 * (i % 2), 4.2, 3.2, 2.6))
    for k in range(14):
        s.append((pine(r.uniform(4, 6.5)) if k % 2 else birch_tree(r.uniform(2.5, 4))).mv(wrap(r.uniform(-24, 24), t, v), 0, r.uniform(5.5, 9.0)))
    for k in range(12):
        s.append((pine(r.uniform(4.5, 7)) if k % 3 else birch_tree(r.uniform(3, 4.5))).mv(wrap(r.uniform(-22, -7), t, v), 0, r.uniform(-4, 10)))
    s.append(cottage(wrap(-12.0, t, v), 3.5, 4.2, 3.2, 2.6))
    s.append(pump50(4.0, -4.0))
    env = _env(sky_top=(70, 120, 200), sky_hor=(255, 190, 120), ground=(80, 110, 70), sun_dir=(0.75, 0.3, -0.6), sun=(255, 205, 150), sun_i=2.2,
               amb_i=0.9, fog=(18, 80), fog_col=(240, 190, 150), exposure=0.98, stars=0.0, bloom=0.7, sun_disc=True, sat=1.15, shadow_size=10, points=[])
    return s, [], [((4.0, 1.75, -4.0), (255, 240, 200), 0.3, 0.8)], env

def era4(t, v, far):
    """1977 city at night: wet asphalt, brick blocks with lit windows, neon DINER / MOTEL / DRIVE-IN signs, sodium streetlights."""
    s = [ground("wet", t, v, m=PAINT), box(-24, 0.0, -6.0, 24, 0.15, -3.2, (90, 88, 92))]
    zb = -6.0
    glow = []; sp = []
    for i, x in enumerate(np.arange(-24, 24, 6.2)):
        xx = wrap(x, t, v); h = 7 + (i * 7 % 4) * 1.6
        s.append(facade_box(xx, zb, 6.0, 8, h, T()["win70"][i % 3], 1, (110, 70, 54), e=0.7))
        s.append(facade_box(wrap(x + 3, t, v), 13.0, 6.0, 8, h + 2, T()["win70"][(i + 1) % 3], -1, (110, 70, 54), e=0.7))
    for x, txt, col in ((-5.5, "DINER", (255, 70, 160)), (2.5, "MOTEL", (80, 230, 255)), (9.0, "DRIVE-IN", (255, 150, 40))):
        xx = wrap(x, t, v); s.append(W.neon(txt, 2.2 if len(txt) > 5 else 1.8, 0.6, col, 3.2).mv(xx, 3.6, zb + 0.2))
        sp.append(((xx, 3.6, zb + 0.6), col, 0.6, 0.5))
    for x in (-8.0, 0.0, 8.0):
        m, spr, bm = streetlight(wrap(x, t, v), -3.4, t, face=1); s.append(m); sp.append(spr); glow.append(bm)
    env = _env(sky_top=(8, 6, 22), sky_hor=(70, 36, 70), ground=(30, 24, 30), sun_dir=(0.2, 0.9, 0.3), sun=(140, 150, 210), sun_i=0.7,
               amb_i=0.75, fog=(14, 60), fog_col=(40, 26, 44), exposure=1.12, stars=0.35, bloom=1.0, sun_disc=False, sat=1.2, shadow_size=10,
               points=[((0.0, 4.6, -2.5), (255, 160, 60), 2.2, 5.0), ((-5.5, 3.6, -5.0), (255, 70, 160), 1.4, 4.0)])
    return s, glow, sp, env

def era5(t, v, far):
    """Today: concrete plaza at blue hour, glass towers with lit floors, an EV charger, an LED billboard, trees in planters."""
    s = [ground("concrete", t, v, z0=-22)]
    zb = -15.0
    r = np.random.default_rng(15)
    for i, x in enumerate(np.arange(-30, 30, 7.0)):
        h = r.uniform(14, 34); d = r.uniform(5, 8)
        s.append(box(x - 3.2, 0, zb - d, x + 3.2, h, zb, (60, 80, 110), texs={"f": T()["glassw"][i % 3], "r": T()["glassw"][(i + 1) % 3]}, e=0.45, m=GLASS))
    for i, x in enumerate(np.arange(-30, 30, 9.0)):
        h = r.uniform(18, 40)
        s.append(box(x - 3.5, 0, 16, x + 3.5, h, 22, (60, 80, 110), texs={"b": T()["glassw"][i % 3]}, e=0.45, m=GLASS))
    s.append(charger(-4.6, -2.8)); s.append(charger(-3.2, -2.8))
    for x in (-8.5, 8.5):
        s += [bbox(x - 0.6, 0, -4.6, x + 0.6, 0.5, -3.4, (190, 190, 196), b=0.05), birch_tree(3.2).mv(x, 0.5, -4.0)]
    env = _env(sky_top=(14, 26, 70), sky_hor=(120, 110, 190), ground=(40, 44, 60), sun_dir=(-0.3, 0.8, 0.5), sun=(190, 205, 255), sun_i=1.6,
               amb_i=0.95, fog=(18, 70), fog_col=(60, 70, 120), exposure=1.06, stars=0.1, bloom=0.95, sun_disc=False, sat=1.18, shadow_size=10,
               points=[((-3.9, 1.3, -2.4), (90, 220, 255), 1.0, 3.0)])
    return s, [], [], env

ERAS = [era0, era1, era2, era3, era4, era5]

def world(st, t, v=0.0, far=False):
    return ERAS[st](t, v, far)

def _blend_env(a, b, k):
    out = {}
    for key in a:
        x, y = a[key], b.get(key, a[key])
        if key == "points": out[key] = [(p, c, i * (1 - k), r) for p, c, i, r in x] + [(p, c, i * k, r) for p, c, i, r in y]
        elif key == "fog": out[key] = (mix_(x[0], y[0], k), mix_(x[1], y[1], k))
        elif isinstance(x, (tuple, list)): out[key] = tuple(mix_(p, q, k) for p, q in zip(x, y))
        elif isinstance(x, bool): out[key] = y if k > 0.5 else x
        else: out[key] = mix_(x, y, k)
    return out
def mix_(a, b, k): return a + (b - a) * k

def sweep_x(k):
    """Scan position for the world sweep: slow across the car (|x| < 1.6), fast through the far world."""
    p = 2 * min(max(k, 0.0), 1.0) - 1
    return -(1.9 * p + 22 * p ** 7)

def _cut(meshes, xs, keep_lt):
    out = []
    for m in meshes:
        q = m.copy(); cx = q.t.mean(1)[:, 0]; q.keep(cx < xs if keep_lt else cx >= xs)
        if len(q.t): out.append(q)
    return out

def world_wipe(a, b, t, k, v=0.0, far=False):
    """Old era a behind the scan plane (x < xs), new era b in front of it; env blends with k."""
    sa, ga, pa, ea = world(a, t, v, far); sb, gb, pb, eb = world(b, t, v, far)
    xs = sweep_x(k)
    s = _cut(sa, xs, True) + _cut(sb, xs, False)
    g = _cut(ga, xs, True) + _cut(gb, xs, False)
    sp = [x for x in pa if x[0][0] < xs] + [x for x in pb if x[0][0] >= xs]
    return s, g, sp, _blend_env(ea, eb, ease3_(k)), xs
def ease3_(u): u = min(max(u, 0.0), 1.0); return u * u * u * (u * (6 * u - 15) + 10)

def world_scan(xs, acc, k=1.0):
    """Huge faint scan wall sweeping the whole world (plus the bright frame W.scan_fx draws round the car)."""
    if k <= 0: return []
    return [PR.glow_quad(60, 14, acc, 0.22 * k, None).rot("y", 90).mv(xs, 6.5, 0)]
