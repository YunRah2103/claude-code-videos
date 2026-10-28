"""Renders the 'Car stuff, explained' TikTok on why the engine revs up when the air con turns on, synced to the voiceover."""
import json, math, os, sys, subprocess
from functools import lru_cache
from multiprocessing import Pool
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFont
import pix, sfx

W, H, FPS, S = 1080, 1920, 60, 9
GROUND = 1180
DUR = 17.1
BG = (255, 255, 255)
NAVY = (26, 26, 46)
VO_OFF = 0.0  # the voice starts on frame 0 so the hook lands immediately
LEAD = VO_OFF
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
    if w <= 2 * S: return  # prop still popping in
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

HOPS = [1.88, 4.25, 9.4, 11.3]

def hop(t):
    # (lift, sx, sy): crouch, jump, squash on landing
    for t0 in HOPS:
        dt = t - t0
        if 0 <= dt < 0.08:
            k = 0.07 * dt / 0.08; return 0.0, 1 + k, 1 - k
        if 0.08 <= dt < 0.4:
            u = (dt - 0.08) / 0.32; return -120 * math.sin(math.pi * u), 0.95, 1.06
        if 0.4 <= dt < 0.54:
            k = 0.08 * math.sin(math.pi * (dt - 0.4) / 0.14); return 0.0, 1 + k, 1 - k
    return 0.0, 1.0, 1.0

def guy(cv, t, cx, expr='smile', sx=1.0, sy=1.0, lift=0.0, npc=False, scale=1.0, bob=True, poses=None):
    hl, hx, hy = hop(t)
    squash = (hx, hy) != (1.0, 1.0)
    lift += hl; sx *= hx; sy *= hy
    shadow(cv, cx, 260 * sx * scale, 1 - min(1, abs(lift) / 400))
    b = idle_bob(t) if bob and sy == 1 else 0
    pose = pick_pose(t, expr, poses) if sy > 0.9 or squash else 'down'
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
    d = ImageDraw.Draw(cv); R = r * k; rot = dt * 22
    for i in range(10):
        a0 = rot + i * 36
        d.pieslice((x - R, y - R, x + R, y + R), a0, a0 + 14, fill=col)

def ring(cv, t, t0, x, y, col, life=0.35, r1=330):
    dt = t - t0
    if dt < 0 or dt > life: return
    p = oc(dt / life); R = 40 + r1 * p
    ImageDraw.Draw(cv).ellipse((x - R, y - R, x + R, y + R), outline=col, width=max(3, int(3 * S * (1 - p))))

def jelly(t, t0):
    dt = t - t0
    return math.exp(-dt * 9) * math.sin(dt * 32) if dt > 0 else 0.0

PALE_Y, PALE_R, PALE_G = (255, 248, 220), (255, 237, 237), (231, 250, 235)

def stamp_at(cv, t, t0, text, x, y, rot=-10, s=12, col='#e0303a'):
    # red stamp with white fill so it reads over props; lands with a jelly wobble and shockwave
    if t < t0: return
    ks = slam(t, t0, 0.14, 1.8); j = 0.09 * jelly(t, t0 + 0.14)
    ring(cv, t, t0 + 0.12, x, y, (255, 210, 63))
    blit(cv, big('stamp', text, col, '#ffffff', s=s), x, y, ks * (1 + j), ks * (1 - j), rot, anchor='center')

def snap(v): return round(v / S) * S

# ------------------------------------------------------------------ dashboard
DX, DY = 690, 858          # dash panel centre; rev counter sits 87 px above it, A/C button 213 px below
IDLE = 205                 # needle angle at normal idle (225 = zero)

@lru_cache(None)
def panel_img():
    img = Image.new('RGBA', (450, 626), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, 449, 625), 44, fill=NAVY)
    d.rounded_rectangle((9, 9, 440, 616), 36, fill=(58, 59, 68))
    d.rectangle((54, 20, 396, 28), fill=(93, 99, 110))
    for i in range(4):
        y = 470 + i * 30
        d.rectangle((30, y, 100, y + 12), fill=(30, 31, 38)); d.rectangle((350, y, 420, y + 12), fill=(30, 31, 38))
    return img

def wob(t, t0s, amt=0.1):
    # squash/stretch pair from a jelly wobble started at each time in t0s
    j = amt * sum(jelly(t, a) for a in t0s)
    return 1 + j, 1 - j

