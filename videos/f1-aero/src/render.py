"""F1 aerodynamics explainer, lit isometric pixel art, presented by Main Guy. 1080x1920.
Usage: python render.py video VOICE.wav WORDS.json OUT.mp4
       python render.py still WORDS.json OUTDIR t1 t2 ..."""
import json, math, subprocess, sys, wave
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from engine import W, H, SC, C, col, hr, BAYER, ease, grade
import car as CAR
import scenes as S

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'new-car-trap' / 'src'))
import pix, sfx                                      # Main Guy sprite + sound effects

OW, OH, FPS, SR = W * SC, H * SC, 30, 44100
FONT_DIR = Path('/usr/share/fonts/opentype/inter')
F_CAP = ImageFont.truetype(str(FONT_DIR / 'Inter-Black.otf'), 92)
F_CAP2 = ImageFont.truetype(str(FONT_DIR / 'Inter-Black.otf'), 100)
F_TITLE = ImageFont.truetype(str(FONT_DIR / 'Inter-Black.otf'), 150)
F_PILL = ImageFont.truetype(str(FONT_DIR / 'Inter-ExtraBold.otf'), 50)
F_NUM = ImageFont.truetype(str(FONT_DIR / 'Inter-Black.otf'), 86)
F_SMALL = ImageFont.truetype(str(FONT_DIR / 'Inter-Bold.otf'), 38)
YEL, CYAN, RED, GRN, WHITE = '#ffd84a', '#6ae6ff', '#ff5a48', '#4ade80', '#ffffff'

WORDS, LINE_T = [], []


def load_words(p):
    global WORDS, LINE_T
    WORDS = json.load(open(p)); n = max(w['line'] for w in WORDS) + 1
    LINE_T = [min(w['s'] for w in WORDS if w['line'] == i) for i in range(n)]


def wt(line, i): return [w for w in WORDS if w['line'] == line][i]['s']


def cur_line(t):
    k = 0
    for i, s in enumerate(LINE_T):
        if t >= s - .1: k = i
    return k


# ============================== scene builders: return (small RGB array, HUD list) ==============================
def lab_car(t, cam=(74, 159), k=4.0, Z=0.0, hi=(), flap=0.0, squash=0.0, mode=None, posts=False, smoke_cl='#e6f8ff', speed=34):
    c, I = S.lab(t, cam, k)
    if mode: S.smoke(I, t, Z=Z if mode == 'under' else 0, mode=mode, when='far', speed=speed)
    if posts: S.lift_posts(I, Z)
    CAR.f1(I, 0, 0, '+x', t, Z, hi, flap, squash, spin=0 if mode is None else 6)
    if mode: S.smoke(I, t, Z=Z if mode == 'under' else 0, mode=mode, cl=smoke_cl, speed=speed)
    return c, I


def g_lab(a): return grade(a, (.92, 1.0, 1.08), (1.0, 1.0, 1.02), .4, .45)
def g_gold(a): return grade(a, (.95, .95, 1.05), (1.06, 1.0, .92), .38, .35)


def sc_hook(t, lt):
    k = 1.55 + .3 * ease(lt / 3)
    c, I = S.track(t + 1.0, k=k, cam=(108 - (35 - 18) * k, 196 - ((35 + 18) / 2) * k))
    a = g_gold(c.a)
    if wt(0, 6) <= t < wt(0, 6) + .5: a = a[::-1]
    return a, []


def sc_air(t, lt):
    on = t >= wt(1, 6) - .1
    c, I = lab_car(t, mode='over' if on else None)
    hud = [('pill', 108, 300, 'NOT THE ENGINE', RED)] if not on else [('pill', 108, 300, 'THE AIR', CYAN)]
    return g_lab(c.a), hud


def flipstate(t, ev):
    fy = ev[0][1]; prev = fy
    for te, tg in ev:
        if t >= te: fy = prev + (tg - prev) * ease((t - te) / .4); prev = tg
    return fy


