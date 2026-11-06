"""Grass-nap: seamless 1080x1920 pixel-art loop. Main guy + car buddy napping in a meadow.

python render.py still <t> <out.png>
python render.py video <out.mp4> [audio.wav] [seconds]
"""
import math
import subprocess
import sys
from functools import lru_cache

import numpy as np
from PIL import Image, ImageFilter

import sprites as S
from pix import hexc  # noqa: E402

W, H, SC = 180, 320, 6
FPS = 30
NFRAMES = 613
DUR = NFRAMES / FPS          # 20.433 s, same as the reference; every motion loops on DUR
BEATS = 32                   # music: 8 bars of 4/4 across DUR
BEAT = DUR / BEATS

RAMP = ['#143a37', '#1a4a40', '#225944', '#2c6447', '#386f49', '#447b48', '#548f44',
        '#6aa940', '#83c33f', '#9cd947', '#b2e957', '#c4f26c', '#d6f98a']
RAMP_A = np.array([hexc(c)[:3] for c in RAMP], np.uint8)

GUY = (68, 150)
BUDDY = (130, 183)
PLAYER = (114, 133)
HELMET = (60, 112)
MAG = (82, 184)


def tp(t, k=1):
    return 2 * math.pi * k * t / DUR


def noise(w, h, cell, seed):
    r = np.random.default_rng(seed).random((h // cell + 3, w // cell + 3))
    im = Image.fromarray((r * 255).astype(np.uint8)).resize(((w // cell + 3) * cell, (h // cell + 3) * cell), Image.BICUBIC)
    return np.asarray(im, np.float32)[cell:cell + h, cell:cell + w] / 255.0


def fbm(w, h, seed):
    return 0.5 * noise(w, h, 40, seed) + 0.3 * noise(w, h, 14, seed + 1) + 0.2 * noise(w, h, 5, seed + 2)


# ---------------------------------------------------------------- static layers

def light_field():
    """0 = deep tree shade, 1 = full sun. Same composition as the reference wallpaper."""
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    # diagonal shadow edge: from upper-left (x~22) sweeping to the lower-right (y~225)
    edge_y = 122 + 0.6 * x + 10 * np.sin(x / 13.0) + 6 * np.sin(x / 5.0)
    edge_x = 22 + 4 * np.sin(y / 11.0)
    d = np.minimum(edge_y - y, x - edge_x)               # >0 inside shade
    d = np.where(y < 72, np.minimum(d, (x - 8) * 0.6 + (72 - y) * 0.15), d)
    n = fbm(W, H, 7)
    L = 1 / (1 + np.exp((d + (n - 0.5) * 26) / 7.0))
    # sunny upper-left glade and bright bottom
    L = np.maximum(L, np.clip(1 - np.hypot(x / 70, y / 70), 0, 1) * 0.75)
    L = np.maximum(L, np.clip((y - 250) / 50, 0, 1) * 0.95)
    # darker under the trunk (top-right)
    L *= 1 - 0.35 * np.clip(1 - np.hypot((x - 175) / 70, (y - 30) / 90), 0, 1)
    L = 0.28 + 0.72 * L
    return np.clip(L, 0, 1), n


def _limb(g, pts, w0, w1, body, top, rim):
    n = len(pts) - 1
    for i in range(n):
        (x0, y0), (x1, y1) = pts[i], pts[i + 1]
        steps = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
        for k in range(steps):
            u = (i + k / steps) / n
            x = x0 + (x1 - x0) * k / steps; y = y0 + (y1 - y0) * k / steps
            w = w0 + (w1 - w0) * u
            g.disc(x, y, w, body)
    for i in range(n):
        (x0, y0), (x1, y1) = pts[i], pts[i + 1]
        steps = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
        for k in range(steps):
            u = (i + k / steps) / n
            x = x0 + (x1 - x0) * k / steps; y = y0 + (y1 - y0) * k / steps
            w = w0 + (w1 - w0) * u
            g.disc(x - w * 0.35, y - w * 0.45, w * 0.45, top)
            g.px(int(x - w * 0.75), int(y + w * 0.55), rim)


def tree(img):
    g = S.Grid(W, H)
    rng = np.random.default_rng(3)
    # trunk down the right side, roots fanning into the grass
    _limb(g, [(176, -4), (168, 40), (160, 80), (150, 108)], 16, 4, '#0d1d1a', '#152b25', '#2fd39a')
    _limb(g, [(176, 60), (172, 95), (166, 120)], 9, 2, '#0d1d1a', '#152b25', '#2fd39a')
    _limb(g, [(158, 70), (145, 90), (137, 104)], 5, 1.5, '#0d1d1a', '#152b25', '#2fd39a')
    # big mossy limb sweeping in from the top-left
    _limb(g, [(-10, 12), (28, 14), (66, 24), (100, 42), (122, 66)], 15, 5, '#28382a', '#465a36', '#7ff0b0')
    _limb(g, [(156, -6), (144, 22), (130, 52)], 9, 3, '#17271f', '#2a4031', '#3fe0a6')
    # bark grooves on the limb
    for k in range(4):
        for x in range(0, 118):
            y = 12 + x * 0.12 + (x / 118) ** 2 * 45 - 6 + k * 3 + math.sin(x / 7 + k) * 1.2
            if (x + k * 9) % 17 < 10 and g.g[int(y)][x] is not None:
                g.px(x, int(y), '#1e2c22' if k % 2 else '#3a4d30')
    # bark grooves
    for k in range(5):
        for y in range(0, 95):
            x = int(172 - y * 0.18 + k * 3 - 6 + 1.5 * math.sin((y + k * 4) / 6))
            if (y + k * 7) % 19 < 11 and g.g[min(H - 1, y)][min(W - 1, x)] is not None:
                g.px(x, y, '#1b3a31')
    # glowing teal leaves + moss clumps
    for _ in range(55):
        x = int(rng.integers(60, 160)); y = int(rng.integers(0, 24))
        c = ['#2fd3a8', '#62f0d6', '#1f9a7a', '#7cf7a0'][int(rng.integers(0, 4))]
        g.px(x, y, c)
        if rng.random() < 0.5:
            g.px(x + 1, y, c); g.px(x, y + 1, c)
    for _ in range(25):
        x = int(rng.integers(0, 110)); y = int(rng.integers(2, 16))
        if g.g[y][x] is not None:
            g.px(x, y, '#6f8c3e')
    img.alpha_composite(g.image(outline=True, oc=(10, 22, 18, 255)))


FLOWER_KINDS = ('daisy', 'butter', 'puff', 'violet', 'clover')


@lru_cache(None)
def flower_head(kind):
    g = S.Grid(13, 13)
    if kind == 'daisy':
        for (cx, cy) in ((6, 2.5), (9.3, 4.8), (8.2, 8.6), (3.8, 8.6), (2.7, 4.8)):
            g.disc(cx, cy, 2.1, '#fbfdf6')
        g.disc(6, 6, 2.6, '#fbfdf6')
        for (cx, cy) in ((8.2, 8.6), (3.8, 8.6)):
            g.px(int(cx), int(cy) + 1, '#d3e2c4')
        g.disc(6, 6, 1.6, '#ffd34d'); g.px(6, 6, '#f2a93b'); g.px(7, 7, '#f2a93b'); g.px(5, 5, '#fff3a6')
    elif kind == 'butter':
        for (cx, cy) in ((6, 3), (9, 5.5), (7.8, 8.8), (4.2, 8.8), (3, 5.5)):
            g.disc(cx, cy, 1.7, '#ffd84a')
        g.disc(6, 6.4, 2, '#ffd84a'); g.px(6, 6, '#f59b2b'); g.px(5, 5, '#fff3a8'); g.px(6, 3, '#fff3a8')
        g.px(8, 9, '#f0b23a'); g.px(4, 9, '#f0b23a')
    elif kind == 'puff':
        g.disc(6, 6, 3.6, '#d7f2b0'); g.disc(6, 6, 2.4, '#effcd8'); g.disc(5.5, 5.5, 1.1, '#ffffff')
    elif kind == 'violet':
        for (cx, cy) in ((6, 4), (8, 6), (6, 8), (4, 6)):
            g.disc(cx, cy, 1.3, '#b7a6ff')
        g.px(6, 6, '#fff3a0'); g.px(6, 3, '#e0d8ff'); g.px(7, 8, '#8f7de6'); g.px(5, 8, '#8f7de6')
    else:  # sprig: a little three-blade grass sprout
        for (x, y) in ((6, 4), (6, 5), (6, 6), (6, 7), (6, 8), (4, 6), (5, 7), (8, 5), (7, 7), (3, 5), (9, 4)):
            g.px(x, y, '#4fb447')
        g.px(6, 3, '#8be070'); g.px(3, 4, '#8be070'); g.px(9, 3, '#8be070')
        return g.image(outline=False)
    return g.image(outline=True, oc=(24, 70, 38, 255))


def plant_base(g, x, y, kind, rng, dark):
    leaf = '#2d8a3a' if not dark else '#1f5e38'
    leafhi = '#5ec24c' if not dark else '#32804c'
    if kind == 'clover':
        return
    g.rect(x, y, x, y + 5, leaf)
    for s in (-1, 1):
        if rng.random() < 0.85:
            for i in range(5):
                lx = x + s * (1 + i); ly = y + 4 - (1 if 1 <= i <= 3 else 0)
                g.px(lx, ly, leaf); g.px(lx, ly + 1, leaf)
                if 1 <= i <= 3: g.px(lx, ly - 1, leafhi if i == 2 else leaf)


@lru_cache(None)
def layout():
    """Background (static) + list of animated flower heads."""
    L, n = light_field()
    rng = np.random.default_rng(11)
    lv = L + (fbm(W, H, 21) - 0.5) * 0.18
    idx = np.clip((lv * (len(RAMP) - 1)).round().astype(int), 0, len(RAMP) - 1)
    patch = (noise(W, H, 9, 31) * 0.6 + noise(W, H, 4, 32) * 0.4) > 0.66      # darker grass clumps
    idx = np.where(patch & (L > 0.55), idx - 2, idx)
    idx = np.clip(idx, 0, len(RAMP) - 1)
    rgb = RAMP_A[idx]
    bg = Image.fromarray(rgb, 'RGB').convert('RGBA')
    g = S.Grid(W, H)
    # grass tufts and specks, coloured from the local ramp tone
    for _ in range(1800):
        x, y = int(rng.integers(0, W)), int(rng.integers(0, H))
        i = int(idx[y, x])
        up = RAMP[min(len(RAMP) - 1, i + 1)]; dn = RAMP[max(0, i - 1)]
        r = rng.random()
        if r < 0.45:
            g.px(x, y, up); g.px(x - 1, y - 1, up); g.px(x + 1, y - 1, up)
        elif r < 0.8:
            g.px(x, y, dn); g.px(x + 1, y, dn)
        else:
            g.px(x, y, up)
    for _ in range(700):                                    # bright pollen specks in the sun
        x, y = int(rng.integers(0, W)), int(rng.integers(120, H))
        if L[y, x] > 0.75:
            g.px(x, y, '#effbd0')
    bg.alpha_composite(g.image(outline=False))
    tree(bg)
    # pebbles / crystals
    g = S.Grid(W, H)
    for (x, y, c) in ((80, 38, '#b69ad6'), (68, 52, '#9c84c4'), (143, 263, '#d6b8f0'), (128, 266, '#c6a8e8'), (157, 316, '#c7a9ec')):
        g.rect(x - 4, y - 2, x + 4, y + 2, c); g.rect(x - 3, y - 3, x + 3, y + 3, c)
        g.rect(x - 2, y - 2, x + 1, y - 1, '#efe3ff'); g.rect(x - 3, y + 2, x + 3, y + 3, '#7d6aa8')
    bg.alpha_composite(g.image(outline=True, oc=(40, 60, 50, 255)))
    # flowers: denser in the sun, avoiding the nappers
    keep = [(GUY, 34), (BUDDY, 30), (PLAYER, 18), (HELMET, 16), (MAG, 18)]
    heads = []
    stems = S.Grid(W, H)
    tries = 0
    centers = [(int(rng.integers(0, W)), int(rng.integers(20, H))) for _ in range(26)]
    while len(heads) < 70 and tries < 40000:
        tries += 1
        cx0, cy0 = centers[int(rng.integers(0, len(centers)))]
        x, y = int(cx0 + rng.normal(0, 13)), int(cy0 + rng.normal(0, 10))
        if not (4 <= x < W - 4 and 8 <= y < H - 4):
            continue
        if x > 128 + y * 0.2 and y < 125:
            continue
        if any(math.hypot(x - cx, y - cy) < r for (cx, cy), r in keep):
            continue
        if any(abs(x - hx) < 11 and abs(y - hy) < 11 for hx, hy, *_ in heads):
            continue
        lt = L[y, x]
        if rng.random() > 0.18 + 0.82 * lt:
            continue
        r = rng.random()
        if lt < 0.5:
            kind = 'violet' if r < 0.35 else 'butter' if r < 0.6 else 'daisy' if r < 0.8 else 'clover'
        else:
            kind = 'daisy' if r < 0.4 else 'butter' if r < 0.62 else 'puff' if r < 0.78 else 'clover'
        plant_base(stems, x, y + 4, kind, rng, lt < 0.5)
        heads.append((x, y, kind, float(rng.random()), lt < 0.4))
    bg.alpha_composite(stems.image(outline=False))
    return bg, heads, L


# ---------------------------------------------------------------- dynamic pieces

def wind(t, x, y):
    tq = math.floor(t * 10) / 10                         # pixel-art 10 fps sway
    gust = 0.55 + 0.45 * math.sin(tp(tq, 3) + 1.0)
    return round(1.15 * gust * math.sin(tp(tq, 9) - x * 0.05 - y * 0.02))


def dapple(t):
    """Hard-edged sun flecks dropping through the leaves (native-res mask)."""
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    a = tp(t, 2); b = tp(t, 3)
    f = (np.sin(x * 0.13 + 1.6 * math.sin(a) + y * 0.05) * np.sin(y * 0.11 - 1.2 * math.cos(b) + x * 0.04)
         + 0.6 * np.sin((x + y) * 0.07 + 1.3 * math.sin(a + 1)))
    return f > 0.95


@lru_cache(None)
def static_shadowed():
    """Background with soft contact shadows under the sprites."""
    bg, heads, L = layout()
    a = np.asarray(bg, np.float32).copy()
    for spr, (cx, cy), k in ((S.guy_lying(), GUY, 0.62), (S.car_buddy(-15), BUDDY, 0.6),
                             (S.walkman(0), PLAYER, 0.7), (S.helmet(), HELMET, 0.66), (S.magazine(0), MAG, 0.75)):
        m = np.asarray(spr)[..., 3] > 0
        x0 = cx - spr.width // 2 + 2; y0 = cy - spr.height // 2 + 2
        for dy in range(m.shape[0]):
            for dx in range(m.shape[1]):
                if m[dy, dx] and 0 <= y0 + dy < H and 0 <= x0 + dx < W:
                    a[y0 + dy, x0 + dx, :3] *= k
    return Image.fromarray(a.astype(np.uint8), 'RGBA'), heads, L


def place(img, spr, c):
    img.alpha_composite(spr, (c[0] - spr.width // 2, c[1] - spr.height // 2))


def cable(img, a, b, t):
    g = S.Grid(W, H)
    n = 40
    for i in range(n + 1):
        u = i / n
        x = a[0] + (b[0] - a[0]) * u + 5 * math.sin(u * math.pi) + 2 * math.sin(u * 7)
        y = a[1] + (b[1] - a[1]) * u + 4 * math.sin(u * math.pi * 2)
        g.px(int(round(x)), int(round(y)), '#18231f')
    img.alpha_composite(g.image(outline=False))


def ear_point(spr, c):
    a = np.asarray(spr)
    ys, xs = np.where(np.all(a[..., :3] == hexc(S.CUP)[:3], axis=2))
    i = np.argmax(xs + ys * 0.3)
    return (c[0] - spr.width // 2 + int(xs[i]) + 1, c[1] - spr.height // 2 + int(ys[i]))


FLIPS = (2.2, 8.9, 14.6)
SPARKS = np.random.default_rng(5)
SPARK_LIST = [(float(SPARKS.uniform(0, DUR)), int(SPARKS.integers(4, W - 4)), int(SPARKS.integers(10, H - 6))) for _ in range(46)]
MOTES = [(float(SPARKS.uniform(0, 1)), float(SPARKS.uniform(0, 110)), float(SPARKS.uniform(0, 160)), float(SPARKS.uniform(0.6, 1.4))) for _ in range(26)]


def native(t):
    bg, heads, L = static_shadowed()
    img = bg.copy()
    # flower heads sway with the breeze
    for (x, y, kind, ph, dark) in heads:
        hd = flower_head(kind)
        dx = wind(t, x, y) if kind != 'clover' else wind(t, x, y) // 2
        img.alpha_composite(hd, (x - 6 + dx, y - 6))
    # props + nappers
    beat = (t / BEAT) % 1.0
    glow = 0.45 + 0.55 * math.exp(-beat * 3.5)
    spool = int(t * 8) % 6
    place(img, S.helmet(), HELMET)
    page = 0
    for f in FLIPS:
        k = int((t - f) / 0.1)
        if 0 <= k < 5:
            page = k + 1
    place(img, S.magazine(page), MAG)
    place(img, S.walkman(spool, round(glow, 1)), PLAYER)
    guy = S.guy_lying()
    place(img, guy, GUY)
    snore = 1 if (t % (DUR / 5)) / (DUR / 5) > 0.82 else 0
    place(img, S.car_buddy(-15, snore), BUDDY)
    wm = S.walkman(0)
    cable(img, ear_point(guy, GUY), (PLAYER[0] - wm.width // 2 + 0, PLAYER[1] + 12), t)
    # dappled sunlight (crisp, on the native grid)
    a = np.asarray(img, np.float32).copy()
    m = dapple(t) & (L < 0.85)
    a[m, :3] = a[m, :3] * 1.22 + np.array([18, 22, 4], np.float32)
    # twinkling glints
    for (t0, x, y) in SPARK_LIST:
        age = (t - t0) % DUR
        if age < 0.6:
            s = 1 if age < 0.15 or age > 0.45 else 2
            for dx, dy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)) + ((((2, 0), (-2, 0), (0, 2), (0, -2)) if s == 2 else ())):
                if 0 <= x + dx < W and 0 <= y + dy < H:
                    a[y + dy, x + dx, :3] = (250, 255, 225) if (dx, dy) == (0, 0) or s == 1 else (205, 240, 170)
    # drifting pollen in the sun shaft
    for (ph, x0, y0, sp) in MOTES:
        u = (t / DUR * sp * 2 + ph) % 1.0
        x = int(x0 + 25 * u + 3 * math.sin(tp(t, 4) + ph * 6)) % W
        y = int(y0 + 40 * u) % 200
        a[y, x, :3] = (255, 248, 200)
    return np.clip(a[..., :3], 0, 255).astype(np.uint8)


@lru_cache(None)
def overlays():
    y, x = np.mgrid[0:1920, 0:1080].astype(np.float32)
    glow = np.clip(1 - np.hypot(x / 900, y / 820), 0, 1) ** 1.15                     # warm sun, top-left
    rays = np.clip(np.sin((x * 0.8 - y * 0.6) / 70.0) * 0.5 + 0.5, 0, 1) ** 6 * glow
    vig = np.clip(np.hypot((x - 540) / 760, (y - 1010) / 1150), 0, 1) ** 2.2
    topshade = np.clip(1 - y / 900, 0, 1) * np.clip((x - 300) / 780, 0, 1)
    return glow, rays, vig, topshade


def frame(t):
    a = native(t)
    big = a.repeat(SC, 0).repeat(SC, 1).astype(np.float32)
    glow, rays, vig, topshade = overlays()
    pulse = 1 + 0.03 * math.sin(tp(t, 7))
    warm = np.array([255, 212, 0], np.float32)
    k = (0.85 * glow + 0.22 * rays * (0.8 + 0.2 * math.sin(tp(t, 2)))) * pulse
    big = big * (1 - k[..., None] * 0.55) + warm * k[..., None] * 0.55
    big *= (1 - 0.18 * vig - 0.12 * topshade)[..., None] * (1 + 0.025 * math.sin(tp(t, 7)))
    out = np.clip(big, 0, 255).astype(np.uint8)
    im = Image.fromarray(out)
    # soft bloom like the reference's dreamy haze
    bl = np.asarray(im.resize((270, 480), Image.BILINEAR).filter(ImageFilter.GaussianBlur(6)).resize((1080, 1920), Image.BILINEAR), np.float32)
    out = np.clip(out * 0.86 + np.maximum(bl - 70, 0) * 0.32 + out * 0.0, 0, 255)
    m = out.mean(2, keepdims=True)
    out = m + (out - m) * 1.22                       # punchier, like the reference's saturated greens
    out = out * np.array([0.9, 0.98, 0.92], np.float32)
    return np.clip(out, 0, 255).astype(np.uint8)


def video(path, audio=None, secs=DUR):
    n = int(round(secs * FPS))
    cmd = ['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '1080x1920', '-r', str(FPS), '-i', '-']
    if audio:
        cmd += ['-i', audio, '-c:a', 'aac', '-b:a', '192k', '-shortest']
    cmd += ['-c:v', 'libx264', '-preset', 'slow', '-crf', '16', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', path]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(n):
        p.stdin.write(frame(i / FPS).tobytes())
        if i % 60 == 0:
            print(f'frame {i}/{n}', flush=True)
    p.stdin.close()
    sys.exit(p.wait())


if __name__ == '__main__':
    if sys.argv[1] == 'still':
        Image.fromarray(frame(float(sys.argv[2]))).save(sys.argv[3])
    elif sys.argv[1] == 'video':
        video(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 and sys.argv[3] != '-' else None,
              float(sys.argv[4]) if len(sys.argv) > 4 else DUR)
