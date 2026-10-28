"""Small shared pixel props: tags, stamps, badges, labels, ticks, glyphs, sparkles, arrows, snowflakes, bubbles."""
import math as _m
from functools import lru_cache
from .grid import Grid, text_width, FONT, up


@lru_cache(None)
def tag(text, body='#fff6e0', ink='#d6303a', strike=False):
    tw = text_width(text)
    w, h = tw + 14, 15
    g = Grid(w, h)
    for y in range(1, h-1):
        g.rect(1 + max(0, 4 - min(y-1, h-2-y)), y, w-2, y, body)
    g.px(5, 7, '#1a1a2e')
    g.text(9, 4, text, ink)
    if strike:
        g.rect(7, 7, w-3, 7, '#1a1a2e')
    return g.image()

@lru_cache(None)
def stamp(text, col='#e0303a', fill=None):
    tw = text_width(text)
    w, h = tw + 10, 15
    g = Grid(w, h)
    if fill:
        g.rect(1, 1, w - 2, h - 2, fill)
    g.rect(1, 1, w-2, 2, col); g.rect(1, h-3, w-2, h-2, col)
    g.rect(1, 1, 2, h-2, col); g.rect(w-3, 1, w-2, h-2, col)
    g.text(5, 4, text, col)
    return g.image(outline=False)

@lru_cache(None)
def badge(text, body='#ffd23f', ink='#d6303a', shade='#e8b923'):
    tw = text_width(text)
    w, h = tw + 10, 13
    g = Grid(w, h)
    g.rect(2, 1, w-3, h-2, body); g.rect(1, 2, w-2, h-3, body)
    g.rect(2, h-3, w-3, h-2, shade)
    g.text(5, 3, text, ink)
    return g.image()

@lru_cache(None)
def label(text, col='#ffffff'):
    g = Grid(text_width(text) + 2, 9)
    g.text(1, 1, text, col)
    return g.image()

@lru_cache(None)
def check():
    g = Grid(16, 13)
    pts = [(2, 6), (3, 7), (4, 8), (5, 9), (6, 8), (7, 7), (8, 6), (9, 5), (10, 4), (11, 3), (12, 2)]
    for x, y in pts:
        g.rect(x, y, x+1, y+2, '#3cc85a')
    return g.image()

@lru_cache(None)
def xmark():
    g = Grid(15, 15)
    for i in range(1, 13):
        g.rect(i, i, i+1, i+1, '#e0303a')
        g.rect(13-i, i, 14-i, i+1, '#e0303a')
    return g.image()

@lru_cache(None)
def glyph(ch, col):
    rows = FONT[ch]
    g = Grid(len(rows[0]) + 2, 9)
    g.text(1, 1, ch, col)
    return g.image()

@lru_cache(None)
def bubble(dots=3):
    g = Grid(32, 24)
    g.rect(2, 1, 29, 15, '#ffffff'); g.rect(1, 2, 30, 14, '#ffffff')
    for i in range(5):
        g.rect(6 - i // 2, 16 + i, 9 - i, 16 + i, '#ffffff')
    for i in range(dots):
        g.rect(8 + i*6, 7, 10 + i*6, 9, '#1a1a2e')
    return g.image()

@lru_cache(None)
def heart():
    g = Grid(11, 10)
    rows = ["0110110", "1111111", "1111111", "0111110", "0011100", "0001000"]
    for y, r in enumerate(rows):
        for x, b in enumerate(r):
            if b == '1': g.px(x+2, y+2, '#ff4d6d')
    g.px(3, 3, '#ffb3c1')
    return g.image()

@lru_cache(None)
def arrow():
    g = Grid(13, 14)
    g.rect(4, 1, 8, 6, '#ffd23f')
    for i in range(6):
        g.rect(1+i, 7+i, 11-i, 7+i, '#ffd23f')
    return g.image()

@lru_cache(None)
def star(col='#ffd23f'):
    g = Grid(7, 7)
    g.rect(3, 1, 3, 5, col); g.rect(1, 3, 5, 3, col)
    return g.image()

@lru_cache(None)
def sparkle(size=0):
    g = Grid(9, 9)
    if size == 0:
        g.px(4, 4, '#ffffff'); g.px(4, 3, '#fff6b0'); g.px(4, 5, '#fff6b0'); g.px(3, 4, '#fff6b0'); g.px(5, 4, '#fff6b0')
    else:
        g.rect(4, 1, 4, 7, '#fff6b0'); g.rect(1, 4, 7, 4, '#fff6b0'); g.rect(3, 3, 5, 5, '#ffffff')
    return g.image(oc=(255, 200, 60, 255))

FLAKE = ["0001000", "0101010", "0011100", "1111111", "0011100", "0101010", "0001000"]
def _flake(g, cx, cy, col):
    for j, row in enumerate(FLAKE):
        for i, b in enumerate(row):
            if b == '1': g.px(cx - 3 + i, cy - 3 + j, col)

@lru_cache(None)
def snowflake(col='#7fd4ff'):
    g = Grid(11, 11)
    _flake(g, 5, 5, col)
    return g.image()

