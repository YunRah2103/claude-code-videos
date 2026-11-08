"""2D pose timeline built from mocap clips: blending in bone-angle space, falls, shoves, flinches."""
import math, bisect
import numpy as np
import mocap
from mocap import IDX, NAMES

BONES = [('hip', 'chest'), ('chest', 'neck'), ('neck', 'head'), ('neck', 'rsh'), ('rsh', 'rel'), ('rel', 'rhand'),
         ('neck', 'lsh'), ('lsh', 'lel'), ('lel', 'lhand'), ('hip', 'rhp'), ('rhp', 'rkn'), ('rkn', 'rft'), ('rft', 'rtoe'),
         ('hip', 'lhp'), ('lhp', 'lkn'), ('lkn', 'lft'), ('lft', 'ltoe')]
BI = [(IDX[a], IDX[b]) for a, b in BONES]
UPPER = [0, 1, 2, 3, 4, 5, 6, 7, 8]          # bones rotated by a flinch

class Clip2D:
    """Mocap clip projected to a side view: per-frame hip xy, bone angles/lengths, joint depth."""
    def __init__(s, name, ref=None):
        fps, P = _raw(name)
        i0 = 0 if ref is None else max(0, min(len(P) - 1, int(ref*fps)))
        win = P[max(0, i0 - 15):i0 + 16]
        lat = (win[:, IDX['lhp']] - win[:, IDX['rhp']]).mean(0)
        th = math.atan2(lat[0], lat[2])            # rotate about y so lateral axis -> z
        c, n = math.cos(th), math.sin(th)
        X = P[:, :, 0]*c - P[:, :, 2]*n; Z = P[:, :, 0]*n + P[:, :, 2]*c
        fwd = (X[:, IDX['ltoe']] - X[:, IDX['lft']] + X[:, IDX['rtoe']] - X[:, IDX['rft']])[max(0, i0 - 15):i0 + 16].mean()
        if fwd < 0: X, Z = -X, -Z
        s.fps, s.T = fps, len(P); s.dur = (s.T - 1)/fps
        s.x = X*mocap.S; s.y = -P[:, :, 1]*mocap.S; s.z = Z
        s.pose = [s._frame(i) for i in range(s.T)]
    def _frame(s, i):
        x, y = s.x[i], s.y[i]
        ang = np.array([math.atan2(y[b] - y[a], x[b] - x[a]) for a, b in BI])
        ln = np.array([math.hypot(x[b] - x[a], y[b] - y[a]) for a, b in BI])
        return (np.array([x[0], y[0]]), ang, ln, s.z[i].copy())
    def detr(s, u):
        """Root x minus its 0.8 s moving average: keeps footwork bounce, removes drift."""
        if not hasattr(s, '_sm'):
            k = max(3, int(0.8*s.fps)) | 1; pad = k//2
            xs = np.pad(s.x[:, 0], pad, mode='edge'); s._sm = np.convolve(xs, np.ones(k)/k, mode='valid')
        f = max(0.0, min(s.T - 1.0, u*s.fps)); i = min(int(f), s.T - 2); w = f - i
        return (s.x[i, 0] - s._sm[i])*(1 - w) + (s.x[i+1, 0] - s._sm[i+1])*w
    def match(s, p, face, a=0.0, b=None, step=1/30):
        """Clip time whose pose best matches pose p (bone angles), for seamless returns."""
        b = s.dur if b is None else b; best = (1e9, a); u = a
        while u < b:
            q = mirror(s.at(u), face)
            d = np.abs((q[1] - p[1] + np.pi) % (2*np.pi) - np.pi)[[1, 3, 4, 5, 6, 7, 8, 10, 11, 14, 15]].sum()
            if d < best[0]: best = (d, u)
            u += step
        return best[1]
    def at(s, u):
        f = max(0.0, min(s.T - 1.0, u*s.fps)); i = min(int(f), s.T - 2); w = f - i
        return blend(s.pose[i], s.pose[i+1], w)

def angmix(a, b, w):
    d = (b - a + np.pi) % (2*np.pi) - np.pi
    return a + d*w

