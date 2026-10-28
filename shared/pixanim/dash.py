"""Car interior close-up: windscreen, instrument cluster (rev counter + speedometer), warning lights, centre console
with A/C button, fan and temperature knobs, air vents. Drawn on a 5 px pixel grid (216x384 for 1080x1920).

    D = Dashboard(outside=garage_base_image)
    layer = D.frame(t, rpm_deg=..., ac_on=..., press=0..1)   # RGBA full-res
Anchors (px): D.TACHO, D.SPEEDO, D.AC_BTN, D.VENTS, D.LIGHTS; D.needle_tip(deg) for interactions.
Needle angles are maths degrees: 225 = needle at rest (zero), sweeping clockwise to -45.
"""
import math
from functools import lru_cache
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from .grid import Grid, FONT, text_width, outline

S = 5
GW, GH = 216, 386
NAVY = (26, 26, 46)
PLASTIC, PLASTIC_HI, PLASTIC_SH = (40, 41, 48), (62, 64, 74), (27, 28, 33)
FACE, FACE_HI = (15, 16, 22), (25, 27, 38)
CHROME = [(214, 220, 230), (176, 182, 194), (132, 138, 150), (96, 100, 112)]
TICK, TICK_DIM, RED = (236, 240, 248), (120, 126, 140), (232, 52, 63)
NEEDLE, NEEDLE_HI = (255, 96, 40), (255, 190, 120)


def _text(d, x, y, s, col):
    for ch in s:
        rows = FONT[ch]
        for j, row in enumerate(rows):
            for i, b in enumerate(row):
                if b == '1': d.point((x + i, y + j), fill=col)
        x += len(rows[0]) + 1


