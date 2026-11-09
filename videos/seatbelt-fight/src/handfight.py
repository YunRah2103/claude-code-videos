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

STANCE = dict(sq=0.0, lean=10, head=-4, rot=0, air=0, lhip=30, lknee=42, rhip=-24, rknee=32, lsh=48, lel=78, rsh=28, rel=112)
POSES = {
    'stance': {},
    'bob': dict(lknee=50, rknee=40, lean=13),
    'crouch': dict(sq=-.14, lean=30, head=-10, lhip=48, lknee=86, rhip=-4, rknee=78, lsh=20, lel=60, rsh=4, rel=74),
    'dash': dict(sq=.10, lean=48, head=-20, lhip=74, lknee=36, rhip=-58, rknee=86, lsh=-44, lel=24, rsh=-62, rel=20),
    'jab': dict(sq=.10, lean=22, lhip=42, lknee=26, rhip=-32, rknee=20, lsh=90, lel=0, rsh=32, rel=120),
    'cross': dict(sq=.12, lean=30, lhip=48, lknee=30, rhip=-38, rknee=8, rsh=92, rel=0, lsh=38, lel=104),
    'slip': dict(lean=-26, head=-14, lhip=22, lknee=30, rhip=-34, rknee=48, lsh=40, lel=90, rsh=20, rel=120),
    'chamber': dict(lean=-14, rhip=96, rknee=122, lhip=6, lknee=16, lsh=44, lel=70, rsh=-18, rel=60),
    'kick': dict(sq=.12, lean=-34, rhip=112, rknee=0, lhip=2, lknee=12, lsh=62, lel=60, rsh=-40, rel=20),
    'hit': dict(lean=-26, head=-32, lhip=18, lknee=34, rhip=-36, rknee=24, lsh=24, lel=12, rsh=-32, rel=22),
    'stagger': dict(lean=-14, head=-10, lhip=10, lknee=34, rhip=-42, rknee=30, lsh=64, lel=30, rsh=-20, rel=44),
    'wind': dict(sq=-.06, lean=-10, head=-10, rsh=205, rel=20, lsh=70, lel=40, lhip=36, lknee=48, rhip=-20, rknee=36),
    'slash': dict(sq=.14, lean=36, head=4, rsh=60, rel=0, lsh=-30, lel=20, lhip=56, lknee=30, rhip=-42, rknee=14),
    'follow': dict(lean=42, rsh=-42, rel=10, lsh=-40, lel=20, lhip=60, lknee=40, rhip=-40, rknee=20),
    'tuck': dict(sq=-.10, lean=16, lhip=84, lknee=132, rhip=72, rknee=130, lsh=86, lel=60, rsh=62, rel=60),
    'airkick': dict(sq=.12, lean=-30, head=8, rhip=102, rknee=0, lhip=42, lknee=112, lsh=-30, lel=30, rsh=104, rel=30),
    'land': dict(sq=-.12, lean=36, head=-12, lhip=52, lknee=88, rhip=-6, rknee=82, lsh=12, lel=40, rsh=-10, rel=40),
    'lunge': dict(lean=32, lhip=62, lknee=30, rhip=-46, rknee=4, rsh=94, rel=0, lsh=22, lel=92),
    'block': dict(lean=4, rsh=118, rel=64, lsh=62, lel=92, lhip=34, lknee=46, rhip=-22, rknee=38),
    'slide': dict(lean=-42, head=6, lhip=86, lknee=4, rhip=12, rknee=130, lsh=-20, lel=30, rsh=60, rel=40),
    'fly': dict(sq=.10, lean=-44, head=-24, lhip=52, lknee=64, rhip=30, rknee=84, lsh=124, lel=20, rsh=142, rel=30),
    'load': dict(sq=-.10, lean=2, head=-6, lhip=26, lknee=38, rhip=-30, rknee=56, lsh=40, lel=88, rsh=20, rel=118),
    'step': dict(lean=16, lhip=44, lknee=32, rhip=-30, rknee=36, lsh=52, lel=74, rsh=28, rel=112),
    'jab_recoil': dict(lean=18, lhip=40, lknee=30, rhip=-30, rknee=24, lsh=70, lel=40, rsh=30, rel=118),
    'cross_recoil': dict(lean=24, lhip=46, lknee=34, rhip=-36, rknee=14, rsh=70, rel=36, lsh=40, lel=100),
    'land2': dict(sq=-.18, lean=40, head=-14, lhip=58, lknee=104, rhip=-4, rknee=98, lsh=6, lel=40, rsh=-14, rel=40),
    'hit_head': dict(lean=4, head=-48, lsh=40, lel=60, rsh=10, rel=80),
    'hit_body': dict(sq=.08, lean=-30, head=-26, lhip=16, lknee=36, rhip=-40, rknee=26, lsh=20, lel=20, rsh=-36, rel=30),
    'recover': dict(lean=18, head=2, lhip=34, lknee=48, rhip=-22, rknee=38, lsh=46, lel=80, rsh=26, rel=110),
    'sprawl': dict(lean=-60, head=-20, lhip=70, lknee=30, rhip=40, rknee=60, lsh=150, lel=10, rsh=170, rel=10),
}


