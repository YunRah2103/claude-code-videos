"""Scene 3: rainy cyber-industrial depot, tower '05', green neon, truck and kiosk."""
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from lib import Canvas, hx, mix, glyph, vgrad, Rain, ShortRain

W, H = 360, 341
LINE = '#0e3c74'
LINE2 = '#1c5c98'
GRN = '#a8f010'


def _grid(c, x0, y0, x1, y1, step=3, col='#06163a'):
    for x in range(x0, x1 + 1, step):
        c.rect(x, y0, x, y1, col)
    for y in range(y0, y1 + 1, step):
        c.rect(x0, y, x1, y, col)


def _slat_panel(c, x0, y0, x1, y1):
    c.d.rounded_rectangle([x0, y0, x1, y1], radius=5, fill=hx('#01040e'), outline=hx('#0a2650'))
    c.d.rounded_rectangle([x0 + 2, y0 + 2, x1 - 2, y1 - 2], radius=4, outline=hx('#061a3c'))


def slats(c, x0, y0, x1, y1, t, seed):
    """Lit slats with dim glitch patches drifting slowly downward."""
    rr = np.random.default_rng(seed)
    patches = [(rr.uniform(0, 1), rr.uniform(8, 18), rr.uniform(18, 30)) for _ in range(3)]
    span = y1 - y0
    for y in range(y0 + 5, y1 - 4, 4):
        dim = False
        for (p0, hgt, sp) in patches:
            py = y0 + ((p0 * span + sp * t) % span)
            if py <= y < py + hgt:
                dim = True
        c.rect(x0 + 4, y, x1 - 4, y + 1, '#0c2a5a')
        c.px(x1 - 4, y + 1, '#020818')
        if dim:
            for x in range(x0 + 4, x1 - 3):
                if (x * 7 + y * 3 + int(t * 10)) % 5 < 3:
                    c.px(x, y, '#040f26'); c.px(x, y + 1, '#040f26')
        c.px(x1 - 4, y, '#06183c')


