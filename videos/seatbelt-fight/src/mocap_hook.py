"""3-second motion-capture fight hook test (CMU mocap -> flat 2D figures).

Hero: CMU 14_01 (boxing: duck, then straight right). Opponent: CMU 14_02 (boxing take,
throws a punch) until the impact frame, then CMU 90_18 (RugPullFall) as the knock-down reaction.
Pipeline: ASF/AMC FK -> low-pass -> retarget bone directions onto our proportions ->
foot-plant lock (2-bone IK) -> three-quarter orthographic projection -> time remap
(anticipation slow-down, hit-stop) -> camera -> render.
Usage: bash get_mocap.sh; python mocap_hook.py [--frames 0,40,...]
"""
import math, os, subprocess, sys
import numpy as np, cairo, cv2
from scipy.ndimage import gaussian_filter1d

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import hook, mocap  # noqa: E402
from hook import C, blob, PAL, over, surf_to_np, layer_matrix, make_layers, draw_ground, SC, ease  # noqa: E402

W, H, FPS, NF, SRC = 1080, 1920, 60, 180, 120
OUT = hook.OUT
MOCAP = os.environ.get('MOCAP_DIR', os.path.join(hook.ROOT, 'out/mocap-cmu'))
FI, HS, SLOW = 75, 3, 0.6          # impact output frame, hit-stop frames, slow factor for 6 frames before
FLASH = {FI: 0.62, FI + 1: 0.22}
THETA = math.radians(22)           # three-quarter view angle
R_HEAD = 62
KNOCK = 260                        # px; the only non-mocap motion layer (see MOCAP.md)
SIDE = dict(hipjoint=45, femur=195, tibia=190, foot=58, toes=26, clavicle=52, humerus=150, radius=140,
            wrist=16, hand=44, fingers=8, thumb=8)
CENTRE = dict(lowerback=85, upperback=85, thorax=80, lowerneck=14, upperneck=16, head=124)


def blen(n):
    return SIDE[n[1:]] if n[0] in 'lr' and n[1:] in SIDE else CENTRE[n]


def tau(fx):
    """Output frame -> story time (s) relative to impact: slow-in, hit-stop, full-speed follow-through."""
    a = FI - 6
    if fx < a: return (fx - a) / FPS - 6 * SLOW / FPS
    if fx < FI: return (fx - FI) * SLOW / FPS
    if fx < FI + HS: return 0.0
    return (fx - FI - HS + 1) / FPS


# ---------------------------------------------------------------- data
def load(cid):
    s = cid.split('_')[0]
    cache = os.path.join(MOCAP, cid + '.npz')
    if os.path.exists(cache):
        z = np.load(cache, allow_pickle=True); return list(z['names']), z['P'], list(z['par'])
    names, P, par = mocap.joints(os.path.join(MOCAP, s + '.asf'), os.path.join(MOCAP, cid + '.amc'))
    np.savez(cache, names=np.array(names), P=P, par=np.array(par))
    return names, P, par


