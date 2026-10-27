"""Renders the 'airbag' TikTok explainer, synced to the voiceover."""
import json, math, os, sys, subprocess
from functools import lru_cache
from multiprocessing import Pool
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import pix, sfx

W, H, FPS, S = 1080, 1920, 60, 9
GROUND = 1180
DUR = 18.9
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

def dust(cv, t, t0, x, y, n=10, seed=5, life=0.6, dirx=0, fill=(205, 205, 214)):
    dt = t - t0
    if dt < 0 or dt > life: return
    r = rng_for(seed); d = ImageDraw.Draw(cv)
    k = 1 - dt / life
    for i in range(n):
        vx = r.uniform(-500, 500) + dirx; vy = r.uniform(-260, -40)
        px = x + vx * dt; py = y + vy * dt
        s = S * (1 + int(2 * k * r.uniform(0.5, 1.5)))
        d.rectangle((px - s, py - s, px + s, py + s), fill=fill, outline=NAVY, width=3)

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

def dizzy(cv, t, cx, y):
    for i in range(3):
        a = t * 6 + i * 2 * math.pi / 3
        blit(cv, big('star', s=8), cx + math.cos(a) * 120, y + math.sin(a) * 30, anchor='center')

def motion_lines(cv, cx, y, k=1.0, dirn=-1):
    d = ImageDraw.Draw(cv)
    for i, (dy, ln) in enumerate(((-150, 200), (-80, 140), (-20, 240))):
        x1 = cx + dirn * (260 + i * 30); x2 = x1 + dirn * ln * k
        d.rectangle((min(x1, x2), y + dy, max(x1, x2), y + dy + S), fill=(190, 190, 200))

def smell(cv, t, t0, cx, cy):
    dt = t - t0
    if dt < 0: return
    d = ImageDraw.Draw(cv)
    for i in range(4):
        ph = (dt * 0.9 + i / 4) % 1
        bx = cx + (-150, -60, 70, 160)[i]; by = cy + 120 - ph * 420
        for j in range(5):
            yy = by - j * 22
            xx = bx + 18 * math.sin((j + dt * 6 + i) * 1.2)
            d.rectangle((xx, yy, xx + S * 2, yy + S * 2), fill=(155, 227, 168))

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

def car(cv, t, cx, color, moving=False, bounce=0.0, sx=1.0):
    phase = int(t * 24) % 2 if moving else 0
    shadow(cv, cx, 440 * sx)
    blit(cv, big('car', color, phase), cx, GROUND + bounce, sx, sx)

# ------------------------------------------------------------------ scenes
@lru_cache(None)
def mirrored(name, *args, s=S):
    return big(name, *args, s=s).transpose(Image.FLIP_LEFT_RIGHT)

def burst(cv, t, t0, x, y, n=14, col=(255, 210, 63), life=0.38, r0=150, reach=430):
    dt = t - t0
    if dt < 0 or dt > life: return
    p = oc(dt / life); d = ImageDraw.Draw(cv)
    for i in range(n):
        a = i / n * 2 * math.pi + 0.2
        ra, rb = r0 + reach * p, r0 + reach * p + 110 * (1 - p)
        d.line((x + math.cos(a) * ra, y + math.sin(a) * ra, x + math.cos(a) * rb, y + math.sin(a) * rb), fill=col, width=2 * S)

def radar(cv, t, x, y):
    d = ImageDraw.Draw(cv)
    for i in range(3):
        r = 40 + 170 * ((t * 1.4 + i / 3) % 1)
        d.arc((x - r, y - r, x + r, y + r), 200, 340, fill=(60, 200, 90), width=S)

def hearts(cv, t, t0, x, y, n=4, seed=31):
    dt = t - t0
    if dt < 0 or dt > 1.2: return
    r = rng_for(seed)
    for i in range(n):
        vx = r.uniform(-120, 160); k = popin(t, t0 + i * 0.08, 0.25) * (1 - ic(prog(t, t0 + 0.8, 0.4)))
        blit(cv, big('heart', s=8), x + vx * dt + i * 30, y - 320 * dt - i * 40, k, k, anchor='center')

WX, WY = 760, 830   # steering wheel / airbag centre