def _tower(c):
    # main tower body with chamfered top-left corner
    c.poly([(138, 20), (156, 3), (276, 3), (276, 88), (266, 100), (266, 180), (138, 180)], '#010818')
    _grid(c, 140, 5, 275, 178, 3, '#030c26')
    r = np.random.default_rng(9)
    for _ in range(160):  # weathering blotches
        x, y = int(r.integers(140, 270)), int(r.integers(6, 175))
        c.rect(x, y, x + 2, y + 2, '#051636' if r.random() < .5 else '#00040c')
    c.line(138, 20, 156, 3, LINE)
    c.rect(156, 3, 276, 3, LINE)
    c.rect(276, 3, 276, 88, LINE)
    c.line(276, 88, 266, 100, LINE)
    c.rect(138, 20, 138, 180, LINE)
    c.rect(140, 5, 182, 7, '#04102c')
    for (x, y) in [(141, 24), (172, 24)]:
        c.box(x, y, x + 7, y + 7, '#0d3466')
    c.box(267, 7, 273, 13, LINE2)
    # vertical slatted panel
    _slat_panel(c, 145, 56, 176, 168)
    glyph(c, 151, 48, ['#.#.###.#.#.#', '##..#.#.##..#', '#.#.###.#.#.#'], '#0f3a70')
    c.rect(140, 37, 276, 38, '#0d2c5c')
    # hexagon logo
    hexp = [(205 + 16 * math.cos(math.radians(a + 90)), 39 + 16 * math.sin(math.radians(a + 90))) for a in range(0, 360, 60)]
    c.poly(hexp, '#020c22', LINE2)
    hexp2 = [(205 + 14 * math.cos(math.radians(a + 90)), 39 + 14 * math.sin(math.radians(a + 90))) for a in range(0, 360, 60)]
    c.poly(hexp2, None, LINE2)
    for (cx, cy) in [(201, 35), (209, 35), (205, 42)]:
        c.circle(cx, cy, 4, None, '#16508a')
    c.rect(180, 38, 189, 39, LINE2)
    c.rect(221, 37, 276, 38, LINE2)
    c.rect(221, 41, 276, 43, '#16508a')
    glyph(c, 218, 29, ['###.#.#.###.###.#.#', '#.#.###.#...#.#..#.', '###.#.#.###.###.###'], '#1a5a96', 1)
    c.rect(258, 29, 275, 34, '#1a5a96')
    # big "-05-"
    O = ['.#####.', '##...##', '#.....#', '#.....#', '#.....#', '#.....#', '#.....#', '#.....#', '#.....#', '#.....#', '##...##', '.#####.']
    S = ['.######', '##.....', '#......', '#......', '##.....', '.#####.', '.....##', '......#', '......#', '......#', '.....##', '######.']
    glyph(c, 218, 49, O, '#1b6aa6', 3) if False else None
    for (pat, x0) in [(O, 220), (S, 243)]:
        for j, row in enumerate(pat):
            for i, ch in enumerate(row):
                if ch == '#':
                    c.rect(x0 + i * 2 + 1, 49 + j * 2 + 1, x0 + i * 2 + 2, 49 + j * 2 + 2, '#1e74b4')
    c.rect(210, 61, 218, 62, '#1e74b4'); c.rect(210, 65, 218, 66, '#1e74b4')
    c.rect(262, 61, 271, 62, '#1e74b4'); c.rect(262, 65, 271, 66, '#1e74b4')
    c.box(262, 88, 266, 92, LINE2)
    # stepped diagonal structure with green lights
    left, right = [], []
    for i in range(9):
        y0, y1 = 100 + i * 10, 110 + i * 10
        xl = 248 - i * 9
        left += [(xl, y0), (xl - 9, y1)] if i % 2 else [(xl, y0), (xl, y1)]
        right += [(xl + 20, y0), (xl + 20, y1)]
    c.poly(left + right[::-1], '#01050c', LINE)
    for i in range(1, 9, 2):
        c.box(248 - i * 9 - 8, 104 + i * 10, 248 - i * 9 - 5, 107 + i * 10, '#0a2a58')
    for (cx, cy, rad) in [(270, 140, 12), (250, 166, 17)]:
        c.circle(cx, cy, rad, '#020a1e', LINE2)
        for y in range(cy - rad + 3, cy + rad - 2, 3):
            dx = int(math.sqrt(max(0, rad * rad - (y - cy) ** 2))) - 2
            c.rect(cx - dx, y, cx + dx, y, '#0a2a58')
    c.circle(240, 192, 20, '#020a1e', LINE)


def side_lights(c, t):
    """Small green window lights on the far-left and far-right structures."""
    for i, (x, y) in enumerate([(26, 204), (31, 205), (36, 204), (41, 206), (30, 210), (38, 211),
                                (332, 198), (337, 199), (343, 198), (350, 200), (356, 199), (340, 204), (352, 205)]):
        on = math.sin(t * 2.0 + i * 1.7) > -0.8
        c.rect(x, y, x + 1, y, '#3af04a' if on else '#0c4a16')


def green_dots(c, t):
    rr = np.random.default_rng(31)
    k = 0
    for j in range(40):
        q = rr.uniform(0, 1)
        y = int(102 + q * 86)
        xc = 256 - q * 78
        x = int(xc + rr.uniform(-6, 8))
        if True:
            wide = rr.random() < 0.3
            ph = rr.uniform(0, 6.28)
            on = math.sin(t * 3 + ph) > -0.6
            col = '#3af04a' if on else '#0c4a16'
            c.rect(x, y, x + (2 if wide else 0), y, col)
            k += 1


def _right_tower(c):
    c.poly([(318, 82), (334, 66), (360, 66), (360, 210), (318, 210)], '#03102a')
    _grid(c, 320, 70, 359, 208, 3, '#05122e')
    c.line(318, 82, 334, 66, LINE)
    c.rect(334, 66, 359, 66, LINE)
    c.rect(318, 82, 318, 210, LINE)
    c.rect(340, 80, 340, 210, '#0a2a58')
    _slat_panel(c, 324, 104, 344, 196)
    c.rect(351, 48, 352, 66, '#020818')
    c.rect(347, 56, 349, 66, '#020818')
    c.circle(358, 96, 8, None, LINE2)


