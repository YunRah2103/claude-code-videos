"""Hand-keyed stickman fight (replaces the mocap pipeline for pixel6).

Both fighters are animated pose-to-pose: every key is a hand-placed pose (joint angles) with its own easing,
holds for hit-stop, and anticipation / follow-through keys. Strike keys marked `reach` are solved so the
fist, foot or blade tip lands exactly on the target at the contact frame. Output: per-frame joint arrays in
the 31-joint layout the renderer uses (60 fps, hit-stops baked in as holds).

Classic stickman proportions: ~520 units tall, head diameter ~22 % of the height, legs ~half the height,
arms reaching mid-thigh. Keyed curves are smoothed (strike and hit-stop frames kept crisp) and the arms
trail the body by 2 frames, the head by 1, for overlapping, fluid motion.
Angles in degrees: limbs from straight down (+ = forward / up), spine from vertical (+ = leaning forward),
'rot' rolls the whole body (+ = backward flip). 'dx' moves the fighter toward the opponent.
"""
import math
import numpy as np

NAMES = ['root', 'lhipjoint', 'lfemur', 'ltibia', 'lfoot', 'ltoes', 'rhipjoint', 'rfemur', 'rtibia', 'rfoot', 'rtoes',
         'lowerback', 'upperback', 'thorax', 'lowerneck', 'upperneck', 'head', 'lclavicle', 'lhumerus', 'lradius',
         'lwrist', 'lhand', 'lfingers', 'lthumb', 'rclavicle', 'rhumerus', 'rradius', 'rwrist', 'rhand', 'rfingers', 'rthumb']
I = {n: i for i, n in enumerate(NAMES)}
HEAD_R, FIG, BLADE = 58.0, 520.0, 210.0
L = dict(hip=16, thigh=116, shin=110, foot=32, lb=50, ub=50, th=46, ln=8, un=14, head=78, upper=96, fore=88, hand=26)

STANCE = dict(lean=10, head=-4, rot=0, air=0, lhip=30, lknee=42, rhip=-24, rknee=32, lsh=48, lel=78, rsh=28, rel=112)
POSES = {
    'stance': {},
    'bob': dict(lknee=50, rknee=40, lean=13),
    'crouch': dict(lean=30, head=-10, lhip=48, lknee=86, rhip=-4, rknee=78, lsh=20, lel=60, rsh=4, rel=74),
    'dash': dict(lean=48, head=-20, lhip=74, lknee=36, rhip=-58, rknee=86, lsh=-44, lel=24, rsh=-62, rel=20),
    'jab': dict(lean=22, lhip=42, lknee=26, rhip=-32, rknee=20, lsh=90, lel=0, rsh=32, rel=120),
    'cross': dict(lean=30, lhip=48, lknee=30, rhip=-38, rknee=8, rsh=92, rel=0, lsh=38, lel=104),
    'slip': dict(lean=-26, head=-14, lhip=22, lknee=30, rhip=-34, rknee=48, lsh=40, lel=90, rsh=20, rel=120),
    'chamber': dict(lean=-14, rhip=96, rknee=122, lhip=6, lknee=16, lsh=44, lel=70, rsh=-18, rel=60),
    'kick': dict(lean=-34, rhip=112, rknee=0, lhip=2, lknee=12, lsh=62, lel=60, rsh=-40, rel=20),
    'hit': dict(lean=-26, head=-32, lhip=18, lknee=34, rhip=-36, rknee=24, lsh=24, lel=12, rsh=-32, rel=22),
    'stagger': dict(lean=-14, head=-10, lhip=10, lknee=34, rhip=-42, rknee=30, lsh=64, lel=30, rsh=-20, rel=44),
    'wind': dict(lean=-10, head=-10, rsh=205, rel=20, lsh=70, lel=40, lhip=36, lknee=48, rhip=-20, rknee=36),
    'slash': dict(lean=36, head=4, rsh=60, rel=0, lsh=-30, lel=20, lhip=56, lknee=30, rhip=-42, rknee=14),
    'follow': dict(lean=42, rsh=-42, rel=10, lsh=-40, lel=20, lhip=60, lknee=40, rhip=-40, rknee=20),
    'tuck': dict(lean=16, lhip=84, lknee=132, rhip=72, rknee=130, lsh=86, lel=60, rsh=62, rel=60),
    'airkick': dict(lean=-30, head=8, rhip=102, rknee=0, lhip=42, lknee=112, lsh=-30, lel=30, rsh=104, rel=30),
    'land': dict(lean=36, head=-12, lhip=52, lknee=88, rhip=-6, rknee=82, lsh=12, lel=40, rsh=-10, rel=40),
    'lunge': dict(lean=32, lhip=62, lknee=30, rhip=-46, rknee=4, rsh=94, rel=0, lsh=22, lel=92),
    'block': dict(lean=4, rsh=118, rel=64, lsh=62, lel=92, lhip=34, lknee=46, rhip=-22, rknee=38),
    'slide': dict(lean=-42, head=6, lhip=86, lknee=4, rhip=12, rknee=130, lsh=-20, lel=30, rsh=60, rel=40),
    'fly': dict(lean=-44, head=-24, lhip=52, lknee=64, rhip=30, rknee=84, lsh=124, lel=20, rsh=142, rel=30),
    'sprawl': dict(lean=-60, head=-20, lhip=70, lknee=30, rhip=40, rknee=60, lsh=150, lel=10, rsh=170, rel=10),
}


