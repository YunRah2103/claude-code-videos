"""6-second fight + headlights transition test, composed from the mocap move library.

Pipeline: choreography sheet (fight6_choreo.json) -> segments of library moves per fighter
(key-aligned, speed-scaled, mirrored) -> composition with 6-frame cross-fades (bone-direction blending,
root motion preserved and chained) -> stage solve (attacker nudged so the strike reaches) -> foot-plant
cleanup -> anticipation lean, contact IK, head look-at -> hit-stops -> camera -> flat 2D render ->
transition (flash = cut, headlights on the hero's face, whip pan, cartoon brake, freeze-frame).
Usage: python fight6.py [--frames 0,60,...]
"""
import json, math, os, subprocess, sys
import numpy as np, cairo, cv2
from scipy.ndimage import gaussian_filter1d

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '../../..'))
LIB = os.path.join(ROOT, 'shared/assets/mocapmoves')
sys.path.insert(0, HERE); sys.path.insert(0, LIB); sys.path.insert(0, os.path.join(ROOT, 'videos/new-car-trap/src'))
import hook, mocap_hook as MH, sfx  # noqa: E402
from build import blen  # noqa: E402
from hook import C, blob, over, surf_to_np, layer_matrix, make_layers, draw_ground, SC, ease  # noqa: E402

W, H, FPS = 1080, 1920, 60
OUT = hook.OUT
SHEET = os.path.join(HERE, '../fight6_choreo.json')
THETA = math.radians(22)
R_HEAD = 62
MOON = (-330, -760, 150)          # high and left: never behind the fighters' heads


# ---------------------------------------------------------------- library
class Move:
    def __init__(s, name):
        z = np.load(os.path.join(LIB, name + '.npz'))
        s.name, s.Q = name, z['Q'].astype(float)
        s.key, s.dur, s.kind, s.eff = float(z['key']), float(z['dur']), str(z['kind']), str(z['effector'])
        s.names, s.par = [str(n) for n in z['names']], [int(p) for p in z['parents']]


LIBRARY = {}
def mv(name):
    if name not in LIBRARY:
        LIBRARY[name] = Move(name)
    return LIBRARY[name]


NAMES, PAR = mv('ready').names, mv('ready').par
I = {n: i for i, n in enumerate(NAMES)}
J = len(NAMES)
def _mate(n):
    return ('r' if n[0] == 'l' else 'l') + n[1:]


PERM = [I[_mate(n)] if n[0] in 'lr' and _mate(n) in I else i for i, n in enumerate(NAMES)]


def descendants(j):
    out, todo = [], [j]
    while todo:
        a = todo.pop()
        for k in range(J):
            if PAR[k] == a:
                out.append(k); todo.append(k)
    return out


DESC = {j: descendants(j) for j in range(J)}
LEN = [0.0] + [blen(NAMES[j]) for j in range(1, J)]


def sample(m, t, mirror):
    x = min(max(t * 120, 0), len(m.Q) - 1.001); i = int(x); u = x - i
    P = m.Q[i] * (1 - u) + m.Q[i + 1] * u
    if mirror:
        P = P[PERM].copy(); P[:, 2] *= -1
    return P


def blend(A, B, w):
    """Blend two poses on bone directions (global joint rotations); root lerped; bone lengths kept."""
    if w <= 0: return A
    if w >= 1: return B
    out = np.zeros_like(A); out[0] = A[0] * (1 - w) + B[0] * w
    for j in range(1, J):
        d = (A[j] - A[PAR[j]]) * (1 - w) + (B[j] - B[PAR[j]]) * w
        n = np.linalg.norm(d)
        out[j] = out[PAR[j]] + (d / n * LEN[j] if n > 1e-6 else 0)
    return out


# ---------------------------------------------------------------- choreography -> segments
class Seg:
    def __init__(s, move, start, speed=1.0, mirror=False, loop=False, slide=False, fly=False, dx=0.0):
        s.m, s.start, s.speed, s.mirror, s.loop, s.slide, s.fly, s.dx = mv(move), start, speed, mirror, loop, slide, fly, dx
        s.A = None; s.L0 = None; s.dx_end = None

    @property
    def end(s):
        return s.start + s.m.dur * FPS / s.speed

    def local(s, f):
        t = (f - s.start) / FPS * s.speed
        if s.loop:  # ping-pong the stance so it never freezes
            d = s.m.dur; t = t % (2 * d); t = 2 * d - t if t > d else t
        return sample(s.m, t, s.mirror)


