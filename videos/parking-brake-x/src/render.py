"""Renders the experimental looping cut of the 'parking brake truth' TikTok explainer, synced to the voiceover."""
import json, math, os, sys, subprocess
from functools import lru_cache
from multiprocessing import Pool
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import pix, sfx

W, H, FPS, S = 1080, 1920, 60, 9
GROUND = 1180
DUR = 17.1
BG = (255, 255, 255)
NAVY = (26, 26, 46)
VO_OFF = 0.8  # scenes/cues below are authored on a timeline where the voice starts at 0.8 s
LEAD = VO_OFF  # output frame time t maps to authored time t + LEAD, so the voice plays from 0 s
WORDS = [dict(w, s=round(w['s'] + VO_OFF, 2), e=round(w['e'] + VO_OFF, 2)) for w in json.load(open('words.json'))]

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
GOLD = ('#ffd23f', '#1a1a2e', '#e8b923')
GREEN = ('#3cc85a', '#ffffff', '#2a9a45')
RUSTB = ('#b5562a', '#ffffff', '#8a3f1e')
RUST = [(181, 86, 42), (138, 63, 30), (217, 120, 58)]

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

def rays(cv, t, t0, x, y, col, life=0.8, hold=False, r=560):
    # rotating sunburst drawn behind props on key beats
    dt = t - t0
    if dt < 0 or (not hold and dt > life): return
    k = oc(min(1.0, dt / 0.25)) * (1 if hold else 1 - ic(prog(t, t0 + life - 0.25, 0.25)))
    if k <= 0.02: return
    d = ImageDraw.Draw(cv); R = r * k; rot = dt * 40
    for i in range(12):
        a0 = rot + i * 30
        d.pieslice((x - R, y - R, x + R, y + R), a0, a0 + 15, fill=col)

def ring(cv, t, t0, x, y, col, life=0.35, r1=330):
    dt = t - t0
    if dt < 0 or dt > life: return
    p = oc(dt / life); R = 40 + r1 * p
    ImageDraw.Draw(cv).ellipse((x - R, y - R, x + R, y + R), outline=col, width=max(3, int(3 * S * (1 - p))))

def jelly(t, t0):
    dt = t - t0
    return math.exp(-dt * 9) * math.sin(dt * 32) if dt > 0 else 0.0

PALE_Y, PALE_R, PALE_G = (255, 243, 196), (255, 226, 226), (218, 246, 224)

def stamp_at(cv, t, t0, text, x, y, rot=-10, s=12):
    # red stamp with white fill so it reads over props; lands with a jelly wobble and shockwave
    if t < t0: return
    ks = slam(t, t0, 0.14, 1.8); j = 0.16 * jelly(t, t0 + 0.14)
    ring(cv, t, t0 + 0.12, x, y, (255, 210, 63))
    blit(cv, big('stamp', text, '#e0303a', '#ffffff', s=s), x, y, ks * (1 + j), ks * (1 - j), rot, anchor='center')

def snap(v): return round(v / S) * S

def disc_pts(seed, n, cx, cy, r0, r1):
    r = rng_for(seed)
    return [(snap(cx + d * math.cos(a)), snap(cy + d * math.sin(a)))
            for a, d in ((r.uniform(0, 2 * math.pi), r.uniform(r0, r1)) for _ in range(n))]

def rust_dots(cv, t, pts, t0, t1):
    d = ImageDraw.Draw(cv)
    for i, (x, y) in enumerate(pts):
        ti = t0 + (t1 - t0) * i / max(1, len(pts) - 1)
        if t < ti: continue
        sz = S * (1.0 + (i % 3 == 0)) * ob(prog(t, ti, 0.18))
        d.rectangle((x - sz - 3, y - sz - 3, x + sz + 3, y + sz + 3), fill=NAVY)
        d.rectangle((x - sz, y - sz, x + sz, y + sz), fill=RUST[i % 3])

def lever(cv, cx, deg, s=S, dusty=False, base=GROUND, k=1.0):
    if base == GROUND and k > 0.1: shadow(cv, cx + 18 * s, 30 * s * k)
    blit(cv, big('handbrake', int(round(deg)), dusty, s=s), cx, base, k, k)

