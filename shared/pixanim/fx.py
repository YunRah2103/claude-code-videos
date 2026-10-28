"""Reusable drawing helpers and effects for pixel scenes (draw onto RGBA layers).

blit() pastes a sprite with nearest-neighbour scaling; the rest are time-driven effects:
sparkles, confetti, dust, poof, light shafts (rays), shock rings, impact bursts, glints, stamps.
"""
import math
from functools import lru_cache
import numpy as np
from PIL import Image, ImageChops, ImageDraw
from . import sprites
from .grid import up
from .motion import clamp, prog, oc, ic, ob, io, jelly

NAVY = (26, 26, 46)


@lru_cache(None)
def big(name, *args, s=9):
    return up(getattr(sprites, name)(*args), s)


def blit(cv, img, cx, y, sx=1.0, sy=1.0, rot=0.0, anchor='bottom', flip=False):
    if sx <= 0.01 or sy <= 0.01: return
    if flip: img = img.transpose(Image.FLIP_LEFT_RIGHT)
    if sx != 1 or sy != 1:
        img = img.resize((max(1, int(img.width * sx)), max(1, int(img.height * sy))), Image.NEAREST)
    if rot:
        img = img.rotate(rot, resample=Image.NEAREST, expand=True)
    x = cx - img.width / 2
    y = y - img.height if anchor == 'bottom' else y - img.height / 2
    cv.paste(img, (int(round(x)), int(round(y))), img)


def popin(t, t0, d=0.28): return 0.0 if t < t0 else ob(prog(t, t0, d))
def popout(t, t0, d=0.2): return 1.0 if t < t0 else 1 - ic(prog(t, t0, d))
def slam(t, t0, d=0.14, k=1.6): return 1 + k * (1 - oc(prog(t, t0, d)))
def rng(seed): return np.random.default_rng(seed)
def snap(v, s=9): return round(v / s) * s