class Clip:
    def __init__(s, cid, t0, t1):
        names, P, par = load(cid)
        s.cid, s.names, s.par = cid, names, par
        s.I = {n: i for i, n in enumerate(names)}
        a, b = int(t0 * SRC), int(t1 * SRC)
        P = gaussian_filter1d(P[a:b], 1.0, axis=0)                   # low-pass mocap jitter
        s.t0 = t0
        I = s.I
        leg = np.mean([np.linalg.norm(P[:, I[k + 'femur']] - P[:, I[k + 'hipjoint']], axis=1).mean() +
                       np.linalg.norm(P[:, I[k + 'tibia']] - P[:, I[k + 'femur']], axis=1).mean() for k in 'lr'])
        sc = (SIDE['femur'] + SIDE['tibia']) / leg
        Q = np.zeros_like(P); Q[:, 0] = P[:, 0] * sc                  # keep root motion, scaled to our legs
        for j in range(1, len(names)):
            d = P[:, j] - P[:, par[j]]
            n = np.linalg.norm(d, axis=1, keepdims=True)
            Q[:, j] = Q[:, par[j]] + np.where(n > 1e-6, d / np.maximum(n, 1e-6), 0) * blen(names[j])
        s.planted = s.plant(Q)
        s.Q = Q

    def kids(s, j):
        out = [j]
        for k in range(len(s.names)):
            if s.par[k] in out and k not in out:
                out.append(k)
        return out

    def plant(s, Q):
        """Lock feet during ground contact: detect contact, hold the ankle, re-solve the knee (2-bone IK)."""
        I, info = s.I, {}
        for k in 'lr':
            hip, kn, an = I[k + 'hipjoint'], I[k + 'femur'], I[k + 'tibia']
            y = Q[:, an, 1]
            v = np.linalg.norm(np.diff(Q[:, an][:, [0, 2]], axis=0), axis=1) * SRC
            v = np.r_[v, v[-1]]
            con = (y < np.percentile(y, 15) + 22) & (v < 160)
            corr = np.zeros((len(Q), 3)); f = 0
            while f < len(Q):
                if con[f]:
                    e = f
                    while e < len(Q) and con[e]: e += 1
                    if e - f >= 6:
                        tgt = Q[f:e, an].mean(0)
                        corr[f:e, [0, 2]] = tgt[[0, 2]] - Q[f:e, an][:, [0, 2]]
                    f = e
                else:
                    f += 1
            corr = gaussian_filter1d(corr, 3, axis=0)
            l1, l2 = blen(k + 'femur'), blen(k + 'tibia')
            for f in range(len(Q)):
                if not np.any(np.abs(corr[f]) > 0.05):
                    continue
                Hh, A = Q[f, hip], Q[f, an] + corr[f]
                D = np.linalg.norm(A - Hh); D = min(D, l1 + l2 - 0.5)
                d = (A - Hh) / np.linalg.norm(A - Hh); A = Hh + d * D
                pole = Q[f, kn] - Hh; pole -= d * (pole @ d); pole /= max(np.linalg.norm(pole), 1e-6)
                aa = (l1 * l1 - l2 * l2 + D * D) / (2 * D); bb = math.sqrt(max(l1 * l1 - aa * aa, 0))
                Q[f, kn] = Hh + d * aa + pole * bb
                shift = A - Q[f, an]
                for j in s.kids(an):
                    Q[f, j] += shift
            info[k] = con
        return info

    def facing(s, f, kind):
        Q = s.Q
        if kind == 'punch':
            h = s.I['rhand'] if np.linalg.norm(Q[f, s.I['rhand']] - Q[f, s.I['thorax']]) > \
                np.linalg.norm(Q[f, s.I['lhand']] - Q[f, s.I['thorax']]) else s.I['lhand']
            v = Q[f, h] - Q[f, s.I['thorax']]
        else:  # feet
            v = sum(Q[:f + 1, s.I[k + 'toes']].mean(0) - Q[:f + 1, s.I[k + 'tibia']].mean(0) for k in 'lr')
        v = np.array([v[0], 0, v[2]]); return v / np.linalg.norm(v)

    def project(s, fwd, fd, base_x, ref, gf=None):
        """Three-quarter orthographic view; world x right, y down (ground 0), z depth."""
        side = np.array([fwd[2], 0, -fwd[0]])
        ex = math.cos(THETA) * fwd + math.sin(THETA) * side
        ez = -math.sin(THETA) * fwd + math.cos(THETA) * side
        Q = s.Q.copy(); Q[:, :, [0, 2]] -= Q[ref, 0][[0, 2]]
        anks = np.minimum(Q[:, s.I['ltibia'], 1], Q[:, s.I['rtibia'], 1])
        g = np.percentile(anks[:gf], 10) - 40      # planted ankle sits 40 px above the ground line
        V = np.zeros_like(Q)
        V[..., 0] = base_x + fd * (Q @ ex)
        V[..., 1] = -(Q[..., 1] - g)
        V[..., 2] = Q @ ez
        s.V = V
        return V

    def at(s, t):
        """Pose at clip time t (s, absolute clip time), linear interpolation."""
        x = (t - s.t0) * SRC
        x = min(max(x, 0), len(s.V) - 1.001)
        i = int(x); u = x - i
        return s.V[i] * (1 - u) + s.V[i + 1] * u


