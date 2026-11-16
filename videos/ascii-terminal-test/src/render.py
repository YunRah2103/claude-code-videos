"""ASCII terminal hypercar test: 5 s silent loop, 1080x1920, 30 fps.

python render.py still OUTDIR 0 2.5 4.5      # PNG stills (f_<t>.png), EMA pre-rolled
python render.py video OUT.mp4 [--frames N]  # lossless master -> 2-pass x264 <= 8 Mbps
"""
import json
import math
import os
import subprocess
import sys
import time
from pathlib import Path

import cv2
import numpy as np
from numba import njit, prange
from PIL import Image, ImageDraw, ImageFont
from scipy.interpolate import CubicSpline

import source

DUR = 5.0
W, H, FPS, SUB = 1080, 1920, 30, 4
N = int(DUR * FPS)
CW, CH = 10, 18
COLS, ROWS = W // CW, (H - 12) // CH          # 108 x 106
Y0 = (H - ROWS * CH) // 2
SX, SY = 4, 6
PRE = 12                                      # EMA / hysteresis pre-roll frames (wrap from the end)
EMA = 0.6
FONT = '/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-Bold.ttf'
FONT_THIN = '/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-Regular.ttf'

XS = np.array([c * CW + (s + .5) * CW / SX for c in range(COLS) for s in range(SX)], np.float64)
YS = np.array([Y0 + r * CH + (s + .5) * CH / SY for r in range(ROWS) for s in range(SY)], np.float64)

# ---------------------------------------------------------------- timeline helpers
def sstep(a, b, x):
    u = min(max((x - a) / (b - a), 0.0), 1.0)
    return u * u * u * (u * (6 * u - 15) + 10)          # smootherstep: C2, no linear ramps


def glitch(t):
    return max(1 - sstep(0.18, 0.45, t), sstep(4.70, 4.985, t), 0.14 * (sstep(0.3, 0.5, t) - sstep(1.25, 1.45, t)))


def dim(t):           # 1 = dim, 0 = full brightness (below the decode line)
    return 1.0 if t < 1.6 else sstep(4.66, 4.985, t)


def wipe_y(t):
    return -120 + (H + 240) * sstep(1.30, 1.60, t)


def heat_lvl(t):
    return (0.2 + 0.8 * sstep(3.25, 3.95, t) * (1 - sstep(4.62, 4.99, t))) * (0.92 + 0.08 * math.sin(4 * math.pi * t))


# ---------------------------------------------------------------- camera (periodic C2 spline, 2.5D over the photo)
YC = 0.52 * H            # screen row the camera's source point lands on
S0 = W / source.SW       # zoom 1 = photo width fills the frame
#        t     zoom   sx     sy     roll(deg)
KEYS = [(0.00, 1.410, 486.8, 380.4, -0.6),     # front 3/4, dim glitch (loops from the end)
        (0.85, 1.069, 518.5, 342.1, 0.0),      # wide while the command types
        (1.60, 1.329, 604.7, 335.6, 0.4),      # decoded; side pass begins
        (2.45, 1.533, 592.3, 294.8, 0.7),      # along the flank
        (3.30, 1.217, 486.7, 300.4, 0.2),
        (4.15, 1.380, 423.7, 325.6, -0.6),     # front close-up, heat glow
        (5.00, 1.410, 486.8, 380.4, -0.6)]     # spline-optimised for even screen motion per second
_K = np.array(KEYS)
CAM = CubicSpline(_K[:, 0], _K[:, 1:], bc_type='periodic')


FREEZE = os.environ.get('FREEZE_CAM')   # flicker test: hold the camera, keep everything else moving


def camera(t):
    zoom, sx, sy, roll = CAM(float(FREEZE) if FREEZE else t % DUR)
    return float(zoom) * S0, float(sx), float(sy), math.radians(roll)


def project(p, cam):
    """photo point -> screen point"""
    s, sx, sy, a = cam
    ux, uy = (p[0] - sx) * s, (p[1] - sy) * s
    c, sn = math.cos(a), math.sin(a)
    return np.array([W / 2 + ux * c - uy * sn, YC + ux * sn + uy * c])


