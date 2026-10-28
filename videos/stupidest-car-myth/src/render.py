"""Renders the 'stupidest car myth' (engine warm-up) TikTok explainer, synced to the voiceover."""
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

def dizzy(cv, t, cx, y):
    for i in range(3):
        a = t * 6 + i * 2 * math.pi / 3
        blit(cv, big('star', s=8), cx + math.cos(a) * 120, y + math.sin(a) * 30, anchor='center')

def motion_lines(cv, cx, y, k=1.0):
    d = ImageDraw.Draw(cv)
    for i, (dy, ln) in enumerate(((-150, 200), (-80, 140), (-20, 240))):
        x1 = cx - 260 - i * 30
        d.rectangle((x1 - ln * k, y + dy, x1, y + dy + S), fill=(190, 190, 200))

def smell(cv, t, t0, cx, cy, col=(155, 227, 168)):
    dt = t - t0
    if dt < 0: return
    d = ImageDraw.Draw(cv)
    for i in range(4):
        ph = (dt * 0.9 + i / 4) % 1
        bx = cx + (-150, -60, 70, 160)[i]; by = cy + 120 - ph * 420
        for j in range(5):
            yy = by - j * 22
            xx = bx + 18 * math.sin((j + dt * 6 + i) * 1.2)
            d.rectangle((xx, yy, xx + S * 2, yy + S * 2), fill=col)

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

# ------------------------------------------------------------------ eye-candy helpers
def rays(cv, t, cx, cy, k=1.0, n=12, col=(255, 243, 196)):
    if k <= 0.01: return
    d = ImageDraw.Draw(cv); R = 900 * k
    for i in range(n):
        a = t * 0.7 + i * 2 * math.pi / n; b = a + math.pi / n * 0.6
        d.polygon([(cx, cy), (cx + R * math.cos(a), cy + R * math.sin(a)), (cx + R * math.cos(b), cy + R * math.sin(b))], fill=col)

def ring(cv, t, t0, cx, cy, col=(255, 210, 63)):
    dt = t - t0
    if dt < 0 or dt > 0.35: return
    p = dt / 0.35; r = 80 + 520 * oc(p)
    ImageDraw.Draw(cv).ellipse((cx - r, cy - r, cx + r, cy + r), outline=col, width=max(2, int(26 * (1 - p))))

def squiggles(cv, t, t0, t1, cx, cy, col=(255, 150, 60)):
    if not t0 <= t < t1: return
    smell(cv, t, t0, cx, cy, col)

def puffs(cv, t, t0, t1, x, y, every=0.3, dirx=-350, seed=40):
    for i in range(int((t1 - t0) / every) + 1):
        dust(cv, t, t0 + i * every, x, y, n=5, seed=seed + i, life=0.5, dirx=dirx)

def oldcar(cv, t, cx, moving=False, bounce=0.0):
    shadow(cv, cx, 420)
    blit(cv, big('oldcar', int(t * 14) % 2 if moving else 0), cx, GROUND + bounce)

# ------------------------------------------------------------------ scenes
CLK = (720, 800)

def scene_hook(cv, t):
    cx, cy = CLK
    rays(cv, t, cx, cy, popin(t, -0.15, 0.35) * (1 - ic(prog(t, 2.6, 0.3))))
    ring(cv, t, 0.07, cx, cy); ring(cv, t, 1.83, cx, cy, (255, 77, 77))
    squiggles(cv, t, 0.63, 1.83, cx, cy - 200)
    k = popin(t, -0.13, 0.3)
    crossed = t >= 1.83
    col = '#8a8f9a' if crossed else ('#ff3b3b' if int(t * 5) % 2 == 0 else '#ff9a9a')
    rot = 6 * math.sin(t * 34) * math.exp(-5 * t) + (-6 * oc(prog(t, 1.83, 0.2)) if crossed else 0)
    if not crossed:
        k *= 1 + 0.05 * abs(math.sin(t * 2 * math.pi * 1.8))  # heartbeat pulse
    blit(cv, big('dashclock', '5:00', col, s=16), cx, cy, k, k, rot, anchor='center')
    if not crossed:
        sparkles(cv, t, cx, cy, 640, 380, n=9, seed=31)
        ka = popin(t, 0.3)
        bob = 26 * abs(math.sin(t * 7))
        blit(cv, big('arrow', s=9), cx + 150 - bob * 0.7, cy + 230 - bob * 0.7, ka, ka, -135, anchor='center')
    else:
        kx = slam(t, 1.83, 0.13, 1.8)
        blit(cv, big('xmark', s=24), cx, cy, kx, kx, anchor='center')
        confetti(cv, t, 1.83, cx, cy - 100, n=18, seed=33, spread=0.6)
    expr = 'shock' if 1.83 <= t < 2.5 else 'smile'
    lift = -120 * math.sin(math.pi * prog(t, 1.83, 0.4)) if 1.83 <= t < 2.23 else 0
    kg = 0.45 + 0.55 * popin(t, -0.15, 0.3)
    guy(cv, t, 230, expr, lift=lift, scale=kg, poses=[(0.0, 1.83, 'point'), (1.83, 2.4, 'shock')])

