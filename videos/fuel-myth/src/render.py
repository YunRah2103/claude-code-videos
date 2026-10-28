"""Renders the 'stupidest fuel myth' TikTok explainer, synced to the voiceover."""
import json, math, os, sys, subprocess
from functools import lru_cache
from multiprocessing import Pool
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import pix, sfx

W, H, FPS, S = 1080, 1920, 60, 9
GROUND = 1180
DUR = 18.0
BG = (255, 255, 255)
NAVY = (26, 26, 46)
WORDS = json.load(open('words.json'))

# ------------------------------------------------------------------ easing
def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def prog(t, a, d): return clamp((t - a) / d)
def ob(x):
    c1 = 1.70158; c3 = c1 + 1
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2
def oc(x): return 1 - (1 - x) ** 3
def ic(x): return x ** 3
def io(x): return 4 * x ** 3 if x < .5 else 1 - (-2 * x + 2) ** 3 / 2
def popin(t, t0, d=0.28): return 0.0 if t < t0 else ob(prog(t, t0, d))
def slam(t, t0, d=0.14, k=1.6): return 1 + k * (1 - oc(prog(t, t0, d)))

# ------------------------------------------------------------------ drawing
@lru_cache(None)
def big(name, *args, s=S):
    return pix.up(getattr(pix, name)(*args), s)

@lru_cache(None)
def big_guy(expr, npc, pose):
    return pix.up(pix.guy(expr, npc, pose), S)

def blit(cv, img, cx, y, sx=1.0, sy=1.0, rot=0.0, anchor='bottom'):
    if sx <= 0.01 or sy <= 0.01:
        return
    if sx != 1 or sy != 1:
        img = img.resize((max(1, int(img.width * sx)), max(1, int(img.height * sy))), Image.NEAREST)
    if rot:
        img = img.rotate(rot, resample=Image.NEAREST, expand=True)
    x = cx - img.width / 2
    y = y - img.height if anchor == 'bottom' else y - img.height / 2
    cv.paste(img, (int(round(x)), int(round(y))), img)