def contact_shadow(cv, cx, gy, w, k=1.0, s=9, alpha=120):
    w = w * k
    if w <= 2 * s: return
    d = ImageDraw.Draw(cv)
    d.rectangle((cx - w / 2 + s, gy - s, cx + w / 2 - s, gy + s), fill=(0, 0, 0, alpha))
    d.rectangle((cx - w / 2, gy - s // 2, cx + w / 2, gy + s // 2), fill=(0, 0, 0, alpha))


def sparkles(cv, t, cx, cy, w, h, n=6, seed=1, s=7):
    r = rng(seed)
    for i in range(n):
        x = cx + r.uniform(-w / 2, w / 2); y = cy + r.uniform(-h / 2, h / 2)
        v = math.sin(2 * math.pi * (t * r.uniform(1.2, 2.0) + r.uniform(0, 1)))
        if v > 0.3: blit(cv, big('sparkle', 1 if v > 0.75 else 0, s=s), x, y, anchor='center')


def gsparkles(cv, t, cx, cy, w, h, n=8, seed=31, col='#7fe3a0', s=8):
    r = rng(seed)
    for i in range(n):
        x = cx + r.uniform(-w / 2, w / 2); y = cy + r.uniform(-h / 2, h / 2)
        v = math.sin(2 * math.pi * (t * r.uniform(1.4, 2.2) + r.uniform(0, 1)))
        if v > 0.2:
            k = 0.6 + 0.6 * v
            blit(cv, big('star', col, s=s), x, y, k, k, anchor='center')


CONFETTI = [(255, 77, 109), (255, 210, 63), (61, 127, 214), (60, 200, 90), (255, 138, 61), (160, 100, 255)]
def confetti(cv, t, t0, x, y, n=40, seed=3, spread=1.0, s=9, life=2.4):
    dt = t - t0
    if dt < 0 or dt > life: return
    r = rng(seed); d = ImageDraw.Draw(cv)
    for i in range(n):
        vx = r.uniform(-650, 650) * spread; vy = r.uniform(-1700, -900)
        px = x + vx * dt; py = y + vy * dt + 0.5 * 2600 * dt * dt
        sz = s if (int((dt * 8 + i)) % 2) else s * 2
        d.rectangle((px, py, px + sz, py + s), fill=CONFETTI[i % len(CONFETTI)])


def dust(cv, t, t0, x, y, n=10, seed=5, life=0.6, dirx=0, s=9, col=(205, 205, 214)):
    dt = t - t0
    if dt < 0 or dt > life: return
    r = rng(seed); d = ImageDraw.Draw(cv); k = 1 - dt / life
    for i in range(n):
        vx = r.uniform(-500, 500) + dirx; vy = r.uniform(-260, -40)
        px = x + vx * dt; py = y + vy * dt
        q = s * (1 + int(2 * k * r.uniform(0.5, 1.5)))
        d.rectangle((px - q, py - q, px + q, py + q), fill=col, outline=NAVY, width=3)


def puff(cv, t, t0, x, y, seed=9, life=0.7, size=1.0, drift=(-120, -160), col=(170, 172, 180)):
    """Exhaust/smoke puff: a few pixel blobs that grow, rise and fade (alpha)."""
    dt = t - t0
    if dt < 0 or dt > life: return
    r = rng(seed); d = ImageDraw.Draw(cv); k = dt / life
    for i in range(5):
        ox, oy = r.uniform(-30, 30), r.uniform(-20, 20)
        rad = snap((18 + 34 * oc(k)) * size * r.uniform(0.7, 1.2))
        cx = x + ox + drift[0] * k; cy = y + oy + drift[1] * k
        a = int(200 * (1 - k) ** 1.4)
        d.ellipse((cx - rad, cy - rad, cx + rad, cy + rad), fill=col + (a,))


def poof(cv, t, t0, x, y, seed=9, life=0.55, scale=1.0):
    dt = t - t0
    if dt < 0 or dt > life: return
    r = rng(seed); d = ImageDraw.Draw(cv); k = dt / life
    for i in range(7):
        a = i / 7 * 2 * math.pi + r.uniform(0, 0.5)
        dist = (40 + 200 * oc(k)) * scale
        rad = (70 + r.uniform(0, 40)) * (1 - k) ** 0.7 * (0.6 + 0.6 * oc(min(1, k * 4))) * scale
        cx, cy = x + math.cos(a) * dist, y + math.sin(a) * dist * 0.7
        d.ellipse((cx - rad, cy - rad, cx + rad, cy + rad), fill=(245, 245, 248), outline=NAVY, width=7)


def rays(cv, t, t0, x, y, col, life=0.8, hold=False, r=560, n=10):
    """Rotating sunburst; pass an RGBA col with low alpha for a translucent light shaft."""
    dt = t - t0
    if dt < 0 or (not hold and dt > life): return
    k = oc(min(1.0, dt / 0.25)) * (1 if hold else 1 - ic(prog(t, t0 + life - 0.25, 0.25)))
    if k <= 0.02: return
    d = ImageDraw.Draw(cv); R = r * k; rot = dt * 22
    for i in range(n):
        a0 = rot + i * 360 / n
        d.pieslice((x - R, y - R, x + R, y + R), a0, a0 + 140 / n, fill=col)


def ring(cv, t, t0, x, y, col, life=0.35, r1=330, s=9):
    dt = t - t0
    if dt < 0 or dt > life: return
    p = oc(dt / life); R = 40 + r1 * p
    ImageDraw.Draw(cv).ellipse((x - R, y - R, x + R, y + R), outline=col, width=max(3, int(3 * s * (1 - p))))


def burst(cv, t, t0, x, y, col=(255, 210, 63), n=12, life=0.42, r0=150, r1=430, seed=71, s=9):
    dt = t - t0
    if dt < 0 or dt > life: return
    p = oc(dt / life); d = ImageDraw.Draw(cv); r = rng(seed)
    for i in range(n):
        a = i / n * 2 * math.pi + r.uniform(-0.15, 0.15)
        R = r0 + (r1 - r0) * p * r.uniform(0.8, 1.15); L = 70 * (1 - p) + 12
        x0, y0 = x + R * math.cos(a), y + R * math.sin(a)
        x1, y1 = x + (R + L) * math.cos(a), y + (R + L) * math.sin(a)
        wd = int(2 * s * (1 - p)) + 4
        d.line((x0, y0, x1, y1), fill=NAVY, width=wd + 6)
        d.line((x0, y0, x1, y1), fill=col, width=wd)


@lru_cache(None)
def _disc_mask(r):
    m = Image.new('L', (2 * r, 2 * r), 0)
    ImageDraw.Draw(m).ellipse((0, 0, 2 * r - 1, 2 * r - 1), fill=255)
    return m


def glint(cv, t, t0, cx, cy, r=172, life=0.45):
    """Diagonal shine sweeping across round glass (gauges, lenses)."""
    if not (t0 <= t < t0 + life): return
    u = io((t - t0) / life); r = int(r)
    band = Image.new('L', (2 * r, 2 * r), 0); d = ImageDraw.Draw(band)
    x = -1.4 * r + 4 * r * u
    for off, w, a in ((0, 46, 120), (70, 18, 90)):
        d.polygon([(x + off, 0), (x + off + w, 0), (x + off + w - 1.2 * r, 2 * r), (x + off - 1.2 * r, 2 * r)], fill=a)
    band = ImageChops.multiply(band, _disc_mask(r))
    cv.paste(Image.new('RGBA', (2 * r, 2 * r), (255, 255, 255, 255)), (int(cx - r), int(cy - r)), band)


def stamp_at(cv, t, t0, text, x, y, rot=-10, s=12, col='#e0303a'):
    """Stamp with a white fill so it reads over anything; slams down, then wobbles like jelly."""
    if t < t0: return
    ks = slam(t, t0, 0.14, 1.8); j = 0.09 * jelly(t, t0 + 0.14)
    ring(cv, t, t0 + 0.12, x, y, (255, 210, 63))
    blit(cv, big('stamp', text, col, '#ffffff', s=s), x, y, ks * (1 + j), ks * (1 - j), rot, anchor='center')


def flakes(cv, t, t0, x, y, n=9, seed=61, spread=300, life=1.5, rise=420, s=5, t1=None):
    """Snowflakes drifting out of a vent."""
    if t < t0 or (t1 is not None and t > t1 + life): return
    r = rng(seed)
    for i in range(n):
        ph = r.uniform(0, 1); vx = r.uniform(-1, 1) * spread
        dt = t - t0 - ph * 0.5
        if dt < 0: continue
        born = t - (dt % life)
        if t1 is not None and born > t1: continue
        u = (dt % life) / life
        px = x + vx * u + 22 * math.sin(dt * 5 + i); py = y - rise * u
        k = math.sin(math.pi * u) * (0.8 + 0.4 * (i % 2))
        blit(cv, big('snowflake', s=s), px, py, k, k, anchor='center')


def speed_lines(cv, k, seed, horizontal=True, col=(150, 156, 170), w=1080, h=1920, s=9):
    if k < 0.1: return
    r = rng(100 + seed); d = ImageDraw.Draw(cv)
    for i in range(18):
        a = snap(r.uniform(240, (h if horizontal else w) - 220)); L = r.uniform(220, 640) * k
        b = r.uniform(-200, (w if horizontal else h))
        if horizontal: d.rectangle((b, a, b + L, a + s * (1 + i % 2)), fill=col)
        else: d.rectangle((a, b, a + s * (1 + i % 2), b + L), fill=col)
