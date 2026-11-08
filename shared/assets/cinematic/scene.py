"""Dusk proving ground in depth layers + a parallax/zoom camera.

    cam = Cam(sx=scroll_px, z=zoom, fx=focus_x, fy=focus_y, dy=0)   # sx: camera travel along the track (ground px)
    bg = backdrop(cam, dof=1.0)          # RGB 1080x1920: sky, far hills/city, floodlights, track (blurred by depth)
    fg = foreground(cam, dof=1.0)        # RGBA: blurred near posts/cones, composite after the car
    cam.ground(X, Y)                     # world point on the car plane -> screen px; cam.scale(s) -> s * zoom
Layer depths (parallax): sky 0.04, far 0.18, mid 0.5, track 1.0, foreground 1.7. Zoom per layer = z ** depth.
"""
import math, random
from dataclasses import dataclass
from functools import lru_cache
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from stickman.vec import Layer, hexc, shade, mix, SS
from .paint import glow

W, H = 1080, 1920
HY = 1200            # horizon (zoom 1)
GY = 1700            # car ground line (zoom 1)


@dataclass
class Cam:
    sx: float = 0.0
    z: float = 1.0
    fx: float = 540.0
    fy: float = 1500.0
    dy: float = 0.0
    shake: tuple = (0.0, 0.0)

    def ground(self, X, Y):
        return (self.fx + (X - self.sx - self.fx) * self.z + self.shake[0], self.fy + (Y + self.dy - self.fy) * self.z + self.shake[1])

    def scale(self, s): return s * self.z


def _vgrad(h, stops, w=W):
    ys = np.arange(h, dtype=np.float32)
    pos = [p for p, _ in stops]; cols = np.array([c[:3] for _, c in stops], np.float32)
    out = np.stack([np.interp(ys, pos, cols[:, k]) for k in range(3)], -1)
    return np.repeat(out[:, None, :], w, 1)


@lru_cache(1)
def sky():
    a = _vgrad(H, [(0, hexc('#09122a')), (420, hexc('#132a4a')), (760, hexc('#1f4a63')), (980, hexc('#7a6b6e')),
                   (1100, hexc('#e3874c')), (1200, hexc('#ffb469')), (1260, hexc('#f39a58'))])
    img = Image.fromarray(a.astype(np.uint8), 'RGB').convert('RGBA')
    L = Layer(W, H); P = L.pen(); rnd = random.Random(4)
    glow(P, (760, 1190), 520, (255, 170, 90), 0.55)                          # sun glow
    glow(P, (760, 1200), 150, (255, 230, 180), 0.9)
    for _ in range(90):                                                       # stars
        x, y = rnd.uniform(0, W), rnd.uniform(0, 620) ** 1.0
        P.circle((x, y), rnd.uniform(0.8, 2.0), (255, 255, 255, int(rnd.uniform(60, 200) * (1 - y / 700))), ow=0)
    img.alpha_composite(L.done())
    # soft clouds lit from the horizon
    cl = Layer(W, H); Q = cl.pen()
    for cx, cy, rx, ry in ((180, 820, 300, 34), (700, 700, 380, 40), (980, 900, 260, 26), (420, 980, 340, 22), (60, 560, 220, 22), (860, 480, 260, 20)):
        Q.ellipse((cx, cy), rx, ry, (44, 62, 92, 210), ow=0)
        Q.ellipse((cx + 20, cy + ry * 0.45), rx * 0.86, ry * 0.5, (245, 160, 110, 150 if cy > 650 else 70), ow=0)
    img.alpha_composite(cl.done().filter(ImageFilter.GaussianBlur(10)))
    return img.convert('RGB')


@lru_cache(8)
def _far(blur):
    w, y0, h = 3200, 960, 360
    L = Layer(w, h); P = L.pen(0, -y0); rnd = random.Random(7)
    hills = [(0, HY + 10)] + [(x, HY - 70 - 50 * math.sin(x / 260) - 30 * math.sin(x / 97 + 1)) for x in range(0, w + 1, 40)] + [(w, HY + 10)]
    P.fillpoly(hills, hexc('#24435a'))
    for k in range(0, w, 1600):                                                # city skyline, repeats every 1600
        x = k + 200
        for i in range(26):
            bw, bh = rnd.uniform(30, 70), rnd.uniform(40, 170)
            P.fillpoly([(x, HY + 5), (x, HY - bh), (x + bw, HY - bh), (x + bw, HY + 5)], hexc('#1c3448'))
            for _ in range(int(bh / 16)):
                wx, wy = x + rnd.uniform(5, bw - 6), HY - rnd.uniform(8, bh - 8)
                P.fillpoly([(wx, wy), (wx + 4, wy), (wx + 4, wy + 5), (wx, wy + 5)], (255, 196, 120, int(rnd.uniform(120, 255))))
            x += bw + rnd.uniform(4, 30)
        P.line([(k + 1250, HY), (k + 1250, HY - 300)], 4, hexc('#1c3448'))
        P.circle((k + 1250, HY - 300), 5, (255, 70, 60, 255), ow=0)
    P.fillpoly([(0, HY - 60), (w, HY - 60), (w, HY + 20), (0, HY + 20)], (255, 170, 110, 60))      # haze
    img = L.done()
    return (img.filter(ImageFilter.GaussianBlur(blur)) if blur else img), y0, 1600


