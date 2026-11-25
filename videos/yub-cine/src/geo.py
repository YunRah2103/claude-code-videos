"""Geometry for the cinematic low-poly renderer: triangle bags (P) with per-vertex normals and materials, primitive
builders (bevelled boxes, lathes, lofts, superellipsoids, tubes) and texture helpers. Colours are sRGB 0-255 on input."""
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFont

TEX = []                                   # float32 (h, w, 3) linear-light textures
def tex(img, srgb=True):
    a = np.asarray(img.convert("RGB"), np.float32) / 255.0
    TEX.append(a ** 2.2 if srgb else a); return len(TEX) - 1
TEX.append(np.ones((1, 1, 3), np.float32)); WHITE = 0

# materials: id -> (specular strength, shininess, reflection strength)
MATTE, PAINT, GLASS, CHROME, SATIN, SKIN, GLOW, RUBBER, SCREEN, CLOTH, HAIR = range(11)
MATS = np.float32([[0.04, 10, 0.0], [0.55, 90, 0.30], [0.9, 260, 0.75], [1.0, 140, 0.85], [0.22, 30, 0.10],
                   [0.12, 14, 0.0], [0, 1, 0], [0.04, 6, 0.0], [0.2, 80, 0.15], [0.02, 6, 0.0], [0.25, 22, 0.02]])

def rgb(c):
    if isinstance(c, str):
        c = c.lstrip("#"); c = tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))
    return (np.float32(c) / 255.0) ** 2.2

def rotm(axis, deg):
    a = math.radians(deg); c, s = math.cos(a), math.sin(a)
    if axis == "x": return np.float32([[1, 0, 0], [0, c, -s], [0, s, c]])
    if axis == "y": return np.float32([[c, 0, s], [0, 1, 0], [-s, 0, c]])
    return np.float32([[c, -s, 0], [s, c, 0], [0, 0, 1]])

def _flat(t):
    n = np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0]); n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
    return np.repeat(n[:, None], 3, 1).astype(np.float32)

class P:
    """Triangles t (n,3,3); colour c (n,3) linear; texture k (n,); uv (n,3,2); emission e (n,); material m (n,);
    vertex normals nv (n,3,3)."""
    def __init__(s, t, c=(255, 255, 255), k=-1, uv=None, e=0.0, m=MATTE, nv=None):
        s.t = np.asarray(t, np.float32).reshape(-1, 3, 3); n = len(s.t)
        s.c = np.broadcast_to(rgb(c) if not isinstance(c, np.ndarray) else c, (n, 3)).astype(np.float32).copy()
        s.k = np.full(n, WHITE if k < 0 else k, np.int32)
        s.uv = np.zeros((n, 3, 2), np.float32) if uv is None else np.asarray(uv, np.float32).reshape(n, 3, 2)
        s.e = np.full(n, e, np.float32); s.m = np.full(n, m, np.int8)
        s.nv = _flat(s.t) if nv is None else np.asarray(nv, np.float32).reshape(n, 3, 3)
    def copy(s):
        p = P.__new__(P)
        for a in ("t", "c", "k", "uv", "e", "m", "nv"): setattr(p, a, getattr(s, a).copy())
        return p
    def mv(s, x=0, y=0, z=0): s.t += np.float32([x, y, z]); return s
    def sc(s, x, y=None, z=None):
        f = np.float32([x, x if y is None else y, x if z is None else z]); s.t *= f
        s.nv /= f; s.nv /= np.linalg.norm(s.nv, axis=2, keepdims=True) + 1e-12; return s
    def rot(s, axis, deg, pivot=(0, 0, 0)):
        R = rotm(axis, deg); pv = np.float32(pivot); s.t = (s.t - pv) @ R.T + pv; s.nv = s.nv @ R.T; return s
    def fn(s, f):
        s.t = f(s.t.reshape(-1, 3)).reshape(-1, 3, 3).astype(np.float32); s.nv = _flat(s.t); return s
    def mat(s, m): s.m[:] = m; return s
    def glow(s, e=1.0): s.e[:] = e; return s
    def smooth(s, angle=55.0):
        """Average normals of coincident vertices whose faces differ by less than `angle` degrees."""
        f = _flat(s.t)[:, 0]
        area = np.linalg.norm(np.cross(s.t[:, 1] - s.t[:, 0], s.t[:, 2] - s.t[:, 0]), axis=1)[:, None] + 1e-9
        key = np.round(s.t.reshape(-1, 3) * 2000).astype(np.int64)
        _, inv = np.unique(key, axis=0, return_inverse=True); inv = inv.reshape(-1)
        acc = np.zeros((inv.max() + 1, 3), np.float64)
        np.add.at(acc, inv, np.repeat(f * area, 3, 0))
        g = acc[inv]; g /= np.linalg.norm(g, axis=1, keepdims=True) + 1e-12
        fr = np.repeat(f, 3, 0); ok = (g * fr).sum(1) > math.cos(math.radians(angle))
        s.nv = np.where(ok[:, None], g, fr).reshape(-1, 3, 3).astype(np.float32); return s
    def keep(s, mask):
        for a in ("t", "c", "k", "uv", "e", "m", "nv"): setattr(s, a, getattr(s, a)[mask])
        return s

