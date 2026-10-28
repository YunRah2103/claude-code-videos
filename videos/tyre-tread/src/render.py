"""Renders the 'why tyres have tread' TikTok explainer, synced to the voiceover."""
import json, math, os, sys, subprocess
from functools import lru_cache
from multiprocessing import Pool
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import pix, sfx

W, H, FPS, S = 1080, 1920, 60, 9
GROUND = 1180
DUR = 16.2
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
    i = np.searchsorted(WSTART, t, side='right') - 1
    if sx == 1 and sy == 1 and i >= 0 and t - WSTART[i] < 0.16:
        q = math.sin(math.pi * (t - WSTART[i]) / 0.16); sy, sx = 1 + 0.05 * q, 1 - 0.025 * q
    pose = pick_pose(t, expr, poses) if sy > 0.9 else 'down'
    blit(cv, big_guy(face(t, expr), npc, pose), cx, GROUND + lift + b, sx * scale, sy * scale)

def car(cv, t, cx, color, moving=False, bounce=0.0, sx=1.0):
    phase = int(t * 24) % 2 if moving else 0
    shadow(cv, cx, 440 * sx)
    blit(cv, big('car', color, phase), cx, GROUND + bounce, sx, sx)

# ------------------------------------------------------------------ scenes
TX = 740  # prop column, right of the guy
WATER, WATER_HI = (90, 169, 255), (191, 227, 255)
RUBBER = ((52, 53, 62), (36, 37, 44), (84, 87, 99))
TREAD_TOP = GROUND - 52 * 12
GROOVES = (TX - 60, TX + 72)  # centre x of the two tread grooves at s=12

def droplet(d, x, y, sz=S):
    d.rectangle((x - sz - 3, y - sz - 3, x + sz + 3, y + sz + 3), fill=NAVY)
    d.rectangle((x - sz, y - sz, x + sz, y + sz), fill=WATER)
    d.rectangle((x - sz, y - sz, x - sz + 5, y - sz + 5), fill=WATER_HI)

def clouds(cv, t, t0):
    if t < t0: return
    y = -260 + 590 * oc(prog(t, t0, 0.5))
    blit(cv, big('cloud', s=10), 290, y + 10 * math.sin(t * 1.5), anchor='center')
    blit(cv, big('cloud', s=12), 790, y - 40 + 8 * math.sin(t * 1.2 + 1), anchor='center')

def rain(cv, t, t0, n=30, seed=31):
    if t < t0: return
    r = rng_for(seed); img = big('drop', s=6); d = ImageDraw.Draw(cv)
    top, span = 400, GROUND - 400
    for i in range(int(n * min(1, (t - t0) / 0.5))):
        x = r.uniform(70, 1010); sp = r.uniform(1500, 2000); ph = r.uniform(0, 1)
        q = (t * sp / span + ph) % 1
        if q > 0.94:  # tiny splash where it lands
            k = (q - 0.94) / 0.06
            for sgn in (-1, 1):
                d.rectangle((x + sgn * 40 * k - 6, GROUND - 30 - 30 * k, x + sgn * 40 * k + 6, GROUND - 18 - 30 * k), fill=WATER)
        else:
            blit(cv, img, x, top + q / 0.94 * span, anchor='center')

def puddle(cv, t, x0, x1, k=1.0, gap=None):
    """Water sheet on the road; `gap` is a dry span (a, b)."""
    hgt = int(3 * S * k)
    if hgt < S: return
    d = ImageDraw.Draw(cv)
    spans = [(x0, x1)] if not gap else [(x0, gap[0]), (gap[1], x1)]
    for a, b in spans:
        if b - a < 3 * S: continue
        d.rectangle((a, GROUND - hgt, b, GROUND + S), fill=NAVY)
        d.rectangle((a + 4, GROUND - hgt + 4, b - 4, GROUND + S - 4), fill=WATER)
        for xx in range(int(a) + 2 * S, int(b) - 4 * S, 8 * S):
            o = int(t * 4 + xx / 50) % 3 * S
            d.rectangle((xx + o, GROUND - hgt + 4, xx + o + 3 * S, GROUND - hgt + 4 + S), fill=WATER_HI)

def tread_front(cv, t, cx, worn=False, lift=0.0, k=1.0, rot=0.0):
    if k < 0.1: return
    shadow(cv, cx, 420 * k)
    blit(cv, big('tread', worn, s=12), cx, GROUND + lift, k, k, rot)

