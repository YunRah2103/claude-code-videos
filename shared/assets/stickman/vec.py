"""Flat-vector drawing on a 2x supersampled RGBA layer (PIL only): thick dark outlines, round-capped limbs, soft shadows.

    L = Layer(W, H)                      # 2x canvas, transparent
    P = L.pen(ox, oy, s)                 # world -> screen: (x, y) -> (ox + x*s, oy + y*s), in 1x pixels
    P.poly(pts, fill, ow=6)              # outlined polygon (ow in 1x px)
    P.limb(a, b, w, fill, ow=5)          # capsule with dark outline
    P.circle(c, r, fill, ow=5)
    img = L.done()                       # 1x RGBA, box-filtered (anti-aliased)
"""
import math
from functools import lru_cache
from PIL import Image, ImageDraw, ImageFilter

INK = (34, 36, 44)          # outline colour used everywhere
SS = 2                      # supersampling factor


def hexc(h, a=255):
    h = h.lstrip('#'); return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), a)


def mix(c1, c2, k):
    return tuple(int(round(c1[i] + (c2[i] - c1[i]) * k)) for i in range(len(c1)))


def shade(c, k):            # k<0 darker, k>0 lighter
    return mix(c, (0, 0, 0, c[3] if len(c) > 3 else 255) if k < 0 else (255, 255, 255, c[3] if len(c) > 3 else 255), abs(k))


class Pen:
    def __init__(self, layer, ox, oy, s, rot=0.0, piv=(0, 0), kx=1.0, ky=1.0):
        self.L, self.d, self.ox, self.oy, self.s = layer, layer.d, ox, oy, s
        self.rot, self.piv, self.kx, self.ky = rot, piv, kx, ky       # kx/ky: squash & stretch about the local origin

    def sub(self, ox, oy, s):           # nested transform (local frame placed at world ox, oy, scaled by s)
        X, Y = self.p((ox, oy))
        return Pen(self.L, X / SS, Y / SS, self.s * s, self.rot, (0, 0))

    def p(self, pt):
        x, y = pt
        if self.rot:
            c, sn = math.cos(self.rot), math.sin(self.rot)
            x, y = x - self.piv[0], y - self.piv[1]
            x, y = x * c - y * sn + self.piv[0], x * sn + y * c + self.piv[1]
        return ((self.ox + x * self.kx * self.s) * SS, (self.oy + y * self.ky * self.s) * SS)

    def _blend(self, q, pad, fn):
        """PIL overwrites (does not blend) translucent ink on RGBA images: draw on a temp tile and composite it."""
        x0 = int(min(a for a, _ in q) - pad); y0 = int(min(b for _, b in q) - pad)
        x1 = int(max(a for a, _ in q) + pad) + 1; y1 = int(max(b for _, b in q) + pad) + 1
        W2, H2 = self.L.img.size
        x0, y0, x1, y1 = max(0, x0), max(0, y0), min(W2, x1), min(H2, y1)
        if x1 <= x0 or y1 <= y0: return
        tile = Image.new('RGBA', (x1 - x0, y1 - y0), (0, 0, 0, 0))
        fn(ImageDraw.Draw(tile), [(a - x0, b - y0) for a, b in q])
        self.L.img.alpha_composite(tile, (x0, y0))

    def poly(self, pts, fill, ow=6, oc=INK):
        q = [self.p(t) for t in pts]
        if ow:
            self.d.line(q + [q[0], q[1]], fill=oc, width=int(ow * 2 * SS), joint='curve')
            for t in q: self._dot(t, ow * SS, oc)
        self.d.polygon(q, fill=fill)

    def fillpoly(self, pts, fill):
        q = [self.p(t) for t in pts]
        if len(fill) == 4 and fill[3] < 255: self._blend(q, 2, lambda d, r: d.polygon(r, fill=fill))
        else: self.d.polygon(q, fill=fill)

    def _dot(self, q, r, col):
        self.d.ellipse((q[0] - r, q[1] - r, q[0] + r, q[1] + r), fill=col)

    def line(self, pts, w, col, cap=True):      # w in 1x px (not scaled)
        q = [self.p(t) for t in pts]
        if len(col) == 4 and col[3] < 255:
            def fn(d, r):
                d.line(r, fill=col, width=max(1, int(w * SS)), joint='curve')
                if cap:
                    for t in (r[0], r[-1]): d.ellipse((t[0] - w * SS / 2, t[1] - w * SS / 2, t[0] + w * SS / 2, t[1] + w * SS / 2), fill=col)
            return self._blend(q, w * SS, fn)
        self.d.line(q, fill=col, width=max(1, int(w * SS)), joint='curve')
        if cap:
            for t in (q[0], q[-1]): self._dot(t, w * SS / 2, col)

    def limb(self, pts, w, fill, ow=5, oc=INK):  # thick round-capped polyline with outline; w in world units
        ww = w * self.s
        q = [self.p(t) for t in pts]
        if ow:
            self.d.line(q, fill=oc, width=int((ww + 2 * ow) * SS), joint='curve')
            for t in q: self._dot(t, (ww / 2 + ow) * SS, oc)
        self.d.line(q, fill=fill, width=int(ww * SS), joint='curve')
        for t in q: self._dot(t, ww / 2 * SS, fill)

    def circle(self, c, r, fill, ow=5, oc=INK):
        self.ellipse(c, r, r, fill, ow, oc)

    def ellipse(self, c, rx, ry, fill, ow=0, oc=INK):
        x, y = self.p(c); X, Y = rx * self.s * SS, ry * self.s * SS; o = ow * SS
        if ow: self.d.ellipse((x - X - o, y - Y - o, x + X + o, y + Y + o), fill=oc)
        if len(fill) == 4 and fill[3] < 255:
            return self._blend([(x - X, y - Y), (x + X, y + Y)], 1, lambda d, q: d.ellipse((q[0][0], q[0][1], q[1][0], q[1][1]), fill=fill))
        self.d.ellipse((x - X, y - Y, x + X, y + Y), fill=fill)

    def arc(self, c, r, a0, a1, w, col):        # degrees, PIL convention (clockwise from +x)
        x, y = self.p(c); R = r * self.s * SS
        if len(col) == 4 and col[3] < 255:
            return self._blend([(x - R, y - R), (x + R, y + R)], 2, lambda d, q: d.arc((q[0][0], q[0][1], q[1][0], q[1][1]), a0, a1, fill=col, width=int(w * SS)))
        self.d.arc((x - R, y - R, x + R, y + R), a0, a1, fill=col, width=int(w * SS))

    def rrect(self, box, rad, fill, ow=5, oc=INK):
        x0, y0 = self.p(box[:2]); x1, y1 = self.p(box[2:])
        if fill is not None and len(fill) == 4 and fill[3] < 255:
            self._blend([(x0, y0), (x1, y1)], ow * SS + 1, lambda d, q: d.rounded_rectangle((q[0][0], q[0][1], q[1][0], q[1][1]), rad * self.s * SS, fill=fill))
            fill = None
        self.d.rounded_rectangle((x0, y0, x1, y1), rad * self.s * SS, fill=fill, outline=oc if ow else None, width=int(ow * SS))

    def text(self, xy, s, font, fill, anchor='mm', stroke=0, sc=INK):
        x, y = self.p(xy)
        self.d.text((x, y), s, font=font, fill=fill, anchor=anchor, stroke_width=stroke * SS, stroke_fill=sc)

    def paste(self, img, xy, anchor='mm'):        # img is a 2x RGBA sprite
        x, y = self.p(xy)
        if anchor == 'mm': x, y = x - img.width / 2, y - img.height / 2
        self.L.img.alpha_composite(img, (int(x), int(y)))