def load_sheet():
    sh = json.load(open(SHEET))
    acts = {'hero': [], 'opp': []}; contacts = []; byb = {}
    for b in sh['beats']:
        for a in b['actions']:
            m = mv(a['move']); sp = a.get('speed', 1.0)
            start = a['at'] - (m.key * FPS / sp if a.get('align') == 'key' else 0)
            sg = Seg(a['move'], start, sp, a.get('mirror', False), loop=(a['move'] == 'ready'))
            acts[a['who']].append(sg); byb.setdefault(b['n'], []).append((a['who'], sg))
    for b in sh['beats']:
        c = b.get('contact')
        if not c:
            continue
        src = byb[b.get('of_beat', b['n'])]
        att = [sg for who, sg in src if who == c['attacker']][0]
        cf = att.start + att.m.key * FPS / att.speed
        att.dx_end = cf - 4
        eff = att.m.eff
        if att.mirror:
            eff = ('r' if eff[0] == 'l' else 'l') + eff[1:]
        k = dict(c=int(round(cf)), att=c['attacker'], dfn=c['defender'], target=c['target'], seg=att, eff=eff,
                 hitstop=c.get('hitstop', 0), size=c.get('size', 1.0), evade=c.get('evade', False),
                 finisher=c.get('finisher', False), beat=b['n'])
        r = c.get('reaction')
        if r:
            rs = Seg(r['move'], k['c'], r.get('speed', 1.0), r.get('mirror', False), slide=r.get('slide', False),
                     fly=r.get('fly', False))
            acts[c['defender']].append(rs); k['rseg'] = rs
        contacts.append(k)
    X = sh['crossfade']; S = sh['fight_story_frames']
    segs = {}
    for who, L in acts.items():
        L.sort(key=lambda g: g.start)
        out = []
        for i, g in enumerate(L):
            out.append(g)
            nxt = L[i + 1].start if i + 1 < len(L) else S + 40
            if not g.loop and not g.fly and nxt > g.end - X + 2:
                out.append(Seg('ready', max(g.end - X, g.start + X), 1.0, loop=True))
        segs[who] = out
    return sh, segs, contacts


# ---------------------------------------------------------------- composition
D = {'hero': 1, 'opp': -1}


def world(sg, f, d):
    P = sg.local(f).copy()
    P[:, 0] -= sg.L0[0]; P[:, 2] -= sg.L0[2]
    if d < 0:
        P[:, 0] *= -1; P[:, 2] *= -1
    P[:, 0] += sg.A[0]; P[:, 2] += sg.A[2]
    if sg.dx and sg.dx_end:  # stage nudge spread over the move's approach (not a jump)
        P[:, 0] += d * sg.dx * ease((f - sg.start) / max(sg.dx_end - sg.start, 1), 'io')
    if sg.fly:  # finisher launch layer (not mocap): thrown backwards out of frame
        t = max(0.0, (f - sg.start) / FPS)
        P[:, 0] += -d * (2300 * t - 500 * t * t); P[:, 1] += max(0.0, 520 * t - 700 * t * t)
    return P


def compose(segs, x0, d, S, X):
    out = np.zeros((S, J, 3)); k = 0
    s0 = segs[0]; s0.L0 = s0.local(0)[0]; s0.A = np.array([x0, 0.0, 0.0])
    slide = np.zeros(S, bool)
    for f in range(S):
        while k + 1 < len(segs) and segs[k + 1].start <= f:
            k += 1; sg = segs[k]
            sg.L0 = sg.local(f)[0]
            prev = world(segs[k - 1], f, d)
            sg.A = np.array([prev[0, 0], 0.0, prev[0, 2]])
        P = world(segs[k], f, d)
        if k > 0 and f < segs[k].start + X:
            P = blend(world(segs[k - 1], f, d), P, ease((f - segs[k].start) / X, 'io'))
        out[f] = P
        slide[f] = segs[k].slide or segs[k].fly
    return out, slide


def head_c(P):
    a, b = P[I['upperneck']], P[I['head']]
    return a + (b - a) * 0.5


def target_point(Pd, kind, Pa, eff):
    if kind == 'head':
        Cc, r = head_c(Pd), R_HEAD + 14
    elif kind == 'guard':
        h = 'lhand' if Pd[I['lhand'], 1] > Pd[I['rhand'], 1] else 'rhand'
        Cc, r = Pd[I[h]], 22
    else:
        Cc, r = Pd[I['upperback']], 58
    u = Cc - Pa[I[eff]]; u[1] = 0
    u /= max(np.linalg.norm(u), 1e-6)
    return Cc - u * r


def solve_stage(segs, contacts, sh):
    """Nudge each attack so its strike reaches the target (stage spacing), in beat order."""
    S, X = sh['fight_story_frames'], sh['crossfade']
    st = sh['start']
    for k in contacts:
        for it in range(2):
            Wd = {w: compose(segs[w], st[w]['x'], D[w], S, X)[0] for w in ('hero', 'opp')}
            Pa, Pd = Wd[k['att']][k['c']], Wd[k['dfn']][k['c'] - (12 if k['evade'] else 0)]
            T = target_point(Pd, k['target'], Pa, k['eff'])
            dx = (T[0] - Pa[I[k['eff']], 0]) * D[k['att']]
            k['seg'].dx = float(np.clip(k['seg'].dx + dx, -320, 320))
        k['residual'] = float(abs(dx))


