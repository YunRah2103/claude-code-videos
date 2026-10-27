"""Renders the 'how strong is your car roof' TikTok explainer, synced to the voiceover."""
import json, math, os, sys, subprocess
from functools import lru_cache
from multiprocessing import Pool
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import pix, sfx

W, H, FPS, S = 1080, 1920, 60, 9
GROUND = 1180
DUR = 24.6
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
    y = y - img.height if anchor == 'bottom' else y if anchor == 'top' else y - img.height / 2
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

def guy(cv, t, cx, expr='smile', sx=1.0, sy=1.0, lift=0.0, npc=False, scale=1.0, bob=True, poses=None, hat=None):
    shadow(cv, cx, 260 * sx * scale, 1 - min(1, abs(lift) / 400))
    b = idle_bob(t) if bob and sy == 1 else 0
    pose = pick_pose(t, expr, poses) if sy > 0.9 else 'down'
    blit(cv, big_guy(face(t, expr), npc, pose), cx, GROUND + lift + b, sx * scale, sy * scale)
    if hat is not None and t >= hat:  # hard hat drops onto the head (head rows 0-21 of the 60px sprite)
        top = GROUND + lift + b - 60 * S * sy * scale
        blit(cv, big('hardhat'), cx, top + 7 * S - 700 * (1 - ob(prog(t, hat, 0.3))), sx * scale, sy * scale)

def car(cv, t, cx, color, moving=False, bounce=0.0, sx=1.0):
    phase = int(t * 24) % 2 if moving else 0
    shadow(cv, cx, 440 * sx)
    blit(cv, big('car', color, phase), cx, GROUND + bounce, sx, sx)

# ------------------------------------------------------------------ scenes
CW, CH = 52 * S, 24 * S          # car sprite size on screen
ROOF = GROUND - CH + 4 * S       # roof line of an upright car standing on the ground
CX = 760

def gx(cx, x, k=1.0): return cx - CW * k / 2 + x * S * k     # car grid -> screen (upright car at cx, scale k)
def gy(y, k=1.0): return GROUND - CH * k + y * S * k

@lru_cache(None)
def xray_car():
    a = np.array(big('car', 'red', 0)).astype(np.float32)
    a[..., :3] = a[..., :3] * 0.45 + np.array([215, 230, 250]) * 0.55
    return Image.fromarray(a.astype(np.uint8), 'RGBA')

def car_rot(cv, cx, rot, color='red', lift=0.0):
    """Car rotated about its centre, resting on the ground whatever the angle."""
    a = math.radians(rot)
    h = CW * abs(math.sin(a)) + CH * abs(math.cos(a))
    shadow(cv, cx, 440 * (0.5 + 0.5 * abs(math.cos(a))), 1 - min(1, abs(lift) / 400))
    blit(cv, big('car', color, 0), cx, GROUND - h / 2 + lift, rot=rot, anchor='center')

def burst(cv, t, t0, x, y, n=8, r0=60, r1=230, life=0.45, col='#ffd23f'):
    """Ring of stars flying out from an impact point."""
    dt = t - t0
    if dt < 0 or dt > life: return
    p = oc(dt / life)
    for i in range(n):
        a = i / n * 2 * math.pi + 0.3
        k = 1 - ic(dt / life)
        blit(cv, big('star', col, s=9), x + math.cos(a) * (r0 + r1 * p), y + math.sin(a) * (r0 + r1 * p) * 0.8, k, k, anchor='center')

def roof_glow(cv, t, cx, col=(255, 210, 63)):
    d = ImageDraw.Draw(cv)
    w = 6 + 3 * math.sin(t * 14)
    d.rectangle((gx(cx, 15) - w, gy(3) - w, gx(cx, 34) + w, gy(5) + w), outline=col, width=int(w))

