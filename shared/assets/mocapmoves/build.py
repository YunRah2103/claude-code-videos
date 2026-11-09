"""Build the retargeted fight-move library from CMU mocap (see INDEX.md).

Each move -> <name>.npz: Q[frames, 31, 3] at 120 fps in a canonical frame
(x = facing forward, y = up with ground at 0, z = lateral; root starts at x=z=0),
retargeted onto the flat-figure proportions below, plus its key time (contact /
duck bottom / slip apex / block apex / reaction onset).
Raw clips: videos/seatbelt-fight/src/get_mocap.sh -> out/mocap-cmu (not committed).
Usage: python shared/assets/mocapmoves/build.py [MOCAP_DIR]
"""
import os, sys
import numpy as np
from scipy.ndimage import gaussian_filter1d

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from amc import joints  # noqa: E402

FPS = 120
SRC_FPS = {'88': 60}   # subject 88 was captured at 60 fps
SIDE = dict(hipjoint=45, femur=195, tibia=190, foot=58, toes=26, clavicle=52, humerus=150, radius=140,
            wrist=16, hand=44, fingers=8, thumb=8)
CENTRE = dict(lowerback=85, upperback=85, thorax=80, lowerneck=14, upperneck=16, head=124)

# name, kind, clip, t0, t1, effector (attacks) / key rule
MOVES = [
    ('ready', 'stance', '14_01', 22.40, 23.05, None),
    ('step_in', 'step', '14_03', 19.85, 20.30, None),
    ('step_back', 'step', '14_03', 21.15, 21.65, None),
    ('jab', 'attack', '14_03', 3.50, 4.20, 'lhand'),
    ('cross', 'attack', '14_03', 14.30, 15.00, 'rhand'),
    ('hook', 'attack', '14_03', 11.50, 12.30, 'rhand'),
    ('roundhouse', 'attack', '135_07', 0.30, 1.60, 'rtoes'),
    ('knee', 'attack', '86_06', 16.25, 16.90, 'rfemur'),
    ('spin_kick', 'attack', '88_06', 0.30, 1.75, 'rtoes'),
    ('lunge_punch', 'attack', '135_09', 1.80, 3.00, 'rhand'),
    ('slip', 'defence', '13_17', 20.10, 20.80, 'slip'),
    ('duck', 'defence', '14_01', 22.95, 23.65, 'duck'),
    ('block', 'defence', '144_26', 3.90, 4.70, 'block'),
    ('stagger', 'reaction', '91_59', 0.40, 1.90, 0.75),        # reactions: onset search limit (s into window)
    ('knock_back', 'reaction', '104_13', 3.30, 4.58, 0.60),
    ('fall', 'reaction', '90_18', 0.60, 3.25, 0.55),
]


def blen(n):
    return SIDE[n[1:]] if n[0] in 'lr' and n[1:] in SIDE else CENTRE[n]


def retarget(P, names, par):
    I = {n: i for i, n in enumerate(names)}
    leg = np.mean([np.linalg.norm(P[:, I[k + 'femur']] - P[:, I[k + 'hipjoint']], axis=1).mean() +
                   np.linalg.norm(P[:, I[k + 'tibia']] - P[:, I[k + 'femur']], axis=1).mean() for k in 'lr'])
    Q = np.zeros_like(P); Q[:, 0] = P[:, 0] * (SIDE['femur'] + SIDE['tibia']) / leg
    for j in range(1, len(names)):
        d = P[:, j] - P[:, par[j]]; n = np.linalg.norm(d, axis=1, keepdims=True)
        Q[:, j] = Q[:, par[j]] + np.where(n > 1e-6, d / np.maximum(n, 1e-6), 0) * blen(names[j])
    return Q


def hip_facing(Q, I, f0, f1):
    v = (Q[f0:f1, I['rhipjoint']] - Q[f0:f1, I['lhipjoint']]).mean(0)
    v = np.cross([0, 1, 0], v); v[1] = 0
    return v / np.linalg.norm(v)


