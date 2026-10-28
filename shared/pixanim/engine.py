"""Animated engine cutaway in a dark engine bay, on a 5 px pixel grid (216x384 for 1080x1920).

Working parts: two pistons on con-rods driven by a rotating crankshaft, spark flashes at the top of each stroke,
a serpentine belt (crank -> A/C compressor -> alternator -> tensioner) with moving ribs, pulleys spinning at
belt speed, and an A/C compressor whose electromagnetic clutch plate locks to the pulley when engaged,
after which the refrigerant line frosts up.

    E = Engine()
    th = crank_angle(t, [(0, 1.6), (5.65, 1.6), (5.8, 1.1), ...])   # rev/s profile -> degrees
    layer = E.frame(t, theta=th, clutch=t >= 5.65, clutch_t0=5.65)
Anchors (px): E.COMP (compressor pulley), E.COMP_BODY, E.CRANK, E.ALT, E.BLOCK, E.PISTONS
"""
import math
from functools import lru_cache
import numpy as np
from PIL import Image, ImageDraw
from .grid import FONT, text_width

S = 5
GW, GH = 216, 386
NAVY = (26, 26, 46)

# grid-space layout
CRANK, CRANK_R = (82, 200), 13
COMP, COMP_R = (48, 168), 12
ALT, ALT_R = (76, 118), 8
TENS, TENS_R = (94, 152), 4
BELT = [(CRANK, CRANK_R), (COMP, COMP_R), (ALT, ALT_R), (TENS, TENS_R)]
AXIS_Y, THROWS, THROW_R, ROD = 200, (124, 160), 9, 32
BORES = ((112, 136), (148, 172)); BORE_TOP, BORE_BOT = 128, 188

BLOCK, BLOCK_HI, BLOCK_SH = (104, 110, 122), (146, 152, 164), (72, 76, 86)
CUT, HATCH = (150, 156, 168), (118, 124, 136)
CAVITY = (24, 25, 31)
COVER, COVER_HI, COVER_SH = (196, 40, 50), (255, 110, 116), (140, 24, 32)
STEEL, STEEL_HI, STEEL_SH = (190, 196, 206), (236, 240, 246), (120, 126, 138)
BELT_C, RIB = (36, 37, 43), (88, 92, 102)
COMP_C, COMP_HI, COMP_SH = (88, 140, 196), (150, 196, 236), (56, 100, 150)


def _text(d, x, y, s, col):
    for ch in s:
        rows = FONT[ch]
        for j, row in enumerate(rows):
            for i, b in enumerate(row):
                if b == '1': d.point((x + i, y + j), fill=col)
        x += len(rows[0]) + 1


def crank_angle(t, profile):
    """Integrate a piecewise-linear speed profile [(t, rev_per_s)] to a crank angle in degrees."""
    th, (pt, pv) = 0.0, profile[0]
    if t <= pt: return 360 * pv * (t - pt)
    for nt, nv in profile[1:]:
        if t <= nt:
            v = pv + (nv - pv) * (t - pt) / (nt - pt) if nt > pt else nv
            return 360 * (th + (pv + v) / 2 * (t - pt))
        th += (pv + nv) / 2 * (nt - pt); pt, pv = nt, nv
    return 360 * (th + pv * (t - pt))