def plant(Wp, skip):
    """Foot-plant cleanup at 60 fps: lock ankles during ground contact, re-solve knees (2-bone IK)."""
    Wp = Wp.copy(); S = len(Wp)
    for side in 'lr':
        hip, kn, an = I[side + 'hipjoint'], I[side + 'femur'], I[side + 'tibia']
        y = Wp[:, an, 1]
        v = np.r_[np.linalg.norm(np.diff(Wp[:, an][:, [0, 2]], axis=0), axis=1), 0] * FPS
        con = (y < 64) & (v < 170) & ~skip
        corr = np.zeros((S, 3)); f = 0
        while f < S:
            if con[f]:
                e = f
                while e < S and con[e]: e += 1
                if e - f >= 4:
                    tgt = Wp[f:e, an].mean(0)
                    corr[f:e, [0, 2]] = tgt[[0, 2]] - Wp[f:e, an][:, [0, 2]]
                f = e
            else:
                f += 1
        corr = gaussian_filter1d(corr, 1.5, axis=0)
        l1, l2 = LEN[kn], LEN[an]
        for f in range(S):
            if np.abs(corr[f]).max() < 0.3:
                continue
            Hh, A = Wp[f, hip], Wp[f, an] + corr[f]
            Kn, Ac = two_bone(Hh, Wp[f, kn], A, l1, l2)
            shift = Ac - Wp[f, an]; Wp[f, kn] = Kn
            Wp[f, an] = Ac
            for j in DESC[an]:
                Wp[f, j] += shift
    return Wp


def two_bone(A, B0, T, l1, l2):
    d = T - A; Dd = max(min(np.linalg.norm(d), l1 + l2 - 0.5), abs(l1 - l2) + 0.5)
    d = d / max(np.linalg.norm(d), 1e-6)
    pole = B0 - A; pole = pole - d * (pole @ d)
    pole = pole / max(np.linalg.norm(pole), 1e-6)
    a = (l1 * l1 - l2 * l2 + Dd * Dd) / (2 * Dd); b = math.sqrt(max(l1 * l1 - a * a, 0))
    return A + d * a + pole * b, A + d * Dd


def rot_about(P, joints, pivot, ang):
    """Rotate joints about the lateral (z) axis through pivot (y up; +ang leans toward -x)."""
    c, s = math.cos(ang), math.sin(ang)
    v = P[joints] - pivot
    P[joints] = pivot + np.stack([v[:, 0] * c - v[:, 1] * s, v[:, 0] * s + v[:, 1] * c, v[:, 2]], -1)


def contact_w(f, c):
    if c - 8 <= f <= c: return ease((f - c + 8) / 8, 'io')
    if c < f <= c + 6: return 1 - ease((f - c) / 6, 'io')
    return 0.0


def layer_proc(Wd, contacts):
    """Anticipation lean, contact IK (fist/foot on the target), head look-at."""
    S = len(Wd['hero'])
    upper = [I['lowerback']] + DESC[I['lowerback']]
    for k in contacts:                                   # anticipation: lean back before the strike
        P = Wd[k['att']]; d = D[k['att']]
        for f in range(max(0, k['c'] - 20), max(0, k['c'] - 5)):
            u = (f - (k['c'] - 20)) / 15
            rot_about(P[f], upper, P[f, 0].copy(), d * math.radians(5 * k['size'] ** 0.5) * math.sin(math.pi * u))
    for k in contacts:                                   # contact IK
        if k['evade']:
            continue
        P, Pd = Wd[k['att']], Wd[k['dfn']]; e = k['eff']; side = e[0]
        for f in range(max(0, k['c'] - 8), min(S, k['c'] + 7)):
            w = contact_w(f, k['c'])
            if w <= 0 or e.endswith('femur'):
                continue
            T = target_point(Pd[f], k['target'], P[f], e)
            Q = P[f].copy()
            if e.endswith('hand'):
                a, b, c_ = I[side + 'clavicle'], I[side + 'humerus'], I[side + 'radius']
            else:
                a, b, c_ = I[side + 'hipjoint'], I[side + 'femur'], I[side + 'tibia']
            tw = T - (Q[I[e]] - Q[c_])
            Bn, Cn = two_bone(Q[a], Q[b], tw, LEN[b], LEN[c_])
            sh = Cn - Q[c_]; Q[b] = Bn; Q[c_] = Cn
            for j in DESC[c_]:
                Q[j] += sh
            P[f] = blend(P[f], Q, w)
    neck = [I['upperneck']] + DESC[I['upperneck']]
    for who, oth in (('hero', 'opp'), ('opp', 'hero')):  # head look-at (pitch toward the other head)
        P, O = Wd[who], Wd[oth]; d = D[who]
        for f in range(S):
            h, o = head_c(P[f]), head_c(O[f])
            e = math.atan2(o[1] - h[1], abs(o[0] - h[0]) + 1)
            rot_about(P[f], neck, P[f, I['lowerneck']].copy(), d * float(np.clip(0.5 * e, -0.22, 0.22)))
    return Wd


