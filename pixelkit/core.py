"""pixelkit: genuine pixel-art video rendering on a native low-res grid.

Everything is drawn into a uint8 *index* canvas at native resolution
(180x320 by default). Index 255 is transparent in sprites. Colour only exists
at the very end, through a palette lookup, so a frame can never contain more
colours than the palette. Lighting = remapping indices (palette swap).
"""
import json
import math
import os
import subprocess

import numpy as np
from PIL import Image, ImageDraw, ImageFont

T = 255  # transparent index
HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(HERE, "fonts")

# ---------------------------------------------------------------- palette ---
# ENDESGA 32 by Endesga (lospec.com/palette-list/endesga-32), free to use.
# PICO-8 16 by Lexaloffle, colour values widely reused.
PALETTES = {
    "endesga32": (
        "be4a2f d77643 ead4aa e4a672 b86f50 733e39 3e2731 a22633 e43b44 f77622 "
        "feae34 fee761 63c74d 3e8948 265c42 193c3e 124e89 0099db 2ce8f5 ffffff "
        "c0cbdc 8b9bb4 5a6988 3a4466 262b44 181425 ff0044 68386c b55088 f6757a "
        "e8b796 c28569"),
    "pico8": (
        "000000 1d2b53 7e2553 008751 ab5236 5f574f c2c3c7 fff1e8 ff004d ffa300 "
        "ffec27 00e436 29adff 83769c ff77a8 ffccaa"),
}


class Palette:
    """Named palette. `pal["e43b44"]` or `pal[3]` gives an index."""

    def __init__(self, name="endesga32"):
        self.name = name
        hexes = PALETTES[name].split()
        self.hex = hexes
        self.rgb = np.array([[int(h[i:i + 2], 16) for i in (0, 2, 4)] for h in hexes], np.uint8)
        self.lut = np.zeros((256, 3), np.uint8)
        self.lut[:len(hexes)] = self.rgb

    def __len__(self):
        return len(self.hex)

    def __getitem__(self, k):
        return k if isinstance(k, int) else self.hex.index(k.lower().lstrip("#"))

    def to_rgb(self, idx):
        return self.lut[idx]

    def remap(self, pairs):
        """Build an index->index LUT (a palette swap) from {src: dst}."""
        lut = np.arange(256, dtype=np.uint8)
        for s, d in pairs.items():
            lut[self[s]] = self[d]
        return lut

    def ffmpeg_palette_png(self, path):
        """16x16 = 256 px palette image for paletteuse (colours repeated)."""
        reps = np.resize(self.rgb, (256, 3)).reshape(16, 16, 3)
        Image.fromarray(reps).save(path)
        return path


# ----------------------------------------------------------------- sprites ---
def sprite(rows, key):
    """ASCII art -> index array. `key` maps chars to indices; '.' and ' ' are
    transparent. Rows may be a multi-line string or a list."""
    if isinstance(rows, str):
        rows = [r.strip() for r in rows.strip("\n").splitlines() if r.strip()]
    w = max(len(r) for r in rows)
    a = np.full((len(rows), w), T, np.uint8)
    for y, r in enumerate(rows):
        for x, ch in enumerate(r):
            if ch not in ". ":
                a[y, x] = key[ch]
    return a


def outline(spr, c, diagonal=False):
    """Add a 1px outline in colour c around the opaque area (grows by 1px)."""
    a = np.pad(spr, 1, constant_values=T)
    m = a != T
    o = np.zeros_like(m)
    shifts = [(0, 1), (0, -1), (1, 0), (-1, 0)]
    if diagonal:
        shifts += [(1, 1), (1, -1), (-1, 1), (-1, -1)]
    for dy, dx in shifts:
        o |= np.roll(np.roll(m, dy, 0), dx, 1)
    a[o & ~m] = c
    return a


def flip(spr, h=True):
    return spr[:, ::-1] if h else spr[::-1]