def sc_wing(t, lt):
    fy = flipstate(t, [(0, 1), (wt(2, 9), -1), (wt(3, 0) - .1, 1), (wt(3, 6), -1)])
    if abs(fy) < .08: fy = .08 if fy >= 0 else -.08
    c, I = S.lab(t, (96, 170), 3.6)
    S.smoke(I, t, X0=-2, Y0=-6, lanes=[(-4, 4), (-1, 4)], when='front', speed=30)
    S.wing_section(I, fy, t)
    lanes = [(2 + i * 4, 0) for i in range(6)]
    for li, (ly, _) in enumerate(lanes):                    # air over / under the aerofoil
        for i in range(6):
            head = 40 - ((t * 32 + i * 9 + li * 2.3) % 60)
            for j in range(32):
                u = j / 32; X = head + u * 9
                inside = -2 < X < 26
                bump = 3.2 * math.sin(math.pi * min(1, max(0, (26 - X) / 28))) if inside else 0
                for side in (1, -1):
                    z = 12 + side * (5 + bump * (1.3 if side * fy > 0 else .55))
                    x_, y_ = I.p(X, -6 + ly, z)
                    fast = side * fy > 0
                    S.blend(c, x_, y_, '#9af0ff' if fast else '#e6f8ff', (1 - u) * (.8 if fast else .5))
    if fy > .6: S.arrow3d_up(I, 12, 7, 20, 8, '#3ac860')
    if fy < -.6: S.arrow3d(I, 12, 7, 19, 8, '#ff4a3a')
    hud = [('pill', 108, 300, 'PLANE WING  =  LIFT', GRN)] if fy > .6 else ([('pill', 108, 300, 'F1 WING  =  DOWNFORCE', RED)] if fy < -.6 else [])
    return g_lab(c.a), hud


def sc_slam(t, lt):
    sq = .7 * ease((lt - .25) / .2)
    c, I = lab_car(t, squash=sq)
    for i, (X, Y) in enumerate(((6, 3), (6, 10), (15, 6.5), (23, 3.5), (23, 9.5))):
        u = ease((lt - i * .05) / .3)
        S.arrow3d(I, X, Y, 6.5 + (1 - u) * 22, 7)
    if lt > .3:
        sh = int(3 * math.sin(lt * 70) * max(0, .6 - lt))
        c.a[:] = np.roll(c.a, sh, 0)
        I.glow(15, 6.5, 0, 40, '#ffd84a', .25 * max(0, 1 - (lt - .3) * 2), 14)
    return g_lab(c.a), ([('title', 'DOWNFORCE', 1160, YEL)] if lt > .25 else [])


def sc_tyre(t, lt):
    c, I = S.straight(t, speed=110, cam=(38, 78), k=7)
    sq = .35 + .15 * math.sin(lt * 7)
    CAR.f1(I, 0, 0, '+x', t, squash=sq, spin=20)
    I.glow(23, 13.6, 0, 14, '#ffd84a', .45 + .2 * math.sin(lt * 7), 4)
    for i, X in enumerate((20, 23, 26)):
        S.arrow3d(I, X, 13, 5.2 + .8 * abs(math.sin(lt * 5 + i)), 2.5, w=.8)
    return g_gold(c.a), [('meter', 'GRIP', min(1, lt / 2.6), GRN)]


def sc_corner(t, lt):
    c, I, (gx, gy), (x, y) = S.corner(t, lt)
    hud = [('wpill', I.p(gx, gy + 6.5, 12), 'NO AERO', '#c8ccd8'), ('wpill', I.p(x, y, 12), 'AERO', CYAN)]
    if lt > 1.25: hud.append(('pill', 108, 300, 'SLIDES OFF', RED))
    return g_gold(c.a), hud


def sc_front(t, lt):
    c, I = lab_car(t, cam=(15, 131), k=5.0, hi=('fw',), mode='front')
    return g_lab(c.a), [('wpill', I.p(28, 13, 6), 'FRONT WING', YEL)]


def sc_rear(t, lt):
    c, I = lab_car(t, cam=(128, 214), k=5.0, hi=('rw',), mode='rear')
    S.arrow3d(I, 1.6, 6.5, 9.4 + .8 * abs(math.sin(lt * 5)), 7)
    return g_lab(c.a), [('wpill', I.p(2, 0, 14), 'REAR WING', YEL)]


def sc_floor(t, lt):
    Z = 6 * ease(lt / .9)
    c, I = lab_car(t, Z=Z, hi=('floor',) if lt > .8 else (), posts=True)
    return g_lab(c.a), ([('wpill', I.p(15, 13, Z), 'THE FLOOR', YEL)] if lt > .9 else [])


