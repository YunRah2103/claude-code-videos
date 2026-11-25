"""Shared props for the cinematic shorts: volumetric light beams, floodlight towers, gears, speakers, neon signs,
glowing flow tubes, a 3D line graph, phones/screens, and small gag props."""
import math
import numpy as np
from PIL import Image, ImageDraw
from geo import (P, cat, quad, box, cbox, bbox, cb, lathe, cyl, superellipsoid, sphere, capsule, tube, tiles, panel, tex, word_tex,
                 font, rgb, TEX, MATTE, PAINT, GLASS, CHROME, SATIN, RUBBER, GLOW, SCREEN, T_DISC)

def _fade_tex(n=64, p=1.4):
    y = np.linspace(0, 1, n)[:, None]; a = np.repeat((1 - y) ** p, n, 1)
    TEX.append(np.repeat(a[..., None], 3, 2).astype(np.float32)); return len(TEX) - 1
T_FADE = _fade_tex()

def beam(apex, direction, length, radius, col=(255, 230, 190), e=0.35, seg=18, r0=0.05):
    """Additive volumetric cone from apex along direction (fades with distance)."""
    d = np.float32(direction); d /= np.linalg.norm(d)
    up = np.float32([0, 1, 0]) if abs(d[1]) < 0.9 else np.float32([1, 0, 0])
    a = np.cross(d, up); a /= np.linalg.norm(a); b = np.cross(d, a)
    A = np.float32(apex); tris, uvs = [], []
    for j in range(seg):
        t0, t1 = 2 * math.pi * j / seg, 2 * math.pi * (j + 1) / seg
        p0 = A + (a * math.cos(t0) + b * math.sin(t0)) * r0; p1 = A + (a * math.cos(t1) + b * math.sin(t1)) * r0
        q0 = A + d * length + (a * math.cos(t0) + b * math.sin(t0)) * radius; q1 = A + d * length + (a * math.cos(t1) + b * math.sin(t1)) * radius
        tris += [(p0, q0, q1), (p0, q1, p1)]; uvs += [((0, 0), (0, 1), (1, 1)), ((0, 0), (1, 1), (1, 0))]
    return P(np.float32(tris), col, T_FADE, np.float32(uvs), e, GLOW)

def glow_quad(w, h, col, e=1.0, tid=None):
    return quad((-w / 2, -h / 2, 0), (w / 2, -h / 2, 0), (w / 2, h / 2, 0), (-w / 2, h / 2, 0), col, T_DISC if tid is None else tid, e, m=GLOW)

def floodlight(x, z, h=9.0, aim=(0, -1, 0.3), col=(255, 236, 200), beam_e=0.12):
    """Floodlight tower: mast, lamp bank (emissive), additive light cone. Returns (mesh, glow, sprite, point light)."""
    mast = cyl(0.12, 0.09, h, 10, (70, 72, 80), MATTE)
    bank = cat([cb(0, h + 0.3, 0, 1.6, 0.7, 0.25, (40, 40, 46), b=0.05)] +
               [cb(-0.55 + 0.55 * i, h + 0.3 + 0.2 * j - 0.1, 0.14, 0.42, 0.16, 0.04, (255, 250, 235), b=0.01, e=4.0) for i in range(3) for j in range(2)])
    m = cat([mast, bank]).mv(x, 0, z)
    g = beam((x, h + 0.2, z + 0.15), aim, h * 1.4, h * 0.6, col, beam_e)
    return m, g, ((x, h + 0.3, z + 0.2), col, 0.9, 1.2), ((x, h - 1, z + 1.5), col, 1.6, h * 1.2)

def gear(r=0.3, teeth=16, w=0.08, col=(200, 204, 214), m=CHROME, hole=0.3):
    body = cyl(r * 0.86, r * 0.86, w, 32, col, m, capcol=col)
    th = [cb(r * 0.92 * math.cos(a), w / 2, r * 0.92 * math.sin(a), r * 0.18, w * 0.95, r * 0.13, col, b=0.006, m=m).rot("y", -math.degrees(a), (r * 0.92 * math.cos(a), 0, r * 0.92 * math.sin(a)))
          for a in np.linspace(0, 2 * math.pi, teeth, endpoint=False)]
    hub = cyl(r * hole, r * hole, w * 1.3, 16, (60, 62, 70), MATTE).mv(0, -w * 0.15, 0)
    return cat([body, *th, hub])

