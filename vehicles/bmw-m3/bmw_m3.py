"""BMW M3 (E90 sedan) pixel sprite, side view facing left, 96x35 grid.

Traced from a side-on E90 M3 photo: long hood, front fender gill, Hofmeister kink,
trunk lip spoiler, wraparound tail light, quad pipes and mesh wheels.
Import:  sys.path.insert(0, 'vehicles/bmw-m3'); import bmw_m3; bmw_m3.sprite('blue', phase)
Export:  python bmw_m3.py <outdir>   (writes 1x, 8x and preview PNGs for every colour)
"""
import math, sys
from functools import lru_cache
from PIL import Image

W, H = 96, 35
OUT = (26, 26, 46, 255)
WHEELS, WY = (14, 77), 26  # wheel centres
COLORS = {                 # body, shade, highlight
    'blue':     ('#1f5fd1', '#163f94', '#6fa3ff'),
    'silver':   ('#a7abb3', '#7d828c', '#d9dce2'),
    'black':    ('#2b2d33', '#16171b', '#5d636e'),
    'red':      ('#c8102e', '#8f0b20', '#ff5a6e'),
    'green':    ('#0f6b4a', '#0a4c35', '#3fa57c'),
    'broken':   ('#a8585c', '#844246', '#c47a7d'),
}
GLASS, GLASS_HI, DARK, TRIM = '#bfe3f5', '#ffffff', '#16171b', '#2b2d33'


def rgba(h):
    h = h.lstrip('#'); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)) + (255,)