def scene_old(cv, t):
    cx = 730 + 900 * (1 - oc(prog(t, 2.85, 0.5)))
    chug = -S * (int(t * 16) % 2) if t < 6.0 else 0
    puffs(cv, t, 2.9, 6.0, cx - 230, GROUND - 40, seed=41)
    if t >= 5.1:
        for i in range(3): dust(cv, t, 5.1 + i * 0.12, cx - 240, GROUND - 60, n=9, seed=50 + i, life=0.7, dirx=-500)
    oldcar(cv, t, cx, moving=t < 3.4, bounce=chug)
    if t >= 3.3:
        k = slam(t, 3.3, 0.13, 1.8)
        blit(cv, big('stamp', 'OLD', s=13), cx, GROUND - 130, k, k, 10, anchor='center')
    if t >= 3.6:
        k = popin(t, 3.6)
        blit(cv, big('badge', '1970', '#fff6e0', '#1a1a2e', '#d6d9e2', s=7), cx + 120, GROUND - 300, k, k, -6 + 3 * math.sin(t * 3), anchor='center')
    if t >= 4.59:
        k = popin(t, 4.59)
        step = int(4 * prog(t, 4.9, 0.3))
        blit(cv, big('choke', step, s=10), 760, 600, k, k, 2 * math.sin(t * 4), anchor='center')
        kb = popin(t, 4.7)
        blit(cv, big('badge', 'CHOKE', '#ffffff', '#1a1a2e', '#d6d9e2', s=7), 690, 450, kb, kb, -4, anchor='center')
        if 4.6 <= t < 5.6: sparkles(cv, t * 2, 760, 600, 460, 220, n=8, seed=43)
    expr = 'shock' if 3.3 <= t < 3.9 else 'smile'
    guy(cv, t, 230, expr, poses=[(2.95, 3.3, 'point'), (3.3, 3.9, 'shock'), (4.59, 5.4, 'pointup'), (5.42, 6.05, 'shrug')])

def scene_modern(cv, t):
    cx = 730
    poof(cv, t, 6.12, cx, GROUND - 130)
    if t < 6.15:
        oldcar(cv, t, cx)
    else:
        bounce = -1000 * (1 - ob(prog(t, 6.15, 0.38)))
        car(cv, t, cx, 'blue', bounce=bounce)
        if t > 6.4: sparkles(cv, t * 1.4, cx, GROUND - 120, 520, 260, n=10, seed=51)
        dust(cv, t, 6.36, cx, GROUND - 20, n=12, seed=52)
    if t >= 6.3:
        k = popin(t, 6.3)
        blit(cv, big('badge', 'MODERN', '#bff0c8', '#1f7a3a', '#8fd6a0', s=7), cx, GROUND - 330, k, k, -4 + 2 * math.sin(t * 2.5), anchor='center')
    if t >= 6.78:
        k = popin(t, 6.78)
        blit(cv, big('choke', 4, s=8), 760, 560, k, k, anchor='center')
        if t >= 6.88:
            kx = slam(t, 6.88, 0.12, 1.6)
            blit(cv, big('xmark', s=13), 760, 560, kx, kx, anchor='center')
    guy(cv, t, 230, 'smile', poses=[(6.15, 6.75, 'hips'), (6.78, 7.55, 'point')])

