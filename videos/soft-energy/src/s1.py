"""Scene 1: rainy roadside store under a giant tower, flooded street reflection."""
import math
import numpy as np
from PIL import Image, ImageFilter
from lib import Canvas, hx, mix, glyph, vgrad, Rain, ShortRain

W, H, K = 240, 228, 3
WL = 141  # waterline

SKY_T, SKY_B = '#1394b3', '#1ea0bc'
HILL1, HILL2 = '#1085b3', '#0c7eae'
WIRE = '#0b3d52'
TREE_A, TREE_B, TREE_C = '#0a4d63', '#08455c', '#063a4e'
TOWER = '#022135'
NEON = '#ff2a4a'


def _sky(c):
    vgrad(c, 0, 0, W - 1, 100, SKY_T, SKY_B)
    # far hills, hazy
    c.poly([(0, 40), (12, 41), (30, 46), (48, 52), (60, 58), (60, 100), (0, 100)], HILL1)
    c.poly([(0, 44), (14, 45), (28, 49), (44, 54), (60, 60), (60, 100), (0, 100)], '#0e80ae')
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
    cols = ['#043546', '#022b3a', '#01222f']
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
            c.px(xx, yy, '#0a4558' if r.random() < .45 else '#011a24')


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
    # bundle from upper-right falling to the left
    for i, (xa, xb) in enumerate([(100, 44), (108, 52), (116, 60), (124, 68), (90, 36), (135, 80)]):
        c.line(xa, 0, xb - 10, 96, WIRE if i % 2 else '#0d4a63')
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
            f = 0.35 * (1 - y / 30) if y < 30 else 0.04
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
    c.rect(0, 101, 52, 140, '#04435f')
    c.rect(0, 101, 52, 102, '#0a5470')
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
    c.rect(62, 96, 150, 140, '#031a20')
    c.rect(60, 93, 152, 98, '#05435d')
    c.rect(60, 93, 152, 93, '#0e5a76')
    # roof-top board (tilted)
    c.poly([(91, 75), (114, 67), (114, 90), (93, 97)], '#1c1418')
    c.poly([(91, 75), (114, 67), (114, 69), (91, 77)], '#2a2022')
    for (x, y) in [(95, 77), (99, 76), (103, 75), (106, 73), (109, 72), (97, 80), (101, 79), (105, 78), (108, 77)]:
        c.rect(x, y, x + 1, y, '#3c7b92')
    c.rect(96, 82, 111, 82, '#2a6e86')
    c.rect(102, 70, 103, 98, '#100c0e')
    c.rect(99, 88, 102, 89, '#3a2c2e')
    # store windows (warm)
    Y = '#ddd47e'
    c.rect(68, 112, 89, 123, '#0d6a84')
    c.rect(69, 113, 74, 122, Y)
    c.rect(76, 113, 85, 117, Y)
    c.rect(76, 118, 78, 122, Y)
    c.rect(85, 113, 89, 122, Y)
    c.rect(97, 112, 107, 138, '#0d6a84')
    c.rect(98, 113, 106, 120, Y)
    c.rect(99, 116, 104, 117, '#3a8a9a')
    c.rect(98, 123, 106, 129, Y)
    c.rect(98, 131, 106, 137, '#9a9a5a')
    c.rect(112, 112, 131, 123, '#0d6a84')
    c.rect(113, 113, 130, 122, Y)
    c.rect(115, 117, 117, 122, '#2b4e5a')
    c.rect(119, 116, 126, 120, '#2b4e5a')
    c.rect(121, 117, 124, 119, Y)
    c.rect(66, 102, 70, 103, '#3a8aa8')
    c.rect(66, 105, 70, 106, '#3a8aa8')
    c.rect(66, 108, 70, 108, '#3a8aa8')
    glyph(c, 88, 107, ['#.#..#.##.#', '#.#.##.#..#'], '#2a7896')
    # little sign by the road
    c.rect(56, 128, 76, 138, '#1b1015')
    glyph(c, 57, 130, ['#.#.###.##.##', '#.#.#.#.#.#.#', '#.#.###.#.#.#', '#.#.#...#.#.#', '#.#.#...##.##'], '#7aa8b8')
    # ICE freezer
    c.rect(75, 121, 92, 140, '#2a6f94')
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
    """Station wagon seen from the rear three-quarter, roof rack on top."""
    # roof rack load
    c.rect(16, 110, 36, 110, '#0a2836')
    for x in (17, 24, 31, 36):
        c.rect(x, 110, x, 116, '#0a2836')
    c.line(19, 112, 33, 108, '#0e3446')
    # cabin
    c.poly([(10, 123), (18, 116), (42, 116), (47, 123)], '#0f3a50')
    c.poly([(14, 122), (20, 117), (40, 117), (44, 122)], '#1c6888')
    c.line(22, 121, 26, 117, '#3e94b6'); c.line(30, 121, 34, 117, '#3e94b6')
    c.rect(28, 117, 28, 122, '#0f3a50')
    c.rect(40, 118, 42, 121, '#c8c070')
    # body
    c.rect(3, 123, 50, 136, '#0b2a3a')
    c.rect(3, 123, 50, 123, '#2a7090')
    c.rect(4, 130, 48, 131, '#3a8aa8')
    c.rect(12, 125, 30, 128, '#082230')
    c.rect(15, 126, 27, 127, '#174a62')
    c.rect(44, 123, 50, 135, '#235f7c')
    c.rect(47, 125, 49, 128, '#d0c878')
    c.rect(3, 125, 6, 128, '#b03040')
    c.rect(3, 133, 50, 135, '#06141c')
    c.rect(7, 136, 12, 140, '#020c12')
    c.rect(38, 136, 44, 140, '#020c12')


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
        s.rain = ShortRain(W, H, 60, 11, 6, 16, (300, 420), (0.12, 0.3), 0, WL + 3)
        s.rain_far = ShortRain(W, H, 40, 12, 2, 6, (200, 280), (0.1, 0.25), 0, WL)
        r = np.random.default_rng(5)
        s.ph = r.uniform(0, 6.28, H)

    def frame(s, t):
        c = s.base.copy()
        flick = 0.92 + 0.08 * math.cos(2 * math.pi * (t - 0.6) / 1.85)  # slow breathing pulse
        neon_ring(c, flick)
        a = c.arr()
        top = a[:WL].copy()
        # reflection: flipped, rippled, darkened
        out = a.copy()
        for y in range(WL, H):
            sy = 2 * 135 - y
            if sy < 0:
                sy = 0
            d = (y - WL) / (H - WL)
            amp = 0.6 + 2.6 * d
            off = int(round(amp * 0.7 * math.sin(t * 1.6 + y * 0.9 + s.ph[y]) + amp * 0.25 * math.sin(t * 3.1 + y * 2.1)))
            row = np.roll(top[sy], off, axis=0)
            dark = 0.42 * (1 - d) ** 2.2 + 0.03
            base = np.array(mix('#001c26', '#00263a', d / 0.3) if d < 0.3 else mix('#00263a', '#002134', (d - 0.3) / 0.7), np.float32)
            k = dark * (0.45 if y % 2 else 1.0)
            out[y] = base * (1 - k) + row * k * np.array([0.55, 0.9, 0.75])
        # broken shimmer lines on reflection
        rr = np.random.default_rng(int(t * 3))
        for _ in range(14):
            y = int(rr.integers(WL + 2, H - 10))
            x = int(rr.integers(0, W - 12))
            ln = int(rr.integers(2, 9))
            out[y, x:x + ln] = out[y, x:x + ln] * 0.75 + np.array(hx('#0b4e66')) * 0.25
        # neon reflection ripple: appears only briefly (as in the source clip)
        vis = 0.0
        if 0.43 <= t < 0.87:
            vis = 0.45 + 0.55 * (t - 0.43) / 0.44
        elif 2.2 <= t < 2.5:
            vis = 1.0
        if vis > 0:
            for k in range(84):
                x = 133 + k
                yb = 190 + 0.18 * k
                fade = (1 - k / 95) * vis
                hgt = 2 + int(3 * abs(math.sin(k * 1.9 + t * 7)))
                for j in range(hgt):
                    if (k * 3 + j) % 5 == 4:
                        continue
                    yy, xx = int(yb + j - hgt // 2 + math.sin(k * 0.8) * 1.2), x
                    if WL < yy < H and xx < W:
                        f = 0.7 * fade
                        out[yy, xx] = out[yy, xx] * (1 - f) + np.array(hx('#c03060')) * f
            if t >= 2.2:  # brighter blob where the ripple starts
                for (dx, dy) in [(0, 0), (1, 0), (0, 1), (1, 1), (2, 0), (-1, 1)]:
                    out[190 + dy, 133 + dx] = out[190 + dy, 133 + dx] * 0.4 + np.array(hx('#d03868')) * 0.6
        # small blue splash glow on the water
        for dy in range(-4, 5):
            for dx in range(-3, 4):
                if abs(dx) + abs(dy) * 0.7 <= 3.2 and (dx + dy) % 2 == 0:
                    out[213 + dy, 163 + dx] = out[213 + dy, 163 + dx] * 0.55 + np.array(hx('#1a5a9a')) * 0.45
        s.rain_far.draw(out, t, '#4fb7d6', 0.35)
        s.rain.draw(out, t, '#8fe6ff', 0.7)
        # rain splashes on water
        rs = np.random.default_rng(int(t * 30) + 999)
        for _ in range(4):
            x = int(rs.integers(0, W)); y = int(rs.integers(WL + 4, H - 4))
            out[y, max(0, x - 1):x + 2] = out[y, max(0, x - 1):x + 2] * 0.5 + np.array(hx('#2b6f88')) * 0.5
        return out