def scene_hook(cv, t):
    shake = 7 * math.sin(t * 80) * prog(t, 0.48, 0.7) if 0.48 <= t < 1.18 else 0
    k = popin(t, 0.0, 0.35)
    blit(cv, big('wheel', s=11), WX + shake, WY, k, k, 4 * math.sin(t * 3), anchor='center')
    if 0.48 <= t < 1.18:
        sparkles(cv, t * 2, WX, WY, 460, 460, n=10, seed=12)
    if t >= 1.18:
        ka = ob(prog(t, 1.18, 0.2)) * (1 + 0.025 * math.sin(t * 7))
        blit(cv, big('airbag', s=12), WX, WY - 10, ka, ka, anchor='center')
        sparkles(cv, t, WX, WY, 560, 460, n=7, seed=14)
    burst(cv, t, 1.18, WX, WY)
    poof(cv, t, 1.18, WX, WY, seed=10)
    if 1.24 <= t < 2.3:
        kp = slam(t, 1.24, 0.14, 1.6) * (1 - ic(prog(t, 2.05, 0.25)))
        blit(cv, big('label', 'POP!', '#ffd23f', s=13), WX - 20, WY + 300, kp, kp, -10 + 3 * math.sin(t * 9), anchor='center')
    if t >= 2.3:
        ke = popin(t, 2.3, 0.25)
        blit(cv, big('eye', 2.56 <= t < 2.8, s=9), WX, 470, ke, ke, anchor='center')
        if t >= 2.56:
            motion_lines(cv, WX + 40, 560, oc(prog(t, 2.56, 0.2)) * (1 - prog(t, 2.9, 0.3)), dirn=1)
    expr = 'shock' if 1.18 <= t < 2.3 else 'smile'
    lift = -130 * math.sin(math.pi * prog(t, 1.18, 0.42)) if 1.18 <= t < 1.6 else 0
    kg = 0.4 + 0.6 * popin(t, -0.2, 0.32)
    guy(cv, t, 255, expr, lift=lift, scale=kg, poses=[(0.48, 1.1, 'point'), (1.18, 1.9, 'flail'), (2.3, 3.3, 'pointup')])
    confetti(cv, t, 1.2, WX, WY - 100, n=34, seed=4, spread=0.9)

WALLX, IMPACT = 520, 4.89

def scene_crash(cv, t):
    rot = 3 * math.sin((t - IMPACT) * 30) * math.exp(-(t - IMPACT) * 5) if t >= IMPACT else 0
    blit(cv, big('wall', s=9), WALLX, GROUND, rot=rot)
    hit = WALLX + 81 + 234
    if t < IMPACT:
        p = prog(t, 3.3, IMPACT - 3.3); cx = 1250 - (1250 - hit) * p; sq = 0
    else:
        cx = hit + 45 * oc(prog(t, IMPACT, 0.25)); sq = 1 - oc(prog(t, IMPACT, 0.35))
    moving = t < IMPACT
    if 3.6 <= t < IMPACT:
        motion_lines(cv, cx, GROUND, oc(prog(t, 3.6, 0.2)), dirn=1)
    shadow(cv, cx, 440)
    blit(cv, mirrored('car', 'red', int(t * 24) % 2 if moving else 0), cx, GROUND, 1 - 0.16 * sq, 1 + 0.08 * sq)
    if t >= 3.83:
        sy = GROUND - 216 - 150
        ks = popin(t, 3.83, 0.3)
        radar(cv, t, cx, sy - 30)
        blit(cv, big('sensor', s=8), cx, sy, ks, ks, anchor='center')
        if t >= 4.18:
            kx = slam(t, 4.18, 0.12, 1.5)
            blit(cv, big('glyph', '!', '#ff3b3b', s=14), cx + 150, sy - 120 + 10 * math.sin(t * 12), kx, kx, 8, anchor='center')
    dust(cv, t, IMPACT, hit - 234, GROUND - 120, n=16, seed=15, dirx=300)
    burst(cv, t, IMPACT, hit - 234, GROUND - 160, n=12, r0=60, reach=260)
    if t >= IMPACT:
        k = slam(t, IMPACT, 0.13, 1.8)
        blit(cv, big('stamp', 'CRASH!', s=11), 700, 520, k, k, -8, anchor='center')
    expr = 'shock' if t >= IMPACT else 'smile'
    guy(cv, t, 215, expr, poses=[(3.83, 4.6, 'point'), (IMPACT, 5.6, 'flail')])

BX, BY = 690, 640   # airbag centre for fill / deflate

