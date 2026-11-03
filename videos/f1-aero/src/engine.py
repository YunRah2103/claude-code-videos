"""Lit isometric pixel engine for the F1 explainer: shaded boxes with edge highlights,
dioramas, smoke trails, colour grading. Canvas 216x384 (x5 -> 1080x1920)."""
import importlib.util, math
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter

_p = Path(__file__).resolve().parents[2] / 'style-reel' / 'src' / 'render.py'
_s = importlib.util.spec_from_file_location('style_reel', _p); sr = importlib.util.module_from_spec(_s); _s.loader.exec_module(sr)
C, col, hr, BAYER = sr.C, sr.col, sr.hr, sr.BAYER

W, H, SC = 216, 384, 5


def canvas(): return C(w=W, h=H)


def lerp(a, b, u): return a + (b - a) * u


def ease(u): u = min(1.0, max(0.0, u)); return u * u * (3 - 2 * u)


class Light:
    def __init__(s, top=1.06, left=.80, right=.60, tint=(1, 1, 1), edge=1.22):
        s.top, s.left, s.right, s.tint, s.edge = top, left, right, np.array(tint, np.float32), edge


class Iso:
    """X runs to the lower right, Y to the lower left, Z up. Visible faces: top, Y+ (left), X+ (right)."""
    def __init__(s, c, ox, oy, k, light=None):
        s.c, s.ox, s.oy, s.k, s.L = c, ox, oy, k, light or Light()
        s.items = []
    def p(s, X, Y, Z=0.0): return (s.ox + (X - Y) * s.k, s.oy + ((X + Y) / 2 - Z) * s.k)
    def poly(s, pts, cl): return s.c.poly([s.p(*q) for q in pts], cl)
    def line(s, a, b, cl):
        x0, y0 = s.p(*a); x1, y1 = s.p(*b); s.c.line(x0, y0, x1, y1, cl)
    def lit(s, base, face):
        m = {'top': s.L.top, 'left': s.L.left, 'right': s.L.right}[face]
        return np.clip(col(base) * m * s.L.tint, 0, 255)
    def box(s, X, Y, Z, dx, dy, dz, mat, edges=True, faces=None):
        tp, lf, rt = faces or (s.lit(mat, 'top'), s.lit(mat, 'left'), s.lit(mat, 'right'))
        s.poly([(X, Y + dy, Z), (X + dx, Y + dy, Z), (X + dx, Y + dy, Z + dz), (X, Y + dy, Z + dz)], lf)
        s.poly([(X + dx, Y, Z), (X + dx, Y + dy, Z), (X + dx, Y + dy, Z + dz), (X + dx, Y, Z + dz)], rt)
        s.poly([(X, Y, Z + dz), (X + dx, Y, Z + dz), (X + dx, Y + dy, Z + dz), (X, Y + dy, Z + dz)], tp)
        if edges and min(dx, dy) * s.k > 2.2:
            e = np.clip(np.asarray(tp) * s.L.edge + 10, 0, 255)
            s.line((X, Y + dy, Z + dz), (X + dx, Y + dy, Z + dz), e)
            s.line((X + dx, Y, Z + dz), (X + dx, Y + dy, Z + dz), e)
            if dz * s.k > 3: s.line((X + dx, Y + dy, Z), (X + dx, Y + dy, Z + dz), np.clip(np.asarray(lf) * 1.12, 0, 255))
    def qx(s, X, Y0, Y1, Z0, Z1, cl): return s.poly([(X, Y0, Z0), (X, Y1, Z0), (X, Y1, Z1), (X, Y0, Z1)], cl)
    def qy(s, X0, X1, Y, Z0, Z1, cl): return s.poly([(X0, Y, Z0), (X1, Y, Z0), (X1, Y, Z1), (X0, Y, Z1)], cl)
    def qz(s, X0, X1, Y0, Y1, Z, cl): return s.poly([(X0, Y0, Z), (X1, Y0, Z), (X1, Y1, Z), (X0, Y1, Z)], cl)
    def circle_x(s, X, Yc, Zc, r, cl, n=18):     # disc in the X = const plane
        return s.poly([(X, Yc + r * math.cos(a), Zc + r * math.sin(a)) for a in np.linspace(0, 6.283, n)], cl)
    def circle_y(s, Xc, Y, Zc, r, cl, n=18):     # disc in the Y = const plane
        return s.poly([(Xc + r * math.cos(a), Y, Zc + r * math.sin(a)) for a in np.linspace(0, 6.283, n)], cl)
    def shadow(s, pts, k=.55, soft=True):
        L = C(layer=True, w=W, h=H); L.poly([s.p(*q) for q in pts], '#000000')
        m = L.m
        if soft:
            d = sr.dilate(m) & ~m
            s.c.a[d & (BAYER[s.c.ys % 4, s.c.xs % 4] > .5)] *= (1 + k) / 2
        s.c.a[m] *= k
    def glow(s, X, Y, Z, r, cl, k=.6, ry=None, steps=4): s.c.glow(*s.p(X, Y, Z), r, cl, k, ry, steps)
    def ground(s, fn, mask=None):
        u = (s.c.xs - s.ox) / s.k; v = 2 * (s.c.ys - s.oy) / s.k
        a = fn((u + v) / 2, (v - u) / 2) * s.L.top * s.L.tint
        if mask is None: s.c.a[:] = a
        else: s.c.a[mask] = a[mask]
    def add(s, depth, fn): s.items.append((depth, fn))
    def draw(s):
        for _, fn in sorted(s.items, key=lambda q: q[0]): fn()
        s.items = []


