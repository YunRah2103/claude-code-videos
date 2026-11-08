"""'car stuff, explained': the seatbelt pretensioner, cinematic illustrated 2.5D (loops, 15.0 s, 1080x1920, 60 fps).

Reuses the seatbelt-stickman voiceover + faster-whisper words.json (same script). Shots:
  1 hook   0.00  dusk proving ground, push-in on the orange hatchback racing at a barrier (already moving on frame 0);
                 headline 'Your seatbelt can TIGHTEN by itself' (no captions while it is up)
  2 cut    ~2.95 camera glides into the cabin cutaway: glowing retractor + PRETENSIONER pill, slack belt snaps snug with
                 a flash; the guy points, jumps at the snap, thumbs-up; framed real photo card slides in
  3 crash  ~8.25 full-width slow-mo crash, pass 1 WITHOUT PRETENSIONER (dummy lurches), wipe, pass 2 WITH (SNUG, SAFE)
  4 ask    ~12.95 pull back to the guy: steps back surprised, turns to camera, asks; poll YES / NO; loops to shot 1
    python render.py still <dir> t... | cover <png> | checks | video <out.mp4> [t0 t1]
"""
import json, math, os, subprocess, sys, wave
from functools import lru_cache
from multiprocessing import Pool
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'shared')); sys.path.insert(0, os.path.join(ROOT, 'shared', 'assets'))
from audio import sfx
from pixanim.motion import prog, clamp, oc, io, ob, ic
from stickman.vec import Layer, hexc, SS
from stickman import car as SC, physics as Ph, fx as FX, stage as ST
from cinematic import scene as SN, post as PO, cards as CD
from cinematic.car import draw_car
from cinematic.guy import Guy, draw_guy, blend_pose, aim, joints
from cinematic.paint import glow, comp

W, H, FPS = 1080, 1920, 60
DUR = 15.0
OUT = os.path.join(ROOT, 'out', 'seatbelt-cinematic')
WORDS = json.load(open(os.path.join(HERE, 'words.json')))
def ws(i): return WORDS[i]['s']

T2, T3, T4, TL = ws(6) - 0.19, ws(23) - 0.09, ws(36) - 0.19, 14.8
TIGHT, CHG, MOT, PULL, SNUG, FRAC = ws(3), ws(11), ws(13), ws(14), ws(16), ws(19)
IA, WB, IB = 8.62, 10.1, 10.42          # impact (pass 1), wipe, impact (pass 2)
L_WITH, L_SNUG, L_SAFE = (WB + 0.05, 10.95), (11.0, 11.85), (11.9, T4)
TAP_T = 14.2
SX, SY = 459, 1105                      # caption centre (left 85 %, above 62 %)
RED, YEL, WHITE, NAVY = (232, 52, 63), (255, 201, 40), (255, 255, 255), (26, 26, 46)
SPEED = 2800.0
FONT_PATH = '/usr/share/fonts/opentype/inter/Inter-Black.otf'
PHOTO = os.path.join(HERE, '..', 'assets', 'photo.jpg')
CREDITS = os.path.join(HERE, '..', 'assets', 'credits.json')


def font(sz):
    try: return ImageFont.truetype(FONT_PATH, sz)
    except OSError: return ImageFont.load_default(size=sz)


# ------------------------------------------------------------------ voice-driven mouth
@lru_cache(1)
def _env():
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', os.path.join(OUT, 'voiceover.wav'), '-ac', '1', '-ar', '24000', '-f', 'f32le', '-'],
                         capture_output=True, check=True).stdout
    a = np.frombuffer(raw, np.float32); hop = 24000 // FPS
    e = np.array([np.sqrt(np.mean(a[i:i + hop * 2] ** 2)) for i in range(0, len(a), hop)])
    e = e / (np.percentile(e, 95) + 1e-9)
    return np.convolve(e, np.ones(3) / 3, mode='same')


def mouth(t):
    e = _env(); i = int(t * FPS)
    return float(np.clip((e[i] - 0.12) / 0.7, 0, 1)) if 0 <= i < len(e) else 0.0


def blink(t): return 1.0 if (t + 0.4) % 3.3 < 0.08 else 0.0


# ------------------------------------------------------------------ dummy + cabin
REST = Ph.crash(True)[0]


def seated(t, back=0.0):
    bob = 0.12 * math.sin(t * 23) + 0.06 * math.sin(t * 37)
    return {k: (v[0] - back * (0.6 if k in ('neck', 'head', 'sh', 'chest') else 0.15), v[1] + bob) if isinstance(v, tuple) else v
            for k, v in REST.items()}


