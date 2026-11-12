"""Tiny numpy 3D renderer: perspective camera, z-buffered triangle rasterizer, per-pixel attributes.

Meshes are dicts: V (n,3) world verts, N (n,3) world normals, F (m,3) faces, Lc (n,3) local coords (for
procedural materials), obj (int), discard(Lc) -> bool mask (optional, evaluated per fragment before the z-test).
raster() returns depth, obj id, local coords and normals per pixel; shading is done by the caller.
"""
import math
import numpy as np


def norm(v): return v / np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-9)


class Cam:
    def __init__(self, eye, target, fov_deg, w, h, up=(0, 0, 1)):
        self.eye = np.array(eye, float); t = np.array(target, float)
        f = norm(t - self.eye); r = norm(np.cross(f, up)); u = np.cross(r, f)
        self.R = np.stack([r, u, f]); self.w, self.h = w, h
        self.f = (h / 2) / math.tan(math.radians(fov_deg) / 2)

    def project(self, P):
        c = (P - self.eye) @ self.R.T
        z = c[:, 2]
        return self.w / 2 + self.f * c[:, 0] / z, self.h / 2 - self.f * c[:, 1] / z, z

    def rays(self, sx, sy):
        d = np.stack([(sx - self.w / 2) / self.f, -(sy - self.h / 2) / self.f, np.ones_like(sx)], -1)
        return norm(d @ self.R)


def grid_faces(nu, nv, wrap_v=False):
    """Faces for a (nu, nv) vertex grid (u = stations, v = around)."""
    vv = nv if wrap_v else nv - 1
    i, j = np.meshgrid(np.arange(nu - 1), np.arange(vv), indexing='ij')
    a = i * nv + j; b = i * nv + (j + 1) % nv; c = (i + 1) * nv + j; d = (i + 1) * nv + (j + 1) % nv
    return np.concatenate([np.stack([a, c, b], -1).reshape(-1, 3), np.stack([b, c, d], -1).reshape(-1, 3)])


def grid_normals(G, outward_ref=None):
    """Vertex normals of a (nu, nv, 3) grid from finite differences; flipped to point away from outward_ref."""
    du = np.gradient(G, axis=0); dv = np.gradient(G, axis=1)
    n = norm(np.cross(du, dv))
    if outward_ref is not None:
        s = np.sign(np.sum(n * (G - outward_ref), -1, keepdims=True)); s[s == 0] = 1; n = n * s
    return n