def watch_text(t):
    if t < 7.9: return '5:00'
    v = int(round((300 - 270 * io(prog(t, 7.9, 0.87))) / 10)) * 10
    return f'{v // 60}:{v % 60:02d}'

def scene_timer(cv, t):
    cx, cy = 720, 790
    rays(cv, t, cx, cy, popin(t, 8.77, 0.35), col=(214, 247, 222))
    ring(cv, t, 8.77, cx, cy, (60, 200, 90))
    k = popin(t, 7.6, 0.3) * (slam(t, 8.77, 0.14, 0.35) if t >= 8.77 else 1)
    spin = 8 * math.sin(t * 50) if 7.9 <= t < 8.77 else 0
    col = '#1f9a45' if t >= 8.77 else '#e0303a'
    blit(cv, big('stopwatch', watch_text(t), col, s=15), cx, cy, k, k, spin, anchor='center')
    if t >= 7.7:
        kb = popin(t, 7.7)
        blit(cv, big('badge', 'MAKERS SAY', '#ffffff', '#1a1a2e', '#d6d9e2', s=7), cx, 420, kb, kb, -3 + 2 * math.sin(t * 3), anchor='center')
    if t >= 8.77:
        sparkles(cv, t * 1.5, cx, cy, 680, 640, n=12, seed=61)
    if t >= 9.55:
        kc = popin(t, 9.55, 0.3)
        blit(cv, big('check', s=16), cx + 220, cy - 230, kc, kc, anchor='center')
        confetti(cv, t, 9.55, cx + 200, cy - 200, n=36, seed=62)
    lift = -130 * math.sin(math.pi * prog(t, 9.55, 0.42)) if 9.55 <= t < 9.97 else 0
    guy(cv, t, 230, 'smile', lift=lift, poses=[(8.77, 9.5, 'point'), (9.55, 10.4, 'up')])

def road(cv, off):
    d = ImageDraw.Draw(cv)
    for i in range(10):
        x = (i * 160 - off) % (W + 320) - 160
        d.rectangle((x, GROUND + 40, x + 80, GROUND + 40 + S), fill=(205, 205, 214))

def scene_drive(cv, t):
    cx = 690
    s = max(0.0, t - 10.49)
    off = 320 * (s * s if s < 0.5 else s - 0.25)
    road(cv, off)
    moving = t >= 10.49
    bob = -S * (int(t * 6) % 2) if moving else 0
    if moving: puffs(cv, t, 10.5, 14.6, cx - 240, GROUND - 40, every=0.45, dirx=-450, seed=70)
    if 13.24 <= t < 14.0: motion_lines(cv, cx, GROUND - 60, oc(prog(t, 13.24, 0.2)))
    shadow(cv, cx, 440)
    blit(cv, big('car', 'blue', int(t * 10) % 2 if moving else 0), cx, GROUND + bob)
    squiggles(cv, t, 12.82, 14.6, cx + 150, GROUND - 260)
    if t >= 11.57:
        k = popin(t, 11.57)
        blit(cv, big('badge', 'GENTLY', '#bff0c8', '#1f7a3a', '#8fd6a0', s=8), cx - 40, GROUND - 330, k, k, -5 + 2 * math.sin(t * 2.5), anchor='center')
        if t < 12.4: sparkles(cv, t * 2, cx - 40, GROUND - 330, 420, 160, n=8, seed=71)
    if t >= 12.45:
        k = popin(t, 12.45)
        lvl = int(round(1 + 9 * io(prog(t, 12.82, 1.3))))
        blit(cv, big('thermo', lvl, s=9), 860, 600, k, k, anchor='center')
        if t >= 13.81:
            kc = popin(t, 13.81)
            blit(cv, big('check', s=10), 720, 440, kc, kc, anchor='center')
            sparkles(cv, t * 2, 860, 600, 260, 420, n=8, seed=72)
    guy(cv, t, 230, 'smile', poses=[(10.49, 11.2, 'wave'), (11.26, 12.1, 'point'), (13.81, 14.55, 'up')])

