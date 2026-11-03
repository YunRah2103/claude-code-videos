"""2D pixel twins of the 3D assets in pix3d/ (same palette and pixel maps), for 2D episodes and for the shared overlay.

All sprites are small RGBA grids; scale them with pixanim.grid.up(img, s) (s=4 matches the 3D version's 4x pixel).
  PAL                      palette.js as RGB tuples
  gauge(value, fill, glow, limit_on, limit=155, vmax=200)  small speedometer: lit segments, red limit line, needle,
                           glowing limit digits (the only number on it), steel panel with bolts (70x66)
  handshake(), key(), padlock(open_k)   the deal / unlock props (same maps as pix3d/props.js)
  force_wall(w, h, k, t)   glowing force-field wall (grid lines, posts with lamps); k = hit flash 0..1
"""
import math
from functools import lru_cache
from PIL import Image, ImageDraw
from pixanim.grid import Grid, outline


def _rgb(h): return ((h >> 16) & 255, (h >> 8) & 255, h & 255)


PAL = {k: _rgb(v) for k, v in dict(
    navy=0x1a1a2e, silver=0x5c616c, silverHi=0x848a96, silverSh=0x3c3f47, glow=0xffd23f, glowHi=0xffeea0, red=0xff5a5a,
    gold=0xf2b829, goldSh=0xa8761a, skin=0xe0a77a, sleeve=0xeceef4, carBlue=0x2f6fd6, carOrange=0xff8c1e,
    face=0x101116, segOff=0x2a2c34, stampRed=0xe0303a).items()}
A0, SWEEP = 225, 270


def _ang(v, vmax): return math.radians(A0 - SWEEP * v / vmax)


