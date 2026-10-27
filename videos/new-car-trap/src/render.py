"""Renders the 'new car depreciation' TikTok explainer, synced to the voiceover."""
import json, math, os, sys, subprocess
from functools import lru_cache
from multiprocessing import Pool
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import pix, sfx

W, H, FPS, S = 1080, 1920, 60, 9
GROUND = 1180
DUR = 37.9
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
def scene_lot(cv, t):
    cx = 760 + 650 * (1 - oc(prog(t, -0.22, 0.45)))
    bounce = 0
    if 0.23 < t < 0.73:
        p = prog(t, 0.23, 0.5); bounce = 14 * math.sin(p * math.pi * 3) * (1 - p)
    if 6.35 <= t < 6.67: cx = 760 - 22 * oc(prog(t, 6.35, 0.3))
    if 6.67 <= t < 7.92: cx = 738 + 1100 * ic(prog(t, 6.67, 0.75))
    if t >= 7.92: cx = 760 + 1100 * (1 - ob(prog(t, 7.92, 0.38)))
    used = t >= 7.9
    moving = t < 0.23 or 6.67 <= t < 8.3
    if 6.7 <= t < 7.45:
        motion_lines(cv, cx, GROUND, oc(prog(t, 6.7, 0.2)))
    dust(cv, t, 6.67, 600, GROUND - 20, n=12, seed=11, dirx=-500)
    car(cv, t, cx, 'used' if used else 'red', moving, bounce)
    if not used and t > 0.5:
        sparkles(cv, t, cx, GROUND - 120, 480, 220, n=7, seed=2)
        if 0.9 <= t < 1.6: sparkles(cv, t * 2, cx, GROUND - 120, 520, 260, n=10, seed=21)
    # price tag
    ty = GROUND - 216 - 140
    if t >= 3.3:
        dt = t - 3.3
        rot = 9 * math.sin(2 * math.pi * 1.1 * dt) * math.exp(-0.7 * dt) + 2 * math.sin(t * 2.3)
        k = popin(t, 3.3, 0.3)
        if t < 10.43:
            blit(cv, big('tag', '$45,000', s=7), cx, ty, k, k, rot, anchor='center')
        else:
            p = oc(prog(t, 10.43, 0.25))
            blit(cv, big('tag', '$45,000', '#e9e4d8', '#9a9a9a', True, s=7), cx - 90 * p, ty - 150 * p, 1 - 0.25 * p, 1 - 0.25 * p, rot - 6 * p, anchor='center')
            k2 = popin(t, 10.6, 0.3)
            blit(cv, big('tag', '$36,000', '#ffe066', s=7), cx + 30, ty + 10, k2, k2, -6 + rot * 0.5, anchor='center')
    if t >= 8.25:
        k = slam(t, 8.25, 0.13, 1.8)
        blit(cv, big('stamp', 'USED', s=10), cx, GROUND - 110, k, k, 12, anchor='center')
    # guy
    expr = 'smile'
    if 8.25 <= t < 10.43: expr = 'shock'
    elif t >= 10.43: expr = 'sad'
    lift = -150 * math.sin(math.pi * prog(t, 2.2, 0.45)) if 2.2 <= t < 2.65 else 0
    k = 0.4 + 0.6 * popin(t, -0.2, 0.32)
    guy(cv, t, 265, expr, lift=lift, scale=k, poses=[(0.85, 1.9, 'point'), (2.2, 3.0, 'up'), (3.35, 4.9, 'point'), (6.67, 7.7, 'wave')])
    confetti(cv, t, 2.2, 250, 700, n=46, seed=4)
    confetti(cv, t, 2.25, 800, 760, n=30, seed=8, spread=0.8)

BAR1 = (500, 680); BAR2 = (790, 970); BH = 540; SEG = 108
BLUE = ((91, 141, 239), (60, 105, 200), (160, 195, 255))
RED = ((235, 64, 64), (180, 40, 40), (255, 140, 140))

