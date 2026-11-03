"""Original 10 s pixel-art mood piece: rainy bus stop -> dusk at the beach.
Usage: python render.py video OUT.mp4 | python render.py still OUTDIR t1 t2 ..."""
import math, subprocess, sys, wave
from pathlib import Path
import numpy as np
from PIL import Image
import sprites as SPR

W = H = 135; S = 8; FPS = 30; DUR = 10.0; CUT = 5.0; SR = 44100
BAYER = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) / 16.0
YS, XS = np.mgrid[0:H, 0:W]


def hx(h): return np.array([int(h[i:i + 2], 16) for i in (1, 3, 5)], np.float32)
def col(c): return hx(c) if isinstance(c, str) else np.asarray(c, np.float32)


class C:
    def __init__(s, layer=False):
        s.a = np.zeros((H, W, 3), np.float32); s.m = np.zeros((H, W), bool) if layer else None
    def rect(s, x, y, w, h, c):
        x0, y0, x1, y1 = max(0, int(x)), max(0, int(y)), min(W, int(x + w)), min(H, int(y + h))
        if x1 > x0 and y1 > y0:
            s.a[y0:y1, x0:x1] = col(c)
            if s.m is not None: s.m[y0:y1, x0:x1] = True
    def px(s, x, y, c): s.rect(round(x), round(y), 1, 1, c)
    def line(s, x0, y0, x1, y1, c):
        n = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
        for i in range(n + 1):
            t = i / n; s.px(x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, c)
    def grad(s, y0, y1, cols, x0=0, x1=W):
        cs = np.stack([col(c) for c in cols]); n = len(cols) - 1
        ys, xs = YS[y0:y1, x0:x1], XS[y0:y1, x0:x1]
        t = (ys - y0) / max(1, y1 - y0 - 1) * n + BAYER[ys % 4, xs % 4] - .5
        s.a[y0:y1, x0:x1] = cs[np.clip(np.round(t), 0, n).astype(int)]
    def glow(s, cx, cy, r, c, k=.55, ry=None):
        ry = ry or r
        d = np.sqrt(((XS - cx) / r) ** 2 + ((YS - cy) / ry) ** 2)
        lv = np.clip(np.floor((1 - d) * 3 + BAYER[YS % 4, XS % 4]), 0, 3) / 3 * k
        s.a[:] = s.a * (1 - lv[..., None]) + col(c) * lv[..., None]
    def spr(s, x, y, rows, pal, flip=False):
        for j, r in enumerate(rows):
            if flip: r = r[::-1]
            for i, ch in enumerate(r):
                if ch in pal: s.px(x + i, y + j, pal[ch])


def light(L, mul, rims, dark=1.0):
    """Tint a character layer, add 1px rim lights: rims = [(side, colour, strength)]."""
    a = L.a * np.array(mul, np.float32) * dark; m = L.m
    for side, c, k in rims:
        edge = m & ~np.roll(m, side, axis=1)
        a[edge] = a[edge] * (1 - k) + col(c) * k
    return a


def comp(bg, L, a):
    bg.a[L.m] = a[L.m]


def P(**kw): return {k: hx(v) for k, v in kw.items()}


rng = np.random.default_rng

# ================= scene 1: waiting out the rain in the bus shelter =================
DADP = P(H='#23222a', h='#46424f', S='#d9a383', s='#b07a62', d='#8e5a4a', g='#5a4038', l='#e6c0a4', e='#2a2028',
         B='#5a423a', b='#43302b', m='#4a2c2a', F='#9a7a5c', f='#6c5240', J='#5b705f', j='#43544a', K='#7f9580',
         T='#a8cdd0', t='#7aa4aa', C='#ece4d4', c='#b8ae9e', L='#a4523c', P='#3e4b68', p='#2c3550',
         Q='#56648a', X='#24242c', x='#4a4a56')
