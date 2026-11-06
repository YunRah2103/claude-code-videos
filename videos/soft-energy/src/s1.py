"""Scene 1: rainy roadside store under a giant tower, flooded street reflection."""
import math
import numpy as np
from PIL import Image, ImageFilter
from lib import Canvas, hx, mix, glyph, vgrad, Rain

W, H, K = 240, 228, 3
WL = 141  # waterline

SKY_T, SKY_B = '#24a8c6', '#168db0'
HILL1, HILL2 = '#1286a8', '#0f7799'
WIRE = '#0b3d52'
TREE_A, TREE_B, TREE_C = '#0a4d63', '#08455c', '#063a4e'
TOWER = '#042637'
NEON = '#ff2a4a'


def _sky(c):
    vgrad(c, 0, 0, W - 1, 100, SKY_T, SKY_B)
    # far hills, hazy
    c.poly([(0, 40), (12, 41), (30, 46), (48, 52), (60, 58), (60, 100), (0, 100)], HILL1)
    c.poly([(0, 44), (14, 45), (28, 49), (44, 54), (60, 60), (60, 100), (0, 100)], '#148cad')
    c.poly([(40, 72), (58, 66), (75, 63), (92, 64), (110, 70), (125, 74), (125, 100), (40, 100)], HILL1)
    c.poly([(50, 76), (68, 70), (85, 68), (100, 70), (125, 78), (125, 100), (50, 100)], HILL2)


def _trees(c):
    r = np.random.default_rng(3)
    trees = []
    x = -4
    while x < 126:
        top = 58 + int(r.integers(0, 12)) + int(max(0, x - 25) * 0.16)
        trees.append((x, top, int(r.integers(0, 3))))
        x += int(r.integers(3, 7))
    cols = ['#0a4357', '#083a4d', '#062f40']
    for xx in range(0, 122):
        best, k = 999, 0
        for (px, top, ci) in trees:
            y = top + abs(xx - px) * 2.2
            if y < best:
                best, k = y, ci
        y0 = int(best)
        c.rect(xx, y0, xx, 100, cols[k])
        # branch notches on the silhouette
        if (xx + y0) % 3 == 0:
            c.px(xx, y0 - 1, cols[k])
    for _ in range(260):
        xx, yy = int(r.integers(0, 121)), int(r.integers(64, 99))
        p = c.im.getpixel((xx, yy))
        if p in [hx(cc) for cc in cols]:
            c.px(xx, yy, '#0e5870' if r.random() < .45 else '#04283a')


def _pole(c, x, y0, y1, arms):
    c.rect(x, y0, x + 1, y1, '#072f40')
    for (yy, a, b) in arms:
        c.rect(a, yy, b, yy + 1, '#072f40')
        for k in range(a, b + 1, 3):
            c.px(k, yy - 1, '#072f40')


def _wires(c):
    # bundle from upper-left falling to the right (towards the tower)
    for i, (y0, y1) in enumerate([(2, 46), (5, 48), (9, 51), (12, 53), (16, 56), (-3, 40)]):
        c.line(0, y0, 130, y1 + 25, WIRE if i % 2 else '#0d4a63')
        c.line(0, y0 + 1, 130, y1 + 26, '#0f5a75')
    # bundle from upper-right falling to the left
    for i, (xa, xb) in enumerate([(100, 44), (108, 52), (116, 60), (124, 68), (90, 36), (135, 80)]):
        c.line(xa, 0, xb - 10, 96, WIRE if i % 2 else '#0d4a63')
        c.line(xa + 1, 0, xb - 9, 96, '#0f5a75')
    for i, (xa, xb) in enumerate([(152, 105), (160, 112), (140, 98)]):
        c.line(xa, 0, xb - 30, 96, '#0d4a63')
    # horizontal sagging wires
    for y, sag in [(51, 2), (55, 2), (58, 1)]:
        for x in range(0, W):
            dy = int(sag * math.sin(math.pi * (x % 120) / 120))
            c.px(x, y + dy, '#05283a')