def icon_lever(cv, t, t0, cx, cy, deg):
    k = popin(t, t0, 0.3)
    if k <= 0.02: return
    d = ImageDraw.Draw(cv)
    r = 175 * k
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(242, 244, 248), outline=NAVY, width=8)
    blit(cv, big('handbrake', int(round(deg)), s=5), cx - 20, cy + 110 * k, k, k)

# 1. hook: he yanks a lever that won't budge
def scene_hook(cv, t):
    # opens mid-yank: lever rattles, one hard jerk on "brake", hand stays on the grip
    rays(cv, t, 0.9, 660, GROUND - 450, PALE_R, life=0.9)
    gx = 230 + 5 * math.sin(t * 38)
    cx = gx + 144 + 32 * S - (54 - 44 * math.cos(math.radians(9))) * S
    jerk = 8 * math.sin(math.pi * prog(t, 1.51, 0.2)) if 1.51 <= t < 1.71 else 0
    deg = 9 + 1.8 * math.sin(t * 55) + jerk
    lift = -44 * S * (math.sin(math.radians(deg)) - math.sin(math.radians(9)))
    lever(cv, cx, deg)
    d = ImageDraw.Draw(cv)
    if int(t * 20) % 2:
        for i in range(3):  # strain marks around the grip
            a = math.radians(-150 + i * 35)
            x, y = gx + 144 + 120 * math.cos(a), GROUND - 207 + lift + 120 * math.sin(a)
            d.rectangle((x - S, y - S, x + S, y + S), fill=(255, 210, 63), outline=NAVY, width=3)
    sparkles(cv, t * 1.6, cx + 120, GROUND - 280, 700, 520, n=14, seed=2)
    stamp_at(cv, t, 0.9, 'STUCK?', 660, GROUND - 450, -9, 12)
    dust(cv, t, 0.92, cx + 160, GROUND - 180, n=14, seed=41)
    dust(cv, t, 1.53, cx + 180, GROUND - 160, n=10, seed=40)
    if t >= 0.9:
        kx = popin(t, 0.9, 0.22) * (1 + 0.08 * math.sin(t * 14))
        blit(cv, big('glyph', '!', '#e0303a', s=12), gx - 10, GROUND - 610, kx, kx, -8, anchor='center')
    expr = 'shock' if t < 1.25 or 1.51 <= t < 1.75 else 'smile'
    guy(cv, t, gx, expr, lift=lift, bob=False, poses=[(-1, 2.5, 'catch')])

# 2. drum brake seizes
DRUM_C = (720, GROUND - 300)
DRUM_PTS = disc_pts(11, 18, *DRUM_C, 60, 215)
def scene_drum(cv, t):
    rays(cv, t, 2.01, 720, GROUND - 300, PALE_Y, life=0.75)
    cx, cy = DRUM_C
    k = popin(t, 1.85, 0.3)
    blit(cv, big('drum', s=11), cx, cy, k, k, anchor='center')
    rust_dots(cv, t, DRUM_PTS, 2.05, 2.65)
    dust(cv, t, 2.03, cx, cy - 240, n=12, seed=42)
    if t >= 2.01:
        ks = slam(t, 2.01, 0.14, 1.8)
        blit(cv, big('tag', 'SEIZE', '#ffd23f', '#1a1a2e', s=10), cx, cy - 300, ks, ks, swing(t, 2.01, 10), anchor='center')
    kl = popin(t, 2.15)
    blit(cv, big('badge', 'MANY OLDER CARS', '#ffffff', '#1a1a2e', '#d6d9e2', s=5), cx, cy + 320, kl, kl, -2 + math.sin(t * 3), anchor='center')
    expr = 'shock' if 2.01 <= t < 2.45 else 'smile'
    guy(cv, t, 230, expr, poses=[(1.85, 2.0, 'point'), (2.0, 2.45, 'shock'), (2.45, 2.9, 'point')])