# ---------------------------------------------------------------- timing + projection
def build(sh, segs, contacts):
    S, X = sh['fight_story_frames'], sh['crossfade']
    solve_stage(segs, contacts, sh)
    Wd, sl = {}, {}
    for w in ('hero', 'opp'):
        Wd[w], sl[w] = compose(segs[w], sh['start'][w]['x'], D[w], S, X)
        Wd[w] = plant(Wd[w], sl[w])
    Wd = layer_proc(Wd, contacts)
    hs = {k['c']: k['hitstop'] for k in contacts if k['hitstop']}
    story = []
    for f in range(S):
        story.append(f)
        story += [f] * hs.get(f, 0)
    return Wd, story


def proj(P):
    c, s = math.cos(THETA), math.sin(THETA)
    out = np.empty_like(P)
    out[:, 0] = P[:, 0] * c + P[:, 2] * s
    out[:, 1] = -P[:, 1]
    out[:, 2] = -P[:, 0] * s + P[:, 2] * c
    return out


class G:  # glue for mocap_hook.draw_fighter
    I = I


# ---------------------------------------------------------------- transition scene
TR = 72


def car_x(i):
    """Front-bumper x of the car (moving left), cartoon brake from i=26 to a stop at i=56."""
    v, i0, i1, stop = 2600 / FPS, 26, 56, 290.0
    brake = v * (i1 - i0) / 2
    if i <= i0: return stop + brake + v * (i0 - i)
    if i <= i1:
        u = (i - i0) / (i1 - i0); return stop + brake * (1 - u) ** 2
    return stop


def car_pitch(i):
    if i < 26: return 0.0
    if i <= 56: return math.radians(7) * ease((i - 26) / 8, 'out')
    t = (i - 56) / FPS                                  # spring back after the stop
    return math.radians(7) * math.exp(-t * 9) * math.cos(t * 26)


def draw_car(cr, i):
    x0 = car_x(i); p = car_pitch(i)
    cr.save(); cr.translate(x0 + 120, 0); cr.rotate(-p); cr.translate(-120, 0)   # nose dips forward (left)
    sq = 1 - 0.05 * min(1, abs(p) / math.radians(7))
    cr.scale(1 + (1 - sq) * 0.8, sq)
    body, dark = C('#2bb3a6'), C('#1b7f77')
    blob(cr, [('poly', [(30, -95), (10, -150), (40, -215), (190, -240), (300, -365), (590, -370), (700, -245),
                        (790, -230), (800, -150), (780, -95)])], body)
    blob(cr, [('poly', [(318, -340), (440, -345), (440, -250), (250, -250)]),
              ('poly', [(460, -345), (575, -345), (650, -250), (460, -250)])], C('#9fd6ff'))
    blob(cr, [('poly', [(20, -115), (800, -115), (795, -95), (30, -95)])], dark)
    cr.set_source_rgba(*C('#fff3b0')); cr.arc(36, -180, 22, 0, 2 * math.pi); cr.fill()
    cr.set_source_rgba(*C('#ff4b5c')); cr.rectangle(776, -205, 22, 30); cr.fill()
    cr.restore()
    spin = 0 if i >= 26 else -(2600 / FPS) * i / 70
    for wx in (x0 + 160, x0 + 640):
        cr.set_source_rgba(*C('#121218')); cr.arc(wx, -70, 70, 0, 2 * math.pi); cr.fill()
        cr.set_source_rgba(*C('#9aa0ad')); cr.arc(wx, -70, 32, 0, 2 * math.pi); cr.fill()
        cr.set_source_rgba(*C('#5b6070')); cr.set_line_width(8)
        for kk in range(3):
            a = spin + kk * 2 * math.pi / 3
            cr.move_to(wx, -70); cr.line_to(wx + 30 * math.cos(a), -70 + 30 * math.sin(a)); cr.stroke()