def _far(c):
    # hazy distant structures on the left
    c.poly([(28, 140), (64, 138), (72, 148), (72, 175), (22, 175)], '#05163c')
    c.rect(30, 136, 60, 140, '#0a1f4c')
    c.rect(36, 132, 37, 138, '#05163c'); c.rect(46, 133, 47, 138, '#05163c')
    c.rect(84, 150, 118, 162, '#04122e')
    c.rect(104, 130, 105, 150, '#04122e'); c.rect(109, 138, 110, 150, '#04122e')
    c.poly([(98, 148), (104, 142), (112, 142), (116, 148)], '#04122e')
    c.rect(118, 150, 136, 152, '#08204a')
    for x in range(120, 137, 3):
        c.rect(x, 150, x, 175, '#06183c')
    c.rect(20, 196, 48, 216, '#030c22')
    c.rect(326, 192, 360, 210, '#030c22')
    # tall pylon
    for x in (86, 100):
        c.rect(x, 190, x, 285, '#04102a')
    for y in range(195, 285, 10):
        c.line(86, y, 100, y + 10, '#04102a')
        c.line(100, y, 86, y + 10, '#04102a')
    c.rect(80, 190, 106, 192, '#04102a')
    c.rect(76, 210, 110, 211, '#04102a')
    # water tower right-middle
    c.poly([(290, 175), (296, 168), (310, 168), (316, 175)], '#06183c')
    c.rect(290, 175, 316, 186, '#06183c')
    c.rect(292, 177, 314, 178, '#12807a')
    for x in (294, 312):
        c.rect(x, 186, x, 210, '#06183c')
    c.line(294, 190, 312, 205, '#06183c'); c.line(312, 190, 294, 205, '#06183c')
    c.rect(302, 160, 303, 168, '#06183c')
    # small cyan-lettered building
    c.rect(86, 150, 118, 162, '#041430')
    glyph(c, 93, 151, ['###.###.###', '#.#..#..#.#'], '#30c8a8')
    glyph(c, 88, 155, ['#.###.###.###', '.##.#.#.#.#.#'], '#30c8a8')
    # lattice behind (center)
    for x in range(204, 232, 6):
        c.rect(x, 190, x, 270, '#040e28')
    c.rect(200, 200, 270, 201, '#040e28')
    c.rect(200, 230, 270, 231, '#040e28')
    for x in (215, 230):
        for y in range(195, 285, 9):
            pass
    for y in range(190, 280, 10):
        c.line(108, y, 122, y + 10, '#040e28')
    for x in range(250, 290, 8):
        c.rect(x, 205, x, 270, '#040e28')


def _bridge(c):
    # long diagonal conveyor bridge seen from below-left: top deck + dark side + green-lit underside
    top = lambda x: 146 + x * 0.25
    for (xa, ya, xb, yb, w) in [(16, 168, 12, 322, 7), (54, 172, 30, 300, 5), (146, 192, 142, 292, 6),
                                 (236, 206, 200, 262, 5), (108, 184, 128, 272, 4), (300, 230, 318, 262, 4)]:
        for k in range(w):
            c.line(xa + k, ya, xb + k, yb, '#010510')
    c.poly([(0, 145), (360, 235), (360, 262), (0, 172)], '#01050f')
    for x in range(0, 360):
        y = int(top(x))
        c.px(x, y - 1, '#1a3c7c')
        c.rect(x, y, x, y + 5, '#05122e' if x % 3 else '#081a40')
        c.px(x, y + 6, '#12306a')
        if x % 5 == 0:
            c.rect(x, y + 7, x, y + 14, '#06132e')
    # green-tinted underside fading toward the sign
    for x in range(4, 352):
        y = int(top(x)) + 15
        f = max(0, 1 - abs(x - 250) / 190)
        for k in range(8):
            if (x + k) % 2 == 0:
                c.px(x, y + k, mix('#030c1a', '#24480c', f * (1 - k / 10)))
    glyph(c, 156, 179, ['###.###.###.###.#.#.#.#.#.#.#.#', '#...#...#.#.#.#.#.#.#.#.##..#.#', '###.##..###.###.#.#.##..##..#.#',
                        '..#.#...#...#...#.#.#.#.#.#.#.#', '###.###.#...#...###.#.#.#.#.###'], '#1e528e')
    glyph(c, 189, 186, ['###.###.###.###', '#.#.#.#.#...#..', '#.#.#.#.#.#.##.', '###.###.###.###'], '#1e528e')