def _tower(c):
    # giant cooling-tower-like structure on the right, edge curving outward
    edge = lambda y: 123 + int(17 * (1 - min(1, y / 95)) ** 2)
    c.poly([(edge(y), y) for y in range(0, 141, 4)] + [(W, 140), (W, 0)], TOWER)
    for y in range(0, 141):
        c.px(edge(y), y, '#0b4258')
    r = np.random.default_rng(7)
    vgl = np.asarray(c.im).copy()
    for y in range(0, 60):  # lighter crown above the neon ring
        for x in range(edge(y) + 1, W):
            f = 0.55 * (1 - y / 30) if y < 30 else 0.06
            vgl[y, x] = vgl[y, x] * (1 - f) + np.array(hx('#1a7aa0')) * f
    from PIL import Image as _I, ImageDraw as _D
    c.im = _I.fromarray(vgl.astype(np.uint8)); c.d = _D.Draw(c.im)
    # vertical panel lines fanning out from the crown
    cx = 190
    for k in range(34):
        u = k / 33
        xb = 128 + u * 112
        col = '#0d5373' if k % 3 else '#156f96'
        y = int(r.integers(2, 16))
        while y < 136:
            ln = int(r.integers(3, 18)) if y < 70 else int(r.integers(2, 9))
            for yy in range(y, min(y + ln, 136)):
                xx = int(cx + (xb - cx) * (0.62 + 0.38 * yy / 136))
                if xx > edge(yy) + 1:
                    c.px(xx, yy, col)
            y += ln + int(r.integers(2, 10))
    # window specks
    for _ in range(42):
        x, y = int(r.integers(140, 236)), int(r.integers(22, 46))
        c.rect(x, y, x + int(r.integers(0, 3)), y, '#d9a531' if r.random() < .6 else '#9b7a2a')
    c.rect(157, 1, 170, 6, '#2fd0f0')
    c.rect(161, 0, 166, 1, '#8ff0ff')
    # sign boards on tower face
    c.rect(141, 64, 150, 90, '#021820')
    glyph(c, 142, 66, ['###.', '#...', '###.', '#...', '###.', '....', '###.', '#..#', '###.'], '#0e4c62')
    glyph(c, 142, 77, ['###', '#.#', '###', '#..', '###', '...', '#.#', '###'], '#0e4c62')