def down(a):
    a = math.radians(a); return np.array([math.sin(a), -math.cos(a)])


def pose(k):
    """Joint positions (local frame, facing +x) from an angle key; grounded unless airborne/rolled."""
    P = np.zeros((31, 3))
    u = np.array([math.sin(math.radians(k['lean'])), math.cos(math.radians(k['lean']))])
    hu = np.array([math.sin(math.radians(k['lean'] + k['head'])), math.cos(math.radians(k['lean'] + k['head']))])
    def put(n, xy, z=0.0): P[I[n]] = [xy[0], xy[1], z]
    root = np.zeros(2); put('root', root)
    lb = root + u * L['lb']; ub = lb + u * L['ub']; th = ub + u * L['th']; ln = th + u * L['ln']; un = ln + u * L['un']
    put('lowerback', lb); put('upperback', ub); put('thorax', th); put('lowerneck', ln); put('upperneck', un)
    put('head', un + hu * L['head'])
    for s, z in (('l', -1), ('r', 1)):
        hip = root + [0, -L['hip']]
        thigh = k[s + 'hip']; shin = thigh - k[s + 'knee']
        kn = hip + down(thigh) * L['thigh']; an = kn + down(shin) * L['shin']
        fd = np.array([math.cos(math.radians(shin * .4)), math.sin(math.radians(shin * .4))])
        ft = an + fd * L['foot'] + [0, -8]; to = ft + fd * 12
        put(s + 'hipjoint', hip, 20 * z); put(s + 'femur', kn, 30 * z); put(s + 'tibia', an, 36 * z)
        put(s + 'foot', ft, 38 * z); put(s + 'toes', to, 38 * z)
        sh = th + [0, -6]; ua = k[s + 'sh']; fa = ua + k[s + 'el']
        el = sh + down(ua) * L['upper']; wr = el + down(fa) * L['fore']
        put(s + 'clavicle', sh, 30 * z); put(s + 'humerus', el, 34 * z); put(s + 'radius', wr, 32 * z)
        put(s + 'wrist', wr + down(fa) * 10, 38 * z); put(s + 'hand', wr + down(fa) * L['hand'], 38 * z)
        put(s + 'fingers', wr + down(fa) * (L['hand'] + 6), 38 * z); put(s + 'thumb', wr + down(fa + 30) * 10, 34 * z)
    r = k.get('rot', 0) % 360
    if abs(r) > 1e-6:
        c = P[I['lowerback'], :2].copy(); a = math.radians(r); ca, sa = math.cos(a), math.sin(a)
        v = P[:, :2] - c
        P[:, 0] = c[0] + v[:, 0] * ca - v[:, 1] * sa; P[:, 1] = c[1] + v[:, 0] * sa + v[:, 1] * ca
        low = P[:, 1].min() - 24
    else:
        low = min(P[I['ltibia'], 1], P[I['rtibia'], 1])
    P[:, 1] += 24 - low + k['air']
    P[:, 1] = np.maximum(P[:, 1], 0)
    return P