def dash(cv, t, deg, k=1.0, ac=True, jel=()):
    if k <= 0.02: return
    jx, jy = wob(t, jel, 0.06)
    shadow(cv, DX, 470 * k * jx)
    blit(cv, panel_img(), DX, GROUND - 12, k * jx, k * jy)
    ty = GROUND - 12 - (GROUND - 12 - (DY - 87)) * k * jy
    blit(cv, big('tacho', int(round(deg)), s=8), DX, ty, k * jx, k * jy, anchor='center')
    by = GROUND - 12 - (GROUND - 12 - (DY + 213)) * k * jy
    blit(cv, big('acbtn', ac, s=7), DX, by, k * jx, k * jy, anchor='center')

@lru_cache(None)
def disc_mask(r):
    m = Image.new('L', (2 * r, 2 * r), 0)
    ImageDraw.Draw(m).ellipse((0, 0, 2 * r - 1, 2 * r - 1), fill=255)
    return m

def glint(cv, t, t0, cx=DX, cy=DY - 87, r=172, life=0.45):
    # diagonal shine sweeping across the dial glass
    if not (t0 <= t < t0 + life): return
    u = io((t - t0) / life)
    band = Image.new('L', (2 * r, 2 * r), 0); d = ImageDraw.Draw(band)
    x = -1.4 * r + 4 * r * u
    for off, w, a in ((0, 46, 120), (70, 18, 90)):
        d.polygon([(x + off, 0), (x + off + w, 0), (x + off + w - 1.2 * r, 2 * r), (x + off - 1.2 * r, 2 * r)], fill=a)
    band = ImageChops.multiply(band, disc_mask(r))
    cv.paste(Image.new('RGB', (2 * r, 2 * r), (255, 255, 255)), (int(cx - r), int(cy - r)), band)

def burst(cv, t, t0, x, y, col=(255, 210, 63), n=12, life=0.42, r0=150, r1=430, seed=71):
    # impact lines flying outward on a key hit
    dt = t - t0
    if dt < 0 or dt > life: return
    p = oc(dt / life); d = ImageDraw.Draw(cv); r = rng_for(seed)
    for i in range(n):
        a = i / n * 2 * math.pi + r.uniform(-0.15, 0.15)
        R = r0 + (r1 - r0) * p * r.uniform(0.8, 1.15); L = 70 * (1 - p) + 12
        x0, y0 = x + R * math.cos(a), y + R * math.sin(a)
        x1, y1 = x + (R + L) * math.cos(a), y + (R + L) * math.sin(a)
        wd = int(2 * S * (1 - p)) + 4
        d.line((x0, y0, x1, y1), fill=NAVY, width=wd + 6)
        d.line((x0, y0, x1, y1), fill=col, width=wd)

def spring(t, t0, frm, to, w=17, damp=5):
    # needle snaps to a new angle with a springy overshoot
    if t < t0: return frm
    dt = t - t0
    return to + (frm - to) * math.exp(-dt * damp) * math.cos(dt * w)

def shiver(t): return 1.3 * math.sin(t * 31) + 0.6 * math.sin(t * 53)

def flakes(cv, t, t0, x, y, n=9, seed=61, spread=300, life=1.5, rise=420):
    if t < t0: return
    r = rng_for(seed)
    for i in range(n):
        ph = r.uniform(0, 1); vx = r.uniform(-1, 1) * spread
        dt = t - t0 - ph * 0.5
        if dt < 0: continue
        u = (dt % life) / life
        px = x + vx * u + 22 * math.sin(dt * 5 + i); py = y - rise * u
        k = math.sin(math.pi * u) * (0.8 + 0.4 * (i % 2))
        blit(cv, big('snowflake', s=5), px, py, k, k, anchor='center')

def rev_marks(cv, t, t0, x, y, r=250, life=0.7):
    # yellow motion squares flicking off the dial when it revs
    if not (t0 <= t < t0 + life) or int(t * 20) % 2 == 0: return
    d = ImageDraw.Draw(cv)
    for a in (-160, -125, -90, -55, -20):
        rr = r + 40 * prog(t, t0, life)
        x0, y0 = x + rr * math.cos(math.radians(a)), y + rr * math.sin(math.radians(a))
        d.rectangle((x0 - S, y0 - S, x0 + S, y0 + S), fill=(255, 210, 63), outline=NAVY, width=3)

