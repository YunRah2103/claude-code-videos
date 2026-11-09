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
UP, FPS = 6, 60
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


MAXT = dict(jab=60, cross=90, hook=90, roundhouse=140, knee=140, lunge_punch=220, step_in=150, step_back=150,
            slip=60, duck=60, block=60, ready=30, knock_back=420, stagger=170)


def clamp_drift(m, M):
    """Clamp a mocap move's forward/back root travel to M (world units); feet are re-planted later."""
    rx = m.Q[:, 0, 0] - m.Q[0, 0, 0]; peak = float(np.abs(rx).max())
    if peak > M:
        m.Q[:, :, 0] -= (rx * (1 - M / peak))[:, None]
    return peak


def build_motion():
    import authored
    F6.LIBRARY.update(authored.library())
    for n, M in MAXT.items():
        m = F6.mv(n)
        if not getattr(m, 'clamped', False):
            m.clamped = True; m.travel = (clamp_drift(m, M), M)
    sh, segs, contacts = F6.load_sheet()
    S, X = sh['fight_story_frames'], sh['crossfade']
    fx = {b['n']: b['contact'].get('fx', 'spark') for b in sh['beats'] if b.get('contact')}
    wp = {b['n']: b['contact'].get('weapon', False) for b in sh['beats'] if b.get('contact')}
    for k in contacts: k['fx'] = fx[k['beat']]; k['weapon'] = wp[k['beat']]
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
TRD = NDRAW - 144
NF_FIGHT, NF_TR = 288, 72
import handfight as HF  # noqa: E402
FIG = HF.FIG                                                  # compact stickman height in world units (to head top)
SHOTS = {'wide': (0.27, 1.0, .885), 'medium': (0.40, 1.6, .95), 'close': (0.56, 2.4, None)}   # height frac, world zoom, feet row
BLADE = HF.BLADE


def scale_of(kind):
    return SHOTS[kind][0] * H / FIG