def down(a):
    a = math.radians(a); return np.array([math.sin(a), -math.cos(a)])


def pose(k):
    """Joint positions (local frame, facing +x) from an angle key; grounded unless airborne/rolled.
    k['sq'] squashes (<0) or stretches (>0) the spine and limbs."""
    global L
    L0 = L; g = 1 + k.get('sq', 0.0)
    L = {q: (v if q in ('head', 'hip', 'foot') else v * g) for q, v in L0.items()}
    try:
        return _pose(k)
    finally:
        L = L0


def _pose(k):
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
        'lin': lambda u: u, 'snap': lambda u: 1 - (1 - u) ** 4, 'hold': lambda u: 0.0,
        'back': lambda u: 1 + 2.4 * (u - 1) ** 3 + 1.4 * (u - 1) ** 2}         # overshoot then settle


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

HERO = [K(0, 'stance'), K(18, 'bob'), K(34, 'step', dx=25), K(46, 'stance', 'back'),
        K(54, 'load', 'io'), K(60, 'slip', 'out', dx=-30), K(70, 'slip', 'io'), K(78, 'stance', 'back', dx=10),
        K(84, 'load', 'io'), K(89, 'step', 'out', dx=30), K(92, 'jab', 'snap', reach=('head', 'lhand')), K(96, 'jab', 'hold'),
        K(100, 'jab_recoil', 'out'), K(106, 'load', 'io'), K(112, 'cross', 'snap', reach=('head', 'rhand')), K(116, 'cross', 'hold'),
        K(121, 'cross_recoil', 'out'), K(132, 'stance', 'back'),
        K(140, 'crouch', 'io'), K(147, 'tuck', 'out', dx=-100, air=170, rot=120), K(158, 'tuck', 'lin', dx=-100, air=190, rot=260),
        K(169, 'land', 'in', dx=-50, rot=360), K(175, 'land2', 'out', rot=360), K(188, 'stance', 'back', rot=360, weapon=True),
        K(196, 'crouch', 'io', rot=360), K(205, 'dash', 'out', dx=110, rot=360), K(213, 'wind', 'out', dx=40, rot=360),
        K(222, 'slash', 'snap', reach=('head', 'blade'), rot=360), K(228, 'slash', 'hold', rot=360),
        K(238, 'follow', 'out', dx=30, rot=360), K(246, 'crouch', 'back', rot=360),
        K(254, 'wind', 'out', dx=165, air=150, rot=360), K(262, 'slash', 'snap', reach=('head', 'blade'), air=110, rot=360),
        K(270, 'slash', 'hold', air=110, rot=360), K(279, 'land2', 'in', dx=30, air=0, rot=360), K(287, 'follow', 'back', rot=360)]

