"""Side-scrolling night street with parallax, on a 3 px pixel grid (360x640 for 1080x1920).

    ST = Street()
    layer = ST.frame(t, scroll_px)     # scroll_px: how far the camera has tracked to the right (px)
Layers (parallax factor): stars/moon (0.02), far skyline (0.12), lit mid buildings + pulsing sign (0.35),
lamp posts with light pools (0.75), kerb + road with lane markings and wet reflections (1.0).
ROAD_Y is the ground line (px) for cars driving on it.
"""
import math
import numpy as np
from PIL import Image, ImageDraw
from .grid import FONT, text_width

S = 3
GW, GH = 360, 640
ROAD_Y = 1150


def _text(d, x, y, s, col):
    for ch in s:
        rows = FONT[ch]
        for j, row in enumerate(rows):
            for i, b in enumerate(row):
                if b == '1': d.point((x + i, y + j), fill=col)
        x += len(rows[0]) + 1


def _r(seed): return np.random.default_rng(seed)


class Street:
    ROAD_Y = ROAD_Y

    def __init__(self, seed=11):
        self.seed = seed
        self._sky = None

    def _sky_img(self):
        if self._sky is None:
            img = Image.new('RGBA', (GW, GH), (0, 0, 0, 255)); d = ImageDraw.Draw(img)
            for y in range(0, 300):
                k = y / 300
                d.line((0, y, GW, y), fill=(int(12 + 18 * k), int(13 + 19 * k), int(19 + 24 * k)))
            d.rectangle((0, 300, GW, GH), fill=(30, 32, 43))
            return img
        return self._sky

    def frame(self, t, scroll):
        if self._sky is None: self._sky = self._sky_img()
        img = self._sky.copy(); d = ImageDraw.Draw(img)
        sc = scroll / S
        r = _r(self.seed)
        for i in range(40):                                     # stars
            x = (r.uniform(0, GW) - sc * 0.02) % GW; y = r.uniform(70, 230)
            if math.sin(t * r.uniform(1, 3) + i) > -0.3: d.point((x, y), fill=(200, 206, 220) if i % 4 else (255, 255, 255))
        mx = 70 - sc * 0.02
        d.ellipse((mx - 14, 96, mx + 14, 124), fill=(222, 226, 234)); d.ellipse((mx - 6, 98, mx + 18, 122), fill=(30, 32, 44))
        # far skyline
        base = 255
        off = sc * 0.12
        for k in range(int(off // 22) - 1, int((off + GW) // 22) + 2):
            rr = _r(1000 + k); h = rr.integers(30, 90); w = rr.integers(16, 24)
            x = k * 22 - off
            d.rectangle((x, base - h, x + w, base), fill=(28, 30, 40))
            for wy in range(base - h + 4, base - 4, 6):
                for wx in range(int(x) + 3, int(x + w) - 2, 5):
                    if rr.random() < 0.18: d.point((wx, wy), fill=(84, 88, 104))
        # mid buildings with lit windows and a pulsing sign
        base = 300; off = sc * 0.35
        for k in range(int(off // 70) - 1, int((off + GW) // 70) + 2):
            rr = _r(2000 + k); h = int(rr.integers(70, 140)); w = int(rr.integers(56, 68))
            x = k * 70 - off
            d.rectangle((x, base - h, x + w, base), fill=(42, 44, 54)); d.line((x, base - h, x + w, base - h), fill=(64, 67, 80))
            d.rectangle((x, base - h - 3, x + w, base - h), fill=(36, 38, 46))
            for wy in range(base - h + 8, base - 22, 12):
                for wx in range(int(x) + 6, int(x + w) - 8, 11):
                    lit = rr.random() < 0.45
                    col = (206, 200, 170) if lit and rr.random() < 0.5 else ((150, 156, 170) if lit else (28, 30, 38))
                    d.rectangle((wx, wy, wx + 6, wy + 6), fill=col)
                    if lit: d.line((wx, wy + 6, wx + 6, wy + 6), fill=(100, 104, 118))
            d.rectangle((x + 8, base - 20, x + w - 8, base), fill=(30, 32, 40))      # shopfront
            d.rectangle((x + 12, base - 16, x + w - 12, base - 2), fill=(70, 74, 86) if k % 2 else (54, 58, 70))
            if k % 3 == 0:
                glow = 0.6 + 0.4 * (0.5 + 0.5 * math.sin(t * 4 + k))
                col = tuple(int(c * glow) for c in (255, 96, 110))
                tw = text_width('GARAGE')
                d.rectangle((x + w / 2 - tw / 2 - 3, base - h + 2, x + w / 2 + tw / 2 + 2, base - h + 12), fill=(20, 21, 26))
                _text(d, int(x + w / 2 - tw / 2), base - h + 4, 'GARAGE', col)
        # pavement, kerb
        d.rectangle((0, 300, GW, 332), fill=(62, 64, 72))
        off = sc * 1.0
        for k in range(int(off // 16) - 1, int((off + GW) // 16) + 2):
            x = k * 16 - off
            d.line((x, 300, x, 332), fill=(54, 56, 63))
        d.rectangle((0, 332, GW, 336), fill=(132, 138, 150)); d.line((0, 332, GW, 332), fill=(176, 182, 194))
        # road with lane markings and wet reflections
        d.rectangle((0, 337, GW, 400), fill=(30, 31, 36))
        for k in range(int(off // 40) - 1, int((off + GW) // 40) + 2):
            x = k * 40 - off
            d.rectangle((x, 366, x + 20, 368), fill=(214, 218, 226))
        d.rectangle((0, 400, GW, 404), fill=(110, 116, 128))
        d.rectangle((0, 405, GW, GH), fill=(20, 21, 25))
        # lamp posts (in front of the buildings, behind the cars)
        off = sc * 0.75
        lamps = []
        for k in range(int(off // 140) - 1, int((off + GW) // 140) + 2):
            x = k * 140 - off + 40
            d.rectangle((x, 206, x + 2, 334), fill=(60, 63, 72)); d.line((x, 206, x, 334), fill=(96, 100, 112))
            d.line((x + 1, 206, x + 16, 200), fill=(60, 63, 72), width=2)
            d.rectangle((x + 12, 199, x + 22, 203), fill=(90, 94, 106)); d.rectangle((x + 13, 203, x + 21, 204), fill=(255, 244, 210))
            lamps.append(x + 17)
        # foreground railing (parallax 1.5) gives the shot depth in front of the road
        off = sc * 1.5
        d.rectangle((0, 418, GW, 421), fill=(52, 55, 63)); d.line((0, 418, GW, 418), fill=(90, 94, 106))
        d.rectangle((0, 440, GW, 442), fill=(44, 46, 53))
        for k in range(int(off // 34) - 1, int((off + GW) // 34) + 2):
            x = k * 34 - off
            d.rectangle((x, 414, x + 4, 470), fill=(40, 42, 49)); d.line((x, 414, x, 470), fill=(76, 80, 92))
            d.rectangle((x - 1, 412, x + 5, 415), fill=(64, 67, 77))
        d.rectangle((0, 470, GW, GH), fill=(16, 17, 20))
        out = img.resize((GW * S, GH * S), Image.NEAREST)
        # light pools from the lamps and their reflections on the wet road (smooth light over the pixel art)
        light = Image.new('L', (GW * S, GH * S), 0); ld = ImageDraw.Draw(light)
        for lx in lamps:
            X = lx * S
            ld.polygon([(X - 18, 612), (X + 18, 612), (X + 170, 1000), (X - 170, 1000)], fill=26)
            ld.ellipse((X - 200, 960, X + 200, 1040), fill=40)
            for k in range(5): ld.rectangle((X - 10 + k * 2, 1016 + k * 22, X + 10 - k * 2, 1016 + k * 22 + 12), fill=22 - k * 4)
        out.paste((255, 246, 220), (0, 0, GW * S, GH * S), light)
        return out
