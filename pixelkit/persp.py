"""Top-down perspective for pixel scenes: a camera above (cx, cy) looking
straight down. World x/y are floor pixels (z = 0 maps 1:1), z is height
toward the camera. Points at height z spread away from the centre by
f / (f - z), so walls become slanted faces and tall props lean outward.

Everything is drawn with nearest-neighbour sampling at native resolution:
`warp` paints a flat pixel-art image onto a floor, wall or box face by
inverse-mapping every covered screen pixel to one image pixel. No blending,
no smoothing: edges come out as pixel staircases.
"""
import numpy as np

from .core import T, curve_points


class Persp:
    def __init__(self, w, h, cx, cy, f):
        self.w, self.h, self.cx, self.cy, self.f = w, h, float(cx), float(cy), float(f)
        self.yy, self.xx = np.mgrid[0:h, 0:w].astype(float) + 0.5

    def s(self, z):
        return self.f / (self.f - z)

    def P(self, x, y, z=0.0):
        s = self.s(z)
        return (self.cx + (x - self.cx) * s, self.cy + (y - self.cy) * s)

    # ------------------------------------------------------------- texture ---
    def warp(self, c, img, plane, k, a0, a1, b0, b1, write=True):
        """Paint index image `img` onto a world rectangle.
        plane 'z': horizontal at height k, a = x range, b = y range.
        plane 'y': vertical at y = k,      a = x range, b = z range.
        plane 'x': vertical at x = k,      a = y range, b = z range.
        Image row 0 is the far edge for 'z' (b0) and the TOP for walls (b1).
        Returns the bool mask of covered screen pixels."""
        if np.isscalar(img):
            img = np.full((max(1, int(round(b1 - b0))), max(1, int(round(a1 - a0)))), img, np.uint8)
        xx, yy, cx, cy, f = self.xx, self.yy, self.cx, self.cy, self.f
        with np.errstate(divide="ignore", invalid="ignore"):
            if plane == "z":
                s = self.s(k)
                u, v = cx + (xx - cx) / s - a0, cy + (yy - cy) / s - b0
                ok = np.ones_like(xx, bool)
            elif plane == "y":
                s = (yy - cy) / (k - cy)
                z = f * (1 - 1 / s)
                u, v = cx + (xx - cx) / s - a0, b1 - z
                ok = (s > 0) & (z >= b0 - 1e-6) & (z <= b1 + 1e-6)
            else:
                s = (xx - cx) / (k - cx)
                z = f * (1 - 1 / s)
                u, v = cy + (yy - cy) / s - a0, b1 - z
                ok = (s > 0) & (z >= b0 - 1e-6) & (z <= b1 + 1e-6)
        ih, iw = img.shape
        du, dv = a1 - a0, b1 - b0
        m = ok & (u >= 0) & (u < du) & (v >= 0) & (v < dv)
        iu = np.clip((u[m] * iw / du).astype(int), 0, iw - 1)
        iv = np.clip((v[m] * ih / dv).astype(int), 0, ih - 1)
        vals = img[iv, iu]
        keep = vals != T
        ys, xs = np.nonzero(m)
        ys, xs, vals = ys[keep], xs[keep], vals[keep]
        if write:
            c.a[ys, xs] = vals
        out = np.zeros(m.shape, bool)
        out[ys, xs] = True
        return out

    def box(self, c, x0, y0, x1, y1, z0, z1, top, ns, ew, hi=None, line=None, ao=None):
        """Axis-aligned box. Draws only the faces turned toward the camera
        centre, then the top. top/ns/ew are colours or index images (ns =
        north/south faces, ew = east/west faces). `hi` dashes a highlight
        along the top's camera-facing edges (also breaks long straight runs)."""
        cx, cy = self.cx, self.cy
        if y1 <= cy:
            self.warp(c, ns, "y", y1, x0, x1, z0, z1)
        if y0 >= cy:
            self.warp(c, ns, "y", y0, x0, x1, z0, z1)
        if x1 <= cx:
            self.warp(c, ew, "x", x1, y0, y1, z0, z1)
        if x0 >= cx:
            self.warp(c, ew, "x", x0, y0, y1, z0, z1)
        self.warp(c, top, "z", z1, x0, x1, y0, y1)
        if hi is not None:
            edges = []
            if y1 <= cy:
                edges.append(((x0, y1), (x1, y1)))
            if y0 >= cy:
                edges.append(((x0, y0), (x1, y0)))
            if x1 <= cx:
                edges.append(((x1, y0), (x1, y1)))
            if x0 >= cx:
                edges.append(((x0, y0), (x0, y1)))
            for (ax, ay), (bx, by) in edges:
                self.dashed(c, self.P(ax, ay, z1 - 0.5), self.P(bx, by, z1 - 0.5), hi)
        if line is not None:                     # dashed rim on the far top edges
            for (ax, ay), (bx, by) in (((x0, y0), (x1, y0)), ((x0, y1), (x1, y1)),
                                       ((x0, y0), (x0, y1)), ((x1, y0), (x1, y1))):
                if not ((y1 <= cy and ay == y1 == by) or (y0 >= cy and ay == y0 == by) or
                        (x1 <= cx and ax == x1 == bx) or (x0 >= cx and ax == x0 == bx)):
                    self.dashed(c, self.P(ax, ay, z1 - 0.5), self.P(bx, by, z1 - 0.5), line, on=5, off=2)
        if ao is not None and z0 == 0:           # dashed contact shadow on the floor
            o = 1
            if y1 <= cy:
                self.dashed(c, (x0, y1 + o), (x1, y1 + o), ao, on=4, off=2)
            if y0 >= cy:
                self.dashed(c, (x0, y0 - o), (x1, y0 - o), ao, on=4, off=2)
            if x1 <= cx:
                self.dashed(c, (x1 + o, y0), (x1 + o, y1), ao, on=4, off=2)
            if x0 >= cx:
                self.dashed(c, (x0 - o, y0), (x0 - o, y1), ao, on=4, off=2)

    def extrude(self, c, mask, x, y, z0, z1, side, top_img):
        """Prism from any footprint mask (blobs, cushions): side colour stacked
        from z0 to z1 along the perspective direction, then the top image."""
        h, w = mask.shape
        ccx, ccy = x + w / 2, y + h / 2
        side_spr = np.where(mask, np.uint8(side), np.uint8(T))
        for z in np.arange(z0, z1, 0.5):
            px, py = self.P(ccx, ccy, z)
            _blit(c, side_spr, int(round(px - w / 2)), int(round(py - h / 2)))
        px, py = self.P(ccx, ccy, z1)
        _blit(c, top_img, int(round(px - w / 2)), int(round(py - h / 2)))
        return int(round(px - w / 2)), int(round(py - h / 2))

    @staticmethod
    def dashed(c, a, b, col, on=6, off=1):
        for i, (x, y) in enumerate(curve_points([a, b])):
            if i % (on + off) < on and 0 <= x < c.w and 0 <= y < c.h:
                c.a[y, x] = col


def _blit(c, spr, x, y):
    c.blit(spr, x, y)