OPP = [K(0, 'stance'), K(16, 'crouch', 'io'), K(30, 'dash', 'out', dx=50), K(37, 'land2', 'out', dx=10), K(46, 'stance', 'back', dx=10),
       K(51, 'load', 'io'), K(55, 'step', 'out', dx=90), K(58, 'jab', 'snap', reach=('head@50', 'lhand')), K(64, 'jab_recoil', 'out'),
       K(76, 'stance', 'back'),
       K(92, 'stance', 'io'), K(96, 'stance', 'hold'), K(99, 'hit_head', 'snap', dx=-10), K(104, 'hit_body', 'out', dx=-35),
       K(110, 'recover', 'io'), K(112, 'recover', 'io'), K(116, 'recover', 'hold'),
       K(119, 'hit_head', 'snap', dx=-15), K(126, 'hit_body', 'out', dx=-55), K(134, 'stagger', 'out', dx=-20), K(141, 'recover', 'back'),
       K(146, 'chamber', 'out', dx=60), K(150, 'kick', 'snap', reach=('head@138', 'rtoes')), K(160, 'chamber', 'out'), K(172, 'stance', 'back'),
       K(214, 'stance', 'io'), K(222, 'stance', 'io'), K(228, 'stance', 'hold'),
       K(231, 'hit_head', 'snap', dx=-20), K(238, 'fly', 'out', dx=-170, air=70, rot=-10), K(245, 'land2', 'in', dx=-40, rot=0),
       K(253, 'stagger', 'out', dx=-10), K(262, 'recover', 'io'), K(270, 'recover', 'hold'),
       K(274, 'hit_head', 'snap', dx=-30, air=40), K(281, 'fly', 'out', dx=-250, air=200, rot=-60), K(287, 'sprawl', 'lin', dx=-200, air=240, rot=-140)]

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

    def frames(s, n, crisp, events=()):
        """Physics playback. Every pose channel is a spring-damper chasing the keyed pose, so the body has
        mass: momentum, lag, overshoot and wobble (head and arms loose, spine heavier, legs firm). Hits and
        landings inject impulses (whiplash, recoil, knee compression). Idle phases breathe, sway and bounce.
        Strike frames and hit-stops are pinned to the keys so every contact still lands exactly."""
        names = list(STANCE) + ['x']
        raw = [s.params(f) for f in range(n)]
        A = np.array([[p[q] for q in STANCE] + [x] for p, x in raw])
        pin = np.zeros(n, bool)
        for c0, c1 in crisp:
            pin[max(0, c0 - 2):min(n, c1 + 1)] = True
        # idle life added to the targets: boxer bounce, breathing sway (fades out while airborne/flipping)
        t = np.arange(n) / 60.0; ph = 0.0 if s.d > 0 else 1.7
        calm = (A[:, names.index('air')] < 5).astype(float)
        bounce = np.sin(2 * math.pi * 1.7 * t + ph); sway = np.sin(2 * math.pi * .55 * t + ph * .6)
        T = A.copy()
        for q, amp, wave in (('lknee', 3, bounce), ('rknee', 2.5, bounce), ('lean', 1.5, sway), ('head', 2, -sway),
                             ('lsh', 2, sway), ('lel', 2, bounce)):
            T[:, names.index(q)] += amp * wave * calm
        # per-channel natural frequency (rad/s) and damping ratio
        spec = dict(sq=(26, .3), x=(16, .95), air=(60, 1.0), rot=(60, 1.0), lean=(20, .5), head=(15, .32),
                    lhip=(28, .65), rhip=(28, .65), lknee=(30, .6), rknee=(30, .6),
                    lsh=(19, .42), rsh=(19, .42), lel=(22, .4), rel=(22, .4))
        om = np.array([spec[q][0] for q in names]); ze = np.array([spec[q][1] for q in names])
        imp = {}
        for f, dv in events:
            imp.setdefault(f, []).append(dv)
        for f in range(1, n):                                             # landings compress the legs
            if A[f - 1, names.index('air')] > 20 and A[f, names.index('air')] <= 3:
                imp.setdefault(f, []).append(dict(lknee=520, rknee=480, lean=260, head=-200, sq=-4.0))
        q = T[0].copy(); v = np.zeros(len(names)); dt = 1 / 60; out = np.zeros_like(A)
        for f in range(n):
            if pin[f]:
                q = A[f].copy(); v = (A[f] - A[f - 1]) / dt if f and not pin[f - 1] else (A[f] - A[max(0, f - 1)]) / dt
            else:
                for _ in range(4):                                        # 4 substeps, semi-implicit
                    acc = om * om * (T[f] - q) - 2 * ze * om * v
                    v += acc * dt / 4; q += v * dt / 4
                for dv in imp.get(f, []):
                    for k_, val in dv.items(): v[names.index(k_)] += val
            out[f] = q
        res = []
        for f in range(n):
            p = {k_: out[f, i] for i, k_ in enumerate(names[:-1])}
            res.append(world(pose(p), out[f, -1], s.d))
        return plant_feet(np.array(res), s.d)


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
    ev = {'hero': [], 'opp': []}
    for c in CONTACTS:                                                    # hit impulses after the hit-stop
        f1 = c['c'] + 2 * c.get('hitstop', 0) + 1
        dfn = 'opp' if c['att'] == 'hero' else 'hero'; sz = c.get('size', .6)
        if c.get('evade'):
            ev[c['att']].append((f1, dict(lean=150, head=120)))          # overcommits on the miss
            continue
        ev[dfn].append((f1, dict(head=-1100 * sz, lean=-650 * sz, lsh=500 * sz, rsh=650 * sz, lel=-300 * sz,
                                 lknee=300 * sz, x=-FACE[dfn] * 900 * sz)))
        side = 'l' if c['eff'] == 'lhand' else 'r'
        ev[c['att']].append((f1, {side + 'sh': -260, side + 'el': 200, 'lean': -90, 'x': -FACE[c['att']] * 120}))
    Wd = {w: t.frames(N_FIGHT, crisp, ev[w]) for w, t in tracks.items()}
    Wd['opp'] = apply_ragdolls(Wd['opp'], FACE['opp'])                     # physical knock-backs
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


