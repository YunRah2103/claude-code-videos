"""Ambient pixel-moment kit (calm 'lo-fi' look: teal rain at night, pink-orange sunrise), first used by videos/flood-save.

Everything works on native-resolution numpy RGB arrays (float32, 0-255) at about 216x384 for 9:16 and is upscaled
5x nearest at the end (`up`), so one art pixel = 5x5 screen pixels, like the reference preview.

    rain(a, t, seed)                 falling diagonal rain streaks + splash rings below `water_y` (layer of the flood scene)
    glow(a, cx, cy, r, col, k)       soft light pool, quantised with an ordered 4x4 Bayer dither (pixel-art glow)
    vgrad(h, stops)                  dithered vertical gradient (skies)
    dissolve(a, b, e)                night-to-sunrise style dissolve: per-pixel Bayer threshold, no blur
    depth_graphic(t, w, h)           neutral water-depth graphic: gauge post, rippling water line, two car outlines, '?'
    mini_guy(blink)                  the main guy (characters/main-guy) as a small 9x23 figure in this style, no outline
    umbrella()                       red umbrella canopy for him
    hatchback(col) / suv(col)        generic side-view cars (no logos or badges), facing left
"""
import math
import numpy as np

BAYER = (np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]], np.float32) + 0.5) / 16