def sc_under(t, lt):
    ts = wt(10, 7)
    Z = 6 if t < ts else 6 * (1 - ease((t - ts) / .3))
    c, I = lab_car(t, Z=Z, hi=('floor',), mode='under', posts=t < ts, smoke_cl='#7ae8ff', speed=60)
    if t < ts:
        I.glow(15, 6.5, Z * .4, 34, '#3a8aff', .3 + .1 * math.sin(t * 6), 14)
        return g_lab(c.a), [('wpill', I.p(15, 13, 0), 'FAST AIR = LOW PRESSURE', CYAN)]
    I.glow(15, 6.5, 0, 50, '#ffd84a', .3 * max(0, 1 - (t - ts - .3) * 2), 14)
    return g_lab(c.a), [('title', 'SUCKED DOWN', 1160, YEL)]


def sc_weight(t, lt):
    dur = LINE_T[12] - LINE_T[11]; u = min(1, lt / (dur - .3))
    c, I = S.straight(t, speed=90 + 160 * u)
    CAR.f1(I, 0, 0, '+x', t, squash=.5 * u, spin=24)
    f = u * 1.05
    return g_gold(c.a), [('bars', .55, f), ('speed', int(100 + 230 * u), WHITE)]


def sc_ceiling(t, lt):
    c, I = S.straight(t, speed=220, cam=(74, 150), k=3.6)
    CAR.f1(I, 0, 0, '+x', t, spin=26)
    a = g_gold(c.a)[::-1].copy()                              # the road is now the tunnel ceiling
    a[250:] = a[250:] * .25 + np.array([10, 10, 16]) * .75
    for i in range(7):
        x = (i * 37 - t * 260) % 260 - 30
        a[262:265, max(0, int(x)):max(0, int(x + 18))] = col('#ffd98a')
    return np.clip(a, 0, 255), ([('title', 'IT STICKS', 1160, YEL)] if lt > .6 else [])


def sc_drag(t, lt):
    tk = wt(13, 7)
    c, I = lab_car(t, mode='wake', speed=40)
    spd = 340 if t < tk else int(340 - 50 * ease((t - tk) / .8))
    hud = [('speed', spd, WHITE if t < tk else RED)]
    if lt > .5: hud.append(('arrow', I.p(30, 6.5, 6), I.p(4, 6.5, 6), 'DRAG', RED))
    return g_lab(c.a), hud


def sc_flaps(t, lt):
    tb = wt(14, 10)
    st = t < tb
    fl = ease(lt / .45) if st else 1 - ease((t - tb) / .3)
    c, I = S.straight(t, speed=170 if st else 80, cam=(128, 214), k=5.0)
    CAR.f1(I, 0, 0, '+x', t, flap=fl, hi=('rw', 'fw') if (st and lt < 1.2) or (not st and t - tb < .8) else (), spin=22)
    spd = int(300 + 50 * ease(lt / 2)) if st else int(350 - 160 * ease((t - tb) / 1.2))
    return g_gold(c.a), [('pill', 108, 300, 'STRAIGHT MODE: LOW DRAG' if st else 'CORNER MODE: GRIP', CYAN if st else YEL),
                         ('speed', spd, WHITE)]


def sc_recap(t, lt):
    k = 1.7
    c, I = S.track(t + 1.0, k=k, cam=(108 - 17 * k, 196 - 26.5 * k))
    hud = [('wpill', I.p(S.TX - 2, 2, 4), 'GRIP', YEL), ('wpill', I.p(2, S.TY - 2, 4), 'GRIP', YEL),
           ('wpill', I.p(S.TX / 2, S.TY + 3, 4), 'SPEED', CYAN), ('wpill', I.p(S.TX / 2, -3, 4), 'SPEED', CYAN)]
    return g_gold(c.a), hud


def sc_cta(t, lt):
    a, _ = sc_recap(t, lt)
    return a * .45, [('title', 'UPSIDE', 760, YEL), ('title', 'DOWN?', 920, YEL), ('pill', 108, 300 + 0, 'COMMENT BELOW', WHITE)]


SCENES = [sc_hook, sc_air, sc_wing, sc_wing, sc_slam, sc_tyre, sc_corner, sc_front, sc_rear, sc_floor, sc_under,
          sc_weight, sc_ceiling, sc_drag, sc_flaps, sc_recap, sc_cta]
POSE = ['point', 'talkR', 'talkB', 'pointup', 'cheer', 'point', 'shock', 'point', 'hips', 'pointup', 'talkB', 'shrug',
        'shock', 'sad', 'point', 'cheer', 'wave']