def _hills(c):
    r = np.random.default_rng(4)
    for x in range(0, W):
        h = 252 + int(14 * max(0.0, min(1.0, (x - 60) / 30, (210 - x) / 30))) + int(6 * math.sin(x * 0.05) + 4 * math.sin(x * 0.13 + 1)) + int(r.integers(-2, 3))
        c.rect(x, h, x, 300, '#010614')
        if r.random() < 0.3:
            c.rect(x, h - int(r.integers(1, 6)), x, h, '#010614')
    for x in range(0, W, 2):
        y = 258 + int(5 * math.sin(x * 0.07)) + int(r.integers(0, 6))
        c.px(x, y, '#061a36')


def _lamp_posts(c):
    for (x0, y0, x1, y1) in [(22, 226, 36, 233), (82, 224, 64, 233), (166, 224, 182, 232), (348, 226, 360, 232)]:
        c.line(x0, y0 - 1, x1, y1 - 1, '#04122e')
    c.rect(40, 230, 41, 300, '#030c22')
    c.circle(41, 232, 3, None, '#0a2048')


def lamps(c, t):
    for i, (x0, y0, x1, y1) in enumerate([(22, 226, 36, 233), (82, 224, 64, 233), (166, 224, 182, 232), (348, 226, 360, 232)]):
        f = 0.7 if 0.7 <= t < 1.0 else 1.0
        c.line(x0, y0, x1, y1, mix('#1a4a7a', '#d8f4ff', f))
        c.line(x0, y0 + 1, x1, y1 + 1, mix('#123a6a', '#6ac8f0', f))


def _truck(c):
    """Box trailer + cab-over truck; coordinates measured from the source frame."""
    r = np.random.default_rng(5)
    # trailer
    c.rect(73, 283, 133, 330, '#091322')
    for _ in range(260):
        x, y = int(r.integers(74, 133)), int(r.integers(284, 330))
        c.px(x, y, '#0f1e32' if r.random() < .6 else '#060e1a')
    c.box(73, 283, 133, 330, '#1c3450')
    for x in range(77, 133, 7):
        c.rect(x, 285, x, 328, '#0a1626')
    c.circle(103, 306, 15, None, '#25466c')
    c.circle(103, 306, 13, None, '#16304e')
    c.d.arc([95, 296, 111, 312], 200, 340, fill=hx('#25466c'))
    c.rect(102, 300, 104, 316, '#25466c')
    c.line(95, 310, 111, 310, '#25466c')
    c.rect(99, 298, 101, 300, '#25466c'); c.rect(105, 298, 107, 300, '#25466c')
    c.rect(73, 330, 133, 332, '#04080e')
    # cab roof sign
    c.rect(132, 283, 169, 296, '#3a4a62')
    c.rect(134, 285, 167, 294, '#5a6c86')
    c.rect(134, 285, 150, 294, '#46607e')
    glyph(c, 152, 286, ['#.#.###.###', '#.#.#.#..#.', '###.###..#.', '#.#.#.#..#.'], '#1e5aa0')
    c.rect(137, 288, 147, 291, '#2a6ab0')
    # cab body (rounded) and windshield
    c.poly([(136, 299), (140, 296), (176, 296), (182, 300), (184, 334), (136, 334)], '#05070f')
    c.poly([(140, 299), (176, 299), (179, 316), (141, 316)], '#0a1222')
    c.poly([(158, 300), (175, 300), (177, 314), (164, 314)], '#162440')
    c.line(165, 301, 171, 313, '#24385c')
    c.rect(161, 316, 183, 318, '#8a1a1a')
    c.rect(161, 318, 183, 319, '#3a0c0c')
    c.rect(161, 327, 184, 329, '#0c0e18')
    # wheels
    c.circle(146, 331, 6, '#020308', '#0c1424')
    c.circle(146, 331, 2, '#0c1424', None)
    for x in (88, 124):
        c.circle(x, 332, 4, '#020308', '#0a1220')