def cat(parts):
    parts = [p for p in parts if p is not None and len(p.t)]
    p = P.__new__(P)
    for a in ("t", "c", "k", "uv", "e", "m", "nv"): setattr(p, a, np.concatenate([getattr(q, a) for q in parts]))
    return p

UVQ = ((0, 1), (1, 1), (1, 0), (0, 0))
def quad(a, b, c, d, col=(255, 255, 255), k=-1, e=0.0, uvr=(0, 0, 1, 1), m=MATTE):
    """a=bottom-left b=bottom-right c=top-right d=top-left (as seen from the front)."""
    u0, v0, u1, v1 = uvr
    uv = [(u0, v1), (u1, v1), (u1, v0), (u0, v0)]
    return P([a, b, c, a, c, d], col, k, [uv[0], uv[1], uv[2], uv[0], uv[2], uv[3]], e, m)

def box(x0, y0, z0, x1, y1, z1, col=(200, 200, 200), faces=None, texs=None, e=0.0, m=MATTE):
    F = {"f": ((x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)), "b": ((x1, y0, z0), (x0, y0, z0), (x0, y1, z0), (x1, y1, z0)),
         "r": ((x1, y0, z1), (x1, y0, z0), (x1, y1, z0), (x1, y1, z1)), "l": ((x0, y0, z0), (x0, y0, z1), (x0, y1, z1), (x0, y1, z0)),
         "t": ((x0, y1, z1), (x1, y1, z1), (x1, y1, z0), (x0, y1, z0)), "d": ((x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1))}
    faces, texs = faces or {}, texs or {}
    return cat([quad(*q, col=faces.get(f, (255, 255, 255) if texs.get(f, -1) >= 0 else col), k=texs.get(f, -1), e=e, m=m) for f, q in F.items()])

def cbox(cx, cy, cz, sx, sy, sz, col=(200, 200, 200), **kw):
    return box(cx - sx / 2, cy - sy / 2, cz - sz / 2, cx + sx / 2, cy + sy / 2, cz + sz / 2, col, **kw)