def blend(par, A, B, w, names):
    """Blend two poses in bone-direction space (keeps our bone lengths)."""
    out = np.zeros_like(A); out[0] = A[0] * (1 - w) + B[0] * w
    for j in range(1, len(A)):
        da, db = A[j] - A[par[j]], B[j] - B[par[j]]
        d = da * (1 - w) + db * w
        n = np.linalg.norm(d)
        out[j] = out[par[j]] + (d / n * blen(names[j]) if n > 1e-6 else 0)
    return out


# ---------------------------------------------------------------- setup
def detect_impact(cl, lo, hi):
    """Impact = full extension right after the peak striking-hand speed."""
    Q, I = cl.Q, cl.I
    best = None
    for h in ('rhand', 'lhand'):
        v = np.linalg.norm(np.diff(Q[:, I[h]], axis=0), axis=1) * SRC
        a, b = int((lo - cl.t0) * SRC), int((hi - cl.t0) * SRC)
        p = a + int(np.argmax(v[a:b]))
        if best is None or v[p] > best[0]:
            best = (v[p], p, h)
    _, p, h = best
    reach = np.linalg.norm(Q[:, I[h]] - Q[:, I['thorax']], axis=1)
    imp = p + int(np.argmax(reach[p:p + int(0.15 * SRC)]))
    return cl.t0 + p / SRC, cl.t0 + imp / SRC, h


def setup():
    hero = Clip('14_01', 22.3, 26.2)
    t_peak, t_imp, hand = detect_impact(hero, 23.4, 24.2)
    fh = hero.facing(int((t_imp - hero.t0) * SRC), 'punch')
    hero.project(fh, 1, -250, int((t_imp + tau(0) - hero.t0) * SRC))
    oa = Clip('14_02', 13.6, 16.0)
    o_peak, o_imp, _ = detect_impact(oa, 14.6, 15.2)
    OFF = o_peak + 0.62                    # opponent's punch peaks ~0.62 s before the impact
    fa = oa.facing(int((o_imp - oa.t0) * SRC), 'punch')
    oa.project(fa, -1, 250, int((OFF + tau(0) - oa.t0) * SRC))
    ob = Clip('90_18', 0.0, 3.25)
    # reaction onset = head starts to whip (head speed relative to the pelvis)
    hv = np.linalg.norm(np.diff(ob.Q[:, ob.I['head']] - ob.Q[:, 0], axis=0), axis=1) * SRC
    pk = int(np.argmax(hv[:int(1.6 * SRC)]))
    on = pk
    while on > 0 and hv[on] > 0.3 * hv[pk]:
        on -= 1
    r0 = on / SRC
    T = ob.Q[min(on + int(0.6 * SRC), len(ob.Q) - 1), ob.I['head']] - ob.Q[on, ob.I['head']]
    fb = -np.array([T[0], 0, T[2]]) / np.hypot(T[0], T[2])      # orient so he falls away from the hero
    ob.project(fb, -1, 0, on, gf=on)
    S = dict(hero=hero, oa=oa, ob=ob, t_imp=t_imp, t_peak=t_peak, hand=hand, OFF=OFF, r0=r0)
    # place the opponent so the hero's fist lands on his face at the impact frame
    fist = hero.at(t_imp)[hero.I[hand]]
    head = head_centre(oa, oa.at(OFF))
    dx = fist[0] - head[0] + R_HEAD * 0.7
    oa.V[..., 0] += dx
    ob.V[..., 0] += oa.at(OFF)[0, 0] - ob.at(r0)[0, 0]       # continuous root at the switch
    mid = (hero.at(t_imp + tau(0))[0, 0] + oa.at(OFF + tau(0))[0, 0]) / 2
    for c in (hero, oa, ob):
        c.V[..., 0] -= mid
    S['fist_vs_head_y'] = float(fist[1] - head[1])
    S['IP'] = (hero.at(t_imp)[hero.I[hand]][:2] + head_centre(oa, oa.at(OFF))[:2]) / 2
    S['knock_dir'] = float(ob.V[min(on + int(0.6 * SRC), len(ob.V) - 1), ob.I['head'], 0] - ob.V[on, ob.I['head'], 0])
    return S