def scene_hook(cv, t):
    lift = -900 * (1 - ic(prog(t, -0.12, 0.3))) if t < 0.18 else 0
    if 0.18 <= t < 0.7:
        p = prog(t, 0.18, 0.52); lift = -40 * abs(math.sin(p * math.pi * 2)) * (1 - p)
    car(cv, t, CX, 'red', bounce=lift)
    dust(cv, t, 0.18, CX, GROUND - 20, n=16, seed=31)
    if t > 0.3: sparkles(cv, t, CX, GROUND - 120, 500, 240, n=8, seed=2)
    if t >= 0.7:  # "roof"
        if t < 1.5 and int(t * 10) % 2 == 0 or t >= 1.5: roof_glow(cv, t, CX)
        k = popin(t, 0.7)
        blit(cv, big('arrow', s=10), CX, ROOF - 50 - 26 * abs(math.sin(t * 7)), k, k)
    if t >= 1.79:  # "thin"
        k = slam(t, 1.79, 0.12, 1.5)
        blit(cv, big('badge', 'THIN?', '#ffffff', '#1a1a2e', '#d6d9e2', s=8), CX + 120, ROOF - 290, k, k, -8 + 3 * math.sin(t * 4), anchor='center')
    if t >= 2.08:  # "right?"
        k = popin(t, 2.08)
        blit(cv, big('glyph', '?', '#ff9f1c', s=16), 300, GROUND - 640 + 10 * math.sin(t * 6), k, k, 8 * math.sin(t * 3), anchor='center')
    k = 0.4 + 0.6 * popin(t, -0.2, 0.32)
    guy(cv, t, 255, 'smile', scale=k, poses=[(0.6, 1.75, 'point'), (2.0, 2.9, 'shrug')])
    confetti(cv, t, 0.2, CX, GROUND - 260, n=24, seed=4, spread=0.8)

def scene_fragile(cv, t):
    sy = 1.0
    if t >= 3.32:
        dt = t - 3.32; sy = 1 - 0.07 * math.sin(dt * 34) * math.exp(-dt * 7)
    car(cv, t, CX, 'red', sx=1.0) if sy == 1 else blit(cv, big('car', 'red', 0), CX, GROUND, 1, sy)
    wy = -80 + (ROOF + S + 80) * ic(prog(t, 3.04, 0.28))
    if t >= 3.32: wy = GROUND - (CH - 5 * S) * sy
    if t >= 3.04: blit(cv, big('weight', '1KG', s=5), CX - 30, wy)
    dust(cv, t, 3.32, CX - 30, ROOF, n=8, seed=33)
    if t >= 3.54:  # "much"
        k = slam(t, 3.54, 0.13, 1.8)
        blit(cv, big('stamp', 'FRAGILE?', s=9), CX, GROUND - 330, k, k, 10, anchor='center')
    expr = 'shock' if t >= 3.32 else 'smile'
    guy(cv, t, 255, expr, poses=[(2.88, 3.3, 'talkR')])

def scene_roll(cv, t):
    rot, lift = 0.0, 0.0
    if t >= 5.24:
        p = prog(t, 5.24, 0.62); rot = -90 * oc(p); lift = -160 * math.sin(math.pi * p)
    if t >= 5.86: rot = -90 + 4 * math.sin((t - 5.86) * 20) * math.exp(-(t - 5.86) * 5)
    if t >= 7.2: rot = -90 - 90 * ic(prog(t, 7.2, 0.3)); lift = 0
    if t >= 7.5: lift = -26 * abs(math.sin((t - 7.5) * 14)) * math.exp(-(t - 7.5) * 6)
    if 5.24 <= t < 5.7: motion_lines(cv, CX + 120, GROUND - 60, oc(prog(t, 5.24, 0.15)))
    car_rot(cv, CX, rot, 'red', lift)
    dust(cv, t, 5.86, CX + 160, GROUND - 20, n=12, seed=35)
    dust(cv, t, 7.5, CX, GROUND - 20, n=22, seed=37, life=0.8)
    burst(cv, t, 7.5, CX, GROUND - 60, n=10)
    if 6.32 <= t < 7.25:  # "roof" faces right while the car lies on its side
        k = popin(t, 6.32)
        blit(cv, big('arrow', s=10), CX + CH / 2 + 110 + 24 * abs(math.sin(t * 7)), GROUND - CW / 2, k, k, rot=-90, anchor='center')
        if t >= 6.73:
            k = popin(t, 6.73)
            blit(cv, big('badge', '1ST HIT', s=6), CX + 90, GROUND - CW - 90, k, k, 6 * math.sin(t * 3), anchor='center')
    if t >= 7.5:
        k = slam(t, 7.5, 0.14, 1.9)
        blit(cv, big('label', 'BAM!', '#ff3b3b', s=16), CX, GROUND - 470, k, k, -8 + 2 * math.sin(t * 5), anchor='center')
    expr = 'shock' if t >= 5.24 else 'smile'
    guy(cv, t, 255, expr, poses=[(5.24, 5.9, 'flail'), (6.3, 7.2, 'point'), (7.5, 8.4, 'flail')])

