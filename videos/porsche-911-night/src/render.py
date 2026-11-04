"""NIGHT RUN // 911 — pixel-art drive of a 2017 Porsche 911 (991.2 Carrera 4S) through a rainy neon city.

usage: python render.py still OUTDIR t1 t2 ...   |   python render.py video OUT.mp4 [t0 t1]
"""
import sys, subprocess, math
from functools import lru_cache
from multiprocessing import Pool
import numpy as np
from PIL import Image
from pixkit import (W, H, Lay, blit, blit_tile, grad, bloom, finish, reflect, Rain, splashes, text, text_w, alien,
                    smooth)
import car911 as C

FPS, SC = 30, 3
DUR = 27.5
CUTS = [0.0, 5.0, 10.0, 15.0, 20.0, DUR]


def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def oc(x): return 1 - (1 - clamp(x)) ** 3
def io(x): x = clamp(x); return 4 * x ** 3 if x < .5 else 1 - (-2 * x + 2) ** 3 / 2
def cruise(u): u = clamp(u); return u + 0.12 * math.sin(2 * math.pi * u)   # fast in/out, slow through the middle


def flick(t, seed, rate=0.04):
    fr = int(t * 30)
    r = np.random.default_rng(seed * 7919 + fr // 2)
    if r.random() < rate: return 0.12
    return 0.93 + 0.07 * math.sin(t * 50 + seed)


def mix(a, b, k): return np.array(a, float) * (1 - k) + np.array(b, float) * k


def beam(F, E, x0, y0, length, col=(210, 225, 255), k=1.0, spread=(2, 26), dirn=1):
    for i in range(int(length)):
        x = int(x0 + dirn * i)
        if not 0 <= x < W: continue
        uu = i / length
        half = spread[0] + (spread[1] - spread[0]) * uu
        ya, yb = max(int(y0 - half * 0.45), 0), min(int(y0 + half), H)
        if ya >= yb: continue
        yy = np.arange(ya, yb)
        edge = 1 - np.abs((yy - y0 - half * 0.27) / (half * 0.73 + 1e-6))
        inten = (k * (1 - uu) ** 1.6 * np.clip(edge, 0, 1) ** 0.7)[:, None]
        E[ya:yb, x] += np.array(col) * inten * 0.2
        F[ya:yb, x] += np.array(col) * inten * 0.14


def put_car(F, E, c, x, yG, dist, speed, env, env2=None, streak=0.0, spoiler=False, beam_on=True, gloss=1.0, bk=1.0):
    r = c['wheels'][0][2]
    ang = -dist / r
    blur = clamp(speed / FPS / r * 0.9, 0, 2.4)
    L = C.side_frame(c, ang, blur, env, env2, streak, True, spoiler, gloss)
    y = yG - 1 - c['gy']
    x0, x1 = max(int(x + 0.1 * c['s']), 0), min(int(x + 4.5 * c['s']), W)
    if x0 < x1: F[yG - 3:yG, x0:x1] *= 0.4
    blit(F, E, L, x, y)
    if beam_on:
        beam(F, E, x + 4 + 4.40 * c['s'], y + c['gy'] - 0.72 * c['s'], int(4.0 * c['s']), k=bk, spread=(1.5, 0.9 * c['s']))
        beam(F, E, x + 4, y + c['gy'] - 0.86 * c['s'], int(0.8 * c['s']), col=(255, 40, 40), k=0.6 * bk,
             spread=(1, 0.22 * c['s']), dirn=-1)


def brick(lay, x0, y0, x1, y1, base, r, bw=8, bh=4, var=6, mortar=0.78):
    base = np.array(base, float)
    for y in range(int(y0), int(y1), bh):
        off = (y // bh) % 2 * (bw // 2)
        for x in range(int(x0) - off, int(x1), bw):
            lay.rect(max(x, x0), y, min(x + bw - 2, x1), min(y + bh - 2, y1), base + r.uniform(-var, var))
        lay.rect(x0, y + bh - 1, x1, y + bh - 1, base * mortar)


def ac_unit(lay, x, y, w=14, h=9, base=(70, 76, 88)):
    b = np.array(base, float)
    lay.rect(x, y, x + w, y + h, b); lay.rect(x, y, x + w, y, b * 1.3); lay.rect(x, y + h, x + w, y + h, b * 0.5)
    lay.ellipse(x + 2, y + 2, x + 8, y + h - 2, b * 0.55)
    for k in range(x + 10, x + w - 1, 2): lay.rect(k, y + 2, k, y + h - 2, b * 0.7)
    lay.rect(x + w - 3, y + h, x + w - 2, y + h + 3, b * 0.5)


def shoji(lay, x0, y0, x1, y1, lit, frame, glow_k=0.7, gx=6, gy=7):
    lay.rect(x0 - 1, y0 - 1, x1 + 1, y1 + 1, frame)
    lay.rect(x0, y0, x1, y1, lit, glow=np.array(lit) * glow_k)
    for x in range(x0 + gx, x1, gx): lay.rect(x, y0, x, y1, np.array(lit) * 0.62)
    for y in range(y0 + gy, y1, gy): lay.rect(x0, y, x1, y, np.array(lit) * 0.62)


def window(lay, x, y, w, h, wall, r, lit_p=0.3, cols=((255, 190, 100),)):
    wall = np.array(wall, float)
    lay.rect(x - 1, y - 1, x + w, y + h + 1, wall * 0.55)
    lay.rect(x - 1, y + h + 1, x + w, y + h + 2, wall * 1.35)
    if r.random() < lit_p:
        c = np.array(cols[int(r.integers(0, len(cols)))], float) * r.uniform(0.6, 1.0)
        lay.rect(x, y, x + w - 1, y + h, c, glow=c * 0.45)
        if r.random() < 0.6:
            cw = int(r.uniform(2, w / 2)); lay.rect(x, y, x + cw, y + h, c * 0.6)
        if r.random() < 0.3:
            px = x + int(r.uniform(2, max(3, w - 5)))
            lay.ellipse(px, y + h - 9, px + 3, y + h - 6, c * 0.25); lay.rect(px - 1, y + h - 6, px + 4, y + h, c * 0.25)
        lay.rect(x + w // 2, y, x + w // 2, y + h, c * 0.55)
    else:
        lay.rect(x, y, x + w - 1, y + h, wall * 0.3 + np.array((4, 6, 14)))
        lay.rect(x, y, x + 1, y + 2, wall * 0.9)
        lay.rect(x + w // 2, y, x + w // 2, y + h, wall * 0.5)


# ======================================================================= S1 teal dusk causeway
class S1:
    yG = 436

    @lru_cache(None)
    def build(self):
        yG = self.yG; r = np.random.default_rng(1)
        d = {}
        sky = grad(yG, W, [(0, (10, 50, 78)), (0.42, (22, 102, 132)), (0.82, (50, 148, 170)), (1, (96, 184, 194))], 6)
        for _ in range(9):
            y = int(r.uniform(15, 300)); x0 = int(r.uniform(-60, W)); ln = int(r.uniform(60, 200))
            for k in range(2):
                xs = slice(max(0, x0 + k * 9), max(0, min(W, x0 + ln - k * 14)))
                sky[y + k, xs] = sky[y + k, xs] * 0.82 + np.array((120, 196, 206)) * 0.18
        d['sky'] = sky
        cx = 262
        ys, xs = np.mgrid[0:yG, 0:W]
        hw = 70 * np.sqrt(1 + ((ys - 140) / 165.0) ** 2)
        u = (xs - cx) / hw
        inside = np.abs(u) <= 1
        sq = np.sqrt(np.clip(1 - u * u, 0, 1))
        lit = np.clip(0.62 - 0.5 * u + 0.18 * sq, 0, 1)
        col = mix((10, 34, 52), (46, 104, 126), lit[..., None])
        rib = np.abs(((np.arcsin(np.clip(u, -1, 1)) / (np.pi / 18)) % 1) - 0.5) < 0.09
        col = np.where(rib[..., None], col * 0.88, col)
        bandy = (ys + 5 * sq) % 15
        col = np.where((bandy < 1.2)[..., None], col * 0.9, col)
        hz = smooth(160, 430, ys)[..., None] * 0.4
        col = col * (1 - hz) + sky * hz
        e = np.zeros((yG, W, 3))
        winm = (bandy > 4) & (bandy < 5.5) & inside & (r.random((yG, W)) < 0.10) & (ys < 330)
        wc = np.where((r.random((yG, W)) < 0.7)[..., None], np.array((255, 214, 130)), np.array((150, 230, 255)))
        col = np.where(winm[..., None], wc * (1 - hz * 0.8), col)
        e = np.where(winm[..., None], wc * 0.5 * (1 - hz), e)
        for y0, k, th in ((48, 1.0, 2), (56, 0.5, 1), (186, 0.55, 1)):
            ring = inside & (np.abs(ys - (y0 + 6 * sq)) < th * 0.5 + 0.5)
            col = np.where(ring[..., None], np.maximum(col, np.array((255, 64, 96)) * k), col)
            e = np.where(ring[..., None], np.array((255, 30, 70)) * k, e)
        d['tower'] = dict(rgb=col, a=inside.astype(float), e=e)
        m = Lay(720, yG)
        xx = np.arange(0, 721, 2)
        for base, amp, colm, seed in ((340, 34, (50, 128, 150), 0), (372, 22, (34, 98, 122), 1)):
            rr = np.random.default_rng(seed + 10)
            ridge = base - amp * (0.6 * np.sin(xx / 720 * 2 * np.pi * 2 + seed) + 0.3 * np.sin(xx / 720 * 2 * np.pi * 7 + 2 * seed)
                                  + 0.15 * np.sin(xx / 720 * 2 * np.pi * 19)) + rr.uniform(-1.5, 1.5, len(xx))
            m.poly([(0, yG)] + list(zip(xx, ridge)) + [(720, yG)], colm)
            m.line(list(zip(xx, ridge)), np.array(colm) * 1.18)
        d['mount'] = m.done()
        f = Lay(480, yG)
        f.rect(0, 404, 479, yG, (10, 38, 48))
        x = 0.0
        while x < 480:
            hgt = r.uniform(18, 48); bx = x
            for k in range(int(hgt)):
                hwk = (k / hgt) * 7 + 0.5 + (k % 6 == 5) * 1.5
                f.rect(bx - hwk, 404 - hgt + k, bx + hwk, 404 - hgt + k, (10, 38, 48) if k % 6 else (14, 48, 58))
            f.rect(bx - 0.5, 404 - hgt - 3, bx + 0.5, 404 - hgt, (14, 48, 58))
            x += r.uniform(4, 10)
        d['forest'] = f.done()
        s = Lay(720, yG)
        s.rect(0, yG - 5, 719, yG, (14, 30, 38))
        bx, bw, top = 70, 200, yG - 60
        wall = np.array((20, 46, 58))
        s.rect(bx, top, bx + bw, yG - 5, wall); s.rect(bx - 4, top - 4, bx + bw + 4, top, wall * 0.6)
        s.rect(bx - 4, top - 4, bx + bw + 4, top - 4, wall * 1.6)
        for k in range(8):
            wx = bx + 10 + k * 22
            s.rect(wx, top + 14, wx + 18, top + 40, (255, 236, 150), glow=(210, 170, 80))
            s.rect(wx, top + 30, wx + 18, top + 40, (210, 170, 90))
            if k % 3 == 1:
                s.ellipse(wx + 6, top + 18, wx + 11, top + 23, (60, 44, 30)); s.rect(wx + 4, top + 23, wx + 13, top + 32, (60, 44, 30))
        s.rect(bx + bw - 26, top + 10, bx + bw - 10, yG - 5, (130, 200, 210), glow=(50, 110, 120))
        s.rect(bx + bw - 24, top + 12, bx + bw - 12, top + 30, (200, 240, 245), glow=(80, 140, 150))
        for px in (bx + 40, bx + 120): s.rect(px, top - 26, px + 1, top - 4, (12, 30, 40))
        s.rect(bx + 30, top - 40, bx + 132, top - 22, (14, 22, 30))
        text(s, 'DINER', bx + 36, top - 37, (255, 80, 100), glow=(255, 40, 70), sc=2)
        s.rect(bx + 30, top - 40, bx + 132, top - 40, (255, 80, 100), glow=(200, 40, 60))
        for vx in (bx + bw + 10, bx + bw + 24):
            s.rect(vx, yG - 30, vx + 11, yG - 5, (190, 230, 240), glow=(90, 150, 170))
            s.rect(vx + 2, yG - 27, vx + 9, yG - 18, (80, 140, 200)); s.rect(vx + 2, yG - 14, vx + 9, yG - 11, (40, 60, 70))
        s.rect(bx - 40, yG - 74, bx - 39, yG - 5, (12, 28, 36)); s.rect(bx - 40, yG - 74, bx - 28, yG - 73, (12, 28, 36))
        s.rect(bx - 31, yG - 73, bx - 26, yG - 71, (255, 190, 110), glow=(255, 150, 60))
        hx = 400; s.poly([(hx - 6, yG - 44), (hx + 40, yG - 66), (hx + 86, yG - 44)], (16, 36, 46))
        s.rect(hx, yG - 44, hx + 80, yG - 5, (18, 40, 50))
        s.rect(hx + 12, yG - 34, hx + 24, yG - 22, (255, 196, 110), glow=(180, 120, 50)); s.rect(hx + 18, yG - 34, hx + 18, yG - 22, (150, 100, 50))
        s.rect(hx + 50, yG - 34, hx + 62, yG - 22, (12, 26, 34))
        s.rect(hx + 32, yG - 26, hx + 42, yG - 5, (12, 26, 34))
        gx = 560; s.rect(gx, yG - 40, gx + 110, yG - 5, (16, 36, 46)); s.rect(gx - 3, yG - 43, gx + 113, yG - 40, (24, 50, 60))
        for k in range(3):
            s.rect(gx + 8 + k * 34, yG - 30, gx + 34 + k * 34, yG - 5, (24, 48, 58))
            for yy in range(yG - 28, yG - 5, 3): s.rect(gx + 8 + k * 34, yy, gx + 34 + k * 34, yy, (14, 32, 40))
        s.rect(gx + 40, yG - 56, gx + 70, yG - 46, (20, 30, 36)); alien(s, gx + 43, yG - 54, 6, (120, 255, 220), glow=(40, 170, 150), seed=7)
        d['shops'] = s.done()
        p = Lay(300, yG)
        pc = (8, 26, 34)
        for xx in (150, 450, -150):
            p.rect(xx, 96, xx + 2, yG - 5, pc)
            for ay, aw in ((104, 24), (122, 16)):
                p.rect(xx - aw, ay, xx + aw + 2, ay + 1, pc)
                for o in (-aw, -aw // 2, aw // 2, aw): p.rect(xx + o, ay - 3, xx + o + 1, ay - 1, (44, 70, 80))
            p.rect(xx - 6, 138, xx + 8, 152, (16, 40, 50)); p.rect(xx - 6, 138, xx + 8, 138, (40, 70, 80))
        xs_ = np.linspace(0, 300, 80)
        for ay, aw in ((104, 24), (122, 16)):
            for o in (-aw, -aw // 2, aw // 2, aw):
                for base in (-150, 150):
                    p.line(list(zip(base + o + xs_, ay - 2 + 26 * (1 - ((xs_ - 150) / 150) ** 2))), (6, 22, 30))
        d['poles'] = p.done()
        rp = Lay(60, yG)
        rp.rect(10, yG - 12, 11, yG - 1, (180, 190, 190)); rp.rect(10, yG - 11, 11, yG - 9, (255, 70, 60), glow=(200, 30, 30))
        d['posts'] = rp.done()
        d['rain'] = Rain(330, 11, speed=(260, 360), length=(5, 11), slant=0.14, col=(176, 222, 236), alpha=(0.18, 0.45))
        d['car'] = C.side(156)
        return d

    def frame(self, t):
        d = self.build(); yG = self.yG
        F = np.vstack([d['sky'], np.zeros((H - yG, W, 3))]).astype(float); E = np.zeros_like(F)
        v = 95.0
        scroll = v * t + 60
        sx = -180 + 285 * oc(t / 2.6) + 8 * math.sin(t * 0.9)
        blit(F, E, d['tower'], -scroll * 0.03, 0, ek=0.85 + 0.15 * math.sin(t * 2.5))
        blit_tile(F, E, d['mount'], scroll * 0.08, 0)
        blit_tile(F, E, d['forest'], scroll * 0.22, 0)
        blit_tile(F, E, d['shops'], scroll * 0.5, 0)
        blit_tile(F, E, d['poles'], scroll * 0.75, 0)
        blit_tile(F, E, d['posts'], scroll * 1.0, 0)
        sp = v + 285 * 3 * (1 - clamp(t / 2.6)) ** 2 / 2.6
        put_car(F, E, d['car'], sx, yG, scroll + sx, sp, env=(40, 140, 170), env2=(170, 235, 245), streak=-scroll * 0.6)
        reflect(F, E, yG, t, dark=0.52, tint=(4, 20, 30), stretch=0.74)
        F[yG] = F[yG] * 0.5 + np.array((40, 90, 100)) * 0.5
        d['rain'].draw(F, t, E=E)
        splashes(F, t, yG + 2, H - 2, 22, 1, (150, 210, 225))
        return F, E


# ======================================================================= S2 neon ramen street (hero shop)
class S2:
    yG = 548
    LW = 560

    @lru_cache(None)
    def build(self):
        yG, LW = self.yG, self.LW; r = np.random.default_rng(2)
        d = {}
        d['sky'] = grad(H, W, [(0, (3, 5, 18)), (0.5, (8, 12, 38)), (1, (12, 18, 52))], 6)
        back = Lay(LW, yG)
        x = 0
        while x < LW:
            bw = int(r.uniform(30, 70)); top = int(r.uniform(10, 120))
            back.rect(x, top, x + bw, yG, (10, 14, 36)); back.rect(x, top, x + bw, top, (20, 26, 60))
            for _ in range(int(bw * (yG - top) / 500)):
                wx, wy = int(r.uniform(x + 2, x + bw - 3)), int(r.uniform(top + 4, yG - 100))
                back.rect(wx, wy, wx + 1, wy, (50, 60, 110))
            x += bw - 2
        d['back'] = back.done()
        f = Lay(LW, yG); sg = Lay(LW, yG); fl = Lay(LW, yG)
        wl = np.array((18, 22, 48))       # left neighbour with fire escape + blue blade sign
        f.rect(0, 70, 120, yG, wl); f.rect(0, 70, 120, 72, wl * 1.6)
        for fy in range(96, yG - 90, 44):
            for wx in range(10, 100, 26): window(f, wx, fy, 14, 20, wl, r, 0.25, ((255, 180, 90), (120, 200, 255)))
            f.rect(0, fy + 30, 118, fy + 31, wl * 0.6)
        for k, fy in enumerate(range(120, yG - 70, 44)):
            f.rect(84, fy + 26, 120, fy + 27, (40, 46, 70))
            for sx in range(84, 121, 4): f.rect(sx, fy + 20, sx, fy + 26, (34, 40, 62))
            a, b = (86, 118) if k % 2 == 0 else (118, 86)
            f.line([(a, fy + 26), (b, fy + 70)], (40, 46, 70), width=2)
        sg.rect(30, 140, 48, 270, (8, 14, 40))
        sg.rect(30, 140, 48, 140, (90, 150, 255), glow=(40, 90, 220)); sg.rect(30, 270, 48, 270, (90, 150, 255), glow=(40, 90, 220))
        for gy in range(148, 262, 14): alien(sg, 33, gy, 1, (140, 200, 255), glow=(60, 120, 230), seed=gy, sz=11)
        x0, x1, top = 130, 420, 34       # hero ramen building
        wall = np.array((46, 20, 28))
        f.rect(x0, top, x1, yG, wall * 0.9)
        brick(f, x0, top + 10, x1, 330, wall, r)
        f.rect(x0 - 4, top, x1 + 4, top + 9, wall * 0.6); f.rect(x0 - 4, top, x1 + 4, top, wall * 1.7)
        f.rect(x0 + 200, top - 30, x0 + 236, top, (36, 30, 40)); f.ellipse(x0 + 200, top - 36, x0 + 236, top - 24, (50, 42, 54))
        for k in range(3): f.rect(x0 + 204 + k * 12, top - 24, x0 + 204 + k * 12, top, (24, 20, 30))
        f.line([(x0 + 40, top), (x0 + 40, top - 40)], (30, 26, 36)); f.line([(x0 + 34, top - 30), (x0 + 46, top - 30)], (30, 26, 36))
        for k in range(0, 290, 6): f.rect(x0 + k, top - 6, x0 + k, top, (30, 22, 30))
        f.rect(x0, top - 7, x1, top - 7, (50, 38, 48))
        for wx in (x0 + 16, x0 + 76, x0 + 210):
            shoji(f, wx, top + 26, wx + 42, top + 70, (150, 84, 40), wall * 0.4, 0.35)
            ac_unit(f, wx + 6, top + 76)
        shoji(f, x0 + 136, top + 26, x0 + 178, top + 70, (255, 176, 80), wall * 0.4, 0.6)
        f.ellipse(x0 + 152, top + 40, x0 + 160, top + 48, (90, 50, 30)); f.rect(x0 + 148, top + 48, x0 + 164, top + 70, (90, 50, 30))
        f.rect(x0, top + 96, x1, top + 98, wall * 0.55)
        for wx in (x0 + 196, x0 + 246): shoji(f, wx, 210, wx + 34, 252, (220, 140, 60), wall * 0.4, 0.45)
        f.rect(x0 + 190, 252, x0 + 286, 254, (60, 50, 60))
        for bx in range(x0 + 190, x0 + 287, 5): f.rect(bx, 240, bx, 252, (60, 50, 60))
        f.rect(x0 + 190, 240, x0 + 286, 240, (80, 66, 76))
        for px in (x0 + 196, x0 + 230, x0 + 262):
            f.rect(px, 246, px + 6, 252, (70, 40, 34)); f.ellipse(px - 2, 238, px + 8, 247, (20, 60, 40))
        f.rect(x1 - 8, top + 10, x1 - 6, yG, (30, 26, 36)); f.rect(x1 - 8, top + 10, x1 - 8, yG, (60, 52, 66))
        for yy in range(top + 40, yG, 60): f.rect(x1 - 10, yy, x1 - 4, yy + 2, (60, 52, 66))
        cx, cy, R = x0 + 70, 168, 40      # big red neon circle + pill sign
        sg.rect(cx, cy - 22, cx + 150, cy + 22, (36, 4, 10))
        sg.ellipse(cx + 128, cy - 22, cx + 172, cy + 22, (36, 4, 10))
        sg.line([(cx, cy - 22), (cx + 150, cy - 22)], (255, 46, 46), glow=(255, 30, 30), width=2)
        sg.line([(cx, cy + 22), (cx + 150, cy + 22)], (255, 46, 46), glow=(255, 30, 30), width=2)
        sg.ellipse(cx + 128, cy - 22, cx + 172, cy + 22, None, outline=(255, 46, 46), glow=(255, 30, 30))
        for k in range(3): alien(sg, cx + R + 8 + k * 30, cy - 14, 1, (255, 255, 250), glow=(255, 190, 190), seed=60 + k, sz=11)
        alien(sg, cx + R + 8, cy + 8, 10, (255, 230, 226), glow=(180, 110, 110), seed=71, sz=4)
        sg.ellipse(cx - R, cy - R, cx + R, cy + R, (226, 24, 32), glow=(255, 30, 40))
        sg.ellipse(cx - R + 3, cy - R + 3, cx + R - 3, cy + R - 3, None, outline=(255, 120, 110), glow=(255, 70, 70))
        sg.ellipse(cx - R, cy - R, cx + R, cy + R, None, outline=(255, 170, 150), glow=(255, 100, 100))
        sg.poly([(cx - 22, cy + 2), (cx + 22, cy + 2), (cx + 15, cy + 20), (cx - 15, cy + 20)], (255, 240, 226), glow=(255, 200, 180))
        sg.poly([(cx - 18, cy + 5), (cx + 18, cy + 5), (cx + 12, cy + 17), (cx - 12, cy + 17)], (226, 24, 32))
        sg.rect(cx - 8, cy + 20, cx + 8, cy + 23, (255, 240, 226), glow=(255, 200, 180))
        for nx in range(-13, 14, 4): sg.line([(cx + nx, cy - 24), (cx + nx, cy + 2)], (255, 214, 70), glow=(230, 160, 40))
        sg.line([(cx - 4, cy - 30), (cx + 26, cy - 6)], (255, 240, 226), glow=(255, 200, 180), width=2)
        sg.line([(cx + 2, cy - 32), (cx + 30, cy - 10)], (255, 240, 226), glow=(255, 200, 180), width=2)
        sg.rect(cx - 24, cy + 2, cx + 24, cy + 3, (255, 240, 226), glow=(255, 200, 180))
        vx = x1 - 34                       # flickering vertical banner + yellow bars
        fl.rect(vx, 20, vx + 22, 230, (232, 22, 32), glow=(255, 24, 34))
        fl.rect(vx + 2, 22, vx + 20, 228, (210, 16, 26))
        for gy in range(30, 220, 18): alien(fl, vx + 5, gy, 1, (70, 0, 8), seed=gy, sz=12)
        fl.rect(vx, 20, vx + 22, 21, (255, 150, 150), glow=(255, 90, 90)); fl.rect(vx, 229, vx + 22, 230, (255, 150, 150), glow=(255, 90, 90))
        for k in range(5): sg.rect(x0 + 200, 270 + k * 8, x0 + 250, 273 + k * 8, (255, 214, 60), glow=(230, 160, 30))
        f.rect(x0, 330, x1, yG, wall * 0.5)  # shopfront
        f.rect(x0, 330, x1, 356, (16, 10, 16))
        alien(sg, x0 + 14, 337, 7, (90, 245, 235), glow=(30, 170, 170), seed=12, sz=6)
        for k in range(2): sg.ellipse(x0 + 230 + k * 14, 336, x0 + 240 + k * 14, 348, (90, 245, 235), glow=(30, 170, 170))
        aw0 = 358
        for k, ax in enumerate(range(x0 + 4, x1 - 6, 12)):
            c_ = (170, 124, 50) if k % 2 == 0 else (46, 30, 24)
            f.poly([(ax, aw0), (ax + 12, aw0), (ax + 15, aw0 + 22), (ax + 3, aw0 + 22)], c_)
            f.ellipse(ax + 3, aw0 + 19, ax + 15, aw0 + 26, c_)
        f.rect(x0 + 2, aw0, x1 - 2, aw0, (200, 160, 80))
        wx0, wx1 = x0 + 14, x0 + 176
        shoji(f, wx0, 392, wx1, 530, (255, 230, 86), (30, 16, 12), 0.75, gx=18, gy=34)
        f.rect(wx0, 470, wx1, 474, (120, 70, 30))
        f.ellipse(wx0 + 36, 410, wx0 + 52, 428, (40, 24, 20)); f.rect(wx0 + 32, 404, wx0 + 56, 412, (240, 236, 226))
        f.rect(wx0 + 30, 428, wx0 + 58, 470, (40, 24, 20))
        f.ellipse(wx0 + 106, 422, wx0 + 120, 438, (40, 24, 20)); f.rect(wx0 + 100, 438, wx0 + 126, 470, (40, 24, 20))
        for k in range(3): f.rect(wx0 + 70 + k * 6, 440 - k * 9, wx0 + 72 + k * 6, 446 - k * 9, (255, 246, 200))
        for k in range(4):
            sg.line([(wx0 + 20 + k * 40, 392), (wx0 + 20 + k * 40, 400)], (60, 40, 20))
            sg.ellipse(wx0 + 15 + k * 40, 400, wx0 + 25 + k * 40, 406, (255, 250, 200), glow=(255, 220, 120))
        f.rect(wx0, 474, wx1, 530, (90, 52, 26))
        dx0, dx1 = x0 + 196, x0 + 262
        f.rect(dx0, 386, dx1, yG, (14, 22, 46))
        sg.ellipse(dx0 + 10, 440, dx1 - 10, 496, None, outline=(90, 170, 230), glow=(30, 80, 130))
        sg.poly([(dx0 + 22, 466), (dx1 - 22, 466), (dx1 - 28, 480), (dx0 + 28, 480)], (60, 120, 180), glow=(20, 60, 100))
        for k in range(4):
            f.rect(dx0 + 2 + k * 16, 386, dx0 + 15 + k * 16, 420, (200, 26, 34))
            f.rect(dx0 + 2 + k * 16, 386, dx0 + 15 + k * 16, 388, (120, 10, 20))
            alien(f, dx0 + 5 + k * 16, 396, 1, (250, 236, 226), seed=k + 3, sz=7)
        for lx in (dx0 - 8, dx1 + 10):
            sg.line([(lx, 380), (lx, 388)], (40, 20, 20))
            sg.ellipse(lx - 7, 388, lx + 7, 408, (255, 40, 40), glow=(240, 30, 30))
            for yy in (393, 398, 403): sg.rect(lx - 6, yy, lx + 6, yy, (160, 10, 20))
            sg.rect(lx - 3, 386, lx + 3, 388, (30, 20, 20)); sg.rect(lx - 3, 408, lx + 3, 410, (30, 20, 20))
        f.rect(x1 - 30, 500, x1 - 6, yG - 2, (30, 26, 30)); f.poly([(x1 - 30, 500), (x1 - 6, 500), (x1 - 10, 488), (x1 - 26, 488)], (40, 34, 40))
        alien(sg, x1 - 26, 506, 3, (255, 220, 120), glow=(200, 150, 60), seed=88, sz=5)
        for k in range(3): f.rect(x0 + 180, yG - 14 - k * 10, x0 + 192, yG - 6 - k * 10, (70, 50, 36))
        wr = np.array((16, 20, 44))         # right neighbour
        f.rect(420, 110, LW, yG, wr); f.rect(420, 110, LW, 112, wr * 1.6)
        for fy in range(132, yG - 100, 46):
            for wx in range(434, LW - 14, 30): window(f, wx, fy, 16, 22, wr, r, 0.22, ((255, 180, 90),))
        for k in range(4): ac_unit(f, 430, 300 + k * 13, base=(56, 60, 76))
        for vx in (470, 488):
            f.rect(vx, yG - 52, vx + 15, yG - 2, (150, 220, 240), glow=(60, 130, 160))
            f.rect(vx + 2, yG - 48, vx + 13, yG - 30, (40, 90, 160)); f.rect(vx + 2, yG - 20, vx + 13, yG - 16, (30, 40, 60))
            for yy in range(yG - 46, yG - 31, 4): f.rect(vx + 3, yy, vx + 12, yy, (220, 120, 90))
        f.rect(440, 160, 442, yG, (34, 38, 60)); f.rect(450, 160, 452, yG, (34, 38, 60))
        f.rect(0, yG - 3, LW, yG, (30, 24, 34))
        d['front'] = f.done(); d['signs'] = sg.done(); d['flick'] = fl.done()
        d['rain'] = Rain(380, 22, speed=(300, 400), length=(6, 12), slant=0.08, col=(170, 170, 230), alpha=(0.16, 0.42))
        d['car'] = C.side(196)
        return d

    def frame(self, t):
        d = self.build(); yG = self.yG
        F = d['sky'].astype(float).copy(); E = np.zeros_like(F)
        off = 30 + 120 * io(t / 5.0)
        blit(F, E, d['back'], -off * 0.4, 0)
        blit(F, E, d['front'], -off, 0)
        blit(F, E, d['signs'], -off, 0, ek=flick(t, 3, 0.02))
        blit(F, E, d['flick'], -off, 0, ek=flick(t, 9, 0.08) * 1.1)
        sx = -220 + 620 * cruise(t / 5.0)
        wx = sx + off + 100
        env2 = (255, 60, 60) if 120 < wx < 330 else (255, 214, 100) if wx < 420 else (140, 210, 255)
        put_car(F, E, d['car'], sx, yG, 124 * t, 124, env=(56, 26, 60), env2=env2, streak=-(sx + off * 2), gloss=1.15)
        reflect(F, E, yG, t, dark=0.58, tint=(6, 6, 20), stretch=0.55, band=0.35)
        d['rain'].draw(F, t, E=E)
        splashes(F, t, yG + 2, H - 2, 18, 2, (190, 170, 230))
        return F, E


# ======================================================================= S3 close-up pan along the car
class S3:
    yG = 452

    @lru_cache(None)
    def build(self):
        r = np.random.default_rng(3); yG = self.yG
        d = {}
        d['sky'] = grad(H, W, [(0, (5, 3, 16)), (0.55, (16, 9, 36)), (1, (26, 14, 50))], 6)
        city = Lay(1000, yG)
        x = 0
        while x < 1000:
            bw = int(r.uniform(20, 56)); top = int(r.uniform(180, 330))
            city.rect(x, top, x + bw, yG, (16, 10, 34)); city.rect(x, top, x + bw, top, (34, 20, 60))
            for wy in range(top + 5, yG - 40, 6):
                for wx in range(x + 3, x + bw - 6, 6):
                    if r.random() < 0.22:
                        c = np.array([(255, 170, 80), (255, 90, 170)][int(r.random() < 0.3)])
                        city.rect(wx, wy, wx + 2 + int(r.integers(0, 8)), wy, c * 0.55, glow=c * 0.3)
            x += bw + 3
        d['city'] = city.done()
        bok = Lay(900, yG)
        for _ in range(60):
            bx, by, br = r.uniform(0, 900), r.uniform(160, yG - 50), r.uniform(4, 15)
            c = np.array([(255, 70, 150), (255, 170, 70), (110, 170, 255)][int(r.integers(0, 3))])
            k = r.uniform(0.25, 0.55)
            bok.ellipse(bx - br * 1.7, by - br, bx + br * 1.7, by + br, c * k * 0.55, glow=c * k * 0.45)
        d['bokeh'] = bok.done(); d['bokeh']['a'] *= 0.55
        streaks = Lay(800, 60)
        for _ in range(36):
            sx, sy, sl = r.uniform(0, 800), r.uniform(0, 60), r.uniform(30, 110)
            c = np.array([(255, 80, 150), (120, 190, 255), (255, 190, 90)][int(r.integers(0, 3))])
            streaks.line([(sx, sy), (sx + sl, sy)], c * 0.6, glow=c * 0.5)
        d['streaks'] = streaks.done()
        rail = Lay(200, yG)
        rail.rect(0, yG - 44, 199, yG - 38, (70, 78, 100)); rail.rect(0, yG - 44, 199, yG - 44, (160, 168, 196))
        rail.rect(0, yG - 33, 199, yG - 31, (46, 50, 70))
        for k in range(10): rail.rect(k * 20, yG - 44, k * 20 + 12, yG - 4, (26, 26, 40))
        rail.rect(0, yG - 4, 199, yG, (18, 16, 26))
        d['rail'] = rail.done(); d['rail']['a'] *= 0.85
        d['rain'] = Rain(300, 33, speed=(220, 300), length=(8, 18), slant=-0.9, col=(200, 200, 255), alpha=(0.18, 0.45))
        d['car'] = C.side(520)
        tl = Lay(W, 50)
        text(tl, 'CARRERA 4S', 180 - text_w('CARRERA 4S', 3) // 2, 4, (255, 255, 255), glow=(200, 200, 230), sc=3)
        text(tl, '991.2  /  2017', 180 - text_w('991.2  /  2017', 1) // 2, 34, (255, 90, 100), glow=(220, 40, 60), sc=1)
        d['title'] = tl.done()
        return d

    def frame(self, t):
        d = self.build(); yG = self.yG; c = d['car']
        F = d['sky'].astype(float).copy(); E = np.zeros_like(F)
        v = 1100.0
        blit_tile(F, E, d['city'], v * t * 0.05, 0)
        blit_tile(F, E, d['bokeh'], v * t * 0.22, 0)
        blit_tile(F, E, d['streaks'], v * t * 0.6, 200)
        blit_tile(F, E, d['rail'], v * t, 0)
        x = -(c['w'] - W) - 10 + (c['w'] - W + 20) * io(t / 5.0)
        shake = int(round(math.sin(t * 47) * 0.6))
        put_car(F, E, c, x, yG + shake, v * t, v, env=(70, 30, 110), env2=(255, 130, 210), streak=-v * t * 0.2,
                spoiler=t > 1.4, gloss=1.1, bk=1.3)
        reflect(F, E, yG, t, dark=0.5, tint=(6, 4, 18), stretch=0.8, band=0.3, wob=1.6)
        rr = np.random.default_rng(int(t * 30))
        for _ in range(12):
            y = int(rr.uniform(yG + 4, H - 4)); x0 = int(rr.uniform(-40, W)); ln = int(rr.uniform(30, 90))
            F[y, max(x0, 0):max(0, min(x0 + ln, W))] += 26
        d['rain'].draw(F, t, E=E)
        a = smooth(1.4, 2.2, t) * (1 - smooth(4.4, 4.9, t))
        if a > 0: blit(F, E, d['title'], 0, 560, alpha=a, ek=a * flick(t, 5, 0.05))
        return F, E


# ======================================================================= S4 blue overpass + lightning
class S4:
    yG = 566

    @lru_cache(None)
    def build(self):
        r = np.random.default_rng(4); yG = self.yG
        d = {}
        d['sky'] = grad(H, W, [(0, (3, 8, 28)), (0.55, (10, 24, 64)), (1, (18, 38, 88))], 6)
        far = Lay(W, yG)
        for x, w, top in ((0, 44, 150), (196, 40, 110), (300, 60, 80), (150, 30, 250), (240, 34, 300)):
            far.rect(x, top, x + w, yG, (12, 24, 58)); far.rect(x, top, x + w, top, (22, 40, 84))
            for wy in range(top + 6, yG, 7):
                for wx in range(x + 3, x + w - 3, 5):
                    if r.random() < 0.12: far.rect(wx, wy, wx + 1, wy, (60, 100, 170))
        d['far'] = far.done()
        tw = Lay(W, yG)
        x0, x1, top = 64, 214, 60
        base = np.array((16, 30, 66))
        tw.rect(x0, top, x1, yG, base)
        for k, px in enumerate(range(x0, x1, 15)): tw.rect(px, top, px + 2, yG, base * 1.45 if k % 2 == 0 else base * 0.7)
        for wy in range(top + 70, yG - 80, 9):
            tw.rect(x0 + 3, wy + 6, x1 - 3, wy + 7, base * 0.6)
            for wx in range(x0 + 4, x1 - 8, 5):
                if r.random() < 0.16: tw.rect(wx, wy + 1, wx + 3, wy + 3, (120, 170, 235), glow=(40, 80, 140))
                else: tw.rect(wx, wy + 1, wx + 3, wy + 3, base * 0.55)
        tw.rect(x0 - 6, top - 4, x1 + 6, top + 60, (12, 24, 54)); tw.rect(x0 - 6, top - 4, x1 + 6, top - 4, (40, 70, 130))
        tw.rect(x0 + 20, top - 26, x1 - 20, top - 4, (14, 26, 58)); tw.rect(x0 + 20, top - 26, x1 - 20, top - 26, (40, 70, 130))
        tw.rect(x0 + 72, top - 80, x0 + 74, top - 26, (30, 50, 90))
        cx, cy = x0 + 26, top + 26
        hexp = [(cx + 15 * math.cos(a), cy + 15 * math.sin(a)) for a in np.linspace(0, 2 * np.pi, 7)[:-1] + np.pi / 6]
        tw.poly(hexp, (8, 20, 48)); tw.line(hexp + [hexp[0]], (130, 225, 255), glow=(60, 160, 220), width=2)
        tw.ellipse(cx - 6, cy - 6, cx + 6, cy + 6, None, outline=(130, 225, 255), glow=(60, 160, 220))
        tw.rect(cx + 22, cy - 1, cx + 30, cy + 1, (130, 225, 255), glow=(60, 160, 220))
        text(tw, '911', cx + 36, cy - 10, (180, 238, 255), glow=(70, 170, 230), sc=3)
        tw.rect(cx + 100, cy - 1, cx + 108, cy + 1, (130, 225, 255), glow=(60, 160, 220))
        alien(tw, x0 + 10, top + 46, 22, (90, 160, 230), glow=(30, 80, 140), seed=21, sz=3)
        d['tower'] = tw.done()
        tw2 = Lay(W, yG)
        tw2.rect(246, 190, 340, yG, (12, 24, 58))
        tw2.rect(246, 190, 247, yG, (120, 220, 255), glow=(40, 140, 200))
        for wy in range(200, yG - 60, 10):
            tw2.rect(252, wy, 334, wy + 5, (18, 34, 74))
            for wx in range(254, 332, 8):
                if r.random() < 0.28: tw2.rect(wx, wy + 1, wx + 5, wy + 3, (90, 150, 220), glow=(30, 60, 110))
        d['tower2'] = tw2.done()
        br = Lay(W, yG)
        ya, yb = 418, 372
        Y = lambda x: ya + (yb - ya) * x / W
        for px in (40, 196, 330):
            br.rect(px, Y(px) + 18, px + 14, yG, (10, 18, 40)); br.rect(px, Y(px) + 18, px + 2, yG, (26, 44, 80))
            br.rect(px - 8, Y(px) + 18, px + 22, Y(px) + 24, (14, 24, 50))
            for yy in range(int(Y(px) + 40), yG, 26): br.rect(px + 4, yy, px + 10, yy + 1, (20, 34, 66))
        br.poly([(-2, Y(-2)), (W + 2, Y(W + 2)), (W + 2, Y(W + 2) + 18), (-2, Y(-2) + 18)], (12, 22, 48))
        for x in range(0, W, 10): br.line([(x, Y(x) + 8), (x + 10, Y(x + 10) + 17)], (16, 28, 58))
        br.line([(-2, Y(-2) + 8), (W + 2, Y(W + 2) + 8)], (20, 34, 66))
        br.line([(-2, Y(-2) + 18), (W + 2, Y(W + 2) + 18)], (6, 10, 24))
        br.poly([(-2, Y(-2) - 8), (W + 2, Y(W + 2) - 8), (W + 2, Y(W + 2)), (-2, Y(-2))], (22, 38, 74))
        br.line([(-2, Y(-2) - 8), (W + 2, Y(W + 2) - 8)], (60, 96, 150))
        for x in range(4, W, 16): br.rect(x, Y(x) - 3, x + 5, Y(x) - 2, (130, 230, 255), glow=(60, 170, 210))
        gx, gy = 196, int(Y(196)) - 34
        br.line([(gx, gy + 30), (gx, gy + 34)], (20, 30, 50), width=2); br.line([(gx + 60, gy + 24), (gx + 60, gy + 32)], (20, 30, 50), width=2)
        br.rect(gx + 8, gy + 8, gx + 86, gy + 24, (8, 22, 16)); br.rect(gx + 8, gy + 8, gx + 86, gy + 8, (180, 255, 70), glow=(110, 220, 40))
        br.rect(gx + 8, gy + 24, gx + 86, gy + 24, (180, 255, 70), glow=(110, 220, 40))
        alien(br, gx + 28, gy + 11, 6, (200, 255, 100), glow=(130, 230, 50), seed=12, sz=5)
        alien(br, gx + 28, gy + 19, 12, (150, 230, 80), glow=(80, 160, 30), seed=13, sz=2)
        br.ellipse(gx - 16, gy - 2, gx + 18, gy + 32, (14, 40, 18), glow=(30, 70, 20))
        br.ellipse(gx - 16, gy - 2, gx + 18, gy + 32, None, outline=(190, 255, 80), glow=(130, 230, 50))
        br.ellipse(gx - 8, gy + 6, gx + 10, gy + 24, None, outline=(190, 255, 80), glow=(130, 230, 50))
        br.rect(gx - 1, gy + 10, gx + 2, gy + 20, (210, 255, 110), glow=(140, 240, 60))
        d['bridge'] = br.done()
        st = Lay(W, yG)
        st.rect(0, yG - 52, W, yG, (10, 18, 40)); st.rect(0, yG - 52, W, yG - 52, (24, 40, 76))
        for sx0, sw in ((6, 92), (110, 100), (226, 120)):
            st.rect(sx0, yG - 44, sx0 + sw, yG - 2, (6, 12, 28))
            n = 4
            for k in range(n):
                wx = sx0 + 4 + k * (sw - 8) // n
                c = np.array([(130, 255, 235), (236, 248, 255), (100, 200, 255)][(k + sx0) % 3])
                st.rect(wx, yG - 38, wx + (sw - 8) // n - 4, yG - 20, c * 0.78, glow=c * 0.45)
                st.rect(wx + 2, yG - 32, wx + 5, yG - 20, (16, 36, 56))
                st.rect(wx, yG - 26, wx + (sw - 8) // n - 4, yG - 26, c * 0.5)
            st.rect(sx0, yG - 50, sx0 + sw, yG - 46, (30, 58, 96))
            alien(st, sx0 + 6, yG - 49, 5, (200, 240, 255), glow=(80, 140, 200), seed=sx0, sz=3)
        st.rect(98, yG - 34, 108, yG - 2, (160, 230, 255), glow=(60, 130, 180)); st.rect(100, yG - 30, 106, yG - 22, (60, 100, 160))
        st.rect(214, yG - 90, 215, yG - 2, (30, 50, 80)); st.rect(206, yG - 92, 222, yG - 90, (30, 50, 80))
        st.rect(208, yG - 90, 213, yG - 88, (255, 210, 140), glow=(255, 170, 80))
        d['street'] = st.done()
        d['rain'] = Rain(520, 44, speed=(360, 470), length=(8, 16), slant=0.1, col=(150, 190, 255), alpha=(0.16, 0.45))
        d['car'] = C.side(150)
        bolt = Lay(W, 360)
        pts = [(250, 0)]; x, y = 250.0, 0.0
        while y < 300:
            y += r.uniform(12, 28); x += r.uniform(-18, 18); pts.append((x, y))
            if r.random() < 0.3:
                bolt.line([(x, y), (x + r.uniform(-40, 40), y + r.uniform(20, 50))], (200, 220, 255), glow=(150, 180, 255))
        bolt.line(pts, (240, 245, 255), width=2, glow=(220, 230, 255))
        d['bolt'] = bolt.done()
        return d

    def frame(self, t):
        d = self.build(); yG = self.yG
        F = d['sky'].astype(float).copy(); E = np.zeros_like(F)
        fl = clamp(max(0.0, 1 - abs(t - 1.25) / 0.12) + 0.7 * max(0.0, 1 - abs(t - 1.5) / 0.08) + max(0.0, 1 - abs(t - 3.55) / 0.12))
        F[:yG] += np.array((80, 110, 180)) * fl * 0.9
        if fl > 0.3: blit(F, E, d['bolt'], 0, 0, alpha=fl)
        blit(F, E, d['far'], 0, 0)
        blit(F, E, d['tower2'], 0, 0)
        blit(F, E, d['tower'], 0, 0, ek=flick(t, 4, 0.03))
        if int(t * 2) % 2 == 0:
            F[0:3, 136:141] = (255, 40, 40); E[0:3, 136:141] = (255, 20, 20)
        blit(F, E, d['street'], 0, 0)
        cx = -170 + 560 * (t / 5.0)
        put_car(F, E, d['car'], cx, yG, 112 * t, 112, env=(30, 60, 130) if fl < 0.3 else (200, 220, 255),
                env2=(130, 220, 255), streak=-cx * 1.4, gloss=1 + fl)
        blit(F, E, d['bridge'], 0, 0, ek=flick(t, 6, 0.03))
        for k in range(3):
            px = (t * 140 + k * 140) % (W + 60) - 30
            py = 418 + (372 - 418) * px / W - 11
            for o in (0, 8):
                xx = int(px + o)
                if 0 <= xx < W: F[int(py), xx] = (255, 60, 60); E[int(py), xx] = (255, 40, 40)
        reflect(F, E, yG, t, dark=0.5, tint=(4, 10, 28), stretch=0.7, band=0.3)
        d['rain'].draw(F, t, E=E)
        splashes(F, t, yG + 2, H - 2, 24, 4, (150, 190, 255))
        F += fl * 30
        return F, E


# ======================================================================= S5 rear chase -> title
class S5:
    HZ, f, hc = 286, 330.0, 1.25

    @lru_cache(None)
    def build(self):
        r = np.random.default_rng(5)
        d = {}
        d['sky'] = grad(H, W, [(0, (6, 3, 22)), (0.36, (28, 10, 48)), (0.446, (86, 30, 80)), (0.4475, (12, 8, 22)), (1, (8, 6, 16))], 6)
        sk = Lay(W, self.HZ + 1)
        x = 0
        while x < W:
            bw = int(r.uniform(6, 22)); top = int(self.HZ - r.uniform(14, 90) * (1 - abs(x - 180) / 260))
            sk.rect(x, top, x + bw, self.HZ, (24, 10, 42)); sk.rect(x, top, x + bw, top, (40, 18, 64))
            for wy in range(top + 3, self.HZ - 2, 3):
                for wx in range(x + 1, x + bw - 1, 3):
                    if r.random() < 0.14:
                        c = np.array([(255, 120, 200), (255, 190, 100)][int(r.random() < 0.6)])
                        sk.px(wx, wy, c * 0.6, glow=c * 0.35)
            x += bw
        d['skyline'] = sk.done()
        b = []
        z = 4.0
        while z < 420:
            dep = r.uniform(10, 24)
            for sd in (-1, 1):
                b.append((sd, z + r.uniform(0, 3), z + dep, r.uniform(12, 34),
                          np.array([(28, 14, 44), (20, 16, 46), (34, 14, 36)][int(r.integers(0, 3))]),
                          np.array([(255, 50, 130), (90, 220, 255), (255, 190, 70)][int(r.integers(0, 3))]),
                          int(r.integers(0, 1 << 30))))
            z += dep + r.uniform(1, 4)
        d['blds'] = b
        d['rain'] = Rain(380, 55, speed=(320, 440), length=(7, 14), slant=0.05, col=(190, 170, 240), alpha=(0.16, 0.42))
        tl = Lay(W, 140)
        text(tl, '911', 180 - text_w('911', 12, 1) // 2, 6, (255, 70, 80), glow=(255, 30, 50), sc=12, gap=1)
        text(tl, 'CARRERA 4S', 180 - text_w('CARRERA 4S', 3) // 2, 100, (255, 255, 255), glow=(180, 180, 210), sc=3)
        text(tl, '2017', 180 - text_w('2017', 2) // 2, 126, (255, 150, 160), glow=(200, 70, 90), sc=2)
        d['title'] = tl.done()
        return d

    def P(self, X, Y, Z): return 180 + self.f * X / Z, self.HZ + self.f * (self.hc - Y) / Z

    def world(self, lay, cam, mirror, t):
        s = -1 if mirror else 1
        P = lambda X, Y, Z: self.P(X, s * Y, Z)
        d = self.build()
        items = []
        for (sd, z0, z1, hgt, col, sc, seed) in d['blds']:
            a0, a1 = z0 - cam, z1 - cam
            if a1 < 0.6 or a0 > 170: continue
            items.append((max(a0, 0.6), 'b', sd, max(a0, 0.6), a1, hgt, col, sc, seed))
        base = math.floor(cam / 14) * 14
        for k in range(0, 13):
            zz = base + k * 14 + 7 - cam
            if zz >= 2.5:
                for sd in (-1, 1): items.append((zz, 'l', sd, zz))
        items.sort(key=lambda it: -it[0])
        X = 6.5
        for it in items:
            if it[1] == 'b':
                _, _, sd, a0, a1, hgt, col, sc, seed = it
                fog = clamp(a0 / 130)
                cc = col * (1 - fog) + np.array((40, 16, 50)) * fog
                dim = 0.55 if mirror else 1
                lay.poly([P(sd * X, 0, a0), P(sd * X, 0, a1), P(sd * X, hgt, a1), P(sd * X, hgt, a0)], cc * dim)
                lay.line([P(sd * X, hgt, a0), P(sd * X, hgt, a1)], cc * 1.6 * dim)
                rr = np.random.default_rng(seed)
                nz = max(1, int((a1 - a0) / 2.2))
                for j in range(int(hgt / 3.2)):
                    lay.line([P(sd * X, 2.8 + j * 3.2, a0), P(sd * X, 2.8 + j * 3.2, a1)], cc * 0.7 * dim)
                    for i in range(nz):
                        if rr.random() < 0.3:
                            za, zb = a0 + (i + 0.25) * (a1 - a0) / nz, a0 + (i + 0.75) * (a1 - a0) / nz
                            ya, yb = 1.4 + j * 3.2, 2.5 + j * 3.2
                            wc = np.array((255, 196, 120)) * (0.35 + 0.45 * rr.random()) * (1 - fog * 0.7)
                            lay.poly([P(sd * X, ya, za), P(sd * X, ya, zb), P(sd * X, yb, zb), P(sd * X, yb, za)],
                                     wc * (0.5 if mirror else 1), glow=wc * (0.35 if not mirror else 0.2))
                za = a0 + 1.2
                if za < a1 and hgt > 14:
                    gk = (1 - fog) * dim * 0.9 * flick(t, seed % 97, 0.03) + 0.0
                    q = [P(sd * (X - 0.1), 4, za), P(sd * (X - 1.5), 4, za), P(sd * (X - 1.5), 12, za), P(sd * (X - 0.1), 12, za)]
                    lay.poly(q, sc * gk * 0.85, glow=sc * gk)
                    if not mirror and za < 40:
                        for g in range(5):
                            yg = 5 + g * 1.4
                            lay.poly([P(sd * (X - 0.45), yg, za), P(sd * (X - 1.15), yg, za), P(sd * (X - 1.15), yg + 0.7, za),
                                      P(sd * (X - 0.45), yg + 0.7, za)], sc * 0.35 * gk)
            else:
                _, _, sd, zz = it
                fog = clamp(zz / 150)
                p0, p1, p2 = P(sd * 6.0, 0, zz), P(sd * 6.0, 7.5, zz), P(sd * 4.2, 7.6, zz)
                wpx = max(1, int(0.25 * self.f / zz))
                pc = np.array((30, 24, 44)) * (1 - fog * 0.5)
                lay.line([p0, p1], pc, width=wpx); lay.line([p1, p2], pc, width=wpx)
                lr = max(1, 0.35 * self.f / zz)
                c = np.array((255, 190, 110)) * (1 - fog * 0.6) * (0.6 if mirror else 1)
                lay.ellipse(p2[0] - lr, p2[1] - lr * 0.6, p2[0] + lr, p2[1] + lr * 0.6, c, glow=c * 1.1)

    def frame(self, t):
        d = self.build(); HZ = self.HZ
        F = d['sky'].astype(float).copy(); E = np.zeros_like(F)
        vcam, tb = 26.0, 2.6
        cam = vcam * t if t < tb else vcam * tb + vcam * (1 - math.exp(-(t - tb) * 1.6)) / 1.6
        carz = 3.6 if t < tb else 3.6 + (vcam * (t - tb) + 9 * (t - tb) ** 2) - (cam - vcam * tb)
        carz = min(carz, 300)
        blit(F, E, d['skyline'], 0, 0)
        m = Lay(W, H); self.world(m, cam, True, t); M = m.done()
        rows = np.arange(H)
        wob = (np.sin(rows * 0.9 + t * 7) * (rows > HZ) * 1.2).astype(int)
        cols = np.clip(np.arange(W)[None, :] + wob[:, None], 0, W - 1)
        Ma = M['a'][rows[:, None], cols][..., None]
        F = F * (1 - Ma) + M['rgb'][rows[:, None], cols] * Ma; E = E * (1 - Ma) + M['e'][rows[:, None], cols] * Ma * 0.7
        road = Lay(W, H)
        road.poly([self.P(-5.2, 0, 0.9), self.P(5.2, 0, 0.9), self.P(5.2, 0, 400), self.P(-5.2, 0, 400)], (10, 8, 20, 120))
        dash0 = math.floor(cam / 8) * 8
        for k in range(30):
            z0 = dash0 + k * 8 - cam
            if z0 < 1: continue
            for lx in (-1.75, 1.75):
                road.poly([self.P(lx - 0.07, 0, z0), self.P(lx + 0.07, 0, z0), self.P(lx + 0.07, 0, z0 + 3.5),
                           self.P(lx - 0.07, 0, z0 + 3.5)], (140, 130, 170, 160))
        for ex in (-5.2, 5.2): road.line([self.P(ex, 0, 1.5), self.P(ex, 0, 400)], (90, 80, 120, 180))
        blit(F, E, road.done(), 0, 0, add_e=False)
        w_ = Lay(W, H); self.world(w_, cam, False, t); blit(F, E, w_.done(), 0, 0)
        cw = 1.85 * self.f / carz
        if cw >= 3:
            c = C.rear(cw)
            brake = clamp(1 - abs(t - 2.45) / 0.25)
            L = C.rear_frame(c, env=(120, 50, 140), brake=brake, glow=1.2)
            bx, by = self.P(0, 0, carz)
            bob = int(round(math.sin(t * 31) * 0.5)) if carz < 8 else 0
            x0, y0 = bx - c['w'] / 2, by - c['gy'] - 1 + bob
            Rf = dict(rgb=L['rgb'][::-1] * 0.42, a=L['a'][::-1] * 0.8, e=L['e'][::-1] * 0.6)
            blit(F, E, Rf, x0 + wob[min(H - 1, int(by) + 4)], by)
            sk = max(4, int(cw * 0.9))
            for lx in (-0.7, 0.7):
                sx = int(bx + lx * self.f / carz)
                if 0 <= sx < W:
                    for k in range(sk):
                        yy = int(by + 2 + k)
                        if yy < H:
                            kk = (1 - k / sk) ** 1.5
                            E[yy, max(sx - 1, 0):sx + 2] += np.array((255, 30, 40)) * kk * 0.7
                            F[yy, max(sx - 1, 0):sx + 2] += np.array((120, 10, 20)) * kk
            sh = Lay(W, H)
            sh.ellipse(bx - cw * 0.55, by - cw * 0.03, bx + cw * 0.55, by + cw * 0.05, (0, 0, 0, 140))
            blit(F, E, sh.done(), 0, 0, add_e=False)
            blit(F, E, L, x0, y0)
        d['rain'].draw(F, t, E=E)
        splashes(F, t, HZ + 40, H - 2, 24, 5, (180, 150, 220))
        a = smooth(4.3, 4.8, t)
        if a > 0:
            band = (0.66 * a * np.exp(-((np.arange(H) - 150) / 70.0) ** 2))[:, None, None]
            F *= 1 - band; E *= 1 - band
            k = a * (flick(t, 77, 0.12) if t < 5.3 else 1.0)
            blit(F, E, d['title'], 0, 80, alpha=a, ek=k * 1.3)
        return F, E


SCENES = [S1(), S2(), S3(), S4(), S5()]
_yy, _xx = np.mgrid[0:H, 0:W]
VIG = (1 - 0.35 * (((_xx - W / 2) / (W * 0.75)) ** 2 + ((_yy - H / 2) / (H * 0.75)) ** 2))[..., None]


def raw(t):
    i = max(k for k in range(5) if CUTS[k] <= t)
    F, E = SCENES[i].frame(t - CUTS[i])
    F = bloom(F, E, 1.0) * VIG
    if t > DUR - 0.6: F *= clamp((DUR - t) / 0.6)
    if t < 0.35: F *= clamp(t / 0.35)
    return finish(F, 5)


def frame_bytes(n): return raw(n / FPS).tobytes()


if __name__ == '__main__':
    mode = sys.argv[1]
    if mode == 'still':
        for ts in sys.argv[3:]:
            Image.fromarray(raw(float(ts))).resize((W * SC, H * SC), Image.NEAREST).save(f'{sys.argv[2]}/f_{ts}.png')
    elif mode == 'video':
        out = sys.argv[2]
        t0, t1 = (float(sys.argv[3]), float(sys.argv[4])) if len(sys.argv) > 4 else (0.0, DUR)
        import audio
        audio.build('mix.wav', t0, t1)
        n0, n1 = int(t0 * FPS), int(t1 * FPS)
        ff = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}',
                               '-r', str(FPS), '-i', '-', '-i', 'mix.wav', '-vf', f'scale={W * SC}:{H * SC}:flags=neighbor',
                               '-c:v', 'libx264', '-preset', 'slow', '-crf', '16', '-pix_fmt', 'yuv420p',
                               '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', '-shortest', out], stdin=subprocess.PIPE)
        with Pool(4) as pool:
            for i, b in enumerate(pool.imap(frame_bytes, range(n0, n1), chunksize=4)):
                ff.stdin.write(b)
                if i % 150 == 0: print(f'{i}/{n1 - n0}', flush=True)
        ff.stdin.close(); ff.wait()
        print('done', ff.returncode)
        raise SystemExit(ff.returncode)