def head_centre(cl, P):
    a, b = P[cl.I['upperneck']], P[cl.I['head']]
    return a + (b - a) * 0.5


def poses(S, fx):
    """Hero and opponent world poses at fractional output frame fx."""
    t = tau(fx)
    hero, oa, ob = S['hero'], S['oa'], S['ob']
    h = hero.at(S['t_imp'] + t)
    if fx > NF - 25:                                   # return to ready stance -> seamless loop
        w = ease((fx - (NF - 25)) / 24, 'io')
        h = blend(hero.par, h, hero.at(S['t_imp'] + tau(0)), w, hero.names)
    if t < 0 or fx < FI:
        o = oa.at(S['OFF'] + t)
    else:
        b = ob.at(S['r0'] + t)
        w = ease(t / 0.18, 'io') if t < 0.18 else 1.0
        o = blend(ob.par, oa.at(S['OFF']), b, w, ob.names) if w < 1 else b
        o = o.copy(); o[:, 0] += KNOCK * ease(min(t / 0.45, 1.0), 'out')   # added knock-back slide (not mocap)
    return h, o


# ---------------------------------------------------------------- drawing
def cap(p0, p1, r0, r1): return ('cap', np.asarray(p0[:2]), np.asarray(p1[:2]), r0, r1)
def circ(p, r): return ('circ', np.asarray(p[:2]), r)


