"""Sprites for the grass-nap loop: lying main guy, car buddy, props. Native pixel scale."""
import sys
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'new-car-trap/src'))
import pix  # noqa: E402
from pix import Grid, hexc, OX  # noqa: E402

pix.POSES['sprawl'] = (((4, 1), (9, -3)), ((4, 2), (9, 4)))   # relaxed, arms flopped out


# ---------------------------------------------------------------- rotation (RotSprite-style)

def _scale2x(a):
    """EPX/Scale2x on an HxWx4 uint8 array (keeps pixel-art edges clean when rotated)."""
    h, w, _ = a.shape
    p = np.pad(a, ((1, 1), (1, 1), (0, 0)), mode='edge')
    E = p[1:-1, 1:-1]; B = p[:-2, 1:-1]; H = p[2:, 1:-1]; D = p[1:-1, :-2]; F = p[1:-1, 2:]
    eq = lambda x, y: np.all(x == y, axis=2)
    c = (~eq(B, H) & ~eq(D, F))[..., None]
    out = np.empty((h * 2, w * 2, 4), np.uint8)
    out[0::2, 0::2] = np.where(c & eq(D, B)[..., None], D, E)
    out[0::2, 1::2] = np.where(c & eq(B, F)[..., None], F, E)
    out[1::2, 0::2] = np.where(c & eq(D, H)[..., None], D, E)
    out[1::2, 1::2] = np.where(c & eq(H, F)[..., None], F, E)
    return out


