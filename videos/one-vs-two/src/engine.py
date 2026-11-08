"""Procedural anime fight engine: skeletal fighters, camera, time warp and effects."""
import math, bisect, random
import numpy as np

W, H, FPS, SS = 720, 1280, 60, 1.5   # logical 720x1280 -> 1080x1920 output
HZ = 0.60                      # screen y (fraction) of the camera focus
FONT = '/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf'
INK = (8, 6, 16)

def hexc(h, a=None):
    h = h.lstrip('#'); c = tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
    return c if a is None else c + (int(a),)
def shade(c, k): return tuple(max(0, min(255, int(v*k))) for v in c[:3])
def mix(c1, c2, s): return tuple(int(a+(b-a)*s) for a, b in zip(c1, c2))
def lerp(a, b, s): return a + (b-a)*s
def clamp(x, a=0., b=1.): return a if x < a else b if x > b else x
def add(p, q): return (p[0]+q[0], p[1]+q[1])
def mul(p, k): return (p[0]*k, p[1]*k)
def smooth(s): s = clamp(s); return s*s*(3-2*s)

EASE = {'lin': lambda s: s, 'out': lambda s: 1-(1-s)**3, 'in': lambda s: s**3,
        'io': lambda s: s*s*(3-2*s), 'snap': lambda s: 1-(1-s)**6,
        'hold': lambda s: 0.0 if s < 1 else 1.0,
        'back': lambda s: 1 + 2.4*(s-1)**3 + 1.4*(s-1)**2}

# ---------------------------------------------------------------- time warp
class Warp:
    """Maps real time <-> animation time with hit-stops and slow motion."""
    def __init__(s): s.stops, s.slows = [], []
    def stop(s, t, d): s.stops.append((t, d))
    def slow(s, t, d, rate): s.slows.append((t, t+d, rate))
    def R(s, ta):
        r = ta + sum(d for t, d in s.stops if t < ta)
        for a, b, rate in s.slows:
            r += max(0, min(ta, b) - a) * (1/rate - 1)
        return r
    def A(s, tr):
        lo, hi = 0.0, tr + 1e-9
        for _ in range(48):
            m = (lo+hi)/2
            if s.R(m) <= tr: lo = m
            else: hi = m
        return lo