def cabin(j, slack, glow_b=0.0, spin=0.0, charge=0.0, motor=0.0, spark=-1.0):
    from stickman import rig as R

    def fn(Q):
        SC.draw_seat(Q); R.draw_dummy(Q, j, 3.4); SC.draw_wheel_col(Q)
        SC.draw_belt(Q, j['chest'], slack, glow_b, j['hip']); SC.draw_retractor(Q, spin, charge, motor)
        if spark >= 0: FX.spark(Q, (SC.RETRACTOR[0], SC.RETRACTOR[1] + 3), spark, 3.4)
    return fn


def ghosts(L, ox, oy, s, n, dx, a0=70):
    for k in range(n, 0, -1):
        L.pen(ox - dx * k, oy, s).fillpoly(SC.body_pts(), (239, 122, 50, int(a0 / k)))


def guy_at(L, x, y, s, g):
    return draw_guy(L.pen(x, y, s), g)


# ------------------------------------------------------------------ shot 1: hook
def car1_xs(tt): return 520 - 1450 * (1 - oc(prog(tt, -0.35, 0.72))) + 14 * math.sin(tt * 1.4)


def cam1(tt):
    z = 1.0 + 0.3 * io(prog(tt, -0.35, 3.3))
    return SN.Cam(sx=SPEED * tt, z=z, fx=540, fy=1580)


def shot_hook(tt):
    cam = cam1(tt)
    img = SN.backdrop(cam, 1.0)
    L = Layer(W, H)
    FX.speed_lines(L.pen(), tt, (0, 1240, W, 1890), 26, 3, 3.4, (255, 236, 210, 150), 6)
    FX.speed_lines(L.pen(), tt + 0.3, (0, 700, W, 1150), 8, 13, 2.2, (255, 220, 190, 70), 4)
    xs = car1_xs(tt); v = (car1_xs(tt + 0.01) - car1_xs(tt - 0.01)) / 0.02; vn = clamp(v / 1600)
    ox, oy = cam.fx + (xs - cam.fx) * cam.z, cam.fy + (SN.GY - cam.fy) * cam.z
    s = 11.0 * cam.z
    bxs = 1330 - 230 * oc(prog(tt, 1.85, 1.05))
    if tt > 1.75:
        ST.barrier(L.pen(cam.fx + (bxs - cam.fx) * cam.z, oy, s), 0, 0)
        glow(L.pen(cam.fx + (bxs - cam.fx) * cam.z, oy, s), (14, -18), 16, (255, 190, 90), 0.25)
    if vn > 0.1: ghosts(L, ox, oy, s, 3, 55 * vn)
    k = io(prog(tt, TIGHT - 0.05, 0.16))
    j = seated(tt, back=0.5 * k)
    gl = math.exp(-max(0, tt - TIGHT) * 2.2) * (tt > TIGHT - 0.05)
    draw_car(L.pen(ox, oy + 1.2 * math.sin(tt * 40), s), 0, 'glass', cabin(j, 1.6 * (1 - k), gl), blur=1.0, lights=1.0)
    if gl > 0.02: glow(L.pen(ox, oy, s), j['chest'], 12, (255, 200, 90), 0.9 * gl)
    img.alpha_composite(L.done())
    img.alpha_composite(SN.foreground(cam, 1.0))
    return img, dict(cam=cam)


# ------------------------------------------------------------------ shot 2: cabin cutaway
def cut_geom(t):
    k = ob(prog(t, T2, 0.7), 1.2)                     # glide with a little overshoot
    k0 = clamp(k, 0, 1.05)
    s = 12.0 + (21.0 - 12.0) * k0
    # cabin point (car -8, -20) from where it sat in shot 1 to its hero position
    c1 = cam1(T2); xs = car1_xs(T2)
    p1 = (c1.fx + (xs - c1.fx) * c1.z - 8 * 10 * c1.z, c1.fy + (SN.GY - c1.fy) * c1.z - 20 * 10 * c1.z)
    p2 = (700, 1430)
    cx, cy = p1[0] + (p2[0] - p1[0]) * k0, p1[1] + (p2[1] - p1[1]) * k0
    return cx + 8 * s, cy + 20 * s, s, k0