KIDP = P(y='#efc24a', Y='#c49434', Z='#9a7028', H='#6a442e', S='#f0b898', s='#c88a70', e='#2a2028',
         r='#e88a80', P='#3a4566', p='#2a3350', R='#c8463e', q='#e8706a')
R1 = rng(5)
BOKEH = [(R1.random() * W, 24 + R1.random() * 50, R1.choice(['#d8b36a', '#7fb8c4', '#e07a6a', '#a6d6cc']),
          R1.random()) for _ in range(26)]
DROPS = np.c_[R1.random(70) * W, R1.random(70) * H, R1.random(70)]
SEAT, FLOOR = 92, 106
DBX, DBY = 26, SEAT - 17          # dad body origin
KBX, KBY = 56, SEAT - 8           # kid body origin


def swap(rows, a, b, row=None):
    return [r.replace(a, b) if row is None or j == row else r for j, r in enumerate(rows)]


def scene1(t):
    c = C()
    # night street seen through the shelter glass
    c.grad(0, 80, ['#0a1820', '#0e222c', '#123038', '#1a3e48'])
    for i, (bx, by, cl, z) in enumerate(BOKEH):   # out-of-focus lights
        r = 2 + z * 3; tw = .5 + .5 * math.sin(t * (1 + z) + i)
        c.glow(bx, by, r, cl, .35 + .3 * tw)
    c.grad(80, FLOOR, ['#1a3a42', '#163238', '#122a30', '#10262c'])
    if 2.6 < t < 4.9:   # car headlights sweeping past behind the glass
        cx = -30 + (t - 2.6) / 2.3 * (W + 60)
        c.glow(cx, 80, 30, '#fff0c0', .55, 8); c.rect(cx - 22, 78, 26, 7, '#0e1a20')
        c.rect(cx + 2, 80, 3, 2, '#fff3c8'); c.rect(cx - 22, 80, 2, 2, '#e04a4a')
    # glass panes: streaks of water running down
    for k in range(60):
        x_ = (k * 37) % W; y_ = (k * 53 + t * (8 + k % 5) * 3) % 90 + 4
        c.line(x_, y_, x_, y_ + 3 + k % 4, '#2e5662')
        c.px(x_, y_ + 4 + k % 4, '#5d8f98')
    c.a[4:100] = c.a[4:100] * .82 + col('#2a5560') * .18          # glass tint
    for gx in (0, 44, 88, 132): c.rect(gx, 4, 3, 96, '#16262c'); c.rect(gx + 1, 4, 1, 96, '#34525a')
    c.rect(0, 46, W, 2, '#16262c')
    # ad panel (right)
    c.rect(94, 14, 38, 72, '#16262c'); c.rect(96, 16, 34, 68, '#bfe6dc'); c.rect(98, 18, 30, 64, '#d8f2e8')
    c.rect(100, 22, 26, 26, '#f09a72'); c.glow(113, 35, 9, '#ffe2a8', .9)
    c.rect(100, 54, 22, 3, '#2f5f6a'); c.rect(100, 60, 16, 2, '#5d8f98'); c.rect(100, 64, 18, 2, '#5d8f98')
    c.rect(100, 72, 8, 6, '#2f5f6a')
    c.glow(112, 50, 46, '#8fd8cc', .32, 60)
    # roof + drips
    c.rect(0, 0, W, 5, '#0e1a1f'); c.rect(0, 4, W, 1, '#4a6a70')
    # bench
    c.rect(14, SEAT, 72, 4, '#7a5a44'); c.rect(14, SEAT, 72, 1, '#a07a5a'); c.rect(14, SEAT + 4, 72, 1, '#4a3428')
    c.rect(18, SEAT + 5, 3, FLOOR - SEAT - 5, '#1c2a2e'); c.rect(80, SEAT + 5, 3, FLOOR - SEAT - 5, '#1c2a2e')
    c.rect(14, SEAT - 26, 72, 3, '#6a4c3a'); c.rect(14, SEAT - 26, 72, 1, '#90705a')   # backrest
    c.rect(14, SEAT - 16, 72, 3, '#6a4c3a'); c.rect(14, SEAT - 16, 72, 1, '#90705a')
    # floor
    c.grad(FLOOR, H, ['#26404a', '#1e353e', '#182c33', '#13242a'])
    c.rect(0, FLOOR, W, 1, '#3c5a62')
    for k in range(0, W, 16): c.line(k, FLOOR + 1, k - 12, H, '#1a2e35')
    # light from the street lamp (left) and ad (right)
    c.glow(0, 30, 70, '#f2c46d', .28, 90)
    # ---------- characters ----------
    L = C(layer=True)
    bre = int((t % 2.4) > 1.2)
    look = t > 1.9                       # dad turns to look at the kid
    lean = t > 2.9                       # kid leans on dad's arm
    blink = (t % 2.6) < .12 or 1.85 < t < 1.95
    dh = list(SPR.DAD_HEAD)
    if blink: dh = swap(dh, 'glegglelg', 'gllggllgg', 10)
    elif look: dh = swap(dh, 'glegglelg', 'gllegglle', 10)
    if lean: dh = swap(dh, 'BBBSmmmSBBB', 'BBmSSSSSmBB', 15)   # smile
    L.spr(DBX, DBY + 16, SPR.DAD_BODY[16:], DADP)
    L.spr(DBX, DBY + bre, SPR.DAD_BODY[:16], DADP)
    L.spr(DBX + SPR.DAD_HEAD_X + look, DBY + SPR.DAD_HEAD_Y + bre + (lean and look), dh, DADP)
    kh = list(SPR.KID_HEAD)
    if lean: kh = swap(kh, 'e', 's'); kh = swap(kh, 'SSSSSSSS', 'SSSSSSSS')
    elif (t % 3.1) < .12: kh = swap(kh, 'e', 's')
    swing = int(t * (4 if not lean else 1.5)) % 2
    kb = int((t % 2.0) > 1.0)
    L.spr(KBX, KBY + 10, SPR.KID_LEGS[swing], KIDP)
    L.spr(KBX - lean, KBY + kb * (not lean), SPR.KID_BODY, KIDP)
    L.spr(KBX + SPR.KID_HEAD_X - 3 * lean, KBY + SPR.KID_HEAD_Y + 2 * lean, kh, KIDP)
    a = light(L, (.84, .92, .98), [(1, '#ffcf86', .45), (-1, '#9fe4d6', .35)])
    c.glow(DBX + 15, FLOOR + 1, 16, '#0a161a', .5, 2.5)
    comp(c, L, a)
    # steam from the cup
    for i in range(5):
        ph = (t * .6 + i / 5) % 1
        sx = DBX + 15 + math.sin(ph * 6 + i) * 2; sy = DBY + 11 + bre - ph * 18
        if ph < .85: c.px(sx, sy, col('#e8eef0') * (1 - ph) * .6 + c.a[int(sy), int(sx)] * (1 - (1 - ph) * .6))
    # rain in the foreground + drips from the roof
    for rx, ry, z in DROPS:
        y = (ry + t * (150 + 90 * z)) % (H + 20) - 10; x_ = (rx - t * 18 * (1 + z)) % W
        if z > .62 and not (DBX - 4 < x_ < KBX + 18 and y < FLOOR): c.line(x_, y, x_ - 1, y + 3 + int(z * 3), '#5f8a94' if z < .8 else '#8fb8c0')
    for i in range(9):
        ph = (t * .9 + i * .37) % 1; dx_ = 7 + i * 15
        c.px(dx_, 5, '#8fb8c0')
        if ph > .6: c.px(dx_, 5 + (ph - .6) ** 2 * 300, '#8fb8c0')
    return c