def scene_build(cv, t):
    sy = 1.0
    if t >= 10.13:
        dt = t - 10.13; sy = 1 - 0.05 * math.sin(dt * 30) * math.exp(-dt * 7)
    blit(cv, big('car', 'red', 0), CX, GROUND, 1, sy); shadow(cv, CX, 440)
    for i, t0 in enumerate((9.17, 9.47, 9.72)):  # welding sparks on the roof
        if t0 <= t < t0 + 0.5:
            x = (gx(CX, 17), gx(CX, 31), gx(CX, 24))[i]
            sparkles(cv, t * 3, x, ROOF, 160, 120, n=10, seed=40 + i)
            burst(cv, t, t0, x, ROOF, n=6, r0=10, r1=110, life=0.3, col='#ff9f1c')
    if t >= 9.85:  # a whole second car lands on the roof
        y = -260 + (ROOF + 2 * S + 260) * ic(prog(t, 9.85, 0.28))
        if t >= 10.13: y = GROUND - (CH - 6 * S) * sy
        blit(cv, big('car', 'blue', 0), CX, y)
    dust(cv, t, 10.13, CX, ROOF, n=16, seed=41)
    if t >= 10.4:
        k = popin(t, 10.4)
        blit(cv, big('badge', 'WHOLE CAR', '#ffffff', '#1a1a2e', '#d6d9e2', s=6), CX, ROOF - CH - 110, k, k, -4 + 2 * math.sin(t * 3), anchor='center')
    if t >= 10.8:
        k = popin(t, 10.8)
        blit(cv, big('check', s=11), CX + 300, ROOF - CH - 130, k, k, anchor='center')
        sparkles(cv, t * 1.6, CX, ROOF - 120, 520, 300, n=10, seed=43)
    expr = 'shock' if 10.13 <= t < 10.75 else 'smile'
    guy(cv, t, 255, expr, hat=8.5, poses=[(8.5, 9.1, 'point'), (9.1, 10.0, 'hips'), (10.8, 11.5, 'up')])

PILLARS = [(11.57, ((16, 4.5), (10.5, 10.5))), (11.8, ((26.5, 4.5), (26.5, 11))),
           (11.95, ((32, 4.5), (40.5, 10.5))), (12.15, ((16, 4.5), (32, 4.5)))]
STEEL = ((205, 218, 232), (120, 140, 165))

PK, PX = 1.3, 690   # bigger car for the x-ray close-up

def scene_pillars(cv, t):
    shadow(cv, PX, 440 * PK)
    xr = popin(t, 11.5, 0.2) > 0.5
    blit(cv, xray_car() if xr else big('car', 'red', 0), PX, GROUND, PK, PK)
    d = ImageDraw.Draw(cv)
    glow = 1 + (0.35 + 0.35 * math.sin(t * 16) if t >= 12.83 else 0)
    for t0, ((x0, y0), (x1, y1)) in PILLARS:
        if t < t0: continue
        p = oc(prog(t, t0, 0.22))
        ax, ay, bx, by = gx(PX, x0, PK), gy(y0, PK), gx(PX, x0 + (x1 - x0) * p, PK), gy(y0 + (y1 - y0) * p, PK)
        d.line((ax, ay, bx, by), fill=(150, 205, 255), width=int(5 * S * glow))
        d.line((ax, ay, bx, by), fill=NAVY, width=int(3.2 * S))
        d.line((ax, ay, bx, by), fill=(96, 160, 235), width=int(2 * S))
        sh = (t * 1.3 + t0) % 1  # moving shine
        d.line((ax + (bx - ax) * sh, ay + (by - ay) * sh, ax + (bx - ax) * min(1, sh + 0.2), ay + (by - ay) * min(1, sh + 0.2)), fill=(255, 255, 255), width=S)
    if t >= 12.83:  # "steel"
        k = slam(t, 12.83, 0.13, 1.6)
        blit(cv, big('badge', 'STEEL', '#dfe8f2', '#1a1a2e', '#a9b7c8', s=9), PX, gy(0, PK) - 200, k, k, 6, anchor='center')
        if t < 13.5: sparkles(cv, t * 2, PX, gy(6, PK), 520, 200, n=10, seed=45)
    if t >= 13.76:  # "cabin" cage
        k = popin(t, 13.76); w = int(S * (1 + (int(t * 8) % 2)))
        pad = 30 * (1 - k)
        squeeze = 26 * math.sin(math.pi * prog(t, 14.26, 0.37)) if 14.26 <= t < 14.63 else 0
        d.rectangle((gx(PX, 8, PK) - pad + squeeze, gy(2, PK) - pad + squeeze, gx(PX, 44, PK) + pad - squeeze, gy(12, PK) + pad), outline=(60, 200, 90), width=w)
        if 14.26 <= t < 14.8:  # forces push in, cage holds
            q = math.sin(math.pi * prog(t, 14.26, 0.54))
            blit(cv, big('arrow', s=9), gx(PX, 4, PK) - 60 + 40 * q, gy(7, PK), 1, 1, rot=90, anchor='center')
            blit(cv, big('arrow', s=9), gx(PX, 48, PK) + 60 - 40 * q, gy(7, PK), 1, 1, rot=-90, anchor='center')
            blit(cv, big('arrow', s=9), PX, gy(0, PK) - 80 + 40 * q, anchor='center')
    if t >= 14.63:  # "shape"
        k = popin(t, 14.63)
        blit(cv, big('check', s=12), PX + 170, gy(0, PK) - 380, k, k, anchor='center')
        if t < 15.4: sparkles(cv, t * 2, PX, gy(6, PK), 640, 300, n=12, seed=47)
    expr = 'smile'
    guy(cv, t, 200, expr, scale=0.85, poses=[(11.57, 12.6, 'point'), (13.0, 14.0, 'hips'), (14.63, 15.5, 'up')])