def shot_cut(t):
    ox, oy, s, k0 = cut_geom(t)
    cam = SN.Cam(sx=SPEED * T2 + 650 * (t - T2), z=1.2 + 0.8 * k0, fx=700, fy=1430)
    img = SN.backdrop(cam, 1.0 + 2.2 * k0)
    L = Layer(W, H)
    FX.speed_lines(L.pen(), t, (0, 1250, W, 1880), 10, 5, 1.6, (255, 236, 210, 80), 5)
    pull = io(prog(t, PULL, SNUG - PULL + 0.04))
    snap = math.exp(-max(0, t - SNUG) * 6) * (t > SNUG - 0.02)
    j = seated(t, back=0.55 * pull + 0.3 * snap)
    spin = -(t - PULL) * 24 * pull if t > PULL else 0.0
    chg, mot = ob(prog(t, CHG - 0.06, 0.25)), ob(prog(t, MOT - 0.06, 0.25))
    pulse = 0.55 + 0.25 * math.sin(t * 7)
    gret = clamp((t - T2 - 0.5) / 0.4) * (pulse + 1.2 * snap)
    P = L.pen(ox, oy + 0.8 * math.sin(t * 40), s)
    spark = (t - CHG) * 1.3 if t > CHG else -1
    draw_car(P, 0, 'cut', cabin(j, 1.6 * (1 - pull), 0.3 * pull + 1.2 * snap, spin, chg, mot, spark), blur=1.0, glow_ret=gret)
    if t > SNUG - 0.02: FX.burst(P, (j['chest'][0] - 1, j['chest'][1] + 1), t - SNUG, 4.5, 0.4)
    rp = P.p(SC.RETRACTOR); rp = (rp[0] / SS, rp[1] / SS)
    # the guy: points at the retractor, jumps at the snap, thumbs-up on 'fraction'
    gk = ob(prog(t, T2 + 0.25, 0.45))
    g = Guy(pose='point', expr='talk', mouth=mouth(t), blink=blink(t), look=(0.6, 0.2))
    if t > SNUG - 0.05 and t < SNUG + 0.7:
        g = Guy(pose='surprised', expr='surprised', brow=1.0, step=-2.5 * math.sin(clamp((t - SNUG) / 0.7) * math.pi), blink=0)
    elif t >= FRAC + 0.1:
        g = Guy(pose='thumbs', expr='smile', mouth=mouth(t), brow=0.4, blink=blink(t), look=(0.2, 0))
    gs = 6.3; gx, gy = 205, 1905 + 220 * (1 - gk)
    if g.pose == 'point': aim(g, 'R', ((rp[0] - gx) / gs, (rp[1] - gy) / gs))
    g.bob = 0.5 * math.sin(t * 3.1)
    guy_at(L, gx, gy, gs, g)
    img.alpha_composite(L.done())
    img.alpha_composite(SN.foreground(cam, 2.0))
    return img, dict(rp=rp)


# ------------------------------------------------------------------ shot 3: two slow-mo crash passes
S3, BX, GY3 = 14.0, 1075, 1730
V3 = 1700.0


def _tau(t, t_imp):
    """Display time -> sim time for one pass: 1x, eased down to 0.07x over the 0.2 s before impact (tau = 0 at impact)."""
    a = t_imp - 0.2
    ramp = lambda u: -0.2 * ((1 - u) - 0.465 * (1 - u * u))      # integral of (1 - 0.93 u) from u to 1, times 0.2 s
    if t < a: return (t - a) + ramp(0.0)
    if t < t_imp: return ramp((t - a) / 0.2)
    return (t - t_imp) * 0.07


