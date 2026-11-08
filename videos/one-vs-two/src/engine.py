"""Procedural anime fight engine: skeletal fighters, camera, time warp and effects."""
import math, bisect, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS, SS = 720, 1280, 30, 2
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

    def anim(s, ta):
        """Interpolated pose plus overlap/follow-through, stance bounce and footwork."""
        st = s.state(ta); lag = s.state(ta - 0.035); lag2 = s.state(ta - 0.07)
        p = st['pose']
        for k_, src, w in (('fa2', lag, .55), ('ra2', lag, .55), ('h', lag2, .6), ('fl2', lag, .35),
                           ('rl2', lag, .35), ('sw', lag, .3), ('t', lag, .25)):
            a_, b_ = p[k_], src['pose'][k_]
            if a_ is not None and b_ is not None: p[k_] = lerp(a_, b_, w)
        ph = s.seed
        ground = st['alt'] < 2 and abs(st['rot']) % 360 < 1
        prev = s.state(ta - 0.05); vx = (st['x'] - prev['x'])/0.05
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

# ---------------------------------------------------------------- drawing helpers
def seg(d, a, b, w, col):
    d.line([a, b], fill=col, width=max(1, int(w)))
    r = w/2
    for p in (a, b): d.ellipse([p[0]-r, p[1]-r, p[0]+r, p[1]+r], fill=col)
def dot(d, p, r, col): d.ellipse([p[0]-r, p[1]-r, p[0]+r, p[1]+r], fill=col)
def ring(d, p, r, col, w):
    d.ellipse([p[0]-r, p[1]-r, p[0]+r, p[1]+r], outline=col, width=max(1, int(w)))

def chain(base, n, seglen, ang0, t, amp, speed=9, phase=0.7):
    pts = [base]; p = base
    for i in range(n):
        a = ang0 + math.sin(t*speed - i*phase) * amp * (0.3 + i/n)
        p = (p[0] + math.cos(a)*seglen, p[1] + math.sin(a)*seglen); pts.append(p)
    return pts

def ribbon(d, pts, w0, w1, col, outline=None, ow=0):
    n = len(pts)-1
    for pas in ((outline, ow), (col, 0)) if outline else ((col, 0),):
        c, extra = pas
        for i in range(n):
            w = lerp(w0, w1, i/n) + extra
            seg(d, pts[i], pts[i+1], w, c)

# ---------------------------------------------------------------- fighter rendering
def bez(a, b, c, bend=0.8, n=9):
    m = ((a[0]+c[0])/2, (a[1]+c[1])/2)
    q = (b[0] + (b[0]-m[0])*bend, b[1] + (b[1]-m[1])*bend)
    out = []
    for i in range(n):
        t = i/(n-1); u = 1-t
        out.append((u*u*a[0] + 2*u*t*q[0] + t*t*c[0], u*u*a[1] + 2*u*t*q[1] + t*t*c[1]))
    return out

def tube(d, pts, w0, w1, col):
    n = len(pts); L, R = [], []
    for i, p in enumerate(pts):
        a, b = pts[max(0, i-1)], pts[min(n-1, i+1)]
        dx, dy = b[0]-a[0], b[1]-a[1]; ln = math.hypot(dx, dy) or 1
        w = lerp(w0, w1, i/(n-1))/2
        L.append((p[0] - dy/ln*w, p[1] + dx/ln*w)); R.append((p[0] + dy/ln*w, p[1] - dx/ln*w))
    d.polygon(L + R[::-1], fill=col)
    dot(d, pts[0], w0/2, col); dot(d, pts[-1], w1/2, col)