# ---------------------------------------------------------------- skeleton
LEN = dict(torso=48, neck=7, head=16, ua=28, fa=27, th=38, sn=38)
BASE = dict(t=5, h=0, ra1=-10, ra2=5, fa1=10, fa2=25, rl1=-6, rl2=-12, fl1=10, fl2=2, sw=None, bob=0, run=0)
POSES = {
    'stand':  dict(bob=0.4),
    'look':   dict(bob=0.4, h=-14, t=0),
    'guard':  dict(bob=1, t=12, h=-4, ra1=35, ra2=150, fa1=55, fa2=140, rl1=-20, rl2=-34, fl1=34, fl2=4),
    'guard2': dict(bob=1, t=16, h=-6, ra1=45, ra2=155, fa1=70, fa2=150, rl1=-26, rl2=-40, fl1=40, fl2=6),
    'jab':    dict(t=22, ra1=30, ra2=150, fa1=88, fa2=90, rl1=-36, rl2=-48, fl1=50, fl2=14),
    'cross':  dict(t=30, ra1=90, ra2=90, fa1=40, fa2=150, rl1=-40, rl2=-52, fl1=52, fl2=14),
    'elbow':  dict(t=32, h=-8, fa1=96, fa2=205, ra1=25, ra2=140, rl1=-42, rl2=-54, fl1=55, fl2=12),
    'block':  dict(bob=0.5, t=6, h=6, fa1=70, fa2=170, ra1=40, ra2=160, rl1=-24, rl2=-38, fl1=30, fl2=4),
    'chamber':dict(t=-6, ra1=40, ra2=150, fa1=50, fa2=140, fl1=100, fl2=8, rl1=-4, rl2=-8),
    'kick':   dict(t=-30, h=12, fa1=-35, fa2=15, ra1=60, ra2=125, fl1=112, fl2=114, rl1=-8, rl2=-10),
    'upkick': dict(t=-42, h=18, fa1=-60, fa2=-30, ra1=80, ra2=130, fl1=160, fl2=165, rl1=-6, rl2=-10),
    'crouch': dict(t=38, h=-18, ra1=40, ra2=150, fa1=60, fa2=145, fl1=88, fl2=-4, rl1=22, rl2=-78),
    'sweep':  dict(t=58, h=-20, fa1=80, fa2=10, ra1=40, ra2=-10, fl1=84, fl2=96, rl1=58, rl2=-62),
    'tuck':   dict(t=14, ra1=40, ra2=140, fa1=60, fa2=150, fl1=112, fl2=12, rl1=82, rl2=-10),
    'airkick':dict(t=-22, h=8, fa1=-40, fa2=10, ra1=100, ra2=160, fl1=96, fl2=96, rl1=48, rl2=-32),
    'hurt':   dict(t=-30, h=-26, fa1=50, fa2=62, ra1=30, ra2=72, fl1=26, fl2=10, rl1=-26, rl2=-34),
    'flyback':dict(t=-48, h=-30, fa1=128, fa2=118, ra1=108, ra2=98, fl1=62, fl2=40, rl1=30, rl2=8),
    'lying':  dict(t=0, h=-8, fa1=150, fa2=170, ra1=-160, ra2=-175, fl1=12, fl2=4, rl1=-10, rl2=-14),
    'kneel':  dict(t=18, h=22, fa1=60, fa2=8, ra1=-8, ra2=4, fl1=86, fl2=0, rl1=2, rl2=-88),
    'power':  dict(bob=0.3, t=-8, h=-18, fa1=26, fa2=12, ra1=-26, ra2=-14, fl1=26, fl2=14, rl1=-26, rl2=-16),
    'horse':  dict(bob=0.4, t=4, h=-4, fa1=95, fa2=128, ra1=-95, ra2=-128, fl1=46, fl2=-2, rl1=-46, rl2=2),
    'push':   dict(t=0, h=-10, fa1=92, fa2=92, ra1=-92, ra2=-92, fl1=48, fl2=4, rl1=-48, rl2=-4),
    'iai':    dict(bob=0.5, t=26, h=-10, fa1=42, fa2=-30, ra1=20, ra2=-40, fl1=62, fl2=6, rl1=-48, rl2=-62),
    'swup':   dict(t=-6, h=-6, fa1=150, fa2=172, ra1=140, ra2=165, fl1=34, fl2=6, rl1=-24, rl2=-36, sw=185),
    'swdown': dict(t=34, h=-10, fa1=70, fa2=78, ra1=60, ra2=75, fl1=58, fl2=12, rl1=-42, rl2=-56, sw=35),
    'swfwd':  dict(t=28, h=-8, fa1=90, fa2=92, ra1=-40, ra2=-20, fl1=56, fl2=10, rl1=-44, rl2=-56, sw=92),
    'swback': dict(t=10, h=-6, fa1=-60, fa2=-80, ra1=-30, ra2=-10, fl1=40, fl2=8, rl1=-30, rl2=-44, sw=-110),
    'swguard':dict(bob=1, t=14, h=-6, fa1=40, fa2=118, ra1=50, ra2=128, fl1=36, fl2=4, rl1=-22, rl2=-36, sw=150),
    'swlow':  dict(t=34, h=10, fa1=100, fa2=90, ra1=-40, ra2=-30, fl1=86, fl2=0, rl1=2, rl2=-88, sw=150),
    'run':    dict(run=1, t=34, h=-14, fa1=60, fa2=150, ra1=-20, ra2=60, fl1=30, fl2=-10, rl1=-30, rl2=-50),
    'axeup':  dict(t=-28, h=10, fa1=-50, fa2=10, ra1=70, ra2=120, fl1=175, fl2=178, rl1=-6, rl2=-10),
    'axedown':dict(t=30, h=-10, fa1=60, fa2=20, ra1=-40, ra2=0, fl1=60, fl2=40, rl1=-30, rl2=-40),
    'swhigh': dict(bob=0.5, t=4, h=-8, fa1=150, fa2=120, ra1=140, ra2=110, fl1=40, fl2=6, rl1=-28, rl2=-40, sw=200),
    'dash':   dict(t=48, h=-24, fa1=-64, fa2=-44, ra1=-74, ra2=-56, fl1=72, fl2=18, rl1=-42, rl2=-74),
    'land':   dict(t=34, h=-12, fa1=112, fa2=92, ra1=-62, ra2=-30, fl1=84, fl2=-6, rl1=-10, rl2=-84),
    'dive':   dict(t=40, h=-16, fa1=150, fa2=165, ra1=-30, ra2=10, fl1=60, fl2=18, rl1=-22, rl2=-44),
    'facedown':dict(t=0, h=8, fa1=170, fa2=178, ra1=10, ra2=4, fl1=4, fl2=-4, rl1=-8, rl2=-14),
}
def P(name, **kw):
    d = dict(BASE); d.update(POSES[name]); d.update(kw); return d

