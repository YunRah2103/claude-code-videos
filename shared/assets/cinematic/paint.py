"""Soft-shading helpers on top of stickman.vec (gradients, glows, soft blur) for the cinematic look.

    gfill(P, pts, c0, c1, a, b)      # linear gradient c0 at local point a -> c1 at b, clipped to polygon pts
    glow(P, c, r, col, k=1.0)        # additive-looking radial glow (cached sprite)
    soft(img, r)                     # cheap large gaussian blur (downscale, blur, upscale)
"""
from functools import lru_cache
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from stickman.vec import SS


def gfill(P, pts, c0, c1, a, b):
    q = [P.p(t) for t in pts]
    W2, H2 = P.L.img.size
    x0, y0 = max(0, int(min(x for x, _ in q)) - 1), max(0, int(min(y for _, y in q)) - 1)
    x1, y1 = min(W2, int(max(x for x, _ in q)) + 2), min(H2, int(max(y for _, y in q)) + 2)
    if x1 <= x0 or y1 <= y0: return
    m = Image.new('L', (x1 - x0, y1 - y0), 0)
    ImageDraw.Draw(m).polygon([(x - x0, y - y0) for x, y in q], fill=255)
    A, B = P.p(a), P.p(b); dx, dy = B[0] - A[0], B[1] - A[1]; L2 = dx * dx + dy * dy or 1.0
    xs = np.arange(x0, x1, dtype=np.float32)[None, :]; ys = np.arange(y0, y1, dtype=np.float32)[:, None]
    k = np.clip(((xs - A[0]) * dx + (ys - A[1]) * dy) / L2, 0, 1)[..., None]
    c0 = np.array(c0 if len(c0) == 4 else tuple(c0) + (255,), np.float32)
    c1 = np.array(c1 if len(c1) == 4 else tuple(c1) + (255,), np.float32)
    col = c0 + (c1 - c0) * k
    col[..., 3] *= np.asarray(m, np.float32) / 255
    P.L.img.alpha_composite(Image.fromarray(col.astype(np.uint8), 'RGBA'), (x0, y0))


@lru_cache(64)
def _glow(r2, col):
    n = int(r2 * 2) + 2
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    d = np.sqrt((xx - n / 2) ** 2 + (yy - n / 2) ** 2) / r2
    a = np.clip(1 - d, 0, 1) ** 2.2
    out = np.zeros((n, n, 4), np.float32); out[..., :3] = col[:3]; out[..., 3] = a * col[3]
    return Image.fromarray(out.astype(np.uint8), 'RGBA')


def glow(P, c, r, col, k=1.0):
    if k <= 0.01: return
    r2 = max(2, int(r * P.s * SS))
    g = _glow(r2, (col[0], col[1], col[2], int(min(255, 255 * k))))
    x, y = P.p(c)
    comp(P.L.img, g, int(x - g.width / 2), int(y - g.height / 2))


def comp(base, im, x, y):
    """alpha_composite that accepts offsets partly outside the base image."""
    cx0, cy0 = max(0, -x), max(0, -y)
    cx1, cy1 = min(im.width, base.width - x), min(im.height, base.height - y)
    if cx1 <= cx0 or cy1 <= cy0: return
    base.alpha_composite(im.crop((cx0, cy0, cx1, cy1)), (x + cx0, y + cy0))


def soft(img, r):
    if r <= 0.3: return img
    w, h = img.size; f = 4 if r > 6 else 2
    s = img.resize((max(1, w // f), max(1, h // f)), Image.BILINEAR).filter(ImageFilter.GaussianBlur(r / f))
    return s.resize((w, h), Image.BILINEAR)
