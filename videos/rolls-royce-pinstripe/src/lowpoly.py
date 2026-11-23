"""Tiny PS1-style software renderer: triangles, z-buffer, flat shading, affine (warping) texture mapping,
integer vertex snapping, depth fog, 15-bit colour with ordered dither. Pure numpy + Pillow."""
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H = 270, 480                      # internal resolution; upscaled 4x nearest to 1080x1920
TEX = []                             # float32 (h, w, 3) arrays

def tex(img):
    TEX.append(np.asarray(img.convert("RGB"), np.float32) / 255.0)
    return len(TEX) - 1

def rgb(c):
    if isinstance(c, str):
        c = c.lstrip("#"); c = tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))
    return np.float32(c) / 255.0

def rotm(axis, deg):
    a = math.radians(deg); c, s = math.cos(a), math.sin(a)
    if axis == "x": return np.float32([[1, 0, 0], [0, c, -s], [0, s, c]])
    if axis == "y": return np.float32([[c, 0, s], [0, 1, 0], [-s, 0, c]])
    return np.float32([[c, -s, 0], [s, c, 0], [0, 0, 1]])

class P:
    """A bag of triangles: t (n,3,3) world, c (n,3) colour 0..1, k (n,) texture id or -1, uv (n,3,2), e (n,) emissive."""
    def __init__(s, t, c=(255, 255, 255), k=-1, uv=None, e=0.0):
        s.t = np.asarray(t, np.float32).reshape(-1, 3, 3); n = len(s.t)
        s.c = np.broadcast_to(rgb(c) if not isinstance(c, np.ndarray) else c, (n, 3)).astype(np.float32).copy()
        s.k = np.full(n, k, np.int32)
        s.uv = np.zeros((n, 3, 2), np.float32) if uv is None else np.asarray(uv, np.float32).reshape(n, 3, 2)
        s.e = np.full(n, e, np.float32)
    def copy(s):
        p = P.__new__(P); p.t, p.c, p.k, p.uv, p.e = s.t.copy(), s.c.copy(), s.k.copy(), s.uv.copy(), s.e.copy(); return p
    def mv(s, x=0, y=0, z=0): s.t += np.float32([x, y, z]); return s
    def sc(s, x, y=None, z=None):
        s.t *= np.float32([x, x if y is None else y, x if z is None else z]); return s
    def rot(s, axis, deg, pivot=(0, 0, 0)):
        pv = np.float32(pivot); s.t = (s.t - pv) @ rotm(axis, deg).T + pv; return s
    def fn(s, f):
        s.t = f(s.t.reshape(-1, 3)).reshape(-1, 3, 3).astype(np.float32); return s
    def glow(s, e=1.0): s.e[:] = e; return s

def cat(parts):
    parts = [p for p in parts if p is not None and len(p.t)]
    p = P.__new__(P)
    p.t = np.concatenate([q.t for q in parts]); p.c = np.concatenate([q.c for q in parts])
    p.k = np.concatenate([q.k for q in parts]); p.uv = np.concatenate([q.uv for q in parts])
    p.e = np.concatenate([q.e for q in parts]); return p

UVQ = ((0, 1), (1, 1), (1, 0), (0, 0))
def quad(a, b, c, d, col=(255, 255, 255), k=-1, e=0.0, uvr=(0, 0, 1, 1)):
    """a=bottom-left b=bottom-right c=top-right d=top-left (as seen from the front)."""
    u0, v0, u1, v1 = uvr
    uv = [(u0, v1), (u1, v1), (u1, v0), (u0, v0)]
    return P([a, b, c, a, c, d], col, k, [uv[0], uv[1], uv[2], uv[0], uv[2], uv[3]], e)

def box(x0, y0, z0, x1, y1, z1, col=(200, 200, 200), faces=None, texs=None, e=0.0):
    """faces/texs: dict face->colour / texture id for 'f'(+z) 'b'(-z) 'r'(+x) 'l'(-x) 't'(+y) 'd'(-y)."""
    F = {"f": ((x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)),
         "b": ((x1, y0, z0), (x0, y0, z0), (x0, y1, z0), (x1, y1, z0)),
         "r": ((x1, y0, z1), (x1, y0, z0), (x1, y1, z0), (x1, y1, z1)),
         "l": ((x0, y0, z0), (x0, y0, z1), (x0, y1, z1), (x0, y1, z0)),
         "t": ((x0, y1, z1), (x1, y1, z1), (x1, y1, z0), (x0, y1, z0)),
         "d": ((x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1))}
    faces, texs = faces or {}, texs or {}
    out = []
    for f, q in F.items():
        k = texs.get(f, -1)
        out.append(quad(*q, col=faces.get(f, (255, 255, 255) if k >= 0 else col), k=k, e=e))
    return cat(out)