KEY = {'AIR', 'WING', 'DOWNFORCE', 'GRIP', 'TIRES', 'FLOOR', 'DRAG', 'CEILING', 'UPSIDE', 'DOWN', 'CORNERS', 'STRAIGHTS',
       'FLATTEN', 'STICK', 'UP', 'FASTER'}


# ============================== overlays at full resolution ==============================
_GUY = {}


def guy_img(e, p):
    if (e, p) not in _GUY:
        g = pix.guy(e, False, p).convert('RGBA')
        _GUY[(e, p)] = g.resize((g.width * 10, g.height * 10), Image.NEAREST)
    return _GUY[(e, p)]


def presenter(img, t, line):
    talking = any(w['s'] <= t < w['e'] for w in WORDS)
    p = POSE[line]
    if p == 'cheer': p = 'up1' if int(t * 5) % 2 else 'up2'
    if p == 'wave': p = 'wave1' if int(t * 4) % 2 else 'wave2'
    if line == 3 and t >= wt(3, 6): p = 'point'
    if line == 6 and t < LINE_T[6] + 1.25: p = 'point'
    if line == 13 and t < wt(13, 7): p = 'talkR'
    e = ('talk' if int(t * 11) % 2 == 0 else 'smile') if talking else ('blink' if (t % 3.1) < .12 else 'smile')
    if p == 'shock' and not talking: e = 'shock'
    if p == 'sad': e = 'sadtalk' if talking and int(t * 11) % 2 == 0 else 'sad'
    g = guy_img(e, p)
    bob = 10 if (not talking and (t * 1.6) % 1 < .5) else 0
    x0, y0 = -40, OH - g.height + 30 + bob
    sh = Image.new('RGBA', img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(sh)
    d.ellipse([x0 + 90, OH - 70, x0 + 400, OH - 10], fill=(0, 0, 0, 110))
    img.alpha_composite(sh); img.alpha_composite(g, (x0, y0))


def stroke_text(d, xy, s, font, fill, stroke=10, anchor='mm'):
    d.text(xy, s, font=font, fill=fill, stroke_width=stroke, stroke_fill=(10, 10, 18), anchor=anchor)


def captions(img, t):
    said = [w for w in WORDS if w['s'] - .05 <= t]
    if not said: return
    li = said[-1]['line']; ws = [w for w in WORDS if w['line'] == li]
    groups, cur = [], []
    d = ImageDraw.Draw(img)
    for w in ws:
        trial = ' '.join(x['w'].upper().strip('.,?') for x in cur + [w])
        if cur and (len(cur) == 3 or d.textlength(trial, font=F_CAP) > 900): groups.append(cur); cur = []
        cur.append(w)
    if cur: groups.append(cur)
    for gi, g in enumerate(groups):
        end = groups[gi + 1][0]['s'] if gi + 1 < len(groups) else g[-1]['e'] + .3
        if not (g[0]['s'] - .05 <= t < end): continue
        font = F_CAP2 if t - g[0]['s'] < .07 else F_CAP
        toks = [w['w'].upper().strip('.,') for w in g]
        total = sum(d.textlength(s_, font=font) for s_ in toks) + 26 * (len(toks) - 1)
        x = OW / 2 - total / 2
        for w, s_ in zip(g, toks):
            key = s_.strip("?!'S") in KEY or s_.strip('?!') in KEY
            active = w['s'] - .05 <= t
            fill = YEL if key else WHITE
            if not active: fill = (255, 255, 255, 150)
            stroke_text(d, (x, 175), s_, font, fill, 11, 'lm')
            x += d.textlength(s_, font=font) + 26


def pill(img, cx, cy, s, color, font=F_PILL):
    ov = Image.new('RGBA', img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    w = d.textlength(s, font=font) + 64; h = 84
    cx = min(OW - w / 2 - 20, max(w / 2 + 20, cx))
    d.rounded_rectangle([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2], radius=h // 2, fill=(12, 14, 22, 215),
                        outline=color, width=6)
    d.text((cx, cy + 2), s, font=font, fill=color, anchor='mm')
    img.alpha_composite(ov)


def hud(img, items, t):
    d = ImageDraw.Draw(img)
    for it in items:
        k = it[0]
        if k == 'pill': pill(img, it[1] * SC, it[2], it[3], it[4])
        elif k == 'wpill':
            (x, y), s_, cl = it[1], it[2], it[3]
            pill(img, x * SC, y * SC - 70, s_, cl)
        elif k == 'title':
            stroke_text(ImageDraw.Draw(img), (OW / 2, it[2]), it[1], F_TITLE, it[3], 14)
        elif k == 'speed':
            ov = Image.new('RGBA', img.size, (0, 0, 0, 0)); dd = ImageDraw.Draw(ov)
            dd.rounded_rectangle([OW - 420, 1440, OW - 40, 1640], radius=36, fill=(12, 14, 22, 215), outline=(255, 255, 255, 90), width=4)
            dd.text((OW - 230, 1520), f'{it[1]}', font=F_NUM, fill=it[2], anchor='mm')
            dd.text((OW - 230, 1598), 'KM/H', font=F_SMALL, fill=(200, 205, 220), anchor='mm')
            img.alpha_composite(ov)
        elif k == 'meter':
            ov = Image.new('RGBA', img.size, (0, 0, 0, 0)); dd = ImageDraw.Draw(ov)
            x0, y0, x1, y1 = OW - 200, 500, OW - 100, 1100
            dd.rounded_rectangle([x0 - 14, y0 - 14, x1 + 14, y1 + 14], radius=30, fill=(12, 14, 22, 215))
            hh = (y1 - y0) * min(1, max(0, it[2]))
            dd.rounded_rectangle([x0, y1 - hh, x1, y1], radius=18, fill=it[3])
            dd.text(((x0 + x1) / 2, y1 + 70), it[1], font=F_PILL, fill=it[3], anchor='mm')
            img.alpha_composite(ov)
        elif k == 'bars':
            ov = Image.new('RGBA', img.size, (0, 0, 0, 0)); dd = ImageDraw.Draw(ov)
            dd.rounded_rectangle([60, 330, OW - 60, 640], radius=36, fill=(12, 14, 22, 205))
            for row, (label, frac, cl) in enumerate((('WEIGHT', it[1], (170, 176, 194)),
                                                    ('DOWNFORCE', it[2], YEL if it[2] > it[1] and int(t * 8) % 2 else CYAN))):
                y = 420 + row * 130
                dd.text((100, y), label, font=F_SMALL, fill=(230, 232, 240), anchor='lm')
                dd.rounded_rectangle([420, y - 30, OW - 100, y + 30], radius=30, fill=(40, 44, 58))
                dd.rounded_rectangle([420, y - 30, 420 + (OW - 520) * min(1, max(0, frac)), y + 30], radius=30, fill=cl)
            img.alpha_composite(ov)
        elif k == 'arrow':
            (xa, ya), (xb, yb), label, cl = it[1], it[2], it[3], it[4]
            xa, ya, xb, yb = xa * SC, ya * SC - 260, xb * SC, yb * SC - 260
            d.line([xa, ya, xb, yb], fill=cl, width=28)
            ang = math.atan2(yb - ya, xb - xa)
            tip = [(xb + 40 * math.cos(ang), yb + 40 * math.sin(ang)),
                   (xb + 60 * math.cos(ang + 2.4), yb + 60 * math.sin(ang + 2.4)),
                   (xb + 60 * math.cos(ang - 2.4), yb + 60 * math.sin(ang - 2.4))]
            d.polygon(tip, fill=cl)
            stroke_text(d, ((xa + xb) / 2, (ya + yb) / 2 - 80), label, F_NUM, cl, 10)


def scene_frame(line, t):
    a, items = SCENES[line](t, t - LINE_T[line])
    return a, items


def frame(t):
    line = cur_line(t)
    a, items = scene_frame(line, t)
    lt = t - LINE_T[line]
    if line > 0 and lt < .14:                                   # chunky dissolve from the previous scene
        b, _ = scene_frame(line - 1, t)
        f = lt / .14
        ys, xs = np.mgrid[0:H, 0:W]
        m = (BAYER[(ys // 3) % 4, (xs // 3) % 4] < f)[..., None]
        a = np.where(m, a, b)
    end = WORDS[-1]['e'] + .9
    a = a * max(0, min(1, t / .25, (end - t) / .5))
    img = Image.fromarray(np.repeat(np.repeat(np.clip(a, 0, 255).astype(np.uint8), SC, 0), SC, 1)).convert('RGBA')
    hud(img, items, t)
    presenter(img, t, line)
    captions(img, t)
    return img.convert('RGB')


# ============================== audio ==============================
def audio(voice_path, out_path, dur):
    with wave.open(str(voice_path)) as w:
        vr = w.getframerate(); v = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
    n = int(SR * dur); tt = np.arange(n) / SR
    voice = np.interp(tt, np.arange(len(v)) / vr, v, right=0)
    noise = np.random.default_rng(3).standard_normal(n)
    lp = lambda x, k: np.convolve(x, np.ones(k) / k, 'same')
    tri = lambda f: 2 / np.pi * np.arcsin(np.sin(2 * np.pi * f * tt))
    music = np.zeros(n); beat = 60 / 112 / 2
    chords = [(220, 261.6, 329.6), (174.6, 220, 261.6), (261.6, 329.6, 392), (196, 246.9, 293.7)]
    for i in range(int(dur / beat)):
        s0 = i * beat; ch = chords[(i // 8) % 4]; f = ch[[0, 1, 2, 1, 2, 1, 0, 2][i % 8]] * 2
        m = (tt >= s0) & (tt < s0 + beat)
        music[m] += tri(f)[m] * np.exp(-(tt[m] - s0) * 8) * .045
        if i % 2 == 0: music[m] += np.exp(-(tt[m] - s0) * 30) * np.sin(2 * np.pi * 55 * (tt[m] - s0)) * .1
        if i % 4 == 2: music[m] += lp(noise, 2)[m] * np.exp(-(tt[m] - s0) * 40) * .035
        if i % 8 == 0:
            m2 = (tt >= s0) & (tt < s0 + beat * 8); music[m2] += tri(ch[0] / 2)[m2] * .028
    env = np.convolve(np.abs(voice) > .02, np.ones(int(SR * .25)) / (SR * .25), 'same')
    music *= 1 - .55 * np.clip(env * 3, 0, 1)
    wind = lp(noise, 30) * .05 * sum(np.clip(np.minimum((tt - LINE_T[i] + .1) / .2, (LINE_T[i + 1] - tt) / .2), 0, 1)
                                     for i in (1, 7, 8, 10, 13) if i + 1 < len(LINE_T))
    cues = [(LINE_T[i] - .05, 'whoosh', .3) for i in range(1, len(LINE_T))]
    cues += [(.15, 'vroom', .5), (wt(0, 6), 'whoosh', .4), (LINE_T[4] + .25, 'boom', .55), (LINE_T[4] + .3, 'ding', .3),
             (LINE_T[6] + 1.2, 'screech', .5), (wt(10, 7) + .25, 'thump', .7), (LINE_T[12] + .6, 'pop', .4),
             (wt(14, 0), 'whoosh', .45), (wt(14, 10), 'stamp', .35), (LINE_T[16], 'sparkle', .4)]
    fx = sfx.render(cues, dur); fx = np.interp(tt, np.arange(len(fx)) / sfx.SR, fx)
    mix = voice + music * .9 + wind + fx * .55
    mix *= np.clip(np.minimum(tt / .2, (dur - tt) / .5), 0, 1)
    mix = np.clip(mix / max(1e-6, np.abs(mix).max()) * .89, -1, 1)
    with wave.open(str(out_path), 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.c_[mix, mix] * 32767).astype(np.int16).tobytes())


if __name__ == '__main__':
    if sys.argv[1] == 'still':
        load_words(sys.argv[2]); out = Path(sys.argv[3]); out.mkdir(parents=True, exist_ok=True)
        for s_ in sys.argv[4:]: frame(float(s_)).save(out / f'f_{s_}.png')
    else:
        voice, words, out = sys.argv[2], sys.argv[3], Path(sys.argv[4]); load_words(words)
        dur = WORDS[-1]['e'] + 1.0
        wav = out.with_suffix('.wav'); audio(voice, wav, dur)
        p = subprocess.Popen(['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{OW}x{OH}',
                              '-r', str(FPS), '-i', '-', '-i', str(wav), '-c:v', 'libx264', '-preset', 'medium', '-crf', '17',
                              '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart',
                              str(out)], stdin=subprocess.PIPE)
        for i in range(int(dur * FPS)): p.stdin.write(frame(i / FPS).tobytes())
        p.stdin.close(); sys.exit(p.wait())
