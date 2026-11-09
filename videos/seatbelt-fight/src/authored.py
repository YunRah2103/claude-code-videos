"""Authored acrobatic moves (pose-to-pose joint-angle keys with easing) in the mocap library's format.

Each move is sampled at 120 fps into Q[frames, 31, 3] on the same skeleton and bone lengths as the CMU
moves (shared/assets/mocapmoves/build.py), so fight6's compose/blend/plant/IK treat them like mocap.
Canonical frame: x forward, y up (ground 0, planted ankle at 40), z lateral; left leg/hand lead.
Pose keys are angles in degrees, measured from straight down for limbs (+ = forward/up) and from vertical
for the spine (+ = leaning forward); 'rot' rolls the whole body (+ = backward, for the flip).
"""
import math
import numpy as np

SIDE = dict(hipjoint=45, femur=195, tibia=190, foot=58, toes=26, clavicle=52, humerus=150, radius=140,
            wrist=16, hand=44, fingers=8, thumb=8)
NAMES = ['root', 'lhipjoint', 'lfemur', 'ltibia', 'lfoot', 'ltoes', 'rhipjoint', 'rfemur', 'rtibia', 'rfoot', 'rtoes',
         'lowerback', 'upperback', 'thorax', 'lowerneck', 'upperneck', 'head', 'lclavicle', 'lhumerus', 'lradius',
         'lwrist', 'lhand', 'lfingers', 'lthumb', 'rclavicle', 'rhumerus', 'rradius', 'rwrist', 'rhand', 'rfingers', 'rthumb']
PARENTS = [-1, 0, 1, 2, 3, 4, 0, 6, 7, 8, 9, 0, 11, 12, 13, 14, 15, 13, 17, 18, 19, 20, 21, 20, 13, 24, 25, 26, 27, 28, 27]
I = {n: i for i, n in enumerate(NAMES)}

STANCE = dict(x=0, air=0, lean=12, head=-8, rot=0,
              lhip=24, lknee=30, rhip=-22, rknee=26,
              lsh=40, lel=85, rsh=22, rel=110)


def down(a):
    a = math.radians(a); return np.array([math.sin(a), -math.cos(a)])


def pose(k):
    """Joint positions from an angle key (sagittal FK + lateral offsets), grounded automatically."""
    P = np.zeros((31, 3))
    u = -down(k['lean'])                                   # spine up-vector
    def put(n, xy, z=0.0): P[I[n]] = [xy[0], xy[1], z]
    root = np.array([0.0, 0.0])
    put('root', root)
    lb = root + u * 85; ub = lb + u * 85; th = ub + u * 80; ln = th + u * 14; un = ln + u * 16
    hu = -down(k['lean'] + k['head'])
    put('lowerback', lb); put('upperback', ub); put('thorax', th); put('lowerneck', ln); put('upperneck', un)
    put('head', un + hu * 124)
    for s, z in (('l', -1), ('r', 1)):
        hip = root + np.array([0, -30.0])
        thigh = k[s + 'hip']; shin = thigh - k[s + 'knee']
        kn = hip + down(thigh) * 195; an = kn + down(shin) * 190
        fdir = np.array([math.cos(math.radians(shin * .4)), math.sin(math.radians(shin * .4))])
        ft = an + fdir * 58 + np.array([0, -14.0]); to = ft + fdir * 26
        put(s + 'hipjoint', hip, 31 * z); put(s + 'femur', kn, 48 * z); put(s + 'tibia', an, 60 * z)
        put(s + 'foot', ft, 64 * z); put(s + 'toes', to, 64 * z)
        sh = th + np.array([0, -8.0]); ua = k[s + 'sh']; fa = ua + k[s + 'el']
        el = sh + down(ua) * 150; wr = el + down(fa) * 140
        wx, hd = wr + down(fa) * 16, wr + down(fa) * 60
        put(s + 'clavicle', sh, 48 * z); put(s + 'humerus', el, 56 * z); put(s + 'radius', wr, 50 * z)
        put(s + 'wrist', wx, 50 * z); put(s + 'hand', hd, 50 * z); put(s + 'fingers', hd + down(fa) * 8, 50 * z)
        put(s + 'thumb', wx + down(fa + 30) * 10, 46 * z)
    r = k.get('rot', 0) % 360
    if abs(r) > 1e-6:                                      # whole-body roll about the waist (flip)
        c = P[I['lowerback'], :2].copy(); a = math.radians(r); ca, sa = math.cos(a), math.sin(a)
        v = P[:, :2] - c
        P[:, 0] = c[0] + v[:, 0] * ca - v[:, 1] * sa; P[:, 1] = c[1] + v[:, 0] * sa + v[:, 1] * ca
    low = min(P[I['ltibia'], 1], P[I['rtibia'], 1]) if abs(r) < 1e-6 else P[:, 1].min() - 40
    P[:, 1] += 40 - low + k['air']
    P[:, 0] += k['x']
    return P


EASE = {'io': lambda u: u * u * (3 - 2 * u), 'in': lambda u: u ** 3, 'out': lambda u: 1 - (1 - u) ** 3,
        'lin': lambda u: u, 'snap': lambda u: 1 - (1 - u) ** 4}