def _gauge_face(d, cx, cy, r, red_from=None, label=None, majors=9):
    for y in range(cy - r, cy + r + 1):                   # chrome bezel, lit from above
        for x in range(cx - r, cx + r + 1):
            dd = math.hypot(x - cx, y - cy)
            if r - 4 < dd <= r + 0.3:
                k = (y - cy) / r * 0.5 + 0.5 - (0.15 if dd > r - 1.5 else 0)
                d.point((x, y), fill=CHROME[min(3, max(0, int(k * 3.99)))])
    d.ellipse((cx - r + 4, cy - r + 4, cx + r - 4, cy + r - 4), fill=FACE)
    d.ellipse((cx - r * 0.55, cy - r * 0.55, cx + r * 0.55, cy + r * 0.55), fill=FACE_HI)
    d.ellipse((cx - r * 0.5, cy - r * 0.5, cx + r * 0.5, cy + r * 0.5), fill=(21, 22, 31))
    ri = r - 6
    n = (majors - 1) * 4
    if red_from is not None:
        a0 = 225 - 270 * red_from / (majors - 1)
        d.arc((cx - ri - 2, cy - ri - 2, cx + ri + 2, cy + ri + 2), 360 - a0, 405, fill=RED, width=2)
    for i in range(n + 1):
        a = math.radians(225 - 270 * i / n)
        major = i % 4 == 0
        red = red_from is not None and i >= red_from * 4
        L = 5 if major else 2
        col = RED if red else (TICK if major else TICK_DIM)
        p0 = (cx + (ri - L) * math.cos(a), cy - (ri - L) * math.sin(a)); p1 = (cx + ri * math.cos(a), cy - ri * math.sin(a))
        d.line((p0, p1), fill=col, width=2 if major else 1)
    if label:
        _text(d, cx - text_width(label) // 2, cy + r // 3, label, (110, 116, 132))


class Dashboard:
    TACHO = (370, 800); TACHO_R = 42 * S
    SPEEDO = (790, 800); SPEEDO_R = 30 * S
    AC_BTN = (540, 1256)
    FAN, TEMP = (300, 1256), (780, 1256)
    VENTS = ((300, 1130), (780, 1130))
    LIGHTS_Y = 1046
    LCD = (790, 985)

    def __init__(self, outside=None):
        self.outside = outside
        self._base = None

    # ------------------------------------------------------------ static
    def _grid(self):
        img = Image.new('RGBA', (GW, GH), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
        # A-pillars and roof lining frame the windscreen
        d.polygon([(0, 0), (22, 0), (6, 96), (0, 96)], fill=(22, 23, 27))
        d.polygon([(GW, 0), (GW - 22, 0), (GW - 6, 96), (GW, 96)], fill=(22, 23, 27))
        d.rectangle((0, 0, GW, 5), fill=(30, 31, 36))
        # rear-view mirror
        d.rectangle((106, 5, 109, 13), fill=(30, 31, 36))
        d.rounded_rectangle((84, 12, 132, 24), 4, fill=(34, 35, 41)); d.rounded_rectangle((86, 14, 130, 22), 3, fill=(70, 78, 92))
        d.line((90, 15, 124, 15), fill=(120, 132, 150))
        # dash top with stitched edge
        d.rectangle((0, 92, GW, 120), fill=PLASTIC)
        d.ellipse((-40, 84, GW + 40, 110), fill=PLASTIC)
        d.line((0, 97, GW, 97), fill=PLASTIC_HI)
        for x in range(2, GW, 4): d.point((x, 101), fill=(70, 72, 82))
        # cluster binnacle: hood overhang + face
        d.rounded_rectangle((14, 108, 202, 214), 18, fill=PLASTIC_SH)
        d.rounded_rectangle((18, 114, 198, 210), 15, fill=(12, 13, 17))
        d.ellipse((10, 100, 206, 124), fill=PLASTIC); d.line((24, 104, 192, 104), fill=PLASTIC_HI)
        tx, ty = self.TACHO[0] // S, self.TACHO[1] // S
        sx, sy = self.SPEEDO[0] // S, self.SPEEDO[1] // S
        _gauge_face(d, tx, ty, 42, red_from=6.5, label='RPM', majors=9)
        _gauge_face(d, sx, sy, 30, label=None, majors=7)
        # LCD between the dials
        lx, ly = self.LCD[0] // S, self.LCD[1] // S
        d.rounded_rectangle((lx - 14, ly - 6, lx + 14, ly + 6), 2, fill=(10, 18, 20), outline=(50, 54, 64))
        # warning lamp housings
        for i in range(6):
            x = 48 + i * 24
            d.rounded_rectangle((x - 5, 205, x + 5, 213), 2, fill=(20, 21, 26))
        # brushed trim strip
        d.rectangle((0, 214, GW, 218), fill=CHROME[2]); d.line((0, 214, GW, 214), fill=CHROME[0]); d.line((0, 218, GW, 218), fill=CHROME[3])
        # centre console
        d.rectangle((0, 219, GW, 280), fill=PLASTIC)
        d.rounded_rectangle((20, 222, 196, 274), 8, fill=(32, 33, 39))
        d.line((26, 223, 190, 223), fill=PLASTIC_HI)
        for vx, vy in self.VENTS:
            gx, gy = vx // S, vy // S
            d.rounded_rectangle((gx - 26, gy - 7, gx + 26, gy + 7), 3, fill=(14, 15, 19))
            for yy in range(gy - 5, gy + 6, 3):
                d.line((gx - 24, yy, gx + 24, yy), fill=(66, 70, 80)); d.line((gx - 24, yy + 1, gx + 24, yy + 1), fill=(30, 31, 37))
            d.rectangle((gx - 2, gy - 6, gx + 2, gy + 6), fill=(90, 96, 108))
        for kx, ky, col in ((*self.FAN, (120, 170, 220)), (*self.TEMP, (232, 90, 70))):
            gx, gy = kx // S, ky // S
            d.ellipse((gx - 12, gy - 12, gx + 12, gy + 12), fill=(20, 21, 26))
            d.ellipse((gx - 10, gy - 10, gx + 10, gy + 10), fill=CHROME[3]); d.ellipse((gx - 9, gy - 9, gx + 9, gy + 9), fill=(54, 56, 64))
            d.arc((gx - 15, gy - 15, gx + 15, gy + 15), 150, 390, fill=col, width=2)
        bx, by = self.AC_BTN[0] // S, self.AC_BTN[1] // S
        d.rounded_rectangle((bx - 22, by - 14, bx + 22, by + 14), 5, fill=(16, 17, 21))
        d.rectangle((0, 281, GW, GH), fill=(19, 20, 24))
        d.line((0, 281, GW, 281), fill=PLASTIC_HI)
        return img

    def base(self):
        if self._base is None:
            full = Image.new('RGBA', (1080, 1930), (14, 15, 18, 255))
            if self.outside is not None:    # the garage seen through the windscreen, dimmed and cool
                view = self.outside.convert('RGB').crop((0, 560, 1080, 1040)).resize((1080, 480), Image.NEAREST)
                view = Image.blend(view, Image.new('RGB', view.size, (12, 16, 24)), 0.45)
                full.paste(view, (0, 0))
                glare = Image.new('L', (1080, 480), 0); gd = ImageDraw.Draw(glare)
                gd.polygon([(160, 0), (330, 0), (120, 480), (-50, 480)], fill=34); gd.polygon([(380, 0), (420, 0), (180, 480), (140, 480)], fill=22)
                full.paste((210, 220, 236), (0, 0, 1080, 480), glare)
            g = self._grid().resize((GW * S, GH * S), Image.NEAREST)
            full.alpha_composite(g)
            self._base = full.crop((0, 0, 1080, 1920))
        return self._base

    # ------------------------------------------------------------ dynamic
    def needle_tip(self, deg, frac=0.78, which='tacho'):
        (cx, cy), r = (self.TACHO, self.TACHO_R) if which == 'tacho' else (self.SPEEDO, self.SPEEDO_R)
        a = math.radians(deg)
        return cx + r * frac * math.cos(a), cy - r * frac * math.sin(a)

    def frame(self, t, rpm_deg=225, ac_on=False, press=0.0, speed_deg=225, lcd=None):
        img = self.base().copy()
        ov = Image.new('RGBA', (GW, GH), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
        for (cx, cy), r, deg in ((self.TACHO, 42, rpm_deg), (self.SPEEDO, 30, speed_deg)):
            gx, gy = cx // S, cy // S
            a = math.radians(deg)
            tip = (gx + (r - 9) * math.cos(a), gy - (r - 9) * math.sin(a))
            tail = (gx - 6 * math.cos(a), gy + 6 * math.sin(a))
            d.line((tail, tip), fill=(120, 30, 10), width=4)
            d.line((tail, tip), fill=NEEDLE, width=2)
            d.line(((gx + tip[0]) / 2, (gy + tip[1]) / 2, *tip), fill=NEEDLE_HI, width=1)
            d.ellipse((gx - 5, gy - 5, gx + 5, gy + 5), fill=(40, 42, 50)); d.ellipse((gx - 3, gy - 3, gx + 3, gy + 3), fill=(90, 96, 110))
            d.point((gx - 2, gy - 2), fill=(200, 206, 216))
            for k in range(118, 152, 3):                   # glass glare
                b = math.radians(k)
                d.point((gx + (r - 7) * math.cos(b), gy - (r - 7) * math.sin(b)), fill=(255, 255, 255, 70))
        # warning lamps: battery, oil, engine, ABS stay dark while running; the A/C snowflake lights with the A/C
        icons = ['BAT', 'OIL', 'ENG', 'AC', 'ABS', 'BELT']
        for i, name in enumerate(icons):
            x = 48 + i * 24
            on = name == 'AC' and ac_on
            col = (110, 200, 255) if on else (48, 50, 58)
            if name == 'AC':
                for j, row in enumerate(["0001000", "0101010", "0011100", "1111111", "0011100", "0101010", "0001000"]):
                    for k, b in enumerate(row):
                        if b == '1': d.point((x - 3 + k, 206 + j), fill=col)
                if on: d.rounded_rectangle((x - 6, 204, x + 6, 214), 3, outline=(70, 150, 210, 140))
            else:
                _text(d, x - text_width(name) // 2, 206, name, col)
        # LCD
        lx, ly = self.LCD[0] // S, self.LCD[1] // S
        txt = lcd if lcd is not None else ('AC ON' if ac_on else 'READY')
        _text(d, lx - text_width(txt) // 2, ly - 3, txt, (120, 230, 200) if ac_on else (70, 120, 110))
        # A/C button: depresses, LED strip lights
        bx, by = self.AC_BTN[0] // S, self.AC_BTN[1] // S
        dp = int(round(2 * press))
        d.rounded_rectangle((bx - 19, by - 11 + dp, bx + 19, by + 11), 4, fill=(54, 56, 66))
        d.rounded_rectangle((bx - 19, by - 11 + dp, bx + 19, by + 9), 4, fill=(70, 73, 84))
        d.line((bx - 15, by - 10 + dp, bx + 15, by - 10 + dp), fill=(104, 108, 120))
        flake = (127, 212, 255) if ac_on else (150, 156, 170)
        for j, row in enumerate(["0001000", "0101010", "0011100", "1111111", "0011100", "0101010", "0001000"]):
            for k, b in enumerate(row):
                if b == '1': d.point((bx - 14 + k, by - 6 + j + dp), fill=flake)
        _text(d, bx - 3, by - 6 + dp, 'AC', (255, 255, 255) if ac_on else (170, 176, 190))
        led = (60, 220, 110) if ac_on else (40, 44, 50)
        d.rectangle((bx - 10, by + 4 + dp, bx + 10, by + 6 + dp), fill=led)
        if ac_on: d.rectangle((bx - 8, by + 4 + dp, bx - 4, by + 4 + dp), fill=(190, 255, 210))
        up = ov.resize((GW * S, GH * S), Image.NEAREST).crop((0, 0, 1080, 1920))
        img.alpha_composite(up)
        if ac_on:   # soft LED bloom
            glow = Image.new('L', (260, 120), 0); ImageDraw.Draw(glow).ellipse((40, 30, 220, 90), fill=60)
            glow = glow.filter(ImageFilter.GaussianBlur(18))
            img.paste((80, 230, 130, 255), (self.AC_BTN[0] - 130, self.AC_BTN[1] - 40), glow)
        return img
