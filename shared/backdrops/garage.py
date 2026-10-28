"""Moody monochrome pixel garage backdrop, shared by the explainer episodes.

Layers, back to front:
  base()       static pixel art (walls, pegboard, shelving, tyres, bench, lamp) with the light cone baked in
  frame(t)     base + LED strip pulse + dust drifting through the light beam
  reflect()    glossy floor reflection of the foreground layer
  rim()        bright top-edge highlights on foreground sprites under the overhead light
  vignette()   heavy dark edges, applied in screen space after the camera

Usage (episode render.py):
    from backdrops.garage import Garage
    GAR = Garage(W, H, GROUND, S)
    base = GAR.frame(t); GAR.reflect(base, fg); fg = GAR.rim(fg); base.paste(fg, (0, 0), fg)
    ... camera ...; GAR.vignette(frame)
"""
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

# monochrome palette: charcoal, gunmetal, brushed silver
CEIL = (24, 25, 29)
WALL = (40, 42, 48)
SEAM, SEAM_HI = (29, 30, 35), (52, 55, 62)
BOLT = (70, 74, 82)
BRICK_A, BRICK_B, MORTAR = (50, 53, 60), (45, 48, 55), (31, 32, 37)
SILVER, SILVER_HI, SILVER_SH = (92, 97, 108), (132, 138, 150), (60, 63, 71)
FLOOR, FLOOR_LINE, STAIN = (35, 37, 42), (27, 28, 32), (30, 32, 36)
PEG, PEG_HOLE, TOOL, TOOL_HI = (47, 49, 56), (31, 32, 37), (25, 26, 30), (68, 72, 80)
SHELF, SHELF_HI, ITEM_A, ITEM_B, ITEM_C = (78, 82, 92), (106, 111, 122), (52, 55, 62), (58, 61, 69), (44, 47, 53)
TYRE, TREAD, TYRE_TOP, HOLE = (22, 23, 27), (31, 33, 37), (37, 39, 44), (15, 16, 19)
BENCH = (58, 61, 69)
LIGHT = (236, 240, 250)