def plant_feet(Wp, d, step=55.0, dur=7, lift=26.0):
    """Weight: a grounded foot stays planted; when the body has moved too far from it, the foot takes a
    quick step (small lift arc) to where the pose wants it. Knees re-solved with 2-bone IK (knee forward)."""
    Wp = Wp.copy(); n = len(Wp)
    l1, l2 = L['thigh'], L['shin']
    for s_ in 'lr':
        hi, kn, an = I[s_ + 'hipjoint'], I[s_ + 'femur'], I[s_ + 'tibia']
        tgt, stp = None, None
        for f in range(n):
            P = Wp[f]; a = P[an, :2].copy()
            if a[1] > 46:                                              # airborne / flipping: foot follows the pose
                tgt, stp = None, None; continue
            if tgt is None:
                tgt = a.copy(); continue
            if stp is None and abs(a[0] - tgt[0]) > step:
                stp = (f, tgt.copy())
            if stp is not None:
                u = min(1.0, (f - stp[0]) / dur); e = u * u * (3 - 2 * u)
                tgt = stp[1] + (a - stp[1]) * e; tgt = tgt + [0, lift * math.sin(math.pi * u)]
                if u >= 1: tgt = a.copy(); stp = None
            H = P[hi, :2]; v = tgt - H; D = max(min(np.linalg.norm(v), l1 + l2 - .5), abs(l1 - l2) + .5)
            v = v / max(np.linalg.norm(v), 1e-6)
            nrm = np.array([-v[1], v[0]])
            if nrm[0] * d < 0: nrm = -nrm                               # knee bends toward the facing side
            x = (l1 * l1 - l2 * l2 + D * D) / (2 * D); y = math.sqrt(max(l1 * l1 - x * x, 0))
            K_ = H + v * x + nrm * y; A_ = H + v * D
            delta = A_ - a
            P[kn, :2] = K_; P[an, :2] = A_
            for j in (I[s_ + 'foot'], I[s_ + 'toes']): P[j, :2] += delta
    return Wp


