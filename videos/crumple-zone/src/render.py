"""Renders the 'why your car is built to crumple' TikTok explainer, synced to the voiceover."""
import json, math, os, sys, subprocess
from functools import lru_cache
from multiprocessing import Pool
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import pix, sfx

W, H, FPS, S = 1080, 1920, 60, 9
GROUND = 1180
DUR = 24.4
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

def shadow(cv, cx, w, k=1.0, y=GROUND):
    if k <= 0: return
    d = ImageDraw.Draw(cv)
    w = w * k
    d.rectangle((cx - w / 2 + S, y - S, cx + w / 2 - S, y + S), fill=(236, 236, 242))
    d.rectangle((cx - w / 2, y - S // 2, cx + w / 2, y + S // 2), fill=(236, 236, 242))

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


# ------------------------------------------------------------------ crash props
WALL_X = 870                       # wall face; crashing cars stop here
LANE_A = 760                       # ground line of the upper lane in the two-car test

def wall(cv, y0, y1=GROUND, x0=WALL_X, x1=WALL_X + 96):
    if y1 < 0: return
    block(cv, x0, y0, x1, y1, (172, 178, 190), (142, 148, 162), (208, 213, 222))
    d = ImageDraw.Draw(cv)
    for i, y in enumerate(range(int(y0) + 70, int(y1) - 20, 64)):   # concrete blocks
        d.rectangle((x0 + S, y, x1 - S, y + 5), fill=(120, 126, 140))
        xm = x0 + (30 if i % 2 else 62)
        d.rectangle((xm, y - 59, xm + 5, y), fill=(120, 126, 140))
    for i in range(6):                                              # hazard stripe cap
        c = (255, 210, 63) if i % 2 == 0 else NAVY
        d.rectangle((x0 + S, y0 + S + i * 9, x1 - S, y0 + S + i * 9 + 8), fill=c)

def drop_wall(cv, t, t0, t1, y_top):
    """Wall falls in from above, landing at time t1."""
    if t < t0: return
    h = GROUND - y_top
    y = y_top - (y_top + h) * (1 - ic(prog(t, t0, t1 - t0)))
    wall(cv, y, y + h)
    dust(cv, t, t1, WALL_X + 48, GROUND - 20, n=14, seed=21)

def crash_car(cv, t, color, front, ground, k=0.0, s=10, sc=1.0, rot=0.0, moving=False):
    """Draws a car whose bumper is at x=front; returns (left, top) of the unscaled car."""
    phase = int(t * 24) % 2 if moving else 0
    img = big('crushed', color, round(k * 10) / 10, phase, s=s)
    left = front - img.width
    if sc <= 0.01: return None
    shadow(cv, left + img.width / 2, img.width * 0.92 * sc, y=ground)
    blit(cv, img, left + img.width / 2, ground, sc, sc, rot)
    return left, ground - img.height

def speed_lines(cv, front, ground, s, k=1.0):
    d = ImageDraw.Draw(cv)
    for i, (dy, ln) in enumerate(((-15, 220), (-10, 150), (-4, 260))):
        x1 = front - 52 * s - 30 - i * 25
        y = ground + dy * s
        d.rectangle((x1 - ln * k, y, x1, y + S), fill=(190, 190, 200))

def burst(cv, t, t0, x, y, r=190):
    dt = t - t0
    if dt < 0 or dt > 0.3: return
    k = oc(min(1, dt / 0.08)) * (1 - ic(prog(dt, 0.16, 0.14)))
    if k <= 0.02: return
    d = ImageDraw.Draw(cv)
    for rr, col in ((r * k, (255, 210, 63)), (r * k * 0.55, (255, 255, 255))):
        pts = []
        for i in range(20):
            a = i / 20 * 2 * math.pi + t0
            q = rr if i % 2 == 0 else rr * 0.5
            pts.append((x + math.cos(a) * q, y + math.sin(a) * q))
        d.polygon(pts, fill=col, outline=NAVY, width=7)

def debris(cv, t, t0, x, y, n=18, seed=7, cols=((58, 59, 68), (205, 210, 220), (232, 52, 63), (191, 227, 245))):
    dt = t - t0
    if dt < 0 or dt > 1.3: return
    r = rng_for(seed); d = ImageDraw.Draw(cv)
    for i in range(n):
        vx, vy = r.uniform(-950, -120), r.uniform(-1250, -300)
        px = x + vx * dt; py = y + vy * dt + 0.5 * 2800 * dt * dt
        if py > GROUND: continue
        sz = S * (1 + i % 2)
        d.rectangle((px - sz, py - sz, px + sz, py + sz), fill=cols[i % len(cols)], outline=NAVY, width=4)

def smoke(cv, t, t0, x, y, n=4, rise=280, grey=(214, 214, 222)):
    if t < t0: return
    d = ImageDraw.Draw(cv)
    for i in range(n):
        ph = ((t - t0) * 0.8 + i / n) % 1
        px = x + 26 * math.sin((t + i) * 3) + (i - n / 2) * 18
        py = y - ph * rise
        rad = (16 + 46 * ph) * min(1, (t - t0) * 4)
        d.ellipse((px - rad, py - rad, px + rad, py + rad), fill=grey, outline=NAVY, width=5)

def dashed_box(cv, x0, y0, x1, y1, col, w=8, dash=28):
    d = ImageDraw.Draw(cv)
    for x in range(int(x0), int(x1), dash * 2):
        d.rectangle((x, y0, min(x + dash, x1), y0 + w), fill=col); d.rectangle((x, y1 - w, min(x + dash, x1), y1), fill=col)
    for y in range(int(y0), int(y1), dash * 2):
        d.rectangle((x0, y, x0 + w, min(y + dash, y1)), fill=col); d.rectangle((x1 - w, y, x1, min(y + dash, y1)), fill=col)

CAGE = [((8, 11), (43, 11)), ((10, 11), (16, 4)), ((16, 4), (33, 4)), ((33, 4), (41, 11)), ((27, 4), (27, 11))]

def cage(cv, left, top, s, k):
    """Steel safety cage snapping onto the cabin, one bar at a time as k goes 0..1."""
    d = ImageDraw.Draw(cv)
    for i, ((ax, ay), (bx, by)) in enumerate(CAGE):
        if k < i / len(CAGE): break
        p = [(left + ax * s, top + ay * s), (left + bx * s, top + by * s)]
        d.line(p, fill=NAVY, width=30); d.line(p, fill=(206, 212, 224), width=16)
        for (px, py) in p:
            d.rectangle((px - 14, py - 14, px + 14, py + 14), fill=(150, 158, 176), outline=NAVY, width=5)

def passenger(cv, left, top, s, k=1.0, dy=0.0):
    if k > 0.02:
        blit(cv, big('mini_head', s=4), left + 32 * s, top + 10 * s + dy, k, k)

def bolts(cv, t, t0, t1, x0, x1, y, seed=31, every=0.11):
    """Energy bolts flying from the wall (x0) into the crumple zone (x1), shrinking as they are absorbed."""
    r = rng_for(seed)
    for i in range(int((t1 - t0) / every)):
        st = t0 + i * every; dy = r.uniform(-90, 70)
        dt = t - st
        if not 0 <= dt < 0.42: continue
        p = dt / 0.42
        x = x0 + (x1 - x0) * oc(min(1, p * 1.4)); k = 1 - ic(prog(p, 0.55, 0.45))
        blit(cv, big('bolt', s=7), x, y + dy, k, k, 15 * math.sin(st * 9), anchor='center')
        if p > 0.6: blit(cv, big('sparkle', 1, s=7), x - 20, y + dy, anchor='center')

# ------------------------------------------------------------------ scenes
TI = 0.30                           # hook impact

def scene_hook(cv, t):
    wall(cv, GROUND - 640)
    front = 260 + (WALL_X - 260) * prog(t, 0, TI) if t < TI else WALL_X - 34 * math.sin(math.pi * prog(t, TI, 0.3))
    k = oc(prog(t, TI, 0.2))
    rot = -3.5 * math.sin(math.pi * prog(t, TI, 0.36)) if t >= TI else 0
    if t < TI: speed_lines(cv, front, GROUND, 10, oc(prog(t, 0, 0.12)))
    left, top = crash_car(cv, t, 'red', front, GROUND, k, rot=rot, moving=t < TI)
    smoke(cv, t, 0.5, WALL_X - 40, top + 80, n=4)
    debris(cv, t, TI, WALL_X - 20, GROUND - 120, n=22, seed=3)
    dust(cv, t, TI, WALL_X - 30, GROUND - 20, n=14, seed=11, dirx=-450)
    burst(cv, t, TI, WALL_X, GROUND - 130)
    if TI < t < 1.0: sparkles(cv, t * 2, WALL_X - 60, GROUND - 130, 220, 200, n=8, seed=4)
    # "on purpose" stamp, then the passenger survives
    if 1.9 <= t < 2.5:
        kk = slam(t, 1.9, 0.13, 1.8) * (1 - ic(prog(t, 2.38, 0.12)))
        blit(cv, big('stamp', 'ON PURPOSE', s=8), 640, GROUND - 330, kk, kk, -8, anchor='center')
    passenger(cv, left, top, 10, popin(t, 2.44))
    if t >= 2.66:
        kh = popin(t, 2.66) * (1 + 0.1 * math.sin(t * 10))
        blit(cv, big('heart', s=10), left + 32 * 10, top - 70 - 12 * math.sin(t * 5), kh, kh, anchor='center')
        sparkles(cv, t, left + 320, top - 40, 300, 180, n=8, seed=5)
    if t >= 3.01:
        kc = popin(t, 3.01)
        blit(cv, big('check', s=9), left + 450, top - 80, kc, kc, anchor='center')
    confetti(cv, t, 3.01, 640, 900, n=44, seed=6)
    expr = 'shock' if TI <= t < 1.75 else 'smile'
    lift = -140 * math.sin(math.pi * prog(t, 3.01, 0.4)) if 3.01 <= t < 3.41 else 0
    guy(cv, t, 245, expr, lift=lift, scale=0.4 + 0.6 * popin(t, -0.2, 0.32),
        poses=[(TI, 1.2, 'flail'), (1.8, 2.42, 'point'), (2.44, 2.98, 'hips'), (3.01, 3.7, 'up')])

def lane_front(t, charge, hit):
    """x of a test car's bumper: parked, reverses out at 6.45, charges back in to hit the wall at `hit`."""
    if t < 6.45: return 860
    if t < charge: return 860 - 1600 * ic(prog(t, 6.45, 0.32))
    if t < hit: return -120 + (WALL_X + 120) * ic(prog(t, charge, hit - charge))
    return None

TA, TB = 7.68, 9.70                 # rigid car hits, crumple car hits

def scene_lanes(cv, t):
    drop_wall(cv, t, 5.08, 5.40, 360)
    # car B (bottom lane, folds) is drawn behind the guy so it passes behind him
    def test_car(color, ground, popt, charge, hit, rigid):
        f = lane_front(t, charge, hit)
        k, rot, moving = 0.0, 0.0, 6.45 <= t < hit
        if f is None:
            if rigid:
                f = WALL_X - 140 * oc(prog(t, hit, 0.28)) + (6 * math.sin(t * 70) if t < hit + 0.45 else 0)
                rot = 3 * math.sin(math.pi * prog(t, hit, 0.3))
            else:
                f = WALL_X - 18 * math.sin(math.pi * prog(t, hit, 0.25))
                k = oc(prog(t, hit, 0.75))
        if f < -40: return None
        if moving: speed_lines(cv, f, ground, 8, 1)
        sc = popin(t, popt)
        return crash_car(cv, t, color, f, ground, k, s=8, sc=sc, rot=rot, moving=moving)
    lb = test_car('blue', GROUND, 4.27, 9.27, TB, False)
    expr = 'smile'
    if TA <= t < 8.6 or TB <= t < 10.25: expr = 'shock'
    guy(cv, t, 200, expr, poses=[(3.78, 4.4, 'point'), (4.6, 5.0, 'shrug'), (6.45, 7.3, 'hips'), (7.48, TA, 'point'),
                                 (TA, 8.4, 'flail'), (9.3, TB, 'point'), (10.3, 11.5, 'up')])
    la = test_car('red', LANE_A, 4.08, 7.25, TA, True)
    for (lt, ground, seed) in ((la, LANE_A, 1), (lb, GROUND, 2)):
        if lt and t < 6.45 and t > 4.3: sparkles(cv, t, lt[0] + 208, ground - 100, 380, 180, n=5, seed=seed)
    if 4.68 <= t < 5.9:
        kk = popin(t, 4.68) * (1 - ic(prog(t, 5.75, 0.15)))
        blit(cv, big('badge', 'SAME CAR', s=6), 650, 880, kk, kk, -3 + 2 * math.sin(t * 3), anchor='center')
    if 5.95 <= t < 6.5:
        for i, (lt, ground) in enumerate(((la, LANE_A), (lb, GROUND))):
            kk = popin(t, 5.95 + 0.12 * i) * (1 - ic(prog(t, 6.38, 0.12)))
            blit(cv, big('badge', '60 MPH', '#ffffff', '#1a1a2e', '#d6d9e2', s=6), 650, ground - 245, kk, kk, 4, anchor='center')
    for i, (c, a) in enumerate((('3', 6.55), ('2', 6.8), ('1', 7.05), ('GO!', 7.25))):
        b = a + (0.25 if i < 3 else 0.35)
        if a <= t < b:
            kk = slam(t, a, 0.1, 0.9)
            blit(cv, big('label', c, '#ff3b3b' if i < 3 else '#3cc85a', s=16), 620, 930, kk, kk, anchor='center')
    # rigid car: all the energy, no fold
    burst(cv, t, TA, WALL_X, LANE_A - 90, 150)
    debris(cv, t, TA, WALL_X - 10, LANE_A - 90, n=10, seed=8)
    if t >= 8.25 and la:
        kk = slam(t, 8.25, 0.13, 1.8)
        blit(cv, big('stamp', 'SOLID', s=9), la[0] + 210, LANE_A - 330, kk, kk, 7, anchor='center')
    if t > 8.0 and la: dizzy(cv, t, la[0] + 230, LANE_A - 215)
    # crumple car: folds like an accordion
    burst(cv, t, TB, WALL_X, GROUND - 90, 170)
    debris(cv, t, TB, WALL_X - 10, GROUND - 90, n=14, seed=9)
    dust(cv, t, TB, WALL_X - 30, GROUND - 20, n=12, seed=12, dirx=-400)
    if TB <= t < 10.6: sparkles(cv, t * 2, WALL_X - 50, GROUND - 100, 160, 160, n=8, seed=10)
    if t >= 10.34:
        ka = popin(t, 10.34)
        blit(cv, big('arrow', s=9), WALL_X - 40, GROUND - 250 + 20 * abs(math.sin(t * 6)), ka, ka)

def scene_zone(cv, t):
    wall(cv, GROUND - 640)
    color = 'used' if t >= 21.79 else 'red'
    jit = 8 * math.sin(t * 80) * (1 - prog(t, 21.79, 0.5)) if 21.79 <= t < 22.3 else 0
    left, top = crash_car(cv, t, color, WALL_X + jit, GROUND, 1.0)
    zx0 = left + 41 * 10
    smoke(cv, t, 11.0, WALL_X - 40, top + 80, n=4)
    if t >= 21.79: smoke(cv, t, 21.8, left + 300, top + 40, n=5, rise=360, grey=(150, 150, 160))
    # "that fold": zone highlight
    if 11.75 <= t < 13.5 and int(t * 8) % 2 == 0:
        dashed_box(cv, zx0 - 24, top + 40, WALL_X + 18, GROUND + 14, (255, 210, 63))
    if 11.75 <= t < 13.5:
        ka = popin(t, 11.75)
        blit(cv, big('arrow', s=9), zx0 + 30, top + 10 + 20 * abs(math.sin(t * 6)), ka, ka)
    if 12.39 <= t < 13.5:
        kk = slam(t, 12.39, 0.13, 1.6) * (1 - ic(prog(t, 13.38, 0.12)))
        blit(cv, big('badge', 'CRUMPLE ZONE', s=7), 590, 600, kk, kk, -5 + 2 * math.sin(t * 3), anchor='center')
        sparkles(cv, t, 590, 600, 640, 160, n=9, seed=13)
    # energy soaked up by the folds
    bolts(cv, t, 13.55, 15.2, WALL_X - 10, zx0 + 20, GROUND - 130)
    if 14.17 <= t < 15.4:
        kk = popin(t, 14.17) * (1 - ic(prog(t, 15.25, 0.15)))
        blit(cv, big('badge', 'ABSORBED', '#bff0c8', '#1f7a3a', '#8fd6a0', s=7), 700, 620, kk, kk, 4, anchor='center')
    # a little bit still reaches the cabin
    if 15.48 <= t < 15.95:
        p = prog(t, 15.48, 0.45)
        kb = 0.6 * (1 - ic(prog(p, 0.6, 0.4)))
        blit(cv, big('bolt', s=7), zx0 - (zx0 - left - 320) * oc(p), GROUND - 200 - 40 * math.sin(math.pi * p), kb, kb, anchor='center')
    hop = -50 * math.sin(math.pi * prog(t, 22.68, 0.35)) if 22.68 <= t < 23.03 else 0
    passenger(cv, left, top, 10, popin(t, 15.91), hop)
    if 16.25 <= t < 17.1:
        kc = popin(t, 16.25) * (1 - ic(prog(t, 16.95, 0.15)))
        blit(cv, big('check', s=8), left + 320, top - 60, kc, kc, anchor='center')
    # the cabin stays rigid
    if 17.18 <= t < 19.5 and int(t * 6) % 2 == 0:
        dashed_box(cv, left + 60, top + 20, zx0 + 10, top + 125, (61, 127, 214))
    if 17.18 <= t < 18.3:
        ka = popin(t, 17.18)
        blit(cv, big('arrow', s=9), left + 230, top - 30 + 20 * abs(math.sin(t * 6)), ka, ka)
    if 18.34 <= t < 19.5:
        kh = popin(t, 18.34) * (1 + 0.1 * math.sin(t * 10))
        blit(cv, big('heart', s=9), left + 320, top - 60 - 10 * math.sin(t * 5), kh, kh, anchor='center')
        sparkles(cv, t, left + 320, top + 40, 260, 160, n=7, seed=14)
    if t >= 19.58: cage(cv, left, top, 10, prog(t, 19.58, 0.3))
    if 19.92 <= t < 21.6:
        kk = slam(t, 19.92, 0.13, 1.6) * (1 - ic(prog(t, 21.45, 0.15)))
        blit(cv, big('badge', 'RIGID', '#ffffff', '#3d7fd6', '#d6d9e2', s=9), left + 240, top - 140, kk, kk, -4 + 2 * math.sin(t * 3), anchor='center')
        sparkles(cv, t * 1.5, left + 250, top + 50, 420, 160, n=8, seed=15)
    # the car is wrecked ...
    debris(cv, t, 21.79, left + 300, top + 60, n=24, seed=16)
    burst(cv, t, 21.79, left + 260, top + 100, 150)
    if 21.79 <= t < 22.75:
        kk = slam(t, 21.79, 0.13, 1.8) * (1 - ic(prog(t, 22.6, 0.15)))
        blit(cv, big('stamp', 'WRECKED', s=10), left + 250, top - 160, kk, kk, -8, anchor='center')
    # ... and you aren't
    if t >= 22.68:
        kk = slam(t, 22.68, 0.13, 1.5)
        blit(cv, big('badge', 'SAFE', '#bff0c8', '#1f7a3a', '#8fd6a0', s=12), 300, 470 + 8 * math.sin(t * 4), kk, kk, -4, anchor='center')
        sparkles(cv, t * 1.4, 400, 700, 760, 600, n=14, seed=17)
    if t >= 23.05:
        kc = popin(t, 23.05)
        blit(cv, big('check', s=9), left + 320, top - 70, kc, kc, anchor='center')
    confetti(cv, t, 22.68, 230, 760, n=50, seed=18)
    confetti(cv, t, 22.75, 760, 760, n=36, seed=19, spread=0.8)
    expr = 'smile'
    if 21.79 <= t < 22.6: expr = 'shock'
    lift = -150 * math.sin(math.pi * prog(t, 22.68, 0.42)) if 22.68 <= t < 23.1 else 0
    guy(cv, t, 245, expr, lift=lift, poses=[(11.75, 12.3, 'point'), (12.39, 13.3, 'up'), (13.61, 14.6, 'talkR'),
        (15.48, 16.2, 'point'), (16.25, 16.9, 'pointup'), (17.18, 18.2, 'point'), (18.34, 19.4, 'hips'),
        (19.58, 20.5, 'up'), (21.14, 21.75, 'shrug'), (21.79, 22.6, 'flail'), (22.68, 24.4, 'up')])

SCENES = [(0.0, scene_hook), (3.70, scene_lanes), (11.45, scene_zone)]
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
SHAKES = [(0.30, 0.45, 44), (5.40, 0.25, 18), (7.68, 0.45, 40), (8.25, 0.15, 10), (9.70, 0.45, 32),
          (12.39, 0.2, 12), (14.6, 0.2, 10), (19.58, 0.2, 14), (19.92, 0.15, 10), (21.79, 0.45, 36), (22.68, 0.2, 12)]
PUNCH = [(0.30, 1.5, 1.12, 790, 1060), (3.78, 4.7, 1.06, 600, 960), (9.70, 11.0, 1.1, 740, 1100),
         (12.39, 13.45, 1.07, 730, 1000), (17.18, 20.9, 1.13, 670, 1040), (22.68, 24.4, 1.08, 420, 950)]
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
EMPH = {'crumpling', 'purpose', 'alive', 'identical', 'wall', 'speed', 'solid', 'folds', 'accordion', 'crumple', 'zone',
        'energy', 'crash', 'less', 'middle', 'rigid', 'destroyed', "don't"}

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

TFONT = font(70)

@lru_cache(None)
def title_img():
    lines = [('why your car is built to', (255, 255, 255)), ('CRUMPLE', (255, 217, 59))]
    img = Image.new('RGBA', (1000, 260), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for i, (txt, col) in enumerate(lines):
        f = TFONT if i == 0 else font(150)
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
    (0.0, 'vroom', 0.9), (0.02, 'whoosh', 0.8), (0.12, 'screech', 0.6), (0.30, 'crash', 1.0), (0.30, 'boom', 0.8),
    (0.62, 'poof', 0.5), (1.9, 'stamp', 1.0), (2.44, 'pop', 0.7), (2.66, 'pop', 0.6), (2.7, 'sparkle', 0.7),
    (3.01, 'ding', 0.9), (3.01, 'confetti', 0.9),
    (3.6, 'whoosh', 0.6), (4.08, 'pop', 0.7), (4.27, 'pop', 0.7), (4.68, 'ding', 0.6), (5.08, 'fall', 0.9), (5.40, 'thump', 1.0),
    (5.95, 'pop', 0.6), (6.07, 'pop', 0.5), (6.45, 'vroom', 0.8), (6.55, 'pop', 0.6), (6.8, 'pop', 0.6), (7.05, 'pop', 0.6),
    (7.25, 'ding', 0.7), (7.27, 'whoosh', 0.7), (7.68, 'crash', 1.0), (7.68, 'boom', 0.9), (8.25, 'stamp', 1.0),
    (9.27, 'vroom', 0.8), (9.3, 'whoosh', 0.7), (9.70, 'crash', 1.0), (9.75, 'slide_down', 0.8), (10.34, 'pop', 0.6),
    (10.4, 'sparkle', 0.7),
    (11.35, 'whoosh', 0.6), (11.75, 'pop', 0.6), (12.39, 'stamp', 0.9), (12.42, 'ding', 0.7), (13.55, 'whoosh', 0.5),
    (14.17, 'pop', 0.6), (14.6, 'ding', 0.6), (15.48, 'whoosh', 0.4), (15.91, 'pop', 0.6), (16.25, 'ding', 0.8),
    (17.18, 'whoosh', 0.5), (17.2, 'pop', 0.6), (18.34, 'pop', 0.7), (18.4, 'sparkle', 0.8),
    (19.58, 'stamp', 1.0), (19.75, 'thump', 0.5), (19.92, 'stamp', 0.6), (19.95, 'ding', 0.8),
    (21.79, 'crash', 1.0), (21.79, 'stamp', 0.8), (22.1, 'poof', 0.6),
    (22.68, 'confetti', 1.0), (22.68, 'ding', 0.9), (22.9, 'sparkle', 0.9), (23.05, 'pop', 0.6),
] + [(13.55 + i * 0.22 + 0.25, 'pop', 0.25) for i in range(7)]

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
        F0, N = int(t0 * FPS), int((t1 - t0) * FPS)
        ff = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS),
                               '-i', '-', '-ss', str(t0), '-i', 'mix.wav', '-c:v', 'libx264', '-preset', 'medium', '-crf', '17', '-pix_fmt', 'yuv420p',
                               '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', '-shortest', out], stdin=subprocess.PIPE)
        with Pool(4) as pool:
            for i, b in enumerate(pool.imap(frame, range(F0, F0 + N), chunksize=6)):
                ff.stdin.write(b)
                if i % 300 == 0: print(f'{i}/{N}', flush=True)
        ff.stdin.close(); ff.wait()
        print('done', ff.returncode)
        raise SystemExit(ff.returncode)