def scene_hook(cv, t):
    cy = GROUND - 253
    cx = TX + 760 * (1 - oc(prog(t, -0.15, 0.5)))
    bounce = 0
    if 0.35 < t < 0.85:
        p = prog(t, 0.35, 0.5); bounce = -40 * abs(math.sin(p * math.pi * 2)) * (1 - p)
    shadow(cv, cx, 380)
    xk = 0 if t < 2.05 else 1 - ic(prog(t, 2.5, 0.2))
    tyre_y = cy + bounce
    blit(cv, big('tyre', False, int((cx - TX) / 300 * 18) % 18, s=11), cx, tyre_y, anchor='center')
    if t > 0.6: sparkles(cv, t, cx, tyre_y, 520, 520, n=6, seed=2)
    # arrows pointing at the grooves
    for t0, ax, ay, rot in ((0.33, TX - 250, cy - 250, 40), (0.45, TX + 250, cy - 250, -40)):
        if t0 <= t < 2.05:
            k = popin(t, t0) * (1 - ic(prog(t, 1.85, 0.2)))
            bobd = 22 * abs(math.sin(t * 6))
            blit(cv, big('arrow', s=9), ax - math.copysign(bobd, rot) * 0.7, ay + bobd * 0.7, k, k, rot, anchor='center')
    # stickers that make it 'decoration' ... then get crossed out
    stick = (('heart', (), 1.40, -130, -110, 10), ('star', (), 1.55, 140, -40, 12), ('sparkle', (1,), 1.70, -40, 120, 11))
    for name, args, t0, dx, dy, sc in stick:
        if t0 <= t < 2.1:
            k = popin(t, t0) * (1 + 0.1 * math.sin(t * 9))
            blit(cv, big(name, *args, s=sc), cx + dx, tyre_y + dy, k, k, 8 * math.sin(t * 4 + dx), anchor='center')
        poof(cv, t, 2.1, cx + dx, tyre_y + dy, seed=int(t0 * 10))
    if 2.05 <= t and xk > 0:
        k = slam(t, 2.05, 0.13, 1.7) * xk
        blit(cv, big('xmark', s=18), cx, tyre_y, k, k, anchor='center')
    expr = 'shock' if 2.05 <= t < 2.45 else 'smile'
    k = 0.4 + 0.6 * popin(t, -0.15, 0.32)
    guy(cv, t, 255, expr, scale=k, poses=[(0.3, 1.3, 'point'), (1.33, 2.0, 'shrug'), (2.05, 2.45, 'shock')])