# ================= scene 2: watching the sunset from the beach =================
DADBP = P(H='#2a2430', h='#4a3c4c', S='#d89a7c', s='#a8685a', g='#2a2428', W='#efe5d2', w='#c9b8a4',
          v='#9a8a80', R='#c24a54', r='#8e3540')
KIDBP = P(K='#7a4a2c', k='#a8703e', T='#e0604c', t='#a8483e', U='#7e3634', P='#3f5f8a', p='#2e4568',
          S='#f0b494', s='#c07c66')
R2 = rng(11)
CLOUDS = sorted([(R2.random() * (W + 120) - 60, int(R2.integers(6, 56)), int(R2.integers(10, 34)),
                  int(R2.integers(3, 6)), R2.random()) for _ in range(16)], key=lambda q: q[1])
HZ, SUNX = 72, 96
DX2, DFEET2 = 28, 126
KX2, KFEET2 = 58, 127


def disc(c, cx, cy, r, colr, ymax):
    for y in range(max(0, int(cy - r)), min(H, int(cy + r) + 1, ymax)):
        hw = math.sqrt(max(0, r * r - (y - cy) ** 2)); c.rect(round(cx - hw), y, round(2 * hw), 1, colr)


def cloud(c, x, y, w, h, z, t):
    x = (x + t * (1.5 + 2 * z)) % (W + 120) - 60
    hl, mid, sh = ('#f8cfae', '#e09a90', '#9a6680') if y > 36 else ('#eab0a6', '#b07c92', '#635a80')
    bl = [(x + k, y - h * .5 * abs(math.sin(k * .3 + z * 9)), h * (.6 + .5 * abs(math.sin(k * .21 + z * 5))))
          for k in range(0, w, 4)]
    for bx, by, r in bl: disc(c, bx, by + 1, r, sh, y + h + 1)
    for bx, by, r in bl: disc(c, bx - .5, by - 1, r - .5, mid, y + h - 1)
    for bx, by, r in bl: disc(c, bx - 1, by - 2.5, r - 1.8, hl, y + h - 3)