def cbox(cx, cy, cz, sx, sy, sz, col=(200, 200, 200), **kw):
    return box(cx - sx / 2, cy - sy / 2, cz - sz / 2, cx + sx / 2, cy + sy / 2, cz + sz / 2, col, **kw)

def cyl(r0, r1, h, seg=10, col=(200, 200, 200), cap=True, capcol=None, captex=-1, e=0.0):
    """Along +y from 0 to h; bottom radius r0, top radius r1 (r1=0 -> cone)."""
    out = []
    for i in range(seg):
        a0, a1 = 2 * math.pi * i / seg, 2 * math.pi * (i + 1) / seg
        p = lambda r, a, y: (r * math.cos(a), y, r * math.sin(a))
        out.append(quad(p(r0, a1, 0), p(r0, a0, 0), p(r1, a0, h), p(r1, a1, h), col, e=e))
        if cap:
            for r, y in ((r0, 0), (r1, h)):
                if r <= 0: continue
                m = -1 if y else 1   # mirror the top cap so a texture reads the right way round on both ends
                uv = [(0.5, 0.5), (0.5 + m * 0.5 * math.cos(a0), 0.5 - 0.5 * math.sin(a0)), (0.5 + m * 0.5 * math.cos(a1), 0.5 - 0.5 * math.sin(a1))]
                out.append(P([(0, y, 0), p(r, a0, y), p(r, a1, y)], capcol or col if captex < 0 else (255, 255, 255), captex, uv, e))
    return cat(out)

def sphere(r, seg=8, rings=5, col=(200, 200, 200), e=0.0):
    out = []
    for j in range(rings):
        b0, b1 = math.pi * j / rings - math.pi / 2, math.pi * (j + 1) / rings - math.pi / 2
        for i in range(seg):
            a0, a1 = 2 * math.pi * i / seg, 2 * math.pi * (i + 1) / seg
            p = lambda a, b: (r * math.cos(b) * math.cos(a), r * math.sin(b), r * math.cos(b) * math.sin(a))
            out.append(quad(p(a1, b0), p(a0, b0), p(a0, b1), p(a1, b1), col, e=e))
    return cat(out)

def prism(pts, z0, z1, col=(200, 200, 200), capcol=None, captex=-1, uvbox=None):
    """Convex XY polygon extruded along z. Caps are fans; captex maps the polygon's bounding box (or uvbox)."""
    pts = [tuple(p) for p in pts]; n = len(pts); out = []
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    bx0, by0, bx1, by1 = uvbox or (min(xs), min(ys), max(xs), max(ys))
    uv = lambda p: ((p[0] - bx0) / (bx1 - bx0), 1 - (p[1] - by0) / (by1 - by0))
    for z, flip in ((z1, False), (z0, True)):
        for i in range(1, n - 1):
            tri = [pts[0], pts[i], pts[i + 1]]
            if flip: tri = tri[::-1]
            out.append(P([(x, y, z) for x, y in tri], (255, 255, 255) if captex >= 0 else (capcol or col),
                         captex, [uv(p) if captex >= 0 else (0, 0) for p in tri]))
    for i in range(n):
        a, b = pts[i], pts[(i + 1) % n]
        out.append(quad((a[0], a[1], z0), (b[0], b[1], z0), (b[0], b[1], z1), (a[0], a[1], z1), col))
    return cat(out)

def tiles(x0, z0, x1, z1, y, step, k=-1, col=(255, 255, 255), rep=1.0, e=0.0):
    """Floor/ceiling grid (subdivided so near-plane culling does not eat it)."""
    out = []
    xs = np.arange(x0, x1 - 1e-6, step); zs = np.arange(z0, z1 - 1e-6, step)
    for x in xs:
        for z in zs:
            xa, za = min(x + step, x1), min(z + step, z1)
            out.append(quad((x, y, za), (xa, y, za), (xa, y, z), (x, y, z), col, k, e, (0, 0, rep, rep)))
    return cat(out)

def wall(x0, y0, x1, y1, z, step, k=-1, col=(255, 255, 255), rep=1.0, axis="z", e=0.0):
    """Vertical grid facing +z (axis 'z', at depth z) or facing +x (axis 'x', at x=z, x0/x1 are z range)."""
    out = []
    for a in np.arange(x0, x1 - 1e-6, step):
        for b in np.arange(y0, y1 - 1e-6, step):
            aa, bb = min(a + step, x1), min(b + step, y1)
            if axis == "z": q = ((a, b, z), (aa, b, z), (aa, bb, z), (a, bb, z))
            else: q = ((z, b, aa), (z, b, a), (z, bb, a), (z, bb, aa))
            out.append(quad(*q, col=col, k=k, e=e, uvr=(0, 0, rep, rep)))
    return cat(out)