def draw_beam(cr, i, strength=1.0):
    x0 = car_x(i); p = car_pitch(i)
    g = cairo.LinearGradient(x0 + 30, 0, x0 - 1100, 0)
    g.add_color_stop_rgba(0, 1, 0.95, 0.7, 0.32 * strength); g.add_color_stop_rgba(1, 1, 0.95, 0.7, 0)
    cr.set_source(g)
    yb = -180 - 120 * math.sin(p)
    cr.move_to(x0 + 30, yb); cr.line_to(x0 - 1100, yb - 260); cr.line_to(x0 - 1100, yb + 200); cr.close_path(); cr.fill()


def draw_road(cr, i):
    draw_ground(cr)
    cr.set_source_rgba(*C('#141020')); cr.rectangle(-4000, 30, 9000, 420); cr.fill()      # asphalt
    cr.set_source_rgba(*C('#2b2244')); cr.rectangle(-4000, -100, 9000, 130); cr.fill()   # verge
    cr.set_source_rgba(*C('#cfc49a'))
    for x in range(-4000, 5000, 260):
        cr.rectangle(x, 230, 130, 12); cr.fill()
    if i > 26:  # skid marks from locked wheels
        a = car_x(26); b = car_x(min(i, 56))
        cr.set_source_rgba(0.02, 0.02, 0.03, 0.55); cr.set_line_width(10)
        for off in (160, 640):
            cr.move_to(a + off, 0); cr.line_to(b + off, 0); cr.stroke()