def tex(X, Y, a, b, n):
    return ((np.floor(X / n) + np.floor(Y / n)) % 2).astype(bool)[..., None] * (col(a) - col(b)) + col(b)


def noise_tex(X, Y, base, amt=10, seed=1):
    h = ((np.floor(X * 1.7) * 73856093).astype(np.int64) ^ (np.floor(Y * 1.7) * 19349663).astype(np.int64) ^ seed) % 997 / 997
    return col(base) + (h[..., None] - .5) * amt


def diorama(I, X0, Y0, X1, Y1, depth, ground_fn, strata=('#5aa040', '#7a5a3a', '#6a4a30', '#58402c', '#4a4a52')):
    """Floating slab: lit top via ground_fn, layered soil sides."""
    c = I.c
    for i, cl in enumerate(strata):
        z1 = 0 if i == 0 else -depth * (.08 + (i - 1) * .3); z0 = -depth * (.08 + i * .3) if i < len(strata) - 1 else -depth
        if i == 0: z0 = -depth * .08
        I.poly([(X0, Y1, z0), (X1, Y1, z0), (X1, Y1, z1), (X0, Y1, z1)], I.lit(cl, 'left'))
        I.poly([(X1, Y0, z0), (X1, Y1, z0), (X1, Y1, z1), (X1, Y0, z1)], I.lit(cl, 'right'))
    for k in range(40):                                       # pebbles in the soil
        u = hr(k, 7); z = -depth * (.15 + .8 * hr(k, 8))
        if k % 2: x_, y_ = I.p(X0 + u * (X1 - X0), Y1, z)
        else: x_, y_ = I.p(X1, Y0 + u * (Y1 - Y0), z)
        c.px(x_, y_, I.lit('#8a7a68', 'left' if k % 2 else 'right'))
    L = C(layer=True, w=W, h=H)
    L.poly([I.p(X0, Y0), I.p(X1, Y0), I.p(X1, Y1), I.p(X0, Y1)], '#000000')
    I.ground(ground_fn, L.m)
    I.line((X0, Y1, 0), (X1, Y1, 0), np.clip(c.a[int(I.p(X0 + 1, Y1 - 1)[1]) % H, int(I.p(X0 + 1, Y1 - 1)[0]) % W] * 1.25 + 8, 0, 255))
    I.line((X1, Y0, 0), (X1, Y1, 0), np.clip(c.a[int(I.p(X1 - 1, Y0 + 1)[1]) % H, int(I.p(X1 - 1, Y0 + 1)[0]) % W] * 1.25 + 8, 0, 255))
    return L.m


def backdrop(c, cols, t, motes='#ffffff', n=40):
    c.grad(0, H, cols)
    for i in range(n):
        ph = (t * (.02 + hr(i, 5) * .03) + hr(i, 6)) % 1
        x = (hr(i, 3) * W + math.sin(t * .5 + i) * 6) % W; y = H - ph * (H + 20)
        if hr(i, 9) > .5: c.px(x, y, col(motes) * .5 + c.a[int(y) % H, int(x)] * .5)


def blend(c, x, y, cl, a):
    x, y = int(round(x)), int(round(y))
    if 0 <= x < W and 0 <= y < H and a > 0: c.a[y, x] = c.a[y, x] * (1 - a) + col(cl) * a


def grade(a, top=(1, 1, 1), bottom=(1, 1, 1), vignette=.35, bloom=.35):
    """Colour grade + vignette + bloom on the small canvas."""
    ys = np.linspace(0, 1, H)[:, None, None]
    a = a * (np.array(top) * (1 - ys) + np.array(bottom) * ys)
    yy, xx = np.mgrid[0:H, 0:W]
    v = 1 - vignette * (((xx - W / 2) / (W * .62)) ** 2 + ((yy - H / 2) / (H * .62)) ** 2)
    a = a * np.clip(v, 0, 1)[..., None]
    if bloom:
        br = np.clip(a - 175, 0, 255)
        im = Image.fromarray(br.astype(np.uint8)).filter(ImageFilter.GaussianBlur(4))
        a = a + np.asarray(im).astype(np.float32) * bloom
    return np.clip(a, 0, 255)