def speaker(r=0.25, col=(26, 26, 30)):
    cone = lathe([(r * 0.95, 0.0), (r * 0.25, -0.12), (r * 0.12, -0.13)], 24, col, MATTE)
    ring = lathe([(r, 0.01), (r * 1.08, 0.0), (r, -0.01)], 24, (200, 204, 214), CHROME)
    cap = sphere(r * 0.2, 14, 8, (40, 40, 46), SATIN).sc(1, 0.4, 1).mv(0, -0.1, 0)
    box_ = cb(0, -0.12, 0, r * 2.4, 0.2, r * 2.4, (24, 24, 28), b=0.04)
    return cat([box_, cone, ring, cap])

def rings(t, n=4, r0=0.2, spacing=0.35, speed=1.6, col=(80, 200, 255), e=1.5, width=0.03, seg=40):
    """Expanding glow rings in the XY plane (facing +z): sound waves."""
    out = []
    for i in range(n):
        r = r0 + ((t * speed + i * spacing) % (n * spacing))
        fade = max(0.0, 1 - (r - r0) / (n * spacing))
        tr = []
        for j in range(seg):
            a0, a1 = 2 * math.pi * j / seg, 2 * math.pi * (j + 1) / seg
            p = lambda rr, a: (rr * math.cos(a), rr * math.sin(a), 0)
            tr += [p(r - width, a0), p(r + width, a0), p(r + width, a1), p(r - width, a0), p(r + width, a1), p(r - width, a1)]
        out.append(P(np.float32(tr).reshape(-1, 3, 3), col, -1, None, e * fade, GLOW))
    return cat(out)

def neon_sign(text, w, h, col, e=2.4, frame=True):
    tid = word_tex(text, int(256 * w / h) if w / h < 4 else 512, 128 if w / h < 4 else int(512 * h / w), (255, 255, 255), (0, 0, 0), None, weight="black")
    face = quad((-w / 2, -h / 2, 0.02), (w / 2, -h / 2, 0.02), (w / 2, h / 2, 0.02), (-w / 2, h / 2, 0.02), col, tid, e, m=MATTE)
    back = cb(0, 0, -0.03, w + 0.1, h + 0.1, 0.06, (18, 18, 22), b=0.02)
    parts = [back, face]
    if frame:
        parts += [cb(0, s * (h / 2 + 0.04), 0.02, w + 0.1, 0.03, 0.03, col, b=0.01, e=e) for s in (1, -1)] + \
                 [cb(s * (w / 2 + 0.04), 0, 0.02, 0.03, h + 0.1, 0.03, col, b=0.01, e=e) for s in (1, -1)]
    return cat(parts)

def flow(pts, t, col=(70, 190, 255), r=0.03, speed=2.0, e=2.5, segs=40):
    """Glowing tube along a polyline with pulses travelling along it."""
    P_ = [np.float32(p) for p in pts]; L = [float(np.linalg.norm(b - a)) for a, b in zip(P_, P_[1:])]; tot = sum(L)
    out = []
    for k in range(segs):
        s0, s1 = tot * k / segs, tot * (k + 1) / segs
        def at(s):
            acc = 0
            for a, b, l in zip(P_, P_[1:], L):
                if s <= acc + l: return a + (b - a) * ((s - acc) / max(l, 1e-6))
                acc += l
            return P_[-1]
        ph = (s0 / tot - t * speed * 0.25) % 1.0
        bright = 0.35 + 1.0 * math.exp(-((ph - 0.5) / 0.08) ** 2)
        out.append(capsule(at(s0), at(s1), r, 6, col, MATTE).glow(e * bright))
    return cat(out)

def line_graph(vals, w=3.0, h=1.4, reveal=1.0, col=(70, 220, 255), r=0.025, e=2.6):
    """Glowing polyline graph in the XY plane (x 0..w, y 0..h) revealed left to right."""
    n = len(vals); xs = np.linspace(0, w, n); ys = np.float32(vals) * h
    m = max(2, int(n * reveal)); pts = [(xs[i], ys[i], 0) for i in range(m)]
    return cat([capsule(a, b, r, 6, col, MATTE).glow(e) for a, b in zip(pts, pts[1:])]), pts[-1]