def draw_fighter(cr, cl, P, hero, fd, prevP):
    I = cl.I; Pal = PAL[hero]
    J = lambda n: P[I[n]]
    # contact shadow
    tx = [J(k + 'foot')[0] for k in 'lr'] + [J(k + 'tibia')[0] for k in 'lr']
    cr.save(); cr.translate((min(tx) + max(tx)) / 2, 6); cr.scale((max(tx) - min(tx)) / 2 + 80, 16)
    cr.arc(0, 0, 1, 0, 2 * math.pi); cr.restore(); cr.set_source_rgba(0.02, 0.01, 0.05, 0.5); cr.fill()
    zl = np.mean([J(n)[2] for n in ('lhumerus', 'lfemur', 'lclavicle')])
    zr = np.mean([J(n)[2] for n in ('rhumerus', 'rfemur', 'rclavicle')])
    near = 'l' if zl < zr else 'r'
    zt = (J('root')[2] + J('thorax')[2]) / 2
    parts = []
    for k in 'lr':
        nk = k == near
        parts.append((np.mean([J(k + n)[2] for n in ('femur', 'tibia')]), 'leg', k, nk))
        parts.append((np.mean([J(k + n)[2] for n in ('humerus', 'radius', 'hand')]), 'arm', k, nk))
    parts.append((zt, 'torso', '', True))
    hc = head_centre(cl, P)
    parts.append((min(hc[2], zt - 1), 'head', '', True))
    for _, kind, k, nk in sorted(parts, key=lambda p: -p[0]):
        if kind == 'leg':
            hip, kn, an, ball, toe = (J(k + n) for n in ('hipjoint', 'femur', 'tibia', 'foot', 'toes'))
            skin = Pal['skin'] if nk else Pal['skin2']
            blob(cr, [cap(hip, kn, 38, 30), cap(kn, an, 29, 19), circ(kn, 29)], skin)
            if hero:
                blob(cr, [cap(hip, hip + (kn - hip) * 0.72, 42, 34)], Pal['shorts'] if nk else Pal['shorts2'])
            shoe = Pal['shoe'] if nk else Pal['shoe2']
            tip = ball + (ball - an) * 0.4                  # shoe along the foot (CMU toe bones vary)
            blob(cr, [circ(an + (an - kn) / np.linalg.norm(an - kn) * 6, 23), cap(an, tip, 22, 16)], shoe)
            if hero:
                dn = np.array([0, 13, 0])
                blob(cr, [cap(an + dn, tip + dn * 0.6, 8, 6)], Pal['sole'])
        elif kind == 'arm':
            sh, el, wr, hd = (J(k + n) for n in ('clavicle', 'humerus', 'radius', 'hand'))
            skin = (Pal.get('arm', Pal['skin']) if nk else Pal['skin2'])
            blob(cr, [cap(sh, el, 27, 23), cap(el, wr, 23, 19), circ(el, 23), cap(wr, hd, 20, 19)], skin)
            if hero:
                blob(cr, [cap(sh, sh + (el - sh) * 0.5, 30, 27)], Pal['tee'] if nk else C('#c9c7d2'))
        elif kind == 'torso':
            root, lb, ub, th = J('root'), J('lowerback'), J('upperback'), J('thorax')
            if hero:
                blob(cr, [cap(J('lhipjoint'), J('rhipjoint'), 42, 42), circ(root, 44)], Pal['shorts'])
                base = root + (lb - root) * 0.3
            else:
                base = root
                blob(cr, [cap(J('lhipjoint'), J('rhipjoint'), 40, 40)], Pal['tee'])
            prims = [cap(base, ub, 47, 56), cap(ub, th, 56, 48), cap(J('lclavicle'), J('rclavicle'), 31, 31)]
            if hero:  # shirt hem trails the pelvis (secondary motion)
                lag = np.clip(-(root - prevP[I['root']])[:2] * 0.6, -26, 26)
                r2 = root[:2]
                prims.append(('poly', [r2 + (-fd * 46, 8), r2 + (-fd * 52, 30) + lag, r2 + (0, 38) + lag * 0.5,
                                       r2 + (fd * 44, 16)]))
            blob(cr, prims, Pal['tee'])
        else:
            blob(cr, [cap(J('thorax'), hc, 19, 18)], Pal['skin'])
            blob(cr, [circ(hc, R_HEAD)], Pal['skin'])
            if hero:
                draw_hair(cr, hc, J('upperneck'), J('head'), fd, hc - head_centre(cl, prevP), Pal)


def draw_hair(cr, hc, neck, top, fd, vel, Pal):
    u = (top - neck)[:2]; u = u / np.linalg.norm(u)
    ha = math.atan2(u[0], -u[1])
    ca, sa = math.cos(ha), math.sin(ha)
    lag = np.clip(-vel[:2] * 0.7, -34, 34)                       # hair trails head motion
    lx, ly = lag[0] * ca + lag[1] * sa, -lag[0] * sa + lag[1] * ca  # world -> rotated frame
    lx *= fd                                                       # -> facing-local x

    def tr(pts):  # head-local (x forward, y down) -> world
        return [(hc[0] + x * fd * ca - y * sa, hc[1] + x * fd * sa + y * ca) for x, y in pts]
    capp = [(-64, 18), (-70, -8), (-60, -40), (-36, -64), (0, -72), (34, -62), (56, -40),
            (60, -14), (44, -26), (34, -18), (20, -34), (-10, -30), (-34, -10), (-44, 22)]
    spikes = [[(-58, -44), (-96 + lx, -60 + ly), (-66, -16)], [(-30, -64), (-52 + lx * .8, -100 + ly * .8), (-4, -70)]]
    blob(cr, [('poly', tr(capp))] + [('poly', tr(sp)) for sp in spikes], Pal['hair'])
    ex, ey = tr([(38, -2)])[0]
    cr.set_source_rgba(*C('#140c10')); cr.arc(ex, ey, 7.5, 0, 2 * math.pi); cr.fill()