PUMP_X = 760; SPOUT = (PUMP_X - 180 + 26.5 * 12, GROUND - 528 + 16 * 12)
DROPS = [14.67 + i * 0.16 for i in range(int((16.5 - 14.67) / 0.16) + 1)]
FALL = math.sqrt(2 * (GROUND - SPOUT[1]) / 3000)

def scene_fuel(cv, t):
    end = 16.55
    out = ic(prog(t, end, 0.25))
    if t < end + 0.25:
        d = ImageDraw.Draw(cv)
        pw = 260 * prog(t, 14.8, 1.7) * (1 - out)
        if pw > 4:
            d.ellipse((SPOUT[0] - pw / 2, GROUND - 14, SPOUT[0] + pw / 2, GROUND + 14), fill=(255, 204, 51), outline=NAVY, width=5)
        k = popin(t, 14.5) * (1 - out)
        blit(cv, big('pump', s=12), PUMP_X, GROUND, k, k)
        for td in DROPS:
            dt = t - td
            if 0 <= dt < FALL:
                blit(cv, big('drop', s=8), SPOUT[0], SPOUT[1] + 1500 * dt * dt, anchor='center')
        if t >= 15.15:
            v = 300 + int(prog(t, 15.15, 1.3) * 29) * 10
            kc = popin(t, 15.15) * (1 - out)
            blit(cv, big('dashclock', f'{v // 60}:{v % 60:02d}', '#ff3b3b', s=8), 560, 470, kc, kc, -4, anchor='center')
        if t >= 15.77:
            kw = slam(t, 15.77, 0.13, 1.8) * (1 - out)
            blit(cv, big('badge', 'WASTED', '#e0303a', '#ffffff', '#a82828', s=12), PUMP_X, 800, kw, kw, -8, anchor='center')
            ring(cv, t, 15.77, PUMP_X, 800, (255, 77, 77))
    # finale: thumbs up, 30 SEC badge, confetti
    if t >= end:
        fx, fy = 700, 760
        rays(cv, t, fx, fy, popin(t, end + 0.1, 0.4), col=(214, 247, 222))
        k = popin(t, end + 0.12, 0.32) * (1 + 0.04 * math.sin(t * 7))
        blit(cv, big('badge', '30 SEC', '#3cc85a', '#ffffff', '#1f7a3a', s=11), fx, fy, k, k, -4 + 2 * math.sin(t * 2.4), anchor='center')
        kc = popin(t, end + 0.35)
        blit(cv, big('check', s=13), fx + 190, fy - 150, kc, kc, anchor='center')
        sparkles(cv, t * 1.5, fx, fy, 760, 520, n=14, seed=81)
        confetti(cv, t, end + 0.1, 300, 700, n=46, seed=82)
        confetti(cv, t, end + 0.15, 800, 640, n=40, seed=83, spread=0.9)
    expr = 'shock' if 15.77 <= t < 16.4 else 'smile'
    lift = -140 * math.sin(math.pi * prog(t, end + 0.1, 0.42)) if end + 0.1 <= t < end + 0.52 else 0
    guy(cv, t, 230, expr, lift=lift, poses=[(14.67, 15.1, 'hips'), (15.15, 15.75, 'shrug'), (15.77, 16.4, 'flail'), (end + 0.05, DUR, 'thumb')])

SCENES = [(0.0, scene_hook), (2.95, scene_old), (6.05, scene_modern), (7.55, scene_timer),
          (10.4, scene_drive), (14.55, scene_fuel)]

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
SHAKES = [(0.07, 0.25, 18), (1.83, 0.35, 32), (3.3, 0.3, 24), (6.5, 0.3, 22), (6.88, 0.15, 10), (8.77, 0.3, 22),
          (9.55, 0.2, 10), (15.77, 0.4, 32), (16.67, 0.3, 16)]
PUNCH = [(0.07, 0.6, 1.1, 720, 800), (1.83, 2.5, 1.14, 720, 800), (3.3, 3.95, 1.1, 730, 1050),
         (8.77, 9.45, 1.12, 720, 790), (13.24, 13.9, 1.08, 690, 1000), (15.77, 16.4, 1.12, 760, 800)]
BASE_Z, BASE_A = 1.18, (540, 1000)