def blend(p, q, w):
    return (p[0] + (q[0] - p[0])*w, angmix(p[1], q[1], w), p[2] + (q[2] - p[2])*w, p[3] + (q[3] - p[3])*w)

def mirror(p, face):
    if face > 0: return p
    return (np.array([-p[0][0], p[0][1]]), np.pi - p[1], p[2], p[3])

def fk(p):
    J = np.zeros((len(NAMES), 2)); J[0] = p[0]
    for k, (a, b) in enumerate(BI):
        J[b] = J[a] + p[2][k]*np.array([math.cos(p[1][k]), math.sin(p[1][k])])
    return J

def ground_y(p):
    J = fk(p); return J[:, 1].max()

_raws, _clips = {}, {}
def _raw(name):
    if name not in _raws:
        _raws[name] = mocap.load_cmu(name[4:]) if name.startswith('cmu:') else mocap.load(name)
    return _raws[name]
def clip(name, ref=None):
    key = (name, None if ref is None else round(ref, 1))
    if key not in _clips: _clips[key] = Clip2D(name, key[1])
    return _clips[key]

def ease(u): u = max(0.0, min(1.0, u)); return u*u*(3 - 2*u)
def ease_out(u): u = max(0.0, min(1.0, u)); return 1 - (1 - u)**3

class Seg:
    pass