def recolor(spr, pairs):
    a = spr.copy()
    for s, d in pairs.items():
        a[spr == s] = d
    return a


class Canvas:
    """Index canvas. All coordinates are rounded to integers on entry."""

    def __init__(self, w, h, fill=0):
        self.w, self.h = w, h
        self.a = np.full((h, w), fill, np.uint8)

    def copy(self):
        c = Canvas(self.w, self.h)
        c.a = self.a.copy()
        return c

    def px(self, x, y, c):
        x, y = int(round(x)), int(round(y))
        if 0 <= x < self.w and 0 <= y < self.h:
            self.a[y, x] = c

    def rect(self, x, y, w, h, c):
        x, y, w, h = (int(round(v)) for v in (x, y, w, h))
        x0, y0, x1, y1 = max(0, x), max(0, y), min(self.w, x + w), min(self.h, y + h)
        if x1 > x0 and y1 > y0:
            self.a[y0:y1, x0:x1] = c

    def box(self, x, y, w, h, fill, line=None, top=None, shade=None):
        """Bevelled prop box: fill, 1px outline, light top row, dark bottom."""
        self.rect(x, y, w, h, line if line is not None else fill)
        o = 1 if line is not None else 0
        self.rect(x + o, y + o, w - 2 * o, h - 2 * o, fill)
        if top is not None:
            self.rect(x + o, y + o, w - 2 * o, 1, top)
        if shade is not None:
            self.rect(x + o, y + h - o - 1, w - 2 * o, 1, shade)

    def line(self, x0, y0, x1, y1, c):
        """Bresenham, integer endpoints, no antialias."""
        x0, y0, x1, y1 = (int(round(v)) for v in (x0, y0, x1, y1))
        dx, dy = abs(x1 - x0), -abs(y1 - y0)
        sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
        err = dx + dy
        while True:
            self.px(x0, y0, c)
            if x0 == x1 and y0 == y1:
                return
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def _pil(self, fn):
        im = Image.fromarray(self.a, "L")
        fn(ImageDraw.Draw(im))
        self.a = np.asarray(im).copy()

    def ellipse(self, x, y, w, h, fill=None, line=None):
        box = [int(x), int(y), int(x) + int(w) - 1, int(y) + int(h) - 1]
        self._pil(lambda d: d.ellipse(box, fill=fill, outline=line))

    def poly(self, pts, fill=None, line=None):
        pts = [(int(round(a)), int(round(b))) for a, b in pts]
        self._pil(lambda d: d.polygon(pts, fill=fill, outline=line))

    def blit(self, spr, x, y, lut=None):
        x, y = int(round(x)), int(round(y))
        h, w = spr.shape
        sx0, sy0 = max(0, -x), max(0, -y)
        sx1, sy1 = min(w, self.w - x), min(h, self.h - y)
        if sx1 <= sx0 or sy1 <= sy0:
            return
        src = spr[sy0:sy1, sx0:sx1]
        if lut is not None:
            src = np.where(src == T, T, lut[src])
        dst = self.a[y + sy0:y + sy1, x + sx0:x + sx1]
        m = src != T
        dst[m] = src[m]

    def mask(self, m, c):
        self.a[m] = c

    def remap(self, lut, where=None):
        """Palette swap the whole canvas, or only where `where` is True."""
        if where is None:
            self.a = lut[self.a]
        else:
            self.a = np.where(where, lut[self.a], self.a)

    def text(self, font, s, x, y, c, outline_c=None, shadow_c=None, align="left", spacing=1):
        m = font.mask(s, spacing)
        h, w = m.shape
        x = int(round(x - (w // 2 if align == "center" else w if align == "right" else 0)))
        y = int(round(y))
        spr = np.where(m, np.uint8(c), np.uint8(T))
        if outline_c is not None:
            spr2 = outline(spr, outline_c, diagonal=True)
            if shadow_c is not None:
                self.blit(np.where(spr2 != T, np.uint8(shadow_c), np.uint8(T)), x - 1, y)
            self.blit(spr2, x - 1, y - 1)
        else:
            if shadow_c is not None:
                self.blit(np.where(spr != T, np.uint8(shadow_c), np.uint8(T)), x, y + 1)
            self.blit(spr, x, y)
        return w, h


def tilemap(canvas, rows, tiles, x0=0, y0=0, size=8):
    """Draw a char grid of tiles. `tiles` maps chars to index arrays."""
    for ty, r in enumerate(rows):
        for tx, ch in enumerate(r):
            if ch in tiles:
                canvas.blit(tiles[ch], x0 + tx * size, y0 + ty * size)


# -------------------------------------------------------------------- text ---
class PixelFont:
    """TTF pixel font rendered 1-bit (fontmode '1') at native resolution."""

    def __init__(self, path=None, size=10):
        self.path = path or os.path.join(FONT_DIR, "PixelifySans-Medium.ttf")
        self.f = ImageFont.truetype(self.path, size)
        self.size = size
        self._cache = {}

    def mask(self, s, spacing=1):
        key = (s, spacing)
        if key not in self._cache:
            l, t, r, b = self.f.getbbox(s)
            im = Image.new("1", (r - l + 2, b - t + 2), 0)
            d = ImageDraw.Draw(im)
            d.fontmode = "1"
            d.text((-l, -t), s, font=self.f, fill=1)
            m = np.asarray(im, bool)
            ys, xs = np.nonzero(m)
            self._cache[key] = m[:ys.max() + 1, :xs.max() + 1] if len(xs) else m
        return self._cache[key]


# Hand-coded 3x5 fallback font (digits, caps, a few symbols).
_G = {
    "A": "010101111101101", "B": "110101110101110", "C": "011100100100011",
    "D": "110101101101110", "E": "111100110100111", "F": "111100110100100",
    "G": "011100101101011", "H": "101101111101101", "I": "111010010010111",
    "J": "001001001101010", "K": "101101110101101", "L": "100100100100111",
    "M": "101111111101101", "N": "110101101101101", "O": "010101101101010",
    "P": "110101110100100", "Q": "010101101110011", "R": "110101110101101",
    "S": "011100010001110", "T": "111010010010010", "U": "101101101101111",
    "V": "101101101101010", "W": "101101111111101", "X": "101101010101101",
    "Y": "101101010010010", "Z": "111001010100111", "0": "111101101101111",
    "1": "010110010010111", "2": "110001010100111", "3": "110001010001110",
    "4": "101101111001001", "5": "111100110001110", "6": "011100111101111",
    "7": "111001010010010", "8": "111101111101111", "9": "111101111001110",
    " ": "000000000000000", ".": "000000000000010", ",": "000000000010100",
    "!": "010010010000010", "?": "110001010000010", "%": "101001010100101",
    "-": "000000111000000", ":": "000010000010000", "'": "010010000000000",
    "+": "000010111010000", "=": "000111000111000", "/": "001001010100100",
    "@": "010101111100011", "_": "000000000000111",
}


class BitmapFont:
    """3x5 hand-coded bitmap font (no external files needed)."""
    size = 5

    def mask(self, s, spacing=1):
        s = s.upper()
        w = max(1, len(s) * (3 + spacing) - spacing)
        m = np.zeros((5, w), bool)
        for i, ch in enumerate(s):
            g = _G.get(ch, _G["?"])
            m[:, i * (3 + spacing):i * (3 + spacing) + 3] = np.array([c == "1" for c in g]).reshape(5, 3)
        return m


# ------------------------------------------------------------------ camera ---
class Camera:
    """Integer camera. Positions are rounded when set; shake is integer."""

    def __init__(self, x=0, y=0):
        self.x, self.y = int(x), int(y)

    def set(self, x, y):
        self.x, self.y = int(round(x)), int(round(y))

    def view(self, world, w, h, shake=(0, 0)):
        """Return a w x h integer crop of a world canvas."""
        x = min(max(0, self.x + shake[0]), world.w - w)
        y = min(max(0, self.y + shake[1]), world.h - h)
        c = Canvas(w, h)
        c.a = world.a[y:y + h, x:x + w].copy()
        return c


def shake(step, amp=1, seed=7):
    """Deterministic integer shake offset for a given animation step."""
    r = np.random.default_rng(seed * 100003 + step)
    return tuple(int(v) for v in r.integers(-amp, amp + 1, 2))


# --------------------------------------------------------------- particles ---
class Particles:
    """Integer particles advanced once per animation step (never per output
    frame). Velocity is in whole pixels per step; `every` slows a particle
    down by moving it only on some steps, which keeps motion on the grid."""

    def __init__(self, seed=1):
        self.p = []
        self.rng = np.random.default_rng(seed)

    def emit(self, x, y, vx, vy, life, colours, every=1):
        self.p.append(dict(x=int(x), y=int(y), vx=int(vx), vy=int(vy), life=int(life),
                           age=0, colours=list(colours), every=max(1, int(every))))

    def step(self, bounds=None):
        for q in self.p:
            q["age"] += 1
            if q["age"] % q["every"] == 0:
                q["x"] += q["vx"]
                q["y"] += q["vy"]
        if bounds:
            x0, y0, x1, y1 = bounds
            self.p = [q for q in self.p if x0 <= q["x"] < x1 and y0 <= q["y"] < y1]
        self.p = [q for q in self.p if q["age"] < q["life"]]

    def draw(self, canvas, ox=0, oy=0, shape=None):
        for q in self.p:
            cs = q["colours"]
            c = cs[min(len(cs) - 1, q["age"] * len(cs) // max(1, q["life"]))]
            if shape is None:
                canvas.px(q["x"] - ox, q["y"] - oy, c)
            else:
                canvas.blit(np.where(shape != T, np.uint8(c), np.uint8(T)), q["x"] - ox, q["y"] - oy)


# ------------------------------------------------------------------- clock ---
class StepClock:
    """Maps output frames to stepped animation 'steps'.

    `holds` is a repeating pattern of how many output frames each unique
    frame is held (uneven, e.g. 3,2,4,3 at 30fps ~= 10 unique fps). The scene
    is evaluated once per step at the step's start time `t`; frames between
    are exact duplicates. Nothing is interpolated.
    """

    def __init__(self, duration, fps=30, holds=(3, 3, 2, 4, 3, 3, 2, 4, 3, 3)):
        self.fps, self.n = fps, int(round(duration * fps))
        self.step_of, self.starts = [], []
        i = k = 0
        while i < self.n:
            self.starts.append(i)
            for _ in range(holds[k % len(holds)]):
                if i < self.n:
                    self.step_of.append(k)
                    i += 1
            k += 1
        self.steps = k

    def t(self, step):
        return self.starts[step] / self.fps


def cycle(t, durations):
    """Sprite-anim frame index for time t with uneven per-frame durations (s)."""
    total = sum(durations)
    x = t % total
    for i, d in enumerate(durations):
        if x < d:
            return i
        x -= d
    return len(durations) - 1


def tween_int(t, t0, t1, a, b, ease=None):
    """Integer position between a and b for time t (evaluated per step)."""
    if t <= t0:
        return int(a)
    if t >= t1:
        return int(b)
    u = (t - t0) / (t1 - t0)
    if ease == "out":
        u = 1 - (1 - u) ** 2
    elif ease == "inout":
        u = u * u * (3 - 2 * u)
    return int(round(a + (b - a) * u))


# ---------------------------------------------------------------- rotation ---
def scale2x(a):
    """EPX/Scale2x on an index array (exact colours, no blending)."""
    p = np.pad(a, 1, mode="edge")
    B, D, E, F, H = p[:-2, 1:-1], p[1:-1, :-2], p[1:-1, 1:-1], p[1:-1, 2:], p[2:, 1:-1]
    c = (B != H) & (D != F)
    e0 = np.where(c & (D == B), D, E)
    e1 = np.where(c & (B == F), F, E)
    e2 = np.where(c & (D == H), D, E)
    e3 = np.where(c & (H == F), F, E)
    out = np.empty((a.shape[0] * 2, a.shape[1] * 2), a.dtype)
    out[0::2, 0::2], out[0::2, 1::2], out[1::2, 0::2], out[1::2, 1::2] = e0, e1, e2, e3
    return out


def rotsprite(spr, deg):
    """RotSprite-style: Scale2x x3, nearest rotate, take block centres /8."""
    pad = int(math.ceil(max(spr.shape) * 0.5)) + 1
    a = np.pad(spr, pad, constant_values=T)
    for _ in range(3):
        a = scale2x(a)
    im = Image.fromarray(a, "L").rotate(-deg, resample=Image.NEAREST, fillcolor=T)
    big = np.asarray(im)
    small = big[3::8, 3::8]
    return small, (pad, pad)


def bake_rotations(spr, n=16):
    """Pre-bake n angles. Returns list of (array, (cx, cy) centre offset)."""
    out = []
    for i in range(n):
        a, _ = rotsprite(spr, 360.0 * i / n)
        out.append((a, (a.shape[1] // 2, a.shape[0] // 2)))
    return out


def angle_index(deg, n=16):
    return int(round((deg % 360) / (360.0 / n))) % n


# ------------------------------------------------------------------ render ---
def _ffmpeg_cmd(w, h, scale, fps, out, master, crf, size=None):
    ow, oh = w * scale, h * scale
    cm = "out_color_matrix=bt709:out_range=tv"
    meta = ["-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
            "-color_range", "tv"]
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{w}x{h}", "-r", str(fps), "-i", "-"]
    if master:
        cmd += ["-filter_complex",
                # split BEFORE scaling so each branch converts RGB->YUV in one
                # nearest-neighbour scale (no auto-inserted bicubic converter)
                f"[0:v]split=2[a][b];"
                f"[a]scale={ow}:{oh}:flags=neighbor:{cm},format=yuv420p[u];"
                f"[b]scale={ow}:{oh}:flags=neighbor:{cm},format=yuv444p[m]",
                "-map", "[u]"]
    else:
        cmd += ["-vf", f"scale={ow}:{oh}:flags=neighbor:{cm},format=yuv420p"]
    x264 = ["-c:v", "libx264", "-preset", "slow", "-tune", "animation"]
    cmd += x264 + ["-crf", str(crf), "-pix_fmt", "yuv420p", "-profile:v", "high"] + meta + [
        "-movflags", "+faststart", out]
    if master:
        cmd += ["-map", "[m]"] + x264 + ["-crf", str(max(0, crf - 4)), "-pix_fmt", "yuv444p",
                                          "-profile:v", "high444"] + meta + [master]
    return cmd


def render(scene, clock, palette, out, scale=6, master=None, native_dir=None, crf=14):
    """Render scene(step, t) -> Canvas (native index canvas) to MP4.

    The scene is called once per step; its frame is duplicated for every
    output frame in that step. Frames are piped as raw RGB at native size and
    upscaled by ffmpeg with an integer nearest-neighbour scale only.
    native_dir receives one PNG per unique step + frames.json (for verify).
    """
    first = scene(0, clock.t(0))
    w, h = first.w, first.h
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    if native_dir:
        os.makedirs(native_dir, exist_ok=True)
        for f in os.listdir(native_dir):
            if f.endswith(".png"):
                os.remove(os.path.join(native_dir, f))
    p = subprocess.Popen(_ffmpeg_cmd(w, h, scale, clock.fps, out, master, crf), stdin=subprocess.PIPE)
    last, buf = None, None
    for i in range(clock.n):
        s = clock.step_of[i]
        if s != last:
            cv = first if s == 0 else scene(s, clock.t(s))
            assert (cv.w, cv.h) == (w, h) and cv.a.dtype == np.uint8
            assert int(cv.a.max()) < len(palette), "transparent/out-of-palette index in frame"
            rgb = palette.to_rgb(cv.a)
            buf = np.ascontiguousarray(rgb).tobytes()
            if native_dir:
                Image.fromarray(rgb).save(os.path.join(native_dir, f"{s:04d}.png"))
            last = s
        p.stdin.write(buf)
    p.stdin.close()
    if p.wait():
        raise RuntimeError("ffmpeg failed")
    if native_dir:
        with open(os.path.join(native_dir, "frames.json"), "w") as fh:
            json.dump(dict(size=[w, h], scale=scale, fps=clock.fps, step_of=clock.step_of), fh)
    return out


def still(canvas, palette, path, zoom=1):
    """Save a native canvas as PNG, optionally integer-zoomed (nearest)."""
    rgb = palette.to_rgb(canvas.a)
    im = Image.fromarray(rgb)
    if zoom > 1:
        im = im.resize((canvas.w * zoom, canvas.h * zoom), Image.NEAREST)
    im.save(path)
    return path


# ----------------------------------------------------------- organic detail ---
# Helpers that keep hand-made irregularity: wobbly silhouettes, clustered
# ramp shading with hue-shifted tones, surface textures, nearest-neighbour
# rotation at native resolution, pixel-perfect cables and clutter.

def wobble_mask(w, h, rng, depth=1, seg=(3, 8), chip=(1, 3), sides="tblr"):
    """w x h bool mask whose edges are inset by 0..depth px in random runs of
    `seg` length, with chipped corners. No straight edge longer than seg[1]."""
    m = np.ones((h, w), bool)

    def runs(n):
        # long sides get longer, calmer runs (still <= 17 px between jogs)
        lo, hi = max(seg[0], min(10, n // 6)), max(seg[1], min(17, n // 4))
        out, i = [], 0
        while i < n:
            k = int(rng.integers(lo, hi + 1))
            out.append((i, min(n, i + k), int(rng.integers(0, depth + 1))))
            i += k
        # never two neighbouring runs at the same depth -> edge always breaks
        for j in range(1, len(out)):
            if out[j][2] == out[j - 1][2]:
                a, b, d = out[j]
                out[j] = (a, b, (d + 1) % (depth + 1))
        return out
    for a, b, d in runs(w) if "t" in sides else []:
        m[:d, a:b] = False
    for a, b, d in runs(w) if "b" in sides else []:
        m[h - d:, a:b] = False
    for a, b, d in runs(h) if "l" in sides else []:
        m[a:b, :d] = False
    for a, b, d in runs(h) if "r" in sides else []:
        m[a:b, w - d:] = False
    for cy, cx, sy, sx in ((0, 0, 1, 1), (0, w - 1, 1, -1), (h - 1, 0, -1, 1), (h - 1, w - 1, -1, -1)):
        k = int(rng.integers(chip[0], chip[1] + 1))
        for i in range(k):
            for j in range(k - i):
                yy, xx = cy + sy * i, cx + sx * j
                if 0 <= yy < h and 0 <= xx < w:
                    m[yy, xx] = False
    return m


def blob_mask(w, h, rng, rough=1):
    """Irregular ellipse-like mask (bean bags, cushions, crumpled cloth)."""
    yy, xx = np.mgrid[0:h, 0:w]
    ang = np.arctan2(yy - (h - 1) / 2, xx - (w - 1) / 2)
    k = rng.integers(3, 6)
    ph = rng.uniform(0, 6.3, 2)
    r = 1 + rough * 0.08 * (np.sin(k * ang + ph[0]) + 0.6 * np.sin((k + 2) * ang + ph[1]))
    d = ((xx - (w - 1) / 2) / (w / 2)) ** 2 + ((yy - (h - 1) / 2) / (h / 2)) ** 2
    return d <= r * r


def _shift(m, dy, dx):
    o = np.zeros_like(m)
    h, w = m.shape
    o[max(0, dy):h + min(0, dy), max(0, dx):w + min(0, dx)] = \
        m[max(0, -dy):h - max(0, dy), max(0, -dx):w - max(0, dx)]
    return o


def shade(mask, ramp, line=None, band=2):
    """Clustered ramp shading of a mask lit from the top-left.
    ramp = [deep shadow (cool), shadow, base, highlight (warm)]."""
    a = np.full(mask.shape, T, np.uint8)
    a[mask] = ramp[2]
    lit = mask & ~_shift(mask, 1, 1)
    sh = mask & ~_shift(mask, -band, -band)
    deep = mask & ~_shift(mask, -1, -1)
    a[sh] = ramp[1]
    a[deep] = ramp[0]
    a[lit & ~deep] = ramp[3]
    if line is not None:
        o = outline(a, line)
        return o
    return a


def _tone(a, ys, xs, ramp, delta):
    pos = {c: i for i, c in enumerate(ramp)}
    for y, x in zip(ys, xs):
        if 0 <= y < a.shape[0] and 0 <= x < a.shape[1] and a[y, x] in pos:
            a[y, x] = ramp[max(0, min(len(ramp) - 1, pos[a[y, x]] + delta))]


def texture(a, ramp, rng, kind="noise", density=0.04, mask=None):
    """Add surface texture in place on an index sprite/canvas array.
    kinds: noise (2-4 px clusters), grain (short streaks), weave (checker
    patches), dither (2-tone checker patches), wrinkle (short folds with a
    highlight), specks (single pixels)."""
    h, w = a.shape
    m = np.isin(a, ramp) if mask is None else mask & np.isin(a, ramp)
    ys, xs = np.nonzero(m)
    if not len(ys):
        return a
    n = max(1, int(len(ys) * density / (3 if kind != "specks" else 1)))
    pick = rng.integers(0, len(ys), n)
    for y, x in zip(ys[pick], xs[pick]):
        d = int(rng.choice([-1, 1]))
        if kind == "noise":
            py, px = [y], [x]
            for _ in range(int(rng.integers(1, 4))):
                y2, x2 = py[-1] + int(rng.integers(-1, 2)), px[-1] + int(rng.integers(-1, 2))
                py.append(y2); px.append(x2)
            _tone(a, py, px, ramp, d)
        elif kind == "specks":
            _tone(a, [y], [x], ramp, d)
        elif kind == "grain":
            L = int(rng.integers(2, 6))
            vert = rng.random() < 0.5
            _tone(a, [y + (i if vert else 0) for i in range(L)],
                  [x + (0 if vert else i) for i in range(L)], ramp, -1)
        elif kind in ("weave", "dither"):
            ph, pw = int(rng.integers(2, 4)), int(rng.integers(3, 6))
            cy, cx = [], []
            for i in range(ph):
                for j in range(pw):
                    if (i + j) % 2 == 0:
                        cy.append(y + i); cx.append(x + j)
            _tone(a, cy, cx, ramp, -1 if kind == "dither" else d)
        elif kind == "wrinkle":
            L = int(rng.integers(3, 7))
            sx = int(rng.choice([-1, 1]))
            py = [y + i for i in range(L)]
            px = [x + sx * (i // 2) for i in range(L)]
            _tone(a, py, px, ramp, -1)
            _tone(a, py, [p + 1 for p in px], ramp, 1)
    return a


def rotate_nn(spr, deg):
    """Rotate an index sprite at native resolution with nearest neighbour
    (pixel staircases, no smoothing). Use for loose props; use rotsprite()
    for hero sprites that rotate during animation."""
    im = Image.fromarray(spr, "L").rotate(deg, resample=Image.NEAREST, expand=True, fillcolor=T)
    a = np.asarray(im).copy()
    ys, xs = np.nonzero(a != T)
    return a[ys.min():ys.max() + 1, xs.min():xs.max() + 1] if len(ys) else a


def curve_points(pts, steps=None):
    """Pixel-perfect points along a quadratic/cubic Bezier (no doubled
    corners), for cables, cords and wire."""
    pts = [np.array(p, float) for p in pts]
    n = steps or int(sum(np.abs(pts[i + 1] - pts[i]).sum() for i in range(len(pts) - 1)) * 2) + 2
    out = []
    for t in np.linspace(0, 1, n):
        q = list(pts)
        while len(q) > 1:
            q = [q[i] * (1 - t) + q[i + 1] * t for i in range(len(q) - 1)]
        p = (int(round(q[0][0])), int(round(q[0][1])))
        if not out or p != out[-1]:
            out.append(p)
    # drop L-corner pixels (x,y) whose neighbours are diagonal to each other
    clean = [out[0]]
    for i in range(1, len(out) - 1):
        a, b = clean[-1], out[i + 1]
        if abs(a[0] - b[0]) == 1 and abs(a[1] - b[1]) == 1:
            continue
        clean.append(out[i])
    clean.append(out[-1])
    return clean


def cable(canvas, pts, c, hi=None):
    for i, (x, y) in enumerate(curve_points(pts)):
        canvas.px(x, y, c)
        if hi is not None and i % 5 == 2:
            canvas.px(x, y, hi)


def scatter(canvas, items, rng, region, n, avoid=None, rotate=True):
    """Scatter small clutter sprites (3-8 px) inside region=(x0,y0,x1,y1),
    skipping pixels where `avoid` (bool world mask) is True."""
    x0, y0, x1, y1 = region
    placed = 0
    for _ in range(n * 6):
        if placed >= n:
            break
        s = items[int(rng.integers(0, len(items)))]
        if rotate:
            s = rotate_nn(s, float(rng.choice([0, 15, 30, 45, 60, 90, 120, 160, -20, -40])))
        x, y = int(rng.integers(x0, max(x0 + 1, x1 - s.shape[1]))), int(rng.integers(y0, max(y0 + 1, y1 - s.shape[0])))
        if avoid is not None and avoid[y:y + s.shape[0], x:x + s.shape[1]].any():
            continue
        canvas.blit(s, x, y)
        if avoid is not None:
            avoid[y:y + s.shape[0], x:x + s.shape[1]] |= s != T
        placed += 1
    return placed


def pattern(a, ramp, kind="dots", mask=None, ox=0, oy=0, delta=-1):
    """Deterministic, designed surface texture (refined alternative to the
    random `texture`). Shifts ramp tones by `delta` on a regular lattice:
    dots (diamond lattice), weave (offset stitches), quilt (diagonal
    diamonds), grain (staggered board streaks), diag (sparse stripes).
    Every pattern has a period < 12 px, so no flat area exceeds 12x12."""
    h, w = a.shape
    yy, xx = np.mgrid[0:h, 0:w]
    xx, yy = xx + ox, yy + oy
    if kind == "dots":
        sel = ((xx % 4 == 0) & (yy % 4 == 0)) | ((xx % 4 == 2) & (yy % 4 == 2))
    elif kind == "weave":
        sel = ((yy % 2 == 0) & (xx % 4 == 0)) | ((yy % 2 == 1) & (xx % 4 == 2))
    elif kind == "quilt":
        sel = ((xx + yy) % 8 == 0) | ((xx - yy) % 8 == 0)
    elif kind == "grain":
        sel = (np.isin(xx % 8, (2, 5))) & (((yy + 5 * (xx // 8) + 3 * (xx % 8)) % 13) < 3)
    elif kind == "diag":
        sel = (xx + yy) % 6 == 0
    else:
        raise ValueError(kind)
    m = np.isin(a, ramp) & sel
    if mask is not None:
        m &= mask
    pos = {c: i for i, c in enumerate(ramp)}
    lut = np.arange(256, dtype=np.uint8)
    for c_, i in pos.items():
        lut[c_] = ramp[max(0, min(len(ramp) - 1, i + delta))]
    a[m] = lut[a[m]]
    return a