def glow_arc(cv, t, t0, a0, a1, k=1.0):
    # green band on the bezel showing how far the idle rose
    if t < t0: return
    p = oc(prog(t, t0, 0.35)) * k
    d = ImageDraw.Draw(cv); R = 212; cx, cy = DX, DY - 87
    d.arc((cx - R, cy - R, cx + R, cy + R), 360 - a0, 360 - a0 + (a0 - a1) * p, fill=NAVY, width=30)
    d.arc((cx - R + 6, cy - R + 6, cx + R - 6, cy + R - 6), 360 - a0, 360 - a0 + (a0 - a1) * p, fill=(60, 200, 90), width=18)

def vroom(cv, t, t0, x, y):
    if t < t0 or t > t0 + 1.0: return
    k = popin(t, t0, 0.2) * (1 - ic(prog(t, t0 + 0.8, 0.2)))
    blit(cv, big('label', 'VROOM', '#ffd23f', s=9), x, y, k, k, swing(t, t0, 10, 2.0), anchor='center')

# 1. hook: AC clicks on, the needle jumps
def scene_hook(cv, t):
    rays(cv, t, 1.88, DX, DY - 87, PALE_Y, life=1.0, r=600)
    deg = IDLE + shiver(t)
    if t >= 1.05: deg = spring(t, 1.05, IDLE, IDLE + 8, 14, 8) + shiver(t)  # load bogs it a touch...
    if t >= 1.88: deg = spring(t, 1.88, IDLE + 8, 176) + shiver(t)          # ...then idle kicks up
    ring(cv, t, 1.9, DX, DY - 87, (255, 210, 63), life=0.4, r1=300)
    dash(cv, t, deg, 1.0, t >= 0.57, (1.88, 0.57))
    glint(cv, t, 0.15); glint(cv, t, 2.05)
    burst(cv, t, 1.88, DX, DY - 87)
    ring(cv, t, 0.57, DX, DY + 213, (127, 212, 255), life=0.35, r1=200)
    flakes(cv, t, 0.62, DX, DY + 200, seed=61)
    if t >= 0.57:
        kc = popin(t, 0.57, 0.22) * (1 - ic(prog(t, 1.6, 0.2)))
        blit(cv, big('label', 'CLICK!', '#e0303a', s=8), DX - 160, DY + 90, kc, kc, -10 + 3 * math.sin(t * 6), anchor='center')
    sparkles(cv, t * 1.5, DX, DY - 87, 560, 480, n=12, seed=2)
    rev_marks(cv, t, 1.88, DX, DY - 87)
    vroom(cv, t, 1.9, DX - 30, DY - 330)
    if t >= 1.88:
        kx = popin(t, 1.88, 0.22) * (1 + 0.08 * math.sin(t * 14))
        blit(cv, big('glyph', '!', '#e0303a', s=12), 210, GROUND - 620, kx, kx, -8, anchor='center')
    expr = 'shock' if 1.88 <= t < 2.4 else 'smile'
    guy(cv, t, 230, expr, poses=[(-1, 1.85, 'point'), (1.88, 2.4, 'shock'), (2.4, 3.0, 'hips')])

# 2. don't worry, it's not broken
def scene_ok(cv, t):
    cx = 680
    rays(cv, t, 3.81, cx, GROUND - 330, PALE_R, life=0.6)
    rays(cv, t, 4.25, cx, GROUND - 330, PALE_G, life=0.6)
    k = popin(t, 2.62, 0.3)
    jx = 3 * math.sin(t * 60) if t < 3.81 else 0
    shadow(cv, cx, 420 * k)
    wx, wy = wob(t, (2.86, 3.81))
    blit(cv, big('car', 'red', 0, s=8), cx + jx, GROUND, k * wx, k * wy)
    burst(cv, t, 3.81, cx - 10, GROUND - 400, (224, 48, 58), seed=72)
    burst(cv, t, 4.25, cx + 170, GROUND - 160, (60, 200, 90), n=10, r0=80, r1=260, seed=73)
    for i, (dx, dy, t0) in enumerate(((-150, -330, 2.88), (0, -420, 3.0), (150, -330, 3.12))):
        if t0 <= t < 3.81:
            kq = popin(t, t0, 0.25)
            blit(cv, big('glyph', '?', '#e0303a', s=11), cx + dx, GROUND + dy + 10 * math.sin(t * 7 + i), kq, kq, 8 * math.sin(t * 5 + i), anchor='center')
    stamp_at(cv, t, 3.81, 'NOT BROKEN', cx - 10, GROUND - 400, -8, 8)
    if t >= 4.25:
        kc = popin(t, 4.25)
        blit(cv, big('check', s=12), cx + 170, GROUND - 160, kc, kc, anchor='center')
        gsparkles(cv, t, cx, GROUND - 300, 560, 420, n=12, seed=37)
    guy(cv, t, 230, 'smile', poses=[(2.62, 2.88, 'point'), (2.88, 3.8, 'shrug'), (3.81, 4.25, 'hips'), (4.25, 5.0, 'thumb')])