# ---------------------------------------------------------------- camera + raster
class Cam:
    def __init__(s, eye, tgt, fov=60, roll=0.0):
        s.eye = np.float32(eye); tgt = np.float32(tgt); f = tgt - s.eye; f /= np.linalg.norm(f)
        up = np.float32([math.sin(math.radians(roll)), math.cos(math.radians(roll)), 0])
        r = np.cross(f, up); r /= np.linalg.norm(r); u = np.cross(r, f)
        s.R = np.stack([r, u, -f]); s.fov = fov

BAYER = (np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]], np.float32) + 0.5) / 16 - 0.5

def sky(top, bottom):
    a, b = rgb(top), rgb(bottom); g = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
    return np.broadcast_to(a * (1 - g) + b * g, (H, W, 3)).copy()

def _detail(seed=11, n=32):
    """Grime texture multiplied over every untextured face (PS1 games textured everything)."""
    r = np.random.default_rng(seed)
    a = r.normal(0, 1, (n // 4, n // 4)).repeat(4, 0).repeat(4, 1) * 0.5 + r.normal(0, 1, (n, n)) * 0.5
    a = 0.93 + 0.09 * np.clip(a, -2, 2)
    for _ in range(6):                     # a few scratches / stains
        y, x = r.integers(0, n, 2); a[y, max(0, x - 5):x + 5] *= 0.86
    return np.repeat(a[..., None], 3, 2).astype(np.float32)
TEX.append(_detail()); DETAIL = len(TEX) - 1
TEX.append(np.ones((1, 1, 3), np.float32)); WHITE = len(TEX) - 1

def render(scene, cam, bg, light=(-0.4, 0.8, 0.45), amb=0.45, dif=0.65, fog=None, near=0.05, points=()):
    """Gouraud-lit (per-vertex) PS1 raster. fog = (near, far, colour). points = [(pos, rgb 0-255, radius)]."""
    p = scene if isinstance(scene, P) else cat(scene)
    t = p.t; N = len(t)
    n = np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0]); n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-9
    tow = cam.eye - t.mean(1); n[(n * tow).sum(1) < 0] *= -1
    L = np.float32(light); L /= np.linalg.norm(L)
    base = amb + dif * np.clip(n @ L, 0, 1) + 0.12 * np.clip(n @ np.float32([0.5, 0.2, -0.8]), 0, 1)
    vs = np.repeat(base[:, None, None], 3, 1) * np.ones((1, 1, 3), np.float32)       # (N, 3 verts, rgb)
    for pos, c, rad in points:
        dv = np.float32(pos) - t; dist = np.linalg.norm(dv, axis=2) + 1e-6
        lam = np.clip((dv * n[:, None, :]).sum(2) / dist, 0, 1) * np.clip(1 - dist / rad, 0, 1) ** 2
        vs += lam[..., None] * rgb(c) * 1.3
    vs[p.e > 0] = 1.0
    vs = np.clip(vs, 0, 1.6).astype(np.float32)
    # planar uv for the grime layer on untextured, non-emissive faces
    ks, uvs = p.k.copy(), p.uv.copy()
    plain = (ks < 0) & (p.e <= 0)
    ax = np.abs(n).argmax(1)
    for a, (i, j) in enumerate(((1, 2), (0, 2), (0, 1))):
        sel = plain & (ax == a)
        uvs[sel] = np.stack([t[sel][..., i], t[sel][..., j]], -1) * 1.7
    ks[plain] = DETAIL
    ks[ks < 0] = WHITE
    col = p.c
    v = (t - cam.eye) @ cam.R.T
    d = -v[..., 2]
    inside = d > near
    keep = inside.all(1)
    part = np.nonzero(inside.any(1) & ~keep)[0]
    if len(part):                    # clip triangles that cross the near plane (Sutherland-Hodgman, one plane)
        nv, nuv, ns, nc, nk = [], [], [], [], []
        for i in part:
            poly = []
            for j in range(3):
                a, b = j, (j + 1) % 3
                if inside[i, a]: poly.append((v[i, a], uvs[i, a], vs[i, a]))
                if inside[i, a] != inside[i, b]:
                    s = (d[i, a] - near) / (d[i, a] - d[i, b])
                    poly.append(tuple(q[a] + s * (q[b] - q[a]) for q in (v[i], uvs[i], vs[i])))
            for j in range(1, len(poly) - 1):
                tri = (poly[0], poly[j], poly[j + 1])
                nv.append([q[0] for q in tri]); nuv.append([q[1] for q in tri]); ns.append([q[2] for q in tri])
                nc.append(col[i]); nk.append(ks[i])
        v, uvs, vs, col, ks = v[keep], uvs[keep], vs[keep], col[keep], ks[keep]
        if nv:
            v = np.concatenate([v, np.float32(nv)]); uvs = np.concatenate([uvs, np.float32(nuv)])
            vs = np.concatenate([vs, np.float32(ns)]); col = np.concatenate([col, np.float32(nc)]); ks = np.concatenate([ks, np.int32(nk)])
    else:
        v, uvs, vs, col, ks = v[keep], uvs[keep], vs[keep], col[keep], ks[keep]
    d = -v[..., 2]; keep = np.ones(len(v), bool)
    f = (H / 2) / math.tan(math.radians(cam.fov) / 2)
    with np.errstate(divide="ignore", invalid="ignore"):
        sx = np.round(W / 2 + v[..., 0] / d * f); sy = np.round(H / 2 - v[..., 1] / d * f)   # integer snap = PS1 wobble
    keep &= (sx.max(1) >= 0) & (sx.min(1) < W) & (sy.max(1) >= 0) & (sy.min(1) < H)
    img = bg.copy(); zb = np.full((H, W), np.inf, np.float32)
    idx = np.nonzero(keep)[0]
    idx = idx[np.argsort(d[idx].min(1))]
    for i in idx:
        x0, x1, x2 = sx[i]; y0, y1, y2 = sy[i]
        area = (x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0)
        if abs(area) < 0.5: continue
        mnx, mxx = int(max(min(x0, x1, x2), 0)), int(min(max(x0, x1, x2), W - 1))
        mny, mxy = int(max(min(y0, y1, y2), 0)), int(min(max(y0, y1, y2), H - 1))
        if mnx > mxx or mny > mxy: continue
        X = np.arange(mnx, mxx + 1, dtype=np.float32)[None, :] + 0.5
        Y = np.arange(mny, mxy + 1, dtype=np.float32)[:, None] + 0.5
        w0 = ((x1 - X) * (y2 - Y) - (x2 - X) * (y1 - Y)) / area
        w1 = ((x2 - X) * (y0 - Y) - (x0 - X) * (y2 - Y)) / area
        w2 = 1 - w0 - w1
        m = (w0 >= 0) & (w1 >= 0) & (w2 >= 0)
        if not m.any(): continue
        dz = d[i]; z = w0 * dz[0] + w1 * dz[1] + w2 * dz[2]
        sub = zb[mny:mxy + 1, mnx:mxx + 1]
        m &= z < sub
        if not m.any(): continue
        sub[m] = z[m]
        a0, a1, a2 = w0[m][:, None], w1[m][:, None], w2[m][:, None]
        shade = a0 * vs[i, 0] + a1 * vs[i, 1] + a2 * vs[i, 2]
        T = TEX[ks[i]]; th, tw = T.shape[:2]; uv = uvs[i]
        u = a0[:, 0] * uv[0, 0] + a1[:, 0] * uv[1, 0] + a2[:, 0] * uv[2, 0]      # affine: no perspective divide (PS1)
        vv = a0[:, 0] * uv[0, 1] + a1[:, 0] * uv[1, 1] + a2[:, 0] * uv[2, 1]
        px = np.floor(u * tw).astype(np.int32) % tw; py = np.floor(vv * th).astype(np.int32) % th
        img[mny:mxy + 1, mnx:mxx + 1][m] = T[py, px] * col[i] * shade
    if fog:
        fn, ff, fc = fog
        a = np.clip((zb - fn) / (ff - fn), 0, 1)[..., None]
        img = img * (1 - a) + rgb(fc) * a
    return img