def scene_chart(cv, t):
    g = ob(prog(t, 11.8, 0.45))
    h = BH * g
    block(cv, BAR1[0], GROUND - h, BAR1[1], GROUND, *BLUE)
    seg_alive = t < 15.77
    if seg_alive:
        block(cv, BAR2[0], GROUND - h + SEG * g, BAR2[1], GROUND, *BLUE)
        red = t >= 13.05 or (t >= 12.6 and int(t * 10) % 2 == 0)
        gap = 22 * oc(prog(t, 13.05, 0.15)) if t >= 13.05 else 0
        wob = 6 * math.sin(t * 40) * (1 - prog(t, 13.05, 0.4)) if t >= 13.05 else 0
        block(cv, BAR2[0] + wob, GROUND - h - gap, BAR2[1] + wob, GROUND - h + SEG * g - gap, *(RED if red else BLUE))
    else:
        block(cv, BAR2[0], GROUND - BH + SEG, BAR2[1], GROUND, *BLUE)
        d = ImageDraw.Draw(cv)
        for x in range(BAR2[0], BAR2[1], 2 * S):  # dashed ghost of the lost value
            d.rectangle((x, GROUND - BH, x + S, GROUND - BH + S // 2 + 2), fill=(235, 64, 64))
    shadow(cv, (BAR1[0] + BAR2[1]) / 2, 560)
    kl = popin(t, 11.95)
    blit(cv, big('badge', 'NEW', '#ffffff', '#1a1a2e', '#d6d9e2', s=5), sum(BAR1) / 2, GROUND + 60, kl, kl, anchor='center')
    k = popin(t, 14.49)
    blit(cv, big('badge', 'YEAR 1', '#ffffff', '#1a1a2e', '#d6d9e2', s=5), sum(BAR2) / 2, GROUND + 60, k, k, anchor='center')
    k = popin(t, 12.1)
    blit(cv, big('badge', '$45K', '#ffffff', '#1a1a2e', '#d6d9e2', s=7), sum(BAR1) / 2, GROUND - BH - 70, k, k, anchor='center')
    k = popin(t, 16.2)
    blit(cv, big('badge', '$36K', '#ffe066', '#d6303a', '#e8b923', s=7), sum(BAR2) / 2, GROUND - BH + SEG - 70, k, k, anchor='center')
    if 13.05 <= t < 17.4:
        k = slam(t, 13.05, 0.15, 1.4)
        blit(cv, big('label', '-20%', '#ff3b3b', s=13), 800, 430, k, k, 8 + 2 * math.sin(t * 3), anchor='center')
    # flying money
    if 15.77 <= t < 17.5:
        r = rng_for(12)
        for i in range(22):
            t0 = 15.77 + i * 0.06
            dt = t - t0
            if dt < 0: continue
            vx, vy = r.uniform(-250, 650), r.uniform(-1500, -900)
            x = r.uniform(*BAR2) + vx * dt; y = GROUND - BH + 50 + vy * dt + 0.5 * 1500 * dt * dt
            blit(cv, big('bill', s=7), x, y, 1, 1, r.uniform(-1, 1) * 400 * dt, anchor='center')
    poof(cv, t, 17.44, 860, 520)
    expr = 'smile'
    if 13.05 <= t < 14.3: expr = 'shock'
    elif 15.77 <= t < 17.44: expr = 'shock'
    elif t >= 17.44: expr = 'sad'
    guy(cv, t, 255, expr, poses=[(11.9, 12.7, 'point'), (15.77, 17.44, 'flail')])

def scene_smell(cv, t):
    yoff = 900 * ic(prog(t, 20.46, 0.35))
    if t < 20.85:
        car(cv, t, 760, 'red', bounce=yoff)
        sparkles(cv, t, 760, GROUND - 120 + yoff, 480, 220, n=6, seed=3)
        if t >= 19.59:
            k = slam(t, 19.59, 0.12, 1.6)
            blit(cv, big('xmark', s=16), 760, GROUND - 110 + yoff, k, k, anchor='center')
    if t >= 20.55:
        dt = t - 20.55
        y = -320 + (760 + 320) * ob(prog(t, 20.55, 0.45))
        rot = 14 * math.sin(2 * math.pi * 1.3 * dt) * math.exp(-0.8 * dt)
        if y - 190 > 0:
            ImageDraw.Draw(cv).rectangle((757, 0, 763, y - 190), fill=NAVY)
        smell(cv, t, 21.0, 760, y)
        blit(cv, big('freshener', s=12), 760, y, 1, 1, rot, anchor='center')
        if 21.59 <= t < 22.6:
            sparkles(cv, t * 2.2, 760, y, 420, 460, n=12, seed=7)
        if t >= 23.12:
            k = slam(t, 23.12, 0.13, 1.6)
            blit(cv, big('badge', 'FREE', s=11), 760, y + 40, k, k, -10, anchor='center')
            confetti(cv, t, 23.12, 760, y, n=26, seed=13, spread=0.7)
    expr = 'smile'
    if 19.59 <= t < 20.4: expr = 'shock'
    if 21.0 <= t < 22.4: expr = 'blink'
    guy(cv, t, 255, expr, poses=[(18.59, 19.55, 'shrug'), (20.9, 21.5, 'point'), (21.5, 22.4, 'hips'), (23.12, 23.95, 'up')])

def falling_block(cv, t, t0, t1, cx, land_y):
    """Weight drops from above, landing at land_y (bottom) at time t1."""
    if t < t0: return
    p = prog(t, t0, t1 - t0)
    y = -60 + (land_y + 60) * ic(p)
    blit(cv, big('weight'), cx, y)

def ground_shadow_grow(cv, t, t0, t1, cx):
    if t0 <= t < t1:
        shadow(cv, cx, 80 + 260 * prog(t, t0, t1 - t0))

def scene_dodge(cv, t):
    # blue car arrives after the dodge
    if t >= 25.55:
        cx = 760 + 800 * (1 - oc(prog(t, 25.55, 0.45)))
        car(cv, t, cx, 'blue', moving=t < 26.0)
        if t > 26.0: sparkles(cv, t, cx, GROUND - 120, 480, 220, n=6, seed=5)
        if t >= 26.37:
            k = popin(t, 26.37)
            blit(cv, big('badge', '1-2 YRS OLD', '#bff0c8', '#1f7a3a', '#8fd6a0', s=6), cx, GROUND - 216 - 110, k, k, -4 + 2 * math.sin(t * 2.5), anchor='center')
        if t >= 26.91:
            k = popin(t, 26.91)
            blit(cv, big('check', s=11), cx, GROUND - 216 - 260, k, k, anchor='center')
    ground_shadow_grow(cv, t, 24.2, 24.88, 540)
    if t < 25.55:
        k = 1 - ic(prog(t, 25.3, 0.25))
        if t < 24.88: falling_block(cv, t, 24.5, 24.88, 540, GROUND)
        else: blit(cv, big('weight'), 540, GROUND, k, k)
    dust(cv, t, 24.88, 540, GROUND - 20, n=14, seed=15)
    # guy: centre -> dodge right -> back left
    x, lift = 540, 0
    if t >= 24.62:
        p = prog(t, 24.62, 0.22); x = 540 + 320 * oc(p); lift = -150 * math.sin(math.pi * p)
    if t >= 25.48:
        p = prog(t, 25.48, 0.4); x = 860 - 605 * io(p); lift = -90 * abs(math.sin(math.pi * 2 * p))
    expr = 'shock' if 24.4 <= t < 25.3 else 'smile'
    guy(cv, t, x, expr, lift=lift, poses=[(24.62, 24.95, 'flail'), (25.48, 25.9, 'flail'), (26.37, 26.9, 'point'), (26.91, 27.6, 'up')])

def scene_npc(cv, t):
    car(cv, t, 760, 'red')
    sparkles(cv, t, 760, GROUND - 120, 480, 220, n=6, seed=6)
    ground_shadow_grow(cv, t, 27.85, 28.42, 250)
    sy = 1.0
    if t >= 28.42:
        p = prog(t, 28.42, 0.08); sy = 1 - 0.65 * oc(p)
        sy += 0.06 * math.sin((t - 28.5) * 30) * math.exp(-(t - 28.5) * 6) if t > 28.5 else 0
    expr = 'shock' if t >= 28.15 else 'smile'
    guy(cv, t, 250, expr, sx=1 + (1 - sy) * 0.45, sy=sy, npc=True, poses=[(27.64, 28.1, 'hips')])
    if t < 28.42: falling_block(cv, t, 28.1, 28.42, 250, GROUND - 540)
    else: blit(cv, big('weight'), 250, GROUND - 540 * sy + 10)
    dust(cv, t, 28.45, 250, GROUND - 20, n=16, seed=17)
    if t > 28.55: dizzy(cv, t, 250, GROUND - 540 * sy - 250)

def scene_win(cv, t):
    car(cv, t, 760, 'blue')
    sparkles(cv, t * 1.5, 760, GROUND - 120, 520, 260, n=10, seed=8)
    lift = -130 * math.sin(math.pi * prog(t, 29.59, 0.42)) if 29.59 <= t < 30.01 else 0
    if t >= 29.59:
        r = rng_for(19)
        for i in range(12):
            dt = t - 29.59
            vx, vy = r.uniform(-500, 500), r.uniform(-1500, -900)
            blit(cv, big('coin', s=8), 760 + vx * dt, GROUND - 260 + vy * dt + 0.5 * 2600 * dt * dt, anchor='center')
        k = popin(t, 29.62)
        blit(cv, big('label', '+$9,000', '#3cc85a', s=10), 760, GROUND - 640 - 100 * oc(prog(t, 29.62, 0.8)), k, k, anchor='center')
    guy(cv, t, 255, 'smile', lift=lift, poses=[(29.18, 29.55, 'point'), (29.59, 30.3, 'up')])

def scene_worth(cv, t):
    car(cv, t, 760, 'red')
    sparkles(cv, t, 760, GROUND - 120, 480, 220, n=6, seed=9)
    if 30.69 <= t < 32.3:
        k = popin(t, 30.69) * (1 - ic(prog(t, 32.05, 0.25)))
        blit(cv, big('glyph', '?', '#ff9f1c', s=22), 760, 600 + 14 * math.sin(t * 5), k, k, 6 * math.sin(t * 3), anchor='center')
    if t >= 32.3:
        k = popin(t, 32.3)
        blit(cv, big('tag', '$45,000', s=7), 760, GROUND - 216 - 140, k, k, 3 * math.sin(t * 2.5), anchor='center')
    # coins flowing from guy to car
    for i in range(14):
        t0 = 32.78 + i * 0.065
        dt = t - t0
        if 0 <= dt < 0.45:
            p = dt / 0.45
            x = 400 + (720 - 400) * p; y = 950 + (1000 - 950) * p - 260 * math.sin(math.pi * p)
            blit(cv, big('coin', s=8), x, y, anchor='center')
    ground_shadow_grow(cv, t, 33.5, 34.38, 255)
    sy = 1.0
    if t >= 34.38:
        p = prog(t, 34.38, 0.08); sy = 1 - 0.65 * oc(p)
        sy += 0.06 * math.sin((t - 34.46) * 30) * math.exp(-(t - 34.46) * 6) if t > 34.46 else 0
    expr = 'shock' if t >= 33.9 else 'smile'
    guy(cv, t, 255, expr, sx=1 + (1 - sy) * 0.45, sy=sy, poses=[(30.69, 31.9, 'shrug'), (32.78, 33.7, 'point')])
    if t < 34.38: falling_block(cv, t, 34.05, 34.38, 255, GROUND - 540)
    else: blit(cv, big('weight'), 255, GROUND - 540 * sy + 10)
    dust(cv, t, 34.4, 255, GROUND - 20, n=16, seed=23)
    if t > 34.5: dizzy(cv, t, 255, GROUND - 540 * sy - 250)

def scene_cta(cv, t):
    k = popin(t, 35.29)
    bx, by = 740, 760
    nd = 1 + int(t * 4) % 3
    blit(cv, big('bubble', nd, s=10), bx, by, k, k, anchor='center')
    if t >= 35.8:
        kh = popin(t, 35.8) * (1 + 0.08 * math.sin(t * 9))
        blit(cv, big('heart', s=9), bx + 150, by - 120, kh, kh, anchor='center')
    if t >= 36.12:
        ka = popin(t, 36.12)
        blit(cv, big('arrow', s=10), bx, 1010 + 22 * abs(math.sin(t * 6)), ka, ka, anchor='center')
    lift = -110 * math.sin(math.pi * prog(t, 35.25, 0.4)) if 35.25 <= t < 35.65 else 0
    guy(cv, t, 270, 'smile', lift=lift, poses=[(35.25, 35.95, 'wave'), (36.12, 37.9, 'pointup')])

SCENES = [(0.0, scene_lot), (11.62, scene_chart), (18.48, scene_smell), (24.02, scene_dodge),
          (27.58, scene_npc), (29.12, scene_win), (30.45, scene_worth), (35.22, scene_cta)]
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
SHAKES = [(4.96, 0.2, 10), (8.3, 0.3, 26), (13.05, 0.35, 30), (19.59, 0.2, 14), (23.12, 0.2, 12),
          (24.88, 0.4, 34), (28.45, 0.45, 40), (34.4, 0.45, 40)]
PUNCH = [(3.65, 4.96, 1.3, 760, 840), (13.05, 13.6, 1.07, 660, 760), (20.9, 21.9, 1.1, 620, 820)]
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
EMPH = {'new', 'used', 'less', 'twenty', 'percent', 'thousands', 'gone', 'smell', 'free', 'dodge', 'old', 'hit', 'extra', 'worth', 'comments', 'congrats'}

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
    lines = [('the new car', (255, 255, 255)), ('TRAP', (255, 90, 90))]
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
    if t >= 3.5: return
    k = ob(prog(t, -0.2, 0.3)) * (1 - ic(prog(t, 3.1, 0.3)))
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
    (0.0, 'whoosh', 0.8), (0.05, 'pop', 0.7), (0.9, 'sparkle', 0.9), (2.2, 'confetti', 1.0), (2.22, 'pop', 0.6),
    (3.3, 'pop', 0.7), (3.9, 'ding', 0.9), (4.96, 'thump', 0.9), (6.55, 'vroom', 1.0), (7.85, 'screech', 1.0),
    (8.25, 'stamp', 1.0), (10.43, 'slide_down', 1.0), (10.6, 'pop', 0.6),
    (11.52, 'whoosh', 0.6), (11.8, 'pop', 0.6), (12.1, 'pop', 0.4), (13.05, 'boom', 1.0), (14.49, 'pop', 0.6),
    (15.77, 'whoosh', 0.7), (16.05, 'whoosh', 0.5), (16.2, 'pop', 0.5), (17.44, 'poof', 1.0),
    (18.38, 'whoosh', 0.6), (19.59, 'buzzer', 1.0), (20.46, 'whoosh', 0.6), (20.9, 'pop', 0.5), (21.59, 'sparkle', 1.0),
    (23.12, 'stamp', 0.7), (23.14, 'ding', 0.8),
    (23.92, 'whoosh', 0.6), (24.5, 'fall', 1.0), (24.62, 'whoosh', 0.5), (24.88, 'crash', 1.0),
    (25.55, 'whoosh', 0.6), (26.37, 'pop', 0.6), (26.91, 'ding', 0.9),
    (27.48, 'whoosh', 0.6), (28.1, 'fall', 1.0), (28.45, 'crash', 1.0),
    (29.02, 'whoosh', 0.6), (29.59, 'cha_ching', 1.0),
    (30.35, 'whoosh', 0.6), (30.69, 'pop', 0.7), (32.3, 'pop', 0.5),
] + [(32.78 + i * 0.13 + 0.45, 'coin', 0.9) for i in range(7)] + [
    (34.05, 'fall', 1.0), (34.4, 'crash', 1.0),
    (35.12, 'whoosh', 0.6), (35.29, 'pop', 0.8), (35.8, 'pop', 0.6), (36.12, 'pop', 0.7),
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
        N = int(DUR * FPS)
        ff = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS),
                               '-i', '-', '-i', 'mix.wav', '-c:v', 'libx264', '-preset', 'medium', '-crf', '17', '-pix_fmt', 'yuv420p',
                               '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', '-shortest', out], stdin=subprocess.PIPE)
        with Pool(4) as pool:
            for i, b in enumerate(pool.imap(frame, range(N), chunksize=6)):
                ff.stdin.write(b)
                if i % 300 == 0: print(f'{i}/{N}', flush=True)
        ff.stdin.close(); ff.wait()
        print('done', ff.returncode)
        raise SystemExit(ff.returncode)