# 3. the compressor adds load
EX, EP = 720, (570, 1065)     # engine centre x; crank pulley centre
CP = (570, 808)               # compressor pulley centre
def belt(cv, t, spin):
    d = ImageDraw.Draw(cv)
    for (x0, r0), x1 in (((CP[0] - 56, 0), EP[0] - 50), ((CP[0] + 56, 0), EP[0] + 50)):
        for w, col in ((2 * S, NAVY), (S, (58, 59, 68))):
            d.line((x0, CP[1], x1, EP[1]), fill=col, width=w * 2)
    off = (t * 600 * spin) % 60
    for side in (-1, 1):
        for j in range(5):
            u = ((j * 60 + off * side) % 300) / 300
            x = CP[0] + side * (56 + (-6) * u); y = CP[1] + (EP[1] - CP[1]) * u
            d.rectangle((x - 4, y - 4, x + 4, y + 4), fill=(160, 166, 178))

def scene_comp(cv, t):
    ke = popin(t, 4.72, 0.3)
    load = t >= 5.65
    jx = 6 * math.sin(t * 55) * math.exp(-(t - 5.65) * 2.5) + (1.5 * math.sin(t * 40) if load else 0) if load else 0
    shadow(cv, EX, 440 * ke)
    wx, wy = wob(t, (4.96, 5.65), 0.08)
    blit(cv, big('engine', s=10), EX + jx, GROUND, ke * wx, ke * wy)
    kc = popin(t, 4.9, 0.3)
    if kc > 0.98: belt(cv, t, 1)
    ring(cv, t, 4.92, CP[0], CP[1] - 90, (127, 212, 255), life=0.35, r1=260)
    cx2, cy2 = wob(t, (5.14,), 0.1)
    blit(cv, big('compressor', int(t * 24) % 12 if t >= 4.9 else 0, s=8), CP[0], CP[1] - 92, kc * cx2, kc * cy2, anchor='center')
    burst(cv, t, 5.65, 830, 760, (224, 48, 58), n=10, r0=90, r1=300, seed=74)
    flakes(cv, t, 5.0, CP[0], CP[1] - 160, n=7, seed=63, spread=200, rise=300)
    kb = popin(t, 4.95)
    blit(cv, big('badge', 'COMPRESSOR', '#3d7fd6', '#ffffff', '#2b5fa8', s=5), CP[0] - 20, CP[1] - 300, kb, kb, -3 + 2 * math.sin(t * 3), anchor='center')
    if load:
        rays(cv, t, 5.65, 820, 760, PALE_R, life=0.6, r=420)
        ka = slam(t, 5.65, 0.14, 1.6) * (1 + 0.1 * math.sin((t - 5.65) * 12))
        blit(cv, big('arrow', s=10), 830, 840 + 14 * math.sin((t - 5.65) * 12), ka, ka, anchor='bottom')
        kl = popin(t, 5.7)
        blit(cv, big('badge', 'LOAD', '#e0303a', '#ffffff', '#b5222c', s=8), 830, 630, kl, kl, swing(t, 5.7, 8), anchor='center')
        if int(t * 20) % 2:
            d = ImageDraw.Draw(cv)
            for i in range(4):  # strain marks around the engine
                a = math.radians(-160 + i * 45); x, y = EX + 300 * math.cos(a), GROUND - 150 + 260 * math.sin(a)
                d.rectangle((x - S, y - S, x + S, y + S), fill=(255, 210, 63), outline=NAVY, width=3)
        dust(cv, t, 5.67, EX + 120, GROUND - 20, n=12, seed=44)
    guy(cv, t, 200, 'smile', poses=[(4.72, 5.6, 'pointup'), (5.65, 6.1, 'shock'), (6.1, 6.6, 'point')])