EASE = {'io': lambda u: u * u * (3 - 2 * u), 'in': lambda u: u ** 3, 'out': lambda u: 1 - (1 - u) ** 3,
        'lin': lambda u: u, 'snap': lambda u: 1 - (1 - u) ** 4, 'hold': lambda u: 0.0}


def K(f, name, ease='io', **kw):
    d = dict(STANCE); d.update(POSES[name]); d.update({k: v for k, v in kw.items() if k in STANCE})
    return dict(f=f, ease=ease, pose=d, dx=kw.get('dx', 0.0), reach=kw.get('reach'), weapon=kw.get('weapon'))


# ---------------------------------------------------------------- the choreography (60 fps output frames)
# Fewer, longer moves: 10-14 frame anticipation, short snap, long follow-through. Hit-stop = held keys.
CONTACTS = [
    dict(beat=2, c=58, att='opp', eff='lhand', target='head', evade=True, label='opponent jab, hero slips'),
    dict(beat=3, c=92, att='hero', eff='lhand', target='head', hitstop=2, size=.7, fx='spark', label='hero jab'),
    dict(beat=4, c=112, att='hero', eff='rhand', target='head', hitstop=2, size=.8, fx='spark', label='hero cross'),
    dict(beat=5, c=150, att='opp', eff='rtoes', target='head', evade=True, tilt=True, label='opponent kick, hero backflips out'),
    dict(beat=7, c=222, att='hero', eff='blade', target='head', hitstop=3, size=1.0, fx='fire', weapon=True, label='dash-in blade slash'),
    dict(beat=10, c=262, att='hero', eff='blade', target='head', hitstop=4, size=1.6, fx='fire', weapon=True, finisher=True, tilt=True,
         label='FINISHER: leaping blade slash, opponent flies away'),
]
SHOTPLAN = [(0, 'wide'), (74, 'medium'), (128, 'wide'), (188, 'medium'), (240, 'wide'), (256, 'close'), (276, 'wide')]
DUST = [(40, 'opp'), (174, 'hero'), (204, 'hero'), (246, 'opp'), (280, 'hero'), (287, 'opp')]

HERO = [K(0, 'stance'), K(18, 'bob'), K(36, 'stance', dx=20), K(50, 'bob'),
        K(58, 'slip', 'out', dx=-30), K(72, 'stance', 'io', dx=10),
        K(82, 'crouch', 'io'), K(92, 'jab', 'snap', reach=('head', 'lhand')), K(96, 'jab', 'hold'),
        K(104, 'crouch', 'out'), K(112, 'cross', 'snap', reach=('head', 'rhand')), K(116, 'cross', 'hold'), K(130, 'stance', 'out'),
        K(138, 'crouch', 'io'),
        K(148, 'tuck', 'out', dx=-110, air=170, rot=130), K(161, 'tuck', 'lin', dx=-100, air=185, rot=265),
        K(174, 'land', 'in', dx=-45, rot=360), K(186, 'stance', 'io', rot=360, weapon=True),
        K(194, 'crouch', 'io', rot=360), K(205, 'dash', 'out', dx=110, rot=360), K(213, 'wind', 'out', dx=40, rot=360),
        K(222, 'slash', 'snap', reach=('head', 'blade'), rot=360), K(228, 'slash', 'hold', rot=360),
        K(238, 'follow', 'out', dx=20, rot=360), K(246, 'crouch', 'io', rot=360),
        K(254, 'wind', 'out', dx=260, air=150, rot=360), K(262, 'slash', 'snap', reach=('head', 'blade'), air=110, rot=360),
        K(270, 'slash', 'hold', air=110, rot=360), K(280, 'follow', 'in', dx=30, air=0, rot=360), K(287, 'follow', 'io', rot=360)]

