"""6-second PIXEL stickman fight test (no VO, no captions) -> out/seatbelt-fight/pixel-fight6.mp4

Motion reuses fight6.py (mocap move library, key-aligned segments, 6-frame bone-direction cross-fades,
stage solve, foot-plant IK, contact IK) with a new 12-beat sheet (pixel6_choreo.json). New here:
contact frames re-found from effector speed (full extension after the speed peak) with the defender's
reaction started on that frame; figures drawn on 1s at 30 fps, effects on 2s, held to 60 fps output.
Look: whole scene drawn at 270x480 in a fixed 32-colour palette (Bayer-dithered gradients, 1-px dark
outlines), 6 parallax layers moved in whole pixels, nearest-neighbour 4x upscale to 1080x1920.
Usage: python pixel6.py [--drawings 0,40,...]   (preview PNGs of single 30 fps drawings)
"""
import json, math, os, subprocess, sys, types
import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import gaussian_filter1d

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
try:
    import cairo  # noqa: F401
except ImportError:  # fight6's flat-vector drawing is not used here; only its motion pipeline
    sys.modules['cairo'] = types.ModuleType('cairo')
import fight6 as F6  # noqa: E402
from fight6 import I, proj, head_c, ease, sample, mv  # noqa: E402
import sfx  # noqa: E402

F6.SHEET = os.path.join(HERE, '../pixel6_choreo.json')
OUT = F6.OUT
UP, FPS = 4, 60
NDRAW = 180                                   # 6.0 s of 30 fps drawings
D = {'hero': 1, 'opp': -1}
import refstyle as RS  # noqa: E402
W, H = RS.W, RS.H


# ---------------------------------------------------------------- motion (fight6 pipeline + speed-found contacts)
def refine_contacts(segs, contacts, sh):
    S, X = sh['fight_story_frames'], sh['crossfade']
    for k in contacts:
        A, _ = F6.compose(segs[k['att']], sh['start'][k['att']]['x'], D[k['att']], S, X)
        v = np.r_[0, np.linalg.norm(np.diff(A[:, I[k['eff']]], axis=0), axis=1)] * FPS
        c = k['c']; lo, hi = max(1, c - 12), min(S - 2, c + 8)
        p = lo + int(np.argmax(v[lo:c + 3]))
        f = p
        while f < hi and v[f] > 0.4 * v[p]: f += 1             # full extension: speed falls after the peak
        nc = int(np.clip(f, c - 6, c + 6))
        k.update(c_planned=c, c=nc, peak=p, vpeak=float(v[p]))
        k['seg'].dx_end = nc - 4
        if k.get('rseg'): k['rseg'].start = nc                 # reaction starts on the contact frame
    for who in segs: segs[who].sort(key=lambda g: g.start)


def separate(Wd, contacts, gap=230.0):
    """Stage spacing: where the bodies would overlap, ease both fighters apart (smoothed, so it reads as
    footwork; the foot-plant IK that runs afterwards keeps planted feet locked). Fly-out frames excluded."""
    from scipy.ndimage import maximum_filter1d
    h, o = Wd['hero'], Wd['opp']
    g = np.minimum(o[:, I['thorax'], 0] - h[:, I['thorax'], 0], o[:, 0, 0] - h[:, 0, 0])
    need = np.clip(gap - g, 0, None)
    fin = [k for k in contacts if k['finisher']]
    if fin: need[fin[0]['c'] + 1:] = 0
    need = gaussian_filter1d(maximum_filter1d(need, 13), 5, mode='nearest')
    h[:, :, 0] -= need[:, None] / 2; o[:, :, 0] += need[:, None] / 2
    return need


def build_motion():
    sh, segs, contacts = F6.load_sheet()
    S, X = sh['fight_story_frames'], sh['crossfade']
    fx = {b['n']: b['contact'].get('fx', 'spark') for b in sh['beats'] if b.get('contact')}
    for k in contacts: k['fx'] = fx[k['beat']]
    refine_contacts(segs, contacts, sh)
    F6.solve_stage(segs, contacts, sh)
    Wd, sl = {}, {}
    for w in ('hero', 'opp'):
        Wd[w], sl[w] = F6.compose(segs[w], sh['start'][w]['x'], D[w], S, X)
    separate(Wd, contacts)
    for w in ('hero', 'opp'):
        Wd[w] = F6.plant(Wd[w], sl[w])
    Wd = F6.layer_proc(Wd, contacts)
    times = list(range(0, S, 2))
    for k in contacts:
        j = int(np.argmin([abs(t - k['c']) for t in times])); times[j] = k['c']
    draws = []
    for t in times:
        draws.append(t)
        draws += [t] * sum(k['hitstop'] for k in contacts if k['c'] == t)
    assert len(draws) == sh['fight_drawings'], (len(draws), sh['fight_drawings'])
    for k in contacts:
        k['d'] = draws.index(k['c'])
    return sh, segs, contacts, Wd, draws, sl