class Grid:
    def __init__(self):
        self.g = [[None] * W for _ in range(H)]

    def px(self, x, y, c):
        if 0 <= x < W and 0 <= y < H: self.g[y][x] = rgba(c) if c else None

    def rect(self, x0, y0, x1, y1, c):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1): self.px(x, y, c)

    def disc(self, cx, cy, r, c, ymax=99):
        for y in range(int(cy - r) - 1, min(int(cy + r) + 2, ymax + 1)):
            for x in range(int(cx - r) - 1, int(cx + r) + 2):
                if (x - cx) ** 2 + (y - cy) ** 2 <= r * r + 0.5: self.px(x, y, c)

    def image(self):
        src, g = self.g, [row[:] for row in self.g]
        for y in range(H):
            for x in range(W):
                if src[y][x] is None and any(0 <= x + dx < W and 0 <= y + dy < H and src[y + dy][x + dx]
                                             for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                    g[y][x] = OUT
        img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        img.putdata([c or (0, 0, 0, 0) for row in g for c in row])
        return img


@lru_cache(None)
def sprite(color='blue', phase=0):
    """phase 0/1 rotates the mesh wheels for a two-frame spin."""
    body, shade, hi = COLORS[color]
    g = Grid()
    # greenhouse: raked windscreen, C-pillar into the trunk
    xl = lambda y: round(40 - (y - 3) * 1.2)
    xr = lambda y: round(70 + (y - 3) * 1.2)
    for y in range(3, 14):
        g.rect(xl(y), y, xr(y), y, body)
    g.rect(xl(3), 3, xr(3), 3, hi)
    for y in range(4, 14):
        g.rect(xl(y) + 1, y, xr(y) - 1, y, DARK)                # black window trim
    for y in range(5, 13):
        g.rect(xl(y) + 3, y, 51, y, GLASS)                      # front door glass
        g.rect(55, y, 66, y, GLASS)                             # rear door glass
        g.rect(68, y, xr(y) - 3 - max(0, y - 9) * 2, y, GLASS)  # quarter glass, Hofmeister kink
    g.px(xl(5) + 4, 5, GLASS_HI); g.px(xl(6) + 4, 6, GLASS_HI); g.px(57, 5, GLASS_HI); g.px(58, 5, GLASS_HI)
    # body: hood slopes to the nose, trunk sits a little higher than the beltline
    def top(x):
        if x < 28: return round(18 - (x - 2) * 5 / 26)
        if x < 80: return 13
        return round(13 - (x - 80) * 2 / 12)
    for x in range(0, 96):
        y0 = max(top(x), 11)
        y1 = 27 if x < 10 or x > 85 else 28
        if x == 0: y0, y1 = 20, 25
        if x == 1: y0, y1 = 19, 26
        g.rect(x, y0, x, y1, body)
        g.px(x, y0, hi)
    g.rect(92, 10, 95, 10, shade); g.rect(93, 11, 95, 11, shade)  # trunk lip spoiler
    g.rect(6, 15, 92, 15, hi)                                     # shoulder crease
    g.rect(2, 24, 94, 25, shade)
    g.rect(22, 27, 69, 28, DARK)                                  # side skirt
    g.rect(0, 26, 10, 27, DARK); g.rect(1, 23, 6, 25, DARK)       # front lip and intake
    g.rect(0, 20, 1, 22, DARK)                                    # kidney grille edge
    g.rect(2, 18, 8, 19, '#eef7ff'); g.rect(3, 19, 4, 19, '#9fd8ff')  # headlight + angel eye
    g.rect(22, 18, 26, 18, DARK); g.px(23, 17, '#d3d8e0')         # fender gill
    for x in (28, 52, 75):
        g.rect(x, 14, x, 26, shade)                               # door shut lines
    g.rect(45, 16, 49, 16, hi); g.rect(66, 16, 70, 16, hi)        # door handles
    g.rect(33, 11, 36, 13, body); g.rect(33, 11, 36, 11, hi)      # mirror
    g.rect(89, 12, 95, 16, '#d0202c'); g.rect(90, 12, 93, 12, '#ff5a66'); g.rect(89, 16, 95, 16, '#8f0b20')  # tail light
    g.rect(86, 26, 95, 27, DARK)                                  # rear diffuser
    for x in (87, 90): g.rect(x, 28, x + 1, 28, '#a9b0bb')        # quad pipes
    # wheels: arch, tyre, mesh rim, red caliper
    for cx in WHEELS:
        for y in range(16, H):
            for x in range(cx - 10, cx + 11):
                if (x - cx) ** 2 + (y - WY) ** 2 <= 9 ** 2: g.px(x, y, None)
        g.disc(cx, WY, 8.4, DARK, ymax=WY)
        g.disc(cx, WY, 7.5, '#1d1e24')
        g.disc(cx, WY, 6, '#c9ccd4')
        g.disc(cx, WY, 5, '#aeb3bd')
        for k in range(10):                                   # mesh: dark windows between spokes
            a = (k / 10 + phase * 0.05) * 2 * math.pi
            for r in (3.2, 4.4):
                g.px(round(cx + math.cos(a) * r), round(WY + math.sin(a) * r), '#3a3d45')
            if k % 2 == 0:
                b = a + math.pi / 10
                g.px(round(cx + math.cos(b) * 2), round(WY + math.sin(b) * 2), '#3a3d45')
        g.px(cx - 3, WY - 1, '#e0303a'); g.px(cx - 3, WY, '#e0303a')  # caliper peeking through
        g.disc(cx, WY, 1.2, '#2b2d33')
    return g.image()


if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else '.'
    for c in COLORS:
        img = sprite(c)
        img.save(f'{out}/bmw-m3_{c}_1x.png')
        img.resize((W * 8, H * 8), Image.NEAREST).save(f'{out}/bmw-m3_{c}_8x.png')
    sheet = Image.new('RGBA', (W * 8 * 2, H * 8 * 3), (255, 255, 255, 255))
    for i, c in enumerate(COLORS):
        sheet.alpha_composite(sprite(c).resize((W * 8, H * 8), Image.NEAREST), ((i % 2) * W * 8, (i // 2) * H * 8))
    sheet.convert('RGB').save(f'{out}/bmw-m3_preview.png')