@lru_cache(8)
def _mid(blur):
    w, y0, h = 2800, 560, 800
    L = Layer(w, h); P = L.pen(0, -y0)
    P.fillpoly([(0, HY + 30), (0, HY - 40), (w, HY - 40), (w, HY + 30)], hexc('#18283a'))          # far track edge / stands base
    for k in range(0, w, 1400):
        P.fillpoly([(k + 520, HY - 40), (k + 560, HY - 120), (k + 980, HY - 120), (k + 1020, HY - 40)], hexc('#1a2d40'))   # grandstand
        for i in range(8): P.line([(k + 580 + i * 52, HY - 110), (k + 580 + i * 52, HY - 50)], 3, hexc('#253f57'))
        for tx in (k + 230, k + 700, k + 1180):                                  # floodlight towers
            P.line([(tx, HY + 20), (tx, 760)], 9, hexc('#14202e'))
            P.fillpoly([(tx - 46, 735), (tx + 46, 735), (tx + 40, 772), (tx - 40, 772)], hexc('#1d2a39'))
            for i in range(4): P.circle((tx - 30 + i * 20, 754), 7, (255, 236, 196, 255), ow=0)
            glow(P, (tx, 756), 120, (255, 200, 130), 0.75)
            P.fillpoly([(tx - 40, 772), (tx + 40, 772), (tx + 260, HY + 40), (tx - 260, HY + 40)], (255, 206, 150, 26))
    for x in range(0, w, 70): P.line([(x, HY + 28), (x, HY - 8)], 3, hexc('#0f1824'))           # fence posts
    P.line([(0, HY - 4), (w, HY - 4)], 3, hexc('#0f1824'), cap=False)
    img = L.done()
    return (img.filter(ImageFilter.GaussianBlur(blur)) if blur else img), y0, 1400


@lru_cache(8)
def _track(blur):
    w, y0 = 2400, HY + 20; h = H - y0 + 300
    a = _vgrad(h, [(0, hexc('#3a3f4a')), (120, hexc('#2c3440')), (520, hexc('#1f2732')), (h, hexc('#141a22'))], w)
    img = Image.fromarray(a.astype(np.uint8), 'RGB').convert('RGBA')
    L = Layer(w, h); P = L.pen(0, -y0)
    for k in range(0, w, 1200):
        for tx in (k + 230,):
            glow(P, (tx + 120, HY + 230), 520, (255, 170, 100), 0.30)         # floodlight pools on the asphalt
        for i in range(0, 1200, 120):                                         # red/white kerb on the far edge
            P.fillpoly([(k + i, HY + 40), (k + i + 60, HY + 40), (k + i + 56, HY + 60), (k + i - 4, HY + 60)], hexc('#d6453d'))
            P.fillpoly([(k + i + 60, HY + 40), (k + i + 120, HY + 40), (k + i + 116, HY + 60), (k + i + 56, HY + 60)], hexc('#e8e4dc'))
        for i in range(0, 1200, 200):                                          # lane dashes
            P.fillpoly([(k + i + 30, GY + 92), (k + i + 150, GY + 92), (k + i + 146, GY + 112), (k + i + 26, GY + 112)], (240, 236, 226, 235))
        for i in range(0, 1200, 400):                                           # skid marks
            P.line([(k + i + 90, GY + 40), (k + i + 380, GY + 52)], 10, (12, 14, 20, 90))
    P.fillpoly([(0, HY + 60), (w, HY + 60), (w, HY + 66), (0, HY + 66)], (255, 200, 150, 60))
    img.alpha_composite(L.done())
    return (img.filter(ImageFilter.GaussianBlur(blur)) if blur else img), y0, 1200


@lru_cache(4)
def _fore(blur):
    w, y0, h = 3600, 1500, 520
    L = Layer(w, h); P = L.pen(0, -y0); rnd = random.Random(11)
    for k in range(0, w, 1800):
        for x in (k + 150, k + 520, k + 900, k + 1220, k + 1560):
            P.fillpoly([(x - 40, 1920), (x - 12, 1690), (x + 12, 1690), (x + 40, 1920)], hexc('#ff7a2e'))      # traffic cone
            P.fillpoly([(x - 26, 1800), (x + 26, 1800), (x + 30, 1830), (x - 30, 1830)], (240, 240, 240, 255))
        for _ in range(14):
            x = k + rnd.uniform(0, 1800)
            P.fillpoly([(x, 1920), (x + rnd.uniform(-20, 20), 1920 - rnd.uniform(60, 150)), (x + 24, 1920)], hexc('#101a14'))
    img = L.done()
    return img.filter(ImageFilter.GaussianBlur(blur)), y0, 1800


def _place(out, layer, depth, cam):
    img, y0, period = layer
    zl = cam.z ** depth
    c = cam.fx - cam.fx / zl + (cam.sx * depth) % period - cam.shake[0] * depth / zl
    f = cam.fy - cam.fy / zl - y0 - (cam.dy + cam.shake[1]) * depth / zl
    t = img.transform((W, H), Image.AFFINE, (1 / zl, 0, c, 0, 1 / zl, f), Image.BILINEAR)
    out.alpha_composite(t)


def backdrop(cam, dof=1.0):
    """dof scales depth-of-field blur (1 = car in focus at normal framing)."""
    zl = cam.z ** 0.04
    s = sky()
    out = s.transform((W, H), Image.AFFINE, (1 / zl, 0, cam.fx - cam.fx / zl + cam.sx * 0.04 % 40, 0, 1 / zl, cam.fy - cam.fy / zl - cam.dy * 0.04), Image.BILINEAR).convert('RGBA')
    _place(out, _far(int(round(3 * dof))), 0.18, cam)
    _place(out, _mid(int(round(2.5 * dof))), 0.5, cam)
    _place(out, _track(int(round(1.2 * max(0, dof - 1) * 3))), 1.0, cam)
    return out


def foreground(cam, dof=1.0):
    out = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    _place(out, _fore(int(10 + 4 * dof)), 1.7, cam)
    return out