class Actor:
    """A fighter's timeline of segments; pose(t) -> joints (world units, y down, ground y=0)."""
    def __init__(s, name):
        s.name = name; s.segs = []; s.shoves = []; s.flinches = []
    # ---- authoring
    def play(s, t, name, a=0.0, b=None, speed=1.0, x=None, face=None, rm=1.0, blend=0.12, loop=False, ground=True):
        g = Seg(); g.kind = 'clip'; g.t = t; g.c = clip(name); g.a = a; g.b = g.c.dur if b is None else b
        g.speed = speed; g.rm = rm; g.blend = blend; g.loop = loop; g.ground = ground
        g.x = s._endx(t) if x is None else x; g.face = s._endface(t) if face is None else face
        s._add(g); return s
    def box(s, t, name, face, keys=(), u0=None, speed=1.0, blend=0.25, ref=None, amp=0.8):
        """Continuous sparring take: real footwork, position follows smooth path keys [(t, x), ...]."""
        g = Seg(); g.kind = 'box'; g.t = t; g.c = clip(name, ref); g.face = face; g.speed = speed; g.blend = blend; g.amp = amp
        x0 = s._endx(t) if s.segs else (keys[0][1] if keys else 0.0)
        if u0 is None:
            u0 = g.c.match(s.pose_raw(t - 1e-4), face, 2.0, g.c.dur - 5.0) if s.segs else 2.0
        g.u0 = u0; g.keys = [(t, x0)] + list(keys)
        s._add(g); return s
    def hold(s, t, name, u, x=None, face=None, blend=0.18, bob=1.0):
        g = Seg(); g.kind = 'hold'; g.t = t; g.c = clip(name); g.u = u; g.blend = blend; g.bob = bob
        g.x = s._endx(t) if x is None else x; g.face = s._endface(t) if face is None else face
        s._add(g); return s
    def fall(s, t, vx, up=260, lie='faceup', dur=0.55, blend=0.02, spin=0.0):
        g = Seg(); g.kind = 'fall'; g.t = t; g.vx = vx; g.up = up; g.dur = dur; g.blend = blend; g.spin = spin
        g.lie = clip('getup_' + lie).pose[0]; g.lie_name = lie
        g.start = s.pose_raw(t - 1e-4); g.face = 1 if vx >= 0 else -1
        g.x = g.start[0][0]
        s._add(g); return s
    def getup(s, t, lie='faceup', speed=1.6, face=None, blend=0.1):
        x = s._endx(t)
        return s.play(t, 'getup_' + lie, speed=speed, face=face, x=x, blend=blend)
    def shove(s, t, dx, dur=0.3): s.shoves.append((t, dx, dur)); return s
    def flinch(s, t, amt=0.45, dur=0.35): s.flinches.append((t, amt, dur)); return s
    def _add(s, g):
        s.segs.append(g); s.segs.sort(key=lambda q: q.t); s._ts = [q.t for q in s.segs]
    def _endx(s, t):
        if not s.segs: return 0.0
        return s.pose_raw(t - 1e-4)[0][0]
    def _endface(s, t):
        prev = [g for g in s.segs if g.t <= t]
        return prev[-1].face if prev else 1
    # ---- evaluation
    def seg_pose(s, g, t):
        if g.kind == 'clip':
            u = g.a + (t - g.t)*g.speed
            off = 0.0
            if g.loop:
                L = g.b - g.a; n = math.floor((u - g.a)/L); u = g.a + (u - g.a) - n*L
                off = n*(g.c.at(g.b)[0][0] - g.c.at(g.a)[0][0])
            else:
                u = min(u, g.b)
            p = g.c.at(u); p0 = g.c.at(g.a)
            hip = np.array([(p[0][0] - p0[0][0] + off)*g.rm, p[0][1]])
            p = (hip, p[1], p[2], p[3]); p = mirror(p, g.face)
            return (np.array([g.x + p[0][0], p[0][1]]), p[1], p[2], p[3])
        if g.kind == 'box':
            L = g.c.dur - 1.0; u = 0.5 + ((g.u0 - 0.5) + (t - g.t)*g.speed) % L
            p = mirror(g.c.at(u), g.face)
            ks = g.keys; x = ks[-1][1]
            for (t0, x0), (t1, x1) in zip(ks, ks[1:]):
                if t <= t1: x = x0 + (x1 - x0)*ease((t - t0)/max(1e-6, t1 - t0)); break
            if t < ks[0][0]: x = ks[0][1]
            return (np.array([x + g.face*g.amp*g.c.detr(u), p[0][1]]), p[1], p[2], p[3])
        if g.kind == 'hold':
            p = mirror(g.c.at(g.u), g.face)
            bob = g.bob*(1 - math.cos((t - g.t)*7.0))*2.2
            return (np.array([g.x, p[0][1] + bob]), p[1], p[2], p[3])
        if g.kind == 'fall':
            tau = t - g.t; u = min(1.0, tau/g.dur)
            lie = mirror(g.lie, -g.face if g.lie_name == 'faceup' else g.face)
            ang = angmix(g.start[1], lie[1], ease_out(u*1.15))
            if g.spin: ang = ang + g.spin*math.sin(math.pi*u)
            p = (g.start[0], ang, g.start[2] + (lie[2] - g.start[2])*ease(u), lie[3])
            x = g.x + g.vx*min(tau, g.dur*1.4)*(1 - 0.35*min(1, tau/g.dur))
            h = g.up*4*u*(1 - u)
            J = fk((np.array([0.0, 0.0]), p[1], p[2], p[3]))
            low = J[:, 1].max()
            base_y = -low
            y0 = g.start[0][1]
            y = (y0 + (base_y - y0)*ease(u)) - h
            if tau > g.dur:   # small bounce then settle
                b = tau - g.dur; y -= 18*math.exp(-b*9)*abs(math.sin(b*14))
            return (np.array([x, y]), p[1], p[2], p[3])
    def pose_raw(s, t):
        if not s.segs: return None
        i = bisect.bisect_right(s._ts, t) - 1
        if i < 0: i = 0
        g = s.segs[i]; p = s.seg_pose(g, max(t, g.t))
        if i > 0 and t - g.t < g.blend:
            q = s.seg_pose(s.segs[i-1], t)
            p = blend(q, p, ease((t - g.t)/g.blend))
        return p
    def pose(s, t):
        p = s.pose_raw(t)
        hip = p[0].copy(); ang = p[1].copy()
        for t0, dx, d in s.shoves:
            if t >= t0: hip[0] += dx*ease_out((t - t0)/d)
        face = s._endface(t)
        for t0, amt, d in s.flinches:
            if 0 <= t - t0 < d*2:
                u = (t - t0)/d; a = amt*math.sin(min(1, u*2.5)*math.pi/2)*math.exp(-max(0, u - 0.4)*2.2)
                ang[UPPER] -= a*face
        return (hip, ang, p[2], p[3])
    def joints(s, t):
        p = s.pose(t); return fk(p), p[3]