# ---------------------------------------------------------------- camera
def build_camera(S):
    """Per-frame camera: tracks the fighters (parallax), pushes in, whips to the impact, pulls back."""
    I = S['hero'].I
    hh = np.array([head_centre(S['hero'], poses(S, f)[0])[:2] for f in range(NF)])
    oh = np.array([head_centre(S['ob'], poses(S, f)[1])[:2] for f in range(NF)])
    oroot = np.array([poses(S, f)[1][0, :2] for f in range(NF)])
    wo = np.array([0.45 if f < FI else 0.55 * (1 - ease((f - FI - 18) / (NF - 28 - FI - 18), 'out'))
                   for f in range(NF)])                 # after the fall: drift from him back onto the hero
    tx = gaussian_filter1d(hh[:, 0] * (1 - wo) + np.where(np.arange(NF)[:, None] < FI, oh, oroot)[:, 0] * wo, 6)
    ty = gaussian_filter1d(np.where(np.arange(NF) < FI, (hh[:, 1] + oh[:, 1]) / 2, hh[:, 1]), 8) + 330
    IP = S['IP']
    cams = []
    for f in range(NF):
        if f <= FI - 3:
            z = 1.32 + 0.3 * (f / (FI - 3)) ** 0.8; c = (tx[f], ty[f], z, 0.0)   # push-in starts at once
        elif f < FI:
            a = cams[FI - 3]; u = ease((f - FI + 3) / 3, 'in')
            c = tuple(a[i] + ((IP[0], IP[1] + 40, 2.7, -0.09)[i] - a[i]) * u for i in range(4))
        elif f <= FI + 3:                            # close-up holds through the hit-stop
            u = (f - FI) / 3; c = (IP[0] + 10 * u, IP[1] + 40 - 8 * u, 2.7 + 0.1 * u, -0.09)
        else:
            c = (tx[f], ty[f] + 20, 1.04 + 0.34 * ease((f - FI - 18) / (NF - 28 - FI - 18), 'out'), 0.0)
            if f < FI + 18:                          # fast pull-back so the knock-down is seen
                a = cams[FI + 3]; u = ease((f - FI - 3) / 15, 'snap')
                c = tuple(a[i] + (c[i] - a[i]) * u for i in range(4))
        cams.append(c)
    for f in range(NF - 28, NF):                     # settle back onto the opening framing (loop)
        u = ease((f - NF + 28) / 27, 'io')
        cams[f] = tuple(cams[f][i] + (cams[0][i] - cams[f][i]) * u for i in range(4))
    S['cams'] = cams


def camera(S, f):
    x, y, z, rot = S['cams'][f]
    shake = np.zeros(2)
    if FI <= f < FI + 5:
        k = f - FI; shake = np.array([16, -11]) * (1 - k / 5) * (1 if k % 2 == 0 else -1)
    return np.array([x, y]), z, rot, shake


def sparks(cr, S, f):
    if not FI <= f < FI + 7:
        return
    u = (f - FI) / 7; c = S['IP']
    cr.set_line_cap(cairo.LINE_CAP_ROUND)
    for i, ang in enumerate((-70, -40, -12, 15, 40, 70)):
        a = math.radians(ang)
        r1, r2 = 20 + 45 * u, (40 + 80 * u) * (0.8 + 0.2 * (i % 2))
        cr.set_source_rgba(1, 0.94, 0.7, 1 - 0.8 * u); cr.set_line_width(max(1.5, 6 * (1 - u)))
        cr.move_to(c[0] + r1 * math.cos(a), c[1] + r1 * math.sin(a))
        cr.line_to(c[0] + r2 * math.cos(a), c[1] + r2 * math.sin(a)); cr.stroke()