# ---------------------------------------------------------------- ragdoll (pymunk) for knock-backs
RAGDOLLS = [  # (start frame, end frame, push velocity (x toward +x for the opponent), spin, blend-back frames)
    dict(start=229, end=242, push=(1150, 620), spin=-3.5, blend=14),
    dict(start=271, end=288, push=(1650, 1250), spin=-6.0, blend=0),
]


def ragdoll(P0, Pprev, push, spin, n, seed=0):
    """Simulate a limp stickman from pose P0 (with velocity from Pprev) for n frames: gravity, ground
    contact, joint limits and weak muscle springs. Returns n poses in the 31-joint layout."""
    import pymunk
    sp = pymunk.Space(); sp.gravity = (0, -2900); sp.iterations = 30
    g = pymunk.Segment(sp.static_body, (-8000, 0), (8000, 0), 4); g.friction = .9; g.elasticity = .15; sp.add(g)
    J = lambda n_: P0[I[n_], :2]; V = (P0[:, :2] - Pprev[:, :2]) * 60
    vel = lambda n_: V[I[n_]] + np.array(push)
    bodies = {}

    def seg(name, a, b, m, va, vb):
        a, b = np.asarray(a, float), np.asarray(b, float); c = (a + b) / 2
        bd = pymunk.Body(m, pymunk.moment_for_segment(m, tuple(a - c), tuple(b - c), 8))
        bd.position = tuple(c); bd.velocity = tuple((va + vb) / 2)
        sh = pymunk.Segment(bd, tuple(a - c), tuple(b - c), 8); sh.friction = .8; sh.filter = pymunk.ShapeFilter(group=1)
        sp.add(bd, sh); bodies[name] = (bd, a - c, b - c)
        return bd
    torso = seg('torso', J('root'), J('lowerneck'), 10, vel('root'), vel('lowerneck'))
    torso.angular_velocity = spin
    hcen = head_center(P0)
    hb = pymunk.Body(4, pymunk.moment_for_circle(4, 0, HEAD_R * .8)); hb.position = tuple(hcen); hb.velocity = tuple(vel('head'))
    hs = pymunk.Circle(hb, HEAD_R * .8); hs.friction = .8; hs.filter = pymunk.ShapeFilter(group=1); sp.add(hb, hs)

    def pivot(a, b, at, lim=None, k=4e4):
        sp.add(pymunk.PivotJoint(a, b, tuple(at)))
        rel = b.angle - a.angle
        if lim is not None: sp.add(pymunk.RotaryLimitJoint(a, b, rel + lim[0], rel + lim[1]))
        sp.add(pymunk.DampedRotarySpring(a, b, rel, k, k * .05))
    pivot(torso, hb, J('lowerneck'), (-.6, .6), 2e5)
    for s_ in 'lr':
        ua = seg(s_ + 'ua', J(s_ + 'clavicle'), J(s_ + 'humerus'), 1.6, vel(s_ + 'clavicle'), vel(s_ + 'humerus'))
        fa = seg(s_ + 'fa', J(s_ + 'humerus'), J(s_ + 'hand'), 1.1, vel(s_ + 'humerus'), vel(s_ + 'hand'))
        th = seg(s_ + 'th', J(s_ + 'hipjoint'), J(s_ + 'femur'), 4, vel(s_ + 'hipjoint'), vel(s_ + 'femur'))
        sh_ = seg(s_ + 'sh', J(s_ + 'femur'), J(s_ + 'tibia'), 3, vel(s_ + 'femur'), vel(s_ + 'tibia'))
        pivot(torso, ua, J(s_ + 'clavicle'), None, 1.5e4); pivot(ua, fa, J(s_ + 'humerus'), (-1.4, 1.4), 1e4)
        pivot(torso, th, J(s_ + 'hipjoint'), (-1.6, 1.6), 6e4); pivot(th, sh_, J(s_ + 'femur'), (-1.5, 1.5), 4e4)
    rest = {s_: (P0[I[s_ + 'foot'], :2] - J(s_ + 'tibia'), P0[I[s_ + 'toes'], :2] - J(s_ + 'tibia')) for s_ in 'lr'}
    a0 = {s_: bodies[s_ + 'sh'][0].angle for s_ in 'lr'}
    out = []
    for _ in range(n):
        for _ in range(10): sp.step(1 / 600)
        P = P0.copy()
        W_ = lambda name, end: np.array(bodies[name][0].local_to_world(tuple(bodies[name][1 if end == 0 else 2])))
        r, nk = W_('torso', 0), W_('torso', 1)
        for nm, u in (('root', 0), ('lowerback', .3), ('upperback', .6), ('thorax', .93)): P[I[nm], :2] = r + (nk - r) * u
        P[I['lowerneck'], :2] = nk
        hc = np.array(hb.position); dv = (hc - nk) / max(np.linalg.norm(hc - nk), 1e-6)
        P[I['upperneck'], :2] = nk + dv * 14; P[I['head'], :2] = nk + dv * 92
        for s_ in 'lr':
            c_, e_, h_ = W_(s_ + 'ua', 0), W_(s_ + 'ua', 1), W_(s_ + 'fa', 1)
            fd = (h_ - e_) / max(np.linalg.norm(h_ - e_), 1e-6)
            P[I[s_ + 'clavicle'], :2] = c_; P[I[s_ + 'humerus'], :2] = e_; P[I[s_ + 'hand'], :2] = h_
            P[I[s_ + 'radius'], :2] = h_ - fd * 26; P[I[s_ + 'wrist'], :2] = h_ - fd * 16
            P[I[s_ + 'fingers'], :2] = h_ + fd * 6; P[I[s_ + 'thumb'], :2] = h_ - fd * 14
            hp, kn, an = W_(s_ + 'th', 0), W_(s_ + 'th', 1), W_(s_ + 'sh', 1)
            P[I[s_ + 'hipjoint'], :2] = hp; P[I[s_ + 'femur'], :2] = kn; P[I[s_ + 'tibia'], :2] = an
            da = bodies[s_ + 'sh'][0].angle - a0[s_]; ca, sa = math.cos(da), math.sin(da)
            for j, off in zip(('foot', 'toes'), rest[s_]):
                P[I[s_ + j], :2] = an + np.array([off[0] * ca - off[1] * sa, off[0] * sa + off[1] * ca])
        out.append(P)
    return np.array(out)


def apply_ragdolls(A, d):
    A = A.copy()
    for r in RAGDOLLS:
        s0, e = r['start'], min(r['end'], len(A))
        push = (r['push'][0] * -d, r['push'][1])
        R = ragdoll(A[s0], A[s0 - 1], push, r['spin'] * -d, e - s0)
        keyed = A.copy()
        A[s0:e] = R
        for i in range(r['blend']):                                         # recover: blend back into the keyed motion
            f = e + i
            if f >= len(A): break
            u = (i + 1) / (r['blend'] + 1); u = u * u * (3 - 2 * u)
            off = R[-1][0] - keyed[e - 1][0]; off[1] = 0                     # carry the ragdoll's landing spot
            A[f] = (R[-1] + (keyed[f] + off * (1 - u) - R[-1]) * u) if False else R[-1] * (1 - u) + (keyed[f] + off * (1 - u)) * u
    return A