def vl(a):
    r = math.radians(a); return (math.sin(r), math.cos(r))
def vu(a):
    r = math.radians(a); return (math.sin(r), -math.cos(r))

def joints(p):
    J = {'hip': (0.0, 0.0)}
    t = vu(p['t'])
    J['chest'] = mul(t, LEN['torso']); J['sh'] = mul(t, LEN['torso']-5)
    J['neck'] = add(J['chest'], mul(vu(p['t']+p['h']*0.4), LEN['neck']))
    J['head'] = add(J['neck'], mul(vu(p['t']+p['h']), LEN['head']*0.9))
    for s in 'rf':
        e = add(J['sh'], mul(vl(p[s+'a1']), LEN['ua'])); J[s+'el'] = e
        J[s+'hand'] = add(e, mul(vl(p[s+'a2']), LEN['fa']))
        k = mul(vl(p[s+'l1']), LEN['th']); J[s+'kn'] = k
        J[s+'ft'] = add(k, mul(vl(p[s+'l2']), LEN['sn']))
        J[s+'toe'] = add(J[s+'ft'], mul(vl(p[s+'l2']+90), 9))
    if p['sw'] is not None:
        d = vl(p['sw']); hd = J['fhand']
        J['pommel'] = add(hd, mul(d, -9)); J['guardp'] = add(hd, mul(d, 6)); J['tip'] = add(hd, mul(d, 84))
    return J

BDT = 1/240
SPRING = {'t': (40, .8), 'h': (26, .55), 'ra1': (58, .62), 'fa1': (58, .62), 'ra2': (44, .5), 'fa2': (44, .5),
          'rl1': (64, .8), 'fl1': (64, .8), 'rl2': (52, .68), 'fl2': (52, .68), 'sw': (72, .6)}
SPRING_KEYS = list(SPRING)

class Key:
    __slots__ = ('t', 'pose', 'x', 'alt', 'face', 'ease', 'arc', 'rot')
    def __init__(s, **kw):
        for k, v in kw.items(): setattr(s, k, v)