# 3. never used: red X, then a dusty lever
def scene_never(cv, t):
    cx = 590
    dusty = t >= 3.45
    k = popin(t, 2.8, 0.3)
    lever(cv, cx, 0, s=10, dusty=dusty, k=k)
    if 3.04 <= t < 3.45:
        ks = slam(t, 3.04, 0.12, 1.6)
        blit(cv, big('xmark', s=16), cx + 60, GROUND - 230, ks, ks, anchor='center')
    dust(cv, t, 3.42, cx + 60, GROUND - 230, n=16, seed=46)
    if dusty:
        kw = popin(t, 3.5, 0.25)
        blit(cv, big('cobweb', s=9), cx + 40 + 72, GROUND - 170 + 72, kw, kw, anchor='center')
        blit(cv, big('cobweb', s=7).transpose(Image.FLIP_LEFT_RIGHT), cx + 310 - 56, GROUND - 170 + 56, kw, kw, anchor='center')
        r = rng_for(13); d = ImageDraw.Draw(cv)
        for i in range(16):
            ph = r.uniform(0, 1); x0 = r.uniform(cx - 300, cx + 380)
            y = GROUND - 620 + ((t * 70 + ph * 520) % 520)
            x = snap(x0 + 30 * math.sin(t * 1.7 + ph * 6))
            d.rectangle((x, y, x + S, y + S), fill=(196, 192, 180))
    expr = 'sad' if t >= 3.45 else 'smile'
    guy(cv, t, 230, expr, poses=[(2.8, 3.45, 'point')])

# 4. rust creeps along the cable to the brake
LV = (420, GROUND - 640)
DRUM2 = (800, GROUND - 250)
def _cable():
    (x0, y0), (x1, y1) = (LV[0] + 40, LV[1] - 40), (DRUM2[0] - 130, DRUM2[1] - 60)
    return [(snap(x0 + (x1 - x0) * u), snap(y0 + (y1 - y0) * u + 110 * math.sin(math.pi * u)))
            for u in (i / 80 for i in range(81))]
CABLE = _cable()
CABLE_RUST = [(x + (S if i % 2 else -S), y + (S if i % 3 else 0)) for i, (x, y) in enumerate(CABLE[6:78:5])]
DRUM2_PTS = disc_pts(17, 12, *DRUM2, 40, 140)
def scene_cable(cv, t):
    d = ImageDraw.Draw(cv)
    k = popin(t, 4.15, 0.3)
    blit(cv, big('handbrake', 30, s=4), LV[0], LV[1] + 60, k, k)
    kd = popin(t, 4.2, 0.3) * (1 + 0.08 * math.exp(-max(0, t - 5.73) * 8) * (t >= 5.73))
    blit(cv, big('drum', s=7), DRUM2[0], DRUM2[1], kd, kd, anchor='center')
    n = int(len(CABLE) * oc(prog(t, 4.15, 0.35)))
    for w, col in ((2 * S, NAVY), (S + 2, (58, 59, 68))):
        for x, y in CABLE[:n]:
            d.rectangle((x - w, y - w, x + w, y + w), fill=col)
    for x, y in CABLE[:n:2]:
        d.rectangle((x - 2, y - S, x + S - 2, y - S + 3), fill=(125, 132, 145))
    rust_dots(cv, t, CABLE_RUST, 4.3, 5.6)
    rust_dots(cv, t, DRUM2_PTS, 5.75, 6.4)
    kr = popin(t, 4.27)
    blit(cv, big('badge', 'RUST', *RUSTB, s=8), 640, GROUND - 840, kr, kr, swing(t, 4.27, 8), anchor='center')
    sparkles(cv, t, DRUM2[0], DRUM2[1], 360, 300, n=6, seed=18) if t >= 5.73 else None
    guy(cv, t, 200, 'smile', poses=[(4.27, 5.0, 'pointup'), (5.73, 6.4, 'point')])