def crash_pass(t, t_imp, pre):
    ta = _tau(t, t_imp); ts = max(0.0, ta)
    shake = 18 * math.exp(-max(0, t - t_imp) * 4) * (t > t_imp)
    sh = (shake * math.sin(t * 71), shake * math.cos(t * 57) * 0.6)
    z = 1.15 + 0.06 * io(prog(t, t_imp, 1.4))
    cam = SN.Cam(sx=SPEED * IA, z=z, fx=520, fy=1450, shake=sh)
    img = SN.backdrop(cam, 1.4)
    L = Layer(W, H)
    G = lambda X: (cam.fx + (X - cam.fx) * z + sh[0], cam.fy + (GY3 - cam.fy) * z + sh[1])
    s = S3 * z
    bx, by = G(BX)
    crum = oc(min(1.0, ts / 0.07)) if ta >= 0 else 0.0
    ST.barrier(L.pen(bx, by, s), 0, 0, crush=crum)
    glow(L.pen(bx, by, s), (14, -18), 16, (255, 190, 90), 0.25)
    if ta < 0:
        xs = BX - 50 * S3 - V3 * (-ta); blur = 1.0
        ox, oy = G(xs)
        ghosts(L, ox, oy, s, 3, 60)
        FX.speed_lines(L.pen(), ta * 3, (0, 1300, max(0, ox - 300), 1700), 9, 7 + pre, 2.0, (255, 236, 210, 120), 6)
        j = seated(t)
    else:
        reb = 0.4 * math.sin(min(1.0, max(0, ts - 0.08) / 0.2) * math.pi)
        ox, oy = G(BX - 50 * S3 + (9 * crum - reb) * S3); blur = 0.0
        j = Ph.sample(Ph.crash(pre), ts)
    P = L.pen(ox, oy, s)
    fire = pre and ts > 0.002
    draw_car(P, 0, 'cut', cabin(j, j.get('slack', 1.6) if ta >= 0 else 1.6, 1.0 if fire else 0.0, -ts * 300 if fire else 0, 0, 0,
                                (ts - 0.002) * 6 if fire else -1), crumple=crum, blur=blur, glow_ret=0.9 if fire else 0.0)
    hit = (bx - 3 * s, by - 17 * s)
    if ta >= 0:
        age = ta * 5
        Q = L.pen(hit[0], hit[1], s)
        FX.smoke(Q, (0, 0), age * 0.8, 12, 11 + pre, 5.0, (-4, -7), 1.8, (205, 196, 186, 255))
        FX.debris(Q, (0, 0), age * 0.8, 16, 21 + pre, 42, 70, 1.4)
        for i in range(10):                                     # glass glints
            a = -2.6 + i * 0.25; d = 30 * age * (0.6 + 0.08 * i)
            if age < 1.2: glow(Q, (math.cos(a) * d, math.sin(a) * d + 30 * age * age), 1.4, (220, 245, 255), 1 - age / 1.2)
        FX.burst(Q, (0, 0), age * 0.55, 12, 0.42)
        glow(Q, (0, 0), 40, (255, 200, 120), max(0, 0.9 - age * 1.2))
    if not pre and ts > 0.04:                                   # red lurch arrow over the head
        h0, h1 = P.p(REST['head']), P.p(j['head'])
        a0, a1 = (h0[0] / SS, h0[1] / SS - 80), (h1[0] / SS, h1[1] / SS - 80)
        if a1[0] - a0[0] > 18:
            Q = L.pen()
            Q.line([a0, (a1[0] - 20, a1[1])], 16, NAVY + (255,)); Q.line([a0, (a1[0] - 20, a1[1])], 9, RED + (255,))
            Q.poly([(a1[0] + 12, a1[1]), (a1[0] - 26, a1[1] - 22), (a1[0] - 26, a1[1] + 22)], RED + (255,), ow=4, oc=NAVY + (255,))
    img.alpha_composite(L.done())
    img.alpha_composite(SN.foreground(cam, 1.4))
    flash = clamp(1 - (t - t_imp) / 0.15) if t >= t_imp else 0
    if flash > 0: img = Image.blend(img, Image.new('RGBA', img.size, (255, 236, 210, 255)), 0.6 * flash)
    ch = P.p(j['chest'])
    return img, dict(chest=(ch[0] / SS, ch[1] / SS))


def shot_crash(t):
    return crash_pass(t, IA, False) if t < WB else crash_pass(t, IB, True)


# ------------------------------------------------------------------ shot 4: the ask
def shot_ask(t):
    z = 1.38 - 0.38 * io(prog(t, T4, 0.9))
    cam = SN.Cam(sx=SPEED * IA + 300 + 60 * (t - T4), z=z, fx=320, fy=1500)
    img = SN.backdrop(cam, 1.7)
    L = Layer(W, H)
    cx, cy = cam.fx + (900 - cam.fx) * z, cam.fy + (1640 - cam.fy) * z
    j = seated(t)
    wv = prog(t, T4 + 0.5, 0.2)
    if wv > 0:                                     # the dummy waves from the car: safe
        a = -2.4 + 0.35 * math.sin((t - T4) * 9)
        j['eF'] = (j['sh'][0] + 4.2 * math.sin(a * wv + (1 - wv) * 2.0), j['sh'][1] + 4.2 * math.cos(a * wv + (1 - wv) * 2.0))
        j['hF'] = (j['eF'][0] + 3.6 * math.sin(a * wv + 0.5), j['eF'][1] + 3.6 * math.cos(a * wv + 0.5))
    draw_car(L.pen(cx, cy, 7.0 * z), 0, 'glass', cabin(j, 0.0), crumple=1.0, lights=0.8)
    FX.smoke(L.pen(cx + 330 * z, cy - 90 * z, 7 * z), (0, 0), 0.6 + 0.3 * ((t - T4) % 1.2), 7, 31, 4, (2, -6), 1.8, (205, 196, 186, 255))
    # the guy: steps back surprised, turns to camera, asks, thumbs-up after the tap
    gs = 6.5 * z; gx, gy = cam.fx + (300 - cam.fx) * z, cam.fy + (1905 - cam.fy) * z
    if t < T4 + 0.42:
        u = clamp((t - T4) / 0.42)
        g = Guy(pose='surprised', expr='surprised', brow=1.0, step=-3.5 * oc(u), look=(0.8, -0.2), turn=0.6, blink=0)
    elif t < TAP_T + 0.12:
        k = io(prog(t, T4 + 0.42, 0.3))
        g = Guy(pose='ask', expr='ask', mouth=mouth(t), brow=0.9 * k, look=(0.8 * (1 - k), -0.3 * k), turn=0.6 * (1 - k), blink=blink(t),
                step=-3.5 * (1 - k), **blend_pose('surprised', 'ask', k))
    else:
        g = Guy(pose='thumbs', expr='smile', mouth=mouth(t), brow=0.5, look=(0, 0), blink=blink(t))
    g.bob = 0.6 * math.sin(t * 3.0)
    guy_at(L, gx, gy, gs, g)
    img.alpha_composite(L.done())
    img.alpha_composite(SN.foreground(cam, 1.7))
    return img, {}


