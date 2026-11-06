"""Scene 2: night ramen shop facade with animated neon signage."""
import math
import numpy as np
from lib import Canvas, hx, mix, glyph, vgrad

W, H = 360, 341
RED, RED2, CREAM = '#ff0a0a', '#d20000', '#f4e6cc'
YEL, YEL2 = '#ffd21a', '#e8a010'

# small invented glyphs (5x5) for signage text
G = {
    'a': ['####.', '#..#.', '####.', '#..#.', '####.'],
    'b': ['.#...', '####.', '..#..', '.#.#.', '#...#'],
    'c': ['#.#.#', '####.', '#.#.#', '#.#..', '#.#.#'],
    'd': ['.#...', '####.', '.#.#.', '#..#.', '#.##.'],
    'e': ['#.##.', '.#..#', '#..#.', '#.#..', '#####'],
    'f': ['####.', '#..#.', '.##..', '...#.', '###..'],
    'g': ['####.', '#....', '###.#', '#..#.', '#.#.#'],
    'h': ['..#..', '..#..', '..#..', '.....', '..#..'],
    'i': ['#.#.#', '###..', '..#.#', '#.###', '#...#'],
    'j': ['##.##', '#..#.', '##.##', '.#..#', '##.##'],
    'k': ['###.#', '#.#..', '###.#', '#....', '#.###'],
}
BIG1 = ['########..#######', '#......#..#.....#', '#.####.#..#.###.#', '#.#..#.####.#.#.#',
        '###..#......#.###', '.....#.######....', '.....#.#..........', '######.#..........',
        '#......#..........', '#.#######.........', '#.#...............', '###...............']
BIG2 = ['#############', '#...........#', '#############', '.............', '.............',
        '.....########', '.....#......#', '.....########', '.............', '.............',
        '#############', '#...........#', '#############']