# ---------------------------------------------------------------- film
TRD = NDRAW - 144                                             # (audio timing) transition = 36 x 2 output frames
NF_FIGHT, NF_TR = 288, 72
SW, GYW = 0.066, 388                                          # wide shot: figure ~56 px (12 % of the frame), feet on the path
SC_CLOSE = 0.13


def scr(P, cx, gy, s):
    """World pose -> whole-pixel screen coords (x, y) + depth; camera offset rounded once (no crawl)."""
    Q = proj(P)
    return np.stack([np.round(Q[:, 0] * s) - round(cx * s) + W // 2, np.round(Q[:, 1] * s) + gy, Q[:, 2]], -1)


def scr_pts(Pxy, cx, gy, s):
    P = np.asarray(Pxy, float)
    return np.stack([np.round(P[:, 0] * s) - round(cx * s) + W // 2, np.round(P[:, 1] * s) + gy], -1)


def anchor(P, a, b, u=.5):
    Q = proj(P)
    return (Q[I[a], :2] + (Q[I[b], :2] - Q[I[a], :2]) * u)


class Film:
    def __init__(s):
        s.sh, s.segs, s.contacts, s.Wd, s.draws, s.slide = build_motion()
        s.ND = len(s.draws)
        S = s.sh['fight_story_frames']
        s.story = []                                           # 60 fps output frame -> story frame (hit-stops repeat)
        for t in range(S):
            s.story.append(t)
            s.story += [t] * (2 * sum(k['hitstop'] for k in s.contacts if k['c'] == t))
        assert len(s.story) == NF_FIGHT, len(s.story)
        for k in s.contacts:
            k['o'] = s.story.index(k['c'])
        s.fin = [k for k in s.contacts if k['finisher']][0]
        s.world = RS.paint_world()
        s.road_world = RS.grade_layers(RS.paint_world(road=True), (.5, .42, .6), (16, 8, 26))
        s.camera(); s.dust_events(); s.cloth()

    def pose(s, who, t):
        return s.Wd[who][int(min(max(t, 0), len(s.Wd[who]) - 1))]

    # -------------------------------------------------------------- camera (whole pixels)
    def camera(s):
        N = NF_FIGHT; hx = np.zeros(N); ox = np.zeros(N)
        for o, t in enumerate(s.story):
            hx[o] = proj(s.pose('hero', t))[I['thorax'], 0]; ox[o] = proj(s.pose('opp', t))[I['thorax'], 0]
        of = s.fin['o']; hs = 2 * s.fin['hitstop']
        ox = np.where(np.arange(N) > of + hs, np.minimum(ox, hx + 500), ox)
        cx = gaussian_filter1d((hx + ox) / 2, 8, mode='nearest')
        u0 = np.clip(np.arange(N) / 45, 0, 1)
        cx += 1000 * (1 - u0 * u0 * (3 - 2 * u0))              # opening truck-in along the meadow
        cx += np.linspace(160, -160, N)                         # slow continuous drift (parallax keeps moving)
        t = s.fin['c']; Ph = proj(s.pose('hero', t))
        IP = (Ph[I[s.fin['eff']], :2] + proj(np.array([head_c(s.pose('opp', t))]))[0, :2]) / 2
        s.close = (of - 8, of + hs + 8)
        s.cams = []
        for o in range(N):
            if s.close[0] <= o < s.close[1]:                    # hard cut to a close shot on the finisher
                s.cams.append((IP[0], int(round(250 - IP[1] * SC_CLOSE)), SC_CLOSE))
            else:
                s.cams.append((cx[o], GYW, SW))
        for k in s.contacts:                                    # whole-pixel camera shake on hits
            if k['evade']: continue
            amp = 2 if k['size'] >= 1 else 1
            for j, (dx, dy) in enumerate(((amp, -amp), (-amp, amp), (amp, 0), (-1, 1), (1, 0))):
                o = k['o'] + j
                if o < N:
                    c = s.cams[o]; s.cams[o] = (c[0] + dx / c[2], c[1] + dy, c[2])

    def dust_events(s):
        ev = []; S = len(s.Wd['hero'])
        for who in ('hero', 'opp'):
            A = s.Wd[who]; last = -99
            for side in 'lr':
                y = A[:, I[side + 'tibia'], 1]; vy = np.r_[0, np.diff(y)] * FPS
                for f in range(2, S):
                    if y[f - 2] > 75 and y[f] <= 62 and vy[f - 1] < -250 and f - last > 30:
                        ev.append((f, who, side)); last = f
            for sg in s.segs[who]:
                if sg.slide and sg.start < S and sg.start - last > 8:
                    ev.append((int(sg.start) + 2, who, 'l')); last = sg.start
        s.dust = [(s.story.index(min(s.story, key=lambda x: abs(x - f))), f, who, side) for f, who, side in sorted(ev)]

    # -------------------------------------------------------------- Verlet cloth (opp cape, hero scarf + hair)
    def cloth(s):
        cape, scarf, hair = RS.Chain(7, 60, back=1.0), RS.Chain(4, 40, back=.8), RS.Chain(3, 26, grav=1800, back=.6)
        s.cape, s.scarf, s.hair = [], [], []
        prev = None
        for o, t in enumerate(s.story):
            Po, Ph = s.pose('opp', t), s.pose('hero', t)
            if t != prev:
                c = cape.step(anchor(Po, 'upperback', 'thorax', .7), -1)
                sc = scarf.step(anchor(Ph, 'lowerneck', 'upperneck', .2), 1)
                hr = hair.step(anchor(Ph, 'upperneck', 'head', 1.0) + [-40, 10], 1)
            s.cape.append(c); s.scarf.append(sc); s.hair.append(hr); prev = t
        s.tr_scarf, s.tr_hair = scarf, hair

    # -------------------------------------------------------------- drawing helpers
    def figure(s, img, P, cloth_pts, hair_pts, cx, gy, sc, hero, mask=None):
        S = scr(P, cx, gy, sc)
        lim = 2 if sc < 0.17 else 3
        cl = scr_pts(cloth_pts, cx, gy, sc) if cloth_pts is not None else None
        hc, hr = RS.draw_figure(img, S, I, hero, cl, mask, lim)
        if hero and hair_pts is not None:
            Hp = scr_pts(hair_pts, cx, gy, sc)
            Hp[0] = hc + np.array([-.8 * hr, -.2 * hr])
            for i in range(1, len(Hp)):
                RS.pline(img, Hp[i - 1], Hp[i], max(1, lim - 1), RS.HAIR, mask)
        return S

    def flash_on(s, o):
        if o >= NF_FIGHT - 2: return True                       # the cut into the transition
        for k in s.contacts:
            if not k['evade'] and k['fx'] == 'fire' and k['o'] <= o < k['o'] + (4 if k['finisher'] else 3):
                return True
        return False

    def fight(s, o):
        t = s.story[o]; cx, gy, sc = s.cams[o]
        img = RS.compose(s.world, round(cx * SW), gy - GYW)
        dark = s.flash_on(o)
        if dark: img = RS.dark_grade(img)
        Po, Ph = s.pose('opp', t), s.pose('hero', t)
        s.figure(img, Po, s.cape[o], None, cx, gy, sc, False)
        s.figure(img, Ph, s.scarf[o], s.hair[o], cx, gy, sc, True)
        z = sc / SW
        for k in s.contacts:                                    # crescent slashes along the striking limb
            age = o - (k['o'] - 4)
            if 0 <= age < 14:
                A = s.Wd[k['att']]
                pts = scr(np.array([A[f][I[k['eff']]] for f in range(max(0, k['c'] - 10), min(len(A), k['c'] + 3))]).reshape(-1, 1, 3)[:, 0], cx, gy, sc) \
                    if False else np.array([scr(A[f], cx, gy, sc)[I[k['eff']], :2] for f in range(max(0, k['c'] - 10), min(len(A), k['c'] + 3))])
                root = scr(A[k['c']], cx, gy, sc)[0, :2]
                tg = np.gradient(pts.astype(float), axis=0); nrm = np.stack([-tg[:, 1], tg[:, 0]], 1)
                side = 1.0 if ((pts - root) * nrm).sum() > 0 else -1.0
                RS.fx_slash(img, pts, age, 14, side, z * (.6 if k['evade'] else 1.0), red=(k['fx'] == 'fire' and not k['evade']))
        for k in s.contacts:                                    # bursts, embers, fire streaks
            if k['evade']: continue
            age = o - k['o']
            if 0 <= age < 20:
                P = scr(s.Wd[k['att']][k['c']], cx, gy, sc)[I[k['eff']], :2]
                fire = k['fx'] == 'fire'
                if fire: RS.fx_streak(img, P, age, z * k['size'] ** .4, D[k['att']], k['beat'], k['finisher'])
                RS.fx_burst(img, P, age, z * k['size'] ** .4, k['beat'] * 31, fire, k['finisher'])
        for o0, f, who, side in s.dust:
            age = o - o0
            if 0 <= age < 12:
                Pp = scr(s.Wd[who][min(f, len(s.Wd[who]) - 1)], cx, gy, sc)[I[side + 'tibia']]
                RS.fx_dust(img, (Pp[0], gy), age, z, D[who])
        return img

    # -------------------------------------------------------------- transition
    def tr_hero(s, i):
        rd = mv('ready'); t = (i / FPS) % (2 * rd.dur); t = 2 * rd.dur - t if t > rd.dur else t
        P = sample(rd, t, False).copy(); P[:, [0, 2]] -= P[0, [0, 2]]
        return P

    def car_x(s, i):
        v, i0, i1, stop = 2600 / FPS, 40, 62, 240.0
        brake = v * (i1 - i0) / 2
        if i <= i0: return stop + brake + v * (i0 - i)
        if i <= i1: u = (i - i0) / (i1 - i0); return stop + brake * (1 - u) ** 2
        return stop

    def car_pitch(s, i):
        if i < 40: return 0.0
        if i <= 62: return math.radians(7) * ease((i - 40) / 6, 'out')
        t = (i - 62) / FPS
        return math.radians(7) * math.exp(-t * 9) * math.cos(t * 26)

    def road(s, i, cx, sc, gy, beam=True):
        img = RS.compose(s.road_world, round(cx * SW), gy - GYW)
        x0 = s.car_x(i); p = s.car_pitch(i)
        X = lambda wx: int(round(wx * sc)) - round(cx * sc) + W // 2
        if i > 40:
            for off in (160, 640):
                a, b = X(s.car_x(40) + off), X(x0 + off)
                img[gy:gy + 2, max(0, b):max(0, min(W, a))] = (24, 22, 28)
        dist = max(0.0, 1 - (x0 - 240) / 1800)
        hl = (X(x0 + 36), int(round(-180 * sc)) + gy)
        if beam:                                                # banded headlight cone toward the hero
            yy, xx = np.mgrid[0:H, 0:W]
            dx = hl[0] - xx; spread = np.abs(yy - hl[1] - dx * .05) < 4 + dx * .3
            for reach, col, a in ((300, (255, 214, 140), .22), (200, (255, 232, 176), .3), (110, (255, 246, 214), .4)):
                RS.blend(img, (dx > 0) & (dx < reach * (.6 + .4 * dist)) & spread & (yy < gy + 30), col, a)
        P = s.tr_hero(i)
        m = np.zeros((H, W), bool)
        sp = s.tr_scarf.step(anchor(P, 'lowerneck', 'upperneck', .2), 1)
        hp = s.tr_hair.step(anchor(P, 'upperneck', 'head', 1.0) + [-40, 10], 1)
        s.figure(img, P, sp, hp, cx, gy, sc, True, m)
        if beam:
            rim = m & ~np.roll(m, -1, 1)
            if dist > .2: img[rim] = (255, 226, 160)
        RS.draw_car(img, x0, p, round(cx * sc), sc, gy)
        return img

    def transition(s, j):
        """j = transition frame 0..71: face close-up (0-23), whip pan (24-33), brake + freeze (34-71)."""
        sc, gy = 0.2, 392
        rest = (W / 2 - 45) / sc
        if j < 24:
            bg = s.road(30, rest - 300, sc, gy, beam=False) if not hasattr(s, '_facebg') else s._facebg
            s._facebg = bg
            return RS.face(j, RS.dark_grade(bg) // 2 + bg // 2)
        if j < 34:
            u = ease((j - 23) / 11, 'out')
            cx = -1600 + (rest + 1600) * u
            img = s.road(j, cx, sc, gy, beam=False)
            step = max(1, 12 - (j - 24))
            idx = (np.arange(W) // step) * step
            return img[:, idx]
        return s.road(min(j, 64), rest, sc, gy)

    def frame(s, o):
        img = s.fight(o) if o < NF_FIGHT else s.transition(o - NF_FIGHT)
        return RS.vignette(img)


def upscale(img):
    return np.repeat(np.repeat(img, UP, 0), UP, 1)


# ---------------------------------------------------------------- chiptune sound
SR = sfx.SR


def crush(x, bits=4, hold=4):
    x = np.repeat(x[::hold], hold)[:len(x)]
    q = 2 ** (bits - 1)
    return np.round(np.clip(x, -1, 1) * q) / q


def sq(f, d, duty=.5):
    ph = np.cumsum(np.broadcast_to(f, (int(SR * d),))) / SR
    return np.where(ph % 1 < duty, 1.0, -1.0)


def chip_thump(d=.22):
    t = np.arange(int(SR * d)) / SR
    s = sq(260 * np.exp(-t * 18) + 45, d) * np.exp(-t * 16) * .7
    n = np.random.default_rng(3).standard_normal(len(t)) * np.exp(-t * 60)
    return crush(s + n * .6, 4, 6)


def chip_bass(d=.45, f=55):
    t = np.arange(int(SR * d)) / SR
    ph = np.cumsum(f * (1 + .6 * np.exp(-t * 20))) / SR
    tri = 2 * np.abs(2 * (ph % 1) - 1) - 1
    return crush(tri * np.exp(-t * 6), 5, 2) * 1.1


def chip_whoosh(d=.2, up=True):
    t = np.arange(int(SR * d)) / SR
    hold = (np.linspace(14, 3, len(t)) if up else np.linspace(3, 14, len(t))).astype(int)
    n = np.random.default_rng(int(d * 1000)).standard_normal(len(t)); y = np.zeros(len(t)); k = 0
    while k < len(t):
        y[k:k + hold[k]] = n[k]; k += hold[k]
    return crush(sfx.lp(y, 3) * np.sin(np.pi * t / d) ** 2, 4, 1) * .8


def chip_screech(d=.6):
    t = np.arange(int(SR * d)) / SR
    f = 1700 + 160 * np.sin(2 * np.pi * 23 * t) - 500 * t
    return crush(sq(f, d, .25) * np.minimum(1, t * 30) * np.exp(-t * 2.5), 4, 2) * .45


def audio(F, path):
    n = int(SR * NDRAW * 2 / FPS); mix = np.zeros(n)

    def put(sig, t, g=1.0):
        i = max(0, int(round(t * SR)))
        if i < n: seg = sig[:n - i]; mix[i:i + len(seg)] += seg * g
    tof = lambda d: 2 * d / FPS
    for k in F.contacts:
        op = F.story.index(min(F.story, key=lambda x: abs(x - k['peak'])))
        put(chip_whoosh(.16 if k['size'] < 1 else .22), op / FPS - .1, .5 + .2 * min(k['size'], 1.5))
        if not k['evade']:
            put(chip_thump(.22 if not k['finisher'] else .35), k['o'] / FPS, .8 + .3 * k['size'])
            put(chip_bass(.6 if k['finisher'] else .4, 45 if k['finisher'] else 55), k['o'] / FPS, .6 + .3 * k['size'])
    for o0, f, who, side in F.dust:
        put(crush(sfx.lp(np.random.default_rng(f).standard_normal(int(SR * .08)), 8) * np.hanning(int(SR * .08)), 4, 4), o0 / FPS, .25)
    t0 = NF_FIGHT / FPS
    put(sfx.boom(1.0), t0 - 2 / FPS, .8)                                        # flash cut
    put(chip_whoosh(.28, False), t0 + 24 / FPS - .05, 1.0)                     # whip pan
    put(crush(sq(70 + 40 * np.linspace(0, 1, int(SR * .5)), .5) * np.linspace(0, .4, int(SR * .5)), 4, 8), t0 + 20 / FPS, .5)
    put(chip_screech(.55), t0 + 40 / FPS, .9)                                   # cartoon brake
    put(chip_thump(.18), t0 + 62 / FPS, .5)
    put(F6.record_scratch(), t0 + 64 / FPS - .02, 1.0)                          # freeze
    fade = np.ones(n); fade[-int(SR * .02):] = np.linspace(1, 0, int(SR * .02)); mix *= fade
    g, ceil = 1.0 / np.abs(mix).max(), 10 ** (-2.0 / 20)
    for _ in range(10):
        y = np.tanh(mix * g / ceil) * ceil
        F6.hook.write_wav(path + '.tmp.wav', y)
        r = subprocess.run(['ffmpeg', '-nostats', '-i', path + '.tmp.wav', '-af', 'ebur128=peak=true', '-f', 'null', '-'],
                           capture_output=True, text=True).stderr
        Il = float(r.split('Integrated loudness:')[1].split('I:')[1].split('LUFS')[0])
        P = float(r.split('True peak:')[1].split('Peak:')[1].split('dBFS')[0])
        if abs(Il + 14) < 0.4 and P <= -1.0: break
        g *= 10 ** ((-14 - Il) / 20)
        if P > -1.0: ceil *= 10 ** ((-1.3 - P) / 20)
    os.remove(path + '.tmp.wav'); F6.hook.write_wav(path, y)
    return Il, P


# ---------------------------------------------------------------- report + main
def report(F):
    print('frames: fight %d (story %d + hit-stops), transition %d' % (NF_FIGHT, len(F.Wd['hero']), NF_TR))
    for k in F.contacts:
        print('beat %2d %-4s %-11s -> %-4s planned %3d speed-found %3d (peak %3d, %4.0f u/s) out %3d hitstop %d%s' % (
            k['beat'], k['att'], k['seg'].m.name, k['dfn'], k['c_planned'], k['c'], k['peak'], k['vpeak'], k['o'],
            k['hitstop'], ' EVADE' if k['evade'] else (' -> ' + k['rseg'].m.name if k.get('rseg') else '')))
    hit = set()
    for k in F.contacts: hit.update(range(k['c'] - 6, k['c'] + 8))
    gaps = [(abs(F.Wd['opp'][f][I['thorax'], 0] - F.Wd['hero'][f][I['thorax'], 0]), f) for f in range(len(F.Wd['hero'])) if f not in hit]
    print('min torso gap outside contacts: %.0f (body width ~110) at story %d' % min(gaps))
    sl = []
    for who in ('hero', 'opp'):
        A = F.Wd[who]
        for side in 'lr':
            an = A[:, I[side + 'tibia']]; v = np.linalg.norm(np.diff(an[:, [0, 2]], axis=0), axis=1)
            on = (an[1:, 1] < 50) & (v > 1.5) & ~F.slide[who][1:]
            sl.append(int(on.sum()))
    print('foot-sliding story frames (ankle down, >1.5 u/frame, not a slide move): hero %d/%d opp %d/%d' % tuple(sl))
    print('dark flash-cut frames:', [o for o in range(NF_FIGHT) if F.flash_on(o)])


def main():
    os.makedirs(OUT, exist_ok=True)
    F = Film(); report(F)
    if '--frames' in sys.argv:
        fr = list(map(int, sys.argv[sys.argv.index('--frames') + 1].split(',')))
        for o in range(max(fr) + 1):                              # cloth state is sequential: render in order
            img = F.frame(o)
            if o in fr: Image.fromarray(img).save(os.path.join(OUT, 'p6_%03d.png' % o))
        return
    wav = os.path.join(OUT, 'pixel-fight6-sfx.wav')
    Il, P = audio(F, wav); print('audio I=%.1f LUFS TP=%.1f dBTP' % (Il, P))
    mp4 = os.path.join(OUT, 'pixel-fight6.mp4')
    cmd = ['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '%dx%d' % (W * UP, H * UP),
           '-r', str(FPS), '-i', '-', '-i', wav, '-map', '0:v', '-map', '1:a', '-c:v', 'libx264', '-preset', 'slow',
           '-crf', '16', '-pix_fmt', 'yuv420p', '-vf', 'setsar=1', '-aspect', '9:16', '-c:a', 'aac', '-b:a', '256k',
           '-t', '6.000', '-movflags', '+faststart', mp4]
    pr = subprocess.Popen(cmd, stdin=subprocess.PIPE); cols = []
    os.makedirs(os.path.join(OUT, 'art'), exist_ok=True)
    for o in range(NDRAW * 2):
        img = F.frame(o)
        if o % 30 == 0:
            cols.append(len(np.unique(img.reshape(-1, 3), axis=0)))
            Image.fromarray(img).save(os.path.join(OUT, 'art', 'a%03d.png' % o))
        pr.stdin.write(upscale(img).tobytes())
    pr.stdin.close(); pr.wait()
    print('colours per frame (every 0.5 s):', cols, '->', mp4)


if __name__ == '__main__':
    main()