# ------------------------------------------------------------------ overlays (registered boxes for the polish checks)
def _text_img(txt, col, sz, stroke=12):
    f = font(sz); d0 = ImageDraw.Draw(Image.new('RGB', (1, 1)))
    w = int(d0.textlength(txt, font=f)) + 60
    img = Image.new('RGBA', (w, int(sz * 1.5)), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.text((30 + 5, 8 + 7), txt, font=f, fill=NAVY, stroke_width=stroke + 1, stroke_fill=NAVY)
    d.text((30, 8), txt, font=f, fill=col, stroke_width=stroke, stroke_fill=(10, 10, 16))
    return img


@lru_cache(None)
def headline_line(i):
    parts = ([('Your seatbelt can', WHITE)], [('TIGHTEN', RED), ('by itself', WHITE)])[i]
    ims = [_text_img(p, c, 118) for p, c in parts]
    w = sum(im.width for im in ims) - 34 * (len(ims) - 1); h = max(im.height for im in ims)
    out = Image.new('RGBA', (w, h), (0, 0, 0, 0)); x = 0
    for im in ims: out.alpha_composite(im, (x, 0)); x += im.width - 34
    return out


@lru_cache(None)
def _hl_scale(): return min(1.0, 790 / max(headline_line(0).width, headline_line(1).width))


def headline_on(t): return t < T2 - 0.02 or t >= TL - 0.1


def paste(cv, im, c, boxes, name, kind='text'):
    x, y = int(c[0] - im.width / 2), int(c[1] - im.height / 2)
    cv.paste(im, (x, y), im)
    a = im.getchannel('A').point(lambda v: 255 if v > 100 else 0).getbbox()      # visible pixels, not the faint shadow
    if a: boxes.append((name, kind, x + a[0], y + a[1], x + a[2], y + a[3]))


def headline(cv, t, boxes):
    tt = tail(t)
    if not headline_on(t): return
    for i, (t0, y) in enumerate(((-0.3, 455), (-0.22, 585))):
        k = ob(prog(tt, t0, 0.32)) * _hl_scale()
        if i == 1: k *= 1 + 0.14 * math.exp(-max(0, tt - TIGHT) * 9) * (tt > TIGHT)
        k *= 1 - ic(prog(tt, T2 - 0.25, 0.22))
        if k < 0.03: continue
        im = headline_line(i)
        im = im.resize((int(im.width * k), int(im.height * k)), Image.BICUBIC).rotate((-2.5 if i else 1.5), Image.BICUBIC, expand=True)
        paste(cv, im, (SX, y), boxes, 'headline%d' % i)


def pill(cv, t, txt, fill, c, t0, t1, boxes, sz=60, icon=None, rot=0.0):
    k = ob(prog(t, t0, 0.28)) * (1 - ic(prog(t, t1 - 0.15, 0.15)))
    if k < 0.03 or t >= t1: return None
    im = CD.pill_img(txt, fill, sz, icon=icon)
    im = im.resize((max(1, int(im.width * k)), max(1, int(im.height * k))), Image.BICUBIC)
    if rot: im = im.rotate(rot, Image.BICUBIC, expand=True)
    paste(cv, im, c, boxes, txt)
    return k


def leader(cv, a, b, k):
    if k <= 0.02: return
    L = Layer(W, H); P = L.pen()
    e = (a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k)
    P.line([a, e], 12, NAVY + (255,)); P.line([a, e], 6, (255, 255, 255, 255)); P.circle(e, 11, YEL + (255,), ow=5, oc=NAVY + (255,))
    im = L.done(); cv.paste(im, (0, 0), im)


@lru_cache(None)
def tag_img(): return _text_img('car stuff, explained', WHITE, 52, 10)


@lru_cache(None)
def credit_img():
    c = (json.load(open(CREDITS)) or [None])[0] if os.path.exists(CREDITS) else None
    txt = c['attribution'] if c else 'Illustrated card'
    im = _text_img(txt, (235, 235, 240), 22, 4)
    return im if im.width <= 840 else im.resize((840, int(im.height * 840 / im.width)), Image.LANCZOS)


def overlays(cv, t, shot, info, boxes):
    if shot == 1:
        im = tag_img(); paste(cv, im, (SX, 288), boxes, 'tag')
        headline(cv, t, boxes)
        if t >= TL - 0.1: paste(cv, credit_img(), (SX, 1160), boxes, 'credit')
    elif shot == 2:
        k = pill(cv, t, 'PRETENSIONER', YEL + (255,), (430, 960), CHG - 0.5, T3 - 0.05, boxes, 62)
        if k: leader(cv, (430, 1006), info['rp'], k)
        ck = ob(prog(t, T2 + 0.55, 0.45)) * (1 - ic(prog(t, T3 - 0.35, 0.3)))
        if ck > 0.03:
            im = CD.photo_card(PHOTO if os.path.exists(PHOTO) else None)
            im = im.resize((int(im.width * ck), int(im.height * ck)), Image.BICUBIC).rotate(3 - 1.5 * math.sin(t * 0.9), Image.BICUBIC, expand=True)
            paste(cv, im, (720 + 40 * (1 - ck) - 18 * (t - T2) / 5, 600 + 8 * math.sin(t * 1.3)), boxes, 'photo', 'card')
    elif shot == 3:
        if t < WB:
            pill(cv, t, 'WITHOUT PRETENSIONER', (255, 120, 110, 255), (440, 430), T3 + 0.12, WB - 0.12, boxes, 56)
        else:
            pill(cv, t, 'WITH PRETENSIONER', YEL + (255,), (420, 430), *L_WITH, boxes, 56)
            k = pill(cv, t, 'SNUG', YEL + (255,), (360, 950), *L_SNUG, boxes, 64)
            if k: leader(cv, (360, 996), info['chest'], k)
            pill(cv, t, 'SAFE', (82, 214, 128, 255), (560, 760), *L_SAFE, boxes, 74, icon='check', rot=-6)
    elif shot == 4:
        k = ob(prog(t, T4 + 0.1, 0.35))
        if k > 0.02:
            tap = clamp((t - TAP_T) / 0.6) if t > TAP_T else 0.0
            im = CD.poll_img(760, round(tap * 20) / 20)
            im = im.resize((max(1, int(im.width * k)), max(1, int(im.height * k))), Image.BICUBIC).rotate(-2 + 1.0 * math.sin(t * 2), Image.BICUBIC, expand=True)
            paste(cv, im, (SX, 690), boxes, 'poll')


# ------------------------------------------------------------------ captions + progress (from videos/ac-idle/src/render.py)
CFONT = font(84)
EMPH = {'tighten', 'crash', 'charge', 'motor', 'snug', 'pretensioner', 'impact', 'belt'}


def make_chunks():
    sents, cur = [], []
    for i, w in enumerate(WORDS):
        cur.append(i)
        if w['w'][-1] in '.,?!': sents.append(cur); cur = []
    if cur: sents.append(cur)
    chunks = []
    for s in sents:
        k = math.ceil(len(s) / 3); base, extra = divmod(len(s), k); j = 0
        for c in range(k):
            n = base + (1 if c < extra else 0); chunks.append(s[j:j + n]); j += n
    out = []
    for ci, c in enumerate(chunks):
        st = WORDS[c[0]]['s'] - 0.04
        nxt = WORDS[chunks[ci + 1][0]]['s'] - 0.04 if ci + 1 < len(chunks) else DUR
        out.append((st, min(nxt, WORDS[c[-1]]['e'] + 0.45), c))
    return out


CHUNKS = make_chunks()


@lru_cache(None)
def caption_img(ci, active):
    idxs = CHUNKS[ci][2]; words = [WORDS[i]['w'].lower().strip('.,!') for i in idxs]
    d0 = ImageDraw.Draw(Image.new('RGB', (1, 1)))
    space = d0.textlength(' ', font=CFONT); widths = [d0.textlength(w, font=CFONT) for w in words]
    tw = sum(widths) + space * (len(words) - 1); pad = 40
    img = Image.new('RGBA', (int(tw + 2 * pad), 160), (0, 0, 0, 0)); d = ImageDraw.Draw(img); x = pad
    for i, (w, wd) in enumerate(zip(words, widths)):
        on = idxs[i] == active
        col = (255, 217, 59) if on else (255, 255, 255)
        if on and w.strip("?'") in EMPH: col = (255, 90, 90)
        d.text((x + 5, 26 + 7), w, font=CFONT, fill=NAVY, stroke_width=13, stroke_fill=NAVY)
        d.text((x, 26), w, font=CFONT, fill=col, stroke_width=12, stroke_fill=(10, 10, 16))
        x += wd + space
    if img.width > 840: img = img.resize((840, int(img.height * 840 / img.width)), Image.LANCZOS)
    return img


def caption_at(t):
    if headline_on(t): return None                      # never the same words twice: no captions under the headline
    for ci, (st, en, idxs) in enumerate(CHUNKS):
        if st <= t < en:
            active = None
            for i in idxs:
                if WORDS[i]['s'] - 0.04 <= t: active = i
            return ci, st, active
    return None


def captions(cv, t, boxes):
    c = caption_at(t)
    if not c: return
    ci, st, active = c
    img = caption_img(ci, active)
    k = 0.8 + 0.2 * ob(prog(t, st, 0.16))
    if active is not None and active != CHUNKS[ci][2][0]: k *= 1 + 0.05 * math.exp(-(t - WORDS[active]['s'] + 0.04) * 14)
    img = img.resize((int(img.width * k), int(img.height * k)), Image.BILINEAR)
    paste(cv, img, (SX, SY + 12 * (1 - ob(prog(t, st, 0.2)))), boxes, 'caption')


def progress(cv, t):
    if t >= TL: t = max(0.0, t - DUR)
    p = clamp(t / DUR); L = Layer(W, 200); P = L.pen()
    x0, x1, y, h = 100, W - 100, 112, 30
    P.rrect((x0 - 6, y - 6, x1 + 6, y + h + 6), 20, (20, 26, 44, 230), ow=0)
    P.rrect((x0, y, x1, y + h), 15, (236, 236, 242, 255), ow=0)
    xp = x0 + (x1 - x0) * p
    if xp > x0 + 30:
        P.rrect((x0, y, xp, y + h), 15, (255, 170, 60, 255), ow=0)
        P.rrect((x0 + 14, y + 6, xp - 14, y + 11), 3, (255, 230, 170, 255), ow=0)
    for tc in (T2, T3, T4):
        xc = x0 + (x1 - x0) * tc / DUR; on = t >= tc
        r = 11 * (1 + 0.6 * math.exp(-(t - tc) * 10) if on else 1)
        P.circle((xc, y + h / 2), r, (60, 200, 110, 255) if on else (200, 204, 212, 255), ow=5, oc=NAVY + (255,))
    SC.draw_car(L.pen(xp, y + h + 8 - 3 * abs(math.sin(t * 9)), 0.95), t * 20, 'glass', shadow=False, paint=hexc('#ef7a32'))
    im = L.done(); cv.paste(im, (0, 0), im)


# ------------------------------------------------------------------ frame
def tail(t):
    """Shot-1 time; the loop tail lands exactly on frame 0's composition on the last frame (seamless loop)."""
    return t if t < T2 else t - DUR + 1 / FPS


def shot_of(t):
    if t < T2 or t >= TL: return 1
    if t < T3: return 2
    if t < T4: return 3
    return 4


def whip(img, t):
    """Smear + light flash around each cut and the crash wipe."""
    for tb in (T2, T3, WB, T4, TL):
        u = 1 - abs(t - tb) / 0.12
        if u > 0:
            sm = img.resize((W // 24, H), Image.BILINEAR).resize((W, H), Image.BILINEAR)
            img = Image.blend(img, sm, 0.85 * u)
            img = Image.blend(img, Image.new('RGB', (W, H), (255, 230, 200)), 0.25 * u * u)
    return img


def base_frame(t):
    s = shot_of(t)
    if s == 1: img, info = shot_hook(tail(t))
    elif s == 2: img, info = shot_cut(t)
    elif s == 3: img, info = shot_crash(t)
    else: img, info = shot_ask(t)
    return img.convert('RGB'), s, info


def frame_img(t, post=True, boxes=None):
    img, s, info = base_frame(t)
    if post: img = PO.finish(img, int(round((tail(t) if s == 1 else t) * FPS)))
    img = whip(img, t)
    boxes = [] if boxes is None else boxes
    overlays(img, t, s, info, boxes)
    captions(img, t, boxes)
    progress(img, t)
    return img


def frame(n): return frame_img(n / FPS).tobytes()


# ------------------------------------------------------------------ audio (mixer adapted from ac-idle)
CUES = [(0.0, 'whoosh', 0.8), (0.55, 'click', 0.9), (TIGHT, 'snap', 1.0),
        (T2, 'whoosh', 0.8), (CHG, 'pop', 0.7), (CHG + 0.03, 'snap', 0.5), (MOT, 'pop', 0.5), (PULL, 'whirr', 0.4), (SNUG, 'snap', 1.0),
        (T3, 'whoosh', 0.8), (IA, 'thump', 1.0), (IA + 0.04, 'glass_crack', 0.6), (IA + 0.06, 'poof', 0.4),
        (WB, 'whoosh', 0.8), (IB, 'thump', 1.0), (IB + 0.02, 'snap', 0.7), (IB + 0.04, 'glass_crack', 0.6), (L_SAFE[0], 'ding', 0.5),
        (T4, 'whoosh', 0.7), (T4 + 0.12, 'ding', 0.8), (TAP_T, 'click', 0.8), (TL, 'whoosh', 0.8)]


def build_audio(vo_path, out_wav, target=-15.5):          # AAC lands ~0.5 LU lower -> about -16 LUFS
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', vo_path, '-ar', str(sfx.SR), '-ac', '1', '-f', 'f32le', '-'], capture_output=True, check=True).stdout
    vo = np.frombuffer(raw, np.float32).astype(np.float64)
    n = int(sfx.SR * DUR); mix_ = np.zeros(n); m = min(n, len(vo)); mix_[:m] = vo[:m]
    f = sfx.render(CUES, DUR); f *= 0.32 * np.max(np.abs(vo)) / max(1e-9, np.max(np.abs(f)))
    mix_ += f
    fade = int(0.04 * sfx.SR); mix_[-fade:] *= np.linspace(1, 0, fade)

    def write(x):
        with wave.open(out_wav, 'wb') as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(sfx.SR); w.writeframes((np.clip(x, -1, 1) * 32767).astype('<i2').tobytes())
    write(mix_ * 0.5)
    log = subprocess.run(['ffmpeg', '-nostats', '-i', out_wav, '-af', 'ebur128', '-f', 'null', '-'], capture_output=True, text=True).stderr
    lufs = float([l for l in log.splitlines() if l.strip().startswith('I:')][-1].split()[1])
    mix_ *= 0.5 * 10 ** ((target - lufs) / 20)
    if np.max(np.abs(mix_)) > 0.89: mix_ = np.tanh(mix_ / 0.89) * 0.89
    write(mix_)


# ------------------------------------------------------------------ polish checks
def _ov(a, b): return min(a[4], b[4]) > max(a[2], b[2]) and min(a[5], b[5]) > max(a[3], b[3])


def checks(step=1):
    y0, y1, x1 = 0.12 * H, 0.62 * H, 0.85 * W
    over, safe, dup = [], [], []
    for n in range(0, int(DUR * FPS), step):
        t = n / FPS; boxes = []; cv = Image.new('RGB', (W, H))
        info = {'rp': (420, 1590), 'chest': (250, 1450)}
        overlays(cv, t, shot_of(t), info, boxes); captions(cv, t, boxes)
        for i in range(len(boxes)):
            b = boxes[i]
            if b[3] < y0 - 1 or b[5] > y1 + 1 or b[4] > x1 + 1 or b[2] < 0: safe.append((round(t, 2), b[0]))
            for c in boxes[i + 1:]:
                if _ov(b, c): over.append((round(t, 2), b[0], c[0]))
        if headline_on(t) and caption_at(t): dup.append(round(t, 2))
    print('overlap:', 'PASS' if not over else f'FAIL {over[:5]} ({len(over)})')
    print('safe zone:', 'PASS' if not safe else f'FAIL {safe[:5]} ({len(safe)})')
    print('duplicate text:', 'PASS' if not dup else f'FAIL {dup[:5]}')
    worst = 0
    for t in np.arange(0, DUR, 0.5):
        a = np.asarray(base_frame(float(t))[0].convert('L').resize((W // 4, H // 4)), np.int16)
        b = a[:a.shape[0] // 12 * 12, :a.shape[1] // 12 * 12].reshape(a.shape[0] // 12, 12, a.shape[1] // 12, 12)
        flat = ((b.max((1, 3)) - b.min((1, 3))) < 3).mean()
        worst = max(worst, flat)
    print(f'empty space: worst frame {worst * 100:.0f} % flat (limit 33 %)', 'PASS' if worst < 1 / 3 else 'FAIL')
    return not (over or safe or dup) and worst < 1 / 3


if __name__ == '__main__':
    mode = sys.argv[1]
    if mode == 'still':
        os.makedirs(sys.argv[2], exist_ok=True)
        for ts in sys.argv[3:]: frame_img(float(ts)).save(os.path.join(sys.argv[2], f'f_{float(ts):05.2f}.png'))
    elif mode == 'cover':
        frame_img(0.0).save(sys.argv[2])
    elif mode == 'checks':
        sys.exit(0 if checks() else 1)
    elif mode == 'video':
        out = sys.argv[2]
        t0, t1 = (float(sys.argv[3]), float(sys.argv[4])) if len(sys.argv) > 4 else (0.0, DUR)
        mixwav = os.path.join(OUT, 'mix.wav')
        build_audio(os.path.join(OUT, 'voiceover.wav'), mixwav)
        F0, N = int(round(t0 * FPS)), int(round(t1 * FPS))
        ff = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                               '-ss', str(t0), '-t', str(t1 - t0), '-i', mixwav, '-map', '0:v', '-map', '1:a',
                               '-c:v', 'libx264', '-preset', 'slow', '-crf', '17', '-pix_fmt', 'yuv420p', '-aspect', '9:16',
                               '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-movflags', '+faststart', '-t', str(t1 - t0), out], stdin=subprocess.PIPE)
        with Pool(4) as pool:
            for i, b in enumerate(pool.imap(frame, range(F0, N), chunksize=4)):
                ff.stdin.write(b)
                if i % 120 == 0: print(f'{i}/{N - F0}', flush=True)
        ff.stdin.close(); ff.wait(); print('done', ff.returncode); sys.exit(ff.returncode)