class Fighter:
    def __init__(s, name, look):
        s.name, s.look, s.keys = name, look, []
        s.sheath_from = None; s.glow_from = None; s.seed = (sum(map(ord, name)) % 17) * 0.7
    def key(s, t, pose, x=None, alt=0, face=None, ease='out', arc=0, rot=None, **kw):
        prev = s.keys[-1] if s.keys else None
        pz = P(pose, **kw) if isinstance(pose, str) else pose
        s.keys.append(Key(t=t, pose=pz, x=prev.x if x is None else x, alt=alt,
                          face=(prev.face if prev else 1) if face is None else face,
                          ease=ease, arc=arc, rot=(prev.rot if prev else 0) if rot is None else rot))
        s.keys.sort(key=lambda k: k.t); s._ts = [k.t for k in s.keys]
        idx = s._ts.index(t); s.dirty = min(getattr(s, 'dirty', 1e9), s._ts[idx-1] if idx > 0 else 0.0)
        return s
    def hold(s, t):
        k = s.keys[-1]; return s.key(t, dict(k.pose), x=k.x, alt=k.alt, face=k.face, rot=k.rot, ease='lin')

    def state(s, ta):
        ks = s.keys
        if ta <= ks[0].t: a = b = ks[0]; u = e = 1.0
        elif ta >= ks[-1].t: a = b = ks[-1]; u = e = 1.0
        else:
            i = bisect.bisect_right(s._ts, ta) - 1
            a, b = ks[i], ks[i+1]
            u = (ta-a.t)/(b.t-a.t); e = EASE[b.ease](u)
        pose = {}
        for k, va in a.pose.items():
            vb = b.pose[k]
            if va is None or vb is None: pose[k] = vb if u >= 0.5 else va
            else: pose[k] = lerp(va, vb, e)
        alt = lerp(a.alt, b.alt, e) + b.arc*4*u*(1-u)
        face = b.face if u > 0.12 else a.face
        return dict(pose=pose, x=lerp(a.x, b.x, e), alt=alt, face=face, rot=lerp(a.rot, b.rot, e))

    def bake(s, T):
        """Spring-damper follow of keyed angles: natural overshoot, settle and follow-through."""
        if not hasattr(s, 'X'):
            s.X, s.V, s.N, s.until = [], [], [], 0.0
        if s.dirty < s.until:
            i0 = max(0, int(s.dirty/BDT) - 1)
            del s.X[i0:]; del s.V[i0:]; del s.N[i0:]
        s.dirty = 1e9
        i = len(s.X)
        x = list(s.X[-1]) if s.X else None; v = list(s.V[-1]) if s.V else None
        while i*BDT <= T:
            p = s.state(i*BDT)['pose']
            if x is None:
                x = [p[k] if p[k] is not None else 0.0 for k in SPRING_KEYS]; v = [0.0]*len(SPRING_KEYS)
            nn = []
            for j, k in enumerate(SPRING_KEYS):
                g = p[k]
                if g is None: nn.append(True); continue
                if s.N and s.N[-1][j]: x[j], v[j] = g, 0.0
                w, z = SPRING[k]
                v[j] += (w*w*(g - x[j]) - 2*z*w*v[j]) * BDT; x[j] += v[j]*BDT
                nn.append(False)
            s.X.append(list(x)); s.V.append(list(v)); s.N.append(nn); i += 1
        s.until = (len(s.X) - 1)*BDT

    def anim(s, ta):
        """Spring-baked pose plus stance bounce and footwork."""
        ta = max(0.0, ta)
        if s.dirty <= ta + 0.02 or ta + 0.02 > getattr(s, 'until', -1): s.bake(ta + 0.5)
        st = s.state(ta); p = st['pose']
        f = ta/BDT; i = min(int(f), len(s.X) - 2); u = f - i
        for j, k in enumerate(SPRING_KEYS):
            if p[k] is not None and not s.N[i+1][j]:
                p[k] = s.X[i][j]*(1-u) + s.X[i+1][j]*u if not s.N[i][j] else s.X[i+1][j]
        ph = s.seed
        ground = st['alt'] < 2 and abs(st['rot']) % 360 < 1
        prev = s.state(max(0, ta - 0.05)); vx = (st['x'] - prev['x'])/0.05
        if ground and p['bob'] > 0:
            c = p['bob'] * (3 + 3*math.sin(ta*7.5 + ph))
            p['fl1'] += c; p['fl2'] -= c*0.8; p['rl1'] += c*0.6; p['rl2'] -= c*1.1; p['t'] += c*0.4
            p['fa1'] += math.sin(ta*7.5 + ph + 1)*3; p['ra1'] += math.sin(ta*7.5 + ph + 2)*3
            A = clamp(abs(vx)/200) * min(1, p['bob']*1.5)
            if A > 0.02:
                q = st['x']/38*st['face']; sn, cs = math.sin(q), math.cos(q)
                p['fl1'] += 20*A*sn; p['rl1'] -= 20*A*sn
                p['fl2'] += 20*A*sn - 26*A*max(0, cs); p['rl2'] -= 20*A*sn + 26*A*max(0, -cs)
        if ground and p['run'] > 0:
            A = p['run'] * clamp(abs(vx)/350)
            q = st['x']/62*st['face']; sn, cs = math.sin(q), math.cos(q)
            p['fl1'] += 48*A*sn; p['rl1'] -= 48*A*sn
            p['fl2'] += 30*A*sn - 60*A*max(0, cs); p['rl2'] -= 30*A*sn + 60*A*max(0, -cs)
            p['fa1'] -= 55*A*sn; p['ra1'] += 55*A*sn
        return st

    def world(s, st):
        """Return joints in world coords plus helper transform."""
        J = joints(st['pose']); r = math.radians(st['rot'] * 1)
        c, sn = math.cos(r), math.sin(r); f = st['face']
        L = {k: (x*c - y*sn, x*sn + y*c) for k, (x, y) in J.items()}
        low = max(v[1] for k, v in L.items() if k in ('rft', 'fft', 'rtoe', 'ftoe', 'rkn', 'fkn', 'rhand', 'fhand'))
        low = max(low, L['head'][1] + LEN['head'])
        ry = -st['alt'] - low; rx = st['x']
        Wd = {k: (rx + x*f, ry + y) for k, (x, y) in L.items()}
        def tf(lx, ly):   # body-local (after pose) -> world
            return (rx + (lx*c - ly*sn)*f, ry + (lx*sn + ly*c))
        return Wd, tf