OPP = [K(0, 'stance'), K(16, 'crouch', 'io'), K(30, 'dash', 'out', dx=120), K(40, 'stance', 'io', dx=25),
       K(50, 'crouch', 'io'), K(58, 'jab', 'snap', reach=('head@50', 'lhand')), K(72, 'stance', 'out'),
       K(92, 'stance', 'io'), K(96, 'stance', 'hold'), K(104, 'hit', 'out', dx=-40), K(110, 'stance', 'io'),
       K(112, 'stance', 'io'), K(116, 'stance', 'hold'), K(126, 'stagger', 'out', dx=-60), K(134, 'stance', 'io'),
       K(140, 'chamber', 'io', dx=40), K(150, 'kick', 'snap', reach=('head@138', 'rtoes')), K(162, 'chamber', 'out'), K(176, 'stance', 'io'),
       K(222, 'stance', 'io'), K(228, 'stance', 'hold'), K(238, 'fly', 'out', dx=-170, air=70, rot=-10), K(246, 'land', 'in', dx=-40, rot=0),
       K(256, 'stagger', 'io'), K(262, 'stagger', 'io'), K(270, 'stagger', 'hold'),
       K(279, 'fly', 'out', dx=-260, air=200, rot=-60), K(287, 'sprawl', 'lin', dx=-220, air=240, rot=-140)]

START = {'hero': -230.0, 'opp': 290.0}
FACE = {'hero': 1, 'opp': -1}
N_FIGHT = 288


def world(P, x, d):
    W_ = P.copy(); W_[:, 0] = x + d * P[:, 0]; W_[:, 2] = d * P[:, 2]
    return W_


def head_center(P):
    a, b = P[I['lowerneck'], :2], P[I['head'], :2]
    u = (b - a) / max(np.linalg.norm(b - a), 1e-6)
    return a + u * HEAD_R * 1.1


def blade_pts(P):
    h, r = P[I['rhand'], :2], P[I['rradius'], :2]
    v = (h - r) / max(np.linalg.norm(h - r), 1e-6)
    return h, h + v * BLADE


def point(P, what):
    if what == 'head': return head_center(P)
    if what == 'blade': return blade_pts(P)[0] + (blade_pts(P)[1] - blade_pts(P)[0]) * .55
    if what == 'bladetip': return blade_pts(P)[1]
    return P[I[what], :2]


class Track:
    def __init__(s, who, keys):
        s.who, s.keys, s.d = who, keys, FACE[who]
        x = START[who]
        for k in keys:
            x += s.d * k['dx']; k['x'] = x
        s.shift = [0.0] * len(keys)

    def xs(s):
        out, acc = [], 0.0
        for k, sh in zip(s.keys, s.shift):
            acc += sh; out.append(k['x'] + acc)
        return out

    def params(s, f):
        ks, xs = s.keys, s.xs()
        j = max(i for i, k in enumerate(ks) if k['f'] <= f) if f >= ks[0]['f'] else 0
        if j == len(ks) - 1 or f <= ks[0]['f']:
            p, x = ks[j]['pose'], xs[j]
        else:
            a, b = ks[j], ks[j + 1]
            u = EASE[b['ease']]((f - a['f']) / max(b['f'] - a['f'], 1e-6))
            p = {q: a['pose'][q] + (b['pose'][q] - a['pose'][q]) * u for q in a['pose']}
            x = xs[j] + (xs[j + 1] - xs[j]) * u
        return p, x

    def at(s, f):
        p, x = s.params(f)
        return world(pose(p), x, s.d)

    def frames(s, n, crisp):
        """Fluid playback: smooth the keyed curves (sigma 2.5 frames) except near strikes/hit-stops (crisp),
        and let the arms trail the body by 2 frames and the head by 1 (overlapping action)."""
        from scipy.ndimage import gaussian_filter1d
        names = list(STANCE)
        raw = [s.params(f) for f in range(n)]
        A = np.array([[p[q] for q in names] + [x] for p, x in raw])
        Sm = gaussian_filter1d(A, 2.5, axis=0, mode='nearest')
        w = np.ones(n)
        for c0, c1 in crisp:
            for f in range(max(0, c0 - 8), min(n, c1 + 4)):
                d = 0 if c0 - 2 <= f <= c1 else min(abs(f - c0), abs(f - c1))
                w[f] = min(w[f], min(1.0, d / 6.0))
        A2 = A * (1 - w[:, None]) + Sm * w[:, None]
        lag = {'lsh': 2, 'lel': 2, 'rsh': 2, 'rel': 2, 'head': 1}
        out = []
        for f in range(n):
            p = {}
            for i, q in enumerate(names):
                g = max(0, f - lag.get(q, 0)) if w[f] > .5 else f
                p[q] = A2[g, i]
            out.append(world(pose(p), A2[f, -1], s.d))
        return np.array(out)


