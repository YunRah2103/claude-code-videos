"""Cozy creator room: no-talk aesthetic pixel loop.

Main guy sits at his desk editing a car video, then looks up and waves.
Reuses the approved jointed sprite (new-car-trap/src/pix.py) and sfx helpers.
Usage: python render.py still OUTDIR T...   |   python render.py video OUT.mp4 [T0 T1]
"""
import sys, math, subprocess, wave
from functools import lru_cache
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'new-car-trap' / 'src'))
import pix, sfx  # noqa: E402

W0, H0, S = 135, 240, 8          # native pixel canvas, upscaled 8x -> 1080x1920
W, H = W0 * S, H0 * S
FPS = 30
DUR = 12.0
BEAT = 0.75                       # 80 BPM, 4 bars = one seamless loop
SR = sfx.SR

CX, Y0 = 60, 104                  # character centre x, sprite top
SX = CX - 24                      # 48px-wide posable sprite
FE = Y0 + 42                      # desk far edge (hands rest here)
HAND_ROW = FE - Y0


def hx(h): return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))
def R(d, x0, y0, x1, y1, c): d.rectangle([x0, y0, x1, y1], fill=hx(c))


def sprite(rows, cmap, oc=(22, 17, 34, 255)):
    g = pix.Grid(len(rows[0]) + 2, len(rows) + 2)
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch != '.': g.px(x + 1, y + 1, cmap[ch])
    return g.image(outline=True, oc=oc)


def paste(im, spr, x, y): im.alpha_composite(spr, (x - 1, y - 1))


# ---------------------------------------------------------------- props
TOYCAR = ["...cccc.....", "..cwwcwwc...", "cccccccccccy", "cddccccccddc", ".kk......kk."]
CAT = [".o.o..............", ".ooo....bbbbbb....", "ooooo.bbbbbbbbbb..", "oeoeo.bbsbbbsbbbb.",
       "ooooobbbbbbbbbbbbb", ".ooobbbbbbbbbbbbbb", "..bbbbbbbbbbbbbbtt", "..tttttttttttttt.."]
CAT_IN = [".o.o....bbbbbb....", ".ooo..bbbbbbbbbb..", "ooooobbbbbbbbbbbb.", "oeoeobbbsbbbsbbbb.",
          "ooooobbbbbbbbbbbbb", ".ooobbbbbbbbbbbbbb", "..bbbbbbbbbbbbbbtt", "..tttttttttttttt.."]
CATC = {'o': '#f0a04b', 'b': '#e8923e', 's': '#c46f2a', 'e': '#3a2230', 't': '#c9772f'}
POSTER_CAR = ["......kkkkkkk.......", "....kkkkkkkkkkk.....", "kkkkkkkkkkkkkkkkkkkk",
              "kkkkkkkkkkkkkkkkkkkk", "..kk..........kk...."]