def truck_lights(c, t):
    u = t % 1.43
    if u < 0.75:
        b = 1 - 0.75 * u / 0.75
    elif u < 1.0:
        b = 0.25 + 0.75 * (u - 0.75) / 0.25
    else:
        b = 1.0
    on = b > 0.6
    col = mix('#2a1606', '#ffb030', b)
    for x0 in (164, 178):
        for (dx, dy) in [(0, 0), (3, 0), (0, 3), (3, 3)]:
            c.rect(x0 + dx, 320 + dy, x0 + dx + 1, 321 + dy, col)
    if on:
        c.px(165, 321, '#fff0c0'); c.px(179, 321, '#fff0c0')
    c.rect(172, 329, 176, 330, '#3ae04a')


def _kiosk(c):
    c.rect(200, 262, 346, 330, '#010611')
    c.rect(198, 260, 348, 268, '#0c2c58')
    c.rect(198, 260, 348, 260, '#1a4a86')
    c.rect(294, 268, 296, 330, '#0a2a58')
    # signs
    c.rect(212, 276, 240, 290, '#06142e')
    c.box(212, 276, 240, 290, '#0e2c5c')
    c.circle(233, 283, 4, None, '#0e2c5c')
    c.rect(246, 276, 288, 290, '#12306a')
    c.rect(247, 277, 287, 282, '#1e52a0')
    glyph(c, 249, 278, ['#.#.###.#.#.###.#.#.###.###', '#.#.#...###.#.#.#.#..#..#..'], '#0a1a40')
    for x in range(247, 288, 2):
        c.px(x, 286, '#5a9af0')
    c.rect(292, 277, 304, 290, '#0e3a3a')
    c.box(292, 277, 304, 290, '#1a6a5a')
    c.circle(298, 283, 3, None, '#2a8a6a')
    # lit windows
    W1 = '#2ea894'
    for (x0, y0, x1, y1) in [(210, 294, 226, 310), (232, 294, 248, 310), (271, 294, 289, 310)]:
        c.rect(x0 - 1, y0 - 1, x1 + 1, y1 + 1, '#0a2a3a')
        c.rect(x0, y0, x1, y1, W1)
    c.rect(212, 296, 218, 300, '#2a8a9a'); c.rect(220, 304, 224, 308, '#1a5a6a')
    c.rect(236, 298, 246, 302, '#1a3a7a'); c.line(232, 294, 240, 302, '#e0fff8')
    glyph(c, 273, 296, ['#.#.#.#.#', '#########', '.#.#.#.#.', '#########', '..#...#..'], '#0a2a3a')
    c.rect(252, 294, 264, 322, '#0a2a3a')
    c.rect(253, 295, 263, 306, '#2aa89a')
    c.rect(253, 300, 263, 302, '#1a4ab0')
    c.rect(253, 308, 263, 321, '#2aa08e')
    for k in range(0, 14, 4):
        c.line(253 + k, 321, 263, 311 + k, '#c0fff4')
    # graffiti panel with cat
    c.rect(298, 270, 344, 326, '#050c22')
    r = np.random.default_rng(12)
    for _ in range(40):
        x, y = int(r.integers(300, 330)), int(r.integers(286, 322))
        c.rect(x, y, x + int(r.integers(0, 3)), y, ['#1a3a7a', '#2a5a9a', '#1a5a5a'][int(r.integers(0, 3))])
    c.box(332, 280, 344, 296, '#1a3a6a')
    c.poly([(332, 280), (334, 274), (337, 280)], None, '#1a3a6a')
    c.poly([(339, 280), (342, 274), (344, 280)], None, '#1a3a6a')
    c.rect(315, 302, 317, 310, '#2a7ad0')
    c.rect(320, 302, 322, 312, '#4a9a5a')
    c.rect(328, 300, 338, 326, '#0a1a3a')
    c.box(328, 300, 338, 326, '#123264')
    # small box on roof
    c.rect(318, 250, 332, 260, '#0a2a1a')
    c.box(318, 250, 332, 260, '#2a6a3a')
    c.rect(220, 248, 250, 260, '#06142c')
    c.rect(252, 252, 300, 260, '#06142c')