def glyph7(c, x, y, rows, col):
    """5x5 glyph stretched to 7x7 (nearest) for the larger shop lettering."""
    for j in range(7):
        for i in range(7):
            if rows[j * 5 // 7][i * 5 // 7] == '#':
                c.px(x + i, y + j, col)


def text(c, x, y, s, col, gap=2):
    for ch in s:
        glyph(c, x, y, G[ch], col)
        x += 5 + gap


def _bg(c):
    vgrad(c, 0, 0, W - 1, H - 1, '#00021a', '#010a2a')
    r = np.random.default_rng(2)
    # distant blue-lit buildings at both sides
    c.rect(0, 70, 22, 340, '#001028')
    c.rect(2, 120, 20, 340, '#00142c')
    for y in range(125, 300, 6):
        c.rect(4, y, 18, y + 1, '#08184a')
    c.rect(300, 60, 359, 340, '#020106')
    c.poly([(290, 175), (359, 165), (359, 200), (300, 205)], '#0b2466')
    c.rect(339, 150, 352, 340, '#081e4c')
    c.rect(341, 150, 343, 340, '#123a7a')
    for y in range(160, 330, 14):
        c.rect(336, y, 355, y + 1, '#0a2a66')
    # main building mass
    c.rect(22, 8, 338, 336, '#030104')
    c.rect(330, 100, 340, 336, '#030104')
    # subtle panel texture + warm red spill near the neon
    for _ in range(900):
        x, y = int(r.integers(22, 338)), int(r.integers(8, 336))
        d = math.hypot(x - 110, y - 100)
        col = mix('#050206', '#1a0404', max(0, 1 - d / 140))
        c.rect(x, y, x + int(r.integers(1, 6)), y, col)
    for y in range(70, 150, 9):
        c.rect(24, y, 100, y, '#0a050c')
    c.poly([(20, 55), (100, 52), (100, 70), (12, 74)], '#0c0710')
    c.poly([(8, 70), (60, 66), (60, 82), (8, 86)], '#09060c')
    # open night sky top-right and top-left, with dark rooftop clutter
    sky = Canvas(W, H, (0, 0, 0)); vgrad(sky, 0, 0, W - 1, 120, '#00021c', '#020c34')
    c.im.paste(sky.im.crop((290, 0, 360, 88)), (290, 0))
    c.im.paste(sky.im.crop((0, 0, 44, 50)), (0, 0))
    c.rect(296, 36, 350, 37, '#040a24')
    for x in range(298, 350, 4):
        c.rect(x, 37, x, 48, '#040a24')
    c.rect(296, 48, 350, 50, '#040a24')
    c.rect(318, 10, 319, 88, '#030820')
    c.rect(330, 22, 352, 34, '#040a24')
    c.rect(290, 60, 360, 88, '#050b26')
    c.poly([(286, 66), (300, 58), (344, 58), (360, 52), (360, 60), (346, 66)], '#03081c')
    c.rect(24, 30, 44, 50, '#040818')
    c.poly([(0, 44), (30, 36), (50, 40), (50, 50), (0, 54)], '#05081a')
    # right pagoda roof eave
    c.poly([(205, 86), (320, 90), (350, 80), (358, 78), (356, 86), (340, 102), (336, 112), (205, 112)], '#0a0710')
    c.poly([(318, 90), (350, 80), (358, 77), (357, 81), (340, 92)], '#1a1430')
    for x in range(210, 338, 5):
        c.rect(x, 100, x + 2, 101, '#120c18')
    # upper floor: red lit lattice windows
    c.rect(104, 20, 202, 52, '#2a0606')
    for i, x0 in enumerate((106, 140, 172)):
        c.rect(x0, 23, x0 + 28, 50, '#541410')
        for gx in range(x0, x0 + 29, 5):
            c.rect(gx, 23, gx, 50, '#4a0a08')
        for gy in range(23, 51, 5):
            c.rect(x0, gy, x0 + 28, gy, '#4a0a08')
        for _ in range(6):
            px, py = x0 + 2 + int(r.integers(0, 5)) * 5, 25 + int(r.integers(0, 5)) * 5
            c.rect(px, py, px + 2, py + 2, '#7a2620')
        c.rect(x0 + 2, 23, x0 + 26, 26, '#140303')
        for k in range(x0 + 3, x0 + 26, 7):
            c.rect(k, 23, k + 3, 28, '#140303')
    c.rect(104, 52, 202, 54, '#3a0808')
    for x in range(106, 202, 3):
        c.rect(x, 55, x, 64, '#5a0c0a')
    c.rect(104, 64, 202, 65, '#3a0808')
    # AC unit and balcony at upper left
    c.box(56, 16, 84, 36, '#2a2224')
    c.rect(58, 18, 82, 34, '#0d0a0e')
    for y in range(20, 34, 3):
        c.rect(60, y, 74, y, '#1c1618')
    c.rect(20, 46, 115, 47, '#0e1a40')
    for x in range(22, 115, 4):
        c.rect(x, 47, x, 54, '#0c1638')
    c.rect(17, 30, 18, 60, '#0a0a12')
    # window lattice upper right (dark blue)
    c.rect(214, 14, 240, 54, '#0a0a1c')
    for x in range(216, 240, 6):
        c.rect(x, 16, x, 52, '#121a3a')
    c.rect(300, 100, 330, 112, '#0a0d24')
    for x in range(300, 331, 4):
        c.rect(x, 100, x, 112, '#121a40')
    # red pole near banner
    c.rect(232, 55, 234, 100, '#3a0606')
    c.rect(226, 75, 240, 76, '#2a0404')
    # roof under neon sign
    c.poly([(30, 138), (300, 138), (330, 148), (346, 144), (340, 152), (6, 152), (0, 146), (14, 148)], '#0c0912')
    c.rect(12, 150, 318, 160, '#050307')
    for x in range(14, 316, 6):
        c.rect(x, 151, x + 2, 152, '#140d18')
    # carved wood band
    c.rect(48, 162, 182, 188, '#140707')
    for (x0, pat) in [(52, 0), (75, 1), (95, 2), (152, 3), (163, 4)]:
        rr = np.random.default_rng(pat + 10)
        for yy in range(170, 186):
            for xx in range(x0, x0 + 16):
                if rr.random() < 0.55:
                    c.px(xx, yy, '#7a2e1c' if rr.random() < .6 else '#a8502a')
    for (x0, y0, x1, y1) in [(51, 167, 72, 168), (78, 165, 95, 166), (140, 166, 168, 167), (170, 167, 180, 168)]:
        c.rect(x0, y0, x1, y1, '#8a2a1c')
    for rad in (6, 10, 14, 18):
        c.d.arc([128 - rad, 168 - rad, 128 + rad, 168 + rad], 20, 160, fill=hx('#9a2418'))
    c.poly([(150, 186), (168, 172), (182, 172), (182, 186)], '#7a3a1a')
    c.poly([(154, 186), (168, 175), (176, 175), (176, 186)], '#5a2410')
    # right middle: dark storage and dim shop sign
    c.rect(190, 162, 300, 188, '#040205')
    for x in range(254, 300, 7):
        c.rect(x, 190, x + 3, 196, '#3a3a10')
    # blue awning band with text area
    c.poly([(16, 196), (330, 196), (345, 205), (345, 214), (8, 214), (8, 205)], '#070d22')
    c.rect(8, 212, 345, 214, '#0c1a36')
    c.rect(20, 196, 330, 197, '#0c1a36')
    # awning: bold brown stripes, slanted on the canopy then hanging straight
    c.rect(30, 216, 192, 250, '#0a0604')
    for x0 in range(34, 186, 23):
        c.poly([(x0 + 8, 217), (x0 + 19, 217), (x0 + 11, 233), (x0, 233)], '#4a2c12')
        c.rect(x0, 233, x0 + 10, 250, '#5a3816')
        c.rect(x0, 233, x0 + 10, 234, '#6e4618')
        rr2 = np.random.default_rng(x0)
        for _ in range(12):
            px, py = x0 + int(rr2.integers(0, 10)), 220 + int(rr2.integers(0, 29))
            if py >= 233 or rr2.random() < .4:
                c.rect(px, py, px + 1, py + 1, '#7a5020' if rr2.random() < .5 else '#3a2208')
    # shop front frame
    c.rect(40, 248, 188, 306, '#080503')
    # shoji lattice windows (warm, dim)
    for (x0, x1) in [(48, 92), (140, 182)]:
        c.rect(x0, 252, x1, 300, '#2e2418')
        for gx in range(x0, x1 + 1, 5):
            c.rect(gx, 252, gx, 300, '#120c08')
        for gy in range(252, 301, 5):
            c.rect(x0, gy, x1, gy, '#120c08')
        rr = np.random.default_rng(x0)
        for _ in range(28):
            px = x0 + 1 + int(rr.integers(0, (x1 - x0) // 5)) * 5
            py = 253 + int(rr.integers(0, 9)) * 5
            c.rect(px, py, px + 3, py + 3, ['#7a5a32', '#946a36', '#5a4c42'][int(rr.random() * 3)])
        c.rect(x0, 285, x1, 300, '#0e0a08')
        c.rect(x0, 286, x1, 286, '#4a4440')
        for gx in range(x0 + 2, x1, 5):
            c.rect(gx, 286, gx, 299, '#3a3430')
    # counter and stools
    c.rect(40, 302, 190, 305, '#3a1a0c')
    c.rect(40, 302, 190, 302, '#5a2a12')
    for (x0, x1) in [(48, 78), (110, 136), (142, 166), (212, 242)]:
        c.rect(x0, 311, x1, 313, '#4a1c0c')
        c.rect(x0 + 1, 311, x1 - 1, 311, '#6a2a12')
    # door with emblem
    c.rect(196, 250, 252, 324, '#010818')
    c.rect(222, 252, 223, 322, '#030818')
    c.circle(220, 284, 26, None, '#173a66')
    c.box(209, 270, 231, 278, '#173a66')
    c.line(205, 285, 235, 285, '#173a66')
    c.line(210, 288, 214, 300, '#173a66')
    c.line(230, 288, 226, 300, '#173a66')
    c.rect(219, 285, 220, 302, '#173a66')
    c.rect(222, 262, 223, 268, '#173a66')
    c.rect(200, 316, 248, 318, '#0a1650')
    c.rect(204, 320, 244, 322, '#0a1650')
    c.rect(192, 250, 194, 330, '#4a2a10')
    c.rect(256, 230, 258, 330, '#2a1a0a')
    # right side clutter: menu board, bike, cat
    c.poly([(262, 290), (292, 290), (284, 330), (256, 330)], '#130a08')
    c.box(262, 290, 292, 295, '#4a2a1a')
    glyph(c, 266, 298, ['########', '.......#', '.#####.#', '.#......', '.######.', '......#.', '#######.'], '#5a3020', 2)
    c.circle(318, 318, 9, None, '#1c1c2c')
    c.circle(338, 318, 9, None, '#1c1c2c')
    c.line(318, 318, 330, 300, '#1c1c2c')
    c.line(330, 300, 338, 318, '#1c1c2c')
    c.rect(300, 270, 330, 280, '#0c0c18')
    c.box(330, 266, 346, 296, '#1c1c2c')
    c.rect(287, 252, 310, 290, '#0a0c22')
    c.box(287, 252, 310, 290, '#0e1640')
    # street glow line
    for x in range(0, W):
        f = max(0, 1 - abs(x - 120) / 160)
        c.rect(x, 333, x, 334, mix('#0a1a10', '#8a9a20', f))
        c.rect(x, 335, x, 340, '#020208')


def _sign_static(c):
    # pill outline to the right of the circle
    c.d.rounded_rectangle([96, 70, 216, 137], radius=33, outline=hx(RED), width=2)
    c.rect(118, 72, 200, 135, '#0c0101')
    for x in range(120, 200, 5):
        c.rect(x, 72, x, 135, '#120202')
    for y in (91, 123):
        c.rect(118, y, 212, y + 1, '#c00808')
    c.rect(120, 70, 200, 71, RED)
    c.rect(120, 136, 200, 137, RED)
    # big outlined glyphs (hollow double-stroke neon lettering), drawn at 2x
    g1 = ['#########.#######',
          '#.......#.#.....#',
          '#.#####.#.#.###.#',
          '#.#...#.###.#.#.#',
          '###...#.....#.###',
          '......#.#####....',
          '......#.#........',
          '#######.#........',
          '#.......#........',
          '#.#######........',
          '#.#..............',
          '#.#######........',
          '#.......#........',
          '#########........']
    g2 = ['##############',
          '#............#',
          '##############',
          '..............',
          '..............',
          '......########',
          '......#......#',
          '......########',
          '..............',
          '..............',
          '##############',
          '#............#',
          '##############']
    glyph(c, 126, 79, g1, CREAM, 2)
    glyph(c, 170, 79, g2, CREAM, 2)
    for i, ch in enumerate('cdefg'):
        glyph7(c, 115 + i * 12, 126, G[ch], CREAM)


def _circle_base(c, on=1.0):
    col = mix('#3a0000', RED, on)
    c.circle(82, 99, 38, col, None)
    rim = mix('#4a1010', CREAM, on)
    # dotted rim
    for a in range(0, 360, 3):
        x = 82 + 38 * math.cos(math.radians(a)); y = 99 + 38 * math.sin(math.radians(a))
        c.px(round(x), round(y), rim)
        x = 82 + 37 * math.cos(math.radians(a + 1.5)); y = 99 + 37 * math.sin(math.radians(a + 1.5))
        c.px(round(x), round(y), rim)


def _bowl(c, col, part=1.0):
    pts = [((60, 104), (102, 104)), ((58, 106), (104, 106)), ((58, 106), (65, 104)),
           ((104, 106), (97, 104)), ((62, 107), (70, 131)), ((100, 107), (92, 131)),
           ((70, 131), (92, 131)), ((80, 104), (80, 131)), ((83, 104), (83, 131)),
           ((80, 104), (83, 104)), ((86, 110), (89, 128))]
    n = max(0, min(len(pts), int(round(part * len(pts)))))
    for (a, b) in pts[:n]:
        c.line(a[0], a[1], b[0], b[1], col)


def _rings(c, col, col2, prog=1.0):
    for (cx, cy, rs) in [(70, 82, (9, 6, 3)), (91, 86, (6, 3))]:
        for k, rad in enumerate(rs):
            if prog * 3 >= k:
                c.circle(cx, cy, rad, None, col if k % 2 == 0 else col2)
        c.px(cx, cy, col)


# per-frame bowl state measured from the source loop: 0 rest, -1 lifted 1px, None hidden, +n dropped n px
_BOWL = {}
for f0, f1, v in [(0, 9, 0), (10, 14, -1), (15, 16, None), (17, 17, 6), (18, 18, 4), (19, 19, 6), (20, 20, 1),
                  (21, 22, 9), (23, 23, 11), (24, 24, 6), (25, 28, -1), (29, 35, 0), (36, 38, -1), (39, 39, None),
                  (40, 42, -1), (43, 43, 1), (44, 48, 0), (49, 51, -1), (52, 52, 4), (53, 53, 9), (54, 54, 6),
                  (55, 61, 0), (62, 64, -1), (65, 66, None), (67, 67, -1), (68, 73, 0), (74, 78, -1), (79, 80, None),
                  (81, 86, 0), (87, 89, -1), (90, 90, None)]:
    for f in range(f0, f1 + 1):
        _BOWL[f] = v


def _bowl_at(c, col, dy):
    sub = Canvas(W, H, (0, 0, 0))
    _bowl(sub, col)
    m = np.asarray(sub.im)
    a = np.asarray(c.im).copy()
    on = m.sum(2) > 0
    ys, xs = np.nonzero(on)
    ys2 = np.clip(ys + dy, 0, H - 1)
    # keep the dropped bowl inside the round sign
    keep = (xs - 82) ** 2 + (ys2 - 99) ** 2 <= 37 ** 2
    a[ys2[keep], xs[keep]] = m[ys[keep], xs[keep]]
    from PIL import Image, ImageDraw
    c.im = Image.fromarray(a); c.d = ImageDraw.Draw(c.im)


def icon(c, t):
    """3-second neon animation cycle inside the round sign."""
    u = t % 3.03
    _circle_base(c, 1.0)
    st = _BOWL.get(int(round(u * 30)) % 91, 0)
    if st is not None:
        _bowl_at(c, CREAM, st)
    if 0.3 < u < 0.78:  # noodles lifted out of the bowl
        p = (u - 0.3) / 0.48
        for i, x in enumerate(range(66, 84, 2)):
            drop = max(0.0, p - 0.35) * (1.2 + 0.9 * abs(math.sin(i * 2.3)))
            rise = min(1.0, p / 0.3)
            top = 103 - int((40 - 4 * (i % 3)) * rise * max(0, 1 - drop))
            if top < 103:
                c.rect(x, top, x, 103, YEL if i % 2 == 0 else YEL2)

    if 0.87 < u < 1.55:  # bubbles rise and pop
        p = (u - 0.87) / 0.68
        rr = np.random.default_rng(4)
        for k in range(9):
            bx = 62 + int(rr.integers(0, 34)); by0 = 92 - int(rr.integers(0, 12))
            d0 = rr.uniform(0, .45)
            q = (p - d0) / 0.55
            if 0 < q < 1:
                rad = 2 + int(6 * q)
                by = by0 - int(12 * q)
                if q < 0.85:
                    c.circle(bx, by, rad, None, YEL if k % 2 else YEL2)
                else:
                    for a in range(0, 360, 60):
                        c.px(bx + int((rad + 2) * math.cos(math.radians(a))), by + int((rad + 2) * math.sin(math.radians(a))), YEL)
    if u >= 1.7:  # fish-cake rings spiral in
        _rings(c, YEL, YEL2, min(1, (u - 1.7) / 0.15))
    if u >= 2.5:  # chopsticks slide in
        p = min(1, (u - 2.5) / 0.4)
        L = int(34 * p)
        for (x0, y0) in [(108, 62), (112, 66)]:
            c.line(x0, y0, x0 - int(L * 0.62), y0 + int(L * 0.78), CREAM)
        if p >= 1 and u > 2.92:
            c.line(84, 92, 88, 104, YEL)


# banner food icons (cream outline sprites)
ICONS = {
    'box': ['..#.#.#..', '.#######.', '#########', '#.......#', '#.#####.#', '#..###..#', '#.......#', '#########'],
    'spoon': ['.......###', '......####', '.....##...', '....##....', '####......', '###.......'],
    'bowl': ['...#####...', '..#.#.#.#..', '.#########.', '###########', '#.........#', '.#.......#.', '..#######..'],
    'sushi': ['....###....', '..#######..', '.#.#.#.#.#.', '###########', '...........', '###########'],
    'cup': ['..###..', '.#####.', '#######', '#.....#', '.#...#.', '.#.#.#.', '..###..'],
    'fork': ['#.#..........', '###########..', '#.#..........'],
    'wave': ['.##...##...##', '#..#.#..#.#..', '....#....#...'],
    'bar': ['#########', '.........', '#########', '.........', '#########'],
}
def _banner_seq():
    """Deterministic stream of food icons entering the banner at varied heights."""
    rr = np.random.default_rng(17)
    names = ['box', 'spoon', 'bowl', 'bar', 'sushi', 'wave', 'cup', 'fork']
    seq, t, lane = [], -1.0, 0
    lanes = [4, 22, 40, 58, 76]
    while t < 3.6:
        name = names[int(rr.integers(0, len(names)))]
        y = lanes[lane % 5] + int(rr.integers(-3, 4))
        seq.append((name, y, t, int(name in ('wave', 'bar') and rr.random() < 0.7)))
        lane += int(rr.integers(2, 4))
        t += float(rr.uniform(0.16, 0.26))
    return seq


BANNER_SEQ = _banner_seq()


def banner(c, t):
    x0, x1, y0, y1 = 246, 283, 0, 96
    c.rect(x0, y0, x1, y1, '#e40808')
    for y in range(y0, y1 + 1, 2):
        c.rect(x0, y, x1, y, '#b00404')
    c.rect(x0, y1 - 1, x1, y1, '#c40000')
    sub = Canvas(x1 - x0 + 1, y1 - y0 + 1, (0, 0, 0))
    for (name, y, start, alt) in BANNER_SEQ:
        dt = t - start
        if dt < -1:
            continue
        x = int(40 - (dt + 0.45) * 60)
        g = ICONS[name]
        if x < -20 or x > 40:
            continue
        glyph(sub, x, y, g, CREAM if not alt else YEL, 2 if name in ('bowl', 'box', 'cup') else 2)
    m = np.asarray(sub.im)
    a = np.asarray(c.im).copy()
    on = m.sum(2) > 0
    reg = a[y0:y1 + 1, x0:x1 + 1]
    reg[on] = m[on]
    # scanline darkening over icons too
    reg[::2][on[::2]] = (reg[::2][on[::2]] * 0.85).astype(np.uint8)
    a[y0:y1 + 1, x0:x1 + 1] = reg
    from PIL import Image, ImageDraw
    c.im = Image.fromarray(a); c.d = ImageDraw.Draw(c.im)
    c.rect(x0 - 2, y0, x0 - 1, y1 + 1, '#2a0000')


def yellow_bars(c, t):
    """Mostly-lit bar sign; a single bar changes every few frames (like the source)."""
    base = [20, 20, 14, 20, 20, 9, 20, 20, 20, 16, 20, 20]
    dimb = [False, False, True, False, False, True, False, False, False, False, True, False]
    k = int(t * 10)
    rr = np.random.default_rng(k)
    i = int(rr.integers(0, 12))
    h = list(base); dm = list(dimb)
    h[i] = int(rr.integers(6, 21)); dm[i] = not dm[i]
    for j, x in enumerate(range(253, 288, 3)):
        c.rect(x, 142, x + 1, 161, '#2a2a06')
        c.rect(x, 162 - h[j], x + 1, 161, '#8a8410' if dm[j] else '#f0e810')


TYPE = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']
TX = [47, 72, 97, 122, 147, 172, 197, 222]


TYPE_T = [0.2, 0.4, 0.6, 0.8, 1.0, 1.2, 1.5, 1.7]


def type_row(c, t):
    f = int(round(t * 30))
    n = sum(1 for tt in TYPE_T if t >= tt - 1e-6)
    col = '#28fce4'
    if f >= 62:
        ph = (f - 62) % 11
        col = '#1e5ae8' if ph < 3 else ('#dce1ff' if ph < 6 else '#28fce4')
    for i in range(n):
        glyph7(c, TX[i], 198, G[TYPE[i]], col)


def lanterns(c, t):
    for i, (x, y) in enumerate([(201, 228), (233, 230)]):
        f = 0.97 + 0.03 * math.sin(t * 2.2 + i * 2)
        body = mix('#400000', '#ff1414', f)
        c.rect(x + 2, y, x + 12, y + 20, body)
        c.rect(x, y + 3, x + 14, y + 17, body)
        for xx in range(x + 2, x + 14, 3):
            c.rect(xx, y + 2, xx, y + 18, mix('#300000', '#b00000', f))
        c.rect(x, y + 9, x + 14, y + 10, mix('#300000', '#a00000', f))
        c.rect(x + 4, y - 2, x + 10, y - 1, '#2a0a0a')
        c.rect(x + 4, y + 21, x + 10, y + 22, '#2a0a0a')


def kitchen(c, t):
    Y, Y2, Y3, D = '#fff21a', '#d8c000', '#9a8400', '#2a2408'
    # ragged lit opening (drapery edges top and sides)
    pts = [(78, 262), (82, 258), (86, 260), (90, 255), (96, 257), (100, 252), (106, 254), (112, 253),
           (118, 256), (122, 252), (126, 253), (128, 248), (131, 252), (134, 247), (138, 251), (141, 250),
           (141, 296), (138, 300), (78, 300)]
    c.poly(pts, Y)
    # dark notches along the top drapery
    for (x, y) in [(84, 258), (92, 256), (104, 254), (115, 255), (130, 251), (137, 250)]:
        c.rect(x, y, x + 2, y + 3, '#2a1c06')
    c.rect(78, 262, 80, 300, '#2a1c06')
    # pale lattice inside the light
    for gy in range(262, 292, 6):
        c.rect(98, gy, 114, gy, Y2)
    for gx in (102, 108):
        c.rect(gx, 258, gx, 292, Y2)
    # left shelves with dark jars
    for y in (264, 272, 280):
        c.rect(80, y, 94, y + 1, Y3)
    for x in range(81, 94, 4):
        c.rect(x, 266, x + 2, 271, D); c.rect(x + 1, 274, x + 2, 279, D)
    c.rect(80, 284, 92, 300, D)
    for x in range(82, 92, 3):
        c.rect(x, 286, x + 1, 296, '#4a4010')
    # steam above the pot
    for k in range(3):
        sy = 278 - int((t * 14 + k * 6) % 16)
        sx = 103 + k * 3 + int(2 * math.sin(t * 3 + k))
        c.rect(sx, sy, sx + 1, sy + 2, '#fffde0')
    # pot with lid
    c.rect(98, 288, 116, 300, '#3a3206')
    c.rect(96, 286, 118, 288, '#2a2404')
    c.rect(105, 283, 109, 285, '#2a2404')
    for x in range(100, 116, 3):
        c.px(x, 297, '#5a4c10')
    # chef silhouette (slow sway)
    sway = int(round(math.sin(t * 1.6)))
    cx = 126 + sway
    c.rect(cx - 3, 266, cx + 4, 270, '#140a1e')
    c.rect(cx - 4, 270, cx + 5, 283, '#140a1e')
    c.rect(cx - 8, 284, cx + 10, 300, '#180c22')
    c.rect(cx - 10, 288, cx - 7, 294, '#180c22')
    c.px(cx - 1, 276, '#ffffff'); c.px(cx + 2, 276, '#ffffff')


def left_sign(c, t):
    """Vertical block-glyph sign at the far left that cycles colour states."""
    seq = ['#3ae0e0', '#2ee03a', None, '#3ae0e0', '#2ee03a', '#f4ecd0', None]
    ph = int(t / 0.53) % len(seq)
    col = seq[ph]
    c.rect(0, 280, 11, 314, '#030818')
    c.rect(4, 277, 6, 278, '#ff2020' if col else '#601010')
    rr = np.random.default_rng(ph * 7 + 3)
    for k in range(5):
        y = 283 + k * 6
        if col is None:
            if rr.random() < 0.6:
                c.px(int(rr.integers(1, 10)), y + 2, '#c01818')
            continue
        c.rect(1, y, 9, y + 3, col)
        for _ in range(3):  # carve glyph detail
            c.px(int(rr.integers(2, 9)), y + int(rr.integers(1, 3)), '#04304a' if col != '#2ee03a' else '#0a4a12')


def blink_dot(c, t):
    c.rect(28, 3, 30, 5, '#ff1010')


class Scene2:
    def __init__(s):
        s.base = Canvas(W, H, '#000000')
        _bg(s.base)
        _sign_static(s.base)

    def frame(s, t):
        c = s.base.copy()
        icon(c, t)
        banner(c, t)
        yellow_bars(c, t)
        type_row(c, t)
        lanterns(c, t)
        kitchen(c, t)
        left_sign(c, t)
        blink_dot(c, t)
        return c.arr()