# 5. eventually it sticks
WHEEL_RUST = disc_pts(23, 10, 720, GROUND - 253, 30, 110)
def scene_wheel(cv, t):
    rays(cv, t, 7.75, 720, GROUND - 253, PALE_R, life=0.9)
    cx = 720
    k = popin(t, 6.65, 0.3)
    deg = 0 if t < 6.86 else 42 * oc(prog(t, 6.86, 0.85))
    jx = 16 * math.sin(t * 70) * math.exp(-(t - 7.75) * 3) if t >= 7.75 else 0
    shadow(cv, cx, 460)
    blit(cv, big('wheel', int(deg) // 3 * 3, s=11), cx + jx, GROUND, k, k)
    if k > 0.98: rust_dots(cv, t, [(x + jx, y) for x, y in WHEEL_RUST], 6.7, 7.4)
    if 6.86 <= t < 7.75:
        r = 300; a0 = math.radians(-60 + deg)
        d = ImageDraw.Draw(cv)
        for i in range(3):
            a = a0 - i * 0.18
            x, y = cx + r * math.cos(a), GROUND - 253 + r * math.sin(a)
            d.rectangle((x - S, y - S, x + S, y + S), fill=(255, 210, 63), outline=NAVY, width=3)
    stamp_at(cv, t, 7.75, 'STUCK', cx, GROUND - 560, -12, 15)
    dust(cv, t, 7.77, cx, GROUND - 20, n=14, seed=43)
    expr = 'shock' if 7.75 <= t < 8.25 else 'smile'
    guy(cv, t, 230, expr, poses=[(6.86, 7.7, 'shrug'), (7.75, 8.25, 'shock'), (8.25, 8.9, 'hips')])

# 6. pull it on a flat road
def lever_clicks(t, t0):
    steps = [t0, t0 + 0.14, t0 + 0.28]
    n = sum(t >= s for s in steps)
    return min(32, n * 11 - (4 * math.exp(-(t - steps[n - 1]) * 18) if n else 0))

def scene_flat(cv, t):
    rays(cv, t, 10.93, 740, GROUND - 320, PALE_G, life=0.6)
    ring(cv, t, 10.95, 940, GROUND - 330, (60, 200, 90))
    cx = 740
    p = prog(t, 8.72, 0.6)
    x = cx + 700 * (1 - oc(p))
    shadow(cv, x, 440)
    blit(cv, big('car', 'red', int(t * 12) % 2 if p < 1 else 0, s=8), x, GROUND)
    dust(cv, t, 9.3, x + 180, GROUND - 10, n=10, seed=44, dirx=300)
    icon_lever(cv, t, 9.42, cx - 40, GROUND - 560, lever_clicks(t, 10.2))
    if t >= 10.2:
        kc = popin(t, 10.2)
        blit(cv, big('label', 'CLICK!', '#e0303a', s=9), cx - 40, GROUND - 790, kc, kc, 8 + 3 * math.sin(t * 6), anchor='center')
    if t >= 10.64:
        kf = popin(t, 10.64)
        d = ImageDraw.Draw(cv)
        for xx in range(470, 1060, 6 * S):
            d.rectangle((xx, GROUND + 2 * S, xx + 3 * S, GROUND + 3 * S), fill=(60, 200, 90))
        blit(cv, big('badge', 'FLAT', *GREEN, s=8), cx - 370, GROUND - 840, kf, kf, -6 + 3 * math.sin(t * 3), anchor='center')
    if t >= 10.93:
        kc = popin(t, 10.93)
        blit(cv, big('check', s=12), cx + 200, GROUND - 330, kc, kc, anchor='center')
        gsparkles(cv, t, cx, GROUND - 420, 600, 560, n=12, seed=37)
    guy(cv, t, 230, 'smile', poses=[(10.2, 10.6, 'point'), (10.93, 11.6, 'thumb')])

# 7. on a slope it holds
SLOPE_X0, SLOPE_T = 430, 0.25
def slope_y(x): return GROUND - max(0, x - SLOPE_X0) * SLOPE_T

@lru_cache(None)
def tilted_car(deg):
    return pix.up(pix.car('red', 0).rotate(deg, resample=Image.NEAREST, expand=True), 8)

def scene_slope(cv, t):
    rays(cv, t, 12.63, 760, GROUND - 450, PALE_G, life=0.8)
    ring(cv, t, 12.68, 900, GROUND - 560, (60, 200, 90))
    d = ImageDraw.Draw(cv)
    rise = oc(prog(t, 11.45, 0.35))
    for x in range(SLOPE_X0, W + 300, S):
        y = snap(GROUND - (GROUND - slope_y(x)) * rise)
        d.rectangle((x, y, x + S - 1, GROUND + S), fill=(228, 230, 236))
        d.rectangle((x, y, x + S - 1, y + S - 1), fill=NAVY)
        d.rectangle((x, y + S, x + S - 1, y + 2 * S - 1), fill=(200, 204, 212))
    ang = math.degrees(math.atan(SLOPE_T)) * rise
    nudge = -10 * math.sin(math.pi * prog(t, 12.0, 0.3)) if 12.0 <= t < 12.3 else 0
    cx = 780 + nudge
    th = math.radians(ang)
    car = tilted_car(int(round(ang)))
    blit(cv, car, cx - 11 * 8 * math.sin(th), GROUND - (GROUND - slope_y(cx)) * rise - 11 * 8 * math.cos(th), anchor='center')
    if t < 12.63: icon_lever(cv, t, 11.55, 640, GROUND - 720, 32)
    if t >= 12.63:
        kb = popin(t, 12.63)
        blit(cv, big('badge', 'HOLDING', *GREEN, s=8), 640, GROUND - 720, kb, kb, 3 * math.sin(t * 3), anchor='center')
        kc = popin(t, 12.66)
        blit(cv, big('check', s=12), 900, GROUND - 560, kc, kc, anchor='center')
        gsparkles(cv, t, 780, GROUND - 400, 560, 400, n=12, seed=38)
    guy(cv, t, 230, 'smile', poses=[(11.72, 12.5, 'point'), (12.63, 13.6, 'thumb')])

# 8. easy habit to forget -> finale
def scene_end(cv, t):
    rays(cv, t, 15.6, 540, 520, PALE_Y, hold=True, r=820)
    ring(cv, t, 15.64, 540, 520, (60, 200, 90), life=0.45, r1=520)
    bx, by = 640, 700 + 8 * math.sin(t * 3)
    if t < 15.08:
        kb = popin(t, 13.5, 0.3)
        blit(cv, big('bubble', 0, s=11), bx, by, kb, kb, anchor='center')
        blit(cv, big('handbrake', 30, s=4), bx, by + 70, kb, kb)
        if t >= 14.38:
            ke = popin(t, 14.38)
            blit(cv, big('badge', 'EASY', *GOLD, s=8), bx + 150, by - 210, ke, ke, 8 + 3 * math.sin(t * 4), anchor='center')
    else:
        poof(cv, t, 15.08, bx, by, seed=47)
        if t < 15.62:
            kq = popin(t, 15.12) * (1 - ic(prog(t, 15.45, 0.17)))
            blit(cv, big('glyph', '?', '#e0303a', s=18), bx, by, kq, kq, 6 * math.sin(t * 9), anchor='center')
    lift = -150 * math.sin(math.pi * prog(t, 15.6, 0.42)) if 15.6 <= t < 16.02 else 0
    guy(cv, t, 290, 'smile', lift=lift, poses=[(15.08, 15.6, 'shrug'), (15.6, 18.0, 'thumb')])
    if t >= 15.6:
        confetti(cv, t, 15.6, 300, 700, n=50, seed=4)
        confetti(cv, t, 15.65, 800, 640, n=44, seed=8, spread=0.9)
        confetti(cv, t, 16.4, 560, 600, n=40, seed=9, spread=1.1)
        confetti(cv, t, 17.0, 400, 640, n=30, seed=12, spread=1.2)
        ks = slam(t, 15.62, 0.16, 1.5) * (1 + 0.04 * math.sin((t - 15.62) * 7))
        blit(cv, big('badge', 'PULL IT ONCE', *GREEN, s=8), 540, 520, ks, ks, -6 + 3 * math.sin(t * 2.4), anchor='center')
        sparkles(cv, t * 1.4, 560, 520, 760, 340, n=14, seed=48)
        gsparkles(cv, t, 760, 900, 520, 500, n=8, seed=49)

SCENES = [(0.0, scene_hook), (1.85, scene_drum), (2.78, scene_never), (4.12, scene_cable),
          (6.62, scene_wheel), (8.72, scene_flat), (11.48, scene_slope), (13.42, scene_end)]
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
SHAKES = [(0.8, 1.0, 7), (0.9, 0.3, 26), (1.51, 0.22, 16), (2.01, 0.3, 24), (3.04, 0.2, 12), (7.75, 0.4, 30), (9.3, 0.15, 8), (15.6, 0.3, 16)]
PUNCH = [(15.6, 17.6, 1.06, 540, 760)]  # eases out during the loop slide
# instant zoom kicks that ease back: (time, amount, anchor x, anchor y)
KICKS = [(0.8, 0.28, 520, 950), (0.9, 0.12, 660, 720), (1.51, 0.08, 600, 960), (2.01, 0.12, 720, 820), (3.04, 0.07, 700, 900),
         (3.45, 0.05, 640, 950), (4.27, 0.08, 620, 600), (5.73, 0.07, 800, 930), (6.86, 0.04, 720, 900),
         (7.75, 0.1, 720, 800), (9.3, 0.04, 760, 1100), (10.2, 0.06, 760, 620), (10.48, 0.04, 760, 620),
         (10.93, 0.08, 760, 850), (11.72, 0.05, 780, 900), (12.63, 0.09, 780, 700), (14.38, 0.06, 820, 560),
         (15.08, 0.06, 690, 700), (15.6, 0.12, 560, 700)]
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
EMPH = {'seize', 'never', 'rust', 'cables', 'sticks', 'pull', 'flat', 'check', 'holding', 'forget'}

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
        nxt = WORDS[chunks[ci + 1][0]]['s'] - 0.04 if ci + 1 < len(chunks) else DUR + LEAD
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
    lines = [('the parking brake', (255, 255, 255)), ('TRUTH', (255, 90, 90))]
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
    if t >= 2.0: return
    k = ob(prog(t, LEAD - 0.12, 0.22)) * (1 - ic(prog(t, 1.7, 0.28)))
    if k <= 0.02: return
    img = title_img()
    rot = 3 * math.sin(t * 4)
    img = img.resize((int(img.width * k), int(img.height * k)), Image.BILINEAR).rotate(rot, resample=Image.BICUBIC, expand=True)
    cv.paste(img, (int(W / 2 - img.width / 2), int(330 - img.height / 2)), img)

@lru_cache(None)
def end_img():
    lines = [('many older cars', (255, 255, 255), 76), ('CHECK YOURS', (255, 217, 59), 120)]
    img = Image.new('RGBA', (1000, 240), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for i, (txt, col, sz) in enumerate(lines):
        f = font(sz); w = d.textlength(txt, font=f); y = 0 if i == 0 else 84
        d.text((500 - w / 2 + 6, y + 8), txt, font=f, fill=NAVY, stroke_width=14, stroke_fill=NAVY)
        d.text((500 - w / 2, y), txt, font=f, fill=col, stroke_width=13, stroke_fill=(10, 10, 16))
    return img

def captions(cv, t):
    if t >= 16.0:
        img = end_img(); k = 0.72 + 0.28 * ob(prog(t, 16.0, 0.16))
        img = img.resize((int(img.width * k), int(img.height * k)), Image.BILINEAR)
        cv.paste(img, (int(W / 2 - img.width / 2), int(1400 - img.height / 2)), img)
        return
    for ci, (st, en, idxs) in enumerate(CHUNKS):
        if st <= t < en:
            active = None
            for i in idxs:
                if WORDS[i]['s'] - 0.04 <= t: active = i
            img = caption_img(ci, active)
            k = 0.72 + 0.28 * ob(prog(t, st, 0.16))
            if active is not None and active != idxs[0]:  # beat pop on each new word
                k *= 1 + 0.07 * math.exp(-(t - WORDS[active]['s'] + 0.04) * 14)
            if k != 1:
                img = img.resize((int(img.width * k), int(img.height * k)), Image.BILINEAR)
            cv.paste(img, (int(W / 2 - img.width / 2), int(1390 - img.height / 2)), img)
            return

# ------------------------------------------------------------------ frame + audio
LOOP = 0.3  # final slide back into the opening frame so the clip loops seamlessly
AUTH_END = DUR + LEAD

def progress(cv, t):
    p = clamp(t / DUR)
    d = ImageDraw.Draw(cv)
    x0, x1, y = 110, W - 110, 64
    d.rectangle((x0 - 6, y - 6, x1 + 6, y + 3 * S + 6), fill=NAVY)
    d.rectangle((x0, y, x1, y + 3 * S), fill=(236, 236, 242))
    xp = x0 + (x1 - x0) * p
    d.rectangle((x0, y, xp, y + 3 * S), fill=(255, 210, 63))
    blit(cv, big('car', 'red', int(t * 12) % 2, s=3), xp, y + 4)

def frame(n):
    t = n / FPS + LEAD
    if t >= AUTH_END - LOOP:
        tt = t - AUTH_END + LEAD
        e = io(prog(t, AUTH_END - LOOP, LOOP))
        last = len(SCENES) - 1
        a = apply_cam(draw_scene(last, t), *camera(t, last)); captions(a, t)
        b = apply_cam(draw_scene(0, tt), *camera(tt, 0)); title(b, tt); captions(b, tt)
        cv = Image.new('RGB', (W, H), BG)
        cv.paste(a, (int(-W * e), 0)); cv.paste(b, (int(W * (1 - e)), 0))
    else:
        cv, idx = world(t)
        cv = apply_cam(cv, *camera(t, idx))
        title(cv, t)
        captions(cv, t)
    progress(cv, n / FPS)
    return cv.tobytes()

SCENE_WHOOSH = [1.73, 2.66, 4.0, 6.5, 8.6, 11.36, 13.3]
CUES = [
    (0.8, 'whoosh', 0.9), (0.8, 'creak', 0.7), (0.84, 'sparkle', 0.8), (0.9, 'stamp', 1.0), (0.92, 'thump', 0.7),
    (1.51, 'thump', 0.8), (1.52, 'creak', 0.6),
    (1.88, 'pop', 0.7), (2.01, 'stamp', 1.0), (2.15, 'pop', 0.5),
    (2.8, 'pop', 0.7), (3.04, 'thump', 0.8), (3.42, 'poof', 0.8),
    (4.15, 'pop', 0.6), (4.27, 'pop', 0.8), (5.73, 'pop', 0.7),
    (6.65, 'pop', 0.7), (6.88, 'creak', 0.9), (7.75, 'stamp', 1.0), (7.77, 'boom', 0.4),
    (8.72, 'vroom', 0.6), (9.3, 'thump', 0.6), (9.42, 'pop', 0.7), (10.2, 'click', 1.0), (10.34, 'click', 1.0), (10.48, 'click', 1.0),
    (10.22, 'pop', 0.5), (10.64, 'pop', 0.7), (10.93, 'ding', 0.9), (10.96, 'sparkle', 0.7),
    (11.55, 'pop', 0.7), (12.0, 'thump', 0.4), (12.63, 'pop', 0.7), (12.66, 'ding', 0.9), (12.7, 'sparkle', 0.7),
    (13.5, 'pop', 0.7), (14.38, 'pop', 0.8), (15.08, 'poof', 0.8), (15.12, 'pop', 0.6),
    (17.5, 'whoosh', 0.7), (17.75, 'creak', 0.5),
    (15.6, 'confetti', 1.0), (15.62, 'pop', 0.8), (15.7, 'sparkle', 0.8), (16.0, 'pop', 0.5), (16.4, 'confetti', 0.6),
] + [(t, "whoosh", 0.6) for t in SCENE_WHOOSH] + [(10.6 + i * 0.12, "sparkle", 0.25) for i in range(3)] + [(4.3 + i * 1.3 / 13, 'pop', 0.22) for i in range(14)] \
  + [(2.05 + i * 0.6 / 17, 'pop', 0.18) for i in range(18)]

def build_audio(vo_path, out_wav):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', vo_path, '-ar', str(sfx.SR), '-ac', '1', '-f', 'f32le', '-'],
                         capture_output=True, check=True).stdout
    vo = np.frombuffer(raw, np.float32).astype(np.float64)
    n = int(sfx.SR * DUR)
    mix = np.zeros(n); m = min(n, len(vo)); mix[:m] = vo[:m]
    fx = sfx.render([(c - LEAD, nm, v) for c, nm, v in CUES if c >= LEAD], DUR)
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
