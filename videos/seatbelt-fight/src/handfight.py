"""Hand-keyed stickman fight (replaces the mocap pipeline for pixel6).

Both fighters are animated pose-to-pose: every key is a hand-placed pose (joint angles) with its own easing,
holds for hit-stop, and anticipation / follow-through keys. Strike keys marked `reach` are solved so the
fist, foot or blade tip lands exactly on the target at the contact frame. Output: per-frame joint arrays in
the 31-joint layout the renderer uses (60 fps, hit-stops baked in as holds).

Compact stickman proportions: ~620 units tall, big round head (radius 70, ~23 % of the height).
Angles in degrees: limbs from straight down (+ = forward / up), spine from vertical (+ = leaning forward),
'rot' rolls the whole body (+ = backward flip). 'dx' moves the fighter toward the opponent.
"""
import math
import numpy as np

NAMES = ['root', 'lhipjoint', 'lfemur', 'ltibia', 'lfoot', 'ltoes', 'rhipjoint', 'rfemur', 'rtibia', 'rfoot', 'rtoes',
         'lowerback', 'upperback', 'thorax', 'lowerneck', 'upperneck', 'head', 'lclavicle', 'lhumerus', 'lradius',
         'lwrist', 'lhand', 'lfingers', 'lthumb', 'rclavicle', 'rhumerus', 'rradius', 'rwrist', 'rhand', 'rfingers', 'rthumb']
I = {n: i for i, n in enumerate(NAMES)}
HEAD_R, FIG, BLADE = 70.0, 620.0, 250.0
L = dict(hip=20, thigh=150, shin=145, foot=40, lb=60, ub=60, th=55, ln=10, un=16, head=90, upper=118, fore=108, hand=34)

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
        ft = an + fd * L['foot'] + [0, -10]; to = ft + fd * 16
        put(s + 'hipjoint', hip, 24 * z); put(s + 'femur', kn, 36 * z); put(s + 'tibia', an, 44 * z)
        put(s + 'foot', ft, 46 * z); put(s + 'toes', to, 46 * z)
        sh = th + [0, -6]; ua = k[s + 'sh']; fa = ua + k[s + 'el']
        el = sh + down(ua) * L['upper']; wr = el + down(fa) * L['fore']
        put(s + 'clavicle', sh, 36 * z); put(s + 'humerus', el, 42 * z); put(s + 'radius', wr, 38 * z)
        put(s + 'wrist', wr + down(fa) * 10, 38 * z); put(s + 'hand', wr + down(fa) * L['hand'], 38 * z)
        put(s + 'fingers', wr + down(fa) * (L['hand'] + 6), 38 * z); put(s + 'thumb', wr + down(fa + 30) * 10, 34 * z)
    r = k.get('rot', 0) % 360
    if abs(r) > 1e-6:
        c = P[I['lowerback'], :2].copy(); a = math.radians(r); ca, sa = math.cos(a), math.sin(a)
        v = P[:, :2] - c
        P[:, 0] = c[0] + v[:, 0] * ca - v[:, 1] * sa; P[:, 1] = c[1] + v[:, 0] * sa + v[:, 1] * ca
        low = P[:, 1].min() - 30
    else:
        low = min(P[I['ltibia'], 1], P[I['rtibia'], 1])
    P[:, 1] += 30 - low + k['air']
    P[:, 1] = np.maximum(P[:, 1], 0)
    return P


EASE = {'io': lambda u: u * u * (3 - 2 * u), 'in': lambda u: u ** 3, 'out': lambda u: 1 - (1 - u) ** 3,
        'lin': lambda u: u, 'snap': lambda u: 1 - (1 - u) ** 4, 'hold': lambda u: 0.0}


def K(f, name, ease='io', **kw):
    d = dict(STANCE); d.update(POSES[name]); d.update({k: v for k, v in kw.items() if k in STANCE})
    return dict(f=f, ease=ease, pose=d, dx=kw.get('dx', 0.0), reach=kw.get('reach'), weapon=kw.get('weapon'))


# ---------------------------------------------------------------- the choreography (60 fps output frames)
# Contacts: frame, attacker, effector, target, hit-stop (30 fps frames, held x2), effect.
CONTACTS = [
    dict(beat=2, c=22, att='opp', eff='lhand', target='head', evade=True, label='opponent jab, hero slips'),
    dict(beat=3, c=34, att='hero', eff='lhand', target='head', hitstop=2, size=.7, fx='spark', label='hero jab'),
    dict(beat=4, c=50, att='hero', eff='rhand', target='head', hitstop=2, size=.8, fx='spark', label='hero cross'),
    dict(beat=5, c=78, att='opp', eff='rtoes', target='head', evade=True, label='opponent kick, hero backflips out'),
    dict(beat=7, c=122, att='hero', eff='blade', target='head', hitstop=3, size=1.0, fx='fire', weapon=True, label='dash-in blade slash'),
    dict(beat=8, c=168, att='hero', eff='rtoes', target='head', hitstop=3, size=1.0, fx='fire', label='leaping aerial kick'),
    dict(beat=9, c=204, att='opp', eff='rhand', target='rhand', hitstop=2, size=.6, fx='spark', label='opponent lunge, blade block'),
    dict(beat=10, c=238, att='hero', eff='blade', target='head', hitstop=4, size=1.6, fx='fire', weapon=True, finisher=True,
         label='FINISHER: slide in, rising blade slash'),
]