def neon_ring(c, flick=1.0):
    col = mix('#7a1428', NEON, flick)
    hi = mix('#7a1428', '#ffb0c8', flick)
    pts = []
    for x in range(130, W):
        u = (x - 130) / 110
        y = 31 - 15 * math.sin(min(1, u * 1.35) * math.pi / 2) + 3 * max(0, u - .74)
        pts.append((x, int(round(y))))
    for (x, y) in pts:
        c.rect(x, y, x, y + 1, col)
        if (x // 9) % 3 == 0:
            c.px(x, y, hi)
    c.rect(202, 99, W, 100, col)
    c.rect(202, 99, 230, 99, hi)


def _houses(c):
    # left house
    c.poly([(0, 94), (10, 92), (62, 114), (62, 140), (0, 140)], '#0b4256')
    c.poly([(0, 92), (8, 90), (64, 113), (60, 116), (6, 95), (0, 97)], '#06303f')
    c.rect(0, 101, 52, 140, '#0f5670')
    c.rect(0, 101, 52, 102, '#136580')
    for x0 in (25, 35, 43):
        c.rect(x0, 106, x0 + 5, 113, '#053040')
        c.rect(x0 + 2, 106, x0 + 2, 113, '#0f5670')
    # right houses behind store
    c.poly([(150, 92), (196, 92), (205, 99), (205, 140), (150, 140)], '#0e4d62')
    c.rect(150, 92, 196, 93, '#16708a')
    c.rect(196, 96, 202, 140, '#0a3f52')
    for (x0, y0) in [(193, 96), (193, 115)]:
        c.rect(x0, y0, x0 + 5, y0 + 10, '#062e3c')
        c.rect(x0 + 2, y0, x0 + 2, y0 + 10, '#127090')
    c.rect(205, 102, W, 140, '#04293a')
    c.poly([(152, 97), (170, 97), (186, 104), (186, 140), (152, 140)], '#0b4255')
    c.rect(171, 98, 172, 118, '#3b8fa8')


def _store(c):
    c.rect(62, 96, 150, 140, '#031a22')
    c.rect(60, 93, 152, 98, '#0f5a74')
    c.rect(60, 93, 152, 93, '#1a7896')
    # roof-top board (tilted)
    c.poly([(91, 75), (114, 67), (114, 90), (93, 97)], '#1c1418')
    c.poly([(91, 75), (114, 67), (114, 69), (91, 77)], '#2a2022')
    for (x, y) in [(95, 77), (99, 76), (103, 75), (106, 73), (109, 72), (97, 80), (101, 79), (105, 78), (108, 77)]:
        c.rect(x, y, x + 1, y, '#3c7b92')
    c.rect(96, 82, 111, 82, '#2a6e86')
    c.rect(102, 70, 103, 98, '#100c0e')
    c.rect(99, 88, 102, 89, '#3a2c2e')
    # store windows (warm)
    Y = '#e9e28f'
    c.rect(68, 112, 89, 123, '#0d6a84')
    c.rect(69, 113, 74, 122, Y)
    c.rect(76, 113, 85, 117, Y)
    c.rect(76, 118, 78, 122, Y)
    c.rect(85, 113, 89, 122, Y)
    c.rect(97, 112, 107, 138, '#0d6a84')
    c.rect(98, 113, 106, 120, Y)
    c.rect(99, 116, 104, 117, '#3a8a9a')
    c.rect(98, 123, 106, 137, Y)
    c.rect(112, 112, 122, 123, '#0d6a84')
    c.rect(113, 113, 121, 122, Y)
    c.rect(115, 116, 118, 120, '#2b5e6a')
    c.rect(66, 102, 70, 103, '#3a8aa8')
    c.rect(66, 105, 70, 106, '#3a8aa8')
    c.rect(66, 108, 70, 108, '#3a8aa8')
    glyph(c, 88, 107, ['#.#..#.##.#', '#.#.##.#..#'], '#2a7896')
    # little sign by the road
    c.rect(56, 128, 76, 138, '#1b1015')
    glyph(c, 57, 130, ['#.#.###.##.##', '#.#.#.#.#.#.#', '#.#.###.#.#.#', '#.#.#...#.#.#', '#.#.#...##.##'], '#7aa8b8')
    # ICE freezer
    c.rect(75, 121, 92, 140, '#2f7fa8')
    c.rect(75, 121, 92, 122, '#4fa0c8')
    c.rect(78, 124, 88, 128, '#1d5f80')
    c.rect(79, 125, 87, 127, '#3f8fb8')
    glyph(c, 77, 132, ['#.###.###', '#.#...#..', '#.#.#.##.', '#.#.#.#..', '#.###.###'], '#0a2a38')
    c.rect(92, 121, 95, 140, '#1f6080')
    # cage / door grill on the right
    for x in range(132, 149, 4):
        c.rect(x, 110, x, 140, '#1d6f90')
    for y in (110, 122, 130, 139):
        c.rect(132, y, 148, y, '#1d6f90')
    c.rect(136, 113, 138, 120, '#e9e28f')
    c.rect(141, 113, 142, 118, '#c9c27a')


def _car(c):
    B, D, L = '#2f86b0', '#0b2d3e', '#57b0d0'
    c.poly([(14, 122), (22, 116), (40, 116), (46, 122)], '#1d6a90')
    c.rect(16, 117, 44, 118, '#081f2c')
    c.rect(11, 115, 31, 116, '#0a3346')  # roof rack
    c.poly([(18, 121), (24, 117), (31, 117), (31, 121)], L)
    c.poly([(33, 117), (40, 117), (44, 121), (33, 121)], '#3c95bb')
    c.rect(4, 122, 52, 133, D)
    c.rect(4, 129, 52, 131, B)
    c.rect(6, 123, 50, 124, '#174f6c')
    c.rect(4, 125, 6, 127, '#c43a4a')
    c.rect(50, 125, 52, 127, '#d6c070')
    c.rect(53, 128, 56, 131, '#e9e28f')  # head-light glow
    c.rect(18, 129, 26, 130, '#7cc4dc')
    c.rect(8, 134, 13, 138, '#03141c')
    c.rect(40, 134, 45, 138, '#03141c')


def _ground(c):
    c.rect(0, 139, W - 1, 141, '#0a4559')
    c.rect(0, 139, W - 1, 139, '#0f566e')


def build():
    c = Canvas(W, H, SKY_B)
    _sky(c)
    _wires(c)
    _pole(c, 37, 17, 96, [(27, 26, 50), (32, 29, 45), (42, 30, 46), (46, 32, 43)])
    c.rect(32, 31, 40, 37, '#0e5a76')
    c.rect(33, 32, 34, 36, '#1a7898')
    _trees(c)
    _pole(c, 89, 48, 100, [(67, 82, 107), (77, 95, 104)])
    _tower(c)
    _houses(c)
    _store(c)
    _car(c)
    _ground(c)
    return c


class Scene1:
    def __init__(s):
        s.base = build()
        s.rain = Rain(W, H, 70, 11, 5, 14, (330, 430))
        s.rain_far = Rain(W, H, 60, 12, 2, 6, (220, 300))
        r = np.random.default_rng(5)
        s.ph = r.uniform(0, 6.28, H)

    def frame(s, t):
        c = s.base.copy()
        flick = 1.0 if (int(t * 30) % 47) not in (3, 4, 19) else 0.55
        neon_ring(c, flick)
        a = c.arr()
        top = a[:WL].copy()
        # reflection: flipped, rippled, darkened
        out = a.copy()
        for y in range(WL, H):
            sy = 2 * WL - y - 1
            if sy < 0:
                sy = 0
            d = (y - WL) / (H - WL)
            amp = 0.6 + 2.6 * d
            off = int(round(amp * 1.4 * math.sin(t * 2.3 + y * 0.9 + s.ph[y]) + amp * 0.5 * math.sin(t * 5.1 + y * 2.1)))
            row = np.roll(top[sy], off, axis=0)
            dark = 0.28 * (1 - d) ** 1.6 + 0.04
            base = np.array(mix('#03283a', '#011824', d), np.float32)
            out[y] = base * (1 - dark) + row * dark * np.array([0.6, 0.85, 0.95])
        # broken shimmer lines on reflection
        rr = np.random.default_rng(int(t * 12))
        for _ in range(26):
            y = int(rr.integers(WL + 2, H - 10))
            x = int(rr.integers(0, W - 12))
            ln = int(rr.integers(2, 9))
            out[y, x:x + ln] = out[y, x:x + ln] * 0.75 + np.array(hx('#0b4e66')) * 0.25
        # neon reflection ripple (bottom right)
        for k in range(60):
            x = 128 + k * 1.7
            y = 196 + 0.12 * k + 2.5 * math.sin(k * 0.7 + t * 6)
            yy, xx = int(y), int(x)
            if 0 <= xx < W and WL < yy < H:
                f = 0.5 + 0.3 * math.sin(k * 1.3 + t * 9)
                out[yy, xx] = out[yy, xx] * (1 - f) + np.array(hx('#c0304e')) * f
                if yy + 1 < H:
                    out[yy + 1, xx] = out[yy + 1, xx] * (1 - f * .5) + np.array(hx('#8a2040')) * f * .5
        s.rain_far.draw(out, t, '#4fb7d6', 0.35, WL)
        s.rain.draw(out, t, '#8fe6ff', 0.75, WL + 3)
        # rain splashes on water
        for _ in range(8):
            x = int(rr.integers(0, W)); y = int(rr.integers(WL + 4, H - 4))
            out[y, max(0, x - 1):x + 2] = out[y, max(0, x - 1):x + 2] * 0.5 + np.array(hx('#2b6f88')) * 0.5
        return out