def bayer(h, w):
    return np.tile(BAYER, (h // 4 + 1, w // 4 + 1))[:h, :w]


def up(a, k=5):
    return np.repeat(np.repeat(a, k, 0), k, 1)


def vgrad(h, w, stops):
    """stops: [(y_frac, (r, g, b)), ...]. Each row lies between two stops; the mix is dithered, not smooth."""
    ys = np.array([s[0] for s in stops]) * (h - 1); cs = np.array([s[1] for s in stops], np.float32)
    f = np.interp(np.arange(h), ys, np.arange(len(stops)))
    i0 = np.clip(np.floor(f).astype(int), 0, len(stops) - 2); fr = (f - i0)[:, None]
    fr = (fr * 4).round() / 4                                   # 5 dither levels per band, like hand-made skies
    pick = (bayer(h, w) < fr)[..., None]
    return np.where(pick, cs[i0 + 1][:, None, :], cs[i0][:, None, :]).astype(np.float32)


def glow(a, cx, cy, r, col, k=0.5, ry=None):
    """Add a soft round (or oval) light pool, quantised to 4 levels and Bayer-dithered."""
    h, w = a.shape[:2]; ry = ry or r
    y0, y1, x0, x1 = max(0, int(cy - ry)), min(h, int(cy + ry) + 1), max(0, int(cx - r)), min(w, int(cx + r) + 1)
    if y0 >= y1 or x0 >= x1: return
    yy, xx = np.mgrid[y0:y1, x0:x1]
    d = np.sqrt(((xx - cx) / r) ** 2 + ((yy - cy) / ry) ** 2)
    v = np.clip(1 - d, 0, 1) ** 1.6 * 4
    q = np.floor(v) + (bayer(h, w)[y0:y1, x0:x1] < (v - np.floor(v)))
    a[y0:y1, x0:x1] += (q / 4 * k)[..., None] * (np.array(col, np.float32) - a[y0:y1, x0:x1] * 0.35)


def dissolve(a, b, e):
    """Dithered cross-dissolve a->b, e in 0..1 (pixels switch over in Bayer order: soft but still pixel art)."""
    if e <= 0: return a
    if e >= 1: return b
    m = (bayer(*a.shape[:2]) < e)[..., None]
    return np.where(m, b, a)


def blend(a, b, e):
    """Plain linear mix (for very slow fades where a dither would crawl)."""
    return a * (1 - e) + b * e


def rain(a, t, seed=1, n=150, col=(150, 205, 210), vy=260.0, vx=-70.0, ln=4, k=0.55, water_y=None, splash=24):
    """Diagonal rain streaks (native px), moving at (vx, vy) px/s; positions depend only on t, so any time is valid."""
    h, w = a.shape[:2]; r = np.random.default_rng(seed)
    x0, y0, sp = r.uniform(0, w, n), r.uniform(0, h, n), r.uniform(0.8, 1.25, n)
    col = np.array(col, np.float32)
    ys = (y0 + vy * sp * t) % (h + 20) - 10; xs = (x0 + vx * sp * t + ys * 0) % w
    for x, y, s in zip(xs, ys, sp):
        for j in range(ln):
            yy, xx = int(y + j), int(x - j * vx / vy + 0.5) % w
            if 0 <= yy < h: a[yy, xx] += (col - a[yy, xx]) * k * (0.55 + 0.45 * j / ln) * min(1, s)
    if water_y is None: return
    for i in range(splash):                                       # splash rings on the water, each lives 0.35 s
        ph = (t * 1.6 + r.uniform(0, 1)) % 1.0
        sx, sy = r.uniform(4, w - 4), r.uniform(water_y + 4, h - 4)
        cyc = math.floor(t * 1.6 + r.uniform(0, 1))
        sx = (sx + cyc * 37.3) % (w - 8) + 4                      # new place each cycle
        if ph < 0.55:
            rr = 1 + int(ph * 7); yy = int(sy)
            for xx in (int(sx) - rr, int(sx) + rr):
                if 0 <= xx < w: a[yy, xx] += (col - a[yy, xx]) * 0.45 * (1 - ph / 0.55)
            if ph < 0.15: a[yy - 1, int(sx)] += (col - a[yy - 1, int(sx)]) * 0.5


def paste(a, spr, x, y, tint=(1, 1, 1), alpha=1.0):
    """Paste an RGBA sprite (h, w, 4 float array) with its top-left at (x, y), multiplied by a tint."""
    h, w = a.shape[:2]; sh, sw = spr.shape[:2]; x, y = int(round(x)), int(round(y))
    if x + sw <= 0 or y + sh <= 0 or x >= w or y >= h: return       # fully off-canvas
    ys, xs = slice(max(0, y), min(h, y + sh)), slice(max(0, x), min(w, x + sw))
    s = spr[ys.start - y:ys.stop - y, xs.start - x:xs.stop - x]
    if s.size == 0: return
    m = s[..., 3:4] / 255 * alpha
    a[ys, xs] = a[ys, xs] * (1 - m) + s[..., :3] * np.array(tint, np.float32) * m


def _sprite(rows, pal):
    h, w = len(rows), max(len(r) for r in rows); s = np.zeros((h, w, 4), np.float32)
    for y, row in enumerate(rows):
        for x, c in enumerate(row):
            if c in pal: s[y, x] = (*pal[c], 255)
    return s


# The main guy (characters/main-guy palette): dark messy hair, silver glasses, brown skin, white tee, dark jeans,
# white sneakers. Drawn small and outline-free like the people in the reference, not as the chunky presenter rig.
GUY_PAL = {'h': (35, 26, 28), 'H': (79, 61, 66), 's': (192, 136, 98), 'd': (160, 107, 75), 'b': (212, 145, 122),
           'g': (169, 176, 187), 'G': (211, 216, 224), 'e': (18, 18, 28), 'm': (110, 47, 51), 'w': (247, 247, 250),
           't': (214, 217, 226), 'j': (43, 45, 51), 'k': (26, 27, 32), 'o': (244, 244, 246), 'O': (185, 188, 198)}
GUY = ['..h.h....', '.hhhhhh..', 'hhHhhhhh.', 'hhhhhhhh.', '.hsssssh.', '.GgGsGgG.', '.gesgseg.', '.sbssbsd.',
       '..ssmsd..', '...ddd...', '.twwwwwt.', 'twwwwwwwt', 'swwwwwwts', 'swwwwwwts', 'd.wwwwt.d', 's.wwwwt.s',
       '..kkkkk..', '..jjjjj..', '..jj.jk..', '..jj.jk..', '..jj.jk..', '..oo.oO..', '.ooo.oOO.']


def mini_guy(blink=False):
    rows = list(GUY)
    if blink: rows[6] = '.gssgssg.'
    return _sprite(rows, GUY_PAL)


def umbrella():
    pal = {'r': (176, 56, 66), 'R': (208, 84, 88), 'u': (112, 34, 46), 'p': (60, 40, 44)}
    return _sprite(['.......RRRRRRR.......', '....RRRRRRRrrrrrr....', '..RRRRrrrrrrrrrrrrr..', '.Rrrrrrrrrrrrrrrrrru.',
                    'rrrrrrrrrrrrrrrrrruuu', 'u.uuu.uuu.uuu.uuu.u.u', '..........p..........', '..........p..........',
                    '..........p..........', '..........p..........', '..........p..........', '..........p..........',
                    '..........p..........', '..........p..........', '.........pp..........'], pal)


def _car(w, h, body, cabin, wins, wheels, col, lights, extra=()):
    from PIL import Image, ImageDraw
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    c = tuple(col); dk = tuple(int(v * 0.7) for v in col); hi = tuple(min(255, int(v * 1.18 + 12)) for v in col)
    d.polygon(cabin, fill=c); d.rectangle(body, fill=c)
    d.line([(body[0] + 1, body[1]), (body[2] - 1, body[1])], fill=hi)          # shoulder highlight
    d.line([(body[0], body[3]), (body[2], body[3])], fill=dk)                   # sill shadow
    for p in wins: d.polygon(p, fill=(40, 62, 74)); d.line([p[0], p[1]], fill=(120, 160, 170))
    for x0, x1 in extra: d.line([(x0, body[1] + 2), (x0, body[3] - 1)], fill=dk)   # door seams
    for cx, cy, r in wheels:
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(24, 24, 30)); d.ellipse((cx - r + 2, cy - r + 2, cx + r - 2, cy + r - 2), fill=(120, 124, 132))
        d.point((cx, cy), fill=(60, 62, 70))
    (fx, fy), (rx, ry) = lights
    d.rectangle((fx, fy, fx + 1, fy + 1), fill=(255, 236, 170)); d.rectangle((rx - 1, ry, rx, ry + 1), fill=(220, 70, 70))
    return np.asarray(im, np.float32).copy()


def hatchback(col=(214, 200, 168)):
    """Small generic hatchback, 40x17, facing left (no badges). Ground contact at the bottom row."""
    return _car(41, 17, (1, 7, 39, 13), [(7, 7), (13, 2), (31, 1), (36, 2), (39, 6), (39, 7)],
                [[(10, 7), (14, 3), (22, 3), (22, 7)], [(24, 7), (24, 3), (31, 2), (35, 3), (36, 7)]],
                [(9, 13, 3), (31, 13, 3)], col, ((1, 8), (39, 8)), extra=[(23, 0)])


def suv(col=(108, 126, 140)):
    """Generic SUV, 49x23, facing left, higher body and ground clearance (no badges)."""
    s = _car(49, 23, (0, 9, 48, 17), [(6, 9), (12, 2), (45, 2), (48, 6), (48, 9)],
             [[(10, 9), (14, 4), (22, 4), (22, 9)], [(24, 9), (24, 4), (34, 4), (34, 9)], [(36, 9), (36, 4), (44, 4), (45, 9)]],
             [(10, 18, 4), (38, 18, 4)], col, ((0, 10), (48, 10)), extra=[(23, 0), (35, 0)])
    s[1, 16:42] = (52, 54, 62, 255)                                             # roof rails
    return s


def depth_graphic(t, w=216, h=384, bg=(18, 40, 46), sweep=0.0):
    """Neutral water-depth graphic: a gauge post with ticks, a water line that rises and settles with ripples, a low
    and a high car outline both reaching it, current streaks, and a pixel question mark. Returns a native RGB array.
    sweep 0..1: the water rises further and the SUV lifts, tilts and is carried off to the right by the current."""
    a = vgrad(h, w, [(0, (14, 30, 36)), (1, bg)])
    for x in range(8, w, 12): a[::12, x] += 6                                  # faint grid
    gy = 246                                                                   # road under the water
    lvl = gy + 2 - 16 * (1 - math.exp(-t * 2.2)) - 6 * sweep + 1.0 * math.sin(t * 2.4)   # ends near the small car's roof, half way up the SUV
    yl = int(lvl)
    px, top = 190, 112
    a[top:gy + 2, px:px + 3] = (200, 206, 196)
    for i, y in enumerate(range(top, gy, 8)): a[y, px - (5 if i % 2 == 0 else 3):px] = (200, 206, 196)
    for spr, x0 in ((hatchback((150, 160, 150)), 34), (suv((150, 160, 150)), 100)):
        o = spr.copy(); o[..., :3] = o[..., :3] * 0.6 + 40; dy = 0
        if sweep and o.shape[1] > 45:                                          # the SUV floats off
            from PIL import Image
            o = np.asarray(Image.fromarray(o.astype(np.uint8), 'RGBA').rotate(-7 * sweep + 2 * math.sin(t * 4) * sweep, Image.NEAREST, expand=True), np.float32)
            x0, dy = x0 + 130 * sweep ** 1.8, -5 * min(1, sweep * 3) + math.sin(t * 5) * sweep
        paste(a, o, x0, gy - o.shape[0] + dy)
    a[gy + 1:gy + 3] = (30, 60, 66)
    water = np.array((46, 120, 140), np.float32)
    a[yl:] = a[yl:] * 0.45 + water * 0.55
    a[gy + 3:] = a[gy + 3:] * 0.7                                             # deeper water below the road line
    for y in range(yl + 4, h, 6):                                             # current streaks, faster when it sweeps
        for j in range(3):
            xx = int((j * 71 + y * 13 + t * (14 + 60 * sweep)) % w); a[y, xx:xx + 5 + int(6 * sweep)] += 22 + 20 * sweep
    for x in range(0, w):
        yy = yl + int(round(1.0 * math.sin(x * 0.35 + t * 5)))
        a[yy, x] = (150, 220, 230)
    for row in range(3):                                                       # current chevrons race right
        yy = yl + 14 + row * 22
        for j in range(4):
            cx = int((j * 60 + row * 23 + t * (20 + 90 * sweep)) % (w + 20)) - 10
            for d in range(4):
                for xx, y2 in ((cx + d, yy - 3 + d), (cx + d, yy + 3 - d)):
                    if 0 <= xx < w and 0 <= y2 < h: a[y2, xx] += (np.array((190, 240, 245)) - a[y2, xx]) * (0.25 + 0.55 * sweep)
    q = ['.qqqq.', 'qq..qq', '....qq', '...qq.', '..qq..', '..qq..', '......', '..qq..']
    qk = max(0.0, 1 - sweep * 3)                                               # the '?' gives way to the answer
    bob = int(round(1.5 * math.sin(t * 3)))
    if qk > 0:
        for y, row in enumerate(q):
            for x, c in enumerate(row):
                if c == 'q':
                    sl = (slice(150 + y * 5 + bob, 155 + y * 5 + bob), slice(90 + x * 5, 95 + x * 5))
                    a[sl] = a[sl] * (1 - qk) + np.array((255, 217, 59)) * qk
        glow(a, 105, 170, 34, (255, 217, 59), 0.22 * qk)
    return a