# ---------------------------------------------------------------- main build
class Film:
    def __init__(s):
        s.sh, s.segs, s.contacts = load_sheet()
        s.Wd, s.story = build(s.sh, s.segs, s.contacts)
        s.NF = len(s.story)
        s.TOTAL = s.NF + TR
        s.cf = [k for k in s.contacts if k['finisher']][0]
        s.out_of = {}
        for o, st in enumerate(s.story):
            s.out_of.setdefault(st, o)
        s.ready = mv('ready')
        s.build_camera()

    def pose_story(s, who, t):
        A = s.Wd[who]; t = min(max(t, 0), len(A) - 1.001); i = int(t); u = t - i
        return A[i] * (1 - u) + A[i + 1] * u

    def story_t(s, fx):
        f = int(math.floor(fx)); u = fx - f
        if f >= s.NF - 1: return float(s.story[-1]) + (fx - (s.NF - 1))
        if f < 0: return 0.0
        a, b = s.story[f], s.story[f + 1]
        return a + (b - a) * u

    def poses(s, fx):
        t = s.story_t(fx)
        return proj(s.pose_story('hero', t)), proj(s.pose_story('opp', t))

    def tr_hero(s, i):
        """Hero in the transition: ready stance at x=0 (facing the oncoming car, +x)."""
        t = (i / FPS) % (2 * s.ready.dur); t = 2 * s.ready.dur - t if t > s.ready.dur else t
        P = sample(s.ready, t, False).copy(); P[:, [0, 2]] -= P[0, [0, 2]]
        return proj(P)

    # camera ------------------------------------------------------------
    def build_camera(s):
        NF = s.NF
        hh = np.array([s.poses(o)[0] for o in range(NF)]); oo = np.array([s.poses(o)[1] for o in range(NF)])
        hcx = np.array([head_c(p)[:2] for p in hh]); ocx = np.array([head_c(p)[:2] for p in oo])
        cf = s.out_of[s.cf['c']]
        wo = np.array([0.5 if o < cf else 0.5 + 0.35 * ease((o - cf - 6) / 10, 'io') for o in range(NF)])
        tx = gaussian_filter1d(hcx[:, 0] * (1 - wo) + ocx[:, 0] * wo, 5)
        ty = gaussian_filter1d(np.where(np.arange(NF) < cf, (hcx[:, 1] + ocx[:, 1]) / 2, hcx[:, 1]), 6) + 330
        z = np.full(NF, 1.22)
        for k in s.contacts:                              # push-ins on wind-ups
            o = s.out_of[k['c']]
            for f in range(NF):
                z[f] += 0.07 * k['size'] * math.exp(-((f - (o - 8)) / 10) ** 2)
        z = gaussian_filter1d(z, 3)
        IP = (s.poses(cf)[0][I[s.cf['eff']], :2] + head_c(s.poses(cf)[1])[:2]) / 2
        s.IP = IP
        cams = []
        for o in range(NF):
            c = (tx[o], ty[o], z[o], 0.0)
            if cf - 5 <= o < cf:                          # whip into the close-up
                u = ease((o - cf + 5) / 5, 'in')
                c = tuple(c[j] + ((IP[0], IP[1] + 40, 2.6, -0.08)[j] - c[j]) * u for j in range(4))
            elif cf <= o <= cf + s.cf['hitstop'] + 3:
                u = (o - cf) / (s.cf['hitstop'] + 3)
                c = (IP[0] + 8 * u, IP[1] + 40, 2.6 + 0.08 * u, -0.08)
            elif o > cf + s.cf['hitstop'] + 3:            # pull back, following him out of frame
                u = ease((o - cf - s.cf['hitstop'] - 3) / 8, 'snap'); a = cams[cf + s.cf['hitstop'] + 3]
                c = tuple(a[j] + ((tx[o], ty[o], 1.12, 0.0)[j] - a[j]) * u for j in range(4))
            cams.append(c)
        shake = np.zeros((NF, 2))
        for k in s.contacts:
            if k['evade']:
                continue
            o = s.out_of[k['c']]; amp = 6 + 7 * k['size']
            for j in range(6):
                if o + j < NF:
                    shake[o + j] = np.array([1.0, -0.7]) * amp * (1 - j / 6) * (1 if j % 2 == 0 else -1)
        s.cams, s.shake = cams, shake
        # transition camera (local frame i)
        hc = head_c(s.tr_hero(0))[:2]
        t_cams = []
        for i in range(TR):
            ccx = car_x(i) + 400
            if i < 14:
                c = (hc[0] + 3 * i, hc[1] + 30, 3.2 - 0.01 * i, 0.0)
            elif i < 28:
                u = ease((i - 14) / 14, 'io'); a = (hc[0] + 42, hc[1] + 30, 3.06, 0.0)
                c = tuple(a[j] + ((ccx, -330, 1.5, 0.0)[j] - a[j]) * u for j in range(4))
            elif i < 60:
                u = ease((i - 28) / 32, 'out'); a = t_cams[27]
                c = tuple(a[j] + (((car_x(i) + 420) / 2 - 20, -330, 1.0, 0.0)[j] - a[j]) * u for j in range(4))
            else:
                c = t_cams[59]
            t_cams.append(c)
        s.t_cams = t_cams

    def camera(s, o):
        if o < s.NF:
            x, y, z, r = s.cams[o]; return np.array([x, y]), z, r, s.shake[o]
        i = min(o - s.NF, TR - 7)                         # last 6 frames: freeze
        x, y, z, r = s.t_cams[i]; return np.array([x, y]), z, r, np.zeros(2)

    # render ------------------------------------------------------------
    def render_one(s, o, fx, layers, fg):
        cam, z, rot, shake = s.camera(o)
        img = np.zeros((H, W, 3), np.float32)
        for a, p, _ in layers:
            M = layer_matrix(cam, z, rot, shake, p)
            over(img, cv2.warpAffine(a, M, (W, H), flags=cv2.INTER_LINEAR,
                                     borderMode=cv2.BORDER_REPLICATE if p < 0.05 else cv2.BORDER_CONSTANT))
        surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H); cr = cairo.Context(surf)
        cr.translate(*(SC + shake)); cr.rotate(rot); cr.scale(z, z); cr.translate(-cam[0], -cam[1])
        if o < s.NF:
            draw_ground(cr)
            h, op = s.poses(fx); hp, opp_ = s.poses(fx - 3)
            MH.draw_fighter(cr, G, op, False, -1, opp_)
            MH.draw_fighter(cr, G, h, True, 1, hp)
            s.sparks(cr, o)
        else:
            i = min(fx - s.NF, TR - 7)
            draw_road(cr, int(i))
            draw_beam(cr, i)
            P = s.tr_hero(i); MH.draw_fighter(cr, G, P, True, 1, s.tr_hero(i - 3))
            s.face_light(cr, P, i)
            draw_car(cr, i)
        surf.flush(); over(img, surf_to_np(surf))
        over(img, cv2.warpAffine(fg[0], layer_matrix(cam, z, rot, shake, fg[1]), (W, H), flags=cv2.INTER_LINEAR))
        return img

    def face_light(s, cr, P, i):
        """Headlights reflected on the hero's face: warm wash from the car side, rim and eye glint."""
        hc = head_c(P); k = max(0.0, 1 - max(0, i - 30) / 30)
        g = cairo.RadialGradient(hc[0] + 70, hc[1], 10, hc[0] + 70, hc[1], 150)
        g.add_color_stop_rgba(0, 1, 0.96, 0.75, 0.55 * k); g.add_color_stop_rgba(1, 1, 0.96, 0.75, 0)
        cr.set_source(g); cr.arc(hc[0], hc[1], R_HEAD + 2, 0, 2 * math.pi); cr.fill()
        cr.set_source_rgba(1, 0.97, 0.8, 0.9 * k); cr.set_line_width(7)
        cr.arc(hc[0], hc[1], R_HEAD - 3, -1.0, 0.9); cr.stroke()
        cr.set_source_rgba(1, 1, 1, k); cr.arc(hc[0] + 41, hc[1] - 4, 3.5, 0, 2 * math.pi); cr.fill()

    def sparks(s, cr, o):
        for k in s.contacts:
            if k['evade']:
                continue
            o0 = s.out_of[k['c']]
            if not o0 <= o < o0 + 6:
                continue
            u = (o - o0) / 6; h, op = s.poses(o0)
            c = (h[I[k['eff']], :2] if k['att'] == 'hero' else op[I[k['eff']], :2])
            d = 1 if k['att'] == 'hero' else -1
            cr.set_line_cap(cairo.LINE_CAP_ROUND)
            for j, ang in enumerate((-60, -25, 10, 45)):
                a = math.radians(ang) if d > 0 else math.pi - math.radians(ang)
                r1, r2 = 18 + 40 * u, (36 + 70 * u) * (0.8 + 0.2 * (j % 2))
                cr.set_source_rgba(1, 0.94, 0.7, 1 - 0.8 * u); cr.set_line_width(max(1.5, 5 * (1 - u)))
                cr.move_to(c[0] + r1 * math.cos(a), c[1] + r1 * math.sin(a))
                cr.line_to(c[0] + r2 * math.cos(a), c[1] + r2 * math.sin(a)); cr.stroke()

    def speed(s, o):
        cam, z, _, _ = s.camera(o)
        if o >= s.NF:
            i = o - s.NF
            if i >= TR - 6: return 0.0
            c0, c1 = s.t_cams[max(i - 1, 0)], s.t_cams[min(i + 1, TR - 1)]
            return max(abs(c1[0] - c0[0]) / 2 * z, abs(car_x(i + 0.5) - car_x(i - 0.5)) * z)
        a, b = s.poses(o - 0.5), s.poses(o + 0.5)
        return max(np.abs(a[i][:, :2] - b[i][:, :2]).max() for i in (0, 1)) * z

    def flash(s, o):
        return {s.NF - 1: 0.85, s.NF: 0.45}.get(o, 0.0)

    def render(s, o, layers, fg):
        if s.speed(o) > 18:
            img = sum(s.render_one(o, o + (k - 1.5) / 4, layers, fg) for k in range(4)) / 4
        else:
            img = s.render_one(o, o, layers, fg)
        a = s.flash(o)
        if a:
            img = img * (1 - a) + np.array([1.0, 0.9, 0.62], np.float32) * a
        return (np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8)


