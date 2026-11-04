"""Low-res pixel-art compositing kit: dithered gradients, layers, bloom, rain, wet reflections."""
import numpy as np
from PIL import Image, ImageDraw

W, H = 360, 640          # native pixel canvas (upscaled 3x nearest -> 1080x1920)

B4 = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) / 16.0


def bayer(h, w, ox=0, oy=0):
    t = np.tile(B4, (h // 4 + 2, w // 4 + 2))
    return t[oy % 4:oy % 4 + h, ox % 4:ox % 4 + w]


def dither(img, step=10, ox=0):
    b = bayer(img.shape[0], img.shape[1], ox)[..., None]
    return np.clip(np.floor(img / step + b) * step, 0, 255)


def grad(h, w, stops, step=9):
    ys = np.linspace(0, 1, h)
    cols = np.stack([np.interp(ys, [s[0] for s in stops], [s[1][k] for s in stops]) for k in range(3)], -1)
    return dither(np.repeat(cols[:, None, :], w, 1), step)


def smooth(a, b, x):
    x = np.clip((x - a) / (b - a), 0, 1)
    return x * x * (3 - 2 * x)


class Lay:
    """PIL drawing surface with a parallel emissive (glow) plane."""

    def __init__(s, w, h):
        s.w, s.h = w, h
        s.im = Image.new('RGBA', (w, h), (0, 0, 0, 0)); s.d = ImageDraw.Draw(s.im)
        s.em = Image.new('RGB', (w, h), (0, 0, 0)); s.de = ImageDraw.Draw(s.em)

    def _c(s, c):
        return tuple(int(v) for v in c) + ((255,) if len(c) == 3 else ())

    def rect(s, x0, y0, x1, y1, c, glow=None):
        if x1 < x0 or y1 < y0: return
        s.d.rectangle([x0, y0, x1, y1], fill=s._c(c))
        if glow is not None: s.de.rectangle([x0, y0, x1, y1], fill=tuple(int(v) for v in glow))

    def poly(s, pts, c, glow=None):
        s.d.polygon([tuple(p) for p in pts], fill=s._c(c))
        if glow is not None: s.de.polygon([tuple(p) for p in pts], fill=tuple(int(v) for v in glow))

    def line(s, pts, c, width=1, glow=None):
        s.d.line([tuple(p) for p in pts], fill=s._c(c), width=width)
        if glow is not None: s.de.line([tuple(p) for p in pts], fill=tuple(int(v) for v in glow), width=width)

    def ellipse(s, x0, y0, x1, y1, c, glow=None, outline=None):
        s.d.ellipse([x0, y0, x1, y1], fill=s._c(c) if c is not None else None,
                    outline=s._c(outline) if outline is not None else None)
        if glow is not None:
            s.de.ellipse([x0, y0, x1, y1], fill=tuple(int(v) for v in glow) if c is not None else None,
                         outline=tuple(int(v) for v in glow) if outline is not None else None)

    def px(s, x, y, c, glow=None):
        if 0 <= x < s.w and 0 <= y < s.h:
            s.im.putpixel((int(x), int(y)), s._c(c))
            if glow is not None: s.em.putpixel((int(x), int(y)), tuple(int(v) for v in glow))

    def done(s):
        a = np.asarray(s.im, float)
        return dict(rgb=a[..., :3].copy(), a=a[..., 3] / 255.0, e=np.asarray(s.em, float).copy())


def blit(F, E, L, x, y, alpha=1.0, ek=1.0, add_e=True):
    x, y = int(round(x)), int(round(y)); h, w = L['a'].shape
    x0, y0, x1, y1 = max(x, 0), max(y, 0), min(x + w, F.shape[1]), min(y + h, F.shape[0])
    if x0 >= x1 or y0 >= y1: return
    sl = (slice(y0 - y, y1 - y), slice(x0 - x, x1 - x))
    a = L['a'][sl][..., None] * alpha
    F[y0:y1, x0:x1] = F[y0:y1, x0:x1] * (1 - a) + L['rgb'][sl] * a
    if E is not None:
        E[y0:y1, x0:x1] *= (1 - a)
        if add_e and L.get('e') is not None:
            E[y0:y1, x0:x1] += L['e'][sl] * a * ek


def blit_tile(F, E, L, off, y, ek=1.0):
    w = L['a'].shape[1]
    x = -(int(round(off)) % w)
    while x < F.shape[1]:
        blit(F, E, L, x, y, ek=ek); x += w


def box(img, r):
    if r <= 0: return img
    for ax in (0, 1):
        pad = [(r + 1, r) if i == ax else (0, 0) for i in range(img.ndim)]
        c = np.cumsum(np.pad(img, pad, mode='edge'), axis=ax)
        n = c.shape[ax]
        img = (np.take(c, range(2 * r + 1, n), axis=ax) - np.take(c, range(0, n - 2 * r - 1), axis=ax)) / (2 * r + 1)
    return img


def bloom(F, E, k=1.0):
    g = box(E, 2) * 0.55 + box(box(E, 6), 5) * 0.55 + box(box(E, 16), 12) * 0.35
    return F + g * k


def finish(F, step=5):
    return dither(np.clip(F, 0, 255), step).astype(np.uint8)


def reflect(F, E, yG, t, dark=0.42, tint=(4, 10, 22), stretch=0.72, wob=1.0, band=0.25, y_end=None):
    """Mirror everything above yG into the wet ground below it, with ripples."""
    y_end = F.shape[0] if y_end is None else y_end
    n = y_end - yG
    if n <= 0: return
    i = np.arange(n)
    rows = np.clip(yG - 1 - (i * stretch).astype(int), 0, F.shape[0] - 1)
    sh = (np.sin(i * 0.85 + t * 6.0) * wob * (0.6 + 2.2 * i / n) + np.sin(i * 2.3 - t * 9) * 0.6 * wob).astype(int)
    cols = np.clip(np.arange(F.shape[1])[None, :] + sh[:, None], 0, F.shape[1] - 1)
    ripple = (1 - band) + band * (0.5 + 0.5 * np.sin(i * 1.7 + t * 4.0 + np.sin(i * 0.31) * 3))
    fall = (1 - 0.55 * i / n) * ripple
    src = F[rows[:, None], cols]
    F[yG:y_end] = src * dark * fall[:, None, None] + np.array(tint, float)
    E[yG:y_end] = E[rows[:, None], cols] * 0.55 * fall[:, None, None]


class Rain:
    def __init__(s, n, seed, speed=(260, 380), length=(5, 10), slant=0.12, col=(150, 190, 230), alpha=(0.25, 0.6)):
        r = np.random.default_rng(seed)
        s.x0 = r.uniform(0, W, n); s.y0 = r.uniform(0, H, n)
        s.v = r.uniform(*speed, n); s.L = r.integers(length[0], length[1] + 1, n)
        s.a = r.uniform(*alpha, n); s.slant = slant; s.col = np.array(col, float)

    def draw(s, F, t, ymax=H, E=None):
        y = (s.y0 + s.v * t) % (H + 20) - 20
        x = (s.x0 + s.slant * (s.v * t)) % W
        Lm = s.L.max()
        k = np.arange(Lm)
        yy = (y[:, None] + k[None, :]).astype(int)
        xx = (x[:, None] + s.slant * k[None, :]).astype(int) % W
        ok = (k[None, :] < s.L[:, None]) & (yy >= 0) & (yy < ymax)
        a = (s.a[:, None] * np.ones_like(yy, float))[ok][:, None]
        yy, xx = yy[ok], xx[ok]
        F[yy, xx] = F[yy, xx] * (1 - a) + s.col * a
        if E is not None: E[yy, xx] *= (1 - a * 0.5)


def splashes(F, t, y0, y1, n=14, seed=0, col=(140, 180, 220)):
    fr = int(t * 30)
    r = np.random.default_rng(seed * 100003 + fr)
    for _ in range(n):
        x = int(r.uniform(2, W - 3)); y = int(r.uniform(y0, y1))
        a = r.uniform(0.25, 0.6)
        w = 1 if r.random() < 0.5 else 2
        F[y, x - w:x + w + 1] = F[y, x - w:x + w + 1] * (1 - a) + np.array(col) * a


GLYPHS = {}
FONT5 = {
    '9': ['01110', '10001', '10001', '01111', '00001', '00010', '01100'],
    '1': ['00100', '01100', '00100', '00100', '00100', '00100', '01110'],
    '2': ['01110', '10001', '00001', '00010', '00100', '01000', '11111'],
    '0': ['01110', '10011', '10101', '10101', '10101', '11001', '01110'],
    '7': ['11111', '00001', '00010', '00100', '01000', '01000', '01000'],
    '4': ['00010', '00110', '01010', '10010', '11111', '00010', '00010'],
    'C': ['01111', '10000', '10000', '10000', '10000', '10000', '01111'],
    'A': ['01110', '10001', '10001', '11111', '10001', '10001', '10001'],
    'R': ['11110', '10001', '10001', '11110', '10100', '10010', '10001'],
    'E': ['11111', '10000', '10000', '11110', '10000', '10000', '11111'],
    'S': ['01111', '10000', '10000', '01110', '00001', '00001', '11110'],
    'P': ['11110', '10001', '10001', '11110', '10000', '10000', '10000'],
    'O': ['01110', '10001', '10001', '10001', '10001', '10001', '01110'],
    'H': ['10001', '10001', '10001', '11111', '10001', '10001', '10001'],
    'N': ['10001', '11001', '10101', '10011', '10001', '10001', '10001'],
    'M': ['10001', '11011', '10101', '10101', '10001', '10001', '10001'],
    'I': ['11111', '00100', '00100', '00100', '00100', '00100', '11111'],
    'G': ['01111', '10000', '10000', '10011', '10001', '10001', '01111'],
    'T': ['11111', '00100', '00100', '00100', '00100', '00100', '00100'],
    'Y': ['10001', '10001', '01010', '00100', '00100', '00100', '00100'],
    'K': ['10001', '10010', '10100', '11000', '10100', '10010', '10001'],
    'U': ['10001', '10001', '10001', '10001', '10001', '10001', '01110'],
    'L': ['10000', '10000', '10000', '10000', '10000', '10000', '11111'],
    'D': ['11110', '10001', '10001', '10001', '10001', '10001', '11110'],
    '-': ['00000', '00000', '00000', '11111', '00000', '00000', '00000'],
    '/': ['00001', '00010', '00010', '00100', '01000', '01000', '10000'],
    '.': ['00000', '00000', '00000', '00000', '00000', '01100', '01100'],
    ' ': ['00000'] * 7,
}


def text(lay, s, x, y, c, glow=None, sc=1, gap=1):
    for ch in s:
        g = FONT5.get(ch, FONT5[' '])
        for j, row in enumerate(g):
            for i, b in enumerate(row):
                if b == '1':
                    lay.rect(x + i * sc, y + j * sc, x + i * sc + sc - 1, y + j * sc + sc - 1, c, glow)
        x += (5 + gap) * sc
    return x


def text_w(s, sc=1, gap=1): return len(s) * (5 + gap) * sc - gap * sc


def alien(lay, x, y, n, c, glow=None, seed=0, sz=3):
    """Pseudo-script glyphs like the shop signs in the reference."""
    r = np.random.default_rng(seed)
    for k in range(n):
        g = r.random((sz, sz)) < 0.55
        g[:, 0] |= r.random() < 0.5; g[0, :] |= r.random() < 0.4
        for j in range(sz):
            for i in range(sz):
                if g[j, i]: lay.rect(x + i, y + j, x + i, y + j, c, glow)
        x += sz + 1
    return x