@lru_cache(512)
def _gauge(v, fill, glow, limit_on, limit, vmax):
    W_, H_, cx, cy, r = 70, 66, 35, 33, 26
    img = Image.new('RGBA', (W_, H_), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rectangle((0, 0, W_ - 1, H_ - 1), fill=PAL['silverSh'])
    for x, y in ((3, 3), (W_ - 5, 3), (3, H_ - 5), (W_ - 5, H_ - 5)): d.rectangle((x, y, x + 1, y + 1), fill=PAL['silverHi'])
    d.ellipse((cx - r - 2, cy - r - 2, cx + r + 2, cy + r + 2), fill=PAL['silverHi'])
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=PAL['face'])
    for i in range(36):                                            # segments
        sv = (i + 0.5) / 36 * vmax; a = _ang(sv, vmax)
        col = (PAL['red'] if sv > limit - 18 else PAL['glow']) if sv <= fill else PAL['segOff']
        d.line([(cx + math.cos(a) * r * 0.74, cy - math.sin(a) * r * 0.74), (cx + math.cos(a) * r * 0.92, cy - math.sin(a) * r * 0.92)], fill=col, width=2)
    for i in range(11):                                            # plain ticks, no numbers
        a = _ang(i / 10 * vmax, vmax)
        d.point((round(cx + math.cos(a) * r * 0.62), round(cy - math.sin(a) * r * 0.62)), fill=PAL['silverHi'])
    if limit_on:
        a = _ang(limit, vmax)
        d.line([(cx + math.cos(a) * r * 0.66, cy - math.sin(a) * r * 0.66), (cx + math.cos(a) * r * 1.06, cy - math.sin(a) * r * 1.06)], fill=PAL['red'], width=3)
    from pixanim.grid import text_width
    g = Grid(text_width(str(limit)) + 2, 7); g.text(1, 1, str(limit), '#%02x%02x%02x' % (PAL['glowHi'] if glow > 0.5 else PAL['glow']))
    dg = g.image(outline=False)
    if glow > 0.05:
        halo = Image.new('RGBA', (dg.width + 6, dg.height + 4), PAL['glow'] + (int(70 * glow),))
        img.alpha_composite(halo, (cx - halo.width // 2, cy + 8 - 2))
    img.alpha_composite(dg, (cx - dg.width // 2 + 1, cy + 8))
    a = _ang(v, vmax)
    d = ImageDraw.Draw(img)
    d.line([(cx, cy), (cx + math.cos(a) * r * 0.8, cy - math.sin(a) * r * 0.8)], fill=PAL['red'], width=2)
    d.ellipse((cx - 3, cy - 3, cx + 3, cy + 3), fill=PAL['silverHi'])
    return outline(img)


def gauge(value=0.0, fill=0.0, glow=0.0, limit_on=True, limit=155, vmax=200):
    return _gauge(round(value), round(fill), round(glow, 1), bool(limit_on), limit, vmax)


def _sprite(rows, cmap):
    img = Image.new('RGBA', (max(map(len, rows)), len(rows)), (0, 0, 0, 0))
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch in cmap: img.putpixel((x, y), cmap[ch] + (255,))
    return img


@lru_cache(None)
def handshake():
    return _sprite(['.oooo.....ooo.........oooo.', 'osssso...okkko.......occcco', 'ossssoooookkkooooooooocccco',
                    'osssssokkkkkkkkkkkkkokcccco', 'osssssokdkkdkkdkkdkkkkcccco', 'osssssokdkkdkkdkkdkkkkcccco',
                    'osssssokdkkdkkdkkdkkkocccco', 'osssso.okkkkkkkkkkkkooocccco', '.oooo...ooooooooooooo..oooo.'],
                   dict(o=PAL['navy'], s=PAL['sleeve'], c=PAL['carBlue'], k=PAL['skin'], d=(176, 122, 82)))


@lru_cache(None)
def key():
    return outline(_sprite(['.ggg...............', 'gGGGg..............', 'gG.GgggggggggggggggG', 'gG.GGGGGGGGGGGGGGGGG',
                            'gGGGg........G.G.G..', '.ggg.........G.G....'], dict(g=PAL['goldSh'], G=PAL['gold'])))


@lru_cache(64)
def padlock(open_k=0.0):
    img = Image.new('RGBA', (8, 14), (0, 0, 0, 0))
    sh = _sprite(['..ssss..', '.s....s.', '.s....s.', '.s....s.'], dict(s=PAL['silverHi']))
    img.alpha_composite(sh, (0, 4 - round(3 * open_k)))
    img.alpha_composite(_sprite(['GGGGGGGG', 'GGGGGGGG', 'GGGnnGGG', 'GGGnnGGG', 'GGGGGGGG', 'gggggggg'],
                                dict(G=PAL['gold'], g=PAL['goldSh'], n=PAL['navy'])), (0, 8))
    return outline(img)


def force_wall(w=16, h=60, k=0.0, t=0.0, base=0.7):
    """Side-on force field: a column of glowing grid cells between two posts with lamps (w x h grid px)."""
    img = Image.new('RGBA', (w + 4, h + 3), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    a = min(255, int(255 * (base + 0.6 * k)))
    gl = PAL['glowHi'] if k > 0.4 else PAL['glow']
    d.rectangle((2, 3, w + 1, h + 2), fill=gl + (int(a * 0.35),))          # the field itself
    for y in range(3, h + 3, 6):
        wob = round(1.5 * k * math.sin(y * 0.5 + t * 30))
        d.line([(2 + wob, y), (w + 1 + wob, y)], fill=gl + (a,))
    for x in range(2, w + 2, 6): d.line([(x, 3), (x, h + 2)], fill=gl + (a,))
    d.rectangle((0, 2, 1, h + 2), fill=PAL['silverSh']); d.rectangle((w + 2, 2, w + 3, h + 2), fill=PAL['silverSh'])
    d.rectangle((0, 0, 1, 1), fill=PAL['glow']); d.rectangle((w + 2, 0, w + 3, 1), fill=PAL['glow'])
    return img