def solve(tracks):
    """Shift each `reach` key so its effector lands on the target at that frame (in time order)."""
    order = sorted([(k['f'], who, i) for who, t in tracks.items() for i, k in enumerate(t.keys) if k['reach']])
    for _ in range(3):
        for f, who, i in order:
            t = tracks[who]; other = tracks['opp' if who == 'hero' else 'hero']
            tgt, eff = t.keys[i]['reach']
            tf = f
            if '@' in tgt: tgt, tf = tgt.split('@'); tf = int(tf)
            T = point(other.at(tf), tgt)
            P = t.at(f)
            side = 'l' if eff == 'lhand' else 'r'                     # aim the limb at the target (straight limb)
            base = P[I[side + 'clavicle'], :2] if eff in ('lhand', 'rhand', 'blade') else P[I[side + 'hipjoint'], :2]
            v = T - base; v[0] *= t.d
            ang = math.degrees(math.atan2(v[0], -v[1]))
            key = 'sh' if eff in ('lhand', 'rhand', 'blade') else 'hip'
            if eff == 'blade': ang -= 8                                  # blade continues past the hand
            j = i
            while j < len(t.keys) and (j == i or t.keys[j]['ease'] == 'hold'):
                t.keys[j]['pose'][side + key] = ang
                if key == 'sh': t.keys[j]['pose'][side + 'el'] = 0
                else: t.keys[j]['pose'][side + 'knee'] = 0
                j += 1
            E = point(t.at(f), 'blade' if eff == 'blade' else eff)
            t.shift[i] += T[0] - E[0]


def build():
    tracks = {'hero': Track('hero', HERO), 'opp': Track('opp', OPP)}
    solve(tracks)
    crisp = [(c['c'], c['c'] + 2 * c.get('hitstop', 0)) for c in CONTACTS]
    Wd = {w: t.frames(N_FIGHT, crisp) for w, t in tracks.items()}
    weapon = np.zeros(N_FIGHT, bool); on = False; kf = 0
    for k in HERO:
        if k['weapon'] is not None:
            if on: weapon[kf:k['f']] = True
            on, kf = k['weapon'], k['f']
    if on: weapon[kf:] = True
    contacts = []
    for c in CONTACTS:
        k = dict(c); k.setdefault('hitstop', 0); k.setdefault('size', .6); k.setdefault('fx', 'spark')
        k.setdefault('evade', False); k.setdefault('finisher', False); k.setdefault('weapon', False)
        k['dfn'] = 'opp' if k['att'] == 'hero' else 'hero'
        k['o'] = k['c']; k['peak'] = k['c'] - 3
        contacts.append(k)
    return Wd, contacts, weapon, tracks


def stance_bob(i, fps=60):
    """Idle stance with a slow breathing bob (for the transition)."""
    u = .5 - .5 * math.cos(2 * math.pi * i / fps * .9)
    p = dict(STANCE); p.update({q: STANCE[q] + (STANCE[q] + POSES['bob'].get(q, STANCE[q]) - 2 * STANCE[q]) * u for q in STANCE})
    return pose(p)