# 4. so the car raises idle speed
def scene_idle(cv, t):
    rays(cv, t, 6.98, DX, DY - 87, PALE_G, life=0.8, r=560)
    k = popin(t, 6.38, 0.3)
    deg = spring(t, 6.98, IDLE, 188, 15, 6) + shiver(t)
    glow_arc(cv, t, 7.0, IDLE, 188, k)
    dash(cv, t, deg, k, jel=(6.62, 6.98))
    glint(cv, t, 6.7)
    burst(cv, t, 7.42, DX, DY - 400, (60, 200, 90), n=10, r0=120, r1=330, seed=75)
    ring(cv, t, 7.0, DX, DY - 87, (60, 200, 90), life=0.4, r1=280)
    flakes(cv, t, 6.4, DX, DY + 200, n=6, seed=64)
    if t >= 7.42:
        kb = slam(t, 7.42, 0.14, 1.5) * (1 + 0.03 * math.sin(t * 5))
        blit(cv, big('badge', 'IDLE UP', *GREEN, s=8), DX, DY - 400, kb, kb, -4 + 3 * math.sin(t * 3), anchor='center')
        gsparkles(cv, t, DX, DY - 300, 560, 300, n=10, seed=39)
    guy(cv, t, 230, 'smile', poses=[(6.4, 7.4, 'point'), (7.42, 8.2, 'pointup')])

# 5. ...to stop the engine stalling
def scene_stall(cv, t):
    cx = 700
    rays(cv, t, 9.4, cx, GROUND - 200, PALE_G, life=0.8)
    k = popin(t, 8.1, 0.3)
    p = prog(t, 8.1, 0.5)
    x = cx + 500 * (1 - oc(p))
    cough = 8.72 <= t < 9.4
    rot = 7 * math.sin((t - 9.0) * 22) * math.exp(-(t - 9.0) * 4) if t >= 9.0 else 0
    jy = -S * (int(t * 18) % 2) if cough else 0
    shadow(cv, x, 330)
    wx, wy = wob(t, (8.6, 9.4), 0.1)
    blit(cv, big('car', 'red', int(t * 12) % 2 if p < 1 else 0, s=6), x, GROUND + jy, wx, wy, rot)
    burst(cv, t, 9.4, 850, 1010, (60, 200, 90), n=10, r0=70, r1=250, seed=76)
    dust(cv, t, 8.72, x - 170, GROUND - 50, n=14, seed=21, dirx=-420)  # engine coughs
    dust(cv, t, 8.9, x - 170, GROUND - 60, n=10, seed=22, dirx=-380)
    # inset: the raised idle needle keeps it running
    ki = popin(t, 8.3, 0.3)
    if ki > 0.02:
        d = ImageDraw.Draw(cv); r = 150 * ki; ix, iy = 560, 700
        d.ellipse((ix - r, iy - r, ix + r, iy + r), fill=(242, 244, 248), outline=NAVY, width=8)
        blit(cv, big('tacho', int(188 + shiver(t)), s=5), ix, iy, ki, ki, anchor='center')
    if t >= 9.0:
        ks = popin(t, 9.0, 0.22)
        blit(cv, big('tag', 'STALL', '#fff6e0', '#d6303a', t >= 9.4, s=8), 740, 880, ks, ks, swing(t, 9.0, 8), anchor='center')
    if t >= 9.4:
        kc = popin(t, 9.4)
        blit(cv, big('check', s=10), 850, 1010, kc, kc, anchor='center')
        gsparkles(cv, t, cx, GROUND - 260, 600, 400, n=12, seed=38)
    expr = 'shock' if 9.0 <= t < 9.4 else 'smile'
    guy(cv, t, 230, expr, poses=[(8.1, 8.9, 'point'), (9.0, 9.4, 'shock'), (9.4, 10.5, 'thumb')])