_yy, _xx = np.mgrid[0:H, 0:W]
VIGNETTE = (1 - 0.38 * (((_xx - W / 2) / (W / 2)) ** 2 + ((_yy - H / 2) / (H / 2)) ** 2) ** 1.4).clip(0.45, 1)[..., None].astype(np.float32)

def finish(img, scale=4, seed=0):
    """Grade (crushed blacks, warm-green PS1 tint, vignette, grain), 15-bit colour with ordered dither, nearest upscale."""
    g = np.clip(img, 0, 1.2)
    g = np.clip((g - 0.04) * 1.08, 0, 1) ** 1.1
    g = g * np.float32([1.0, 1.0, 0.94]) + np.float32([0.0, 0.01, 0.015])
    g = g * VIGNETTE + np.random.default_rng(seed).normal(0, 0.012, (H, W, 1)).astype(np.float32)
    b = np.tile(BAYER, (H // 4 + 1, W // 4 + 1))[:H, :W, None]
    q = np.clip(np.floor(np.clip(g, 0, 1) * 31 + 0.5 + b * 1.1), 0, 31) / 31
    out = (q * 255).astype(np.uint8)
    return out.repeat(scale, 0).repeat(scale, 1)

def font(size, bold=True, serif=False):
    for f in (["/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"] if serif else []) + \
             ["/usr/share/fonts/opentype/inter/Inter-Bold.otf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]:
        try: return ImageFont.truetype(f, size)
        except OSError: pass
    return ImageFont.load_default()