def bbox(x0, y0, z0, x1, y1, z1, col, b=None, ftex=-1, m=MATTE, e=0.0, smooth=True):
    """Chamfered cuboid (smooth-shaded bevels). ftex textures the +z face."""
    b = min(x1 - x0, y1 - y0, z1 - z0) * 0.22 if b is None else b
    lo, hi = np.float32([x0, y0, z0]), np.float32([x1, y1, z1])
    def pt(ax, s, u, v):
        p = np.zeros(3, np.float32); o = [a for a in range(3) if a != ax]
        p[ax] = hi[ax] if s > 0 else lo[ax]
        p[o[0]] = (lo[o[0]] + b) if u == 0 else (hi[o[0]] - b); p[o[1]] = (lo[o[1]] + b) if v == 0 else (hi[o[1]] - b)
        return tuple(p)
    tris, ks, uvs = [], [], []
    def add(q, k=-1, uv=((0, 0),) * 3): tris.append(q); ks.append(WHITE if k < 0 else k); uvs.append(uv)
    for ax in range(3):
        for s in (-1, 1):
            a, bb, c, d = pt(ax, s, 0, 0), pt(ax, s, 1, 0), pt(ax, s, 1, 1), pt(ax, s, 0, 1)
            if ax == 2 and s > 0 and ftex >= 0:
                add((a, bb, c), ftex, ((0, 1), (1, 1), (1, 0))); add((a, c, d), ftex, ((0, 1), (1, 0), (0, 0)))
            else: add((a, bb, c)); add((a, c, d))
    for a1 in range(3):
        for a2 in range(a1 + 1, 3):
            k = 3 - a1 - a2
            for s1 in (-1, 1):
                for s2 in (-1, 1):
                    def ptk(ax, s, oax, os_, kk):
                        o = [a for a in range(3) if a != ax]; uv = [0, 0]; uv[o.index(oax)] = 0 if os_ < 0 else 1; uv[o.index(k)] = kk
                        return pt(ax, s, *uv)
                    p1, p2 = ptk(a1, s1, a2, s2, 0), ptk(a1, s1, a2, s2, 1); q1, q2 = ptk(a2, s2, a1, s1, 0), ptk(a2, s2, a1, s1, 1)
                    add((p1, p2, q2)); add((p1, q2, q1))
    for sx in (-1, 1):
        for sy in (-1, 1):
            for sz in (-1, 1):
                S = (sx, sy, sz); corner = []
                for ax in range(3):
                    o = [a for a in range(3) if a != ax]; corner.append(pt(ax, S[ax], 0 if S[o[0]] < 0 else 1, 0 if S[o[1]] < 0 else 1))
                add(tuple(corner))
    p = P(np.float32(tris), col, -1, np.float32(uvs), e, m); p.k = np.int32(ks)
    if ftex >= 0: p.c[p.k == ftex] = 1.0
    return p.smooth(50) if smooth else p

def cb(cx, cy, cz, sx, sy, sz, col, **kw): return bbox(cx - sx / 2, cy - sy / 2, cz - sz / 2, cx + sx / 2, cy + sy / 2, cz + sz / 2, col, **kw)

def lathe(profile, seg=16, col=(200, 200, 200), m=MATTE, captex=-1, e=0.0, angle=60):
    """Revolve a (radius, y) profile around +y. captex textures a flat disc at the last profile point (if radius>0)."""
    out = []
    for i in range(len(profile) - 1):
        (r0, y0), (r1, y1) = profile[i], profile[i + 1]
        for j in range(seg):
            a0, a1 = 2 * math.pi * j / seg, 2 * math.pi * (j + 1) / seg
            p = lambda r, a, y: (r * math.cos(a), y, r * math.sin(a))
            out.append(quad(p(r0, a1, y0), p(r0, a0, y0), p(r1, a0, y1), p(r1, a1, y1), col, m=m, e=e))
    body = cat(out).smooth(angle)
    if captex >= 0 and profile[-1][0] > 0:
        r, y = profile[-1]; tr = []; uv = []
        for j in range(seg):
            a0, a1 = 2 * math.pi * j / seg, 2 * math.pi * (j + 1) / seg
            tr.append([(0, y, 0), (r * math.cos(a0), y, r * math.sin(a0)), (r * math.cos(a1), y, r * math.sin(a1))])
            uv.append([(0.5, 0.5), (0.5 - 0.5 * math.cos(a0), 0.5 - 0.5 * math.sin(a0)), (0.5 - 0.5 * math.cos(a1), 0.5 - 0.5 * math.sin(a1))])
        body = cat([body, P(tr, (255, 255, 255), captex, uv, e, m)])
    return body

def cyl(r0, r1, h, seg=16, col=(200, 200, 200), m=MATTE, cap=True, capcol=None, captex=-1, e=0.0):
    side = lathe([(r0, 0), (r1, h)], seg, col, m, e=e, angle=70)
    caps = []
    if cap:
        for r, y in ((r0, 0), (r1, h)):
            if r <= 0: continue
            tr, uv = [], []
            for j in range(seg):
                a0, a1 = 2 * math.pi * j / seg, 2 * math.pi * (j + 1) / seg
                tr.append([(0, y, 0), (r * math.cos(a0), y, r * math.sin(a0)), (r * math.cos(a1), y, r * math.sin(a1))])
                mm = -1 if y else 1
                uv.append([(0.5, 0.5), (0.5 + mm * 0.5 * math.cos(a0), 0.5 - 0.5 * math.sin(a0)), (0.5 + mm * 0.5 * math.cos(a1), 0.5 - 0.5 * math.sin(a1))])
            caps.append(P(tr, (255, 255, 255) if captex >= 0 else (capcol or col), captex, uv, e, m))
    return cat([side] + caps)