# 6. most cars do this automatically
CARS = [(480, 10.49, 'red'), (650, 10.6, 'blue'), (820, 10.71, 'used')]
RB = (650, 700)
def scene_auto(cv, t):
    rays(cv, t, 11.3, *RB, PALE_Y, life=1.2, r=520)
    d = ImageDraw.Draw(cv)
    if t >= 11.5:
        for i, (x, t0, _) in enumerate(CARS):  # signal dots from the ECU to each car
            for j in range(6):
                u = (j / 6 + t * 1.6) % 1
                px, py = RB[0] + (x - RB[0]) * u, RB[1] + 170 + (GROUND - 130 - RB[1] - 170) * u
                d.rectangle((snap(px) - S, snap(py) - S, snap(px) + S, snap(py) + S), fill=(60, 200, 90), outline=NAVY, width=3)
    for i, (x, t0, col) in enumerate(CARS):
        kc = popin(t, t0, 0.28)
        shadow(cv, x, 200 * kc)
        blit(cv, big('car', col, int(t * 10) % 2, s=4), x, GROUND - S * (int(t * 6 + i) % 2), kc, kc)
        if t >= 11.65 + i * 0.15:
            kt = popin(t, 11.65 + i * 0.15)
            blit(cv, big('check', s=6), x, GROUND - 160, kt, kt, anchor='center')
    kr = popin(t, 11.3, 0.3)
    rx, ry = wob(t, (11.55,), 0.1)
    blit(cv, big('robot', (t % 1.7) < 0.12, s=10), RB[0], RB[1] + 12 * math.sin(t * 3), kr * rx, kr * ry, 3 * math.sin(t * 2), anchor='center')
    burst(cv, t, 11.3, *RB, seed=77)
    ring(cv, t, 11.32, *RB, (255, 210, 63), life=0.4, r1=300)
    if t >= 11.3: sparkles(cv, t * 1.5, *RB, 520, 420, n=12, seed=52)
    ka = popin(t, 11.55)
    blit(cv, big('badge', 'AUTO', *GOLD, s=7), 840, 520, ka, ka, 8 + 3 * math.sin(t * 4), anchor='center')
    guy(cv, t, 230, 'smile', poses=[(10.4, 11.25, 'point'), (11.3, 12.6, 'pointup')])

# 7. payoff: the rev counter jumps again, that's normal
def scene_end(cv, t):
    rays(cv, t, 13.98, DX, DY - 87, PALE_Y, life=0.9, r=600)
    rays(cv, t, 15.03, DX, DY - 87, PALE_G, hold=True, r=640)
    k = popin(t, 12.52, 0.3)
    deg = spring(t, 13.98, IDLE, 176) + shiver(t)
    dash(cv, t, deg, k, jel=(12.76, 13.98, 15.03))
    glint(cv, t, 12.85); glint(cv, t, 14.15)
    burst(cv, t, 13.98, DX, DY - 87, seed=78)
    burst(cv, t, 15.03, DX, DY - 100, (60, 200, 90), n=14, seed=79)
    ring(cv, t, 14.0, DX, DY - 87, (255, 210, 63), life=0.4, r1=300)
    flakes(cv, t, 12.6, DX, DY + 200, n=7, seed=65)
    rev_marks(cv, t, 13.98, DX, DY - 87)
    vroom(cv, t, 14.0, DX - 30, DY - 330)
    if t >= 15.03:
        gsparkles(cv, t, DX, DY - 100, 640, 600, n=14, seed=49)
        ring(cv, t, 15.1, DX, DY - 87, (60, 200, 90), life=0.45, r1=420)
        stamp_at(cv, t, 15.03, 'NORMAL', DX, DY - 100, -8, 11, '#2a9a45')
    if t >= 15.8:
        kn = popin(t, 15.8, 0.3)
        blit(cv, big('badge', 'NEXT EPISODE', *GOLD, s=6), 500, 430, kn, kn, -4 + 3 * math.sin(t * 3), anchor='center')
        kq = popin(t, 16.0, 0.25) * (1 + 0.1 * math.sin(t * 9))
        blit(cv, big('glyph', '?', '#e0303a', s=12), 830, 430, kq, kq, 8 * math.sin(t * 6), anchor='center')
    lift = -150 * math.sin(math.pi * prog(t, 15.35, 0.42)) if 15.35 <= t < 15.77 else 0
    guy(cv, t, 230, 'smile', lift=lift, poses=[(13.4, 13.98, 'point'), (13.98, 15.0, 'hips'), (15.03, 18.0, 'thumb')])
    if t >= 15.35:
        confetti(cv, t, 15.35, 300, 700, n=50, seed=4)
        confetti(cv, t, 15.4, 800, 640, n=44, seed=8, spread=0.9)
        confetti(cv, t, 16.1, 560, 600, n=40, seed=9, spread=1.1)

SCENES = [(0.0, scene_hook), (2.62, scene_ok), (4.72, scene_comp), (6.38, scene_idle),
          (8.08, scene_stall), (10.38, scene_auto), (12.52, scene_end)]

TR_PRE, TR_LEN = 0.1, 0.26

def draw_scene(i, t):
    cv = Image.new('RGB', (W, H), BG)
    SCENES[i][1](cv, t)
    return cv