def neon_layer():
    im = Image.new('RGBA', (34, 14), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    c = hx('#5ff4ff') + (255,)
    d.line([(1, 9), (1, 6), (5, 5), (10, 1), (20, 1), (25, 5), (30, 6), (31, 9), (28, 9)], fill=c)
    d.line([(10, 9), (21, 9)], fill=c); d.line([(1, 9), (4, 9)], fill=c)
    d.line([(11, 5), (12, 2), (19, 2), (23, 5), (11, 5)], fill=c)
    d.arc([4, 7, 10, 13], 180, 360, fill=c); d.arc([21, 7, 27, 13], 180, 360, fill=c)
    d.line([(3, 13), (30, 13)], fill=hx('#ff5fd2') + (255,))
    return im


NEON = neon_layer()


def build_bg():
    im = Image.new('RGBA', (W0, H0), hx('#5a4c86') + (255,))
    d = ImageDraw.Draw(im)
    em = np.zeros((H0, W0), np.float32)
    R(d, 0, 0, W0 - 1, 5, '#2a2244'); R(d, 0, 7, W0 - 1, 7, '#3e3260')
    for x in range(4, W0, 9): R(d, x, 8, x, 193, '#4f4277')
    R(d, 0, 186, W0 - 1, 193, '#4a3e70'); R(d, 0, 186, W0 - 1, 186, '#6a5c96')
    R(d, 0, 194, W0 - 1, 196, '#2e2546')
    R(d, 0, 197, W0 - 1, H0 - 1, '#6e4f66')
    for i, y in enumerate(range(197, H0, 7)):
        R(d, 0, y, W0 - 1, y, '#58404f')
        for x in range((i * 23) % 31, W0, 31) if y < H0 - 1 else (): R(d, x, y + 1, x, min(y + 6, H0 - 1), "#58404f")
    # rug
    R(d, 16, 206, 120, 235, '#6a3f8f'); R(d, 19, 209, 117, 232, '#8a56b5'); R(d, 22, 212, 114, 229, '#6a3f8f')
    for x in range(16, 121, 3): R(d, x, 236, x, 238, '#cdb6e6'); R(d, x, 203, x, 205, '#cdb6e6')
    # window, curtains
    R(d, 5, 18, 37, 86, '#7a6fa6'); R(d, 6, 19, 36, 85, '#5c5288')
    R(d, 3, 87, 39, 89, '#8e82bb'); R(d, 3, 89, 39, 89, '#6a5f96')
    R(d, 0, 12, 44, 12, '#2a2338')
    for (a, b) in ((0, 5), (37, 42)):
        R(d, a, 13, b, 93, '#7a3f9e')
        for x in range(a + 1, b + 1, 2): R(d, x, 13, x, 93, '#5f2f80')
    # poster (retro sunset + car)
    R(d, 46, 20, 76, 60, '#231a33')
    for i, c in enumerate(['#ffb35a', '#ff8a5c', '#ff6a7f', '#e0559a', '#a548b0', '#6c3aa8']):
        R(d, 47, 21 + i * 5, 75, 25 + i * 5, c)
    for y in range(31, 46):
        for x in range(54, 69):
            if (x - 61) ** 2 + (y - 39) ** 2 <= 49 and y not in (41, 43, 45): d.point((x, y), hx('#ffe07a'))
    R(d, 47, 46, 75, 59, '#3a2350')
    d.polygon([(58, 59), (64, 59), (62, 47), (60, 47)], fill=hx('#5a3a72'))
    for y in (49, 53, 57): R(d, 61, y, 61, y + 1, '#ffd36b')
    paste(im, sprite(POSTER_CAR, {'k': '#1a1026'}), 51, 48)
    # chair
    R(d, 43, 93, 77, 146, '#5a4590'); R(d, 42, 95, 78, 146, '#5a4590')
    R(d, 42, 95, 46, 146, '#463470'); R(d, 74, 95, 78, 146, '#463470')
    R(d, 52, 93, 68, 101, '#7f63c4'); R(d, 53, 94, 67, 94, '#a68ae6')
    R(d, 59, 102, 61, 146, '#9a7bff')
    # shelves
    for y in (50, 80):
        R(d, 89, y, 132, y + 1, '#9a86b8'); R(d, 89, y + 2, 132, y + 2, '#3f3460')
        R(d, 93, y + 3, 94, y + 5, '#3f3460'); R(d, 127, y + 3, 128, y + 5, '#3f3460')
    for (x, c) in ((90, '#e04050'), (104, '#3f7fe0'), (118, '#f4c430')):
        dk = '#' + ''.join(f'{int(v * .7):02x}' for v in hx(c))
        paste(im, sprite(TOYCAR, {'c': c, 'd': dk, 'w': '#bfe6ff', 'k': '#1c1a24', 'y': '#fff2a0'}), x, 45)
    # plant + vines, books, lava lamp base
    R(d, 92, 73, 99, 79, '#c8673f'); R(d, 92, 73, 99, 74, '#e0844f')
    for (x, y) in ((93, 66), (96, 63), (99, 67), (91, 70), (98, 70), (95, 68)):
        R(d, x, y, x + 2, y + 4, '#4fb36a'); d.point((x + 1, y), hx('#7fe08a'))
    for x, l in ((92, 9), (95, 13), (98, 7)):
        for k in range(l): d.point((x + (k // 3) % 2, 82 + k), hx('#4fb36a'))
    for x, hgt, c in ((104, 12, '#e05a6a'), (107, 10, '#5ab0e0'), (110, 13, '#f0d060'), (113, 9, '#7a5cff')):
        R(d, x, 80 - hgt, x + 2, 79, c); R(d, x, 80 - hgt + 2, x + 2, 80 - hgt + 2, '#fff4dc')
    R(d, 121, 64, 128, 65, '#3a3550'); R(d, 120, 78, 129, 79, '#3a3550')
    # ring light + phone
    R(d, 19, 127, 19, 143, '#3a3550'); R(d, 15, 144, 23, 145, '#3a3550')
    for y in range(100, 129):
        for x in range(6, 33):
            v = ((x - 19) / 11.5) ** 2 + ((y - 114) / 12.5) ** 2
            u = ((x - 19) / 9.0) ** 2 + ((y - 114) / 10.0) ** 2
            if v <= 1 and u > 1: d.point((x, y), hx('#fff4e8')); em[y, x] = 1
    R(d, 18, 103, 20, 106, '#3a3550'); R(d, 18, 122, 20, 126, '#3a3550')
    R(d, 15, 106, 23, 122, '#18161f'); R(d, 16, 108, 22, 120, '#2b3556'); em[108:121, 16:23] = .6
    # monitor
    R(d, 89, 100, 130, 131, '#141220'); R(d, 90, 101, 129, 101, '#2c2840')
    R(d, 107, 132, 111, 143, '#3a3550'); R(d, 101, 144, 117, 146, '#3a3550'); R(d, 101, 144, 117, 144, '#55507a')
    em[102:130, 91:129] = 1
    # desk
    R(d, 3, 146, 131, 153, '#8f7aa8'); R(d, 3, 146, 131, 146, '#6a5a86'); R(d, 3, 153, 131, 153, '#b4a2d0')
    R(d, 3, 154, 131, 159, '#5b4b73'); R(d, 3, 159, 131, 159, '#463a5b')
    R(d, 9, 160, 97, 193, '#251e38')
    R(d, 4, 160, 8, 196, '#5b4b73')
    R(d, 98, 160, 130, 196, '#665484'); R(d, 98, 160, 98, 196, '#4c3f66')
    for y in (172, 184): R(d, 99, y, 130, y, '#4c3f66')
    for y in (166, 178, 190): R(d, 110, y, 118, y, '#c8b8e0')
    # legs under the desk (seated, in shadow)
    for (a, b) in ((52, 58), (61, 67)):
        R(d, a, 160, b, 189, '#3a3c46'); R(d, a, 160, a, 189, '#2b2d33')
        R(d, a - 2, 190, b + 1, 193, '#e6e6ee'); R(d, a - 2, 193, b + 1, 193, '#b9bcc6')
    # PC tower
    R(d, 76, 162, 95, 195, '#2a2638'); R(d, 78, 164, 93, 193, '#16131f'); R(d, 76, 162, 95, 162, '#3e3956')
    # keyboard, mouse, mug
    R(d, 49, 147, 71, 151, '#2a2536'); R(d, 49, 147, 71, 147, '#3c364e')
    for y in (148, 150):
        for x in range(50 + (y == 150), 71, 2): d.point((x, y), hx('#6c6688'))
    R(d, 49, 152, 71, 152, '#a77bff'); em[152, 49:72] = .8
    R(d, 72, 147, 81, 152, '#3a3052'); R(d, 75, 148, 78, 151, '#2a2536'); d.point((76, 148), hx('#5ff4ff'))
    R(d, 82, 143, 87, 151, '#efe4d6'); R(d, 82, 143, 87, 143, '#5a3a2a'); R(d, 88, 145, 89, 148, '#efe4d6')
    R(d, 82, 151, 87, 151, '#cfc2b2'); R(d, 84, 146, 85, 148, '#ff7ab8')
    # fairy-light wire
    for x in range(44, 135):
        k = ((x - 44) % 45) / 45
        d.point((x, int(10 + 5 * math.sin(math.pi * k))), hx('#2a2338'))
    return im, em


def build_sky():
    r = np.random.default_rng(11)
    gw, gh = 29, 65
    top, bot = np.array(hx('#0a0f26'), float), np.array(hx('#3a2a5e'), float)
    sky = np.zeros((gh, gw, 3))
    for y in range(gh):
        k = round((y / (gh - 1)) ** 1.4 * 6) / 6
        sky[y] = top * (1 - k) + bot * k
    lit, x = [], 0
    while x < gw:
        bw, bh = r.integers(4, 8), r.integers(20, 36)
        sky[gh - bh:, x:x + bw] = hx('#1d2044'); x += bw
    x = -2
    while x < gw:
        bw, bh = int(r.integers(5, 10)), int(r.integers(10, 28))
        x0, x1 = max(0, x), min(gw, x + bw)
        sky[gh - bh:, x0:x1] = hx('#0e1128')
        for yy in range(gh - bh + 2, gh - 1, 3):
            for xx in range(x0 + 1, x1 - 1, 2):
                if r.random() < .4: lit.append((yy, xx, hx(str(r.choice(['#ffcf6b', '#ff9f5a', '#9fe3ff', '#ffe9b0']))), r.random() * 6.28))
        x += bw + 1
    drops = [(r.integers(0, gw + 16), r.random() * 80, .8 + .4 * r.random()) for _ in range(46)]
    bolt, bx = [], int(r.integers(9, 18))
    for y in range(0, 34):
        if y % 4 == 0: bx += int(r.choice([-1, 1, 1]))
        bolt.append((y, bx))
    return sky, lit, drops, bolt


BG, EMIS = build_bg()
BGA = np.asarray(BG.convert('RGB'), np.float32)
SKY, LIT, DROPS, BOLT = build_sky()

# ---------------------------------------------------------------- lighting
yy, xx = np.mgrid[0:H0, 0:W0].astype(np.float32)


def glow(cx, cy, r, p=1.5, steps=14):
    I = np.clip(1 - np.hypot(xx - cx, yy - cy) / r, 0, 1) ** p
    return (np.floor(I * steps + .35) / steps)[..., None]


C = lambda *v: np.array(v, np.float32)
G_LED = (np.floor(.6 * np.exp(-(yy - 6) / 38) * 14 + .35) / 14)[..., None]
G_RING, G_MON = glow(19, 114, 95), glow(110, 116, 85)
G_WIN, G_PC = glow(21, 52, 60), glow(86, 178, 48)
G_NEON, G_LAVA = glow(112, 30, 45), glow(124, 72, 26)
G_FLASH = glow(21, 52, 140, p=1.0)
L_STATIC = G_LED * C(1, .42, .85) * .6 + G_RING * C(1, .92, .85) * .8 + G_MON * C(.45, .75, 1) * .75
AMB = C(.42, .4, .55)
VIG = 1 - .3 * np.clip((np.hypot((xx - W0 / 2) / W0, (yy - H0 / 2) / H0 * .8) - .32) / .3, 0, 1)
VIG = (np.round(VIG * 8) / 8)[..., None]


def hsv(h):
    k = (np.array([5, 3, 1]) + h * 6) % 6
    return 1 - np.clip(np.minimum(k, 4 - k), 0, 1) * .75


def flash(t):
    v = 0.0
    for t0 in (2.5, 5.9):
        dt = t - t0
        if 0 <= dt < .07: v = max(v, 1)
        elif .12 <= dt < .2: v = max(v, .8)
        elif .2 <= dt < .6: v = max(v, .8 * (1 - (dt - .2) / .4) ** 2)
    return v

# ---------------------------------------------------------------- character
PL = {'kd': ((2, 7), (-4, 11)), 'ku': ((2, 7), (-4, 10))}
PR = dict(PL, m1=((3, 6), (6, 11)), m2=((3, 6), (7, 11)), lift=((4, 2), (6, -3)),
          w1=((4, -4), (5, -12)), w2=((5, -4), (9, -11)))
for l in PL:
    for r in PR: pix.POSES[f'{l}_{r}'] = (PL[l], PR[r])

BURSTS = ((0.0, 2.2), (3.3, 5.2), (6.1, 7.0), (10.9, 12.0))
TYPE_SEQ = np.random.default_rng(5).choice(['kd_ku', 'ku_kd', 'kd_ku', 'ku_kd', 'ku_ku'], 200)
BLINKS = (1.3, 4.4, 6.5, 8.9, 11.5)


def state(t):
    """-> pose, eyes, mouth, nod"""
    eyes, mouth = 'right', 'calm'
    if 2.55 <= t < 3.15: eyes = 'left'                 # glance at the lightning
    if 7.25 <= t < 10.5: eyes, mouth = 'center', 'smile'
    if 7.45 <= t < 10.15: mouth = 'open'
    if 10.5 <= t < 10.7: mouth = 'smile'
    if any(b <= t < b + .1 for b in BLINKS): eyes = 'blink'
    burst = any(a <= t < b for a, b in BURSTS)
    if burst: pose = TYPE_SEQ[int(t / .1)]
    elif 7.0 <= t < 7.5: pose = 'ku_ku'
    elif 7.5 <= t < 7.65 or 10.0 <= t < 10.15: pose = 'ku_lift'
    elif 7.65 <= t < 10.0: pose = 'ku_w1' if int((t - 7.65) / .2) % 2 == 0 else 'ku_w2'
    else: pose = 'ku_m1' if int(t / .5) % 3 else 'ku_m2'
    nod = int(not 7.2 <= t < 10.4 and (t % BEAT) < .2)
    return pose, eyes, mouth, nod


@lru_cache(None)
def guy(pose, eyes, mouth, nod):
    img = pix.guy('talk' if mouth == 'open' else 'smile', False, pose).copy()
    p, O = img.load(), pix.OX
    def put(x, y, c): p[x + O, y] = c
    for a, b in ((11, 15), (20, 24)):
        for y in range(14, 19):
            for x in range(a, b + 1): put(x, y, pix.SKIN)
    dx = {'right': 1, 'left': -1}.get(eyes, 0)
    for ex in (12, 21):
        if eyes == 'blink':
            for x in range(ex, ex + 3): put(x, 16, pix.EYE)
            continue
        x0 = ex + dx
        put(x0, 15, pix.WHITE); put(x0 + 1, 15, pix.WHITE); put(x0 + 2, 15, pix.EYE)
        put(x0 + 1, 16, pix.EYE); put(x0 + 2, 16, pix.EYE)
    if eyes == 'right':
        put(24, 14, (207, 239, 255, 255)); put(23, 14, (150, 210, 255, 255))   # monitor glint
    if mouth == 'calm':
        for y in range(22, 25):
            for x in range(14, 22): put(x, y, pix.SKIN)
        for x in range(16, 20): put(x, 23, pix.MOUTH)
        put(15, 22, pix.MOUTH); put(20, 22, pix.MOUTH)
    if nod:
        head = img.crop((0, 0, img.width, 28))
        img.paste((0, 0, 0, 0), (0, 0, img.width, 1)); img.paste(head, (0, 1))
    a = np.array(img)
    rgb = a[..., :3]
    skin = (rgb == pix.SKIN[:3]).all(-1) | (rgb == pix.SKINSH[:3]).all(-1)
    m = np.zeros(skin.shape, bool); m[HAND_ROW - 1:] = skin[HAND_ROW - 1:]
    dil = m.copy(); dil[1:] |= m[:-1]; dil[:-1] |= m[1:]; dil[:, 1:] |= m[:, :-1]; dil[:, :-1] |= m[:, 1:]
    keep = (m | (dil & (rgb == pix.OUT[:3]).all(-1)))
    keep[:HAND_ROW] = False
    hands = a.copy(); hands[~keep] = 0
    return img, Image.fromarray(hands)


def hand_pos(pose):
    (ex, ey), (hx_, hy) = PR[pose.split('_')[1]]
    return SX + 26 + pix.OX + hx_, Y0 + 31 + hy


# ---------------------------------------------------------------- frame
def frame(n, raw=True):
    t = n / FPS
    fl = flash(t)
    im = BG.copy()
    em = EMIS.copy()
    a = np.array(im)
    # window: sky, city, rain, lightning
    sky = SKY.copy()
    for (y, x, c, ph) in LIT:
        if math.sin(t * .7 + ph * 3) > -.85: sky[y, x] = c
    sky = sky + fl * np.array([150, 160, 190]) * (sky.mean(-1, keepdims=True) < 60)
    if fl > .5 and (t % 3.4) < 3:
        for y, x in BOLT:
            if 0 <= x < 29: sky[y, x] = (240, 245, 255); sky[y, min(x + 1, 28)] = (170, 190, 255)
    for (x0, y0, v) in DROPS:
        y = (y0 + 230 * v * t) % 82 - 10
        for k in range(3):
            yy_, xx_ = int(y + k), int(x0 - (y + k) / 4) % 45 - 8
            if 0 <= yy_ < 65 and 0 <= xx_ < 29: sky[yy_, xx_] = sky[yy_, xx_] * .45 + np.array([150, 165, 220]) * .55
    a[20:85, 7:36, :3] = np.clip(sky, 0, 255).astype(np.uint8)
    em[20:85, 7:36] = 1
    a[20:85, 21, :3] = hx('#5c5288'); a[52, 7:36, :3] = hx('#5c5288'); em[20:85, 21] = 0; em[52, 7:36] = 0
    im = Image.fromarray(a)
    d = ImageDraw.Draw(im)
    # LED strip, fairy lights
    led = .9 + .1 * math.sin(t * 2 * math.pi / 3)
    d.line([(0, 6), (W0, 6)], fill=tuple(int(c * led) for c in hx('#ff6ad5'))); em[6] = 1
    for i, x in enumerate(range(47, 134, 6)):
        k = ((x - 44) % 45) / 45
        y = int(10 + 5 * math.sin(math.pi * k)) + 1
        b = .55 + .45 * math.sin(t * 2.2 + i * 1.7)
        c = hx(['#ffd36b', '#ff7ab8', '#7fe0ff'][i % 3])
        d.point((x, y), tuple(int(v * b) for v in c)); em[y, x] = 1
    # neon car sign (flickers once)
    neon_on = not (4.1 <= t < 4.17 or 4.23 <= t < 4.27)
    if neon_on:
        im.alpha_composite(NEON, (96, 21)); em[21:35, 96:130] = np.maximum(em[21:35, 96:130], np.array(NEON)[..., 3] / 255)
    else:
        dim = Image.new('RGBA', NEON.size, hx('#3a5560') + (255,)); im.paste(dim, (96, 21), NEON)
    # lava lamp
    R(d, 122, 66, 127, 77, '#c2307a'); R(d, 123, 66, 126, 77, '#ff5fa0'); em[66:78, 122:128] = 1
    for k in range(2):
        by = int(71 + 4 * math.sin(t * .9 + k * 2.6))
        R(d, 123, by, 125 + k % 2, by + 1 + k, '#ffd06b')
    # monitor: edit UI with a tiny car clip
    R(d, 91, 102, 128, 129, '#161b2e'); R(d, 91, 102, 128, 103, '#232a44')
    for i, c in enumerate(('#ff5f6d', '#ffd36b', '#5ff4a0')): d.point((93 + i * 2, 102), hx(c))
    R(d, 92, 105, 113, 117, '#2a2350'); R(d, 92, 113, 113, 117, '#1c1830')
    for i in range(6):
        bx = 92 + int((i * 6 - t * 9) % 26) - 2
        if 92 <= bx <= 110: R(d, bx, 108 + i % 3, bx + 2, 112, '#141a33')
        lx = 92 + int((i * 5 - t * 22) % 25) - 2
        if 92 <= lx <= 111: R(d, max(lx, 92), 115, lx + 2, 115, '#ffd36b')
    cy = 112 - (int(t * 8) % 2)
    R(d, 100, cy, 105, cy + 1, '#e04050'); R(d, 101, cy - 1, 103, cy - 1, '#e04050')
    d.point((106, cy + 1), hx('#fff2a0')); d.point((101, cy + 2), hx('#111111')); d.point((104, cy + 2), hx('#111111'))
    for i, c in enumerate(('#6c7bff', '#ff6ad5', '#46d9c8', '#ffd36b', '#9a7bff', '#ff9f5a')):
        R(d, 115 + (i % 2) * 7, 105 + (i // 2) * 4, 119 + (i % 2) * 7, 107 + (i // 2) * 4, c)
    R(d, 91, 119, 128, 119, '#2d3554')
    for x0, x1, y, c in ((92, 101, 121, '#6c7bff'), (103, 114, 121, '#ff6ad5'), (116, 127, 121, '#46d9c8'),
                         (95, 108, 124, '#9a7bff'), (111, 122, 124, '#ffd36b')):
        R(d, x0, y, x1, y + 1, c)
    for x in range(92, 128):
        h = 1 + int(1.5 + 1.5 * math.sin(x * 1.3) * math.sin(x * .4))
        R(d, x, 128 - min(h, 2), x, 128, '#5ff4a0')
    ph = 92 + int((t * 4) % 36)
    R(d, ph, 119, ph, 128, '#ff4d6d'); R(d, ph - 1, 118, ph + 1, 118, '#ff4d6d')
    # phone REC dot
    if (t % 1.0) < .6: d.point((21, 109), hx('#ff3b4e')); em[109, 21] = 1
    # character, desk occluder, hands on the keyboard
    pose, eyes, mouth, nod = state(t)
    body, hands = guy(pose, eyes, mouth, nod)
    im.alpha_composite(body, (SX, Y0))
    im.paste(BG.crop((SX, FE, SX + 48, Y0 + 60)), (SX, FE))
    em[FE:Y0 + 60, SX:SX + 48] = EMIS[FE:Y0 + 60, SX:SX + 48]
    im.alpha_composite(hands, (SX, Y0))
    hm = np.zeros((H0, W0), bool); hm[Y0:Y0 + 60, SX:SX + 48] = np.array(hands)[..., 3] > 0; em[hm] = 0
    d = ImageDraw.Draw(im)
    # wave sparkles
    if pose.endswith(('w1', 'w2')):
        hxp, hyp = hand_pos(pose)
        for k, t0 in enumerate((7.7, 8.5, 9.3)):
            p = (t - t0) / .45
            if 0 <= p < 1:
                sx, sy, rr = hxp + 6 + k * 2, hyp - 6 - k * 3, 1 + int(p * 2.5)
                c = tuple(int(v * (1 - p * .6)) for v in hx('#fff2a0'))
                for dd in range(-rr, rr + 1):
                    d.point((sx + dd, sy), c); d.point((sx, sy + dd), c); em[sy, sx + dd] = 1; em[sy + dd, sx] = 1
    # PC fans (rainbow spin)
    hue = (t * .12) % 1
    for fy in (172, 185):
        for ang in range(0, 360, 12):
            th = math.radians(ang)
            x, y = int(round(85 + 5 * math.cos(th))), int(round(fy + 5 * math.sin(th)))
            c = tuple(int(v * 255) for v in hsv((hue + ang / 360) % 1)); d.point((x, y), c); em[y, x] = 1
        for k in range(3):
            th = t * 9 + k * 2.09
            d.point((int(round(85 + 2.5 * math.cos(th))), int(round(fy + 2.5 * math.sin(th)))), (70, 64, 96))
    # mug steam
    for i in range(3):
        p = (t * .45 + i / 3) % 1
        sx_, sy_ = 84 + int(round(1.6 * math.sin(p * 7 + i * 2))), int(141 - p * 15)
        c = tuple(int(v * (1 - p) * .7 + 60 * p) for v in hx('#e6dcff'))
        R(d, sx_, sy_, sx_, sy_ + 1, '#%02x%02x%02x' % c)
    # sleeping cat on the rug
    paste(im, sprite(CAT_IN if (t % 3.0) < 1.4 else CAT, CATC), 26, 213 - ((t % 3.0) < 1.4))
    paste(im, sprite(TOYCAR, {'c': '#e04050', 'd': '#9c2c38', 'w': '#bfe6ff', 'k': '#1c1a24', 'y': '#fff2a0'}), 96, 224)

    # ---- lighting
    base = np.asarray(im.convert('RGB'), np.float32) / 255
    pc = hsv((hue + .25) % 1)
    L = (L_STATIC + G_PC * pc * .7 + G_WIN * C(.45, .55, 1) * (.35 + 1.2 * fl)
         + G_LAVA * C(1, .45, .6) * .4 + G_NEON * C(.35, .95, 1) * (.45 * neon_on) + G_FLASH * C(.8, .85, 1) * fl * .9)
    lit = base * (AMB + L) + L * .05
    e = em[..., None]
    out = (lit * (1 - e) + base * e) * VIG
    for i in range(16):                      # drifting dust motes in the light
        r_ = np.random.default_rng(100 + i)
        mx = (r_.random() * W0 + t * (1.5 + r_.random() * 2)) % W0
        my = 40 + r_.random() * 140 + 6 * math.sin(t * .5 + i)
        tw = .5 + .5 * math.sin(t * 2 + i * 2.3)
        out[int(my), int(mx)] = out[int(my), int(mx)] * (1 - .45 * tw) + C(1, .93, 1) * .45 * tw
    out = np.clip(out * 255, 0, 255).astype(np.uint8)
    big = out.repeat(S, 0).repeat(S, 1)
    return big.tobytes() if raw else Image.fromarray(big)


# ---------------------------------------------------------------- audio
def events():
    keys, mouse, prev = [], [], None
    for n in range(int(DUR * FPS)):
        pose = state(n / FPS)[0]
        if pose != prev and prev is not None:
            if 'kd' in pose: keys.append(n / FPS)
            if pose == 'ku_m1': mouse.append(n / FPS)
        prev = pose
    return keys, mouse


def build_audio(path):
    n = int(SR * DUR); out = np.zeros(n); mus = np.zeros(n)
    rng = np.random.default_rng(3)
    T = sfx.T

    def add(buf, sig, at, vol):
        i = int(at * SR) % n; j = min(n, i + len(sig))
        buf[i:j] += sig[:j - i] * vol
        if i + len(sig) > n: buf[:i + len(sig) - n] += sig[n - i:] * vol    # wrap -> seamless loop

    def ep(f, d, bright=.35):
        t = T(d)
        s = np.sin(2 * np.pi * f * t) + bright * np.sin(4 * np.pi * f * t) * np.exp(-t * 6) \
            + .12 * np.sin(6 * np.pi * f * t) * np.exp(-t * 9)
        return s * np.minimum(1, t / .012) * np.exp(-t * 1.3) * (1 + .12 * np.sin(2 * np.pi * 4.5 * t))
    mf = lambda m: 440 * 2 ** ((m - 69) / 12)
    bar = 4 * BEAT
    for b, ch in enumerate(([53, 57, 60, 64], [52, 55, 59, 62], [50, 53, 57, 60], [48, 52, 55, 59])):
        t0 = b * bar
        for k, m in enumerate(ch): add(mus, ep(mf(m), bar + .6), t0 + k * .02, .10)
        for k, m in enumerate(ch[1:]): add(mus, ep(mf(m), 1.4), t0 + 2.5 * BEAT + k * .015, .05)
        add(mus, ep(mf(ch[0] - 12), bar, .15), t0, .2)
        for beat in (0, 2.5):
            add(mus, sfx.sweep(95, 42, .35) * sfx.dec(.35, 11), t0 + beat * BEAT, .32)
        for beat in (1, 3):
            nz = rng.standard_normal(int(SR * .2))
            add(mus, sfx.lp(nz - sfx.lp(nz, 12), 3) * sfx.dec(.2, 22) + .4 * np.sin(2 * np.pi * 185 * T(.2)) * sfx.dec(.2, 30), t0 + beat * BEAT, .11)
        for h in range(8):
            nz = rng.standard_normal(int(SR * .05))
            add(mus, (nz - sfx.lp(nz, 4)) * sfx.dec(.05, 70), t0 + (h * .5 + (h % 2) * .09) * BEAT, .035)
    for beat, m in ((1, 72), (2.5, 69), (5.5, 71), (7, 67), (9, 69), (10.5, 65), (12.5, 67), (14, 64)):
        add(mus, ep(mf(m + 12), 1.6, .6), beat * BEAT, .045)
    mus = sfx.lp(mus, 7)                                     # lo-fi warmth
    out += mus
    nz = rng.standard_normal(n)
    rain = sfx.lp(nz, 3) - sfx.lp(nz, 28)
    out += rain * .07 * (1 + .15 * np.sin(2 * np.pi * np.arange(n) / n * 3))
    crack = np.zeros(n); idx = rng.integers(0, n, int(DUR * 7)); crack[idx] = rng.standard_normal(len(idx)) * .25
    out += sfx.lp(crack, 2) + rng.standard_normal(n) * .003
    for t0 in (2.85, 6.2):
        d = 3.0; nz = rng.standard_normal(int(SR * d))
        rum = sfx.lp(sfx.lp(nz, 260), 260) * 260 ** .5 * 2.2
        env = np.minimum(1, T(d) / .08) * np.exp(-T(d) * 1.4) * (.65 + .35 * np.sin(T(d) * 7) ** 2)
        add(out, rum * env, t0, .35)
    keys, mouse = events()
    for k in keys:
        nz = rng.standard_normal(int(SR * .03))
        click = (nz - sfx.lp(nz, 3)) * sfx.dec(.03, 160) + .5 * np.sin(2 * np.pi * 2400 * T(.03)) * sfx.dec(.03, 250)
        add(out, click, k, .05 + .03 * rng.random())
    for m in mouse:
        add(out, np.sin(2 * np.pi * 3200 * T(.012)) * sfx.dec(.012, 300), m, .06)
    add(out, sfx.sparkle(), 7.7, .22)
    out = out / np.abs(out).max() * .85
    st = np.stack([out, np.roll(out, 7)], 1)                 # tiny width
    with wave.open(path, 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((st * 32767).astype('<i2').tobytes())


if __name__ == '__main__':
    mode = sys.argv[1]
    if mode == 'still':
        for ts in sys.argv[3:]:
            frame(int(float(ts) * FPS), raw=False).save(f'{sys.argv[2]}/f_{ts}.png')
    elif mode == 'video':
        out = sys.argv[2]
        t0, t1 = (float(sys.argv[3]), float(sys.argv[4])) if len(sys.argv) > 4 else (0.0, DUR)
        build_audio('mix.wav')
        ff = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}',
                               '-r', str(FPS), '-i', '-', '-ss', str(t0), '-t', str(t1 - t0), '-i', 'mix.wav',
                               '-c:v', 'libx264', '-preset', 'medium', '-crf', '16', '-pix_fmt', 'yuv420p',
                               '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', '-shortest', out],
                              stdin=subprocess.PIPE)
        for i in range(int(t0 * FPS), int(t1 * FPS)):
            ff.stdin.write(frame(i))
        ff.stdin.close(); ff.wait()
        print('done', ff.returncode)
        raise SystemExit(ff.returncode)