# ---------------------------------------------------------------- camera
class Camera:
    def __init__(s): s.keys = []; s.shakes = []
    def key(s, t, cx, cy, z, ease='io', rot=0):
        s.keys.append((t, cx, cy, z, ease, rot)); s.keys.sort(key=lambda k: k[0]); return s
    def shake(s, tr, amp, d=0.4): s.shakes.append((tr, amp, d))
    def at(s, ta, tr):
        ks = s.keys
        if ta <= ks[0][0]: k = ks[0]; cx, cy, z, rot = k[1], k[2], k[3], k[5]
        elif ta >= ks[-1][0]: k = ks[-1]; cx, cy, z, rot = k[1], k[2], k[3], k[5]
        else:
            i = bisect.bisect_right([k[0] for k in ks], ta) - 1
            a, b = ks[i], ks[i+1]; e = EASE[b[4]]((ta-a[0])/(b[0]-a[0]))
            cx, cy, z, rot = (lerp(a[j], b[j], e) for j in (1, 2, 3, 5))
        sx = sy = 0.0
        for t0, amp, d in s.shakes:
            g = tr - t0
            if 0 <= g < d:
                m = amp * (1 - g/d)**2
                sx += m*math.sin(g*97 + t0*13); sy += m*math.cos(g*83 + t0*7)
        return cx, cy, z, sx, sy, rot

class View:
    def __init__(s, cam):
        s.cx, s.cy, s.z, s.sx, s.sy, s.rot = cam
        s.k = s.z * SS
        s.cr, s.sr = math.cos(math.radians(s.rot)), math.sin(math.radians(s.rot))
    def ws(s, x, y, p=1.0):
        zp = 1 + (s.z - 1)*p
        X, Y = (x - s.cx*p)*zp + s.sx, (y - s.cy*p)*zp + s.sy
        if s.rot:
            c, n = s.cr, s.sr; X, Y = X*c - Y*n, X*n + Y*c
        return ((W/2 + X)*SS, (H*HZ + Y)*SS)

# ---------------------------------------------------------------- helpers
def chain(base, n, seglen, ang0, t, amp, speed=9, phase=0.7):
    pts = [base]; p = base
    for i in range(n):
        a = ang0 + math.sin(t*speed - i*phase) * amp * (0.3 + i/n)
        p = (p[0] + math.cos(a)*seglen, p[1] + math.sin(a)*seglen); pts.append(p)
    return pts