def fighter_parts(F, st, v, ta, vel):
    """Drawable primitives, back to front. Thick bendy limbs with mass."""
    Wd, tf = F.world(st); lk = F.look; f = st['face']; k = v.k
    S = lambda name: v.ws(*Wd[name])
    out = []
    ang_head = math.radians(st['pose']['t'] + st['pose']['h'] + st['rot'])
    hc = Wd['head']
    def hl(lx, ly):
        x = lx*math.cos(ang_head) - ly*math.sin(ang_head)
        y = lx*math.sin(ang_head) + ly*math.cos(ang_head)
        return v.ws(hc[0] + x*f, hc[1] + y)
    tx, ty = -vel[0]*0.6 - 60, -vel[1]*0.4 + 25
    base_ang = math.atan2(ty, tx)
    wiggle = 0.25 + min(0.5, math.hypot(*vel)/900)
    if lk['kind'] == 'hero':
        nk = v.ws(*Wd['neck'])
        out.append(('ribbon', chain(nk, 10, 11*k, base_ang, ta, wiggle, speed=11), 11*k, 3*k, hexc(lk['acc'])))
        out.append(('ribbon', chain(nk, 8, 10*k, base_ang + 0.25, ta + 0.6, wiggle*1.2, speed=12), 8*k, 2*k, shade(hexc(lk['acc']), 0.7)))
    if lk['kind'] == 'shade':
        out.append(('ribbon', chain(hl(-13, -4), 9, 10*k, base_ang + 0.35, ta + 0.3, wiggle*1.1, speed=10), 10*k, 2*k, hexc(lk['hair'])))
    top, pants, skin = hexc(lk['top']), hexc(lk['pants']), hexc(lk['skin'])
    aw, lw, tw = 12*k, 15*k, 24*k
    def arm(s, col, hand):
        pts = bez(S('sh'), S(s+'el'), S(s+'hand'))
        return ('tube', pts, aw*1.15, aw*0.8, col, hand, aw*0.66)
    def leg(s, col):
        pts = bez(S('hip'), S(s+'kn'), S(s+'ft'))
        return ('leg', pts, lw*1.25, lw*0.75, col, [S(s+'ft'), S(s+'toe')])
    out.append(arm('r', shade(top, 0.6), shade(skin, 0.65)))
    out.append(leg('r', shade(pants, 0.62)))
    out.append(leg('f', pants))
    out.append(('torso', S('hip'), S('chest'), S('neck'), tw, top, hexc(lk['acc']), pants))
    out.append(('head', S('head'), LEN['head']*k, skin, lk, hl, ta))
    if F.sheath_from is not None and ta >= F.sheath_from:
        out.append(('sheath', v.ws(*tf(-6, -6)), v.ws(*tf(-66, 26)), k))
    out.append(arm('f', top, skin))
    if 'tip' in Wd:
        glow = F.glow_from is not None and ta >= F.glow_from
        out.append(('sword', S('pommel'), S('guardp'), S('tip'), k, glow, hexc(lk['acc'])))
    return out