def _belt_path():
    cx = sum(c[0] for c, _ in BELT) / len(BELT); cy = sum(c[1] for c, _ in BELT) / len(BELT)
    segs, tang = [], []
    n = len(BELT)
    for i in range(n):
        (a, ra), (b, rb) = BELT[i], BELT[(i + 1) % n]
        dx, dy = b[0] - a[0], b[1] - a[1]; L = math.hypot(dx, dy); ux, uy = dx / L, dy / L
        nx, ny = uy, -ux
        mx, my = (a[0] + b[0]) / 2 - cx, (a[1] + b[1]) / 2 - cy
        if nx * mx + ny * my < 0: nx, ny = -nx, -ny
        tang.append(((a[0] + nx * ra, a[1] + ny * ra), (b[0] + nx * rb, b[1] + ny * rb)))
    pts = []
    for i in range(n):
        p0, p1 = tang[i]
        pts += [p0, p1]
        c, r = BELT[(i + 1) % n]
        q0, q1 = p1, tang[(i + 1) % n][0]
        a0 = math.atan2(q0[1] - c[1], q0[0] - c[0]); a1 = math.atan2(q1[1] - c[1], q1[0] - c[0])
        # wrap the outside way (away from the loop centre)
        mid = lambda a, b: math.atan2(math.sin(a) + math.sin(b), math.cos(a) + math.cos(b))
        am = mid(a0, a1)
        if math.cos(am) * (c[0] - cx) + math.sin(am) * (c[1] - cy) < 0:
            a1 = a1 + 2 * math.pi if a1 < a0 else a1 - 2 * math.pi
            span = a1 - a0
        else:
            span = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
        for k in range(1, 12):
            a = a0 + span * k / 12
            pts.append((c[0] + r * math.cos(a), c[1] + r * math.sin(a)))
    pts.append(pts[0])
    seg = [math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1]) for i in range(len(pts) - 1)]
    return pts, seg


BELT_PTS, BELT_SEG = _belt_path()
BELT_LEN = sum(BELT_SEG)


def _along(dist):
    dist %= BELT_LEN
    for i, L in enumerate(BELT_SEG):
        if dist <= L:
            u = dist / L if L else 0
            (x0, y0), (x1, y1) = BELT_PTS[i], BELT_PTS[i + 1]
            return x0 + (x1 - x0) * u, y0 + (y1 - y0) * u
        dist -= L
    return BELT_PTS[0]