# ---------------------------------------------------------------- audio
def record_scratch(d=0.32):
    t = np.arange(int(sfx.SR * d)) / sfx.SR
    f = 260 + 1300 * np.abs(np.sin(np.pi * t / d * 1.5))
    ph = np.cumsum(f) / sfx.SR
    saw = 2 * (ph % 1) - 1
    n = sfx.lp(np.random.default_rng(9).standard_normal(len(t)), 3)
    return sfx.fade(saw * 0.5 + n * 0.5 * np.sin(np.pi * t / d)) * 0.8


def audio(F, path):
    SR = sfx.SR; n = int(SR * F.TOTAL / FPS); mix = np.zeros(n); rng = np.random.default_rng(5)

    def put(sig, t, g=1.0):
        i = max(0, int(round(t * SR)))
        if i >= n: return
        seg = sig[:n - i]; mix[i:i + len(seg)] += seg * g
    cues = []
    for k in F.contacts:                                  # whoosh on the fastest limb frames
        who = 0 if k['att'] == 'hero' else 1
        best, bo = 0, 0
        for o in range(max(0, F.out_of[k['c']] - 24), F.out_of[k['c']] + 1):
            v = np.linalg.norm(F.poses(o + .5)[who][I[k['eff']], :2] - F.poses(o - .5)[who][I[k['eff']], :2])
            if v > best: best, bo = v, o
        put(sfx.whoosh(0.22, 12 if k['size'] > 1 else 18), bo / FPS - 0.13, 0.55 + 0.25 * min(k['size'], 1.5))
        if not k['evade']:
            o = F.out_of[k['c']]; t = o / FPS
            put(sfx.thump(0.3) * (0.8 + 0.3 * k['size']), t)
            put(sfx.boom(0.9 if k['finisher'] else 0.5), t, 0.5 + 0.3 * k['size'])  # bass hit on the contact frame
            cues.append(round(t, 3))
        if k.get('rseg') is not None and (k['rseg'].slide or k['rseg'].fly):
            d = 0.4; tt = np.arange(int(SR * d)) / SR
            put(sfx.lp(rng.standard_normal(len(tt)), 22) * np.sin(np.pi * tt / d) ** 1.5, F.out_of[k['c']] / FPS + 0.03, 0.5)
    t0 = F.NF / FPS
    put(sfx.boom(1.0), (F.NF - 1) / FPS, 0.7)                                       # flash cut
    put(sfx.whoosh(0.3, 10), t0 + 14 / FPS, 0.9)                                     # whip pan
    put(sfx.screech(0.55), t0 + 26 / FPS, 0.7)                                       # cartoon brake
    put(sfx.thump(0.2), t0 + 56 / FPS, 0.5)
    put(record_scratch(), t0 + (TR - 6) / FPS, 1.0)                                   # freeze
    fade = np.ones(n); fade[-int(SR * .02):] = np.linspace(1, 0, int(SR * .02)); mix *= fade
    g, ceil = 1.0 / np.abs(mix).max(), 10 ** (-2.0 / 20)
    for _ in range(8):
        y = np.tanh(mix * g / ceil) * ceil
        hook.write_wav(path + '.tmp.wav', y)
        r = subprocess.run(['ffmpeg', '-nostats', '-i', path + '.tmp.wav', '-af', 'ebur128=peak=true', '-f', 'null', '-'],
                           capture_output=True, text=True).stderr
        Il = float(r.split('Integrated loudness:')[1].split('I:')[1].split('LUFS')[0])
        P = float(r.split('True peak:')[1].split('Peak:')[1].split('dBFS')[0])
        if abs(Il + 14) < 0.3 and P <= -1.0:
            break
        g *= 10 ** ((-14 - Il) / 20)
    os.remove(path + '.tmp.wav'); hook.write_wav(path, y)
    return Il, P, cues