class Layer:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.img = Image.new('RGBA', (w * SS, h * SS), (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.img, 'RGBA')

    def pen(self, ox=0, oy=0, s=1.0, rot=0.0, piv=(0, 0), kx=1.0, ky=1.0):
        return Pen(self, ox, oy, s, rot, piv, kx, ky)

    def done(self):
        return self.img.reduce(SS)


@lru_cache(64)
def soft_ellipse(rx, ry, alpha=90, blur=0.35):
    """2x sprite of a soft contact shadow (dark ellipse, gaussian edge)."""
    pad = int(max(rx, ry) * blur * 2) + 4
    im = Image.new('RGBA', (int(2 * rx + 2 * pad) * SS, int(2 * ry + 2 * pad) * SS), (0, 0, 0, 0))
    ImageDraw.Draw(im).ellipse((pad * SS, pad * SS, (pad + 2 * rx) * SS, (pad + 2 * ry) * SS), fill=(20, 22, 30, alpha))
    return im.filter(ImageFilter.GaussianBlur(max(1, ry * blur * SS)))


def rot(pt, a, c=(0, 0)):
    x, y = pt[0] - c[0], pt[1] - c[1]; cs, sn = math.cos(a), math.sin(a)
    return (c[0] + x * cs - y * sn, c[1] + x * sn + y * cs)


def arcpts(c, r, a0, a1, n=12):                    # radians, y down
    return [(c[0] + r * math.cos(a0 + (a1 - a0) * i / n), c[1] + r * math.sin(a0 + (a1 - a0) * i / n)) for i in range(n + 1)]


def bez(p0, p1, p2, n=16):
    return [((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0],
             (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]) for t in (i / n for i in range(n + 1))]