def scr(P, cx, gy, s):
    """World pose -> whole-pixel screen coords + depth; camera offset rounded once (no crawl)."""
    Q = proj(P)
    return np.stack([np.round(Q[:, 0] * s) - round(cx * s) + W // 2, np.round(Q[:, 1] * s) + gy, Q[:, 2]], -1)


def scr_pts(Pxy, cx, gy, s):
    P = np.asarray(Pxy, float)
    return np.stack([np.round(P[:, 0] * s) - round(cx * s) + W // 2, np.round(P[:, 1] * s) + gy], -1)


def anchor(P, a, b, u=.5):
    Q = proj(P)
    return Q[I[a], :2] + (Q[I[b], :2] - Q[I[a], :2]) * u


def blade_tip(P):
    Q = proj(P); h, r = Q[I['rhand'], :2], Q[I['rradius'], :2]
    v = (h - r) / max(np.linalg.norm(h - r), 1e-6)
    return h, h + v * BLADE


class Film:
    def __init__(s):
        s.Wd, s.contacts, s.weapon_on, s.tracks = HF.build()    # hand-keyed animation, hit-stops baked in as holds
        s.story = list(range(NF_FIGHT))
        s.B = {k['beat']: k for k in s.contacts}
        s.fin = [k for k in s.contacts if k['finisher']][0]
        s.on1 = np.zeros(NF_FIGHT, bool)                       # mixed timing: on 1s around strikes, on 2s otherwise
        for k in s.contacts:
            s.on1[max(0, k['c'] - 7):min(NF_FIGHT, k['c'] + 2 * k['hitstop'] + 7)] = True
        for r in HF.RAGDOLLS:
            s.on1[r['start']:min(NF_FIGHT, r['end'] + 4)] = True
        s.worlds = {k: RS.paint_world(kind='day', zoom=v[1]) for k, v in SHOTS.items()}
        s.dusk = {'wide': RS.paint_world(kind='dusk', zoom=1.0), 'close': RS.paint_world(kind='dusk', zoom=2.4)}
        s.camera(); s.dust_events(); s.cloth()

    def pose(s, who, t):
        return s.Wd[who][int(min(max(t, 0), len(s.Wd[who]) - 1))]

    # -------------------------------------------------------------- shots + camera (whole pixels)
    def camera(s):
        N = NF_FIGHT; o = lambda b: s.B[b]['o']
        hs10 = 2 * s.fin['hitstop']
        s.shots = list(HF.SHOTPLAN) + [(N, None)]
        hx = np.array([proj(s.pose('hero', t))[I['thorax'], 0] for t in s.story])
        ox = np.array([proj(s.pose('opp', t))[I['thorax'], 0] for t in s.story])
        of = o(10)
        ox = np.where(np.arange(N) > of + hs10, np.minimum(ox, hx + 400), ox)
        mid = (hx + ox) / 2
        t = s.fin['c']; Ph = proj(s.pose('hero', t))
        IP = (blade_tip(s.pose('hero', t))[1] + proj(np.array([head_c(s.pose('opp', t))]))[0, :2]) / 2
        s.cams = [None] * N; s.shot_of = [None] * N
        for (a, kind), (b, _) in zip(s.shots[:-1], s.shots[1:]):
            fr = np.arange(a, b)
            sc_k = scale_of(kind) if kind else 1; dz = W * .22 / sc_k   # camera operator: dead zone, then a quick reframe
            cx = np.zeros(b - a); c_ = mid[a]; moving = False
            for i in range(b - a):
                err = mid[a + i] - c_
                if abs(err) > dz: moving = True
                if moving:
                    c_ += err * .35
                    if abs(err) < dz * .25: moving = False
                cx[i] = c_
            sc0 = scale_of(kind)
            for i, f in enumerate(fr):
                sc = sc0; tilt = 0.0; smear = 0
                if kind == 'close':
                    sc = sc0 * (1 + .04 * min(1, (f - a) / 20))
                    hp_ = proj(s.pose('hero', s.story[f]))[I['thorax'], 0]; op_ = proj(s.pose('opp', s.story[f]))[I['thorax'], 0]
                    c = (hp_ + op_) / 2 if abs(op_ - hp_) * sc < W * .8 else IP[0]
                    gy = int(round(H * .42 - IP[1] * sc))
                    if f - a < 5:                               # whip into the close-up
                        u = ease((f - a + 1) / 5, 'in'); pc = s.cams[a - 1]
                        c = pc[0] + (c - pc[0]) * u; smear = 6 - (f - a)
                else:
                    c = cx[i]; gy = int(round(H * SHOTS[kind][2]))
                    if a == 0:                                  # opening: truck-in and push-in
                        u = min(1, f / 24); u = u * u * (3 - 2 * u)
                        c += 260 * (1 - u); sc *= .9 + .1 * u
                for k in s.contacts:
                    if k['evade'] and k['beat'] != 5: continue
                    dd = f - k['o']
                    if not k['evade'] and 0 <= dd < 2 * k['hitstop'] + 3: sc *= 1.04          # punch-in on the hit
                    if k.get('tilt'):                                                     # low tilt on the kicks / leap
                        tilt = max(tilt, 16 * math.exp(-(dd / 16) ** 2) * H / 320)
                s.cams[f] = (c, gy + int(round(tilt * .5)), sc, kind, tilt, smear); s.shot_of[f] = kind
        for k in s.contacts:                                    # whole-pixel shake on hits
            if k['evade']: continue
            amp = 2 if k['size'] >= 1 else 1
            for j, (dx, dy) in enumerate(((amp, -amp), (-amp, amp), (amp, 0), (-1, 1), (1, 0))):
                f = k['o'] + j
                if f < N:
                    c = s.cams[f]; s.cams[f] = (c[0] + dx / c[2], c[1] + dy) + c[2:]

    def dust_events(s):
        ev = []; S = len(s.Wd['hero'])
        for who in ('hero', 'opp'):
            A = s.Wd[who]; last = -99
            for side in 'lr':
                y = A[:, I[side + 'tibia'], 1]; vy = np.r_[0, np.diff(y)] * FPS
                for f in range(2, S):
                    if y[f - 2] > 75 and y[f] <= 62 and vy[f - 1] < -250 and f - last > 24:
                        ev.append((f, who, side)); last = f
        ev += [(f, who, 'l') for f, who in HF.DUST]                                         # dash, landings
        s.dust = [(s.story.index(min(s.story, key=lambda x: abs(x - f))), f, who, side) for f, who, side in sorted(ev)]

    def cloth(s):
        cape, scarf, hair = RS.Chain(6, 46, grav=5200, damp=.86), RS.Chain(4, 32, grav=4200, back=.8), RS.Chain(3, 26, grav=3000, back=.6)
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

    # -------------------------------------------------------------- drawing
    def figure(s, img, P, Pprev, cloth_pts, hair_pts, cx, gy, sc, hero, mask=None, blade=False, flash=False):
        S = scr(P, cx, gy, sc)
        lim = max(2, int(round(FIG * sc / 55)))
        prev = scr(Pprev, cx, gy, sc) if Pprev is not None else None
        cl = scr_pts(cloth_pts, cx, gy, sc) if cloth_pts is not None else None
        bl = None
        if hero and blade:
            h, tip = blade_tip(P); bl = scr_pts([h, tip], cx, gy, sc)
        hc, hr = RS.draw_figure(img, S, I, hero, cl, mask, lim, prev, bl, hr=HF.HEAD_R * sc, flash=flash)
        if False:
            Hp = scr_pts(hair_pts, cx, gy, sc); Hp[0] = hc + np.array([-.8 * hr, -.2 * hr])
            for i in range(1, len(Hp)): RS.pline(img, Hp[i - 1], Hp[i], max(1, lim - 1), RS.HAIR, mask)
        return S

    def flash_on(s, o):
        if o >= NF_FIGHT - 2: return True
        for k in s.contacts:
            if not k['evade'] and k['fx'] == 'fire' and k['o'] <= o < k['o'] + (16 if k['finisher'] else 12):
                return True
        return False

    def fight(s, o):
        t0 = s.story[o]; cx, gy, sc, kind, tilt, smear = s.cams[o]
        hold = 2 if s.on1[t0] else 5                            # action on 30 drawings/s, calm on 12 (hand-drawn rhythm)
        t = t0 - (t0 % hold); oc = o - (o % hold)
        wd = s.worlds[kind]; s_nom = scale_of(kind)
        img = RS.compose(wd, round(cx * s_nom), gy - int(round(H * .885)), tilt, smear)
        if s.flash_on(o): img = RS.dark_grade(img)
        tp = t - hold if t >= hold else t
        Po, Ph = s.pose('opp', t), s.pose('hero', t)
        Pop, Php = (s.pose('opp', tp), s.pose('hero', tp)) if tp != t else (None, None)
        fl = {k['dfn'] for k in s.contacts if not k['evade'] and k['o'] <= o < k['o'] + 2}   # white hit flash (2 frames)
        if s.flash_on(o) and not s.flash_on(o - 1): fl = {'hero', 'opp'}                    # impact frame: white silhouettes
        for k in s.contacts:                                    # smear multiples on the striking limb
            if k['evade'] or not (k['o'] - 5 <= o < k['o']): continue
            A = s.Wd[k['att']]; side = 'l' if k['eff'] in ('lhand', 'ltoes') else 'r'
            jn = ('humerus', 'hand') if 'hand' in k['eff'] or k['eff'] == 'blade' else ('femur', 'tibia')
            segs = [tuple(scr(A[max(0, t - g)], cx, gy, sc)[[I[side + jn[0]], I[side + jn[1]]], :2]) for g in (4, 2, 0)]
            RS.fx_smear(img, segs, RS.BODY[k['att'] == 'hero'][1], max(2, int(round(FIG * sc / 55))))
        z = sc / scale_of('wide')
        for k in s.contacts:                                    # speed trail along the striking fist / foot
            if k['evade'] or k.get('weapon') or not (k['o'] - 5 <= o <= k['o'] + 1): continue
            A = s.Wd[k['att']]
            pts = [scr(A[f], cx, gy, sc)[I[k['eff']], :2] for f in range(max(0, min(t, k['c']) - 6), min(t, k['c']) + 1)]
            RS.fx_trail(img, pts, 3 * z)
        s.figure(img, Po, Pop, s.cape[oc], None, cx, gy, sc, False, flash='opp' in fl)
        s.figure(img, Ph, Php, s.scarf[oc], s.hair[oc], cx, gy, sc, True, blade=bool(s.weapon_on[t]), flash='hero' in fl)
        for k in s.contacts:                                    # impact star + shock lines on every landed hit
            if k['evade']: continue
            age = o - k['o']
            if 0 <= age < 10:
                A = s.Wd[k['att']][k['c']]
                P = scr_pts([blade_tip(A)[1]], cx, gy, sc)[0] if k.get('weapon') else scr(A, cx, gy, sc)[I[k['eff']], :2]
                RS.fx_impact(img, P, age, z * k['size'] ** .3, D[k['att']])
                hd = scr_pts([HF.head_center(s.Wd[k['dfn']][min(t, NF_FIGHT - 1)])], cx, gy, sc)[0]
                RS.fx_shock(img, hd, age - 2 * k['hitstop'], z, D[k['att']])
        for k in s.contacts:                                    # crescent slashes along the blade tip or limb tip
            age = o - (k['o'] - 4)
            if not 0 <= age < 14: continue
            A = s.Wd[k['att']]; rng_f = range(max(0, k['c'] - 10), min(len(A), k['c'] + 3))
            if k.get('weapon'):
                pts = scr_pts([blade_tip(A[f])[1] for f in rng_f], cx, gy, sc); maxlen = BLADE * sc
            else:
                pts = np.array([scr(A[f], cx, gy, sc)[I[k['eff']], :2] for f in rng_f]); maxlen = 190 * sc
            root = scr(A[k['c']], cx, gy, sc)[0, :2]
            tg = np.gradient(pts.astype(float), axis=0); nrm = np.stack([-tg[:, 1], tg[:, 0]], 1)
            side = 1.0 if ((pts - root) * nrm).sum() > 0 else -1.0
            RS.fx_slash(img, pts, age, 14, side, z * (.6 if k['evade'] else 1.0), red=(k['fx'] == 'fire' and not k['evade']), maxlen=maxlen)
        for k in s.contacts:                                    # soft fire / sparks with glowing embers
            if k['evade']: continue
            age = o - k['o']
            if 0 <= age < 22:
                A = s.Wd[k['att']][k['c']]
                P = scr_pts([blade_tip(A)[1]], cx, gy, sc)[0] if k.get('weapon') else scr(A, cx, gy, sc)[I[k['eff']], :2]
                if k['fx'] == 'fire': RS.fx_fire(img, P, age, z * k['size'] ** .4 * 1.5, D[k['att']], k['beat'] * 31, k['finisher'])
                else: RS.fx_spark(img, P, age, z * k['size'] ** .4, D[k['att']], k['beat'] * 31)
        for o0, f, who, side in s.dust:
            age = o - o0
            if 0 <= age < 12:
                Pp = scr(s.Wd[who][min(f, len(s.Wd[who]) - 1)], cx, gy, sc)[I[side + 'tibia']]
                RS.fx_dust(img, (Pp[0], gy), age, z, D[who])
        return img

    # -------------------------------------------------------------- transition
    def tr_hero(s, i):
        return HF.stance_bob(i)

    def car_x(s, i):
        v, i0, i1, stop = 2600 / FPS, 40, 62, 190.0
        brake = v * (i1 - i0) / 2
        if i <= i0: return stop + brake + v * (i0 - i)
        if i <= i1: u = (i - i0) / (i1 - i0); return stop + brake * (1 - u) ** 2
        return stop

    def car_pitch(s, i):
        if i < 40: return 0.0
        if i <= 62: return math.radians(7) * ease((i - 40) / 6, 'out')
        t = (i - 62) / FPS
        return math.radians(7) * math.exp(-t * 9) * math.cos(t * 26)

    def road(s, i, cx, sc, gy, beam=True, smear=0):
        img = RS.compose(s.dusk['wide'], round(cx * scale_of('wide')), gy - int(round(H * .885)), 0, smear)
        x0 = s.car_x(i); p = s.car_pitch(i)
        csc = .4 * H / 620 * .62                                # cartoon car, fixed size next to the stickman
        x0 = x0 + cx - (cx * sc - (.6 * W - W // 2)) / csc     # car stops with its bumper just right of the hero
        X = lambda wx: int(round(wx * csc)) - round(cx * csc) + W // 2
        if i > 40:
            for off in (160, 640):
                a, b = X(x0 - s.car_x(i) + s.car_x(40) + off), X(x0 + off)
                img[gy:gy + 2, max(0, b):max(0, min(W, a))] = (22, 20, 26)
        dist = max(0.0, 1 - (s.car_x(i) - 190) / 1800)
        hl = (X(x0 + 36), int(round(-180 * csc)) + gy)
        if beam:                                                # headlight pool, soft and clumped
            for k in range(5):
                RS.soft_glow(img, (hl[0] - (20 + 30 * k) * H / 320, hl[1] + 6 * k), (26 + 10 * k) * H / 320 * (.6 + .4 * dist),
                             (255, 226, 160), .16, 13 + k, levels=3)
        P = s.tr_hero(i)
        m = np.zeros((H, W), bool)
        sp = s.tr_scarf.step(anchor(P, 'lowerneck', 'upperneck', .2), 1)
        hp = s.tr_hair.step(anchor(P, 'upperneck', 'head', 1.0) + [-40, 10], 1)
        s.figure(img, P, None, sp, hp, cx, gy, sc, True, m)
        if beam and dist > .2: img[m & ~np.roll(m, -1, 1)] = (255, 220, 160)
        RS.draw_car(img, x0, p, round(cx * csc), csc, gy)
        return img

    def transition(s, j):
        """j = 0..71: face close-up (0-23), whip pan along the road (24-33), cartoon brake + freeze (34-71)."""
        sc, gy = .4 * H / FIG, int(round(H * .885))
        rest = (W / 2 - .2 * W) / sc
        if j < 24:
            if not hasattr(s, '_facebg'):
                s._facebg = RS.compose(s.dusk['close'], 0, int(H * .1))
            return RS.face(j, s._facebg)
        if j < 34:
            u = ease((j - 23) / 11, 'out')
            return s.road(j, -1800 + (rest + 1800) * u, sc, gy, beam=False, smear=max(1, 7 - (j - 24) // 2))
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
        if abs(Il + 14) < 0.4 and P <= -2.3: break
        g *= 10 ** ((-14 - Il) / 20)
        if P > -2.3: ceil *= 10 ** ((-2.6 - P) / 20)
    os.remove(path + '.tmp.wav'); F6.hook.write_wav(path, y)
    return Il, P


# ---------------------------------------------------------------- report + main
def report(F):
    print('frames: fight %d (hand-keyed, hit-stops held), transition %d' % (NF_FIGHT, NF_TR))
    for k in F.contacts:
        A, Dd = F.Wd[k['att']][k['c']], F.Wd[k['dfn']][k['c']]
        e = HF.point(A, k['eff']); t = HF.point(Dd, k['target'])
        print('beat %2d f%3d %-4s %-6s -> %-5s hitstop %d  miss %4.0f u  %s' % (k['beat'], k['c'], k['att'], k['eff'], k['target'],
              k['hitstop'], np.linalg.norm(e - t), k['label']))
    print('reach solve shifts:', {w: [(k['f'], round(sh)) for k, sh in zip(t.keys, t.shift) if abs(sh) > .5] for w, t in F.tracks.items()})
    gap = np.array([abs(F.Wd['opp'][f][I['thorax'], 0] - F.Wd['hero'][f][I['thorax'], 0]) for f in range(NF_FIGHT)])
    near = np.zeros(NF_FIGHT, bool)
    for k in F.contacts: near[max(0, k['c'] - 6):k['c'] + 10] = True
    bad = (gap < 110) & ~near; runs = []; f = 0
    while f < NF_FIGHT:
        if bad[f]:
            e = f
            while e < NF_FIGHT and bad[e]: e += 1
            if e - f > 3: runs.append((f, e))
            f = e
        else: f += 1
    print('overlap runs > 3 frames (torso gap < 110, outside contacts):', runs or 'none')
    print('dark flash-cut frames:', [o for o in range(NF_FIGHT) if F.flash_on(o)])
    rows = []
    for (a, kind), (b, _) in zip(F.shots[:-1], F.shots[1:]):
        rows.append('%s %.2f-%.2fs fighters %.0f%%' % (kind, a / FPS, b / FPS, 100 * np.median([FIG * F.cams[o][2] / H for o in range(a, b)])))
    print('shots:', '; '.join(rows))


def main():
    global W, H, UP
    os.makedirs(OUT, exist_ok=True)
    if '--res' in sys.argv:                                       # e.g. --res 270x480x4 (resolution test)
        W, H, UP = map(int, sys.argv[sys.argv.index('--res') + 1].split('x')); RS.set_res(W, H)
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