INTAKE = source.INTAKE
CAR_C = (540.0, 330.0)
_DX = (XS - W / 2).astype(np.float32)[None, :]
_DY = (YS - YC).astype(np.float32)[:, None]


def render_sub(t, buf):
    s, sx, sy, a = camera(t)
    c, sn = math.cos(a), math.sin(a)
    mx = (sx + (_DX * c + _DY * sn) / s).astype(np.float32)
    my = (sy + (-_DX * sn + _DY * c) / s).astype(np.float32)
    source.sample(mx, my, t % DUR, heat_lvl(t % DUR), buf)

# ---------------------------------------------------------------- glyph atlas
GL = ['.', ':', '-', '=', '+', '*', '#', '@', '/', '\\', '|', '_', '0', '1', 'x', '%', '$', '&', '<', '>']
G = {ch: i + 2 for i, ch in enumerate(GL)}
RAMP = np.array([G[c] for c in '.:-=+*#@'])
EDGE = {0: G['_'], 45: G['\\'], 90: G['|'], 135: G['/']}
SCR = np.array([G[c] for c in '01x%$&<>'])
OXS = np.arange(-2, 2.01, .5)
OYS = np.arange(-4.5, 4.51, .5)


def build_atlas():
    S = 8
    at = np.zeros((len(GL) + 2, len(OYS), len(OXS), CH, CW), np.float32)
    for ch, gi in G.items():
        size = 22 if ch in '/\\|_' else 16
        font = ImageFont.truetype(FONT, size * S)
        im = Image.new('L', (CW * S * 3, CH * S * 3), 0)
        d = ImageDraw.Draw(im)
        bb = d.textbbox((0, 0), ch, font=font)
        d.text((CW * S * 1.5 - (bb[0] + bb[2]) / 2, CH * S * 1.5 - (bb[1] + bb[3]) / 2), ch, font=font, fill=255)
        a = np.asarray(im, np.float32) / 255
        for iy, oy in enumerate(OYS):
            for ix, ox in enumerate(OXS):
                y0 = int(CH * S - oy * S); x0 = int(CW * S - ox * S)
                crop = a[y0:y0 + CH * S, x0:x0 + CW * S]
                at[gi, iy, ix] = crop.reshape(CH, S, CW, S).mean((1, 3))
    return np.minimum(at * 1.25, 1.0)


@njit(cache=True, fastmath=True, parallel=True)
def composite(gid, gprev, fade, oxi, oyi, col, inten, dr, ddx, ddy, shift, atlas, img):
    for y in prange(img.shape[0]):
        r = (y - 6) // 18
        if y < 6 or r >= gid.shape[0]:
            continue
        ly = (y - 6) - r * 18
        sh = shift[r]
        for x in range(img.shape[1]):
            xs = x - sh
            if xs < 0 or xs >= img.shape[1]:
                continue
            c = xs // 10
            lx = xs - c * 10
            v = 0.0
            for k in range(2):
                g = gid[r, c] if k == 0 else gprev[r, c]
                w = 1.0 - fade[r, c] if k == 0 else fade[r, c]
                if g == 0 or w <= 0.0:
                    continue
                if g == 1:
                    a = 0.0
                    for h in range(2):
                        rr = dr[r, c, h]
                        if rr > 0.05:
                            px = lx + 0.5 - (5.0 + ddx[r, c])
                            py = ly + 0.5 - (4.5 + 9.0 * h + ddy[r, c, h])
                            dd = math.sqrt(px * px + py * py)
                            a = max(a, min(max(rr - dd + 0.5, 0.0), 1.0) * min(rr * 1.6, 1.0))
                    v += w * a
                else:
                    v += w * atlas[g, oyi[r, c], oxi[r, c], ly, lx]
            if v > 0.0:
                s = v * inten[r, c]
                img[y, x, 0] = col[r, c, 0] * s
                img[y, x, 1] = col[r, c, 1] * s
                img[y, x, 2] = col[r, c, 2] * s