def camera(t, idx):
    s0 = SCENES[idx][0]
    z = BASE_Z * (1 + 0.03 * prog(t, s0, 6))
    z *= 1 + 0.22 * (1 - oc(prog(t, 0, 0.4)))  # frame 0 opens zoomed in and snaps out
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
EMPH = {'stop', 'five', 'minutes', 'old', 'carburetor', "don't", 'thirty', 'seconds', 'plenty', 'gently', 'faster', 'idling', 'wastes', 'fuel'}

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
    lines = [('the stupidest', (255, 255, 255)), ('CAR MYTH', (255, 217, 59))]
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
    if t >= 2.95: return
    k = ob(prog(t, -0.12, 0.3)) * (1 - ic(prog(t, 2.65, 0.3)))
    if k <= 0.02: return
    img = title_img()
    rot = 3 * math.sin(t * 4)
    img = img.resize((int(img.width * k), int(img.height * k)), Image.BILINEAR).rotate(rot, resample=Image.BICUBIC, expand=True)
    cv.paste(img, (int(W / 2 - img.width / 2), int(380 - img.height / 2)), img)

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
    (0.0, 'whoosh', 0.9), (0.0, 'boom', 0.5), (0.07, 'stamp', 0.9), (0.1, 'sparkle', 0.8), (0.3, 'pop', 0.6),
    (1.83, 'stamp', 1.0), (1.85, 'buzzer', 0.8), (1.86, 'confetti', 0.5),
    (2.85, 'whoosh', 0.7), (2.95, 'thump', 0.5), (3.15, 'thump', 0.4), (3.3, 'stamp', 1.0), (3.6, 'pop', 0.7),
    (4.59, 'pop', 0.8), (4.7, 'pop', 0.5), (4.6, 'sparkle', 0.6), (5.1, 'poof', 0.8),
    (5.95, 'whoosh', 0.7), (6.12, 'poof', 0.9), (6.15, 'fall', 0.8), (6.5, 'crash', 0.6), (6.55, 'sparkle', 0.8),
    (6.3, 'pop', 0.6), (6.78, 'pop', 0.6), (6.88, 'buzzer', 0.7),
    (7.45, 'whoosh', 0.7), (7.6, 'pop', 0.8), (7.7, 'pop', 0.5),
] + [(7.9 + i * 0.087, 'tick', 0.9) for i in range(10)] + [
    (8.77, 'stamp', 0.9), (8.79, 'ding', 0.6), (9.55, 'ding', 1.0), (9.55, 'sparkle', 0.9), (9.57, 'confetti', 0.8),
    (10.3, 'whoosh', 0.7), (10.49, 'vroom', 0.6), (11.57, 'pop', 0.8), (11.6, 'sparkle', 0.7),
    (12.45, 'pop', 0.7), (12.82, 'rise', 0.9), (13.24, 'whoosh', 0.6), (13.81, 'ding', 0.9),
    (14.45, 'whoosh', 0.7), (14.55, 'pop', 0.8), (15.15, 'pop', 0.6),
] + [(td + FALL, 'drip', 0.5) for td in DROPS[::2]] + [
    (15.77, 'stamp', 1.0), (15.78, 'buzzer', 0.9),
    (16.5, 'whoosh', 0.7), (16.67, 'pop', 0.9), (16.67, 'confetti', 1.0), (16.7, 'ding', 1.0), (16.9, 'pop', 0.6), (16.9, 'sparkle', 1.0),
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
        build_audio(vo, 'mix.wav')
        t0, t1 = (float(sys.argv[4]), float(sys.argv[5])) if len(sys.argv) > 5 else (0.0, DUR)  # optional test range
        frames = range(int(t0 * FPS), int(t1 * FPS))
        ff = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS),
                               '-i', '-', '-ss', str(t0), '-i', 'mix.wav', '-c:v', 'libx264', '-preset', 'medium', '-crf', '17', '-pix_fmt', 'yuv420p',
                               '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', '-shortest', out], stdin=subprocess.PIPE)
        with Pool(4) as pool:
            for i, b in enumerate(pool.imap(frame, frames, chunksize=6)):
                ff.stdin.write(b)
                if i % 300 == 0: print(f'{i}/{len(frames)}', flush=True)
        ff.stdin.close(); ff.wait()
        print('done', ff.returncode)
        raise SystemExit(ff.returncode)