def kiosk_light(c, t):
    on = ((t + 0.0) % 0.93) < 0.38
    c.rect(324, 252, 328, 257, '#f0fff0' if on else '#3a5a3a')


def _person(c):
    c.rect(34, 300, 40, 322, '#04122e')
    c.rect(35, 296, 39, 300, '#06183c')
    c.rect(34, 306, 44, 309, '#1a3a7a')
    c.rect(35, 322, 36, 326, '#020a1c'); c.rect(38, 322, 39, 326, '#020a1c')
    c.rect(29, 300, 33, 318, '#062018')


def phone(c, t):
    c.rect(37, 291, 44, 298, '#4ac0f0')
    c.rect(38, 292, 43, 297, '#c0f0ff')
    c.rect(39, 294, 42, 294, '#2a6a9a')


SIGN_L = [
    ['################', '#..............#', '#.############.#', '#.#..........#.#', '#.#.######...#.#', '#.#.#....#...#.#',
     '###.#.##.#####.#', '....#.##.......#', '....#.##########', '....#.#.........', '....#.#.........',
     '....#.#.........', '....#.#.........', '....###.........'],
    ['################', '#..............#', '#.####.##.####.#', '#.#..#.##.#..#.#', '#.#..#.##.#..#.#', '#.#..#.##.#..#.#',
     '#.#..#.##.#..#.#', '#.#..#.##.#..#.#', '#.#..####.#..#.#', '#.#.......#..#.#', '#.#########..#.#',
     '#............#.#', '##############.#', '..............##'],
    ['################', '#..............#', '#.####.######.#.', '#.#..#.#....#.#.', '#.####.#.##.#.#.', '#......#.##.#.#.',
     '#.######.##.#.##', '#.#......##.#..#', '#.#.######..##.#', '#.#.#.....#..#.#', '#.###.###.####.#',
     '#.....#.#......#', '#######.########', '................'],
]


def neon(c, t):
    col = GRN
    col2 = '#70b000'
    cy = 208
    # faint dark backing glow behind the lettering
    c.poly([(214, 192), (312, 204), (312, 234), (214, 226)], '#0c0a05')
    # circle emblem: double ring
    c.circle(232, cy, 17, None, col)
    c.circle(232, cy, 16, None, col)
    c.circle(232, cy, 14, '#1a1806', col2)
    # leaf / drop mark: outline left, striped right half
    c.poly([(232, cy - 13), (239, cy - 4), (239, cy + 5), (232, cy + 9), (225, cy + 5), (225, cy - 4)], None, col)
    for y in range(cy - 10, cy + 8, 2):
        c.rect(233, y, 238, y, col)
    c.rect(230, cy - 8, 231, cy + 6, col)
    c.circle(228, cy + 12, 2, None, col)
    # slanted hollow lettering (follows the bridge slope)
    sub = Canvas(70, 40, (0, 0, 0))
    for k, g in enumerate(SIGN_L):
        glyph(sub, k * 18, 2, g, col)
    sub.rect(0, 20, 54, 20, col2)
    glyph(sub, 0, 24, ['##.#.#.###.#.#.#.#.#.#..#.#.#.#.##', '#..##..#.#.##..#.#.#.#..#.#.###.#.'], col2)
    m = np.asarray(sub.im)
    a = np.asarray(c.im).copy()
    x0, y0 = 252, 196
    for x in range(m.shape[1]):
        dy = int((x) * 0.12)
        colm = m[:, x]
        on = colm.sum(1) > 0
        ys = np.nonzero(on)[0]
        for yy in ys:
            Y, X = y0 + yy + dy, x0 + x
            if 0 <= Y < H and 0 <= X < W:
                a[Y, X] = colm[yy]
    c.im = Image.fromarray(a); c.d = ImageDraw.Draw(c.im)
    c.circle(310, 198, 2, None, col)
    # rolling scanline shimmer across the neon
    a = np.asarray(c.im).copy()
    reg = a[188:240, 212:316].astype(np.int16)
    lit = reg[..., 1] > 120
    rows = (np.arange(188, 240) + int(t * 15)) % 3 == 0
    mm = lit & rows[:, None]
    reg[mm] = (reg[mm] * 0.78).astype(np.int16)
    a[188:240, 212:316] = reg.astype(np.uint8)
    c.im = Image.fromarray(a); c.d = ImageDraw.Draw(c.im)