def render_one(S, f, fx, layers, fg):
    cam, z, rot, shake = camera(S, f)
    img = np.zeros((H, W, 3), np.float32)
    for a, p, _ in layers:
        M = layer_matrix(cam, z, rot, shake, p)
        over(img, cv2.warpAffine(a, M, (W, H), flags=cv2.INTER_LINEAR,
                                 borderMode=cv2.BORDER_REPLICATE if p < 0.05 else cv2.BORDER_CONSTANT))
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H); cr = cairo.Context(surf)
    cr.translate(*(SC + shake)); cr.rotate(rot); cr.scale(z, z); cr.translate(-cam[0], -cam[1])
    draw_ground(cr)
    h, o = poses(S, fx); hp, op = poses(S, fx - 3)
    draw_fighter(cr, S['ob'], o, False, -1, op)
    draw_fighter(cr, S['hero'], h, True, 1, hp)
    sparks(cr, S, f)
    surf.flush(); over(img, surf_to_np(surf))
    over(img, cv2.warpAffine(fg[0], layer_matrix(cam, z, rot, shake, fg[1]), (W, H), flags=cv2.INTER_LINEAR))
    return img


def speed(S, f):
    """Max screen-space joint speed (px/frame) used to decide sub-frame motion blur."""
    _, z, _, _ = camera(S, f)
    a, b = poses(S, f - 0.5), poses(S, f + 0.5)
    return max(np.abs(a[i][:, :2] - b[i][:, :2]).max() for i in (0, 1)) * z


def render(S, f, layers, fg):
    if speed(S, f) > 18:
        img = sum(render_one(S, f, f + (k - 1.5) / 4, layers, fg) for k in range(4)) / 4
    else:
        img = render_one(S, f, f, layers, fg)
    if f in FLASH:
        a = FLASH[f]; img = img * (1 - a) + np.array([1.0, 0.86, 0.5], np.float32) * a
    return (np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8)


# ---------------------------------------------------------------- audio
def audio(S, path):
    import sfx
    SR = sfx.SR; n = int(SR * 3.0); mix = np.zeros(n); rng = np.random.default_rng(5)

    def put(sig, t, g=1.0):
        i = max(0, int(round(t * SR))); seg = sig[:n - i]; mix[i:i + len(seg)] += seg * g
    hero, I = S['hero'], S['hero'].I
    hs = [np.linalg.norm(poses(S, f + .5)[0][I[S['hand']]] - poses(S, f - .5)[0][I[S['hand']]]) for f in range(FI)]
    hs = np.array(hs); fast = [f for f in range(FI - 25, FI) if hs[f] > 0.5 * hs.max()]
    ws = (fast[0] if fast else FI - 10) / FPS - 0.04; d = FI / FPS - ws
    t = np.arange(int(SR * d)) / SR
    put(sfx.lp(rng.standard_normal(len(t)), 9) * (t / d) ** 2 * 1.6, ws)          # strike whoosh -> impact
    os_ = [np.abs(poses(S, f + .5)[1][:, :2] - poses(S, f - .5)[1][:, :2]).max() for f in range(FI - 2)]
    po = int(np.argmax(os_)); put(sfx.whoosh(0.24, 14), po / FPS - 0.14, 0.8)        # opponent's punch
    hy = [poses(S, f)[0][I['head'], 1] for f in range(FI)]
    put(sfx.whoosh(0.16, 34), int(np.argmax(hy)) / FPS - 0.1, 0.35)                 # hero ducks
    hit = sfx.thump(0.32) * 1.3
    cr_ = sfx.lp(rng.standard_normal(int(SR * 0.03)), 2) * np.exp(-np.arange(int(SR * .03)) / SR * 140)
    hit[:len(cr_)] += cr_ * 1.1
    put(hit, FI / FPS); put(sfx.boom(0.9), FI / FPS, 0.95)                         # exact impact frame
    ob = S['ob']; fv = []
    for f in range(FI + HS, NF - 25):
        a, b = poses(S, f - .5)[1], poses(S, f + .5)[1]
        fv.append(max(abs(a[ob.I[k + 'tibia'], 0] - b[ob.I[k + 'tibia'], 0]) for k in 'lr'))
    sl = [FI + HS + i for i, v in enumerate(fv) if v > 2.5]
    if sl:
        d = min(0.6, (sl[-1] - sl[0]) / FPS + 0.15); t = np.arange(int(SR * d)) / SR
        put(sfx.lp(rng.standard_normal(len(t)), 22) * np.sin(np.pi * t / d) ** 1.5, sl[0] / FPS, 0.55)
    fade = np.ones(n); fade[-int(SR * .03):] = np.linspace(1, 0, int(SR * .03)); mix *= fade
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
    return Il, P, dict(strike_whoosh=round(ws, 3), opp_punch=round(po / FPS, 3), impact=FI / FPS,
                       slide=(round(sl[0] / FPS, 2), round(sl[-1] / FPS, 2)) if sl else None)