def speed_lines(cv, e, seed):
    k = math.sin(math.pi * e)
    if k < 0.1: return
    r = rng_for(100 + seed); d = ImageDraw.Draw(cv)
    for i in range(16):
        y = snap(r.uniform(260, 1700)); L = r.uniform(220, 640) * k; x = r.uniform(-200, W)
        d.rectangle((x, y, x + L, y + S * (1 + i % 2)), fill=(205, 210, 222))

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
        speed_lines(cv, e, idx)
        return cv, idx
    return draw_scene(idx, t), idx

# ------------------------------------------------------------------ camera
SHAKES = [(-0.02, 0.25, 12), (1.88, 0.4, 26), (3.81, 0.3, 22), (5.65, 0.35, 18), (9.0, 0.3, 16), (11.3, 0.2, 10),
          (13.98, 0.4, 26), (15.03, 0.3, 20)]
PUNCH = [(15.03, 17.6, 1.05, 690, 800)]  # eases out during the loop slide
# instant zoom kicks that ease back: (time, amount, anchor x, anchor y)
KICKS = [(-0.02, 0.14, 690, 800), (0.57, 0.06, 690, 1070), (1.88, 0.16, 690, 770), (2.2, 0.05, 690, 800),
         (2.88, 0.04, 600, 900), (3.81, 0.12, 670, 820), (4.25, 0.06, 760, 1000), (4.9, 0.08, 560, 700),
         (5.65, 0.12, 780, 800), (6.98, 0.08, 690, 770), (7.42, 0.06, 690, 560), (8.72, 0.04, 600, 1100),
         (9.0, 0.1, 760, 900), (9.4, 0.07, 800, 1000), (10.49, 0.04, 480, 1100), (10.71, 0.04, 820, 1100),
         (11.3, 0.1, 650, 700), (11.65, 0.04, 650, 1000), (13.48, 0.05, 690, 800), (13.98, 0.16, 690, 770),
         (15.03, 0.14, 690, 770), (15.35, 0.06, 560, 700)]
BASE_Z, BASE_A = 1.0, (540, 1000)  # wide shot: room to breathe, props clear of TikTok's right-hand buttons


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
EMPH = {'con', 'revs', 'broken', 'compressor', 'load', 'idle', 'stalling', 'automatically', 'jump', 'normal'}

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


TFONT = font(80)

