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
from pixlook import (W, H, S0, GY0, PAL, INK, TEE, WHITE, YEL, FIRE, BAY, paint_layers, draw_world, dim,  # noqa: E402
                     draw_stick, shadow, fx_crescent, fx_streak, fx_spark, fx_dust, glow, draw_car)
import pixlook as PL  # noqa: E402


def to_screen(P, cam):
    cx, gy, s = cam
    Q = proj(P)
    return np.stack([(Q[:, 0] - cx) * s + W / 2, Q[:, 1] * s + gy, Q[:, 2]], -1), s


def draw_fighter(img, P, cam, hero, mask=None):
    S, s = to_screen(P, cam)
    return draw_stick(img, S, s, I, hero, mask)


def fshadow(img, P, cam):
    S, s = to_screen(P, cam)
    shadow(img, [S[I[k + 'tibia']][0] for k in 'lr'], cam[1], s)


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
TRD = NDRAW - 144                                             # transition drawings (1.2 s)


class Film:
    def __init__(s):
        s.sh, s.segs, s.contacts, s.Wd, s.draws, s.slide = build_motion()
        s.ND = len(s.draws)
        s.fin = [k for k in s.contacts if k['finisher']][0]
        s.layers = paint_layers(); s.roadl = paint_layers(road=True)
        s.camera(); s.dust_events()

    def pose(s, who, t):
        return s.Wd[who][int(min(max(t, 0), len(s.Wd[who]) - 1))]

    def camera(s):
        N = s.ND; hx = np.zeros(N); ox = np.zeros(N)
        for d, t in enumerate(s.draws):
            hx[d] = proj(s.pose('hero', t))[I['thorax'], 0]; ox[d] = proj(s.pose('opp', t))[I['thorax'], 0]
        fd = s.fin['d']; hs = s.fin['hitstop']
        wo = np.array([.5 if d < fd else .5 - .3 * ease((d - fd - hs) / 4, 'io') for d in range(N)])
        ox = np.where(np.arange(N) > fd + hs, np.minimum(ox, hx + 700), ox)          # don't chase the flying body
        cx = gaussian_filter1d(hx * (1 - wo) + ox * wo, 3, mode='nearest')
        u0 = np.clip(np.arange(N) / 22, 0, 1)
        cx += 70 * (1 - u0 * u0 * (3 - 2 * u0))                 # opening truck-in
        push = np.clip(np.arange(N) / (N - 1), 0, 1)
        sc = S0 * (1 + 0.07 * push)
        for k in s.contacts:                                   # gentle push-ins on the strikes
            if not k['finisher']:
                sc = sc * (1 + 0.05 * k['size'] * np.exp(-((np.arange(N) - k['d'] + 3) / 6) ** 2))
        sc = gaussian_filter1d(sc, 2, mode='nearest')
        gy = np.full(N, float(GY0)) + 10 * push
        # finisher: whip into a close-up on the impact over 3 drawings, hold the hit-stop, snap back out
        t = s.fin['c']; Ph = proj(s.pose('hero', t)); Po = proj(s.pose('opp', t))
        IP = (Ph[I[s.fin['eff']], :2] + proj(np.array([head_c(s.pose('opp', t))]))[0, :2]) / 2
        s.IP = IP
        close = (IP[0], 0.40)
        cams = []
        for d in range(N):
            c = (cx[d], gy[d], sc[d])
            tgt = (close[0], 250 - IP[1] * close[1], close[1])
            if fd - 3 <= d < fd:
                u = ease((d - fd + 3) / 3, 'in'); c = tuple(c[j] + (tgt[j] - c[j]) * u for j in range(3))
            elif fd <= d <= fd + hs:
                u = (d - fd) / max(hs, 1); c = (tgt[0], tgt[1] + 4 * u, tgt[2] * (1 + .03 * u))
            elif fd + hs < d <= fd + hs + 4:
                u = ease((d - fd - hs) / 4, 'snap'); a = cams[fd + hs]
                c = tuple(a[j] + (c[j] - a[j]) * u for j in range(3))
            cams.append(c)
        s.cams, s.push = cams, push

    def dust_events(s):
        ev = []; S = len(s.Wd['hero'])
        for who in ('hero', 'opp'):
            A = s.Wd[who]; last = -99
            for side in 'lr':
                y = A[:, I[side + 'tibia'], 1]
                vy = np.r_[0, np.diff(y)] * FPS
                for f in range(2, S):
                    if y[f - 2] > 75 and y[f] <= 62 and vy[f - 1] < -250 and f - last > 30:
                        ev.append((f, who, side)); last = f
            for sg in s.segs[who]:
                if sg.slide and sg.start < S and sg.start - last > 8:
                    ev.append((int(sg.start) + 2, who, 'l')); last = sg.start
        s.dust = sorted(ev)

    # -------------------------------------------------------------- fight drawing
    def dim_level(s, d):
        """Backdrop dims around the big hits (fire contacts): ramps in over 2 drawings, out over 3;
        gaps under 12 drawings between two dimmed hits stay dark (no light/dark flicker)."""
        if not hasattr(s, '_dim'):
            raw = [s._dim_raw(x) for x in range(s.ND)]
            on = [i for i, v in enumerate(raw) if v >= 1]
            for i, j in zip(on, on[1:]):
                if 1 < j - i < 12: raw[i:j] = [1.0] * (j - i)
            s._dim = raw
        return s._dim[d]

    def _dim_raw(s, d):
        k = 0.0
        for c in s.contacts:
            if c['fx'] != 'fire' or c['evade']: continue
            a, b = c['d'] - (4 if c['finisher'] else 1), c['d'] + c['hitstop'] + 6
            if a <= d <= b: k = max(k, min(1.0, (d - a + 1) / 2, (b - d + 1) / 3))
        return k

    def fight(s, d):
        t = s.draws[d]; cx, gy, sc = s.cams[d]; cam = (cx, gy, sc)
        img = np.zeros((H, W), np.uint8)
        draw_world(img, s.layers, cx, gy, s.push[d])
        dim(img, s.dim_level(d))
        Ph, Po = s.pose('hero', t), s.pose('opp', t)
        fshadow(img, Po, cam); fshadow(img, Ph, cam)
        z = sc / S0
        for k in s.contacts:                                   # glow behind the figures on fire hits
            e = (d - k['d']) // 2
            if not k['evade'] and k['fx'] == 'fire' and 0 <= e < 2:
                P = to_screen(s.Wd[k['att']][k['c']], cam)[0][I[k['eff']], :2]
                glow(img, P, (60 if k['finisher'] else 40) * z, 1 - .4 * e)
        draw_fighter(img, Po, cam, False)
        draw_fighter(img, Ph, cam, True)
        pil = Image.fromarray(img); dr = ImageDraw.Draw(pil)
        for k in s.contacts:                                   # crescent slashes: 3 frames on 2s from 2 drawings before contact
            e = (d - (k['d'] - 2)) // 2
            if 0 <= e < 3:
                A = s.Wd[k['att']]; f1 = min(t + 2, k['c'] + 3); f0 = max(0, k['c'] - 16)
                pts = [to_screen(A[f], cam)[0][I[k['eff']], :2] for f in range(f0, f1 + 1)]
                root = to_screen(A[k['c']], cam)[0][0, :2]
                fx_crescent(dr, pts, e, z * (0.7 if k['evade'] else 1.0), np.mean(pts, 0) - root)
        for k in s.contacts:                                   # sparks / fire streaks on the contact
            if k['evade']: continue
            e = (d - k['d']) // 2; P = to_screen(s.Wd[k['att']][k['c']], cam)[0][I[k['eff']], :2]
            if k['fx'] == 'fire':
                if 0 <= e < 4: fx_streak(dr, P, e, z * k['size'] ** .4, D[k['att']], k['beat'], k['finisher'])
            elif 0 <= e < 4:
                fx_spark(dr, P, e, z * k['size'] ** .5, D[k['att']], k['beat'])
        for f, who, side in s.dust:                            # dust puffs on landings
            d0 = s.draws.index(min(s.draws, key=lambda x: abs(x - f)))
            e = (d - d0) // 2
            if 0 <= e < 3:
                Pp = to_screen(s.Wd[who][min(f, len(s.Wd[who]) - 1)], cam)[0][I[side + 'tibia']]
                fx_dust(dr, (Pp[0], gy), e, z, D[who])
        return np.array(pil)

    def flash(s, img, kind):
        """Finisher flash = the cut: one white frame, one dark frame; figures as hard silhouettes."""
        t = s.draws[-1]; cam = s.cams[-1]
        m = np.zeros((H, W), bool); tmp = img.copy()
        draw_fighter(tmp, s.pose('hero', t), cam, True, m); draw_fighter(tmp, s.pose('opp', t), cam, False, m)
        out = np.full((H, W), WHITE if kind == 0 else INK, np.uint8)
        if kind == 0: out[BAY < 4] = YEL
        out[m] = INK if kind == 0 else FIRE
        return out

    # -------------------------------------------------------------- transition
    def tr_hero(s, i):
        rd = mv('ready'); t = (i / FPS) % (2 * rd.dur); t = 2 * rd.dur - t if t > rd.dur else t
        P = sample(rd, t, False).copy(); P[:, [0, 2]] -= P[0, [0, 2]]
        return P

    def face(s, i):
        return PL.face(i)

    def car_x(s, i):
        """World x of the car's front bumper; enters at speed, cartoon-brakes to a stop beside the hero."""
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

    def road(s, i, cx, cam_s, gy, beam=True):
        img = np.zeros((H, W), np.uint8)
        draw_world(img, s.roadl, cx, gy, 0)
        dim(img, 1.0); dim(img, 1.0)                           # night: the dark flash carries into the road
        cam = (cx, gy, cam_s)
        X = lambda wx: (wx - cx) * cam_s + W / 2
        x0 = s.car_x(i); p = s.car_pitch(i)
        if i > 40:                                             # skid marks
            a, b = X(s.car_x(40)), X(x0)
            for off in (160, 640):
                img[int(gy) + 1:int(gy) + 3, int(max(0, b + off * cam_s)):int(max(0, min(W, a + off * cam_s)))] = INK
        Ph = s.tr_hero(i)
        m = np.zeros((H, W), bool)
        dist = max(0.0, 1 - (x0 - 240) / 1800)
        if beam:                                               # headlight cone, dithered, toward the hero
            yy, xx = np.mgrid[0:H, 0:W]
            hx, hy = X(x0 + 30), gy - 180 * cam_s - 120 * math.sin(p) * cam_s
            dxp = hx - xx; spread = np.abs(yy - hy) < 6 + dxp * .3
            inten = np.clip(1 - dxp / 280, 0, 1) * (dxp > 0) * spread * 10 * (0.5 + 0.5 * dist)
            img[(inten > BAY) & (yy < gy + 40)] = YEL
            img[(inten > BAY + 6) & (yy < gy + 40)] = WHITE
        draw_fighter(img, Ph, cam, True, m)
        if beam:
            rim = m & ~np.roll(m, -1, 1) & (BAY < 16 * dist)  # headlight rim on the hero
            img[rim] = YEL
        draw_car(img, x0, p, cam)
        return img

    def transition(s, j):
        """j = transition drawing 0..35: face close-up (0-11), whip pan (12-16), brake (17-35)."""
        i = 2 * j
        if j < 12:
            return s.face(j)
        cs, gy = 0.225, 452.0
        rest = (W / 2 - 45) / cs
        if j < 17:                                             # whip pan along the road toward the car
            u = ease((j - 11) / 6, 'out')
            cx = (-1400 + (rest + 1400) * u)
            img = s.road(i, cx, cs, gy, beam=False)
            sm = img.copy(); step = 14 - 2 * (j - 12)          # horizontal pixel smear in the pan direction
            for x in range(W):
                sm[:, x] = img[:, (x // step) * step]
            return sm
        return s.road(i, rest, cs, gy)

    def drawing(s, d):
        return s.fight(d) if d < s.ND else s.transition(min(d - s.ND, TRD - 4))   # last 4 drawings: freeze

    def frame(s, o, cache):
        d = o // 2
        if d not in cache:
            cache.clear(); cache[d] = s.drawing(d)
        img = cache[d]
        if d == s.ND - 1:                                      # finisher flash = the cut (2 output frames)
            img = s.flash(img, o % 2)
        return img


def upscale(idx):
    return PAL[np.repeat(np.repeat(idx, UP, 0), UP, 1)]


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
        dp = F.draws.index(min(F.draws, key=lambda x: abs(x - k['peak'])))
        put(chip_whoosh(.16 if k['size'] < 1 else .22), tof(dp) - .1, .5 + .2 * min(k['size'], 1.5))
        if not k['evade']:
            put(chip_thump(.22 if not k['finisher'] else .35), tof(k['d']), .8 + .3 * k['size'])
            put(chip_bass(.6 if k['finisher'] else .4, 45 if k['finisher'] else 55), tof(k['d']), .6 + .3 * k['size'])
    for f, who, side in F.dust:
        d0 = F.draws.index(min(F.draws, key=lambda x: abs(x - f)))
        put(crush(sfx.lp(np.random.default_rng(f).standard_normal(int(SR * .08)), 8) * np.hanning(int(SR * .08)), 4, 4), tof(d0), .25)
    t0 = tof(F.ND)
    put(sfx.boom(1.0), t0 - 2 / FPS, .8)                                        # flash cut
    put(chip_whoosh(.28, False), t0 + tof(12) - .05, 1.0)                      # whip pan
    put(crush(sq(70 + 40 * np.linspace(0, 1, int(SR * .5)), .5) * np.linspace(0, .4, int(SR * .5)), 4, 8), t0 + tof(10), .5)
    put(chip_screech(.55), t0 + 40 / FPS, .9)                                   # cartoon brake
    put(chip_thump(.18), t0 + 62 / FPS, .5)
    put(F6.record_scratch(), tof(NDRAW - 4) - .02, 1.0)                          # freeze
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
    print('drawings: fight %d (story %d), transition %d; output frames %d' % (F.ND, len(F.Wd['hero']), TRD, NDRAW * 2))
    for k in F.contacts:
        print('beat %2d %-4s %-11s -> %-4s planned %3d speed-found %3d (peak %3d, %4.0f u/s) out %3d hitstop %d%s' % (
            k['beat'], k['att'], k['seg'].m.name, k['dfn'], k['c_planned'], k['c'], k['peak'], k['vpeak'], 2 * k['d'],
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
    fs = [d for d in range(F.ND) if any(abs(d - k['d']) < 1 for k in F.contacts)]
    print('flash output frames:', [2 * F.ND - 2, 2 * F.ND - 1])


def main():
    os.makedirs(OUT, exist_ok=True)
    F = Film(); report(F)
    pal = np.zeros(256, bool)
    if '--drawings' in sys.argv:
        for d in map(int, sys.argv[sys.argv.index('--drawings') + 1].split(',')):
            Image.fromarray(upscale(F.drawing(d))).resize((270 * 2, 480 * 2), Image.NEAREST).save(os.path.join(OUT, 'p6_%03d.png' % d))
        return
    wav = os.path.join(OUT, 'pixel-fight6-sfx.wav')
    Il, P = audio(F, wav); print('audio I=%.1f LUFS TP=%.1f dBTP' % (Il, P))
    mp4 = os.path.join(OUT, 'pixel-fight6.mp4')
    cmd = ['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '%dx%d' % (W * UP, H * UP),
           '-r', str(FPS), '-i', '-', '-i', wav, '-map', '0:v', '-map', '1:a', '-c:v', 'libx264', '-preset', 'slow',
           '-crf', '16', '-pix_fmt', 'yuv420p', '-vf', 'setsar=1', '-aspect', '9:16', '-c:a', 'aac', '-b:a', '256k',
           '-t', '6.000', '-movflags', '+faststart', mp4]
    pr = subprocess.Popen(cmd, stdin=subprocess.PIPE); cache = {}
    for o in range(NDRAW * 2):
        idx = F.frame(o, cache); pal[np.unique(idx)] = True
        pr.stdin.write(upscale(idx).tobytes())
    pr.stdin.close(); pr.wait()
    print('palette colours used: %d ->' % pal.sum(), mp4)


if __name__ == '__main__':
    main()
