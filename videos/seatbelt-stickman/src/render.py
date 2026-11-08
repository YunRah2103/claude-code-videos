"""'car stuff, explained' style test: the seatbelt pretensioner in flat-vector stickman style (loops, 15.0 s, 1080x1920).

Shots (timed to words.json = faster-whisper on out/seatbelt-stickman/voiceover.wav):
  1 rush    0.00  car already sliding in on frame 0, crash dummy at the wheel, hall streaming past; belt snaps tight on
                  'tighten'; headline 'Your seatbelt can TIGHTEN by itself'; presenter lower left points at the dummy
  2 cut     ~2.95 zoom into the cutaway: slack belt, retractor x-ray bubble, small charge ('charge'), or a motor ('motor'),
                  spool reels in ('pulls') -> SNUG glow; stopwatch flick for 'a fraction of a second'; pill PRETENSIONER
  3 split   ~8.25 slow-mo crash into the barrier, two pymunk ragdolls: WITH PRETENSIONER held snug, WITHOUT lurches
                  further; pills SNUG and BEFORE IMPACT; stamp SAFE
  4 ask     ~12.95 presenter + poll 'Did you know that? YES / NO'; whips back to shot 1 so the last frame matches frame 0
    python render.py still <dir> t... | cover <png> | safecheck | video <out.mp4> [t0 t1]
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
from stickman.vec import Layer, INK, hexc, shade, mix, soft_ellipse, arcpts, SS
from stickman import rig as R, car as C, physics as Ph, fx as FX, stage as ST
from stickman.poll import poll_img

W, H, FPS = 1080, 1920, 60
DUR = 15.0
OUT = os.path.join(ROOT, 'out', 'seatbelt-stickman')
WORDS = json.load(open(os.path.join(HERE, 'words.json')))
def ws(i): return WORDS[i]['s']

T2 = ws(6) - 0.19                       # 'In a crash'                -> cutaway
T3 = ws(23) - 0.09                      # "That's called a pretensioner" -> split crash
T4 = ws(36) - 0.19                      # 'Did you know ...'          -> ask
TL = 14.72                              # whip back to shot 1 (loop)
TIGHT, CRASH, CHG, MOT, PULL, SNUG, FRAC = ws(3), ws(8), ws(11), ws(13), ws(14), ws(16), ws(19)
PRE, HOLD, BEFORE, WORSE = ws(26), ws(28), ws(31), ws(35)
T_IMP = 8.85                            # bumper meets the barrier (display time)
SAFE_T = 12.25
TAP_T = 14.25

SX, SY = 459, 1120                      # caption centre: inside the left 85 % and above 62 % of the height
RED, YEL, WHITE, NAVY = (232, 52, 63), (255, 201, 40), (255, 255, 255), (26, 26, 46)
SPEED = 2300.0                          # hall scroll in shots 1-2 (px/s)
FONT_PATH = '/usr/share/fonts/opentype/inter/Inter-Black.otf'


def font(sz):
    try: return ImageFont.truetype(FONT_PATH, sz)
    except OSError: return ImageFont.load_default(size=sz)


def talk(t):
    for w in WORDS:
        if w['s'] <= t < w['e']: return 0.45 + 0.45 * abs(math.sin((t - w['s']) * 17))
    return 0.0


def blink(t, seed=0.0):
    ph = (t + seed) % 3.1
    return 1.0 if 0 < ph < 0.09 else 0.0


# ------------------------------------------------------------------ shared drawing bits
REST = Ph.crash(True)[0]


def dummy_cabin(j, chest, slack, glow=0.0, spin=0.0, charge=0.0, motor=0.0, spark_age=-1.0):
    def fn(Q):
        C.draw_seat(Q)
        R.draw_dummy(Q, j, 3.4)
        C.draw_wheel_col(Q)
        C.draw_belt(Q, chest, slack, glow, j['hip'])
        C.draw_retractor(Q, spin, charge, motor)
        if spark_age >= 0: FX.spark(Q, (C.RETRACTOR[0], C.RETRACTOR[1] + 3), spark_age, 3.2)
    return fn


def seated(t, back=0.0):
    """Rest pose with a little road vibration; `back` pulls the torso into the seat (snug)."""
    bob = 0.12 * math.sin(t * 23) + 0.06 * math.sin(t * 37)
    j = {k: (v[0] - back * (0.6 if k in ('neck', 'head', 'sh', 'chest') else 0.15), v[1] + bob)
         if isinstance(v, tuple) else v for k, v in REST.items()}
    j['head'] = (j['head'][0] + 0.1 * math.sin(t * 9), j['head'][1])
    return j


def presenter(P, t, target, ox, oy, s, look=(0.5, -0.3), brow=0.0, pop=1.0, wave=0.0):
    pose = R.Pose(armF=(2.2, 0.0), armB=(-0.35 - 0.1 * math.sin(t * 2), 0.5), look=look, blink=blink(t), talk=talk(t), brow=brow,
                  hip_y=-0.8 * abs(math.sin(t * 3.2)), lean=0.05 * math.sin(t * 1.7), squash=pop)
    j = R.presenter_joints(pose)
    tx, ty = (target[0] - ox) / s, (target[1] - oy) / s
    a = R.point_angle(j['sh'], (tx, ty)) + 0.06 * math.sin(t * 5) + wave
    pose.armF = (a, -0.12)
    j = R.presenter_joints(pose)
    P.paste(soft_ellipse(int(26 * s), int(3.2 * s), 120), (0, 1))
    R.draw_presenter(P, j, pose)


def ghost_body(P, alpha, col=C.CORAL):
    P.fillpoly(C.body_pts(), col[:3] + (alpha,))


# ------------------------------------------------------------------ shot 1: rush towards the barrier
G1, S1C = 1708, 10.4


def car1_x(tt):
    return 530 - 1350 * (1 - oc(prog(tt, -0.32, 0.64))) + 18 * math.sin(tt * 1.3)


def shot_rush(tt):
    img = ST.view(ST.hall(), SPEED * tt).copy()
    L = Layer(W, H); P0 = L.pen()
    FX.speed_lines(P0, tt, (0, 1270, W, 1890), 16, 3, 2.6, (255, 255, 255, 120), 7)
    FX.speed_lines(P0, tt + 0.4, (0, 560, W, 1200), 7, 9, 1.8, (255, 255, 255, 70), 5)
    x = car1_x(tt); v = (car1_x(tt + 0.01) - car1_x(tt - 0.01)) / 0.02
    vn = clamp(v / 1500)
    if vn > 0.12:
        for k, a in ((2, 70), (1, 120)):
            ghost_body(L.pen(x - 70 * k * vn, G1, S1C, kx=1 + 0.1 * vn), a)
    bx = 1300 - 215 * oc(prog(tt, 1.9, 1.0))
    if tt > 1.8: ST.barrier(L.pen(bx, G1, S1C), 0, 0)
    P = L.pen(x, G1 + 1.2 * math.sin(tt * 40), S1C, kx=1 + 0.09 * vn, ky=1 - 0.04 * vn)
    k = io(prog(tt, TIGHT - 0.05, 0.14))
    slack = 1.6 * (1 - k); glow = math.exp(-max(0, tt - TIGHT) * 2.5) * (tt > TIGHT - 0.05)
    j = seated(tt, back=k * 0.5)
    C.draw_car(P, (SPEED * tt + x) / (C.WR * S1C), 'glass', dummy_cabin(j, j['chest'], slack, glow, spin=tt * 30 * (tt < TIGHT + 0.1)))
    if tt > TIGHT - 0.05:
        FX.burst(P, (j['chest'][0], j['chest'][1]), tt - TIGHT + 0.02, 4.0, 0.36)
    # presenter at the track side, pointing into the window
    s = 3.9
    target = P.p(j['chest']); target = (target[0] / SS, target[1] / SS)
    presenter(L.pen(140, 1900, s), tt, target, 140, 1900, s, look=(0.8, -0.6))
    img.paste(*_layer(L))
    return img


def _layer(L):
    im = L.done(); return im, (0, 0), im


# ------------------------------------------------------------------ shot 2: cutaway + retractor x-ray
BUB_C, BUB_R = (350, 655), 250
RET_IN = (350, 600)
SC2 = 21.0


def cam2(t):
    z = oc(prog(t, T2, 0.42))
    s = 11 + (SC2 - 11) * z
    fx_, fy = 600 + 8 * s, 1410 + 20 * s           # cabin centre (car -8, -20) at screen (600, 1410)
    return fx_ + 60 * (1 - z), fy + 140 * (1 - z), s


def stopwatch(P, c, r, t0, t):
    a = ob(prog(t, t0, 0.25)); fade = 1 - prog(t, T3 - 0.35, 0.25)
    k = a * fade
    if k <= 0.02: return
    rr = r * k
    P.rrect((c[0] - rr * 0.18, c[1] - rr * 1.32, c[0] + rr * 0.18, c[1] - rr * 1.02), 4, shade(hexc('#c9ccd2'), 0), ow=5)
    P.circle(c, rr, (255, 255, 255, 255), ow=7)
    sweep = 40 * oc(prog(t, t0 + 0.18, 0.18))          # a small flick: a fraction of a second
    if sweep > 1:
        P.fillpoly([c] + arcpts(c, rr * 0.86, -math.pi / 2, -math.pi / 2 + math.radians(sweep), 10), YEL + (255,))
    for i in range(12):
        a_ = i * math.pi / 6
        P.line([(c[0] + math.cos(a_) * rr * 0.78, c[1] + math.sin(a_) * rr * 0.78), (c[0] + math.cos(a_) * rr * 0.9, c[1] + math.sin(a_) * rr * 0.9)], 5, INK)
    ha = -math.pi / 2 + math.radians(sweep)
    P.line([c, (c[0] + math.cos(ha) * rr * 0.8, c[1] + math.sin(ha) * rr * 0.8)], 9, RED + (255,))
    P.circle(c, rr * 0.09, INK, ow=0)


def shot_cut(t):
    img = ST.view(ST.hall(dark=0.05), SPEED * t).copy()
    L = Layer(W, H); P0 = L.pen()
    FX.speed_lines(P0, t, (0, 1250, W, 1900), 12, 5, 2.4, (255, 255, 255, 90), 6)
    ox, oy, s = cam2(t)
    shake = 6 * math.exp(-max(0, t - CRASH) * 6) * (t > CRASH)
    P = L.pen(ox + shake * math.sin(t * 90), oy + 0.8 * math.sin(t * 40), s)
    pull = io(prog(t, PULL, SNUG - PULL + 0.04))
    snap = math.exp(-max(0, t - SNUG) * 7) * (t > SNUG)
    slack = 1.6 * (1 - pull)
    j = seated(t, back=pull * 0.55 + 0.25 * snap)
    spin = -(t - PULL) * 26 * pull if t > PULL else 0.0
    chg = ob(prog(t, CHG - 0.06, 0.25)); mot = ob(prog(t, MOT - 0.06, 0.25))
    C.draw_car(P, 0.0, 'cut', dummy_cabin(j, j['chest'], slack, snap + 0.4 * pull, spin, chg, mot))
    rp = P.p(C.RETRACTOR); rp = (rp[0] / SS, rp[1] / SS)
    # x-ray bubble with the retractor, linked to the real one
    b = ob(prog(t, T2 + 0.3, 0.35))
    if b > 0.02:
        r = BUB_R * b
        tail = [(BUB_C[0] - 46 * b, BUB_C[1] + r * 0.9), (BUB_C[0] + 46 * b, BUB_C[1] + r * 0.9), rp]
        P0.poly(tail, (255, 255, 255, 255), ow=7)
        P0.circle(BUB_C, r, (255, 255, 255, 255), ow=8)
        P0.arc(rp, 30, 0, 360, 7, YEL + (255,))
        circ = arcpts(BUB_C, r - 2, 0, 2 * math.pi, 48)

        def inside(Q):
            Q.fillpoly(circ, hexc('#edf0f3'))
            for gx in range(-260, 261, 52):
                Q.line([(BUB_C[0] + gx, BUB_C[1] - 260), (BUB_C[0] + gx, BUB_C[1] + 260)], 2, hexc('#d5dbe2'), cap=False)
                Q.line([(BUB_C[0] - 260, BUB_C[1] + gx), (BUB_C[0] + 260, BUB_C[1] + gx)], 2, hexc('#d5dbe2'), cap=False)
            k2 = 34 * b
            B = Q.sub(RET_IN[0] - C.RETRACTOR[0] * k2, RET_IN[1] - C.RETRACTOR[1] * k2, k2)
            web = [(C.RETRACTOR[0] + 0.2, C.RETRACTOR[1] - 2.4), (C.RETRACTOR[0] + 0.2, C.RETRACTOR[1] - 12)]
            B.line(web, 1.25 * k2 + 8, INK); B.line(web, 1.25 * k2, C.WEB)
            ys = (t * 3) % 1.0 if t > PULL and t < SNUG + 0.1 else 0.0
            for q in range(3):
                yy = C.RETRACTOR[1] - 4 - ((q * 2.6 + ys * 2.6 * (1 + q)) % 7.5)
                if t > PULL - 0.1 and t < SNUG + 0.2:
                    B.line([(web[0][0] + 1.2, yy), (web[0][0] + 1.2, yy + 1.2)], 5, YEL + (255,))
            C.draw_retractor(B, spin, chg, mot)
            if t > CHG: FX.spark(B, (C.RETRACTOR[0], C.RETRACTOR[1] + 5), (t - CHG) * 1.2, 3.4)
            if t > CHG: FX.smoke(B, (C.RETRACTOR[0], C.RETRACTOR[1] + 5), (t - CHG) * 1.1, 6, 4, 1.4, (2.5, -2.0), 1.4)
            if t > PULL:   # reel-in arrows around the spool
                a0 = -(t - PULL) * 6
                for q in range(2):
                    ar = arcpts(C.RETRACTOR, 3.6, a0 + q * math.pi, a0 + q * math.pi + 1.6, 8)
                    B.line(ar, 7, RED + (255,), cap=True)
                    tip = ar[-1]; dirv = (ar[-1][0] - ar[-2][0], ar[-1][1] - ar[-2][1]); n = math.hypot(*dirv) or 1
                    dx, dy = dirv[0] / n, dirv[1] / n
                    B.fillpoly([(tip[0] + dx * 0.9, tip[1] + dy * 0.9), (tip[0] - dy * 0.6, tip[1] + dx * 0.6), (tip[0] + dy * 0.6, tip[1] - dx * 0.6)], RED + (255,))
        C._clip_draw(P0, circ, inside)
        P0.arc(BUB_C, r, 0, 360, 8, INK)
        if t > CRASH and t < CRASH + 0.6:      # crash detected: red pulse on the rim
            P0.arc(BUB_C, r + 10 + 40 * (t - CRASH), 0, 360, 10 * (1 - (t - CRASH) / 0.6), RED + (int(255 * (1 - (t - CRASH) / 0.6)),))
    stopwatch(P0, (770, 560), 92, FRAC - 0.12, t)
    s_ = 4.0
    presenter(L.pen(118, 1900, s_), t, rp, 118, 1900, s_, look=(0.7, -0.2))
    img.paste(*_layer(L))
    return img


# ------------------------------------------------------------------ shot 3: split slow-mo crash
PANELS = ((170, 960, True), (975, 1920, False))
BARRIER_X, S3C = 872, 9.0
V3 = 1500.0


def _rate(t):
    if t < 8.6: return 1.0
    if t < T_IMP: return 1.0 - 0.94 * (t - 8.6) / (T_IMP - 8.6)
    if t < 12.35: return 0.06
    if t < 12.6: return 0.06 + 0.94 * (t - 12.35) / 0.25
    return 1.0


@lru_cache(1)
def _tau_table():
    ts = np.arange(T3 - 0.5, DUR + 0.01, 0.0005)
    r = np.array([_rate(x) for x in ts])
    tau = np.concatenate([[0], np.cumsum((r[1:] + r[:-1]) / 2 * 0.0005)])
    tau -= np.interp(T_IMP, ts, tau)
    return ts, tau


def tau(t):
    ts, ta = _tau_table(); return float(np.interp(t, ts, ta))


def panel(t, ph, pre):
    floor = ph - 300; ground = ph - 72
    strip = ST.hall()
    img = ST.view(strip, 900).crop((0, 1560 - floor, W, 1560 - floor + ph)).copy()
    L = Layer(W, ph)
    ta = tau(t); ts = max(0.0, ta)
    shake = 16 * math.exp(-max(0, t - T_IMP) * 5) * (t > T_IMP)
    sx, sy = shake * math.sin(t * 77), shake * math.cos(t * 61) * 0.6
    if ta < 0:
        x = BARRIER_X - 50 * S3C - V3 * (-ta)
        FX.speed_lines(L.pen(), ta * 3, (0, ground - 330, max(0, x - 200), ground - 20), 9, 7 + pre, 2.0, (255, 255, 255, 140), 6)
        wang = (V3 * ta) / (C.WR * S3C)
        crum = 0.0
    else:
        crum = oc(min(1.0, ts / 0.07))
        reb = 0.4 * math.sin(min(1.0, max(0, ts - 0.08) / 0.2) * math.pi)
        x = BARRIER_X - 50 * S3C + (9 * crum - reb) * S3C
        wang = 0.0
    B = L.pen(BARRIER_X + sx, ground + sy, S3C)
    ST.barrier(B, 0, 0, crush=crum)
    P = L.pen(x + sx, ground + sy, S3C)
    fr = Ph.crash(pre); j = Ph.sample(fr, ts)
    if ta < 0: j = seated(t)
    fire = pre and ts > 0.002
    glow = (0.9 * math.exp(-(t - T_IMP) * 0.7)) if fire else 0.0
    sp_age = (ts - 0.002) * 6 if fire else -1
    C.draw_car(P, wang, 'cut', dummy_cabin(j, j['chest'], j.get('slack', 1.6), glow, -ts * 300 if fire else 0, 0, 0, sp_age), crumple=crum)
    hit = (BARRIER_X - 6 * S3C * 0.4, ground - 17 * S3C)
    if ta >= 0:
        age = ta * 5
        Q = L.pen(hit[0] + sx, hit[1] + sy, S3C)
        FX.smoke(Q, (0, 0), age * 0.9, 10, 11 + pre, 4.2, (-3, -6), 1.6)
        FX.debris(Q, (0, 0), age * 0.8, 12, 21 + pre, 38, 70, 1.3)
        FX.burst(Q, (0, 0), age * 0.55, 11, 0.42)
    if not pre and ts > 0.05:          # red lurch arrow: rest head -> current head
        h0 = P.p(REST['head']); h1 = P.p(j['head'])
        a0, a1 = (h0[0] / SS, h0[1] / SS - 70), (h1[0] / SS, h1[1] / SS - 70)
        if a1[0] - a0[0] > 18:
            Q = L.pen()
            Q.line([a0, (a1[0] - 18, a1[1])], 13, INK); Q.line([a0, (a1[0] - 18, a1[1])], 7, RED + (255,))
            Q.poly([(a1[0] + 10, a1[1]), (a1[0] - 22, a1[1] - 18), (a1[0] - 22, a1[1] + 18)], RED + (255,), ow=4)
    flash = clamp(1 - (t - T_IMP) / 0.12) if t >= T_IMP else 0
    out = img.convert('RGBA'); out.alpha_composite(L.done())
    if flash > 0: out = Image.blend(out, Image.new('RGBA', out.size, (255, 255, 255, 255)), 0.75 * flash)
    return out.convert('RGB'), P, j


PANEL_INFO = {}


def shot_split(t):
    img = Image.new('RGB', (W, H), (34, 36, 44))
    slide = oc(prog(t, T3, 0.35))
    for y0, y1, pre in PANELS:
        im, P, j = panel(t, y1 - y0, pre)
        dx = int((1 - slide) * (W if pre else -W))
        img.paste(im, (dx, y0))
        PANEL_INFO[pre] = (P, j, y0, dx)
    d = ImageDraw.Draw(img)
    d.rectangle((0, PANELS[0][1], W, PANELS[1][0]), fill=(34, 36, 44))
    d.rectangle((0, PANELS[0][1] + 5, int(W * slide), PANELS[1][0] - 5), fill=YEL)
    return img


# ------------------------------------------------------------------ shot 4: the ask + poll
def shot_ask(t):
    img = ST.view(ST.hall(), 300 + 40 * (t - T4)).copy()
    L = Layer(W, H)
    P = L.pen(900, 1790, 7.6)
    j = seated(t)
    wv = prog(t, T4 + 0.3, 0.2) * (1 - prog(t, TL - 0.3, 0.2))
    if wv > 0:                          # the dummy waves: safe and fine
        a = -2.4 + 0.35 * math.sin((t - T4) * 9)
        j['eF'] = (j['sh'][0] + 4.2 * math.sin(a * wv + (1 - wv) * 2.0), j['sh'][1] + 4.2 * math.cos(a * wv + (1 - wv) * 2.0))
        j['hF'] = (j['eF'][0] + 3.6 * math.sin(a * wv + 0.5), j['eF'][1] + 3.6 * math.cos(a * wv + 0.5))
    C.draw_car(P, 0.0, 'glass', dummy_cabin(j, j['chest'], 0.0), crumple=1.0)
    FX.smoke(L.pen(1075, 1600, 7.6), (0, 0), 0.5 + 0.25 * ((t - T4) % 1.2), 7, 31, 4, (2, -6), 1.6)
    pop = 0.75 + 0.25 * ob(prog(t, T4, 0.3))
    s = 5.9
    presenter(L.pen(190, 1902, s), t, (330, 720), 190, 1902, s, look=(0.2, -0.5), brow=1.0, pop=pop)
    img.paste(*_layer(L))
    k = ob(prog(t, T4 + 0.08, 0.35))
    if k > 0.02:
        tap = clamp((t - TAP_T) / 0.6) if t > TAP_T else 0.0
        pi = poll_img(760, round(tap * 20) / 20)
        pi = pi.resize((max(1, int(pi.width * k)), max(1, int(pi.height * k))), Image.BICUBIC).rotate(-2.5 + 1.2 * math.sin(t * 2), Image.BICUBIC, expand=True)
        img.paste(pi, (int(SX - pi.width / 2), int(700 - pi.height / 2)), pi)
        if t > TAP_T - 0.35:              # tap finger
            ft = clamp((t - (TAP_T - 0.35)) / 0.35)
            fx_, fy = 240 + 60 * (1 - oc(ft)), 760 + 40 * (1 - oc(ft))
            Lf = Layer(W, H); Pf = Lf.pen()
            Pf.circle((fx_, fy), 30, R.SKIN, ow=6); Pf.circle((fx_ - 8, fy - 9), 9, shade(R.SKIN, 0.4), ow=0)
            img.paste(*_layer(Lf))
    return img


# ------------------------------------------------------------------ overlays: headline, pills, stamp, tag
def _text_img(txt, col, sz, stroke=13):
    f = font(sz); d0 = ImageDraw.Draw(Image.new('RGB', (1, 1)))
    w = int(d0.textlength(txt, font=f)) + 60
    img = Image.new('RGBA', (w, int(sz * 1.5)), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.text((30 + 6, 8 + 8), txt, font=f, fill=NAVY, stroke_width=stroke + 1, stroke_fill=NAVY)
    d.text((30, 8), txt, font=f, fill=col, stroke_width=stroke, stroke_fill=(10, 10, 16))
    return img


@lru_cache(None)
def headline_line(i, maxw=860):
    parts = ([('Your seatbelt can', WHITE)], [('TIGHTEN', RED), ('by itself', WHITE)])[i]
    ims = [_text_img(p, c, 112) for p, c in parts]
    w = sum(im.width for im in ims) - 30 * (len(ims) - 1); h = max(im.height for im in ims)
    out = Image.new('RGBA', (w, h), (0, 0, 0, 0)); x = 0
    for im in ims: out.alpha_composite(im, (x, 0)); x += im.width - 30
    return out


@lru_cache(None)
def _hl_scale():
    return min(1.0, 860 / max(headline_line(0).width, headline_line(1).width))


def headline(cv, tt):
    if tt >= T2 - 0.02: return
    for i, (t0, y) in enumerate(((-0.28, 440), (-0.2, 560))):
        k = ob(prog(tt, t0, 0.3)) * _hl_scale()
        if i == 1: k *= 1 + 0.13 * math.exp(-max(0, tt - TIGHT) * 9) * (tt > TIGHT)
        if k < 0.03: continue
        im = headline_line(i)
        im = im.resize((int(im.width * k), int(im.height * k)), Image.BICUBIC)
        rot = (-3 if i else 2) * (1 if tt < TIGHT else 0.4)
        im = im.rotate(rot, Image.BICUBIC, expand=True)
        cv.paste(im, (int(SX - im.width / 2), int(y - im.height / 2)), im)


@lru_cache(None)
def pill_img(txt, fill, fg=INK[:3], sz=64):
    f = font(sz * 2); d0 = ImageDraw.Draw(Image.new('RGB', (1, 1)))
    tw = d0.textlength(txt, font=f) / 2
    w, h = int(tw + 76), int(sz * 1.55)
    L = Layer(w + 12, h + 16); P = L.pen()
    P.rrect((6, 14, w + 6, h + 10), h / 2, INK, ow=0)
    P.rrect((6, 4, w + 6, h), h / 2, fill, ow=6)
    P.text(((w + 12) / 2, h / 2 + 2), txt, f, fg, 'mm')
    return L.done()


def pill(cv, txt, fill, c, t, t0, t1=99.0, rot=0.0, sz=64):
    k = ob(prog(t, t0, 0.28)) * (1 - ic(prog(t, t1 - 0.15, 0.15)))
    if k < 0.03: return
    im = pill_img(txt, fill, sz=sz)
    im = im.resize((int(im.width * k), int(im.height * k)), Image.BICUBIC)
    if rot: im = im.rotate(rot, Image.BICUBIC, expand=True)
    cv.paste(im, (int(c[0] - im.width / 2), int(c[1] - im.height / 2)), im)


def leader(cv, a, b, t, t0, t1=99.0):
    k = oc(prog(t, t0 + 0.1, 0.2)) * (1 - prog(t, t1 - 0.15, 0.15))
    if k <= 0.02: return
    L = Layer(W, H); P = L.pen()
    e = (a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k)
    P.line([a, e], 14, INK); P.line([a, e], 7, (255, 255, 255, 255)); P.circle(e, 10, YEL + (255,), ow=5)
    cv.paste(*_layer(L))


@lru_cache(None)
def stamp_img():
    L = Layer(420, 200); P = L.pen()
    P.rrect((14, 14, 406, 186), 30, (60, 207, 110, 255), ow=9)
    P.rrect((34, 34, 386, 166), 18, (0, 0, 0, 0), ow=0)
    P.text((210, 104), 'SAFE', font(120 * 2), (255, 255, 255), 'mm', stroke=5)
    return L.done()


@lru_cache(None)
def tag_img(): return _text_img('car stuff, explained', WHITE, 54, 11)


def overlays(cv, t, shot):
    if shot == 1:
        tt = t if t < T2 else t - DUR
        im = tag_img(); cv.paste(im, (int(SX - im.width / 2), 282 - im.height // 2), im)
        headline(cv, tt)
    elif shot == 2:
        pill(cv, 'PRETENSIONER', YEL, (BUB_C[0] + 10, BUB_C[1] + BUB_R + 52), t, ws(10) - 0.1, T3)
    elif shot == 3:
        pill(cv, 'WITH PRETENSIONER', YEL, (345, 285), t, T3 + 0.25, T4, sz=52)
        pill(cv, 'WITHOUT', (233, 235, 238), (190, 1022), t, T3 + 0.35, T4, sz=52)
        P, j, y0, dx = PANEL_INFO.get(True, (None,) * 4)
        if P is not None:
            ch = P.p(j['chest']); ch = (ch[0] / SS + dx, ch[1] / SS + y0)
            leader(cv, (400, 500), ch, t, HOLD - 0.05, SAFE_T)
            pill(cv, 'SNUG', YEL, (400, 478), t, HOLD - 0.05, SAFE_T)
            pill(cv, 'BEFORE IMPACT', (232, 52, 63, 255), (630, 398), t, BEFORE - 0.05, T4, rot=3, sz=56)
        k = ob(prog(t, SAFE_T, 0.22)) * (1 - prog(t, T4 - 0.12, 0.12))
        if k > 0.02:
            im = stamp_img(); s = k * (1.0 + 0.6 * (1 - prog(t, SAFE_T, 0.12)))
            im = im.resize((int(im.width * s * 0.62), int(im.height * s * 0.62)), Image.BICUBIC).rotate(-9, Image.BICUBIC, expand=True)
            cv.paste(im, (int(560 - im.width / 2), int(560 - im.height / 2)), im)


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
        nxt = WORDS[chunks[ci + 1][0]]['s'] - 0.04 if ci + 1 < len(chunks) else DUR + 1
        out.append((st, min(nxt, WORDS[c[-1]]['e'] + (0.45 if ci + 1 < len(chunks) else 0.1)), c))
    return out


CHUNKS = make_chunks()


def clean(w): return w.lower().strip('.,!')


@lru_cache(None)
def caption_img(ci, active):
    idxs = CHUNKS[ci][2]; words = [clean(WORDS[i]['w']) for i in idxs]
    d0 = ImageDraw.Draw(Image.new('RGB', (1, 1)))
    space = d0.textlength(' ', font=CFONT); widths = [d0.textlength(w, font=CFONT) for w in words]
    tw = sum(widths) + space * (len(words) - 1); pad = 40
    img = Image.new('RGBA', (int(tw + 2 * pad), 160), (0, 0, 0, 0)); d = ImageDraw.Draw(img); x = pad
    for i, (w, wd) in enumerate(zip(words, widths)):
        on = idxs[i] == active
        col = (255, 217, 59) if on else (255, 255, 255)
        if on and w.strip("?'") in EMPH: col = (255, 90, 90)
        d.text((x + 6, 26 + 8), w, font=CFONT, fill=NAVY, stroke_width=13, stroke_fill=NAVY)
        d.text((x, 26), w, font=CFONT, fill=col, stroke_width=12, stroke_fill=(10, 10, 16))
        x += wd + space
    if img.width > 840: img = img.resize((840, int(img.height * 840 / img.width)), Image.LANCZOS)
    return img


def captions(cv, t):
    if t >= DUR - 0.05: t -= DUR          # the last frames show frame 0's caption so the loop is seamless
    for ci, (st, en, idxs) in enumerate(CHUNKS):
        if st <= t < en:
            active = None
            for i in idxs:
                if WORDS[i]['s'] - 0.04 <= t: active = i
            img = caption_img(ci, active)
            k = 0.78 + 0.22 * ob(prog(t, st, 0.16))
            if active is not None and active != idxs[0]: k *= 1 + 0.06 * math.exp(-(t - WORDS[active]['s'] + 0.04) * 14)
            dy = 14 * (1 - ob(prog(t, st, 0.2)))
            if k != 1: img = img.resize((int(img.width * k), int(img.height * k)), Image.BILINEAR)
            cv.paste(img, (int(SX - img.width / 2), int(SY + dy - img.height / 2)), img)
            return


def progress(cv, t):
    if t >= TL: t = max(0.0, t - DUR)              # the bar resets under the whip, so the last frame matches frame 0
    p = clamp(t / DUR); L = Layer(W, 200); P = L.pen()
    x0, x1, y, h = 100, W - 100, 112, 34
    P.rrect((x0 - 7, y - 7, x1 + 7, y + h + 7), 22, NAVY + (255,), ow=0)
    P.rrect((x0, y, x1, y + h), 16, (236, 236, 242, 255), ow=0)
    xp = x0 + (x1 - x0) * p
    if xp > x0 + 32:
        P.rrect((x0, y, xp, y + h), 16, (255, 210, 63, 255), ow=0)
        P.rrect((x0 + 16, y + 7, xp - 16, y + 13), 3, (255, 238, 160, 255), ow=0)
    for tc in (T2, T3, T4):
        xc = x0 + (x1 - x0) * tc / DUR; yc = y + h / 2; on = t >= tc
        r = 12 * (1 + 0.6 * math.exp(-(t - tc) * 10) if on else 1)
        P.circle((xc, yc), r, (60, 200, 90, 255) if on else (200, 204, 212, 255), ow=6)
    C.draw_car(L.pen(xp, y + h + 8 - 3 * abs(math.sin(t * 9)), 0.95), t * 20, 'glass', shadow=False)
    im = L.done(); cv.paste(im, (0, 0), im)


def whip(cv, t):
    for tb in (T2, T3, T4, TL):
        u = (t - tb) / 0.2 + 0.5
        if 0 <= u <= 1:
            L = Layer(W, H); P = L.pen(); x = -1700 + 3400 * io(u)
            P.fillpoly([(x - 900, 0), (x + 500, 0), (x + 900, H), (x - 500, H)], INK)
            P.fillpoly([(x + 500, 0), (x + 600, 0), (x + 1000, H), (x + 900, H)], YEL + (255,))
            P.fillpoly([(x - 1000, 0), (x - 900, 0), (x - 500, H), (x - 600, H)], YEL + (255,))
            cv.paste(*_layer(L))


def shot_of(t):
    if t < T2 or t >= TL: return 1
    if t < T3: return 2
    if t < T4: return 3
    return 4


def frame_img(t):
    s = shot_of(t)
    if s == 1: img = shot_rush(t if t < T2 else t - DUR)
    elif s == 2: img = shot_cut(t)
    elif s == 3: img = shot_split(t)
    else: img = shot_ask(t)
    img = img.convert('RGBA'); img.alpha_composite(ST.vignette()); img = img.convert('RGB')
    overlays(img, t, s)
    captions(img, t)
    progress(img, t)
    whip(img, t)
    return img


def frame(n): return frame_img(n / FPS).tobytes()


# ------------------------------------------------------------------ audio (mixer adapted from ac-idle)
CUES = [(0.0, 'whoosh', 0.8), (0.55, 'click', 0.9), (TIGHT, 'snap', 1.0),
        (T2, 'whoosh', 0.7), (CRASH, 'beep', 0.35), (CHG, 'pop', 0.8), (CHG + 0.03, 'snap', 0.6), (MOT, 'pop', 0.6),
        (PULL, 'whirr', 0.45), (SNUG, 'snap', 1.0), (FRAC, 'click', 0.6),
        (T3, 'whoosh', 0.7), (T_IMP, 'thump', 1.0), (T_IMP + 0.04, 'snap', 0.7), (T_IMP + 0.05, 'poof', 0.5),
        (SAFE_T, 'stamp', 0.8), (T4, 'whoosh', 0.6), (T4 + 0.1, 'ding', 0.7), (TAP_T, 'click', 0.8), (TL, 'whoosh', 0.7)]


def build_audio(vo_path, out_wav, target=-15.5):          # AAC lands ~0.5 LU lower -> about -16 LUFS
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', vo_path, '-ar', str(sfx.SR), '-ac', '1', '-f', 'f32le', '-'],
                         capture_output=True, check=True).stdout
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
    pk = np.max(np.abs(mix_))
    if pk > 0.89: mix_ = np.tanh(mix_ / 0.89) * 0.89     # soft limit the few sfx peaks
    write(mix_)


def safecheck():
    """Text boxes: every headline/caption/pill/poll must lie within y 12-62 % and x < 85 %."""
    y0, y1, x1 = 0.12 * H, 0.62 * H, 0.85 * W
    boxes = []
    for i, (t0, y) in enumerate(((-0.28, 440), (-0.2, 560))):
        im = headline_line(i); k = _hl_scale(); boxes.append(('headline%d' % i, SX - im.width * k / 2, y - im.height * k / 2, SX + im.width * k / 2, y + im.height * k / 2))
    for ci in range(len(CHUNKS)):
        im = caption_img(ci, None); boxes.append(('caption%d' % ci, SX - im.width / 2, SY - im.height / 2 + 26, SX + im.width / 2, SY + im.height / 2 - 20))
    for txt, c, sz in (('PRETENSIONER', (BUB_C[0] + 10, BUB_C[1] + BUB_R + 52), 64), ('WITH PRETENSIONER', (345, 285), 52), ('WITHOUT', (190, 1022), 52),
                       ('SNUG', (400, 478), 64), ('BEFORE IMPACT', (630, 398), 56)):
        im = pill_img(txt, YEL, sz=sz); boxes.append((txt, c[0] - im.width / 2, c[1] - im.height / 2, c[0] + im.width / 2, c[1] + im.height / 2))
    im = stamp_img(); boxes.append(('SAFE', 560 - im.width * 0.62 / 2 - 20, 560 - im.height * 0.62 / 2 - 20, 560 + im.width * 0.62 / 2 + 20, 560 + im.height * 0.62 / 2 + 20))
    im = poll_img(760); boxes.append(('poll', SX - im.width / 2 - 20, 700 - im.height / 2 - 20, SX + im.width / 2 + 20, 700 + im.height / 2 + 20))
    im = tag_img(); boxes.append(('tag', SX - im.width / 2, 282 - im.height / 2, SX + im.width / 2, 282 + im.height / 2))
    bad = [b for b in boxes if b[1] < 0 or b[2] < y0 or b[3] > x1 or b[4] > y1]
    for b in boxes: print('%-18s x %4d-%4d  y %4d-%4d  %s' % (b[0], b[1], b[3], b[2], b[4], 'FAIL' if b in bad else 'ok'))
    print('SAFE ZONE', 'FAIL' if bad else 'PASS', f'(y {y0:.0f}-{y1:.0f}, x < {x1:.0f})')
    return not bad


if __name__ == '__main__':
    mode = sys.argv[1]
    if mode == 'still':
        os.makedirs(sys.argv[2], exist_ok=True)
        for ts in sys.argv[3:]: frame_img(float(ts)).save(os.path.join(sys.argv[2], f'f_{float(ts):05.2f}.png'))
    elif mode == 'cover':
        frame_img(0.0).save(sys.argv[2])
    elif mode == 'safecheck':
        sys.exit(0 if safecheck() else 1)
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