def raster(meshes, cam, W, H, near=0.1):
    zbuf = np.full(W * H, np.inf, np.float32)
    obuf = np.full(W * H, -1, np.int16)
    lbuf = np.zeros((W * H, 3), np.float32); nbuf = np.zeros((W * H, 3), np.float32)
    for m in meshes:
        sx, sy, z = cam.project(m['V'])
        F = m['F']
        zf = z[F]
        ok = (zf > near).all(1)
        fn = m['N'][F].mean(1); cen = m['V'][F].mean(1)
        ok &= np.sum(fn * (cam.eye - cen), 1) > -0.02 * np.linalg.norm(cam.eye - cen, axis=1) if m.get('cull', True) else ok
        X, Y = sx[F], sy[F]
        x0 = np.floor(X.min(1)); x1 = np.ceil(X.max(1)); y0 = np.floor(Y.min(1)); y1 = np.ceil(Y.max(1))
        ok &= (x1 >= 0) & (x0 < W) & (y1 >= 0) & (y0 < H)
        area = (X[:, 1] - X[:, 0]) * (Y[:, 2] - Y[:, 0]) - (X[:, 2] - X[:, 0]) * (Y[:, 1] - Y[:, 0])
        ok &= np.abs(area) > 1e-6
        size = np.maximum(x1 - x0, y1 - y0)
        for k in (2, 4, 8, 16, 32, 64, 128):
            sel = np.nonzero(ok & (size <= k) & (size > k // 2 if k > 2 else True))[0]
            if not len(sel): continue
            for ch in np.array_split(sel, max(1, len(sel) * k * k // 2_000_000 + 1)):
                _frag(m, ch, k, X, Y, zf, area, x0, y0, W, H, zbuf, obuf, lbuf, nbuf)
        big = np.nonzero(ok & (size > 128))[0]
        for f in big:                                                 # rare: very close faces
            _frag(m, np.array([f]), int(size[f]) + 1, X, Y, zf, area, x0, y0, W, H, zbuf, obuf, lbuf, nbuf)
    return zbuf.reshape(H, W), obuf.reshape(H, W), lbuf.reshape(H, W, 3), nbuf.reshape(H, W, 3)


def _frag(m, ch, k, X, Y, zf, area, x0, y0, W, H, zbuf, obuf, lbuf, nbuf):
    oy, ox = np.divmod(np.arange(k * k), k)
    px = x0[ch, None] + ox[None]; py = y0[ch, None] + oy[None]
    cx, cy = px + 0.5, py + 0.5
    Xc, Yc, A = X[ch], Y[ch], area[ch][:, None]
    w0 = ((Xc[:, 1, None] - cx) * (Yc[:, 2, None] - cy) - (Xc[:, 2, None] - cx) * (Yc[:, 1, None] - cy)) / A
    w1 = ((Xc[:, 2, None] - cx) * (Yc[:, 0, None] - cy) - (Xc[:, 0, None] - cx) * (Yc[:, 2, None] - cy)) / A
    w2 = 1 - w0 - w1
    ins = (w0 >= -1e-4) & (w1 >= -1e-4) & (w2 >= -1e-4) & (px >= 0) & (px < W) & (py >= 0) & (py < H)
    fi, si = np.nonzero(ins)
    if not len(fi): return
    b = np.stack([w0[fi, si], w1[fi, si], w2[fi, si]], 1)
    zz = zf[ch[fi]]
    bp = b / zz; s = bp.sum(1, keepdims=True); bp /= s                    # perspective-correct weights
    z = 1 / s[:, 0]
    F = m['F'][ch[fi]]
    Lc = np.einsum('ij,ijk->ik', bp, m['Lc'][F])
    keep = np.ones(len(z), bool)
    if 'discard' in m: keep = ~m['discard'](Lc)
    pix = (py[fi, si] * W + px[fi, si]).astype(np.int64)[keep]
    z = z[keep]; Lc = Lc[keep]; bp = bp[keep]; F = F[keep]
    order = np.lexsort((z, pix)); pix = pix[order]; z = z[order]
    first = np.ones(len(pix), bool); first[1:] = pix[1:] != pix[:-1]
    sel = order[first]; pix = pix[first]; z = z[first]
    win = z < zbuf[pix]
    pix = pix[win]; sel = sel[win]
    zbuf[pix] = z[win]; obuf[pix] = m['obj']; lbuf[pix] = Lc[sel]
    nbuf[pix] = norm(np.einsum('ij,ijk->ik', bp[sel], m['N'][F[sel]]))


def inpoly(px, py, poly):
    poly = np.asarray(poly, float); inside = np.zeros(px.shape, bool)
    xa, ya = poly[:, 0], poly[:, 1]; xb, yb = np.roll(xa, -1), np.roll(ya, -1)
    for i in range(len(poly)):
        c = ((ya[i] > py) != (yb[i] > py)) & (px < (xb[i] - xa[i]) * (py - ya[i]) / (yb[i] - ya[i] + 1e-12) + xa[i])
        inside ^= c
    return inside


def dist_poly(px, py, pts):
    """Distance from points to an open polyline."""
    pts = np.asarray(pts, float); d = np.full(px.shape, np.inf)
    for (ax, ay), (bx, by) in zip(pts[:-1], pts[1:]):
        vx, vy = bx - ax, by - ay; L2 = vx * vx + vy * vy + 1e-12
        t = np.clip(((px - ax) * vx + (py - ay) * vy) / L2, 0, 1)
        d = np.minimum(d, np.hypot(px - ax - t * vx, py - ay - t * vy))
    return d


def cubic(p0, p1, p2, p3, n=24):
    t = np.linspace(0, 1, n)[:, None]
    p0, p1, p2, p3 = map(np.array, (p0, p1, p2, p3))
    return (1 - t) ** 3 * p0 + 3 * (1 - t) ** 2 * t * p1 + 3 * (1 - t) * t ** 2 * p2 + t ** 3 * p3


def path(start, *segs):
    pts = [np.array([start], float)]
    for s in segs:
        last = pts[-1][-1]
        pts.append(cubic(last, *s)[1:] if len(s) == 3 else np.array(s, float))
    return np.concatenate(pts)


def smooth_curve(pts, n=600):
    """Smooth function f(x) through control points (Catmull-Rom in x, then interp)."""
    p = np.asarray(pts, float)
    P = np.concatenate([p[:1] * 2 - p[1:2], p, p[-1:] * 2 - p[-2:-1]])
    out = []
    for i in range(1, len(P) - 2):
        t = np.linspace(0, 1, 30, endpoint=False)[:, None]
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t ** 2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(P[-2:-1]); c = np.concatenate(out)
    o = np.argsort(c[:, 0]); xs, ys = c[o, 0], c[o, 1]
    return lambda x: np.interp(x, xs, ys)


def catmull(P, n):
    """Points along a Catmull-Rom spline through P (k,2), resampled evenly by arc length."""
    P = np.asarray(P, float)
    E = np.concatenate([P[:1] * 2 - P[1:2], P, P[-1:] * 2 - P[-2:-1]])
    seg = []
    t = np.linspace(0, 1, 16, endpoint=False)[:, None]
    for i in range(1, len(E) - 2):
        p0, p1, p2, p3 = E[i - 1], E[i], E[i + 1], E[i + 2]
        seg.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t ** 2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    seg.append(E[-2:-1]); c = np.concatenate(seg)
    d = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(c, axis=0), axis=1))])
    s = np.linspace(0, d[-1], n)
    return np.stack([np.interp(s, d, c[:, 0]), np.interp(s, d, c[:, 1])], 1)