def scene2(t):
    c = C()
    c.grad(0, HZ, ['#2b3f5c', '#3e4f6e', '#6a5d7e', '#a96f85', '#df8f86', '#f2b38d', '#f8d39e'])
    c.glow(SUNX, HZ, 44, '#ffe2a8', .5, 18)
    for q in CLOUDS: cloud(c, *q, t)
    for j in range(8):
        hw = int(math.sqrt(max(0, 64 - (8 - j) ** 2))); c.rect(SUNX - hw, HZ - 8 + j, hw * 2, 1, '#fff2c8')
    for x in range(52):
        hh = int(4 + 2 * math.sin(x * .12) + math.sin(x * .3)); c.rect(x, HZ - hh, 1, hh, '#5e4a6c')
    # sea + sun glitter
    c.grad(HZ, 100, ['#6a6588', '#4f5578', '#3a4668', '#2c3a5a'])
    for j in range(0, 28, 2):
        y = HZ + j; sp_ = 3 + j * .5
        for k in range(3):
            ph = math.sin(t * 2.5 + j * 1.7 + k * 2.1)
            if ph > .2: c.rect(SUNX + math.sin(j * 3.1 + k * 7) * sp_, y, 2 + int(ph * 3), 1, '#f6c79a')
    for i in range(14):
        y = HZ + 3 + (i * 7) % 24; x_ = (i * 41 + t * (5 + i % 3)) % (W + 20) - 10
        c.rect(x_, y, 3 + i % 4, 1, '#7a7898')
    # wet sand mirrors the sky
    c.grad(100, H, ['#8a6a7e', '#a07a80', '#7a5e70', '#5e4a60', '#4a3c52'])
    for y in range(102, H, 3):
        k = (1 - (y - 102) / 34) * .45; w_ = 3 + (y - 102) * .3
        if k > 0:
            x_ = SUNX - w_ / 2 + 2 * math.sin(y * .8 + t * 3)
            c.rect(x_, y, w_, 1, col('#f6c79a') * k + c.a[y, int(x_)] * (1 - k))
    # waves washing in over the feet
    for layer in range(2):
        ph = t * .9 + layer * 1.7
        edge = 104 + 5 * math.sin(ph) + layer * 3
        for x in range(W):
            e = edge + 1.5 * math.sin(x * .15 + ph * 2 + layer) + .8 * math.sin(x * .4 - ph)
            ys = 100 + layer * 2
            c.rect(x, ys, 1, int(e) - ys, '#4a5276' if layer else '#556088')
            c.rect(x, int(e), 1, 1, '#f2e2d6' if (x + int(t * 10)) % 5 else '#c8b8c8')
    # ---------- characters ----------
    L = C(layer=True)
    wind = int(t * 4) % 2
    bre = int((t % 2.6) > 1.3)
    top = DFEET2 - 17 - 20 - 2
    L.spr(DX2, top + 22, SPR.DADB_LEGS, DADBP)
    L.spr(DX2, top + 20, SPR.DADB_HEM[wind], DADBP)
    L.spr(DX2, top + bre, SPR.DADB_BODY, DADBP)
    L.spr(DX2 + 6, top - 12 + bre, SPR.DADB_HEAD, DADBP)
    # dad's right hand reaching down to the kid's hand
    hxp, hyp = DX2 + 24, top + 20 + bre
    L.rect(hxp, hyp, 2, 3, DADBP['S']); L.px(hxp + 1, hyp + 3, DADBP['s'])
    ktop = KFEET2 - 16 - 9
    kbob = int((t % 1.8) > .9)
    L.spr(KX2, ktop + 9, SPR.KIDB_BODY, KIDBP)
    L.spr(KX2, ktop + kbob * 0, SPR.KIDB_HEAD, KIDBP)
    L.spr(KX2 + 1 + wind, ktop, ["kk"], KIDBP)                       # hair tuft in the wind
    L.line(KX2 + 1, ktop + 10, hxp + 1, hyp + 3, KIDBP['S'])        # kid's left arm up to dad
    L.line(KX2, ktop + 10, hxp, hyp + 3, KIDBP['S'])
    L.px(KX2, ktop + 9, KIDBP['T']); L.px(KX2 - 1, ktop + 9, KIDBP['T'])
    if 1.6 < t < 4.4:
        L.spr(KX2 + 11, ktop + 3, SPR.KIDB_ARM_POINT[int(t * 3) % 2], KIDBP)
    else:
        L.spr(KX2 + 11, ktop + 9, SPR.KIDB_ARM_DOWN, KIDBP)
    a = light(L, (.86, .76, .82), [(-1, '#ffd2a0', .7), (1, '#6a5a8a', .2)])
    # reflections in the wet sand
    ys, xs = np.nonzero(L.m)
    for y, x in zip(ys, xs):
        for feet in ((DFEET2,) if x < KX2 - 1 else (KFEET2,)):
            ry = 2 * feet + 1 - y
            if feet < ry < H and ry % 3:
                wx = int(x + math.sin(ry * .9 + t * 5))
                if 0 <= wx < W: c.a[ry, wx] = c.a[ry, wx] * .6 + a[y, x] * .22
    c.glow(DX2 + 13, DFEET2, 12, '#3a2c44', .45, 1.6); c.glow(KX2 + 6, KFEET2, 6, '#3a2c44', .45, 1.3)
    comp(c, L, a)
    for i in range(3):   # gulls
        x_ = (120 - t * 7 + i * 12) % (W + 20) - 10; y_ = 22 + i * 5 + math.sin(t * 1.6 + i) * 2
        fl = int(t * 5 + i) % 2
        for dx_, dy_ in ((0, 0), (-1, -fl), (1, -fl), (-2, fl - 1), (2, fl - 1)): c.px(x_ + dx_, y_ + dy_, '#3a2c44')
    return c