HERO = [K(0, 'stance'), K(10, 'bob'), K(16, 'stance'),
        K(20, 'slip', 'snap', dx=-30), K(28, 'stance', 'io', dx=10),
        K(31, 'crouch', 'out'), K(34, 'jab', 'snap', reach=('head', 'lhand')), K(38, 'jab', 'hold'), K(44, 'stance', 'out'),
        K(46, 'crouch', 'out', dx=10), K(50, 'cross', 'snap', reach=('head', 'rhand')), K(54, 'cross', 'hold'), K(62, 'stance', 'out'),
        K(70, 'crouch', 'out'),
        K(78, 'tuck', 'lin', dx=-150, air=200, rot=140), K(86, 'tuck', 'lin', dx=-120, air=220, rot=290),
        K(94, 'land', 'in', dx=-60, rot=360), K(102, 'stance', 'io', rot=360),
        K(106, 'crouch', 'out', rot=360, weapon=True), K(113, 'dash', 'snap', dx=190, rot=360), K(117, 'wind', 'out', dx=40, rot=360),
        K(122, 'slash', 'snap', reach=('head', 'blade'), rot=360), K(128, 'slash', 'hold', rot=360),
        K(136, 'follow', 'out', dx=20, rot=360), K(146, 'stance', 'io', rot=360, weapon=False),
        K(152, 'crouch', 'out', rot=360), K(160, 'tuck', 'out', dx=400, air=210, rot=360),
        K(168, 'airkick', 'snap', reach=('head', 'rtoes'), air=230, rot=360), K(174, 'airkick', 'hold', air=230, rot=360),
        K(184, 'land', 'in', dx=40, rot=360), K(192, 'stance', 'io', rot=360),
        K(197, 'stance', 'io', rot=360, weapon=True), K(202, 'block', 'snap', rot=360), K(208, 'block', 'hold', rot=360),
        K(212, 'crouch', 'out', dx=-10, rot=360), K(221, 'slide', 'out', dx=110, rot=360), K(228, 'crouch', 'out', dx=40, rot=360),
        K(232, 'wind', 'out', dx=10, rot=360), K(238, 'slash', 'snap', reach=('head', 'blade'), rot=360), K(246, 'slash', 'hold', rot=360),
        K(256, 'follow', 'out', dx=30, rot=360), K(270, 'stance', 'io', rot=360), K(287, 'bob', 'io', rot=360)]

OPP = [K(0, 'stance'), K(4, 'crouch', 'out'), K(12, 'dash', 'snap', dx=170), K(17, 'stance', 'out', dx=20),
       K(22, 'jab', 'snap', reach=('head@16', 'lhand')), K(28, 'stance', 'out'),
       K(34, 'stance', 'hold'), K(38, 'stance', 'hold'), K(43, 'hit', 'snap', dx=-50), K(48, 'stance', 'io', dx=-10),
       K(50, 'stance', 'hold'), K(54, 'stance', 'hold'), K(59, 'stagger', 'snap', dx=-60), K(64, 'stance', 'io'),
       K(71, 'chamber', 'out', dx=50), K(78, 'kick', 'snap', reach=('head@70', 'rtoes')), K(86, 'chamber', 'out'), K(95, 'stance', 'io', dx=10),
       K(116, 'stance', 'io'), K(122, 'stance', 'hold'), K(128, 'stance', 'hold'),
       K(135, 'fly', 'out', dx=-250, air=110, rot=-15), K(143, 'land', 'in', dx=-70, rot=0), K(154, 'stance', 'io'),
       K(162, 'stance', 'io', dx=10), K(168, 'stance', 'hold'), K(174, 'stance', 'hold'),
       K(180, 'hit', 'snap', dx=-90), K(188, 'stagger', 'out', dx=-30), K(195, 'stance', 'io'),
       K(199, 'crouch', 'out', dx=20), K(204, 'lunge', 'snap', reach=('rhand', 'rhand')), K(208, 'lunge', 'hold'),
       K(215, 'stance', 'out', dx=-90), K(224, 'crouch', 'io', dx=-210), K(230, 'stance', 'io'), K(238, 'stance', 'hold'), K(246, 'stance', 'hold'),
       K(252, 'fly', 'out', dx=-320, air=230, rot=-50), K(264, 'sprawl', 'lin', dx=-330, air=280, rot=-130),
       K(278, 'sprawl', 'in', dx=-300, air=150, rot=-220), K(287, 'sprawl', 'in', dx=-200, air=0, rot=-280)]

START = {'hero': -260.0, 'opp': 330.0}
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

    def at(s, f):
        ks, xs = s.keys, s.xs()
        j = max(i for i, k in enumerate(ks) if k['f'] <= f) if f >= ks[0]['f'] else 0
        if j == len(ks) - 1 or f <= ks[0]['f']:
            p, x = ks[j]['pose'], xs[j]
        else:
            a, b = ks[j], ks[j + 1]
            u = EASE[b['ease']]((f - a['f']) / max(b['f'] - a['f'], 1e-6))
            p = {q: a['pose'][q] + (b['pose'][q] - a['pose'][q]) * u for q in a['pose']}
            x = xs[j] + (xs[j + 1] - xs[j]) * u
        return world(pose(p), x, s.d)


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
    Wd = {w: np.array([t.at(f) for f in range(N_FIGHT)]) for w, t in tracks.items()}
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