def scene_rain(cv, t):
    clouds(cv, t, 2.7)
    dry = oc(prog(t, 4.36, 0.9))
    half = 200 * dry
    puddle(cv, t, 80, 1010, oc(prog(t, 2.95, 0.6)), gap=(TX - half, TX + half) if half > 3 * S else None)
    push = 0
    if 6.19 <= t < 6.6:
        push = 22 * math.sin(math.pi * prog(t, 6.19, 0.4))
    k = popin(t, 2.95, 0.3)
    tread_front(cv, t, TX, k=k, lift=push)
    # water running up the grooves and spraying out
    d = ImageDraw.Draw(cv)
    if 4.02 <= t < 5.9:
        fade_k = 1 - prog(t, 5.6, 0.3)
        hgt = (GROUND - TREAD_TOP - 40) * oc(prog(t, 4.02, 0.35)) * fade_k
        for gx in GROOVES if hgt > 20 else ():
            d.rectangle((gx - 10, GROUND - hgt, gx + 10, GROUND - 10), fill=WATER)
            for yy in range(0, int(hgt), 70):
                yv = GROUND - 20 - (yy + t * 700) % max(1, hgt)
                d.rectangle((gx - 5, yv - 18, gx + 5, yv), fill=WATER_HI)
    for i in range(36):
        t0 = 4.02 + i * 0.05
        dt = t - t0
        if dt < 0 or dt > 1.0: continue
        gi = i % 2; gx = GROOVES[gi]; side = -1 if gi == 0 else 1
        ytop = GROUND - 180 - (i // 2 % 4) * 100
        if dt < 0.25:
            droplet(d, gx, GROUND - 30 - (GROUND - 30 - ytop) * oc(dt / 0.25), S)
        else:
            u = dt - 0.25
            x = gx + side * (240 + 900 * u); y = ytop - 520 * u + 1300 * u * u
            droplet(d, x, y, S + (i % 3) * 3)
    if t >= 6.19:
        kc = slam(t, 6.19, 0.13, 1.6)
        blit(cv, big('badge', 'GRIP', '#bff0c8', '#1f7a3a', '#8fd6a0', s=11), TX, TREAD_TOP - 90, kc, kc, -6 + 3 * math.sin(t * 3), anchor='center')
        kk = popin(t, 6.3)
        blit(cv, big('check', s=11), TX + 150, TREAD_TOP - 200, kk, kk, anchor='center')
        for sgn in (-1, 1):  # grip marks
            if t < 6.8:
                p = prog(t, 6.19, 0.5)
                d.rectangle((TX + sgn * (220 + 80 * p) - 25, GROUND - 14, TX + sgn * (220 + 80 * p) + 25, GROUND - 4), fill=(190, 190, 200))
    rain(cv, t, 2.96)
    expr = 'shock' if 2.96 <= t < 3.3 else 'smile'
    guy(cv, t, 255, expr, poses=[(2.96, 3.4, 'up'), (4.0, 5.3, 'point'), (6.19, 6.95, 'up')])

def scene_worn(cv, t):
    clouds(cv, t, 0)
    puddle(cv, t, 80, 1010)
    lift = 0
    if t >= 8.08:  # water can't escape: the bald tyre floats on it
        lift = -(46 + 10 * math.sin((t - 8.08) * 9)) * oc(prog(t, 8.08, 0.3))
    cx = TX + 760 * (1 - oc(prog(t, 7.4, 0.35)))
    if lift:
        ImageDraw.Draw(cv).rectangle((cx - 190, GROUND + lift - 4, cx + 190, GROUND), fill=WATER, outline=NAVY, width=4)
    tread_front(cv, t, cx, worn=True, lift=lift, rot=3 * math.sin((t - 8.08) * 5) if lift else 0)
    if t >= 7.72:
        k = slam(t, 7.72, 0.13, 1.8)
        blit(cv, big('stamp', 'BALD', s=12), cx, GROUND - 330, k, k, 12, anchor='center')
    d = ImageDraw.Draw(cv)
    for i in range(10):  # water bounces off the smooth rubber
        dt = t - (8.08 + i * 0.05)
        if 0 <= dt < 0.45:
            side = -1 if i % 2 else 1
            droplet(d, cx + side * (120 + 300 * dt), GROUND - 40 - 380 * dt + 900 * dt * dt, S)
    if t >= 8.31:
        k = slam(t, 8.31, 0.13, 1.6)
        blit(cv, big('xmark', s=14), cx + 230, TREAD_TOP - 60, k, k, anchor='center')
    rain(cv, t, 0)
    expr = 'sad' if t >= 7.44 else 'smile'
    guy(cv, t, 255, expr, poses=[(7.44, 7.9, 'point')])

def scene_slide(cv, t):
    clouds(cv, t, 0)
    puddle(cv, t, 80, 1010)
    d = ImageDraw.Draw(cv)
    cx = TX - 20 + 800 * (1 - oc(prog(t, 8.9, 0.4)))
    rot = 0
    if t >= 9.62:
        u = t - 9.62
        amp = min(1, u / 0.3) * (1 - prog(t, 10.5, 0.4))
        rot = 14 * math.sin(2 * math.pi * 1.3 * u) * amp
        cx += 50 * math.sin(2 * math.pi * 0.65 * u) * amp
        for j in range(5):  # skid streaks left behind
            xx = TX - 230 + j * 40 + 15 * math.sin(j * 2.1)
            d.rectangle((xx, GROUND - 8, xx + 26, GROUND), fill=(60, 62, 72))
        r = rng_for(int(t * 20))  # spray off the wheels
        for i in range(6):
            droplet(d, cx + r.uniform(-260, 260), GROUND - r.uniform(30, 220), S + int(r.uniform(0, 6)))
    shadow(cv, cx, 440)
    blit(cv, big('car', 'red', int(t * 24) % 2 if t < 9.3 else 0), cx, GROUND - 8, 1, 1, rot)
    if t >= 9.95:
        k = slam(t, 9.95, 0.13, 1.7)
        blit(cv, big('label', 'SLIDE!', '#ff3b3b', s=12), TX - 60, 620, k, k, -8 + 3 * math.sin(t * 7), anchor='center')
    rain(cv, t, 0)
    expr = 'shock' if t >= 9.62 else 'sad'
    guy(cv, t, 255, expr, poses=[(9.62, 10.85, 'flail')])

SLAB = (500, 960); GW = 90; BASE = 90; MMPX = 56

def slab(cv, mm, coin_draw=None):
    """Tread cross-section: 3 rubber lugs with 2 grooves, `mm` deep."""
    lug = (SLAB[1] - SLAB[0] - 2 * GW) / 3
    top = GROUND - BASE - mm * MMPX
    if coin_draw: coin_draw(top)
    for i in range(3):
        x0 = SLAB[0] + i * (lug + GW)
        block(cv, x0, top, x0 + lug, GROUND - BASE + S * 2, *RUBBER)
    block(cv, SLAB[0], GROUND - BASE, SLAB[1], GROUND, *RUBBER)
    shadow(cv, sum(SLAB) / 2, SLAB[1] - SLAB[0] + 40)
    return top, [SLAB[0] + lug + GW / 2, SLAB[0] + 2 * lug + 1.5 * GW]

def scene_gauge(cv, t):
    mm = 8 - 6.4 * io(prog(t, 11.2, 1.41))
    top, grooves = slab(cv, mm)
    d = ImageDraw.Draw(cv)
    if 11.2 <= t < 12.61:
        dust(cv, t, 11.2 + int((t - 11.2) * 6) / 6, sum(SLAB) / 2, top - 10, n=8, seed=int(t * 6), life=0.4)
    line_y = GROUND - BASE - 1.6 * MMPX
    if t >= 11.66 and (t >= 11.95 or int(t * 12) % 2 == 0):
        for x in range(SLAB[0] - 50, SLAB[1] + 40, 3 * S):
            d.rectangle((x, line_y - 4, x + 2 * S, line_y + 4), fill=(235, 64, 64))
    if t >= 11.93:
        k = popin(t, 11.93)
        blit(cv, big('badge', 'LEGAL MIN', '#ffffff', '#d6303a', '#d6d9e2', s=7), sum(SLAB) / 2, 650, k, k, anchor='center')
    # depth readout
    hit = t >= 12.61
    txt = f'{mm:.1f}MM'
    k = popin(t, 10.95) * (slam(t, 12.61, 0.14, 1.5) if hit else 1)
    col = ('#ffe066', '#d6303a', '#e8b923') if hit else ('#ffffff', '#1a1a2e', '#d6d9e2')
    blit(cv, big('badge', txt, *col, s=12), sum(SLAB) / 2, 500, k, k, (-6 if hit else 0) + 2 * math.sin(t * 3), anchor='center')
    # arrow into the groove shows the depth being measured
    gx = grooves[0]
    blit(cv, big('arrow', s=6), gx, top - 70 + 14 * abs(math.sin(t * 6)), anchor='center')
    expr = 'shock' if 12.61 <= t < 13.1 else 'smile'
    guy(cv, t, 255, expr, poses=[(10.94, 11.9, 'point'), (12.61, 13.2, 'up')])

def scene_coin(cv, t):
    mm = 4.0
    t_land = 14.4
    def coin_draw(top):
        gx = slab_grooves[0]
        bottom = GROUND - BASE
        if t < 14.05: return
        p = prog(t, 14.05, t_land - 14.05)
        y = -200 + (bottom - 99 + 200) * ic(p)
        if t >= t_land: y = bottom - 99 - 14 * math.sin(math.pi * prog(t, t_land, 0.12))
        sx = abs(math.cos((t - 14.05) * 14)) if t < t_land else 1
        blit(cv, big('coin', s=18), gx, y, max(0.15, sx), 1, anchor='center')
    lug = (SLAB[1] - SLAB[0] - 2 * GW) / 3
    slab_grooves = [SLAB[0] + lug + GW / 2]
    top, _ = slab(cv, mm, coin_draw)
    if t >= 14.6:
        k = popin(t, 14.6)
        blit(cv, big('check', s=12), SLAB[1] - 40, top - 170, k, k, anchor='center')
        sparkles(cv, t * 1.6, slab_grooves[0], top - 60, 360, 240, n=10, seed=8)
        confetti(cv, t, 14.6, 720, 700, n=40, seed=4)
    lift = -120 * math.sin(math.pi * prog(t, 14.6, 0.42)) if 14.6 <= t < 15.02 else 0
    guy(cv, t, 255, 'smile', lift=lift, poses=[(13.95, 14.55, 'point'), (14.6, 15.3, 'up'), (15.3, 16.3, 'wave')])

SCENES = [(0.0, scene_hook), (2.7, scene_rain), (7.35, scene_worn), (8.9, scene_slide),
          (10.85, scene_gauge), (13.9, scene_coin)]
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
SHAKES = [(0.35, 0.25, 22), (2.05, 0.25, 20), (2.85, 0.3, 14), (6.19, 0.3, 24), (7.72, 0.3, 26), (8.31, 0.25, 18),
          (9.95, 0.45, 34), (12.61, 0.35, 30), (14.4, 0.25, 16)]
PUNCH = [(4.02, 5.6, 1.12, 700, 1000), (9.6, 10.6, 1.08, 760, 1000), (12.61, 13.5, 1.1, 720, 760)]
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
    if t < 1.0:  # hook: open tight on the tyre, then pull out to the guy
        k = 1 - io(prog(t, 0.1, 0.85))
        z *= 1 + 0.5 * k; ax += (TX - ax) * k; ay += (930 - ay) * k
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
EMPH = {'grooves', 'decoration', 'rain', 'water', 'grip', 'worn', "can't", 'slide', 'legal', 'minimum', '1.6', 'millimetres'}

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
    w = w.lower().rstrip('.,!')
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
def title_img(lines=(('why do tyres', (255, 255, 255)), ('HAVE GROOVES?', (255, 217, 59)))):
    img = Image.new('RGBA', (1000, 260), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for i, (txt, col) in enumerate(lines):
        f = TFONT if i == 0 else font(118)
        w = d.textlength(txt, font=f)
        y = 0 if i == 0 else 100
        d.text((500 - w / 2 + 6, y + 8), txt, font=f, fill=NAVY, stroke_width=14, stroke_fill=NAVY)
        d.text((500 - w / 2, y), txt, font=f, fill=col, stroke_width=13, stroke_fill=(10, 10, 16))
    return img

def title(cv, t):
    if t >= 2.7: return
    k = ob(prog(t, 0.1, 0.3)) * (1 - ic(prog(t, 2.35, 0.3)))
    if k <= 0.02: return
    img = title_img()
    rot = 3 * math.sin(t * 4)
    img = img.resize((int(img.width * k), int(img.height * k)), Image.BILINEAR).rotate(rot, resample=Image.BICUBIC, expand=True)
    cv.paste(img, (int(W / 2 - img.width / 2), int(380 - img.height / 2)), img)

END = (('check yours', (255, 255, 255)), ('WITH A COIN', (255, 217, 59)))

def end_card(cv, t):
    if t < 14.0: return
    k = ob(prog(t, 14.0, 0.3)) * (1 + 0.04 * math.sin(t * 7))
    if k <= 0.02: return
    img = title_img(END)
    img = img.resize((int(img.width * k), int(img.height * k)), Image.BILINEAR).rotate(3 * math.sin(t * 4), resample=Image.BICUBIC, expand=True)
    cv.paste(img, (int(W / 2 - img.width / 2), int(1450 - img.height / 2)), img)

def captions(cv, t):
    if t >= 14.0: return  # end card takes over
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
    end_card(cv, t)
    return cv.tobytes()

CUES = [
    (0.0, 'whoosh', 0.8), (0.35, 'thump', 1.0), (0.33, 'pop', 0.6), (0.45, 'pop', 0.5),
    (1.40, 'pop', 0.6), (1.55, 'sparkle', 0.8), (1.70, 'pop', 0.6), (2.05, 'buzzer', 0.9), (2.1, 'poof', 0.7),
    (2.6, 'whoosh', 0.6), (2.85, 'thunder', 0.9), (2.9, 'rain', 0.6), (2.95, 'pop', 0.5),
    (4.02, 'splash', 1.0), (4.4, 'splash', 0.8), (4.8, 'splash', 0.8), (5.2, 'splash', 0.6),
    (6.19, 'stamp', 0.9), (6.21, 'ding', 0.8),
    (7.25, 'whoosh', 0.6), (7.72, 'stamp', 1.0), (8.08, 'splash', 0.7), (8.31, 'buzzer', 0.9),
    (8.8, 'whoosh', 0.6), (8.9, 'vroom', 0.7), (9.62, 'skid', 1.0), (9.95, 'splash', 0.9), (9.97, 'thunder', 0.7),
    (10.75, 'whoosh', 0.6), (10.95, 'pop', 0.6), (11.2, 'slide_down', 0.6), (11.66, 'pop', 0.5), (11.93, 'pop', 0.5),
    (12.61, 'stamp', 1.0), (12.63, 'ding', 0.9),
    (13.8, 'whoosh', 0.6), (14.0, 'pop', 0.7), (14.05, 'fall', 0.8), (14.4, 'coin', 1.2), (14.42, 'thump', 0.5),
    (14.6, 'ding', 0.9), (14.6, 'confetti', 0.8),
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
                               '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11', '-ar', '48000', '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', '-shortest', out], stdin=subprocess.PIPE)
        with Pool(4) as pool:
            for i, b in enumerate(pool.imap(frame, range(N), chunksize=6)):
                ff.stdin.write(b)
                if i % 300 == 0: print(f'{i}/{N}', flush=True)
        ff.stdin.close(); ff.wait()
        print('done', ff.returncode)
        raise SystemExit(ff.returncode)
