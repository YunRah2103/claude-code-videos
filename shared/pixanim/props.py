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


@lru_cache(None)
def charger(glow=0.0, screen=0):
    """Fast-charging post (24x50): tall cabinet, lit screen (`screen` 0..3 bars), holster, cable coiled down the side.
    glow 0..1 lights the side strip. No lettering or logos."""
    img = Image.new('RGBA', (24, 50), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    body, shade, hi = (226, 230, 238), (176, 182, 194), (248, 250, 252)
    d.rectangle((3, 49, 20, 49), fill=(60, 63, 72))                                   # plinth
    d.rounded_rectangle((4, 2, 19, 48), 3, fill=body)
    d.rectangle((15, 4, 18, 47), fill=shade); d.line([(5, 4), (5, 46)], fill=hi)
    g = int(80 + 175 * glow)
    d.rectangle((4, 10, 5, 40), fill=(40, min(255, 120 + g // 2), min(255, 60 + g // 3)))  # status strip
    d.rectangle((7, 7, 15, 15), fill=(26, 26, 46))                                     # screen
    for k in range(screen): d.rectangle((9, 13 - k * 2, 13, 13 - k * 2), fill=(90, 220, 120))
    d.rectangle((8, 20, 14, 28), fill=(60, 63, 72)); d.rectangle((9, 21, 13, 23), fill=(26, 26, 46))  # holster
    d.arc((14, 26, 24, 44), 270, 90, fill=(26, 27, 32), width=2)                       # cable loop
    return outline(img)


@lru_cache(None)
def plug():
    """Charging plug head (12x8) with a short cable stub on the left."""
    img = Image.new('RGBA', (12, 8), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rectangle((0, 3, 3, 4), fill=(26, 27, 32))
    d.rounded_rectangle((3, 0, 10, 7), 2, fill=(60, 63, 72)); d.rectangle((10, 2, 11, 5), fill=(176, 182, 194))
    d.point((5, 1), fill=(150, 156, 170))
    return outline(img)


@lru_cache(None)
def bolt(col=(255, 217, 59)):
    """Lightning bolt (10x16)."""
    img = Image.new('RGBA', (10, 16), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.polygon([(6, 0), (0, 9), (4, 9), (2, 15), (9, 5), (5, 5), (7, 0)], fill=col)
    d.line([(6, 1), (2, 8)], fill=(255, 250, 220))
    return outline(img)


@lru_cache(None)
def stopwatch(frac=0.0):
    """Pixel stopwatch (34x40): crown, two buttons, white dial, red hand at `frac` of a turn."""
    img = Image.new('RGBA', (34, 40), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rectangle((14, 0, 19, 4), fill=(200, 204, 214)); d.rectangle((12, 4, 21, 6), fill=(150, 156, 170))
    d.rectangle((3, 6, 7, 9), fill=(150, 156, 170)); d.rectangle((26, 6, 30, 9), fill=(150, 156, 170))
    d.ellipse((0, 6, 33, 39), fill=(150, 156, 170)); d.ellipse((2, 8, 31, 37), fill=(248, 248, 244))
    for k in range(12):
        a = math.radians(k * 30)
        d.point((16.5 + 12 * math.sin(a), 22.5 - 12 * math.cos(a)), fill=(26, 26, 46))
    a = math.radians(frac * 360)
    d.line([(16.5, 22.5), (16.5 + 11 * math.sin(a), 22.5 - 11 * math.cos(a))], fill=(224, 48, 58), width=2)
    d.ellipse((15, 21, 18, 24), fill=(26, 26, 46))
    d.arc((4, 10, 29, 35), 200, 260, fill=(255, 255, 255))
    return outline(img)
