"""Car-domain props shared across episodes: the ECU robot and the cloth-covered next-episode teaser object."""
import math
from functools import lru_cache
from PIL import Image, ImageDraw
from .grid import Grid, outline
from .sprites import _flake


@lru_cache(None)
def robot(blink=False, signal=0):
    """Friendly ECU robot: chip body with pins, screen face, antenna light (signal 0-2 lights the waves). 30x32."""
    g = Grid(30, 32)
    g.rect(14, 1, 15, 5, '#7b8491'); g.disc(14.5, 2, 2, '#e0303a' if signal == 0 else '#3cc85a'); g.px(14, 1, '#ff9aa0')
    g.rect(5, 6, 24, 19, '#d3d8e0'); g.rect(4, 7, 25, 18, '#d3d8e0'); g.rect(20, 7, 25, 18, '#a9b0bb')
    g.rect(7, 9, 22, 16, '#1a1a2e')
    for ex in (10, 17):
        if blink: g.rect(ex, 12, ex + 2, 12, '#3cc85a')
        else: g.rect(ex, 11, ex + 2, 13, '#3cc85a'); g.px(ex, 11, '#a6f5b8')
    g.rect(12, 15, 17, 15, '#3cc85a')
    g.rect(1, 10, 3, 14, '#a9b0bb'); g.rect(26, 10, 28, 14, '#a9b0bb')
    g.rect(4, 20, 25, 30, '#2b2d33'); g.rect(5, 21, 24, 21, '#5d636e')
    for y in (22, 25, 28):
        g.rect(1, y, 3, y, '#d3d8e0'); g.rect(26, y, 28, y, '#d3d8e0')
    g.text(7, 23, 'ECU', '#ffd23f')
    return g.image()


@lru_cache(64)
def sheet(lift=0.0):
    """Something under a dust sheet (60x42). lift 0..1 raises the right corner, revealing a dark gap and a glint."""
    W, H = 60, 42
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    cloth, fold, hi = (150, 154, 164), (112, 116, 126), (196, 200, 210)
    rise = int(round(16 * lift))
    hem = [(2 + i * 4, 40 - (2 if i % 2 else 0) - (max(0, i - 9) * rise // 5)) for i in range(15)]
    top = [(56, 40 - rise * 2), (57, 24 - rise), (52, 12), (44, 6), (34, 3), (22, 4), (12, 9), (6, 18), (3, 30), (2, 40)]
    if rise:   # what is underneath: dark shape with a metallic glint
        d.polygon([(36, 40), (36, 30), (56, 28), (57, 40)], fill=(24, 25, 30))
        d.ellipse((42, 31, 52, 40), fill=(60, 63, 72)); d.ellipse((45, 33, 49, 37), fill=(150, 156, 168))
        d.point((44, 32), fill=(255, 255, 255)); d.point((46, 34), fill=(230, 236, 246))
    d.polygon(hem + top, fill=cloth)
    for x0, y0, x1, y1 in ((20, 6, 16, 38), (32, 4, 30, 39), (44, 8, 47, 38 - rise)):
        d.line((x0, y0, x1, y1), fill=fold)
    d.line([(12, 9), (22, 4), (34, 3), (44, 6), (52, 12)], fill=hi)
    d.line([(8, 14), (10, 11)], fill=hi)
    return outline(img)