def draw_parts(d, glow, parts, ghost=None):
    for p in parts:
        kind = p[0]
        if kind == 'ribbon':
            ribbon(d, p[1], p[2], p[3], ghost or p[4]); continue
        if kind == 'tube':
            pts, w0, w1, col, hand, hr = p[1:]
            tube(d, pts, w0, w1, ghost or col)
            dot(d, pts[-1], hr, ghost or hand)
            if not ghost:
                hcol = shade(col, 1.3)
                rim = [(x - w0*0.2, y - w0*0.22) for x, y in pts[1:-1]]
                d.line(rim, fill=hcol, width=max(1, int(w0*0.2)))
        elif kind == 'leg':
            pts, w0, w1, col, foot = p[1:]
            tube(d, pts, w0, w1, ghost or col)
            tube(d, [foot[0], mix(foot[0], foot[1], 0.5), foot[1]], w1*1.05, w1*0.8, ghost or shade(col, 0.8))
            if not ghost:
                rim = [(x - w0*0.2, y - w0*0.12) for x, y in pts[1:-2]]
                d.line(rim, fill=shade(col, 1.7), width=max(1, int(w0*0.16)))
        elif kind == 'torso':
            hip, chest, neck, w, col, acc, pants = p[1:]
            mid = mix(hip, chest, 0.5)
            pts = [hip, mid, chest]
            tube(d, [neck, mix(neck, chest, 0.5), chest], w*0.35, w*0.45, ghost or col)
            tube(d, pts, w*0.88, w*1.08, ghost or col)
            if ghost: continue
            tube(d, [hip, mix(hip, chest, 0.12), mix(hip, chest, 0.24)], w*0.95, w*0.92, pants)
            rim = [(x - w*0.25, y - w*0.1) for x, y in pts]
            d.line(rim, fill=shade(col, 1.25), width=max(1, int(w*0.16)))
            dx, dy = chest[0]-hip[0], chest[1]-hip[1]; L = math.hypot(dx, dy) or 1
            ux, uy = dx/L, dy/L; c0 = (hip[0]+ux*w*0.55, hip[1]+uy*w*0.55)
            px, py = -uy*w*0.5, ux*w*0.5
            d.line([(c0[0]-px, c0[1]-py), (c0[0]+px, c0[1]+py)], fill=acc, width=max(1, int(w*0.22)))
        elif kind == 'head':
            c, r, skin, lk, hl, ta = p[1:]
            kk = r/LEN['head']
            if ghost:
                dot(d, c, r*1.1, ghost); continue
            if lk['kind'] == 'shade':
                hood = [(14, -2), (12, -12), (2, -18), (-10, -16), (-22, -8), (-14, 4), (-6, 14), (8, 13)]
                d.polygon([hl(x*1.12, y*1.12) for x, y in hood], fill=hexc(lk['hair']))
                dot(d, c, r*1.05, hexc(lk['hair']))
                d.polygon([hl(15, -3), hl(4, -7), hl(3, 7), hl(13, 8)], fill=skin)
            else:
                dot(d, c, r, skin)
                d.chord([c[0]-r, c[1]-r, c[0]+r, c[1]+r], 200, 340, fill=shade(skin, 1.15)) if False else None
            if lk['kind'] == 'hero':
                sw = math.sin(ta*7)*1.5
                hair = [(13, -3), (11, -12), (3, -18), (7, -27), (-3, -20), (-9, -30+sw), (-12, -19),
                        (-25, -24+sw), (-19, -12), (-33, -10+sw), (-19, -3), (-28, 5+sw), (-14, 5), (-13, 12), (-4, 7), (2, -6)]
                d.polygon([hl(x, y) for x, y in hair], fill=hexc(lk['hair']))
                d.line([hl(-4, -16), hl(-20, -13), hl(-25, -4)], fill=hexc(lk['hair_hl']), width=max(1, int(2.2*kk)))
                d.line([hl(15, -9), hl(-13, -11)], fill=hexc(lk['acc']), width=max(1, int(3.5*kk)))
            if lk['kind'] == 'oni':
                for hp in (((3, -12), (10, -31), (12, -10)), ((-6, -13), (-9, -32), (1, -14))):
                    d.polygon([hl(*q) for q in hp], fill=hexc(lk['hair']))
                d.line([hl(3, 7), hl(14, 7)], fill=hexc(lk['acc']), width=max(1, int(2.4*kk)))
            e = hl(9, -2)
            d.line([hl(5, -3), hl(13, -2)], fill=hexc(lk['eye']), width=max(1, int(3*kk)))
            if lk['kind'] != 'hero' or lk.get('eyeglow'):
                dot(glow, e, 7*kk, shade(hexc(lk['eye']), 0.9))
        elif kind == 'sheath':
            a, b, k = p[1:]
            if ghost: continue
            seg(d, a, b, 5.5*k, (44, 30, 54)); seg(d, a, mix(a, b, 0.12), 6*k, (200, 170, 90))
        elif kind == 'sword':
            pm, gp, tip, k, gl, acc = p[1:]
            if ghost: seg(d, gp, tip, 3*k, ghost); continue
            seg(d, pm, gp, 5*k, (60, 40, 70))
            seg(d, gp, tip, 3.4*k, (236, 242, 255)); dot(d, gp, 4*k, (220, 190, 100))
            if gl: seg(glow, gp, tip, 10*k, shade(acc, 0.8))

# ---------------------------------------------------------------- effects
class FX:
    def __init__(s, kind, tr, d, layer='front', **kw):
        s.kind, s.tr, s.d, s.layer, s.kw = kind, tr, d, layer, kw
        s.rng = random.Random(int(tr*1000) + hash(kind) % 997)
        s.seed = s.rng.random()*1000