def superellipsoid(a, b, c, e1=0.6, e2=0.6, seg=24, rings=16, col=(200, 200, 200), m=MATTE, e=0.0):
    def sp(v, ex): return np.sign(v) * np.abs(v) ** ex
    th = np.linspace(-math.pi / 2, math.pi / 2, rings + 1); ph = np.linspace(0, 2 * math.pi, seg + 1)
    ct, st = sp(np.cos(th), e1), sp(np.sin(th), e1); cp, spp = sp(np.cos(ph), e2), sp(np.sin(ph), e2)
    V = np.stack([a * ct[:, None] * cp[None], b * np.repeat(st[:, None], seg + 1, 1), c * ct[:, None] * spp[None]], -1).astype(np.float32)
    tris = []
    for i in range(rings):
        for j in range(seg):
            p00, p01, p10, p11 = V[i, j], V[i, j + 1], V[i + 1, j], V[i + 1, j + 1]
            if i > 0: tris.append((p00, p01, p11))
            if i < rings - 1: tris.append((p00, p11, p10))
    return P(np.float32(tris), col, -1, None, e, m).smooth(80)

def sphere(r, seg=16, rings=10, col=(200, 200, 200), m=MATTE, e=0.0):
    return superellipsoid(r, r, r, 1, 1, seg, rings, col, m, e)

def capsule(p0, p1, r, seg=12, col=(200, 200, 200), m=MATTE, r1=None):
    """Rounded limb from p0 to p1 (radius r, optional end radius r1)."""
    r1 = r if r1 is None else r1
    p0, p1 = np.float32(p0), np.float32(p1); L = float(np.linalg.norm(p1 - p0))
    prof = [(0.0, -r)] + [(r * math.cos(a), -r * math.sin(a)) for a in np.linspace(math.pi / 2, 0, 4)[1:]] + \
           [(r1 * math.cos(a), L + r1 * math.sin(a)) for a in np.linspace(0, math.pi / 2, 4)[:-1]] + [(0.0, L + r1)]
    s = lathe(prof, seg, col, m, angle=80)
    d = (p1 - p0) / (L + 1e-9); y = np.float32([0, 1, 0]); ax = np.cross(y, d); sn = np.linalg.norm(ax)
    if sn > 1e-6:
        ax /= sn; ang = math.atan2(sn, float(np.dot(y, d)))
        K = np.float32([[0, -ax[2], ax[1]], [ax[2], 0, -ax[0]], [-ax[1], ax[0], 0]])
        R = np.eye(3, dtype=np.float32) + math.sin(ang) * K + (1 - math.cos(ang)) * K @ K
        s.t = s.t @ R.T; s.nv = s.nv @ R.T
    elif float(np.dot(y, d)) < 0: s.rot("x", 180)
    return s.mv(*p0)

def loft(sections, ring=20, col=(200, 200, 200), m=PAINT, close=True, angle=40, sharp=None):
    """Car-body loft along x. sections: [(x, half_width, y_bottom, y_top, roundness 2..8, shoulder 0..1)]. Each cross-section
    is a superellipse |z/w|^n + |(y-yc)/h|^n = 1, squashed towards the top by `shoulder` (tumblehome)."""
    rings = []
    for x, w, y0, y1, n, sh in sections:
        yc, h = (y0 + y1) / 2, (y1 - y0) / 2; pts = []
        for i in range(ring):
            a = 2 * math.pi * i / ring
            ca, sa = math.cos(a), math.sin(a)
            z = w * np.sign(ca) * abs(ca) ** (2 / n); y = h * np.sign(sa) * abs(sa) ** (2 / n)
            if y > 0: z *= 1 - sh * (y / h) ** 2
            pts.append((x, yc + y, z))
        rings.append(pts)
    tris = []
    for i in range(len(rings) - 1):
        A, B = rings[i], rings[i + 1]
        for j in range(ring):
            j2 = (j + 1) % ring
            tris.append((A[j], B[j], B[j2])); tris.append((A[j], B[j2], A[j2]))
    if close:
        for R, flip in ((rings[0], True), (rings[-1], False)):
            c = tuple(np.mean(np.float32(R), 0))
            for j in range(ring):
                tri = (c, R[j], R[(j + 1) % ring]); tris.append(tri[::-1] if flip else tri)
    return P(np.float32(tris), col, -1, None, 0.0, m).smooth(angle)