def scene_fill(cv, t):
    if t < 7.5:
        yo = -1100 * ic(prog(t, 7.15, 0.3))
        k = popin(t, 5.6, 0.3)
        step = int((t - 5.93) * 70) % 16 if 5.93 <= t < 6.49 else (5 if t >= 6.49 else 0)
        blit(cv, big('stopwatch', step, s=12), 760, 700 + yo, k, k, anchor='center')
        if t >= 5.93:
            ms = int(round(30 * prog(t, 5.93, 0.56)))
            kl = slam(t, 6.49, 0.13, 1.5) if t >= 6.49 else 1
            col = '#ff3b3b' if t >= 6.49 else '#1a1a2e'
            blit(cv, big('badge', f'{ms}MS', '#ffffff', col, '#d6d9e2', s=9), 760, 1010 + yo, kl, kl, -4 if t >= 6.49 else 0, anchor='center')
        if 6.49 <= t < 7.2:
            sparkles(cv, t * 2, 760, 700, 520, 520, n=12, seed=16)
        burst(cv, t, 6.49, 760, 700, n=12, r0=200, reach=260)
    if t >= 7.3:
        kc = popin(t, 7.37, 0.3)
        jit = 8 * math.sin(t * 70) if 7.84 <= t < 8.6 else 0
        shadow(cv, 880, 180)
        blit(cv, big('canister', s=11), 880 + jit, GROUND, kc, kc)
        if 7.84 <= t < 8.75:
            d = ImageDraw.Draw(cv)
            nx, ny = 880, GROUND - 286
            for i in range(9):
                ph = ((t - 7.84) * 2.6 + i / 9) % 1
                px = nx + (BX + 60 - nx) * ph + 30 * math.sin(i * 2 + t * 8); py = ny + (BY + 120 - ny) * ph
                r = S * (2 + int(2 * math.sin(math.pi * ph)))
                d.rectangle((px - r, py - r, px + r, py + r), fill=(235, 238, 245), outline=NAVY, width=3)
        if t >= 7.84:
            ka = 0.12 + 0.88 * ob(prog(t, 7.84, 0.71))
            if t >= 8.55: ka *= 1 + 0.05 * math.sin((t - 8.55) * 30) * math.exp(-(t - 8.55) * 6)
            blit(cv, big('airbag', s=11), BX, BY, ka, ka, anchor='center')
        if t >= 8.55:
            kb = slam(t, 8.55, 0.13, 1.6)
            blit(cv, big('badge', 'FULL!', '#bff0c8', '#1f7a3a', '#8fd6a0', s=9), BX + 60, BY - 270, kb, kb, 6, anchor='center')
            sparkles(cv, t * 1.5, BX, BY, 520, 440, n=10, seed=18)
            confetti(cv, t, 8.55, BX, BY - 100, n=28, seed=19, spread=0.8)
    expr = 'shock' if 6.49 <= t < 7.1 else 'smile'
    lift = -110 * math.sin(math.pi * prog(t, 8.55, 0.4)) if 8.55 <= t < 8.95 else 0
    guy(cv, t, 245, expr, lift=lift, poses=[(5.93, 6.45, 'point'), (7.46, 8.2, 'point'), (8.55, 9.4, 'up')])

def road_view(t):
    w, h = 560, 600
    v = Image.new('RGB', (w, h), (150, 210, 255)); d = ImageDraw.Draw(v)
    hz = int(h * 0.42)
    d.rectangle((0, hz, w, h), fill=(110, 200, 90))
    for cx, cy in ((120, 90), (400, 150)):
        d.rectangle((cx - 50, cy - 18, cx + 50, cy + 18), fill=(255, 255, 255))
        d.rectangle((cx - 30, cy - 36, cx + 25, cy), fill=(255, 255, 255))
    mid = w / 2
    d.polygon([(mid - 24, hz), (mid + 24, hz), (mid + 250, h), (mid - 250, h)], fill=(90, 92, 104))
    for i in range(6):
        z = ((i / 6) + t * 0.9) % 1
        y0 = hz + (h - hz) * z ** 2; y1 = hz + (h - hz) * min(1, z + 0.07) ** 2
        hw = 3 + 14 * z
        d.rectangle((mid - hw, y0, mid + hw, y1), fill=(255, 210, 63))
    d.rectangle((0, 0, w - 1, h - 1), outline=NAVY, width=4 * S)
    d.rectangle((4 * S, 4 * S, w - 4 * S - 1, h - 4 * S - 1), outline=(58, 59, 68), width=S)
    return v