class Garage:
    def __init__(self, w=1080, h=1920, ground=1180, s=9, light_x=540, seed=7):
        self.w, self.h, self.g, self.s, self.lx, self.seed = w, h, ground, s, light_x, seed
        self.gw, self.gh = w // s + 1, h // s + 2      # pixel-art grid
        self.wall_y = ground // s - 13                 # wall base row (floor starts here)
        self.ly = 31 * s                               # light origin (bulb) in px
        self._base = self._glow = self._vig = self._rimw = None

    # ------------------------------------------------------------ static art
    def _art(self):
        gw, gh, wy = self.gw, self.gh, self.wall_y
        img = Image.new('RGB', (gw, gh), WALL)
        d = ImageDraw.Draw(img)
        cx = self.lx // self.s
        # ceiling, cornice, LED strip housing
        d.rectangle((0, 0, gw, 18), fill=CEIL)
        for x in range(0, gw, 16):
            d.rectangle((x, 0, x + 1, 18), fill=(29, 30, 35))
        d.rectangle((0, 19, gw, 20), fill=SILVER); d.rectangle((0, 19, gw, 19), fill=SILVER_HI)
        d.rectangle((0, 21, gw, 21), fill=(150, 156, 168))
        d.rectangle((0, 22, gw, 22), fill=SILVER_SH)
        # concrete panels with seams and bolts
        top, mid, bot = 23, 56, 88
        for x in (0, 30, 60, 90):
            d.rectangle((x, top, x, bot), fill=SEAM); d.rectangle((x + 1, top, x + 1, bot), fill=SEAM_HI)
        d.rectangle((0, mid, gw, mid), fill=SEAM); d.rectangle((0, mid + 1, gw, mid + 1), fill=SEAM_HI)
        for x in (3, 27, 33, 57, 63, 87, 93, 117):
            for y in (top + 3, mid - 3, mid + 4, bot - 3):
                d.point((x, y), fill=BOLT)
        # brick wainscot
        d.rectangle((0, bot + 1, gw, wy - 3), fill=MORTAR)
        for r, y in enumerate(range(bot + 2, wy - 3, 4)):
            off = 0 if r % 2 else 5
            for x in range(-off, gw, 10):
                d.rectangle((x, y, x + 8, y + 2), fill=BRICK_A if (x // 10 + r) % 3 else BRICK_B)
                d.point((x, y), fill=SEAM_HI)
        # brushed silver skirting
        d.rectangle((0, wy - 3, gw, wy - 1), fill=SILVER); d.rectangle((0, wy - 3, gw, wy - 3), fill=SILVER_HI)
        d.rectangle((0, wy - 1, gw, wy - 1), fill=SILVER_SH)
        # floor: concrete slabs in perspective
        d.rectangle((0, wy, gw, gh), fill=FLOOR)
        y, step = wy, 3
        while y < gh:
            d.line((0, y, gw, y), fill=FLOOR_LINE); y += step; step = int(step * 1.45) + 1
        for xb in range(-200, gw + 200, 26):
            d.line((cx + (xb - cx) * 0.22, wy, xb, gh), fill=FLOOR_LINE)
        r = np.random.default_rng(self.seed)
        for _ in range(7):
            sx, sy = r.uniform(0, gw), r.uniform(wy + 6, gh); rx = r.uniform(4, 12)
            d.ellipse((sx - rx, sy - rx * 0.3, sx + rx, sy + rx * 0.3), fill=STAIN)
        self._pegboard(d, 4, 30, 48, 74)
        self._shelves(d, 92, 26, 117, wy - 3)
        self._bench(d, 50, 92, 90, wy)
        self._tyres(d, wy)
        self._lamp(d, cx)
        # pixel-scale concrete grain
        a = np.asarray(img).astype(np.int16)
        n = r.integers(-3, 4, size=a.shape[:2])[..., None]
        n[wy:] = n[wy:] // 2
        return Image.fromarray(np.clip(a + n, 0, 255).astype(np.uint8))

    def _pegboard(self, d, x0, y0, x1, y1):
        d.rectangle((x0 - 1, y0 - 1, x1 + 1, y1 + 1), fill=SILVER_SH)
        d.rectangle((x0, y0, x1, y1), fill=PEG)
        for y in range(y0 + 2, y1 - 1, 3):
            for x in range(x0 + 2, x1 - 1, 3):
                d.point((x, y), fill=PEG_HOLE)
        # silhouetted tools with a faint top highlight
        d.line((9, 40, 16, 55), fill=TOOL, width=2)                     # spanner
        d.ellipse((6, 35, 12, 41), fill=TOOL); d.ellipse((8, 37, 10, 39), fill=PEG)
        d.rectangle((8, 35, 10, 35), fill=TOOL_HI)
        d.rectangle((21, 39, 22, 56), fill=TOOL); d.rectangle((17, 36, 26, 39), fill=TOOL)   # hammer
        d.rectangle((17, 36, 26, 36), fill=TOOL_HI)
        d.rectangle((30, 36, 32, 44), fill=TOOL); d.rectangle((31, 45, 31, 54), fill=TOOL)   # screwdriver
        d.rectangle((30, 36, 32, 36), fill=TOOL_HI)
        d.polygon([(36, 38), (46, 38), (46, 45), (36, 50)], fill=TOOL)   # saw
        d.rectangle((44, 35, 47, 38), fill=TOOL); d.line((36, 38, 46, 38), fill=TOOL_HI)
        for i, x in enumerate(range(8, 20, 2)):                             # spanner set
            d.rectangle((x, 60, x, 64 + i), fill=TOOL); d.point((x, 60), fill=TOOL_HI)
        d.ellipse((25, 59, 37, 71), outline=TOOL, width=2)                 # coiled cable
        d.rectangle((40, 60, 44, 70), fill=TOOL); d.rectangle((40, 60, 44, 60), fill=TOOL_HI)  # tape measure

    def _shelves(self, d, x0, y0, x1, y1):
        for x in (x0, x1 - 1):
            d.rectangle((x, y0, x + 1, y1), fill=SHELF); d.rectangle((x, y0, x, y1), fill=SHELF_HI)
        items = {46: [(2, 8, 7, ITEM_A), (11, 5, 9, ITEM_B), (17, 6, 5, ITEM_C)],
                 68: [(2, 4, 8, ITEM_B), (7, 4, 8, ITEM_B), (13, 9, 6, ITEM_A), (19, 3, 10, ITEM_C)],
                 90: [(3, 10, 8, ITEM_C), (15, 7, 7, ITEM_A)]}
        for y, row in items.items():
            for dx, iw, ih, col in row:
                d.rectangle((x0 + dx, y - ih, x0 + dx + iw, y - 1), fill=col)
                d.rectangle((x0 + dx, y - ih, x0 + dx + iw, y - ih), fill=SEAM_HI)
                d.rectangle((x0 + dx + 1, y - ih // 2, x0 + dx + iw - 1, y - ih // 2), fill=SEAM)
            d.rectangle((x0, y, x1, y + 1), fill=SHELF); d.rectangle((x0, y, x1, y), fill=SHELF_HI)
            d.rectangle((x0 + 2, y + 2, x1 - 2, y + 2), fill=SEAM)

    def _bench(self, d, x0, y0, x1, y1):
        d.rectangle((x0, y0, x1, y0 + 1), fill=BENCH)
        for x in (x0 + 2, x1 - 3):
            d.rectangle((x, y0 + 2, x + 1, y1 - 1), fill=BENCH)
        d.rectangle((x0 + 6, y0 + 4, x1 - 6, y0 + 10), outline=(52, 55, 62))
        d.rectangle((x1 - 10, y0 - 4, x1 - 5, y0 - 1), fill=(52, 55, 62))   # vice

    def _tyres(self, d, wy):
        for i in range(4):                       # flat stack, left corner
            yb = wy + 2 - i * 6
            d.rectangle((-9, yb - 6, 16, yb), fill=TREAD)
            for x in range(-9, 17, 2):
                d.rectangle((x, yb - 5, x, yb - 1), fill=TYRE)
            d.ellipse((-9, yb - 10, 16, yb - 3), fill=TYRE_TOP)
            d.ellipse((-2, yb - 8, 9, yb - 5), fill=HOLE)
        cx, cy, r = 107, wy - 7, 9               # one leaning against the shelves
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=TYRE)
        for k in range(16):
            a = k * math.pi / 8
            d.point((cx + (r - 1) * math.cos(a), cy + (r - 1) * math.sin(a)), fill=TREAD)
        d.ellipse((cx - 5, cy - 5, cx + 5, cy + 5), fill=(60, 63, 71)); d.ellipse((cx - 2, cy - 2, cx + 2, cy + 2), fill=TYRE)
        d.arc((cx - r, cy - r, cx + r, cy + r), 200, 300, fill=(70, 74, 82))

    def _lamp(self, d, cx):
        d.rectangle((cx - 1, 0, cx, 24), fill=(18, 19, 22))
        d.polygon([(cx - 7, 24), (cx + 6, 24), (cx + 11, 30), (cx - 12, 30)], fill=SILVER)
        d.rectangle((cx - 7, 24, cx + 6, 24), fill=SILVER_HI)
        d.rectangle((cx - 11, 30, cx + 10, 30), fill=SILVER_SH)
        d.rectangle((cx - 6, 31, cx + 5, 31), fill=(245, 247, 252))

    # ------------------------------------------------------------ light
    def _light_alpha(self):
        w, h, g, lx, ly = self.w, self.h, self.g, self.lx, self.ly
        Y, X = np.mgrid[0:h, 0:w].astype(np.float32)
        u = np.clip((Y - ly) / (g - ly), 0, 1)
        hw = 110 + 560 * u
        cone = np.clip((hw - np.abs(X - lx)) / 140, 0, 1) * (0.85 - 0.45 * u) * (Y > ly) * (Y < g + 20)
        pool = np.clip(1 - (((X - lx) / 620) ** 2 + ((Y - (g + 35)) / 125) ** 2), 0, 1) ** 1.5
        streak = np.exp(-((X - lx) / 40) ** 2) * np.clip(1 - (Y - g) / 520, 0, 1) * (Y > g)   # lamp reflected in the floor
        bloom = np.clip(1 - np.hypot(X - lx, (Y - ly) * 1.3) / 160, 0, 1) ** 2
        return np.clip(cone * 0.26 + pool * 0.28 + streak * 0.22 + bloom * 0.6, 0, 0.8)

    def base(self):
        if self._base is None:
            art = self._art().resize((self.gw * self.s, self.gh * self.s), Image.NEAREST).crop((0, 0, self.w, self.h))
            a = self._light_alpha()[..., None]
            px = np.asarray(art).astype(np.float32)
            self._base = Image.fromarray((px * (1 - a) + np.array(LIGHT, np.float32) * a).astype(np.uint8))
            ys = np.arange(self.h, dtype=np.float32)[:, None]
            xs = np.arange(self.w, dtype=np.float32)[None, :]
            self._rimw = (np.clip(1 - np.abs(xs - self.lx) / 700, 0, 1) ** 1.2 * (ys < self.g)).astype(np.float32)
        return self._base

    def _led_mask(self):
        if self._glow is None:
            y0, y1, yc = 120, 330, 21 * self.s + self.s // 2
            ys = np.arange(y0, y1, dtype=np.float32)[:, None]
            m = np.exp(-((ys - yc) / 34) ** 2) * 0.42 + np.exp(-((ys - yc) / 7) ** 2) * 0.5
            self._glow = (y0, Image.fromarray(np.repeat(m * 255, self.w, axis=1).astype(np.uint8), 'L'))
        return self._glow

    def cone_weight(self, x, y):
        u = min(1.0, max(0.0, (y - self.ly) / (self.g - self.ly)))
        hw = 110 + 560 * u
        return max(0.0, min(1.0, (hw - abs(x - self.lx)) / 140)) * (y > self.ly)

    def frame(self, t):
        img = self.base().copy()
        # LED strip: slow rhythmic pulse
        y0, mask = self._led_mask()
        k = 0.45 + 0.55 * (0.5 + 0.5 * math.sin(2 * math.pi * t / 2.4))
        lut = [int(v * k) for v in range(256)]
        img.paste((226, 232, 246), (0, y0, self.w, y0 + mask.height), mask.point(lut))
        # dust drifting through the beam
        d = ImageDraw.Draw(img); r = np.random.default_rng(self.seed + 1); s = self.s
        for i in range(44):
            x0, y0p, vy, ph = r.uniform(260, 820), r.uniform(0, 1), r.uniform(9, 24), r.uniform(0, 6.3)
            y = self.ly + 20 + ((y0p * 880 + t * vy) % 880)
            x = x0 + 26 * math.sin(t * 0.45 + ph) + 8 * math.sin(t * 1.7 + ph * 2)
            wgt = self.cone_weight(x, y)
            if wgt < 0.12: continue
            b = wgt * (0.45 + 0.55 * (0.5 + 0.5 * math.sin(t * 1.4 + ph)))
            v = int(70 + 170 * b)
            sz = s // 2 if i % 3 else s - 2
            x, y = round(x / 3) * 3, round(y / 3) * 3
            d.rectangle((x, y, x + sz, y + sz), fill=(v, v, min(255, v + 8)))
        return img

    # ------------------------------------------------------------ foreground passes
    def reflect(self, img, fg, depth=330, strength=0.36):
        """Glossy floor: mirror the foreground about the ground line, fading and softening with distance."""
        g = self.g
        src = fg.crop((0, g - depth, self.w, g)).transpose(Image.FLIP_TOP_BOTTOM)
        rgb, a = src.convert('RGB'), np.asarray(src.split()[3], np.float32)
        fade = np.linspace(strength, 0.0, depth, dtype=np.float32)[:, None] ** 1.1
        mask = Image.fromarray((a * fade).astype(np.uint8), 'L').filter(ImageFilter.GaussianBlur(2))
        rgb = Image.blend(rgb, Image.new('RGB', rgb.size, FLOOR), 0.3).filter(ImageFilter.GaussianBlur(1.5))
        img.paste(rgb, (0, g), mask)

    def rim(self, fg, strength=0.75):
        """Lighten the first pixel row under every top outline, weighted by the overhead light."""
        self.base()
        arr = np.array(fg)
        m = arr[..., 3] > 200
        s = self.s
        up1 = np.zeros_like(m); up1[s:] = m[:-s]
        up2 = np.zeros_like(m); up2[2 * s:] = m[:-2 * s]
        band = m & up1 & ~up2
        if not band.any(): return fg
        k = (self._rimw[band] * strength)[:, None]
        px = arr[..., :3][band].astype(np.float32)
        arr[..., :3][band] = (px + (np.array(LIGHT, np.float32) - px) * k).astype(np.uint8)
        return Image.fromarray(arr, 'RGBA')

    def vignette(self, img, power=1.6, amount=225):
        if self._vig is None:
            Y, X = np.mgrid[0:self.h, 0:self.w].astype(np.float32)
            rr = np.hypot((X - self.w / 2) / (self.w * 0.58), (Y - self.h * 0.47) / (self.h * 0.55))
            self._vig = Image.fromarray((np.clip((rr - 0.55) / 0.62, 0, 1) ** power * amount).astype(np.uint8), 'L')
        img.paste((6, 6, 8), (0, 0, self.w, self.h), self._vig)