def rotsprite(img, deg):
    a = np.array(img.convert('RGBA'))
    a = np.pad(a, ((12, 12), (12, 12), (0, 0)))
    for _ in range(3):
        a = _scale2x(a)
    big = Image.fromarray(a).rotate(deg, resample=Image.NEAREST, expand=True)
    w, h = big.size
    small = big.resize((w // 8, h // 8), Image.NEAREST, reducing_gap=None)
    # sample pixel centres explicitly (nearest resize may sample corners)
    b = np.array(big)
    ys = np.arange(h // 8) * 8 + 4; xs = np.arange(w // 8) * 8 + 4
    s = b[ys][:, xs]
    s[s[..., 3] < 128] = 0
    s[..., 3] = np.where(s[..., 3] > 0, 255, 0)
    img = Image.fromarray(s)
    return img.crop(img.getbbox())


# ---------------------------------------------------------------- guy with headphones, eyes shut

HP, HPS, HPH = '#3b3f55', '#262838', '#6b7190'
CUP, CUPH = '#e04a5a', '#ff8a8f'


@lru_cache(None)
def guy_lying(deg=-38):
    img = pix.guy('blink', pose='sprawl').copy()
    g = Grid(img.width, img.height)
    for y in range(img.height):
        for x in range(img.width):
            c = img.getpixel((x, y))
            if c[3]:
                g.g[y][x] = c
    o = OX
    # headband over the hair
    for x in range(8, 28):
        y = 4 if 11 <= x <= 24 else (5 if 9 <= x <= 26 else 6)
        g.px(x + o, y, HP); g.px(x + o, y + 1, HPS)
    for x in range(12, 23):
        g.px(x + o, 4, HPH)
    for y in range(6, 13):
        g.px(7 + o, y, HP); g.px(28 + o, y, HP)
    # ear cups
    for sx in (5, 27):
        g.rect(sx + o, 12, sx + 3 + o, 20, CUP)
        g.rect(sx + o, 12, sx + 3 + o, 12, CUPH)
        g.rect(sx + o + (0 if sx < 10 else 3), 13, sx + o + (0 if sx < 10 else 3), 19, '#b73446')
        g.rect(sx + 1 + o, 14, sx + 2 + o, 18, '#8e2735')
    out = g.image(outline=True)
    return rotsprite(out, deg)


# ---------------------------------------------------------------- car buddy (sleeping bubble car, front view)

CB = {'body': '#f5b934', 'sh': '#d98b22', 'hi': '#ffe48c', 'deep': '#b4661b',
      'glass': '#8fd3e8', 'glasssh': '#5aa7c4', 'glasshi': '#e6fbff',
      'chrome': '#d7dce4', 'chromesh': '#8f97a6', 'tire': '#2a2a33', 'tirehi': '#4a4b57',
      'hub': '#b9c0cc', 'lid': '#5a2c1c', 'blush': '#ff8f6b', 'mouth': '#5a2c1c',
      'stripe': '#fff3d6', 'light': '#fffbe8'}


def _blob(g, cx, cy, rx, ry, c, pred=None):
    for y in range(int(cy - ry) - 1, int(cy + ry) + 2):
        for x in range(int(cx - rx) - 1, int(cx + rx) + 2):
            if ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1.0 and (pred is None or pred(x, y)):
                g.px(x, y, c)


@lru_cache(None)
def car_buddy(deg=18, snore=0):
    C = CB
    g = Grid(60, 56)
    # tires (limbs): front tires stick out at the sides, rear tires at the bottom
    for (x0, y0, x1, y1) in ((2, 26, 9, 37), (50, 26, 57, 37), (13, 44, 22, 53), (37, 44, 46, 53)):
        g.rect(x0, y0, x1, y1, C['tire'])
        g.rect(x0 + 1, y0 + 1, x1 - 1, y0 + 1, C['tirehi'])
        for yy in range(y0 + 3, y1, 3):
            g.px(x0, yy, C['tirehi']); g.px(x1, yy, C['tirehi'])
        mx, my = (x0 + x1) // 2, (y0 + y1) // 2
        g.rect(mx - 1, my - 1, mx + 1, my + 1, C['hub'])
        g.px(mx, my, C['chrome'])
    # chubby body
    _blob(g, 29.5, 31, 22, 18, C['body'])
    _blob(g, 29.5, 33, 22, 16, C['body'])
    _blob(g, 29.5, 40, 21, 9, C['sh'], lambda x, y: y >= 40)
    _blob(g, 29.5, 22, 15, 6, C['hi'], lambda x, y: y <= 19)
    # roof / cabin
    _blob(g, 29.5, 13, 14, 10, C['body'], lambda x, y: y <= 19)
    _blob(g, 29.5, 10, 10, 6, C['hi'], lambda x, y: y <= 7)
    # windshield = forehead visor
    for y in range(9, 19):
        half = 8 + (y - 9) // 2
        g.rect(int(29.5 - half) + 1, y, int(29.5 + half), y, C['glass'])
    g.rect(22, 16, 37, 18, C['glasssh'])
    for i in range(4):
        g.px(23 + i, 12 - i // 2, C['glasshi'])
    g.px(33, 11, C['glasshi']); g.px(34, 11, C['glasshi'])
    g.rect(19, 19, 40, 19, C['chromesh'])
    # mirrors = little ears
    for x0 in (10, 45):
        g.rect(x0, 15, x0 + 4, 19, C['body']); g.rect(x0, 15, x0 + 4, 15, C['hi'])
        g.rect(x0 + 1, 16, x0 + 3, 18, C['glass'])
    # racing stripes over the hood
    g.rect(26, 20, 27, 27, C['stripe']); g.rect(32, 20, 33, 27, C['stripe'])
    # headlight eyes, closed (sleepy lids)
    for cx in (17, 42):
        g.disc(cx, 27, 4.6, C['chromesh'])
        g.disc(cx, 27, 3.6, C['chrome'])
        g.disc(cx, 27, 2.7, C['light'])
        for x in range(cx - 4, cx + 5):
            for y in range(22, 27):
                if (x - cx) ** 2 + (y - 27) ** 2 <= 22:
                    g.px(x, y, C['body'])
        for x in range(cx - 3, cx + 4):
            g.px(x, 27 if abs(x - cx) < 2 else 26, C['lid'])
        g.px(cx - 4, 25, C['lid']); g.px(cx + 4, 25, C['lid'])
    # cheeks
    g.rect(10, 32, 12, 33, C['blush']); g.rect(47, 32, 49, 33, C['blush'])
    # grille smile + bumper chin
    g.rect(24, 33, 35, 33, C['mouth'])
    g.px(23, 32, C['mouth']); g.px(36, 32, C['mouth'])
    if snore:
        g.rect(26, 34, 33, 35, '#3a1a12'); g.rect(25, 34, 25, 34, C['mouth']); g.rect(34, 34, 34, 34, C['mouth'])
    else:
        for x in range(25, 35, 2):
            g.px(x, 34, C['deep'])
    g.rect(13, 40, 46, 42, C['chrome']); g.rect(13, 42, 46, 42, C['chromesh'])
    g.rect(15, 40, 19, 40, '#ffffff')
    g.rect(26, 40, 33, 41, '#f7f2df')                       # plate
    g.px(28, 41, C['chromesh']); g.px(30, 41, C['chromesh']); g.px(32, 41, C['chromesh'])
    # fog lights
    g.rect(15, 37, 17, 38, '#ffd56b'); g.rect(42, 37, 44, 38, '#ffd56b')
    # little antenna
    for i in range(6):
        g.px(46 + i // 2, 8 - i, C['chromesh'])
    g.disc(49.5, 2, 1.2, '#e04a5a')
    return rotsprite(g.image(outline=True), deg)


# ---------------------------------------------------------------- props

@lru_cache(None)
def helmet(deg=-14):
    """Side-view racing helmet lying on the grass (replaces the backpack)."""
    g = Grid(32, 28)
    _blob(g, 16, 15, 14, 12, '#f4f5f8', lambda x, y: y <= 24)
    g.rect(4, 21, 27, 24, '#f4f5f8')
    _blob(g, 13, 10, 8, 6, '#ffffff', lambda x, y: y <= 11)
    _blob(g, 16, 15, 14, 12, '#d3d7e0', lambda x, y: y >= 20 and y <= 24)
    for y in range(3, 25):                       # red + yellow racing stripes over the dome
        for x in range(1, 31):
            if g.g[y][x] is not None and 0 <= (x - 0.55 * y) - 6 < 3:
                g.px(x, y, '#e8384a')
            elif g.g[y][x] is not None and 3 <= (x - 0.55 * y) - 6 < 4:
                g.px(x, y, '#ffd23f')
    g.rect(17, 11, 29, 18, '#1e2335'); g.rect(17, 11, 29, 11, '#3a4466')    # visor opening
    g.rect(19, 13, 24, 13, '#7f93c9'); g.px(19, 14, '#4a5a8f')
    g.rect(27, 19, 30, 23, '#c9ced8')                                         # chin bar
    g.rect(4, 24, 27, 25, '#2a2d3a')                                          # padded rim
    g.rect(9, 14, 11, 16, '#c9ced8')                                          # visor pivot
    return rotsprite(g.image(outline=True), deg)


@lru_cache(None)
def walkman(phase=0, glow=1.0):
    """Cassette player lying on the grass (replaces the console). phase: spool frame."""
    g = Grid(26, 34)
    g.rect(1, 1, 24, 32, '#3d6f8f'); g.rect(1, 1, 24, 2, '#5d93b5'); g.rect(23, 3, 24, 32, '#2c5470')
    g.rect(1, 31, 24, 32, '#2c5470')
    # LCD (glows; colour set later from `glow`)
    k = max(0.0, min(1.0, glow))
    lcd = tuple(int(a + (b - a) * k) for a, b in zip((58, 110, 108), (140, 255, 240)))
    g.rect(4, 4, 21, 10, '#1d3346'); g.rect(5, 5, 20, 9, '#%02x%02x%02x' % lcd)
    if k > 0.4:
        for i, hgt in enumerate((2, 4, 3, 1, 4, 2, 3)):
            hgt = max(1, (hgt + phase) % 4 + 1)
            g.rect(7 + i * 2, 9 - hgt, 7 + i * 2, 9, '#1d6f6a')
    # cassette window with spools
    g.rect(4, 13, 21, 23, '#1a2230'); g.rect(5, 14, 20, 22, '#c9d3dc'); g.rect(7, 16, 18, 20, '#5a4038')
    ring = ((0, -2), (1, -2), (2, -1), (2, 0), (2, 1), (1, 2), (0, 2), (-1, 2), (-2, 1), (-2, 0), (-2, -1), (-1, -2))
    for cx in (9, 16):
        for i, (dx, dy) in enumerate(ring):
            g.px(cx + dx, 18 + dy, '#f2f4f7')
        g.px(cx, 18, '#f2f4f7')
        for k in (0, 6):
            dx, dy = ring[(k + phase * 2) % 12]
            g.px(cx + dx, 18 + dy, '#1a2230')
    # buttons
    for i, c in enumerate(('#ff6b6b', '#ffd36b', '#d9dde6', '#d9dde6')):
        g.rect(4 + i * 5, 26, 7 + i * 5, 29, c); g.rect(4 + i * 5, 29, 7 + i * 5, 29, '#8f97a6')
    g.rect(24, 6, 25, 9, '#c9d3dc')                         # jack
    return g.image(outline=True)


@lru_cache(None)
def magazine(page=0):
    """Open car magazine, top-down. page 0..5 = flip stages (0 flat)."""
    g = Grid(34, 22)
    g.rect(1, 4, 32, 20, '#e9edf2'); g.rect(16, 4, 17, 20, '#b9c1cc')
    g.rect(1, 20, 32, 20, '#9aa4b2')
    # left page: tiny car photo + text
    g.rect(3, 6, 14, 12, '#3d7fd6'); g.rect(4, 10, 13, 11, '#e8343f'); g.rect(5, 9, 11, 9, '#e8343f')
    g.px(6, 12, '#26272e'); g.px(11, 12, '#26272e')
    for y in (14, 16, 18):
        g.rect(3, y, 14 - (y == 18) * 4, y, '#8a94a6')
    # right page: text + gauge
    for y in (6, 8, 10):
        g.rect(19, y, 30, y, '#8a94a6')
    g.disc(24.5, 15.5, 3.4, '#ffd23f'); g.rect(24, 15, 27, 15, '#e8343f')
    # flipping page
    if page:
        ws = {1: 12, 2: 7, 3: 2, 4: 7, 5: 12}[page]
        top = {1: 2, 2: 0, 3: 0, 4: 0, 5: 2}[page]
        if page < 3:
            x0, x1 = 18, 18 + ws
        elif page == 3:
            x0, x1 = 16, 17
        else:
            x0, x1 = 16 - ws, 15
        g.rect(x0, top, x1, 19 - (page != 3) * 1, '#ffffff')
        g.rect(x0, top, x1, top, '#cdd4de')
    return g.image(outline=True)