def scene_deflate(cv, t):
    if t < 11.85:
        blit(cv, big('wheel', s=10), BX, BY + 60, anchor='center')
        k = 1 - 0.88 * io(prog(t, 10.23, 1.1))
        wob = 0.06 * math.sin(t * 26) if 10.23 <= t < 11.4 else 0
        if k > 0.13:
            blit(cv, big('airbag', s=11), BX, BY, k * (1 + wob), k * (1 - wob), anchor='center')
        for i, t0 in enumerate((10.25, 10.6, 10.95)):
            dust(cv, t, t0, BX + (-1) ** i * 180 * k, BY, n=8, seed=40 + i, dirx=(-1) ** i * 500, fill=(240, 242, 248))
        if 10.3 <= t < 11.7:
            kp = popin(t, 10.3) * (1 - ic(prog(t, 11.45, 0.25)))
            blit(cv, big('label', 'PSST!', '#5aa0ff', s=11), BX + 90, BY - 300, kp, kp, 6 * math.sin(t * 8), anchor='center')
    else:
        kv = ob(prog(t, 11.85, 0.32))
        v = road_view(t)
        blit(cv, v.convert('RGBA'), 730, 700, kv, kv, anchor='center')
        if 12.6 <= t < 13.4: sparkles(cv, t * 2, 730, 700, 560, 600, n=10, seed=22)
        if t >= 12.81:
            kc = slam(t, 12.81, 0.13, 1.6)
            blit(cv, big('check', s=13), 960, 420, kc, kc, anchor='center')
    guy(cv, t, 235, 'smile', poses=[(10.23, 11.2, 'shrug'), (12.29, 13.4, 'point')])

def strap(cv, t, cx, b):
    p = oc(prog(t, 15.04, 0.16))
    x0, y0 = cx - 82, 892 + b; x1, y1 = cx + 82, 1068 + b
    xe, ye = x0 + (x1 - x0) * p, y0 + (y1 - y0) * p
    d = ImageDraw.Draw(cv)
    d.line((x0, y0, xe, ye), fill=NAVY, width=6 * S)
    d.line((x0, y0, xe, ye), fill=(70, 72, 84), width=4 * S)
    d.line((x0 + S, y0 - S, xe + S, ye - S), fill=(120, 124, 138), width=S)
    if p > 0.95: blit(cv, big('buckle', s=4), x1, y1, anchor='center')

def scene_belt(cv, t):
    EY = 540
    if 13.78 <= t < 14.4:
        kq = popin(t, 13.78) * (1 - ic(prog(t, 14.2, 0.2)))
        blit(cv, big('glyph', '?', '#ff9f1c', s=20), 720, EY + 12 * math.sin(t * 5), kq, kq, 6 * math.sin(t * 3), anchor='center')
    if t >= 14.34:
        k = popin(t, 14.34)
        blit(cv, big('airbag', s=6), 545, EY, k, k, anchor='center')
    if t >= 14.58:
        k = popin(t, 14.58)
        blit(cv, big('glyph', '+', '#1a1a2e', s=12), 725, EY, k, k, anchor='center')
    if t >= 15.04:
        k = slam(t, 15.04, 0.13, 1.6)
        blit(cv, big('buckle', s=9), 880, EY, k, k, -6, anchor='center')
    if t >= 15.52:
        k = slam(t, 15.52, 0.13, 1.6)
        blit(cv, big('badge', 'BELT ON', '#bff0c8', '#1f7a3a', '#8fd6a0', s=8), 725, EY + 230, k, k, -4 + 2 * math.sin(t * 3), anchor='center')
        blit(cv, big('check', s=11), 725, EY - 230, k, k, anchor='center')
        confetti(cv, t, 15.52, 725, EY, n=26, seed=23, spread=0.8)
    expr = 'shock' if 15.04 <= t < 15.4 else 'smile'
    guy(cv, t, 255, expr, poses=[(13.78, 14.3, 'shrug'), (14.34, 15.0, 'point'), (15.52, 16.1, 'up')])
    if t >= 15.04: strap(cv, t, 255, idle_bob(t))