# ---------------------------------------------------------------- ASCII state machine
GREEN = np.array([.86, .88, .90], np.float32)      # monochrome: cool white
WHITE = np.array([1.0, 1.0, 1.0], np.float32)
AMBER = np.array([1.0, 1.0, 1.0], np.float32)
RED = np.array([1.0, 1.0, 1.0], np.float32)
GDIM = np.array([.55, .56, .58], np.float32)
OFFX = ((np.arange(SX) + .5) * CW / SX - CW / 2).astype(np.float32)
OFFY = ((np.arange(SY) + .5) * CH / SY - CH / 2).astype(np.float32)


def cells(a):
    return a.reshape(ROWS, SY, COLS, SX)


def features(avg):
    lum, spec, heat, mask, gnd, matf, disp = avg
    f = {}
    L4 = cells(lum + 0.35 * spec)
    f['L'] = L4.mean((1, 3))
    f['Lt'] = L4[:, :SY // 2].mean((1, 3))
    f['Lb'] = L4[:, SY // 2:].mean((1, 3))
    w = L4 + 1e-3
    f['cx'] = (w * OFFX).sum((1, 3)) / w.sum((1, 3))
    yt = OFFY[:SY // 2] + CH / 4
    f['cyt'] = (w[:, :SY // 2] * yt[None, :, None, None]).sum((1, 3)) / w[:, :SY // 2].sum((1, 3))
    f['cyb'] = (w[:, SY // 2:] * (OFFY[SY // 2:] - CH / 4)[None, :, None, None]).sum((1, 3)) / w[:, SY // 2:].sum((1, 3))
    for k, a in (('spec', spec), ('heat', heat), ('cov', mask), ('gnd', gnd)):
        f[k] = cells(a).mean((1, 3))
    F = (mask + 0.35 * matf).astype(np.float32)
    gx = cv2.Sobel(F, cv2.CV_32F, 1, 0, ksize=3) / 8
    gy = cv2.Sobel(F, cv2.CV_32F, 0, 1, ksize=3) / 8 * (CW / SX) / (CH / SY)
    f['Jxx'] = cells(gx * gx).mean((1, 3))
    f['Jyy'] = cells(gy * gy).mean((1, 3))
    f['Jxy'] = cells(gx * gy).mean((1, 3))
    m = cells(np.sqrt(gx * gx + gy * gy)) + 1e-4
    f['ex'] = (m * OFFX).sum((1, 3)) / m.sum((1, 3))
    f['ey'] = (m * OFFY[None, :, None, None]).sum((1, 3)) / m.sum((1, 3))
    return f


class Ascii:
    def __init__(self):
        self.s = None
        self.gid = np.zeros((ROWS, COLS), np.int32)
        self.lvl = np.zeros((ROWS, COLS), np.int32)
        self.prev = np.zeros((ROWS, COLS), np.int32)
        self.fade = np.zeros((ROWS, COLS), np.float32)

    def step(self, avg):
        f = features(avg)
        if self.s is None:
            self.s = f
        else:
            for k in f:
                self.s[k] = EMA * self.s[k] + (1 - EMA) * f[k]
        s = self.s
        old = self.gid
        J = s['Jxx'] + s['Jyy']
        E = np.sqrt(J)
        coh = np.sqrt((s['Jxx'] - s['Jyy']) ** 2 + 4 * s['Jxy'] ** 2) / (J + 1e-9)
        was_edge = old >= G['/']
        was_edge &= old <= G['_']
        edge = (E > np.where(was_edge, 0.075, 0.13)) & (coh > np.where(was_edge, 0.25, 0.35))
        # thin outlines: keep cells that are a local max across the edge (soft NMS)
        th = 0.5 * np.arctan2(2 * s['Jxy'], s['Jxx'] - s['Jyy'])
        qx = np.rint(np.cos(th)).astype(int); qy = np.rint(np.sin(th) * CW / CH * 1.6).astype(int)
        Ep = np.pad(E, 1)
        rr, cc = np.indices(E.shape)
        n1 = Ep[rr + 1 + qy, cc + 1 + qx]; n2 = Ep[rr + 1 - qy, cc + 1 - qx]
        edge &= E >= np.where(was_edge, 0.65, 0.9) * np.maximum(n1, n2)
        car = s['cov'] > 0.4
        was_char = (old >= 2) & (old < G['/'])
        hl = s['spec'] > np.where(was_char, 0.22, 0.30)
        char = ~edge & car & hl & False          # clean look: dots + outline glyphs only
        lmax = np.maximum(s['Lt'], s['Lb'])
        dots = ~edge & ~char & (lmax > np.where(old == 1, 0.002, 0.004))   # appears at sub-pixel size: no pop
        # char ramp level with hysteresis
        v = np.clip(s['spec'] * 0.75 + s['L'] * 0.55, 0, .999) * 8
        keep = np.abs(v - (self.lvl + .5)) < 0.8
        self.lvl = np.where(keep, self.lvl, v.astype(np.int32))
        # edge orientation with hysteresis
        phi = (np.degrees(0.5 * np.arctan2(2 * s['Jxy'], s['Jxx'] - s['Jyy'])) + 90) % 180
        eg = np.zeros_like(old)
        best = np.full(old.shape, 999.0)
        for ang, gi in EDGE.items():
            dist = np.abs((phi - ang + 90) % 180 - 90) - np.where(old == gi, 22.0, 0.0)
            better = dist < best
            eg = np.where(better, gi, eg)
            best = np.where(better, dist, best)
        new = np.where(edge, eg, np.where(char, RAMP[self.lvl], np.where(dots, 1, 0))).astype(np.int32)
        ch = new != old
        self.prev = np.where(ch, old, self.prev)
        self.fade = np.where(ch, 0.6, self.fade * 0.45).astype(np.float32)
        self.fade[self.fade < 0.05] = 0
        self.gid = new
        rad = 4.5 * np.sqrt(np.clip(lmax * 1.3, 0, 1))
        prad = getattr(self, 'rad', rad)
        tiny = ((old == 0) | (old == 1)) & ((new == 0) | (new == 1)) & (np.maximum(rad, prad) < 1.5)
        self.vch = ch & ~tiny                     # visible pops: ignore sub-1.5 px dot on/off
        self.vmask = (new > 1) | (rad >= 1.5) | self.vch
        self.rad = rad
        return ch

    def draw(self, t, fidx, img):
        s = self.s
        gid = self.gid.copy()
        g = glitch(t)
        rng = np.random.default_rng(fidx * 7919 + 13)
        # per-cell colour
        isedge = (gid >= G['/']) & (gid <= G['_'])
        wmix = np.clip(s['spec'] * 1.4 + 0.45 * isedge, 0, 1)[..., None]
        col = GREEN * (1 - wmix) + WHITE * wmix
        gmix = np.clip(s['gnd'] - s['cov'], 0, 1)[..., None]
        col = col * (1 - gmix) + GDIM * gmix
        h = s['heat'][..., None]
        h1 = np.clip(h * 3.0, 0, 1); h2 = np.clip(h * 1.8 - 0.35, 0, 1)
        col = col * (1 - h1) + AMBER * h1
        col = col * (1 - h2 * .8) + RED * (h2 * .8)
        inten = np.where(gid == 1, 0.9 + 0.3 * s['spec'],
                         np.where(isedge, 0.95 + 0.25 * s['L'], 0.6 + 0.6 * np.minimum(s['spec'] + s['L'], 1)))
        inten = inten * (1 - 0.3 * gmix[..., 0]) * (1 + 0.25 * h[..., 0])
        # dim + decode wipe (per row)
        yc = Y0 + (np.arange(ROWS) + .5) * CH
        yw = wipe_y(t)
        dm = dim(t)
        rowb = np.where(yc < yw, 0.0, 1.0) if 1.25 < t < 1.65 else np.full(ROWS, 1.0)
        bright = 1 - 0.64 * dm * rowb
        inten = inten * bright[:, None]
        if 1.25 < t < 1.65:      # decode band: scramble + white
            band = ((yc < yw) & (yc > yw - 110))[:, None]
            filled = gid > 0
            pick = band & (filled | (rng.random(gid.shape) < .25))
            gid = np.where(pick, rng.choice(SCR, gid.shape), gid)
            col = np.where(pick[..., None], WHITE, col)
            inten = np.where(pick, 1.15, inten)
        if g > 0.01:
            pick = (gid > 0) & (rng.random(gid.shape) < 0.06 * g)
            gid = np.where(pick, rng.choice(SCR, gid.shape), gid)
        # glyph sub-cell offsets
        isch = gid > 1
        ox = np.where(isedge, s['ex'], s['cx'] * 0.6)
        oy = np.where(isedge, s['ey'], 0.0)
        oxi = np.clip(np.rint((ox - OXS[0]) / .5), 0, len(OXS) - 1).astype(np.int32)
        oyi = np.clip(np.rint((oy - OYS[0]) / .5), 0, len(OYS) - 1).astype(np.int32)
        oxi = np.where(isch, oxi, len(OXS) // 2).astype(np.int32)
        hb = 0.5 * s['heat']
        dr = np.stack([4.5 * np.sqrt(np.clip(s['Lt'] * 1.3 + hb, 0, 1)), 4.5 * np.sqrt(np.clip(s['Lb'] * 1.3 + hb, 0, 1))], -1)
        ddx = np.clip(s['cx'], -2, 2)
        ddy = np.stack([np.clip(s['cyt'], -2, 2), np.clip(s['cyb'], -2, 2)], -1)
        # glitch row shifts: smooth travelling bands
        r = np.arange(ROWS)
        bandm = (0.5 + 0.5 * np.sin(0.21 * r - 11 * t) * np.sin(0.07 * r + 4 * t)) > 0.62
        shift = np.rint(g * 18 * np.sin(0.9 * r + 9 * t) * bandm).astype(np.int32)
        composite(gid.astype(np.int32), self.prev, self.fade, oxi, oyi, col.astype(np.float32),
                  inten.astype(np.float32), dr.astype(np.float32), ddx.astype(np.float32),
                  ddy.astype(np.float32), shift, ATLAS, img)


ATLAS = build_atlas()

# ---------------------------------------------------------------- text overlay
F_BIG = ImageFont.truetype(FONT, 50)
F_HUD = ImageFont.truetype(FONT_THIN, 50)
CMD = '> explain --how "cooling"'
LOG = ['mesh   hyper_01 ....... ok', 'trace  airflow  >> ducts', 'probe  heat  rotor|core',
       'ascii  decode  10x18 cells', 'render 120fps  blur x4']
HUD = 'hot air exits here'
LX, LY0, LH = 64, 300, 70


def overlay(t, img, intake_xy):
    if not (0.36 < t < 1.62 or 3.3 < t < 4.9):
        return
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    green = (200, 204, 210)
    if t < 1.7:
        a = sstep(0.36, 0.46, t) * (1 - sstep(1.36, 1.52, t))
        panel = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(panel).rounded_rectangle((40, LY0 - 46, 900, LY0 + 5 * LH + 20), 14,
                                                fill=(0, 0, 0, int(200 * a)), outline=(150, 150, 155, int(170 * a)), width=2)
        lay.alpha_composite(panel)
        n = int(len(CMD) * sstep(0.42, 0.80, t) + 1e-6) if t > 0.42 else 0
        # scrolling log lines (smooth, eased offsets)
        shown = [(i, 0.84 + 0.085 * i) for i in range(len(LOG)) if t > 0.84 + 0.085 * i]
        scroll = sum(sstep(st, st + 0.08, t) for i, st in shown) - (0 if not shown else 0)
        lines = [(CMD[:n], (255, 255, 255), 0)] + [(LOG[i], green, i + 1) for i, _ in shown]
        top = LY0 - 12
        for txt, c, k in lines:
            y = top + k * LH - max(0.0, scroll - 3) * LH
            if y < top - 4 or y > LY0 + 4 * LH + 4:
                continue
            fa = min(1.0, (y - (top - LH * .6)) / (LH * .6)) if y < top else 1.0
            d.text((LX, y), txt, font=F_BIG, fill=c + (int(255 * a * max(fa, 0)),))
            if k == 0:
                if n < len(CMD) or (t * 7) % 1 < .55:
                    cx = LX + d.textlength(CMD[:n], font=F_BIG) + 4
                    d.rectangle((cx, y + 6, cx + 26, y + 58), fill=(255, 255, 255, int(230 * a)))
    else:
        a = sstep(3.45, 3.6, t) * (1 - sstep(4.55, 4.72, t))
        n = int(len(HUD) * sstep(3.5, 3.85, t))
        txt = HUD[:n]
        if n < len(HUD):
            txt += '%$&x'[int(t * 60) % 4]
        amber = (255, 255, 255)
        tx, ty = LX, 300
        d.rounded_rectangle((40, ty - 18, 40 + d.textlength(HUD, font=F_HUD) + 50, ty + 86), 12, fill=(0, 0, 0, int(190 * a)))
        d.text((tx, ty), txt, font=F_HUD, fill=amber + (int(255 * a),))
        if a > 0 and intake_xy is not None:
            p = sstep(3.62, 3.95, t)
            x0, y0 = tx + 4, ty + 70
            x1, y1 = intake_xy
            xm, ym = x0 + (x1 - x0) * p, y0 + (y1 - y0) * p
            d.line((x0, y0, x0 + 300, y0), fill=amber + (int(220 * a),), width=2)
            d.line((x0, y0, xm, ym), fill=amber + (int(220 * a),), width=2)
            if p > 0.98:
                rr = 22
                d.ellipse((x1 - rr, y1 - rr, x1 + rr, y1 + rr), outline=amber + (int(230 * a),), width=2)
    arr = np.asarray(lay, np.float32) / 255
    al = arr[..., 3:4]
    img *= 1 - al * 0.92
    img += arr[..., :3] * al


# ---------------------------------------------------------------- post
YY = np.arange(H, dtype=np.float32)[:, None]
SCAN = (0.95 + 0.05 * np.cos(2 * np.pi * YY / 3))[..., None]
_vx = (np.arange(W) - W / 2) / (W / 2); _vy = (np.arange(H) - H / 2) / (H / 2)
VIG = (1 - 0.28 * (_vx[None, :] ** 2 * .6 + _vy[:, None] ** 2 * .4))[..., None].astype(np.float32)


def post(t, img):
    g = glitch(t)
    if g > 0.02:
        k = int(round(6 * g))
        img[..., 0] = np.roll(img[..., 0], k, 1)
        img[..., 2] = np.roll(img[..., 2], -k, 1)
    small = cv2.resize(img, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
    b1 = cv2.GaussianBlur(small, (0, 0), 2.0)
    b2 = cv2.GaussianBlur(small, (0, 0), 9.0)
    warm = np.clip(small[..., 0] - small[..., 1] * 0.75, 0, None)          # heat-coloured energy
    halo = cv2.GaussianBlur(warm, (0, 0), 14.0)[..., None] * np.array([1.0, .38, .08], np.float32)
    bloom = cv2.resize(0.40 * b1 + 0.30 * b2, (W, H), interpolation=cv2.INTER_LINEAR)
    img += bloom
    if 1.28 < t < 1.64:                                  # decode scanline bar
        yw = wipe_y(t)
        prof = np.exp(-((YY[:, 0] - yw) / 5) ** 2) * 0.9 + np.exp(-((YY[:, 0] - yw) / 40) ** 2) * 0.18
        img += prof[:, None, None] * np.array([1, 1, 1], np.float32)
    img *= SCAN * VIG
    np.clip(img, 0, 1, out=img)
    return (img * 255 + 0.5).astype(np.uint8)


# ---------------------------------------------------------------- driver
class Track:
    """EMA-matched screen point for overlays and the motion log."""
    def __init__(self):
        self.v = None

    def __call__(self, p):
        self.v = p if self.v is None else EMA * self.v + (1 - EMA) * p
        return self.v


def frames(indices, want):
    """Yield (i, rgb uint8, meta) for frames in `want`; renders sequentially through `indices`."""
    asc, trk = Ascii(), Track()
    buf = np.zeros((7, len(YS), len(XS)), np.float32)
    acc = np.zeros_like(buf)
    for i in indices:
        t = (i % N) / FPS
        acc[:] = 0
        car = np.zeros(2)
        intake = np.zeros(2)
        for k in range(SUB):
            ts = (t + (k - (SUB - 1) / 2) / (FPS * SUB)) % DUR
            render_sub(ts, buf)
            acc += buf
            cam = camera(ts)
            car += project(CAR_C, cam) / SUB
            intake += project(INTAKE, cam) / SUB
        acc /= SUB
        changed = asc.step(acc)
        ik = trk(intake)
        if i not in want:
            continue
        img = np.zeros((H, W, 3), np.float32)
        asc.draw(t, i, img)
        overlay(t, img, ik)
        m = acc[3]
        tot = m.sum()
        cent = [float((m.sum(0) * XS).sum() / tot), float((m.sum(1) * YS).sum() / tot)] if tot > 0 else [0, 0]
        nonempty = (asc.gid > 0) | (asc.prev > 0)
        meta = dict(i=int(i), t=t, car=car.tolist(), centroid=cent, intake=ik.tolist(),
                    flicker_raw=float(changed[nonempty].mean()) if nonempty.any() else 0.0,
                    flicker=float(asc.vch[asc.vmask].mean()) if asc.vmask.any() else 0.0,
                    glyph_cells=int((asc.gid > 0).sum()))
        yield i, post(t, img), meta


def main():
    mode = sys.argv[1]
    if mode == 'still':
        out = Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
        for stamp in sys.argv[3:]:
            fi = int(round(float(stamp) * FPS)) % N
            for i, rgb, _ in frames(range(fi - PRE, fi + 1), {fi}):
                Image.fromarray(rgb).save(out / f'f_{stamp}.png')
                print('still', stamp, 'frame', fi)
        return
    dst = Path(sys.argv[2]).resolve()
    nf = int(sys.argv[sys.argv.index('--frames') + 1]) if '--frames' in sys.argv else N
    dst.parent.mkdir(parents=True, exist_ok=True)
    master = dst.with_suffix('.master.mkv')
    ff = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}',
                           '-r', str(FPS), '-i', '-', '-c:v', 'ffv1', '-pix_fmt', 'yuv444p', str(master)],
                          stdin=subprocess.PIPE)
    metas, t0 = [], time.time()
    for i, rgb, meta in frames(range(-PRE, nf), set(range(nf))):
        ff.stdin.write(rgb.tobytes())
        metas.append(meta)
        if i % 15 == 0:
            print(f'frame {i}/{nf} {time.time() - t0:.0f}s', flush=True)
    ff.stdin.close()
    assert ff.wait() == 0
    json.dump(metas, open(dst.with_suffix('.frames.json'), 'w'))
    log = str(dst.with_suffix('')) + '_2pass'
    common = ['-c:v', 'libx264', '-preset', 'slow', '-profile:v', 'high', '-pix_fmt', 'yuv420p', '-b:v', '7600k',
              '-maxrate', '8000k', '-bufsize', '8000k', '-r', str(FPS), '-g', str(FPS), '-passlogfile', log, '-an']
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(master), *common, '-pass', '1', '-f', 'null', '-'], check=True)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(master), *common, '-pass', '2',
                    '-movflags', '+faststart', str(dst)], check=True)
    for p in Path(dst.parent).glob(Path(log).name + '*'):
        p.unlink()
    print('wrote', dst, f'{time.time() - t0:.0f}s')


if __name__ == '__main__':
    main()