def starburst(d, c, r_in, r_out, n, rot, col, rng):
    for i in range(n):
        a = rot + i*2*math.pi/n + rng.uniform(-0.12, 0.12)
        ro = r_out * rng.uniform(0.55, 1.15)
        w = 0.06 + rng.uniform(0, 0.05)
        p1 = (c[0] + math.cos(a-w)*r_in, c[1] + math.sin(a-w)*r_in)
        p2 = (c[0] + math.cos(a)*ro, c[1] + math.sin(a)*ro)
        p3 = (c[0] + math.cos(a+w)*r_in, c[1] + math.sin(a+w)*r_in)
        d.polygon([p1, p2, p3], fill=col)

def crescent(d, c, r, a0, a1, w, col, squash=1.0, steps=28):
    outer, inner = [], []
    for i in range(steps+1):
        u = i/steps; a = a0 + (a1-a0)*u
        th = w * math.sin(math.pi*u)**0.8
        outer.append((c[0] + math.cos(a)*r, c[1] + math.sin(a)*r*squash))
        inner.append((c[0] + math.cos(a)*(r-th), c[1] + math.sin(a)*(r-th)*squash))
    d.polygon(outer + inner[::-1], fill=col)

def draw_fx(e, age, L, v, fi):
    k = v.k; kw = e.kw; u = age / e.d; rng = random.Random(e.seed)
    front, back, glow = L['front'], L['back'], L['glow']
    acc = hexc(kw.get('col', '#ffffff'))
    if e.kind in ('impact', 'spark'):
        c = v.ws(kw['x'], kw['y']); sz = kw.get('size', 1.0) * k
        big = e.kind == 'impact'
        if age < 0.11:
            s = 1 - age/0.11
            starburst(front, c, 6*sz, (95 if big else 40)*sz*(0.6 + 0.6*(1-s)), 14 if big else 9,
                      rng.random()*6.3, (255, 255, 255, int(255*s**0.5)), random.Random(e.seed+1))
            dot(glow, c, (70 if big else 28)*sz, shade(acc, 1.0*s))
            dot(front, c, (26 if big else 10)*sz*(1+age*6), (255, 255, 255, int(255*s)))
        rr = (24 + 230*(1-(1-u)**3)) * sz * (1 if big else 0.45)
        ring(front, c, rr, (255, 255, 255, int(200*(1-u)**1.5)), max(1, 6*sz*(1-u)))
        if big: ring(glow, c, rr*0.9, shade(acc, 0.6*(1-u)**1.5), max(1, 9*sz*(1-u)))
        # sparks
        n = 22 if big else 12
        r2 = random.Random(e.seed+2)
        for i in range(n):
            a = r2.uniform(0, 6.283); sp = r2.uniform(250, 900 if big else 600)
            life = r2.uniform(0.25, 0.55)
            if age > life: continue
            g = age; q = 1 - g/life
            p1 = (kw['x'] + math.cos(a)*sp*g, kw['y'] + math.sin(a)*sp*g + 500*g*g)
            p0 = (kw['x'] + math.cos(a)*sp*max(0, g-0.03), kw['y'] + math.sin(a)*sp*max(0, g-0.03) + 500*max(0, g-0.03)**2)
            s1, s0 = v.ws(*p1), v.ws(*p0)
            seg(front, s0, s1, 2.4*k*q, (255, 250, 230, int(255*q)))
            seg(glow, s0, s1, 6*k*q, shade(acc, q))
    elif e.kind == 'slash':
        c = v.ws(kw['x'], kw['y']); r = kw.get('r', 90)*k
        a0, a1 = math.radians(kw['a0']), math.radians(kw['a1'])
        grow = clamp(age/0.07); fade_ = 1 - clamp((age-0.06)/(e.d-0.06))
        aa = a0 + (a1-a0)*EASE['out'](grow)
        w = kw.get('w', 26)*k*fade_**0.6; sq = kw.get('squash', 1.0)
        if w > 0.5:
            crescent(glow, c, r*1.03, a0, aa, w*1.9, shade(acc, 0.9*fade_), sq)
            crescent(front, c, r, a0, aa, w, (255, 255, 255, int(255*fade_)), sq)
    elif e.kind == 'ring':
        c = v.ws(kw['x'], kw.get('y', 0)); rr = (20 + kw.get('r', 260)*EASE['out'](u))*k
        sq = kw.get('squash', 0.22)
        ww = max(1, 10*k*(1-u))
        back.ellipse([c[0]-rr, c[1]-rr*sq, c[0]+rr, c[1]+rr*sq], outline=(255, 245, 235, int(200*(1-u))), width=int(ww))
        glow.ellipse([c[0]-rr, c[1]-rr*sq, c[0]+rr, c[1]+rr*sq], outline=shade(acc, 0.7*(1-u)), width=int(ww*2))
    elif e.kind == 'dust':
        n = kw.get('n', 16); dirn = kw.get('dir', 0); spread = kw.get('spread', 1.0)
        r2 = random.Random(e.seed+3)
        for i in range(n):
            side = r2.choice((-1, 1)) if dirn == 0 else -dirn
            sp = r2.uniform(60, 320)*spread; life = r2.uniform(0.5, 1.1)*e.d
            if age > life: continue
            q = age/life
            x = kw['x'] + side*sp*(1-(1-q)**2)*0.9 + r2.uniform(-20, 20)
            y = -r2.uniform(0, 30) - 50*q*r2.uniform(0.3, 1.2)
            rr = (10 + 34*q*r2.uniform(0.6, 1.4))*k*kw.get('size', 1)
            col = kw.get('col_rgb', (150, 120, 150))
            back.ellipse([*map(lambda z: z, (v.ws(x, y)[0]-rr, v.ws(x, y)[1]-rr, v.ws(x, y)[0]+rr, v.ws(x, y)[1]+rr))],
                         fill=col + (int(150*(1-q)**1.5),))
    elif e.kind == 'debris':
        r2 = random.Random(e.seed+4)
        for i in range(kw.get('n', 14)):
            vx = r2.uniform(-350, 350); vy = -r2.uniform(250, 750)
            g = age; y = vy*g + 1400*g*g
            if y > 0: continue
            p = v.ws(kw['x'] + vx*g, y); s = r2.uniform(3, 8)*k
            front.polygon([(p[0]-s, p[1]), (p[0], p[1]-s*0.8), (p[0]+s*0.9, p[1]+s*0.3), (p[0]+s*0.1, p[1]+s)],
                          fill=(60, 45, 70, 255))
    elif e.kind == 'crack':
        c = (kw['x'], 0); fadeg = clamp(1 - (age - e.d + 0.6)/0.6) if age > e.d - 0.6 else 1
        grow = clamp(age/0.15)
        r2 = random.Random(e.seed+5)
        for i in range(kw.get('n', 9)):
            a = r2.uniform(-1, 1)
            pts = [c]; p = c; L = r2.uniform(80, 220)*grow
            for j in range(5):
                p = (p[0] + math.copysign(1, a)*L/5*abs(math.cos(a)) + r2.uniform(-10, 10), p[1] + r2.uniform(-4, 4)*0.6 + 3*math.sin(a))
                pts.append(p)
            sp = [v.ws(*q) for q in pts]
            back.line(sp, fill=(10, 6, 18, int(240*fadeg)), width=max(1, int(4*k)))
            if kw.get('hot'):
                glow.line(sp, fill=shade(acc, 0.35*fadeg), width=max(1, int(3*k)))
    elif e.kind == 'speedlines':
        r2 = random.Random(fi*7 + 1)
        cx, cy = v.ws(*kw['focus']) if kw.get('focus') else (W*SS/2, H*SS*0.5)
        a_in = clamp(age/0.08) * clamp((e.d-age)/0.1)
        if kw.get('mode', 'radial') == 'radial':
            for i in range(70):
                a = r2.uniform(0, 6.283); r0 = r2.uniform(0.35, 0.6)*W*SS; r1 = 1.6*H*SS
                w = r2.uniform(0.01, 0.025)
                pts = [(cx + math.cos(a)*r0, cy + math.sin(a)*r0),
                       (cx + math.cos(a-w)*r1, cy + math.sin(a-w)*r1), (cx + math.cos(a+w)*r1, cy + math.sin(a+w)*r1)]
                front.polygon(pts, fill=(255, 255, 255, int(r2.uniform(60, 150)*a_in)))
        else:
            for i in range(45):
                y = r2.uniform(0, H*SS); x0 = r2.uniform(-0.2, 1)*W*SS; ln = r2.uniform(0.2, 0.7)*W*SS
                th = r2.uniform(1, 5)*SS
                front.polygon([(x0, y), (x0+ln, y-th/2), (x0+ln, y+th/2)], fill=(255, 255, 255, int(r2.uniform(50, 140)*a_in)))
    elif e.kind == 'aura':
        F, st = kw['fighter'], kw['state']
        Wd, _ = F.world(st)
        on = clamp(age/0.4) * clamp((e.d-age)/0.5)
        hip, head = Wd['hip'], Wd['head']
        r2 = random.Random(e.seed+6)
        ka = min(k, 2.4*SS)
        for i in range(20):
            ph = r2.random(); life = r2.uniform(0.35, 0.7)
            q = ((age/life) + ph) % 1.0
            ox = r2.uniform(-40, 40); base_y = r2.uniform(-10, 30)
            x = hip[0] + ox*(1-q*0.4) + math.sin(q*9 + i)*8
            y = hip[1] + base_y - q*170
            rr = (11*(1-q) + 3)*ka
            p = v.ws(x, y)
            col = shade(acc, (1-q)*on*0.5)
            glow.polygon([(p[0]-rr*0.6, p[1]), (p[0], p[1]-rr*2.2), (p[0]+rr*0.6, p[1]), (p[0], p[1]+rr*0.7)], fill=col)
            if i % 3 == 0:
                back.polygon([(p[0]-rr*0.3, p[1]), (p[0], p[1]-rr*1.5), (p[0]+rr*0.3, p[1])], fill=(230, 255, 255, int(120*(1-q)*on)))
        # lightning
        r3 = random.Random(fi//2*31 + 5)
        if on > 0.3 and (fi // 3) % 3 == 0:
            for j in range(1):
                p = (hip[0] + r3.uniform(-50, 50), hip[1] + r3.uniform(-120, 20)); pts = [v.ws(*p)]
                for s in range(6):
                    p = (p[0] + r3.uniform(-22, 22), p[1] + r3.uniform(-26, 14)); pts.append(v.ws(*p))
                front.line(pts, fill=(235, 255, 255, int(255*on)), width=max(1, int(2*k)))
                glow.line(pts, fill=shade(acc, on), width=max(1, int(7*k)))
        dot(glow, v.ws(hip[0], hip[1]-60), 48*k, shade(acc, 0.12*on))
    elif e.kind == 'glint':
        c = v.ws(kw['x'], kw['y']); s = math.sin(math.pi*u)
        L = kw.get('size', 30)*k*s
        for a in (0, math.pi/2):
            front.polygon([(c[0]-math.cos(a)*L, c[1]-math.sin(a)*L), (c[0]+math.sin(a)*L*0.08, c[1]-math.cos(a)*L*0.08),
                           (c[0]+math.cos(a)*L, c[1]+math.sin(a)*L), (c[0]-math.sin(a)*L*0.08, c[1]+math.cos(a)*L*0.08)],
                          fill=(255, 255, 255, int(255*s)))
        dot(glow, c, L*0.7, shade(acc, s))

# ---------------------------------------------------------------- blade trail
def blade_trail(F, v, ta, L, steps=10, dt=1/140):
    pts = []
    for i in range(steps):
        st = F.anim(ta - i*dt)
        if st['pose']['sw'] is None: break
        Wd, _ = F.world(st)
        pts.append((v.ws(*Wd['guardp']), v.ws(*Wd['tip'])))
    if len(pts) < 3: return
    travel = sum(math.dist(pts[i][1], pts[i+1][1]) for i in range(len(pts)-1))
    if travel < 40*v.k: return
    acc = hexc(F.look['acc'])
    for i in range(len(pts)-1):
        q = 1 - i/(len(pts)-1)
        (b0, t0), (b1, t1) = pts[i], pts[i+1]
        m0, m1 = mix(b0, t0, 0.35), mix(b1, t1, 0.35)
        L['front'].polygon([m0, t0, t1, m1], fill=(255, 255, 255, int(200*q**1.5)))
        L['glow'].polygon([b0, t0, t1, b1], fill=shade(acc, 0.8*q))

# ---------------------------------------------------------------- text
_fonts = {}
def font(sz):
    if sz not in _fonts: _fonts[sz] = ImageFont.truetype(FONT, sz)
    return _fonts[sz]