def scene_catch(cv, t):
    sq = math.sin((t - 17.04) * 26) * math.exp(-(t - 17.04) * 5) if t >= 17.04 else 0
    ka = ob(prog(t, 16.1, 0.3))
    shadow(cv, 730, 460)
    blit(cv, big('airbag', s=12), 730, GROUND, ka * (1 + 0.08 * sq), ka * (1 - 0.08 * sq))
    p = prog(t, 16.74, 0.3)
    x = 255 + 190 * oc(p); lift = -170 * math.sin(math.pi * p) if 16.74 <= t < 17.04 else 0
    if t >= 17.99:
        lift = -120 * math.sin(math.pi * prog(t, 17.99, 0.42)) if t < 18.41 else 0
    expr = 'shock' if 17.57 <= t < 17.85 else 'smile'
    guy(cv, t, x, expr, lift=lift, poses=[(16.74, 17.1, 'flail'), (17.1, 17.55, 'hips'), (17.57, 17.95, 'shock'), (17.99, 18.9, 'up')])
    hearts(cv, t, 17.05, 600, 760)
    if 17.04 <= t < 17.6: sparkles(cv, t * 2, 640, 900, 400, 400, n=10, seed=27)
    if t >= 17.5:
        if t < 18.05:
            gx = 1250 - 430 * oc(prog(t, 17.5, 0.25)); gy = 600; rot = 0
        else:
            dt = t - 18.05; gx = 820 + 200 * dt; gy = 600 + 400 * dt + 1800 * dt * dt; rot = -300 * dt
        blit(cv, mirrored('glove', s=10), gx, gy, 1, 1, rot, anchor='center')
        if 17.79 <= t < 18.05:
            kx = slam(t, 17.79, 0.12, 1.7)
            blit(cv, big('xmark', s=14), 820, 600, kx, kx, anchor='center')
    confetti(cv, t, 17.99, 300, 700, n=40, seed=29)
    confetti(cv, t, 18.02, 800, 650, n=34, seed=30, spread=0.8)

SCENES = [(0.0, scene_hook), (3.3, scene_crash), (5.6, scene_fill), (9.45, scene_deflate),
          (13.65, scene_belt), (16.1, scene_catch)]
TR_PRE, TR_LEN = 0.1, 0.24

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
SHAKES = [(1.18, 0.45, 38), (IMPACT, 0.45, 42), (6.49, 0.22, 14), (8.55, 0.3, 22), (12.81, 0.15, 8),
          (15.04, 0.25, 18), (17.04, 0.25, 14), (17.79, 0.25, 22), (17.99, 0.3, 12)]
PUNCH = [(1.18, 2.2, 1.08, WX, WY), (6.1, 7.1, 1.14, 760, 800), (12.4, 13.4, 1.07, 730, 760), (16.74, 17.5, 1.1, 520, 920)]
BASE_Z, BASE_A = 1.18, (540, 1000)

def camera(t, idx):
    s0 = SCENES[idx][0]
    z = BASE_Z * (1 + 0.03 * prog(t, s0, 4)) * (1 + 0.25 * (1 - oc(prog(t, 0, 0.45))))
    ax, ay = BASE_A
    for a, b, zz, px, py in PUNCH:
        if a <= t < b + 0.3:
            k = io(prog(t, a, 0.3)) * (1 - io(prog(t, b, 0.25)))
            z *= 1 + (zz - 1) * k
            ax += (px - ax) * k; ay += (py - ay) * k
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
EMPH = {'airbag', 'blink', 'crash', 'sensor', 'stop', 'thirty', 'milliseconds', 'gas', 'bag', 'deflates', 'fast',
        'road', 'only', 'seatbelt', 'catch', 'hit'}
END_T = 16.2   # final sentence becomes the two-line end card

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

def outlined(d, x, y, txt, f, col):
    d.text((x + 6, y + 8), txt, font=f, fill=NAVY, stroke_width=14, stroke_fill=NAVY)
    d.text((x, y), txt, font=f, fill=col, stroke_width=13, stroke_fill=(10, 10, 16))

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
        outlined(d, x, 30, w, FONT, col)
        x += wd + space
    if img.width > 1000:
        k = 1000 / img.width
        img = img.resize((1000, int(img.height * k)), Image.LANCZOS)
    return img

