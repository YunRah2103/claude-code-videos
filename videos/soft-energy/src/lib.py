"""Tiny pixel-art toolkit: crisp shapes at native resolution, effects in numpy."""
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter


def hx(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def mix(a, b, t):
    a, b = hx(a) if isinstance(a, str) else a, hx(b) if isinstance(b, str) else b
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


class Canvas:
    def __init__(s, w, h, bg='#000000'):
        s.w, s.h = w, h
        s.im = Image.new('RGB', (w, h), hx(bg) if isinstance(bg, str) else bg)
        s.d = ImageDraw.Draw(s.im)

    @staticmethod
    def c(col):
        return hx(col) if isinstance(col, str) else tuple(int(v) for v in col)

    def px(s, x, y, col):
        if 0 <= x < s.w and 0 <= y < s.h:
            s.im.putpixel((int(x), int(y)), s.c(col))

    def rect(s, x0, y0, x1, y1, col):
        if x1 < x0 or y1 < y0:
            return
        s.d.rectangle([x0, y0, x1, y1], fill=s.c(col))

    def box(s, x0, y0, x1, y1, col):
        s.d.rectangle([x0, y0, x1, y1], outline=s.c(col))

    def line(s, x0, y0, x1, y1, col):
        s.d.line([(x0, y0), (x1, y1)], fill=s.c(col))

    def poly(s, pts, col, outline=None):
        s.d.polygon(pts, fill=s.c(col) if col else None,
                    outline=s.c(outline) if outline else None)

    def ellipse(s, x0, y0, x1, y1, col=None, outline=None):
        s.d.ellipse([x0, y0, x1, y1], fill=s.c(col) if col else None,
                    outline=s.c(outline) if outline else None)

    def circle(s, cx, cy, r, col=None, outline=None):
        s.ellipse(cx - r, cy - r, cx + r, cy + r, col, outline)

    def arr(s):
        return np.asarray(s.im).astype(np.float32)

    def paste(s, other, x=0, y=0, mask=None):
        s.im.paste(other.im if isinstance(other, Canvas) else other, (x, y), mask)

    def copy(s):
        c = Canvas(s.w, s.h)
        c.im = s.im.copy()
        c.d = ImageDraw.Draw(c.im)
        return c


def glyph(c, x, y, rows, col, scale=1):
    """Draw a bitmap given as list of strings ('#' = on)."""
    for j, r in enumerate(rows):
        for i, ch in enumerate(r):
            if ch not in ' .':
                c.rect(x + i * scale, y + j * scale, x + i * scale + scale - 1,
                       y + j * scale + scale - 1, col)


def vgrad(c, x0, y0, x1, y1, top, bot, dither=True):
    """Vertical gradient using ordered dithering between banded colours."""
    a = np.asarray(c.im).copy()
    t, b = np.array(hx(top) if isinstance(top, str) else top, float), \
        np.array(hx(bot) if isinstance(bot, str) else bot, float)
    bayer = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) / 16.0
    for y in range(y0, y1 + 1):
        f = (y - y0) / max(1, (y1 - y0))
        for x in range(x0, x1 + 1):
            ff = f
            if dither:
                ff = min(1, max(0, f + (bayer[y % 4, x % 4] - 0.5) / 6))
                ff = round(ff * 6) / 6
            a[y, x] = t + (b - t) * ff
    c.im = Image.fromarray(a.astype(np.uint8))
    c.d = ImageDraw.Draw(c.im)


def upscale(arr, k):
    return np.repeat(np.repeat(arr, k, axis=0), k, axis=1)


def bloom(img, thresh=150, radius=6, gain=0.55):
    """img float32 HxWx3 0..255 -> soft glow around bright/saturated pixels."""
    lum = img.max(axis=2)
    m = np.clip((lum - thresh) / (255 - thresh), 0, 1)[..., None]
    src = Image.fromarray(np.clip(img * m, 0, 255).astype(np.uint8))
    g = np.asarray(src.filter(ImageFilter.GaussianBlur(radius))).astype(np.float32)
    g2 = np.asarray(src.filter(ImageFilter.GaussianBlur(radius * 3))).astype(np.float32)
    return np.clip(img + g * gain + g2 * gain * 0.6, 0, 255)


def vignette(h, w, strength=0.35):
    y, x = np.mgrid[0:h, 0:w]
    d = np.sqrt(((x - w / 2) / (w / 2)) ** 2 + ((y - h / 2) / (h / 2)) ** 2)
    return (1 - strength * np.clip(d - 0.55, 0, 1) ** 1.5)[..., None].astype(np.float32)


class Rain:
    """Deterministic falling streaks at native resolution."""

    def __init__(s, w, h, n, seed, lmin=4, lmax=12, speed=(220, 320), x_slant=0.0):
        r = np.random.default_rng(seed)
        s.w, s.h = w, h
        s.x = r.uniform(0, w, n)
        s.y0 = r.uniform(-h, h, n)
        s.l = r.integers(lmin, lmax + 1, n)
        s.v = r.uniform(*speed, n)
        s.br = r.uniform(0.35, 1.0, n)
        s.slant = x_slant

    def draw(s, a, t, col, alpha=0.7, ymax=None):
        ymax = s.h if ymax is None else ymax
        col = np.array(hx(col) if isinstance(col, str) else col, np.float32)
        span = s.h + 40
        for x, y0, l, v, br in zip(s.x, s.y0, s.l, s.v, s.br):
            y = (y0 + v * t) % span - 20
            xi = int(x + s.slant * y) % s.w
            for k in range(int(l)):
                yy = int(y) + k
                if 0 <= yy < ymax:
                    f = alpha * br * (0.45 + 0.55 * k / max(1, l - 1))
                    a[yy, xi] = a[yy, xi] * (1 - f) + col * f