def shadow(cv, cx, w, k=1.0):
    if k <= 0: return
    d = ImageDraw.Draw(cv)
    w = w * k
    d.rectangle((cx - w / 2 + S, GROUND - S, cx + w / 2 - S, GROUND + S), fill=(236, 236, 242))
    d.rectangle((cx - w / 2, GROUND - S // 2, cx + w / 2, GROUND + S // 2), fill=(236, 236, 242))

def block(cv, x0, y0, x1, y1, fill, shade, hi):
    if y1 - y0 < 2 * S: return
    d = ImageDraw.Draw(cv)
    d.rectangle((x0, y0, x1, y1), fill=NAVY)
    d.rectangle((x0 + S, y0 + S, x1 - S, y1 - S), fill=fill)
    d.rectangle((x1 - 4 * S, y0 + S, x1 - S, y1 - S), fill=shade)
    if y1 - y0 > 5 * S:
        d.rectangle((x0 + 2 * S, y0 + 2 * S, x0 + 3 * S, min(y1 - 2 * S, y0 + 9 * S)), fill=hi)

def rng_for(seed): return np.random.default_rng(seed)

def sparkles(cv, t, cx, cy, w, h, n=6, seed=1):
    r = rng_for(seed)
    for i in range(n):
        x = cx + r.uniform(-w / 2, w / 2); y = cy + r.uniform(-h / 2, h / 2)
        ph = r.uniform(0, 1); sp = r.uniform(1.2, 2.0)
        v = math.sin(2 * math.pi * (t * sp + ph))
        if v > 0.3:
            blit(cv, big('sparkle', 1 if v > 0.75 else 0, s=7), x, y, anchor='center')

def confetti(cv, t, t0, x, y, n=40, seed=3, spread=1.0):
    dt = t - t0
    if dt < 0 or dt > 2.2: return
    r = rng_for(seed)
    cols = [(255, 77, 109), (255, 210, 63), (61, 127, 214), (60, 200, 90), (255, 138, 61), (160, 100, 255)]
    d = ImageDraw.Draw(cv)
    for i in range(n):
        vx = r.uniform(-650, 650) * spread; vy = r.uniform(-1700, -900)
        px = x + vx * dt; py = y + vy * dt + 0.5 * 2600 * dt * dt
        c = cols[i % len(cols)]
        sz = S if (int((dt * 8 + i)) % 2) else S * 2
        d.rectangle((px, py, px + sz, py + S), fill=c)

def dust(cv, t, t0, x, y, n=10, seed=5, life=0.6, dirx=0):
    dt = t - t0
    if dt < 0 or dt > life: return
    r = rng_for(seed); d = ImageDraw.Draw(cv)
    k = 1 - dt / life
    for i in range(n):
        vx = r.uniform(-500, 500) + dirx; vy = r.uniform(-260, -40)
        px = x + vx * dt; py = y + vy * dt
        s = S * (1 + int(2 * k * r.uniform(0.5, 1.5)))
        d.rectangle((px - s, py - s, px + s, py + s), fill=(205, 205, 214), outline=NAVY, width=3)

def poof(cv, t, t0, x, y, seed=9):
    dt = t - t0
    if dt < 0 or dt > 0.55: return
    r = rng_for(seed); d = ImageDraw.Draw(cv)
    k = dt / 0.55
    for i in range(7):
        a = i / 7 * 2 * math.pi + r.uniform(0, 0.5)
        dist = 40 + 200 * oc(k)
        rad = (70 + r.uniform(0, 40)) * (1 - k) ** 0.7 * (0.6 + 0.6 * oc(min(1, k * 4)))
        cx, cy = x + math.cos(a) * dist, y + math.sin(a) * dist * 0.7
        d.ellipse((cx - rad, cy - rad, cx + rad, cy + rad), fill=(245, 245, 248), outline=NAVY, width=7)

# ------------------------------------------------------------------ character face / talking
WSTART = np.array([w['s'] for w in WORDS]); WEND = np.array([w['e'] for w in WORDS])
def speaking(t):
    i = np.searchsorted(WSTART, t, side='right') - 1
    return i >= 0 and t < WEND[i] - 0.03

def face(t, base):
    if base in ('smile', 'sad') and speaking(t) and int(t * 11) % 2 == 0:
        return 'talk' if base == 'smile' else 'sadtalk'
    if base == 'smile' and (t % 3.3) < 0.11:
        return 'blink'
    return base

TALK_CYCLE = ['talkR', 'down', 'talkL', 'talkB', 'down2', 'talkR', 'shrug', 'talkL']

def auto_pose(t, expr):
    if expr == 'shock': return 'shock'
    if expr == 'sad': return 'sad'
    if speaking(t):
        i = np.searchsorted(WSTART, t, side='right') - 1
        return TALK_CYCLE[(i // 2) % len(TALK_CYCLE)]
    return 'down' if (t * 0.8) % 1 < 0.5 else 'down2'

def anim_pose(p, t):
    if p == 'wave': return 'wave1' if int(t * 6) % 2 else 'wave2'
    if p == 'up': return 'up1' if int(t * 7) % 2 else 'up2'
    if p == 'flail': return 'flail1' if int(t * 10) % 2 else 'flail2'
    return p

def pick_pose(t, expr, sched):
    for a, b, p in sched or ():
        if a <= t < b: return anim_pose(p, t)
    return auto_pose(t, expr)

def idle_bob(t): return -S if (t * 1.1) % 1 < 0.5 else 0

def guy(cv, t, cx, expr='smile', sx=1.0, sy=1.0, lift=0.0, npc=False, scale=1.0, bob=True, poses=None):
    shadow(cv, cx, 260 * sx * scale, 1 - min(1, abs(lift) / 400))
    b = idle_bob(t) if bob and sy == 1 else 0
    pose = pick_pose(t, expr, poses) if sy > 0.9 else 'down'
    blit(cv, big_guy(face(t, expr), npc, pose), cx, GROUND + lift + b, sx * scale, sy * scale)

# ------------------------------------------------------------------ scenes
PX = 760
GOLD = ('#ffd23f', '#1a1a2e', '#e8b923')
GREEN = ('#3cc85a', '#ffffff', '#2a9a45')

def swing(t, t0, amp=12, f=1.2, damp=0.9):
    dt = max(0.0, t - t0)
    return amp * math.sin(2 * math.pi * f * dt) * math.exp(-damp * dt) + 2 * math.sin(t * 2.3)

def gsparkles(cv, t, cx, cy, w, h, n=8, seed=31):
    r = rng_for(seed)
    for i in range(n):
        x = cx + r.uniform(-w / 2, w / 2); y = cy + r.uniform(-h / 2, h / 2)
        v = math.sin(2 * math.pi * (t * r.uniform(1.4, 2.2) + r.uniform(0, 1)))
        if v > 0.2:
            k = 0.6 + 0.6 * v
            blit(cv, big('star', '#7fe3a0', s=8), x, y, k, k, anchor='center')

def pump_at(cv, t, cx, green=False, t_in=None):
    if t_in is not None:
        cx = cx + 760 * (1 - ob(prog(t, t_in, 0.42)))
    shadow(cv, cx, 300)
    blit(cv, big('pump', *(('#3cc85a', '#2a9a45', '#9ff0b0', '#3cc85a') if green else ())), cx, GROUND)
    return cx

def scene_hook(cv, t):
    cx = pump_at(cv, t, PX, t_in=-0.18)
    top = GROUND - 504
    k = popin(t, 0.12)
    blit(cv, big('badge', 'PREMIUM', *GOLD, s=6), cx, top - 60, k, k, -3 + 2 * math.sin(t * 3), anchor='center')
    if t > 0.25:
        sparkles(cv, t, cx, GROUND - 300, 460, 560, n=10, seed=2)
        if t < 1.2: sparkles(cv, t * 2, cx, GROUND - 300, 520, 620, n=10, seed=21)
    k = popin(t, 0.35, 0.3)
    tx, ty = cx + 150, GROUND - 330
    rot = swing(t, 0.35, 16)
    if t >= 1.23: rot *= 0.3
    blit(cv, big('tag', '$$$', '#ffd23f', '#1a1a2e', s=8), tx, ty, k, k, rot, anchor='center')
    if t >= 1.23:
        ks = slam(t, 1.23, 0.13, 1.8)
        blit(cv, big('xmark', s=15), tx, ty, ks, ks, anchor='center')
    dust(cv, t, 1.23, tx, ty + 40, n=10, seed=41)
    expr = 'shock' if 1.23 <= t < 1.6 else 'smile'
    k = 0.4 + 0.6 * popin(t, -0.2, 0.32)
    guy(cv, t, 255, expr, scale=k, poses=[(0.25, 1.2, 'point'), (1.23, 1.65, 'shock'), (1.65, 2.2, 'hips')])

def scene_speedo(cv, t):
    sx, sb = 700, GROUND - 300
    k = popin(t, 2.0, 0.32)
    ang = 166 + 2.5 * math.sin(t * 47) * (1 if 2.3 < t < 4.1 else 0)
    if 3.33 <= t < 3.9:
        ang -= 32 * math.sin(math.pi * prog(t, 3.33, 0.5)) * (1 - prog(t, 3.33, 0.57))
    blit(cv, big('speedo', int(ang) // 2 * 2, s=12), sx, sb, k, k)
    kb = popin(t, 2.05)
    blit(cv, big('badge', 'PREMIUM', *GOLD, s=6), sx, sb + 120, kb, kb, -4 + 2 * math.sin(t * 2.6), anchor='center')
    if t >= 3.5:
        k2 = popin(t, 3.5)
        blit(cv, big('label', '0 MPH', '#e0303a', s=9), sx, sb + 260, k2, k2, 3 * math.sin(t * 4), anchor='center')
    if t >= 4.1:
        ks = slam(t, 4.1, 0.14, 1.9)
        blit(cv, big('stamp', 'MYTH', '#e0303a', '#ffffff', s=15), sx, sb - 170, ks, ks, -12, anchor='center')
    dust(cv, t, 4.12, sx, sb - 60, n=14, seed=43)
    expr = 'shock' if 3.4 <= t < 3.95 else 'smile'
    guy(cv, t, 245, expr, poses=[(2.05, 2.8, 'point'), (3.33, 3.4, 'point'), (3.4, 3.95, 'shrug'), (4.1, 4.8, 'hips')])

def scene_engine(cv, t):
    ex = 740 + (3 if int(t * 30) % 2 and t > 5.0 else 0)
    k = popin(t, 4.84, 0.3)
    shadow(cv, ex, 420)
    blit(cv, big('engine', s=11), ex, GROUND, k, k)
    dust(cv, t, 4.86, ex, GROUND - 20, n=12, seed=44)
    by = GROUND - 341 - 140 + 10 * math.sin(t * 4)
    if 5.45 <= t < 6.3:
        kb = popin(t, 5.45)
        blit(cv, big('textbubble', 'PREMIUM?', s=6), ex + 40, by, kb, kb, 3, anchor='center')
    elif t >= 6.3:
        kb = popin(t, 6.3)
        blit(cv, big('textbubble', 'REGULAR OK', '#bff0c8', '#1f7a3a', s=6), ex + 20, by, kb, kb, -3, anchor='center')
    if t >= 7.02:
        kc = popin(t, 7.02)
        blit(cv, big('check', s=11), 880, GROUND - 640, kc, kc, anchor='center')
        gsparkles(cv, t, ex, GROUND - 330, 520, 520, n=10, seed=33)
    guy(cv, t, 245, 'smile', poses=[(4.86, 5.4, 'point'), (5.45, 6.25, 'shrug'), (6.3, 7.0, 'talkR'), (7.02, 7.9, 'thumb')])

BX, BY = 590, 500
def scene_manual(cv, t):
    bob = 8 * math.sin(t * 3)
    if t < 8.26:
        kc = popin(t, 7.83) * (1 - ic(prog(t, 8.14, 0.12)))
        blit(cv, big('book_closed', s=9), BX, BY + bob, max(0.02, kc), popin(t, 7.83), -4, anchor='center')
    else:
        green = t >= 9.11
        ko = popin(t, 8.24, 0.26)
        args = ('FUEL', 'REGULAR', '#7fe3a0') if green else ('', 'CHECK')
        blit(cv, big('book_open', *args, s=7), BX, BY + bob, ko, ko, anchor='center')
        spine = BX
        if 9.11 <= t < 9.41:  # page flip right -> left
            c = math.cos(math.pi * prog(t, 9.11, 0.3))
            pw = 48 * 7 * abs(c)
            blit(cv, big('page', s=7), spine + (pw / 2 + 4) * (1 if c > 0 else -1), BY + bob - 7, abs(c), 1, anchor='center')
        tx = BX + 26 * 7 - 4
        if t >= 8.51:
            ka = popin(t, 8.51)
            blit(cv, big('arrow', s=9), tx, BY + bob - 230 - 18 * abs(math.sin(t * 7)), ka, ka, anchor='center')
        if t >= 9.51:
            gsparkles(cv, t, tx, BY + bob, 380, 200, n=9, seed=35)
        elif 8.51 <= t < 9.11:
            sparkles(cv, t, tx, BY + bob, 380, 200, n=7, seed=36)
    guy(cv, t, 230, 'smile', poses=[(7.83, 8.5, 'pointup'), (8.51, 9.1, 'talkR'), (9.11, 10.1, 'pointup')])

def scene_regular(cv, t):
    cx = pump_at(cv, t, PX, green=True, t_in=9.98)
    kb = popin(t, 10.14)
    blit(cv, big('badge', 'REGULAR', *GREEN, s=6), cx, GROUND - 564, kb, kb, 3 * math.sin(t * 3), anchor='center')
    if t >= 10.39:
        kc = popin(t, 10.39)
        blit(cv, big('check', s=11), cx + 150, GROUND - 700, kc, kc, anchor='center')
        gsparkles(cv, t, cx, GROUND - 330, 520, 640, n=12, seed=37)
    lift = -2 * S * abs(math.sin((t - 10.39) * 2 * math.pi * 1.6)) if 10.39 <= t < 11.0 else 0
    guy(cv, t, 245, 'smile', lift=lift, poses=[(10.14, 10.39, 'point'), (10.39, 11.2, 'down')])

def scene_label(cv, t):
    cx = 780
    kb = popin(t, 11.2, 0.3)
    shadow(cv, cx, 330)
    blit(cv, big('bottle'), cx, GROUND, kb, kb)
    LY = GROUND - 220
    lab = big('badge', 'PREMIUM', *GOLD, s=6)
    if t < 13.32:
        blit(cv, lab, cx, LY + 2 * math.sin(t * 5), kb, kb, 2 * math.sin(t * 3), anchor='center')
        if t > 11.35: sparkles(cv, t, cx, LY, 360, 160, n=6, seed=38)
        if 12.9 <= t < 13.32: sparkles(cv, t * 2.5, cx, LY - 40, 520, 340, n=14, seed=39)
    else:
        p = prog(t, 13.32, 0.28)
        lx = cx + (600 - cx) * oc(p); ly = LY + (GROUND - 40 - LY) * ic(p)
        rot = -40 * p if p < 1 else 22 * math.sin(2 * math.pi * 3 * (t - 13.6)) * math.exp(-4 * (t - 13.6))
        blit(cv, lab, lx, ly, 1, 1, rot, anchor='center')
    dust(cv, t, 13.6, 600, GROUND - 20, n=10, seed=45)
    if 11.48 <= t < 12.6:
        ks = popin(t, 11.48) * (1 - ic(prog(t, 12.4, 0.2)))
        sy = GROUND - 560
        blit(cv, big('speedo', 100, s=6), cx, sy, ks, ks)
        if t >= 11.73:
            kx = slam(t, 11.73, 0.12, 1.6) * (1 - ic(prog(t, 12.4, 0.2)))
            blit(cv, big('xmark', s=10), cx, sy - 90, kx, kx, anchor='center')
    if t >= 13.62:
        ks = slam(t, 13.62, 0.14, 1.8)
        blit(cv, big('stamp', 'NO SPEED GAIN', '#e0303a', '#ffffff', s=9), 600, GROUND - 640, ks, ks, -8, anchor='center')
    expr = 'shock' if 13.32 <= t < 13.62 else 'smile'
    guy(cv, t, 215, expr, poses=[(11.23, 11.7, 'point'), (11.73, 12.35, 'shrug'), (12.9, 13.3, 'point'), (13.32, 13.62, 'shock'), (13.62, 14.1, 'hips')])

HAND = (399, 968)
COIN_T = [14.41 + i * 0.09 for i in range(10)]
def scene_cash(cv, t):
    cx = pump_at(cv, t, PX, green=True)
    kb = popin(t, 14.0) * (1 - ic(prog(t, 15.85, 0.15)))
    blit(cv, big('badge', 'REGULAR', *GREEN, s=6), cx, GROUND - 564, kb, kb, 3 * math.sin(t * 3), anchor='center')
    landed = 0
    for t0 in COIN_T:
        dt = t - t0
        if dt < 0: continue
        if dt >= 0.4: landed += 1; continue
        p = dt / 0.4
        x = cx - 40 + (HAND[0] - cx + 40) * p
        y = GROUND - 400 + (HAND[1] - GROUND + 400) * p - 300 * math.sin(math.pi * p)
        blit(cv, big('coin', s=8), x, y, 1, 1, anchor='center')
    lift = -150 * math.sin(math.pi * prog(t, 16.0, 0.42)) if 16.0 <= t < 16.42 else 0
    guy(cv, t, 245, 'smile', lift=lift, poses=[(14.3, 15.42, 'catch'), (15.42, 18.1, 'thumb')])
    if t < 15.42:
        for i in range(min(landed, 6)):
            blit(cv, big('coin', s=8), HAND[0] + 6, HAND[1] - 20 - i * 3 * S + idle_bob(t), anchor='center')
    else:
        poof(cv, t, 15.42, HAND[0] + 10, HAND[1] - 60, seed=46)
        sparkles(cv, t * 1.5, 420, 900, 260, 260, n=8, seed=47)
    # finale
    if t >= 16.0:
        confetti(cv, t, 16.0, 300, 700, n=50, seed=4)
        confetti(cv, t, 16.05, 800, 640, n=44, seed=8, spread=0.9)
        r = rng_for(19)
        for i in range(16):
            t0 = 16.15 + r.uniform(0, 1.4); dt = t - t0
            if dt < 0: continue
            blit(cv, big('coin', s=8), r.uniform(80, 1000), -60 + 1700 * dt * dt * 0.9, anchor='center')
        ks = slam(t, 16.05, 0.16, 1.5) * (1 + 0.04 * math.sin((t - 16.05) * 7))
        blit(cv, big('badge', 'SAVE $', *GREEN, s=12), 560, 520, ks, ks, -6 + 3 * math.sin(t * 2.4), anchor='center')
        sparkles(cv, t * 1.4, 560, 520, 640, 320, n=12, seed=48)
        gsparkles(cv, t, cx, GROUND - 330, 480, 600, n=8, seed=49)

SCENES = [(0.0, scene_hook), (2.0, scene_speedo), (4.72, scene_engine), (7.72, scene_manual),
          (10.02, scene_regular), (11.12, scene_label), (14.02, scene_cash)]
TR_PRE, TR_LEN = 0.1, 0.26

def draw_scene(i, t):
    cv = Image.new('RGB', (W, H), BG)
    SCENES[i][1](cv, t)
    return cv

def world(t):
    idx = max(i for i, (s, _) in enumerate(SCENES) if t >= s - TR_PRE)
    b = SCENES[idx][0]
    if idx > 0 and t < b - TR_PRE + TR_LEN:
        e = io(prog(t, b - TR_PRE, TR_LEN))
        dirn = 1 if idx % 2 else -1
        a, n = draw_scene(idx - 1, t), draw_scene(idx, t)
        cv = Image.new('RGB', (W, H), BG)
        cv.paste(a, (int(-dirn * W * e), 0))
        cv.paste(n, (int(dirn * W * (1 - e)), 0))
        return cv, idx
    return draw_scene(idx, t), idx

# ------------------------------------------------------------------ camera
SHAKES = [(1.23, 0.25, 18), (4.1, 0.35, 30), (11.73, 0.2, 12), (13.5, 0.2, 10), (13.62, 0.35, 28), (16.0, 0.3, 16)]
PUNCH = [(16.0, 18.0, 1.08, 560, 760)]
# instant zoom kicks that ease back: (time, amount, anchor x, anchor y)
KICKS = [(0.0, 0.22, 600, 900), (1.23, 0.07, 900, 850), (2.05, 0.05, 700, 900), (3.33, 0.1, 700, 820),
         (4.1, 0.08, 700, 780), (5.45, 0.05, 760, 750), (6.3, 0.05, 760, 750), (7.02, 0.06, 760, 800),
         (8.51, 0.08, 760, 520), (9.51, 0.06, 760, 520), (10.39, 0.08, 760, 700), (11.73, 0.07, 780, 700),
         (12.95, 0.05, 780, 960), (13.62, 0.08, 600, 700), (15.42, 0.08, 400, 900), (16.0, 0.12, 560, 700)]
BASE_Z, BASE_A = 1.18, (540, 1000)

def camera(t, idx):
    s0 = SCENES[idx][0]
    z = BASE_Z * (1 + 0.03 * prog(t, s0, 6))
    ax, ay = BASE_A
    for a, b, zz, px, py in PUNCH:
        if a <= t < b + 0.3:
            k = io(prog(t, a, 0.3)) * (1 - io(prog(t, b, 0.25)))
            z *= 1 + (zz - 1) * k
            ax += (px - ax) * k; ay += (py - ay) * k
    for a, amt, px, py in KICKS:
        if a <= t < a + 0.6:
            k = math.exp(-(t - a) * 9)
            z *= 1 + amt * k
            ax += (px - ax) * k * 0.5; ay += (py - ay) * k * 0.5
    sx = sy = 0
    for a, d, amp in SHAKES:
        if a <= t < a + d:
            k = (1 - (t - a) / d) ** 2
            sx += amp * k * math.sin((t - a) * 90); sy += amp * k * math.cos((t - a) * 77)
    return z, ax, ay, sx, sy

def apply_cam(cv, z, ax, ay, sx, sy):
    # zoom about anchor (ax, ay): that world point stays put on screen; then shake
    x0 = ax * (1 - 1 / z) - sx / z; y0 = ay * (1 - 1 / z) - sy / z
    return cv.transform((W, H), Image.AFFINE, (1 / z, 0, x0, 0, 1 / z, y0), resample=Image.NEAREST, fillcolor=BG)

# ------------------------------------------------------------------ captions
FONT_PATH = os.environ.get('PIXEL_FONT', '/usr/share/fonts/opentype/inter/Inter-Black.otf')

def font(size):
    if os.path.isfile(FONT_PATH):
        return ImageFont.truetype(FONT_PATH, size)
    try:
        return ImageFont.truetype('DejaVuSans-Bold.ttf', size)
    except OSError:
        return ImageFont.load_default(size=size)

FONT = font(104)
EMPH = {'premium', 'faster', "doesn't", 'regular', 'fine', 'manual', 'check', 'speed', 'fancy', 'label', 'cash', 'cheap'}

def make_chunks():
    sents, cur = [], []
    for i, w in enumerate(WORDS):
        cur.append(i)
        if w['w'][-1] in '.,?!':
            sents.append(cur); cur = []
    if cur: sents.append(cur)
    chunks = []
    for s in sents:
        k = math.ceil(len(s) / 3)
        base, extra = divmod(len(s), k)
        j = 0
        for c in range(k):
            n = base + (1 if c < extra else 0)
            chunks.append(s[j:j + n]); j += n
    out = []
    for ci, c in enumerate(chunks):
        st = WORDS[c[0]]['s'] - 0.04
        nxt = WORDS[chunks[ci + 1][0]]['s'] - 0.04 if ci + 1 < len(chunks) else DUR
        en = min(nxt, WORDS[c[-1]]['e'] + 0.45)
        out.append((st, en, c))
    return out
CHUNKS = make_chunks()

def clean(w):
    w = w.lower().strip('.,!')
    return w

@lru_cache(None)
def caption_img(ci, active):
    idxs = CHUNKS[ci][2]
    words = [clean(WORDS[i]['w']) for i in idxs]
    d0 = ImageDraw.Draw(Image.new('RGB', (1, 1)))
    space = d0.textlength(' ', font=FONT)
    widths = [d0.textlength(w, font=FONT) for w in words]
    tw = sum(widths) + space * (len(words) - 1)
    pad = 40
    img = Image.new('RGBA', (int(tw + 2 * pad), 190), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    x = pad
    for i, (w, wd) in enumerate(zip(words, widths)):
        on = idxs[i] == active
        col = (255, 217, 59) if on else (255, 255, 255)
        if on and w.strip("?'") in EMPH: col = (255, 90, 90)
        d.text((x + 6, 30 + 8), w, font=FONT, fill=NAVY, stroke_width=14, stroke_fill=NAVY)
        d.text((x, 30), w, font=FONT, fill=col, stroke_width=13, stroke_fill=(10, 10, 16))
        x += wd + space
    if img.width > 1000:
        k = 1000 / img.width
        img = img.resize((1000, int(img.height * k)), Image.LANCZOS)
    return img

TFONT = font(92)

@lru_cache(None)
def title_img():
    lines = [('the stupidest', (255, 255, 255)), ('FUEL MYTH', (255, 90, 90))]
    img = Image.new('RGBA', (1000, 260), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for i, (txt, col) in enumerate(lines):
        f = TFONT if i == 0 else font(130)
        w = d.textlength(txt, font=f)
        y = 0 if i == 0 else 100
        d.text((500 - w / 2 + 6, y + 8), txt, font=f, fill=NAVY, stroke_width=14, stroke_fill=NAVY)
        d.text((500 - w / 2, y), txt, font=f, fill=col, stroke_width=13, stroke_fill=(10, 10, 16))
    return img

def title(cv, t):
    if t >= 3.8: return
    k = ob(prog(t, -0.2, 0.3)) * (1 - ic(prog(t, 3.45, 0.3)))
    if k <= 0.02: return
    img = title_img()
    rot = 3 * math.sin(t * 4)
    img = img.resize((int(img.width * k), int(img.height * k)), Image.BILINEAR).rotate(rot, resample=Image.BICUBIC, expand=True)
    cv.paste(img, (int(W / 2 - img.width / 2), int(330 - img.height / 2)), img)

def captions(cv, t):
    for ci, (st, en, idxs) in enumerate(CHUNKS):
        if st <= t < en:
            active = None
            for i in idxs:
                if WORDS[i]['s'] - 0.04 <= t: active = i
            img = caption_img(ci, active)
            k = 0.72 + 0.28 * ob(prog(t, st, 0.16))
            if k != 1:
                img = img.resize((int(img.width * k), int(img.height * k)), Image.BILINEAR)
            cv.paste(img, (int(W / 2 - img.width / 2), int(1390 - img.height / 2)), img)
            return

# ------------------------------------------------------------------ frame + audio
def frame(n):
    t = n / FPS
    cv, idx = world(t)
    cv = apply_cam(cv, *camera(t, idx))
    title(cv, t)
    captions(cv, t)
    return cv.tobytes()

CUES = [
    (0.0, 'whoosh', 0.8), (0.05, 'pop', 0.7), (0.15, 'pop', 0.5), (0.35, 'pop', 0.6), (0.4, 'sparkle', 0.8), (1.23, 'stamp', 1.0),
    (1.9, 'whoosh', 0.6), (2.02, 'pop', 0.5), (2.07, 'pop', 0.6), (3.25, 'vroom', 0.6), (3.5, 'pop', 0.5),
    (4.1, 'stamp', 1.0), (4.12, 'boom', 0.5),
    (4.62, 'whoosh', 0.6), (4.86, 'thump', 0.8), (5.45, 'pop', 0.7), (6.3, 'pop', 0.7), (7.02, 'ding', 0.9), (7.05, 'sparkle', 0.7),
    (7.62, 'whoosh', 0.6), (7.83, 'pop', 0.7), (8.24, 'whoosh', 0.5), (8.51, 'pop', 0.6), (9.11, 'whoosh', 0.6), (9.51, 'sparkle', 0.8),
    (9.92, 'whoosh', 0.6), (10.14, 'pop', 0.6), (10.39, 'ding', 0.9), (10.42, 'sparkle', 0.7),
    (11.02, 'whoosh', 0.6), (11.2, 'pop', 0.7), (11.48, 'pop', 0.5), (11.73, 'stamp', 0.8), (12.9, 'sparkle', 0.9),
    (13.32, 'slide_down', 0.6), (13.58, 'thump', 0.6), (13.62, 'stamp', 1.0),
    (13.92, 'whoosh', 0.6), (14.0, 'pop', 0.5),
] + [(t0 + 0.4, 'coin', 0.7) for t0 in COIN_T] + [
    (15.42, 'pop', 0.7), (15.45, 'sparkle', 0.6), (16.0, 'confetti', 1.0), (16.0, 'cha_ching', 1.0), (16.05, 'pop', 0.8),
] + [(16.5 + i * 0.22, 'coin', 0.35) for i in range(5)]

def build_audio(vo_path, out_wav):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', vo_path, '-ar', str(sfx.SR), '-ac', '1', '-f', 'f32le', '-'],
                         capture_output=True, check=True).stdout
    vo = np.frombuffer(raw, np.float32).astype(np.float64)
    n = int(sfx.SR * DUR)
    mix = np.zeros(n); mix[:min(n, len(vo))] = vo[:n]
    fx = sfx.render(CUES, DUR)
    fx *= 0.32 * np.max(np.abs(vo)) / max(1e-9, np.max(np.abs(fx)))
    mix += fx
    mix /= max(1.0, np.max(np.abs(mix)) / 0.97)
    pcm = (mix * 32767).astype('<i2')
    import wave
    with wave.open(out_wav, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sfx.SR); w.writeframes(pcm.tobytes())

if __name__ == '__main__':
    mode = sys.argv[1]
    if mode == 'still':
        for ts in sys.argv[3:]:
            t = float(ts); n = int(t * FPS)
            Image.frombytes('RGB', (W, H), frame(n)).save(f'{sys.argv[2]}/f_{ts}.png')
    elif mode == 'video':
        vo, out = sys.argv[2], sys.argv[3]
        t0, t1 = (float(sys.argv[4]), float(sys.argv[5])) if len(sys.argv) > 5 else (0.0, DUR)  # optional test range
        build_audio(vo, 'mix.wav')
        F0, N = int(t0 * FPS), int(t1 * FPS)
        ff = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS),
                               '-i', '-', '-ss', str(t0), '-t', str(t1 - t0), '-i', 'mix.wav', '-c:v', 'libx264', '-preset', 'medium', '-crf', '17', '-pix_fmt', 'yuv420p',
                               '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', '-shortest', out], stdin=subprocess.PIPE)
        with Pool(4) as pool:
            for i, b in enumerate(pool.imap(frame, range(F0, N), chunksize=6)):
                ff.stdin.write(b)
                if i % 300 == 0: print(f'{i}/{N}', flush=True)
        ff.stdin.close(); ff.wait()
        print('done', ff.returncode)
        raise SystemExit(ff.returncode)