class Scene3:
    def __init__(s):
        c = Canvas(W, H, '#001437')
        vgrad(c, 0, 0, W - 1, 170, '#000c30', '#011a48')
        vgrad(c, 0, 171, W - 1, 300, '#01163e', '#021a46')
        _far(c)
        _right_tower(c)
        _tower(c)
        _hills(c)
        _bridge(c)
        _lamp_posts(c)
        lay = Canvas(W, H, (255, 0, 255))
        _truck(lay)
        key = np.all(np.asarray(lay.im) == [255, 0, 255], axis=2)
        a0 = np.asarray(c.im).copy(); al = np.asarray(lay.im)
        TDY = 0
        ys, xs = np.nonzero(~key)
        ok = ys + TDY < H
        a0[ys[ok] + TDY, xs[ok]] = al[ys[ok], xs[ok]]
        c.im = Image.fromarray(a0); c.d = ImageDraw.Draw(c.im)
        _kiosk(c)
        _person(c)
        # wet street
        c.rect(0, 335, W - 1, H - 1, '#00040e')
        for x in range(0, W, 3):
            c.rect(x, 335, x + 1, 335, '#0a2450')
        for y in range(328, H):
            for x in range(0, 70):
                if (x + y) % 3 == 0:
                    c.px(x, y, '#001a3a')
        c.rect(0, 312, 74, 326, '#01030c')
        for x in range(0, 74, 4):
            c.rect(x, 312, x, 326, '#0a2450')
        c.rect(0, 312, 74, 312, '#0c2450')
        for x in range(0, 72, 6):
            c.rect(x, 304, x, 326, '#03091c')
        c.rect(0, 304, 72, 305, '#0a1c3c')
        c.rect(0, 316, 72, 316, '#06122a')
        s.base = c
        s.rain = ShortRain(W, H, 95, 21, 4, 14, (240, 330), (0.12, 0.3), 0, 330)
        r = np.random.default_rng(3)
        s.fog = r.uniform(0, 1, (6, 4))

    def frame(s, t):
        c = s.base.copy()
        green_dots(c, t)
        side_lights(c, t)
        slats(c, 145, 56, 176, 168, t, 1)
        slats(c, 324, 104, 344, 196, t, 2)
        lamps(c, t)
        truck_lights(c, t)
        kiosk_light(c, t)
        phone(c, t)
        neon(c, t)
        # blinking aviation lights
        for i, (x, y) in enumerate([(185, 2), (203, 2), (220, 2), (243, 2), (257, 2), (337, 65), (346, 65), (355, 65)]):
            c.rect(x, y, x + 1, y + 1, '#ff2a2a')
        a = c.arr()
        # reflections on the wet street (mirror of lit kiosk/truck, rippled)
        for y in range(336, H):
            sy = 2 * 333 - y
            off = int(round(1.5 * math.sin(t * 3 + y * 1.3)))
            row = np.roll(a[sy], off, axis=0)
            f = 0.55 * (1 - (y - 336) / (H - 336))
            a[y] = a[y] * (1 - f) + row * f
        # drifting fog banks
        yy, xx = np.mgrid[0:H, 0:W]
        fog = np.zeros((H, W), np.float32)
        for (cx, cy, rx, ry, sp) in [(275, 150, 40, 16, 6), (200, 120, 40, 12, 3)]:
            x = (cx + sp * t) % (W + 120) - 60
            fog += np.exp(-(((xx - x) / rx) ** 2 + ((yy - cy) / ry) ** 2))
        a += fog[..., None] * np.array([8, 22, 50], np.float32) * 0.35
        s.rain.draw(a, t, '#4a88c8', 0.5)
        return a