def frame(t):
    if t < CUT - .35: a = scene1(t).a
    elif t > CUT + .35: a = scene2(t - CUT).a
    else:
        f = (t - (CUT - .35)) / .7
        A, B = scene1(t).a, scene2(t - CUT).a
        m = (BAYER[(YS // 2) % 4, (XS // 2) % 4] < f)[..., None]
        a = np.where(m, B, A)
    a = a * max(0, min(1, t / .5, (DUR - t) / .6))
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).resize((W * S, H * S), Image.NEAREST)


# ---------- audio: rain -> waves, soft triangle chiptune ----------
def audio(path):
    n = int(SR * DUR); tt = np.arange(n) / SR; r = rng(3)
    noise = r.standard_normal(n)
    rain = np.convolve(noise, np.ones(3) / 3, 'same') * .05
    patter = (r.random(n) > .9993) * r.standard_normal(n) * .5
    patter = np.convolve(patter, np.exp(-np.arange(200) / 30), 'same') * .12
    env1 = np.clip((CUT + .3 - tt) / .6, 0, 1)
    car = np.convolve(noise, np.ones(40) / 40, 'same') * np.exp(-((tt - 3.7) / .7) ** 2) * .5
    wave_ = np.convolve(noise, np.ones(90) / 90, 'same') * (1.2 + np.sin(tt * 1.3)) * 1.2
    env2 = np.clip((tt - CUT + .3) / .6, 0, 1)
    gull = sum(np.sin(2 * np.pi * (1800 - 600 * ((tt - s) * 4)) * (tt - s)) *
               np.exp(-((tt - s - .12) / .08) ** 2) for s in (6.6, 6.9)) * .02
    tri = lambda f: 2 / np.pi * np.arcsin(np.sin(2 * np.pi * f * tt))
    music = np.zeros(n); beat = .3
    chords = [(220, 261.6, 329.6), (174.6, 220, 261.6), (196, 246.9, 293.7), (164.8, 207.7, 246.9)]
    for i in range(int(DUR / beat)):
        s0 = i * beat; ch = chords[(i // 8) % 4]; f = ch[[0, 1, 2, 1][i % 4]] * 2
        seg = (tt >= s0) & (tt < s0 + beat)
        music[seg] += tri(f)[seg] * np.exp(-(tt[seg] - s0) * 6) * .06
        if i % 8 == 0:
            seg2 = (tt >= s0) & (tt < s0 + beat * 8)
            music[seg2] += tri(ch[0] / 2)[seg2] * .035
    mix = (rain + patter) * env1 + car + wave_ * env2 + gull + music
    mix *= np.clip(np.minimum(tt / .5, (DUR - tt) / .8), 0, 1)
    mix = np.clip(mix / max(1e-6, np.abs(mix).max()) * .8, -1, 1)
    st = (np.c_[mix, mix] * 32767).astype(np.int16)
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(st.tobytes())


if __name__ == '__main__':
    mode = sys.argv[1]
    if mode == 'still':
        out = Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
        for s in sys.argv[3:]: frame(float(s)).save(out / f'f_{s}.png')
    else:
        out = Path(sys.argv[2]); out.parent.mkdir(parents=True, exist_ok=True)
        wav = out.with_suffix('.wav'); audio(wav)
        p = subprocess.Popen(['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
                              '-s', f'{W * S}x{H * S}', '-r', str(FPS), '-i', '-', '-i', str(wav),
                              '-c:v', 'libx264', '-preset', 'medium', '-crf', '16', '-pix_fmt', 'yuv420p',
                              '-c:a', 'aac', '-b:a', '160k', '-shortest', '-movflags', '+faststart', str(out)],
                             stdin=subprocess.PIPE)
        for i in range(int(DUR * FPS)):
            p.stdin.write(frame(i / FPS).tobytes())
        p.stdin.close(); sys.exit(p.wait())