# ---------------------------------------------------------------- main
def report(S):
    print('hero clip 14_01: speed peak %.3fs, impact %.3fs (%s)' % (S['t_peak'], S['t_imp'], S['hand']))
    print('opponent 14_02 punch peak aligned %.2fs before impact; 90_18 reaction onset %.3fs' % (0.62, S['r0']))
    print('fist-vs-head dy %.0f px; opp head travel +x in 0.6 s after onset: %.0f px' % (S['fist_vs_head_y'], S['knock_dir']))
    gaps = [abs(poses(S, f)[1][0, 0] - poses(S, f)[0][0, 0]) for f in range(NF)]
    print('root separation min %.0f px (body width ~110)' % min(gaps))
    pl = {k: int(v.sum()) for k, v in S['hero'].planted.items()}
    print('hero planted frames (120 fps):', pl)


def main():
    os.makedirs(OUT, exist_ok=True)
    S = setup(); build_camera(S); report(S)
    layers, fg = make_layers()
    if '--frames' in sys.argv:
        for f in map(int, sys.argv[sys.argv.index('--frames') + 1].split(',')):
            cv2.imwrite(os.path.join(OUT, 'm%03d.png' % f), render(S, f, layers, fg)[..., ::-1])
        return
    np.savez_compressed(os.path.join(HERE, 'mocap_poses.npz'),
                        hero=np.array([poses(S, f)[0] for f in range(NF)], np.float32),
                        opp=np.array([poses(S, f)[1] for f in range(NF)], np.float32),
                        names=np.array(S['hero'].names), parents=np.array(S['hero'].par))
    wav = os.path.join(OUT, 'hook-mocap-sfx.wav')
    Il, P, cues = audio(S, wav); print('audio I=%.1f LUFS TP=%.1f dBTP cues %s' % (Il, P, cues))
    mp4 = os.path.join(OUT, 'hook-mocap-test.mp4')
    cmd = ['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '%dx%d' % (W, H),
           '-r', str(FPS), '-i', '-', '-i', wav, '-map', '0:v', '-map', '1:a', '-c:v', 'libx264', '-preset', 'slow',
           '-crf', '17', '-pix_fmt', 'yuv420p', '-vf', 'setsar=1', '-aspect', '9:16', '-c:a', 'aac', '-b:a', '256k',
           '-t', '3.0', '-movflags', '+faststart', mp4]
    pr = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    nb = 0
    for f in range(NF):
        nb += speed(S, f) > 18
        pr.stdin.write(render(S, f, layers, fg).tobytes())
    pr.stdin.close(); pr.wait()
    print('motion-blurred frames:', nb, '->', mp4)


if __name__ == '__main__':
    main()