@lru_cache(None)
def title_img():
    lines = [('car stuff, explained', (255, 255, 255), 80, 0), ('AC REVS UP?', (255, 90, 90), 124, 96)]
    img = Image.new('RGBA', (1000, 260), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for txt, col, sz, y in lines:
        f = font(sz)
        w = d.textlength(txt, font=f)
        d.text((500 - w / 2 + 6, y + 8), txt, font=f, fill=NAVY, stroke_width=14, stroke_fill=NAVY)
        d.text((500 - w / 2, y), txt, font=f, fill=col, stroke_width=13, stroke_fill=(10, 10, 16))
    return img

def title(cv, t):
    if t >= 2.0: return
    k = ob(prog(t, -0.22, 0.22)) * (1 - ic(prog(t, 1.6, 0.25)))
    if k <= 0.02: return
    img = title_img()
    rot = 3 * math.sin(t * 4)
    img = img.resize((int(img.width * k), int(img.height * k)), Image.BILINEAR).rotate(rot, resample=Image.BICUBIC, expand=True)
    cv.paste(img, (int(W / 2 - img.width / 2), int(370 - img.height / 2)), img)

@lru_cache(None)
def end_img():
    lines = [('car stuff, explained', (255, 255, 255), 76, 0), ('follow for the next one', (255, 217, 59), 96, 88)]
    img = Image.new('RGBA', (1300, 240), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for txt, col, sz, y in lines:
        f = font(sz); w = d.textlength(txt, font=f)
        d.text((650 - w / 2 + 6, y + 8), txt, font=f, fill=NAVY, stroke_width=14, stroke_fill=NAVY)
        d.text((650 - w / 2, y), txt, font=f, fill=col, stroke_width=13, stroke_fill=(10, 10, 16))
    bb = img.getbbox(); img = img.crop((bb[0] - 10, 0, bb[2] + 10, 240))
    if img.width > 1000:
        img = img.resize((1000, int(240 * 1000 / img.width)), Image.LANCZOS)
    return img

END_T = max(15.6, WORDS[-1]['e'] + 0.1)

def captions(cv, t):
    if t >= END_T:
        img = end_img(); k = 0.72 + 0.28 * ob(prog(t, END_T, 0.16))
        k *= 1 + 0.03 * math.sin((t - END_T) * 6)
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
            dy = 18 * (1 - ob(prog(t, st, 0.2)))
            if active is not None: dy -= 12 * math.exp(-(t - WORDS[active]['s'] + 0.04) * 16)
            if k != 1:
                img = img.resize((int(img.width * k), int(img.height * k)), Image.BILINEAR)
            cv.paste(img, (int(W / 2 - img.width / 2), int(1390 + dy - img.height / 2)), img)
            return
# ------------------------------------------------------------------ frame + audio
LOOP = 0.3  # final slide back into the opening frame so the clip loops seamlessly
AUTH_END = DUR + LEAD

def progress(cv, t):
    p = clamp(t / DUR)
    d = ImageDraw.Draw(cv)
    x0, x1, y, h = 100, W - 100, 120, 4 * S
    d.rounded_rectangle((x0 - 7, y - 7, x1 + 7, y + h + 7), 22, fill=NAVY)
    d.rounded_rectangle((x0, y, x1, y + h), 16, fill=(236, 236, 242))
    xp = x0 + (x1 - x0) * p
    if xp > x0 + 32:
        d.rounded_rectangle((x0, y, xp, y + h), 16, fill=(255, 210, 63))
        d.rectangle((x0 + 16, y + 7, xp - 16, y + 13), fill=(255, 238, 160))
    for tc, _ in SCENES[1:]:
        xc = x0 + (x1 - x0) * tc / DUR; yc = y + h / 2
        on = t >= tc
        r = 12 * (1 + 0.6 * math.exp(-(t - tc) * 10) if on else 1)
        d.ellipse((xc - r - 6, yc - r - 6, xc + r + 6, yc + r + 6), fill=NAVY)
        d.ellipse((xc - r, yc - r, xc + r, yc + r), fill=(60, 200, 90) if on else (200, 204, 212))
    blit(cv, big('car', 'red', int(t * 12) % 2, s=3), xp, y + 8 - S * (int(t * 8) % 2))

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

SCENE_WHOOSH = [2.5, 4.6, 6.26, 7.96, 10.26, 12.4, 16.8]
CUES = [
    (0.0, 'whoosh', 0.7), (0.0, 'sparkle', 0.6), (0.57, 'click', 1.0), (0.6, 'pop', 0.7), (0.64, 'sparkle', 0.5),
    (1.05, 'thump', 0.4), (1.88, 'vroom', 0.9), (1.88, 'boom', 0.35), (1.9, 'pop', 0.6), (1.95, 'sparkle', 0.8),
    (2.62, 'pop', 0.7), (2.88, 'pop', 0.5), (3.0, 'pop', 0.5), (3.12, 'pop', 0.5),
    (3.81, 'stamp', 1.0), (3.83, 'thump', 0.6), (4.25, 'ding', 0.9), (4.28, 'sparkle', 0.7),
    (4.72, 'pop', 0.7), (4.9, 'pop', 0.8), (4.95, 'pop', 0.5), (4.97, 'sparkle', 0.5),
    (5.65, 'thump', 0.9), (5.66, 'boom', 0.3), (5.7, 'pop', 0.7),
    (6.4, 'pop', 0.7), (6.98, 'vroom', 0.45), (7.0, 'sparkle', 0.6), (7.42, 'pop', 0.8),
    (8.1, 'vroom', 0.35), (8.3, 'pop', 0.6), (8.72, 'poof', 0.5), (8.9, 'poof', 0.35), (9.0, 'pop', 0.8), (9.02, 'thump', 0.5),
    (9.4, 'click', 0.7), (9.4, 'ding', 0.9), (9.43, 'sparkle', 0.7),
    (10.49, 'pop', 0.6), (10.6, 'pop', 0.6), (10.71, 'pop', 0.6), (11.3, 'pop', 0.9), (11.32, 'sparkle', 0.9), (11.55, 'pop', 0.6),
    (11.65, 'ding', 0.45), (11.8, 'ding', 0.5), (11.95, 'ding', 0.6),
    (12.52, 'pop', 0.7), (13.48, 'pop', 0.4), (13.98, 'vroom', 0.9), (13.98, 'boom', 0.35), (14.0, 'sparkle', 0.8),
    (15.03, 'stamp', 1.0), (15.06, 'ding', 0.9), (15.08, 'sparkle', 0.8),
    (15.35, 'confetti', 1.0), (15.62, 'pop', 0.6), (15.8, 'pop', 0.7), (16.0, 'pop', 0.5), (16.1, 'confetti', 0.6),
] + [(t, 'whoosh', 0.6) for t in SCENE_WHOOSH]

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