class AMove:
    def __init__(s, name, kind, eff, keyt, keys):
        s.name, s.kind, s.eff, s.key = name, kind, eff, keyt
        s.dur = keys[-1][0]
        s.names, s.par = NAMES, PARENTS
        K = []
        acc = dict(STANCE)
        for t, e, d in keys:
            acc = dict(acc); acc.update(d); K.append((t, e, acc))
        n = int(round(s.dur * 120)) + 1
        Q = np.zeros((n, 31, 3))
        for i in range(n):
            t = i / 120
            j = max(0, max(jj for jj in range(len(K)) if K[jj][0] <= t + 1e-9))
            if j == len(K) - 1:
                k = K[j][2]
            else:
                (t0, _, a), (t1, e, b) = K[j], K[j + 1]
                u = EASE[e]((t - t0) / max(t1 - t0, 1e-6))
                k = {q: a[q] + (b[q] - a[q]) * u for q in a}
            Q[i] = pose(k)
        Q[:, :, 0] -= Q[0, 0, 0]
        s.Q = Q


def library():
    S = {}
    S['dash_in'] = AMove('dash_in', 'step', 'rhand', 0.0, [
        (0.00, 'io', {}),
        (0.08, 'out', dict(lean=34, lknee=62, rknee=58, lhip=30, rhip=-10, lsh=10, rsh=-10)),
        (0.26, 'snap', dict(x=520, lean=46, lhip=62, lknee=22, rhip=-48, rknee=78, lsh=-45, lel=30, rsh=-60, rel=25)),
        (0.36, 'out', dict(x=590, lean=24, lhip=36, lknee=40, rhip=-26, rknee=40, lsh=30, lel=70, rsh=10, rel=90)),
        (0.46, 'io', dict(STANCE, x=600))])
    S['spin_slash'] = AMove('spin_slash', 'attack', 'rhand', 0.22, [
        (0.00, 'io', {}),
        (0.12, 'out', dict(x=30, lean=-8, head=-14, rsh=205, rel=15, lsh=70, lel=40, lknee=40, rknee=34)),   # blade cocked high behind
        (0.22, 'snap', dict(x=130, lean=32, head=0, rsh=55, rel=0, lsh=-20, lel=20, lhip=48, lknee=22, rhip=-34, rknee=20)),
        (0.36, 'out', dict(x=150, lean=40, rsh=-35, rel=10, lsh=-30)),                                           # follow-through
        (0.60, 'io', dict(STANCE, x=150))])
    S['aerial_kick'] = AMove('aerial_kick', 'attack', 'rtoes', 0.42, [
        (0.00, 'io', {}),
        (0.12, 'out', dict(lean=28, lknee=70, rknee=70, lsh=0, rsh=-20)),
        (0.30, 'out', dict(x=200, air=230, lean=10, lhip=70, lknee=110, rhip=60, rknee=100, lsh=60, rsh=40)),
        (0.42, 'snap', dict(x=290, air=250, lean=-28, head=10, rhip=98, rknee=0, lhip=30, lknee=95, lsh=-30, rsh=80, rel=40)),
        (0.62, 'in', dict(x=350, air=0, lean=26, lhip=40, lknee=70, rhip=-10, rknee=70, lsh=30, rsh=10)),
        (0.80, 'io', dict(STANCE, x=360))])
    S['leap'] = AMove('leap', 'step', 'rhand', 0.0, [
        (0.00, 'io', {}),
        (0.12, 'out', dict(lean=30, lknee=75, rknee=75)),
        (0.36, 'out', dict(x=260, air=280, lean=20, lhip=80, lknee=120, rhip=50, rknee=120, lsh=120, rsh=100)),
        (0.58, 'in', dict(x=450, air=0, lean=30, lknee=70, rknee=60)),
        (0.72, 'io', dict(STANCE, x=460))])
    S['slide'] = AMove('slide', 'step', 'ltoes', 0.0, [
        (0.00, 'io', {}),
        (0.10, 'out', dict(lean=30, lknee=60, rknee=60)),
        (0.30, 'out', dict(x=380, lean=-40, lhip=82, lknee=4, rhip=10, rknee=130, lsh=-30, rsh=60, rel=30)),
        (0.48, 'out', dict(x=470, lean=-30, lhip=80, lknee=6, rhip=14, rknee=128)),
        (0.70, 'io', dict(STANCE, x=480))])
    S['backflip_dodge'] = AMove('backflip_dodge', 'defence', 'rhand', 0.30, [
        (0.00, 'io', {}),
        (0.10, 'out', dict(lean=26, lknee=70, rknee=70, lsh=-30, rsh=-30)),
        (0.30, 'lin', dict(x=-170, air=210, rot=150, lean=0, lhip=95, lknee=120, rhip=90, rknee=120, lsh=140, rsh=140)),
        (0.46, 'out', dict(x=-310, air=230, rot=300)),
        (0.58, 'in', dict(x=-380, air=0, rot=360, lean=30, lhip=40, lknee=70, rhip=-10, rknee=70, lsh=40, rsh=30)),
        (0.74, 'io', dict(STANCE, x=-390, rot=360))])
    return S