def wall(cv, x0, x1, y_off=0):
    block(cv, x0, GROUND - 330 + y_off, x1, GROUND + y_off, (176, 180, 190), (140, 144, 156), (214, 218, 226))

def crumple(cv, x0, x1, t):
    d = ImageDraw.Draw(cv)
    for j in range(3):
        y = gy(12 + j * 2)
        pts = [(x0 + (x1 - x0) * i / 6, y + (S if i % 2 else -S)) for i in range(7)]
        d.line(pts, fill=NAVY, width=S // 2 + 2)

@lru_cache(None)
def driver_head():
    g = pix.guy('smile', False, 'down').crop((13, 2, 35, 20))
    return pix.up(g, 2)

def scene_crush(cv, t):
    img = big('car', 'red', 0)
    rear, cab, front = img.crop((0, 0, 10 * S, CH)), img.crop((10 * S, 0, 42 * S, CH)), img.crop((42 * S, 0, CW, CH))
    c = oc(prog(t, 16.38, 0.12)) if t >= 16.38 else 0
    sq = 1 - 0.5 * c
    blit(cv, cab, CX - CW / 2 + 26 * S, GROUND)
    if t >= 17.5:  # driver pops up in the front window
        k = popin(t, 17.5)
        head = driver_head()
        head = head.crop((0, 0, head.width, max(1, int(head.height * min(1, k)))))
        blit(cv, head, gx(CX, 33), gy(6), anchor='top')
    blit(cv, rear, gx(CX, 10) - 5 * S * sq, GROUND, sq, 1)
    blit(cv, front, gx(CX, 42) + 5 * S * sq, GROUND, sq, 1)
    shadow(cv, CX, 440)
    if c > 0:
        crumple(cv, gx(CX, 10) - 10 * S * sq, gx(CX, 10), t)
        crumple(cv, gx(CX, 42), gx(CX, 42) + 10 * S * sq, t)
    # concrete walls drop in beside the car, then push
    if 16.0 <= t < 17.6:
        drop = -1400 * (1 - oc(prog(t, 16.0, 0.18)))
        out = 900 * ic(prog(t, 17.2, 0.4))
        lx = gx(CX, 10) - 10 * S * sq; rx = gx(CX, 42) + 10 * S * sq
        wall(cv, lx - 80 - out, lx - out, drop)
        wall(cv, rx + out, rx + 80 + out, drop)
    dust(cv, t, 16.18, CX, GROUND - 20, n=10, seed=51)
    dust(cv, t, 16.5, gx(CX, 8), GROUND - 60, n=14, seed=52, dirx=-300)
    dust(cv, t, 16.5, gx(CX, 44), GROUND - 60, n=14, seed=53, dirx=300)
    if 16.45 <= t < 17.6:
        k = slam(t, 16.45, 0.13, 1.8)
        blit(cv, big('stamp', 'CRUSHED', s=10), CX, GROUND - 400, k, k, -9, anchor='center')
    if t >= 17.5:  # safe cabin glow
        d = ImageDraw.Draw(cv); w = int(S * (1 + (int(t * 6) % 2)))
        d.rectangle((gx(CX, 9), gy(2), gx(CX, 43), gy(12)), outline=(60, 200, 90), width=w)
    if t >= 19.04:  # "intact"
        k = slam(t, 19.04, 0.13, 1.6)
        blit(cv, big('badge', 'SAFE', '#bff0c8', '#1f7a3a', '#8fd6a0', s=11), CX, GROUND - 420, k, k, 6, anchor='center')
        sparkles(cv, t * 1.6, CX, GROUND - 160, 560, 320, n=12, seed=55)
    expr = 'shock' if 16.4 <= t < 17.4 else 'smile'
    guy(cv, t, 255, expr, poses=[(16.4, 17.3, 'flail'), (17.5, 18.6, 'point'), (19.04, 20.0, 'up')])

def scene_wow(cv, t):
    car(cv, t, CX, 'red')
    sparkles(cv, t * 1.5, CX, GROUND - 120, 540, 280, n=12, seed=8)
    for i in range(5):  # five-star rating
        t0 = 20.9 + i * 0.12
        if t >= t0:
            k = popin(t, t0, 0.24)
            a = math.pi * (0.85 - 0.175 * i)
            blit(cv, big('star', s=17), CX + math.cos(a) * 330, ROOF - 140 - math.sin(a) * 200 + 8 * math.sin(t * 6 + i), k, k, anchor='center')
    if t >= 21.34:
        k = slam(t, 21.34, 0.13, 1.6)
        blit(cv, big('badge', 'WOW', s=11), CX, ROOF - 520, k, k, -6 + 3 * math.sin(t * 4), anchor='center')
    confetti(cv, t, 21.34, CX, ROOF - 200, n=46, seed=60)
    confetti(cv, t, 21.4, 255, 700, n=30, seed=61, spread=0.7)
    lift = -130 * math.sin(math.pi * prog(t, 21.34, 0.42)) if 21.34 <= t < 21.76 else 0
    guy(cv, t, 255, 'smile', lift=lift, poses=[(20.19, 20.9, 'hips'), (21.34, 22.4, 'up')])

def scene_cta(cv, t):
    bx, by = 740, 760
    k = popin(t, 22.51)
    blit(cv, big('bubble', 1 + int(t * 4) % 3, s=10), bx, by, k, k, anchor='center')
    if t >= 22.9:  # "comments"
        kh = popin(t, 22.9) * (1 + 0.08 * math.sin(t * 9))
        blit(cv, big('heart', s=9), bx + 150, by - 120, kh, kh, anchor='center')
    if t >= 23.3:
        ka = popin(t, 23.3)
        blit(cv, big('arrow', s=10), bx, 1010 + 22 * abs(math.sin(t * 6)), ka, ka, anchor='center')
    if t >= 23.66:
        kc = popin(t, 23.66)
        blit(cv, big('check', s=10), bx - 190, by - 140, kc, kc, -8, anchor='center')
        sparkles(cv, t * 1.5, bx, by, 520, 360, n=10, seed=63)
    confetti(cv, t, 23.66, 540, 900, n=60, seed=64, spread=1.1)
    lift = -110 * math.sin(math.pi * prog(t, 22.45, 0.4)) if 22.45 <= t < 22.85 else 0
    guy(cv, t, 270, 'smile', lift=lift, poses=[(22.45, 23.2, 'wave'), (23.3, DUR, 'pointup')])

SCENES = [(0.0, scene_hook), (2.8, scene_fragile), (4.6, scene_roll), (8.35, scene_build),
          (11.42, scene_pillars), (15.45, scene_crush), (19.98, scene_wow), (22.35, scene_cta)]

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
SHAKES = [(0.18, 0.35, 30), (3.32, 0.2, 10), (3.54, 0.3, 22), (5.86, 0.25, 14), (7.5, 0.5, 44), (10.13, 0.4, 30),
          (12.83, 0.25, 12), (16.45, 0.45, 40), (19.04, 0.25, 14), (21.34, 0.3, 18), (23.66, 0.25, 12)]
PUNCH = [(0.7, 1.7, 1.12, 760, 1000), (6.3, 7.2, 1.12, 860, 900), (12.83, 13.5, 1.06, 690, 1000),
         (17.5, 19.6, 1.16, 760, 1080), (20.2, 21.9, 1.1, 640, 900)]
BASE_Z, BASE_A = 1.18, (540, 1000)

def camera(t, idx):
    s0 = SCENES[idx][0]
    z = BASE_Z * (1 + 0.03 * prog(t, s0, 6)) * (1 + 0.35 * (1 - oc(prog(t, 0, 0.55))))  # hook zoom-out
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
EMPH = {'roof', 'thin', 'hold', 'rolls', 'first', 'ground', 'engineers', 'weight', 'whole', 'strong', 'pillars', 'steel', 'cabin', 'shape', 'crushed', 'intact', 'impressive', 'comments', 'knew'}

def make_chunks():
    sents, cur = [], []
    for i, w in enumerate(WORDS):
        cur.append(i)
        if w['w'][-1] in '.,?!':
            sents.append(cur); cur = []
    if cur: sents.append(cur)
    chunks = []
    for s in sents:
        k = 1 if len(s) == 4 else math.ceil(len(s) / 3)  # keep 4-word sentences whole
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
    lines = [('how strong is your', (255, 255, 255)), ('CAR ROOF?', (255, 210, 63))]
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
    if t >= 2.9: return
    k = ob(prog(t, -0.2, 0.3)) * (1 - ic(prog(t, 2.55, 0.3)))
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
    (0.0, 'fall', 0.8), (0.18, 'crash', 1.0), (0.2, 'confetti', 0.6), (0.7, 'pop', 0.8), (0.75, 'sparkle', 0.8),
    (1.79, 'stamp', 0.8), (2.08, 'pop', 0.7),
    (2.7, 'whoosh', 0.6), (3.04, 'fall', 0.7), (3.32, 'thump', 1.0), (3.54, 'stamp', 1.0),
    (4.5, 'whoosh', 0.6), (5.24, 'screech', 1.0), (5.86, 'thump', 0.8), (6.32, 'pop', 0.7), (6.73, 'pop', 0.6),
    (7.2, 'fall', 0.8), (7.5, 'crash', 1.0), (7.52, 'boom', 0.8),
    (8.25, 'whoosh', 0.6), (8.5, 'fall', 0.5), (8.78, 'pop', 0.8), (9.17, 'coin', 0.7), (9.47, 'coin', 0.7), (9.72, 'coin', 0.7),
    (9.85, 'fall', 1.0), (10.13, 'crash', 1.0), (10.4, 'pop', 0.7), (10.8, 'ding', 1.0),
    (11.32, 'whoosh', 0.6), (11.57, 'pop', 0.5), (11.8, 'pop', 0.5), (11.95, 'pop', 0.5), (12.15, 'pop', 0.5),
    (12.83, 'stamp', 0.9), (12.85, 'sparkle', 0.8), (13.76, 'pop', 0.8), (14.26, 'whoosh', 0.5), (14.63, 'ding', 1.0),
    (15.35, 'whoosh', 0.6), (16.0, 'fall', 0.8), (16.18, 'thump', 0.8), (16.45, 'crash', 1.0), (16.47, 'stamp', 0.7),
    (17.2, 'whoosh', 0.5), (17.5, 'pop', 0.8), (19.04, 'ding', 1.0), (19.06, 'sparkle', 0.8),
    (19.88, 'whoosh', 0.6), (20.9, 'pop', 0.5), (21.02, 'pop', 0.5), (21.14, 'pop', 0.5), (21.26, 'pop', 0.5),
    (21.34, 'confetti', 1.0), (21.36, 'cha_ching', 0.8),
    (22.25, 'whoosh', 0.6), (22.51, 'pop', 0.8), (22.9, 'pop', 0.6), (23.3, 'pop', 0.7), (23.66, 'confetti', 1.0), (23.68, 'ding', 0.8),
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
        t0 = float(sys.argv[4]) if len(sys.argv) > 4 else 0.0   # optional test-clip range
        t1 = float(sys.argv[5]) if len(sys.argv) > 5 else DUR
        build_audio(vo, 'mix.wav')
        ff = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS),
                               '-i', '-', '-ss', str(t0), '-i', 'mix.wav', '-c:v', 'libx264', '-preset', 'medium', '-crf', '17', '-pix_fmt', 'yuv420p',
                               '-c:a', 'aac', '-b:a', '192k', '-ar', '44100', '-ac', '2', '-movflags', '+faststart', '-shortest', out], stdin=subprocess.PIPE)
        with Pool(4) as pool:
            for i, b in enumerate(pool.imap(frame, range(int(t0 * FPS), int(t1 * FPS)), chunksize=6)):
                ff.stdin.write(b)
                if i % 300 == 0: print(f'{i}/{int((t1 - t0) * FPS)}', flush=True)
        ff.stdin.close(); ff.wait()
        print('done', ff.returncode)
        raise SystemExit(ff.returncode)