# ---------------------------------------------------------------- report + main
def report(F):
    print('frames: fight %d (story %d + hit-stops), transition %d, total %d' % (F.NF, len(F.Wd['hero']), TR, F.TOTAL))
    for k in F.contacts:
        print('beat %2d %-4s %-11s -> %-4s %-6s contact story %3d out %3d hitstop %d dx %+.0f residual %.0f%s' % (
            k['beat'], k['att'], k['seg'].m.name, k['dfn'], k['target'], k['c'], F.out_of[k['c']], k['hitstop'],
            k['seg'].dx, k['residual'], ' EVADE' if k['evade'] else (' -> ' + k['rseg'].m.name if k.get('rseg') else '')))
    gaps = []
    hit = set()
    for k in F.contacts:
        hit.update(range(k['c'] - 6, k['c'] + 8))
    for f in range(len(F.Wd['hero'])):
        if f in hit: continue
        h, o = F.Wd['hero'][f], F.Wd['opp'][f]
        gaps.append((abs(o[I['thorax'], 0] - h[I['thorax'], 0]), f))
    print('min torso gap outside contacts: %.0f px at story %d (body width ~110)' % min(gaps))


def main():
    os.makedirs(OUT, exist_ok=True)
    F = Film(); report(F)
    res = dict(json.load(open(SHEET)))
    res['resolved_contacts'] = [dict(beat=k['beat'], attacker=k['att'], move=k['seg'].m.name, story_frame=k['c'],
                                     output_frame=F.out_of[k['c']], hitstop=k['hitstop'], evade=k['evade'],
                                     reaction=(k['rseg'].m.name if k.get('rseg') else None)) for k in F.contacts]
    res['output_frames'] = dict(fight=F.NF, transition=TR, total=F.TOTAL, flash=[F.NF - 1, F.NF], freeze_from=F.TOTAL - 6)
    json.dump(res, open(os.path.join(OUT, 'fight6_choreo_resolved.json'), 'w'), indent=1)
    layers, fg = make_layers(MOON)
    if '--frames' in sys.argv:
        for o in map(int, sys.argv[sys.argv.index('--frames') + 1].split(',')):
            cv2.imwrite(os.path.join(OUT, 'g%03d.png' % o), F.render(o, layers, fg)[..., ::-1])
        return
    wav = os.path.join(OUT, 'fight6-sfx.wav')
    Il, P, cues = audio(F, wav); print('audio I=%.1f LUFS TP=%.1f dBTP contacts at %s' % (Il, P, cues))
    mp4 = os.path.join(OUT, 'fight6-test.mp4')
    cmd = ['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '%dx%d' % (W, H),
           '-r', str(FPS), '-i', '-', '-i', wav, '-map', '0:v', '-map', '1:a', '-c:v', 'libx264', '-preset', 'slow',
           '-crf', '17', '-pix_fmt', 'yuv420p', '-vf', 'setsar=1', '-aspect', '9:16', '-c:a', 'aac', '-b:a', '320k',
           '-t', '%.3f' % (F.TOTAL / FPS), '-movflags', '+faststart', mp4]
    pr = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    nb = 0
    for o in range(F.TOTAL):
        nb += F.speed(o) > 18
        pr.stdin.write(F.render(o, layers, fg).tobytes())
    pr.stdin.close(); pr.wait()
    print('motion-blurred frames:', nb, '->', mp4)


if __name__ == '__main__':
    main()