@lru_cache(None)
def two_line(top, bottom, col=(255, 217, 59), top_size=84, bottom_size=136):
    img = Image.new('RGBA', (1060, 290), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    ft = font(top_size); fb = font(bottom_size)
    while d.textlength(bottom, font=fb) > 980:
        bottom_size -= 6; fb = font(bottom_size)
    for txt, f, c, y in ((top, ft, (255, 255, 255), 0), (bottom, fb, col, top_size + 14)):
        if txt: outlined(d, 530 - d.textlength(txt, font=f) / 2, y, txt, f, c)
    return img

def paste_scaled(cv, img, k, cy, rot=0.0):
    if k <= 0.02: return
    img = img.resize((int(img.width * k), int(img.height * k)), Image.BILINEAR)
    if rot: img = img.rotate(rot, resample=Image.BICUBIC, expand=True)
    cv.paste(img, (int(W / 2 - img.width / 2), int(cy - img.height / 2)), img)

def title(cv, t):
    if t >= 2.3: return
    k = ob(prog(t, -0.2, 0.3)) * (1 - ic(prog(t, 2.0, 0.25)))
    paste_scaled(cv, two_line('how fast is', 'YOUR AIRBAG?'), k, 360, 3 * math.sin(t * 4))

def captions(cv, t):
    if t >= END_T:
        k = ob(prog(t, END_T, 0.25))
        bottom = 'NOT HIT YOU!' if t >= 17.55 else 'CATCH YOU'
        kb = slam(t, 17.55, 0.14, 0.35) if t >= 17.55 else 1
        paste_scaled(cv, two_line('built to', bottom), k * kb, 1420, -2 + 1.5 * math.sin(t * 4))
        return
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
    (0.0, 'whoosh', 0.8), (0.05, 'pop', 0.8), (0.48, 'sparkle', 0.8), (1.16, 'boom', 1.0), (1.18, 'poof', 0.9),
    (1.2, 'confetti', 0.7), (1.24, 'stamp', 0.6), (2.3, 'pop', 0.6), (2.56, 'whoosh', 0.4),
    (3.2, 'whoosh', 0.6), (3.35, 'vroom', 1.0), (3.83, 'pop', 0.7), (4.18, 'ding', 0.7), (4.55, 'screech', 1.0),
    (IMPACT, 'crash', 1.0), (IMPACT + 0.02, 'stamp', 0.8),
    (5.5, 'whoosh', 0.6), (5.62, 'pop', 0.7),
] + [(5.93 + i * 0.08, 'pop', 0.25) for i in range(7)] + [
    (6.49, 'ding', 1.0), (6.5, 'stamp', 0.5),
    (7.15, 'whoosh', 0.5), (7.38, 'pop', 0.7), (7.84, 'poof', 0.8), (7.9, 'whoosh', 0.8), (8.55, 'boom', 0.7),
    (8.57, 'sparkle', 0.8), (8.6, 'confetti', 0.5),
    (9.35, 'whoosh', 0.6), (10.23, 'slide_down', 1.0), (10.25, 'poof', 0.6), (10.6, 'poof', 0.4),
    (11.8, 'whoosh', 0.6), (11.9, 'pop', 0.7), (12.6, 'sparkle', 0.8), (12.81, 'ding', 0.9),
    (13.55, 'whoosh', 0.6), (13.8, 'pop', 0.5), (14.34, 'pop', 0.6), (14.58, 'pop', 0.5),
    (15.04, 'coin', 1.0), (15.06, 'thump', 0.7), (15.52, 'ding', 0.9), (15.54, 'confetti', 0.5),
    (16.0, 'whoosh', 0.6), (16.12, 'pop', 0.7), (16.74, 'whoosh', 0.5), (17.04, 'thump', 0.6), (17.06, 'sparkle', 0.7),
    (17.5, 'whoosh', 0.7), (17.79, 'buzzer', 0.9), (17.8, 'stamp', 0.6), (17.99, 'confetti', 1.0), (18.0, 'cha_ching', 0.6),
]

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
        t0 = float(sys.argv[4]) if len(sys.argv) > 4 else 0.0   # optional test-clip window
        t1 = float(sys.argv[5]) if len(sys.argv) > 5 else DUR
        build_audio(vo, 'mix.wav')
        F0, N = int(t0 * FPS), int(t1 * FPS)
        ff = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS),
                               '-i', '-', '-ss', str(t0), '-i', 'mix.wav', '-c:v', 'libx264', '-preset', 'medium', '-crf', '17', '-pix_fmt', 'yuv420p',
                               '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', '-shortest', out], stdin=subprocess.PIPE)
        with Pool(4) as pool:
            for i, b in enumerate(pool.imap(frame, range(F0, N), chunksize=6)):
                ff.stdin.write(b)
                if i % 300 == 0: print(f'{i}/{N}', flush=True)
        ff.stdin.close(); ff.wait()
        print('done', ff.returncode)
        raise SystemExit(ff.returncode)