def grid_panel(w, h, col=(20, 24, 40), line=(60, 70, 110), n=8):
    im = Image.new("RGB", (512, int(512 * h / w)), col); d = ImageDraw.Draw(im)
    for i in range(1, n): x = i * 512 / n; d.line((x, 0, x, im.height), fill=line, width=2)
    for i in range(1, 5): y = i * im.height / 5; d.line((0, y, 512, y), fill=line, width=2)
    return quad((0, 0, -0.02), (w, 0, -0.02), (w, h, -0.02), (0, h, -0.02), (255, 255, 255), tex(im), 0.35, m=MATTE)

def screen_tex(draw_fn, w=512, h=256, bg=(10, 14, 26)):
    im = Image.new("RGB", (w, h), bg); d = ImageDraw.Draw(im); draw_fn(d, w, h); return tex(im)

def snail(sticker=None):
    shell = cat([sphere(0.07, 16, 10, (200, 130, 70), SATIN).mv(0, 0.075, 0), lathe([(0.0, 0.0), (0.04, 0.005), (0.0, 0.01)], 16, (150, 90, 50)).rot("z", 90).mv(0.071, 0.075, 0)])
    body = cat([capsule((-0.1, 0.02, 0), (0.12, 0.02, 0), 0.025, 10, (170, 200, 130)), capsule((0.11, 0.03, 0), (0.13, 0.1, 0), 0.018, 8, (170, 200, 130)),
                capsule((0.13, 0.1, 0.015), (0.14, 0.15, 0.02), 0.005, 6, (170, 200, 130)), capsule((0.13, 0.1, -0.015), (0.14, 0.15, -0.02), 0.005, 6, (170, 200, 130))])
    parts = [shell, body]
    if sticker is not None: parts.append(box(-0.025, 0.05, 0.068, 0.035, 0.11, 0.072, (255, 255, 255), texs={"f": sticker}))
    return cat(parts)

def duck(s=1.0):
    """Giant inflatable rubber duck."""
    y = (255, 214, 30)
    return cat([superellipsoid(1.0, 0.7, 0.8, 0.9, 0.9, 24, 14, y, SATIN).mv(0, 0.65, 0), sphere(0.55, 20, 12, y, SATIN).mv(0.75, 1.55, 0),
                superellipsoid(0.32, 0.1, 0.22, 0.8, 0.8, 14, 8, (255, 120, 20), SATIN).mv(1.3, 1.48, 0),
                *[sphere(0.07, 10, 6, (20, 20, 24), PAINT).mv(1.18, 1.72, s_ * 0.22) for s_ in (1, -1)]]).sc(s)

def chute(k=1.0):
    """Drag parachute opening (k 0..1), canopy facing -x, attached at the origin."""
    R = 1.3 * k + 0.02; L = 2.4 * k + 0.05
    canopy = superellipsoid(0.5 * R, R, R, 1, 1, 20, 12, (240, 240, 244), SATIN)
    c = canopy.t.mean(1); canopy.keep(c[:, 0] < 0.02)
    stripe = canopy.t.mean(1)[:, 1]; canopy.c[(np.floor((np.arctan2(canopy.t.mean(1)[:, 2], stripe) + math.pi) / (math.pi / 5)) % 2) == 0] = rgb((220, 30, 40))
    canopy.mv(-L, 0, 0)
    lines = [capsule((0, 0, 0), (-L, R * 0.9 * math.cos(a), R * 0.9 * math.sin(a)), 0.006, 4, (230, 230, 230)) for a in np.linspace(0, 2 * math.pi, 8, endpoint=False)]
    return cat([canopy, *lines])

def speed_lines(t, n=14, length=3.0, spread=(2.0, 1.2), col=(220, 235, 255), e=0.8, rng_seed=3):
    """Additive streaks along -x around the origin (motion)."""
    r = np.random.default_rng(rng_seed); out = []
    for i in range(n):
        y, z = r.uniform(0.2, spread[1] * 2), r.uniform(-spread[0], spread[0]); x = ((r.uniform(0, 12) - t * 30) % 12) - 6
        out.append(capsule((x, y, z), (x - length * r.uniform(0.5, 1), y, z), 0.008, 4, col).glow(e).mat(GLOW))
    return cat(out)