def key_time(kind, rule, Q, I):
    if kind == 'attack':
        e = I[rule]
        v = np.linalg.norm(np.diff(Q[:, e], axis=0), axis=1)
        p = int(np.argmax(v))
        base = I['thorax'] if 'hand' in rule else I['root']
        reach = np.linalg.norm(Q[:, e] - Q[:, base], axis=1)
        return (p + int(np.argmax(reach[p:p + int(0.15 * FPS)]))) / FPS
    if rule == 'duck':
        return int(np.argmin(Q[:, I['head'], 1])) / FPS
    if rule == 'slip':
        lat = np.abs(Q[:, I['head'], 2] - Q[:, 0, 2])
        return int(np.argmax(lat)) / FPS
    if rule == 'block':
        return int(np.argmax(np.maximum(Q[:, I['lhand'], 1], Q[:, I['rhand'], 1]))) / FPS
    return 0.0


def build_move(name, kind, clip, t0, t1, rule, src):
    s = clip.split('_')[0]
    names, P, par = joints(os.path.join(src, s + '.asf'), os.path.join(src, clip + '.amc'))
    I = {n: i for i, n in enumerate(names)}
    fps = SRC_FPS.get(s, 120)
    P = P[int(t0 * fps):int(t1 * fps) + 1]
    if fps != FPS:  # resample to 120 fps
        x = np.arange(len(P)); xi = np.linspace(0, len(P) - 1, int((len(P) - 1) * FPS / fps) + 1)
        P = np.stack([np.stack([np.interp(xi, x, P[:, j, k]) for k in range(3)], -1) for j in range(P.shape[1])], 1)
    P = gaussian_filter1d(P, 1.0, axis=0)                                   # low-pass jitter
    Q = retarget(P, names, par)
    if kind == 'reaction':
        # onset = head starts to whip relative to the pelvis; orient so the head is driven backwards
        hv = np.linalg.norm(np.diff(Q[:, I['head']] - Q[:, 0], axis=0), axis=1)
        pk = int(np.argmax(hv[:int(rule * FPS)])); on = pk
        while on > 0 and hv[on] > 0.12 * hv[pk]:
            on -= 1
        Q = Q[on:]
        T = Q[min(int(0.5 * FPS), len(Q) - 1), I['head']] - Q[0, I['head']]; T[1] = 0
        fwd = -T / np.linalg.norm(T)
    else:
        fwd = hip_facing(Q, I, 0, 6)
    side = np.cross(fwd, [0, 1, 0])
    root0 = Q[0, 0].copy(); root0[1] = 0
    C = np.stack([(Q - root0) @ fwd, Q[..., 1], (Q - root0) @ side], -1)
    anks = np.minimum(C[:, I['ltibia'], 1], C[:, I['rtibia'], 1])
    gwin = anks[:max(12, len(anks) // 4)] if kind == 'reaction' else anks
    C[..., 1] -= np.percentile(gwin, 10) - 40        # planted ankle sits 40 px above the ground
    key = key_time(kind, rule, C, I)
    meta = dict(name=name, kind=kind, clip=clip, t0=t0, t1=t1, effector=rule if kind == 'attack' else '',
                key=key, dur=(len(C) - 1) / FPS)
    return C.astype(np.float32), names, par, meta


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, '../../../out/mocap-cmu')
    rows = []
    for m in MOVES:
        C, names, par, meta = build_move(*m, src)
        np.savez_compressed(os.path.join(HERE, meta['name'] + '.npz'), Q=C, names=np.array(names),
                            parents=np.array(par), **{k: np.array(v) for k, v in meta.items()})
        rows.append(meta)
        print('%-12s %-8s %-7s %5.2f-%5.2fs key %.3fs dur %.2fs %s' % (
            meta['name'], meta['kind'], meta['clip'], meta['t0'], meta['t1'], meta['key'], meta['dur'], meta['effector']))
    return rows


if __name__ == '__main__':
    main()