def tube(pts, r, seg=8, col=(200, 200, 200), m=MATTE, e=0.0):
    pts = [np.float32(p) for p in pts]; out = []
    for a, b in zip(pts, pts[1:]): out.append(capsule(a, b, r, seg, col, m))
    return cat(out).glow(e) if e else cat(out)

def tiles(x0, z0, x1, z1, y, step, k=-1, col=(255, 255, 255), rep=1.0, e=0.0, m=MATTE):
    out = []
    for x in np.arange(x0, x1 - 1e-6, step):
        for z in np.arange(z0, z1 - 1e-6, step):
            xa, za = min(x + step, x1), min(z + step, z1)
            out.append(quad((x, y, za), (xa, y, za), (xa, y, z), (x, y, z), col, k, e, (0, 0, rep, rep), m))
    return cat(out)

def panel(w, h, tid, e=0.0, m=MATTE, col=(255, 255, 255)):
    """A flat textured rectangle facing +z, centred on the origin."""
    return quad((-w / 2, -h / 2, 0), (w / 2, -h / 2, 0), (w / 2, h / 2, 0), (-w / 2, h / 2, 0), col, tid, e, m=m)

class Cam:
    def __init__(s, eye, tgt, fov=50, roll=0.0, focus=None, aperture=0.0):
        s.eye = np.float32(eye); tgt = np.float32(tgt); f = tgt - s.eye; dist = float(np.linalg.norm(f)); f /= dist
        up = np.float32([math.sin(math.radians(roll)), math.cos(math.radians(roll)), 0])
        r = np.cross(f, up); r /= np.linalg.norm(r); u = np.cross(r, f)
        s.R = np.stack([r, u, -f]); s.fov = fov; s.focus = dist if focus is None else focus; s.aperture = aperture

FONTS = {"black": "/usr/share/fonts/opentype/inter/Inter-Black.otf", "bold": "/usr/share/fonts/opentype/inter/Inter-Bold.otf",
         "xbold": "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf"}
def font(size, w="black"): return ImageFont.truetype(FONTS[w], size)

def word_tex(text, w=256, h=64, fg=(255, 255, 255), bg=(16, 16, 18), size=None, border=None, weight="black"):
    im = Image.new("RGB", (w * 2, h * 2), bg); d = ImageDraw.Draw(im)
    lines = text.split("\n"); size = size or int(h * 0.62 / len(lines))
    for i, ln in enumerate(lines):
        d.text((w, h * 2 * (i + 0.5) / len(lines)), ln, font=font(size * 2, weight), fill=fg, anchor="mm")
    if border: d.rectangle((0, 0, w * 2 - 1, h * 2 - 1), outline=border, width=max(4, h // 8))
    return tex(im.resize((w, h), Image.LANCZOS))

def grad_tex(n=64, kind="beam"):
    """Soft gradients for additive light: 'beam' fades along v and towards u edges; 'disc' radial."""
    y, x = np.mgrid[0:n, 0:n] / (n - 1)
    if kind == "beam": a = (1 - y) ** 1.6 * np.clip(1 - np.abs(x - 0.5) * 2, 0, 1) ** 1.2
    else: a = np.clip(1 - np.hypot(x - 0.5, y - 0.5) * 2, 0, 1) ** 2
    TEX.append(np.repeat(a[..., None], 3, 2).astype(np.float32)); return len(TEX) - 1
T_BEAM = grad_tex(64, "beam"); T_DISC = grad_tex(64, "disc")
