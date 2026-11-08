"""Filmic finish for 1080x1920 frames: teal/navy shadows + warm highlights grade, soft bloom, vignette, fine grain.

    img = finish(rgb_image, n=frame_index, bloom=0.55, grain=3.0)     # deterministic grain per frame index
"""
from functools import lru_cache
import numpy as np
from PIL import Image, ImageFilter

LUM = np.array([0.299, 0.587, 0.114], np.float32)


@lru_cache(2)
def _vig(w, h, k=0.42):
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.sqrt(((xx - w / 2) / (w * 0.62)) ** 2 + ((yy - h * 0.47) / (h * 0.62)) ** 2)
    return (1 - k * np.clip(d - 0.45, 0, 1) ** 1.6)[..., None]


@lru_cache(4)
def _grain(seed, w, h):
    g = np.random.default_rng(seed).normal(0, 1, (h // 2, w // 2)).astype(np.float32)
    return np.asarray(Image.fromarray(g).resize((w, h), Image.BILINEAR), np.float32)[..., None]


def grade(a):
    l = (a @ LUM)[..., None]
    sh = (1 - l) ** 2
    a = a + sh * np.array([-0.025, 0.012, 0.05], np.float32) + (l ** 2) * np.array([0.045, 0.012, -0.03], np.float32)
    a = 0.5 + (a - 0.5) * 1.06                                                  # gentle contrast
    l2 = (a @ LUM)[..., None]
    return l2 + (a - l2) * 1.08                                                 # slight saturation


def finish(img, n=0, bloom=0.55, grain=3.0, vig=True):
    w, h = img.size
    a = np.asarray(img.convert('RGB'), np.float32) / 255
    a = grade(a)
    if bloom > 0:
        small = img.resize((w // 6, h // 6), Image.BILINEAR)
        s = np.asarray(small, np.float32) / 255
        s = np.clip((s @ LUM)[..., None] - 0.62, 0, 1) / 0.38 * s
        b = Image.fromarray((np.clip(s, 0, 1) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(9)).resize((w, h), Image.BILINEAR)
        a = a + bloom * np.asarray(b, np.float32) / 255
    if vig: a = a * _vig(w, h)
    if grain: a = a + _grain(n % 4, w, h) * (grain / 255)
    return Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8), 'RGB')