class Engine:
    COMP = (COMP[0] * S, COMP[1] * S); COMP_BODY = (22 * S, 168 * S)
    CRANK = (CRANK[0] * S, CRANK[1] * S); ALT = (ALT[0] * S, ALT[1] * S)
    BLOCK = (142 * S, 160 * S); PISTONS = ((124 * S, 160 * S), (160 * S, 160 * S))
    PIPE_TOP = (16 * S, 70 * S)

    def __init__(self):
        self._base = self._mask = None

    def comp_mask(self):
        """Full-res mask of the compressor body and pulley: paste the engine back through it to put things behind."""
        if self._mask is None:
            m = Image.new('L', (GW, GH), 0); d = ImageDraw.Draw(m); cx, cy = COMP
            d.rounded_rectangle((cx - 44, cy - 18, cx - 6, cy + 18), 5, fill=255)
            d.ellipse((cx - COMP_R - 1, cy - COMP_R - 1, cx + COMP_R + 1, cy + COMP_R + 1), fill=255)
            self._mask = m.resize((GW * S, GH * S), Image.NEAREST).crop((0, 0, 1080, 1920))
        return self._mask

    def _static(self):
        img = Image.new('RGBA', (GW, GH), (17, 18, 22, 255)); d = ImageDraw.Draw(img)
        # bonnet underside (quilted insulation) and the firewall behind the engine
        d.rectangle((0, 0, GW, 58), fill=(34, 35, 41))
        for y in range(4, 56, 8):
            for x in range(-4 + (y // 8 % 2) * 6, GW, 12):
                d.polygon([(x, y), (x + 6, y + 4), (x, y + 8), (x - 6, y + 4)], outline=(44, 46, 53))
        d.rectangle((0, 58, GW, 62), fill=(52, 55, 62)); d.line((0, 58, GW, 58), fill=(80, 84, 94))
        d.line((196, 58, 214, 0), fill=(110, 116, 128), width=2)    # bonnet prop rod
        d.rectangle((0, 62, GW, 250), fill=(24, 25, 30))
        for x in range(0, GW, 14):
            d.line((x, 62, x, 250), fill=(28, 29, 35))
        # strut towers and hoses in silhouette
        for cx in (10, 206):
            d.rectangle((cx - 12, 70, cx + 12, 250), fill=(30, 31, 37)); d.ellipse((cx - 12, 62, cx + 12, 80), fill=(36, 38, 45))
            d.ellipse((cx - 5, 66, cx + 5, 76), fill=(22, 23, 28))
        d.arc((120, 30, 230, 140), 180, 270, fill=(20, 21, 25), width=6)
        d.rectangle((0, 250, GW, GH), fill=(14, 15, 18))
        d.line((0, 250, GW, 250), fill=(44, 46, 52))
        # radiator below the drive end
        d.rectangle((24, 232, 112, 250), fill=(34, 36, 42))
        for x in range(26, 112, 3): d.line((x, 233, x, 249), fill=(46, 48, 56))
        # engine block shell, valve cover, oil pan
        d.rounded_rectangle((100, 108, 184, 214), 4, fill=BLOCK)
        d.line((101, 109, 183, 109), fill=BLOCK_HI); d.line((183, 110, 183, 212), fill=BLOCK_SH)
        d.rounded_rectangle((104, 94, 180, 110), 4, fill=COVER)
        d.line((108, 95, 176, 95), fill=COVER_HI); d.line((104, 108, 180, 108), fill=COVER_SH)
        for x in range(112, 176, 8): d.line((x, 98, x, 106), fill=COVER_SH)
        d.rounded_rectangle((156, 88, 166, 94), 2, fill=(40, 42, 50)); d.line((157, 88, 165, 88), fill=(90, 94, 104))
        d.rounded_rectangle((104, 214, 180, 226), 3, fill=BLOCK_SH); d.line((106, 214, 178, 214), fill=BLOCK)
        # cutaway: hatched cut face around the bores and crankcase
        cut = Image.new('RGBA', (73, 89), CUT); hd = ImageDraw.Draw(cut)
        for k in range(-100, 100, 4):
            hd.line((k, 88, k + 88, 0), fill=HATCH)
        img.paste(cut, (106, 122))
        d.rectangle((106, 122, 178, 123), fill=BLOCK_SH)
        for x0, x1 in BORES:
            d.rectangle((x0, BORE_TOP, x1, BORE_BOT), fill=CAVITY)
            d.line((x0, BORE_TOP, x0, BORE_BOT), fill=(56, 58, 66)); d.line((x1, BORE_TOP, x1, BORE_BOT), fill=(56, 58, 66))
            cx = (x0 + x1) // 2
            d.rectangle((cx - 2, BORE_TOP - 8, cx + 2, BORE_TOP), fill=(220, 224, 232)); d.rectangle((cx - 1, BORE_TOP - 11, cx + 1, BORE_TOP - 8), fill=(60, 62, 70))
        d.rounded_rectangle((108, 186, 176, 210), 6, fill=CAVITY)
        # alternator body
        ax, ay = ALT
        d.rounded_rectangle((ax - 20, ay - 13, ax + 2, ay + 13), 5, fill=(150, 156, 168))
        for y in range(ay - 9, ay + 10, 3): d.line((ax - 18, y, ax - 4, y), fill=(108, 114, 126))
        d.line((ax - 19, ay - 12, ax + 1, ay - 12), fill=(200, 206, 216))
        # A/C compressor body, fins and stencil
        cx, cy = COMP
        d.rounded_rectangle((cx - 40, cy - 18, cx - 6, cy + 18), 5, fill=COMP_C)
        d.line((cx - 38, cy - 17, cx - 8, cy - 17), fill=COMP_HI); d.line((cx - 38, cy + 17, cx - 8, cy + 17), fill=COMP_SH)
        for x in range(cx - 36, cx - 8, 4): d.line((x, cy - 13, x, cy + 13), fill=COMP_SH)
        d.rounded_rectangle((cx - 37, cy - 5, cx - 20, cy + 5), 2, fill=(236, 240, 246))
        _text(d, cx - 36, cy - 3, 'A/C', (40, 80, 130))
        d.rounded_rectangle((cx - 44, cy - 8, cx - 40, cy + 8), 1, fill=(150, 156, 168))
        # refrigerant lines up to the condenser
        for x, w in ((cx - 32, 3), (cx - 22, 2)):
            d.rectangle((x, 70, x + w, cy - 18), fill=STEEL_SH); d.line((x, 70, x, cy - 18), fill=STEEL)
        # tensioner arm
        tx, ty = TENS
        d.line((tx, ty, tx + 8, ty + 14), fill=(70, 74, 84), width=4); d.ellipse((tx + 5, ty + 11, tx + 11, ty + 17), fill=(52, 55, 62))
        return img

    def base(self):
        if self._base is None: self._base = self._static()
        return self._base

    def frame(self, t, theta=0.0, clutch=False, clutch_t0=None, frost=0.0, load=0.0, firing=True, stalled=False,
              shake=(0, 0), rpm_deg=None, as_grid=False):
        img = self.base().copy(); d = ImageDraw.Draw(img)
        sx, sy = shake
        # crankshaft, throws, con-rods and pistons
        d.rectangle((CRANK[0], AXIS_Y - 2, 178, AXIS_Y + 2), fill=STEEL_SH); d.line((CRANK[0], AXIS_Y - 2, 178, AXIS_Y - 2), fill=STEEL)
        for i, (tx, (x0, x1)) in enumerate(zip(THROWS, BORES)):
            a = math.radians(theta + 180 * i)
            px, py = tx + THROW_R * math.sin(a), AXIS_Y - THROW_R * math.cos(a)
            cw = (tx - 10 * math.sin(a), AXIS_Y + 10 * math.cos(a))
            d.ellipse((cw[0] - 8, cw[1] - 8, cw[0] + 8, cw[1] + 8), fill=(58, 61, 70))
            d.line((tx, AXIS_Y, px, py), fill=STEEL_SH, width=5)
            wy = py - math.sqrt(max(1, ROD ** 2 - (px - tx) ** 2))
            cx = (x0 + x1) / 2
            d.line((px, py, cx, wy), fill=STEEL_SH, width=5); d.line((px, py, cx, wy), fill=STEEL, width=3)
            d.ellipse((px - 3, py - 3, px + 3, py + 3), fill=STEEL_HI)
            top = wy - 9
            d.rectangle((x0 + 1, top, x1 - 1, wy + 5), fill=STEEL); d.line((x0 + 1, top, x1 - 1, top), fill=STEEL_HI)
            for k in (2, 4, 6): d.line((x0 + 1, top + k, x1 - 1, top + k), fill=STEEL_SH)
            d.ellipse((cx - 2, wy - 2, cx + 2, wy + 2), fill=STEEL_SH)
            # combustion flash near the top of the stroke
            if firing and not stalled and math.cos(a) > 0.93:
                k = (math.cos(a) - 0.93) / 0.07
                d.rectangle((x0 + 2, BORE_TOP + 1, x1 - 2, top - 1), fill=(255, int(150 + 80 * k), 40))
                d.rectangle((cx - 4, BORE_TOP + 1, cx + 4, BORE_TOP + 4), fill=(255, 245, 200))
        # serpentine belt with moving ribs
        belt_speed = 2 * math.pi * CRANK_R / 360          # grid units of belt per degree of crank
        travel = theta * belt_speed
        tight = (220, 70, 70) if load > 0.05 else BELT_C
        d.line(BELT_PTS, fill=(16, 17, 21), width=6); d.line(BELT_PTS, fill=BELT_C, width=4)
        if load > 0.05:      # the side pulling the compressor carries the extra load
            d.line(BELT_PTS[:2], fill=tuple(int(BELT_C[i] + (tight[i] - BELT_C[i]) * load) for i in range(3)), width=4)
        for k in range(int(BELT_LEN // 5)):
            x, y = _along(k * 5 + travel % 5)
            d.rectangle((x - 0.5, y - 0.5, x + 0.5, y + 0.5), fill=RIB)
        # pulleys, spinning at belt speed
        for (c, r), name in zip(BELT, ('crank', 'comp', 'alt', 'tens')):
            ang = math.degrees(travel / r)
            d.ellipse((c[0] - r, c[1] - r, c[0] + r, c[1] + r), fill=(46, 48, 56))
            d.ellipse((c[0] - r + 2, c[1] - r + 2, c[0] + r - 2, c[1] + r - 2), fill=(126, 132, 144))
            for k in range(0, 360, 360 // (6 if r > 6 else 3)):
                a = math.radians(k + ang)
                d.line((c[0] + (r - 2) * 0.35 * math.cos(a), c[1] + (r - 2) * 0.35 * math.sin(a),
                        c[0] + (r - 3) * math.cos(a), c[1] + (r - 3) * math.sin(a)), fill=(84, 88, 100))
            if name == 'comp':
                # clutch plate: still when off, locked to the pulley (and brighter) when engaged
                pa = math.radians(ang if clutch else 15)
                pr = r - 4
                col = (214, 220, 230) if clutch else (96, 100, 112)
                d.ellipse((c[0] - pr, c[1] - pr, c[0] + pr, c[1] + pr), fill=col, outline=(40, 42, 50))
                for k in range(3):
                    a = pa + k * 2 * math.pi / 3
                    d.ellipse((c[0] + 4 * math.cos(a) - 1, c[1] + 4 * math.sin(a) - 1, c[0] + 4 * math.cos(a) + 1, c[1] + 4 * math.sin(a) + 1), fill=(60, 62, 72))
                if clutch and clutch_t0 is not None and 0 <= t - clutch_t0 < 0.25:
                    k = 1 - (t - clutch_t0) / 0.25
                    d.ellipse((c[0] - r - 3, c[1] - r - 3, c[0] + r + 3, c[1] + r + 3), outline=(160, 220, 255), width=max(1, int(3 * k)))
            d.ellipse((c[0] - 2, c[1] - 2, c[0] + 2, c[1] + 2), fill=(200, 206, 216))
        # frost creeping up the suction line once the compressor runs
        if frost > 0:
            cx, cy = COMP
            x = cx - 32; top = cy - 18 - (cy - 18 - 70) * min(1.0, frost)
            for y in range(int(top), cy - 18):
                if (y * 7) % 3 != 0: d.point((x + (y % 2) * 3, y), fill=(220, 240, 255))
                d.point((x + 1, y), fill=(170, 214, 245))
        if stalled:
            for x0, x1 in BORES:
                d.rectangle((x0 + 2, BORE_TOP + 1, x1 - 2, BORE_TOP + 6), fill=(40, 40, 44))
        if rpm_deg is not None:    # small rev counter inset, top right
            gx, gy, r = 176, 30, 16
            d.ellipse((gx - r - 2, gy - r - 2, gx + r + 2, gy + r + 2), fill=(176, 182, 194)); d.ellipse((gx - r, gy - r, gx + r, gy + r), fill=(15, 16, 22))
            for k in range(9):
                a = math.radians(225 - 270 * k / 8)
                d.line((gx + (r - 4) * math.cos(a), gy - (r - 4) * math.sin(a), gx + (r - 1) * math.cos(a), gy - (r - 1) * math.sin(a)),
                       fill=(232, 52, 63) if k >= 7 else (236, 240, 248))
            a = math.radians(rpm_deg)
            d.line((gx, gy, gx + (r - 4) * math.cos(a), gy - (r - 4) * math.sin(a)), fill=(255, 96, 40), width=2)
            d.ellipse((gx - 2, gy - 2, gx + 2, gy + 2), fill=(90, 96, 110))
            _text(d, gx - 8, gy + 6, 'RPM', (110, 116, 132))
        if as_grid: return img
        out = img.resize((GW * S, GH * S), Image.NEAREST).crop((0, 0, 1080, 1920))
        if sx or sy:
            out = out.transform(out.size, Image.AFFINE, (1, 0, -sx, 0, 1, -sy), resample=Image.NEAREST)
        return out
