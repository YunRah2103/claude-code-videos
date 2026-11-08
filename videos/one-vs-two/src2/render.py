"""ONE vs TWO (mocap edition): plain stick fighters driven by real motion capture.

Usage:
  python render.py still OUTDIR t1 t2 ...      # preview PNGs (real seconds)
  python render.py video OUT.mp4 [start end]  # render (real seconds)
"""
import math, os, sys, random, subprocess, wave
import numpy as np
import skia
from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'src'))
import render as R                       # Skia helpers, background, effects, post (original renderer)
from engine import Warp, EASE, hexc, shade, mix, clamp, lerp
import motion
from motion import Actor, fk, clip
from mocap import IDX

DUR = 36.0
FPS = 60
W, H, SS = R.W, R.H, R.SS
WO, HO = R.WO, R.HO
PT, poly, shape, radial = R.PT, R.poly, R.shape, R.radial

COL = {'hero': (240, 244, 252), 'oni': (214, 44, 60), 'kage': (134, 84, 214)}
ACC = {'hero': '#36d9ff', 'oni': '#ff6a3d', 'kage': '#c77dff'}
H_, A_, B_ = Actor('hero'), Actor('oni'), Actor('kage')
ACT = {'hero': H_, 'oni': A_, 'kage': B_}
WARP = Warp()
FXL, HITS, CUES, POST, TEXT, SHOTS = [], [], [], [], [], []
SWORD = (19.7, 27.2)
STANCE = ('punch', 0.05)

def fx(kind, ta, d, layer='front', **kw): FXL.append((ta, kind, d, layer, kw))
def sfx(ta, name, vol=1.0): CUES.append((ta, name, vol))
def post(kind, ta, d, amt=1.0): POST.append((kind, ta, d, amt))
def stance(a, t, x=None, face=None, blend=0.2): a.hold(t, STANCE[0], STANCE[1], x=x, face=face, blend=blend)

def strike(a, t_hit, name, u_hit, joint, tx, ua=None, ub=None, speed=1.0, rm=1.0, contact=14, hit=True,
           big=True, stop=0.07, shake=8, col=None, sound=None, size=1.0, blend=0.12):
    """Start clip `name` so that `joint` reaches target x `tx` at t_hit; registers the impact."""
    c = clip(name); ua = max(0.0, u_hit - 0.55) if ua is None else ua
    t0 = t_hit - (u_hit - ua)/speed
    J = fk(c.at(u_hit)); jdx = J[IDX[joint]][0] - J[0][0]
    dr = (c.at(u_hit)[0][0] - c.at(ua)[0][0])*rm
    cur = a._endx(t0); fdir = 1 if tx >= cur else -1
    face = fdir*(1 if jdx >= 0 else -1)
    x = tx - fdir*contact - face*(dr + jdx)
    gap = x - cur
    if abs(gap) > 60:                      # run in from where the fighter really is
        trun = max(0.25, abs(gap)/420); t_run = t0 - trun
        a.play(t_run, 'run', loop=True, a=0, b=0.8, speed=1.12, x=a._endx(t_run), face=1 if gap > 0 else -1, blend=0.15)
    a.play(t0, name, a=ua, b=ub, speed=speed, x=x, face=face, rm=rm, blend=blend)
    seg = [q for q in a.segs if q.t == t0][-1]
    for _ in range(3):                     # correct so the contact really lands at tx
        J, _z = a.joints(t_hit); seg.x += (tx - fdir*contact) - J[IDX[joint]][0]
    sfx(t0 + 0.05, 'whoosh', 0.7)
    if hit:
        HITS.append((t_hit, a, joint, big, col or ACC[a.name], sound, size))
        if stop: WARP.stop(t_hit, stop)
        if shake: post('shake', t_hit, 0.4, shake)
    return face

def knock(v, t, vx, up=200, lie='faceup', dur=0.55, spin=0.0, slam=1.0):
    v.fall(t, vx, up=up, lie=lie, dur=dur, spin=spin)
    land = t + dur
    fx('dust', land, 1.0, layer='back', actor=v, n=14, size=slam); fx('ring', land, 0.5, layer='back', actor=v, r=150*slam)
    fx('debris', land, 0.9, actor=v, n=8); post('shake', land, 0.5, 10*slam); sfx(land, 'slam', 0.8*slam)
    return land

def X(a, t): return a.pose(t)[0][0]

# ================================================================= choreography (anim time)
TK = {'hero': 'cmu:14_02', 'oni': 'cmu:14_01', 'kage': 'cmu:13_17'}
def box(a, t, face, keys=(), u0=None, blend=0.28):
    a.box(t, TK[a.name], face, keys=keys, u0=u0, blend=blend)
def slow_ramp(t, d, low=0.3):
    n = 6
    for i in range(n):
        r = low + (1 - low)*abs((i + 0.5)/n*2 - 1)**1.5
        WARP.slow(t + d*i/n, d/n, r)

# --- intro: Kaze warms up; Oni runs in, Kage flips in
box(H_, 0.0, 1, keys=[(0.0, 0.0)], u0=0.6)
TEXT.append(('title', 0.4, 2.3))
A_.play(2.6, 'run', loop=True, x=-760, face=1, a=0, b=0.8, speed=1.05)
box(A_, 3.85, 1, keys=[(4.6, -200)])
fx('dust', 3.9, 0.9, layer='back', actor=A_, n=10, dir=-1)
B_.play(3.9, 'sideflip', a=0.25, x=430, face=-1, speed=1.25)
box(B_, 5.5, -1, keys=[(6.0, 240)]); fx('dust', 5.5, 0.8, layer='back', actor=B_, n=10)
sfx(4.6, 'whoosh', 0.9)
box(H_, 4.1, -1, keys=[(5.0, 10)])
TEXT += [('card', 4.05, 1.1, 'AKA ONI', 'oni'), ('card', 5.6, 1.1, 'KAGE', 'kage'), ('card', 6.3, 0.7, 'KAZE', 'hero')]

# --- first exchange: Oni and Kaze trade in close (punches come from the real sparring takes)
box(A_, 5.9, 1, keys=[(6.7, -68), (7.6, -62), (8.0, -95), (8.6, -66), (9.2, -70)], u0=4.1)
box(H_, 6.3, -1, keys=[(6.8, 8), (7.7, 14), (8.3, -8), (9.2, 4)], u0=5.1)
box(B_, 6.6, -1, keys=[(7.8, 205), (9.3, 165)])

# --- Kage cuts in with a spin kick; Kaze answers with a spinning high kick
t = 10.0
strike(B_, t, 'spinkick', 0.8, 'rtoe', X(H_, t - 0.3), ua=0.3, col=ACC['kage'], stop=0.04, shake=12, size=1.2, blend=0.22)
H_.flinch(t, 0.7, 0.4).shove(t, -85, 0.4)
box(H_, t + 0.05, 1, keys=[(t + 0.6, X(H_, t) - 85)])
box(B_, t + 0.55, -1, keys=[(t + 1.0, X(B_, t + 0.5) + 30)])
box(A_, 9.3, 1, keys=[(10.2, -170), (11.6, -150)])
t2 = 11.25
strike(H_, t2, 'spin', 1.75, 'rtoe', X(B_, t2 - 0.4), ua=1.3, ub=2.2, speed=1.2, stop=0.05, shake=14, size=1.3, blend=0.22)
knock(B_, t2, 260, up=220, lie='facedown', dur=0.7, spin=1.0)
B_.getup(t2 + 1.0, 'facedown', speed=2.0)
box(B_, t2 + 1.0 + 3.03/2.0 - 0.2, -1)
box(H_, t2 + 0.5, -1, keys=[(t2 + 1.2, X(H_, t2 + 0.5) - 20)])

# --- Oni presses again; Kaze front-kicks him away
xh = X(H_, 12.4)
box(A_, 11.7, 1, keys=[(12.5, xh - 72), (13.4, xh - 64), (14.0, xh - 76)], u0=9.7)
box(H_, 12.4, -1, keys=[(13.3, xh + 5), (14.0, xh - 5)], u0=12.0)
t = 14.55
strike(H_, t, 'kick', 0.67, 'rtoe', X(A_, t - 0.4), ua=0.22, stop=0.04, shake=12, size=1.2, blend=0.22)
A_.flinch(t, 0.7, 0.45).shove(t, -120, 0.5)
box(A_, t + 0.05, 1, keys=[(t + 0.8, X(A_, t) - 120)])
box(H_, t + 0.6, -1)

# --- Kage punches from behind, Oni's spin kick sends Kaze down
t = 15.75
strike(B_, t, 'punch', 0.83, 'rhand', X(H_, t - 0.3), ua=0.45, ub=1.1, col=ACC['kage'], big=False, stop=0, shake=6, blend=0.22)
H_.flinch(t, 0.55, 0.3).shove(t, -25, 0.25)
t = 16.5
strike(A_, t, 'spinkick', 0.8, 'rtoe', X(H_, t - 0.2), ua=0.3, col=ACC['oni'], stop=0.08, shake=22, size=1.6, blend=0.22)
post('iframe', t, 0.07); post('chroma', t, 0.5, 7); slow_ramp(t - 0.25, 0.7, 0.3)
land = knock(H_, t, 300, up=220, lie='faceup', dur=0.75, spin=-1.0, slam=1.6)
xd = X(H_, land + 0.2)
box(B_, 16.4, -1, keys=[(17.4, xd + 170)]); box(A_, t + 0.5, 1, keys=[(17.6, xd - 175)])
for tt in (17.6, 18.2, 18.8): sfx(tt, 'heart', 1.0)

# --- awakening
tg = 18.6
H_.getup(tg, 'faceup', speed=1.5)
up = tg + 3.77/1.5
fx('aura', tg + 0.6, 30 - tg, actor=H_, col=ACC['hero']); sfx(tg + 0.3, 'rumble', 1.0)
box(H_, up - 0.15, 1, keys=[(up + 0.3, X(H_, up - 0.15))])
fx('glint', up - 0.4, 0.4, actor=H_, joint='head', col='#7ff7ff', size=40); sfx(up - 0.4, 'shing', 0.6)
post('flash', up + 0.05, 0.35); post('shake', up + 0.05, 0.7, 18); fx('ring', up + 0.05, 0.7, layer='back', actor=H_, r=380, col=ACC['hero'])
WARP.stop(up + 0.05, 0.06); sfx(up + 0.05, 'boom', 1.0)
for v in (A_, B_):
    d = 1 if X(v, up) > X(H_, up) else -1
    v.flinch(up + 0.05, 0.55, 0.4).shove(up + 0.05, 90*d, 0.5)
SWORD = (up + 0.25, 30.0); sfx(SWORD[0], 'shing', 0.9)

# --- sword: slash through Oni, spinning cut on Kage
t = up + 1.35
strike(H_, t, 'punch', 0.83, 'rhand', X(A_, t - 0.5), ua=0.45, ub=1.15, shake=14, size=1.3, sound='cut', stop=0.04, blend=0.2)
fx('slash', t - 0.01, 0.3, actor=A_, joint='chest', r=95, a0=200, a1=340, w=30, squash=0.5, col=ACC['hero'])
knock(A_, t, -380 if X(A_, t) < X(H_, t) else 380, up=200, lie='faceup', dur=0.65)
t2 = t + 1.1
strike(H_, t2, 'spin', 1.75, 'rtoe', X(B_, t2 - 0.4), ua=1.2, ub=2.25, speed=1.3, shake=16, size=1.4, sound='cut', stop=0.04, blend=0.2)
fx('slash', t2 - 0.01, 0.32, actor=B_, joint='chest', r=110, a0=-100, a1=80, w=32, col=ACC['hero'])
knock(B_, t2, 360 if X(B_, t2) > X(H_, t2) else -360, up=260, lie='facedown', dur=0.75, spin=1.2)
fh = -1 if X(A_, t2 + 0.6) < X(H_, t2 + 0.6) else 1
box(H_, t2 + 0.55, fh)

# --- final: both rise and charge; one spinning draw-cut
tg2 = t2 + 1.3
A_.getup(tg2, 'faceup', speed=2.1); B_.getup(tg2 + 0.15, 'facedown', speed=2.0)
tc = tg2 + 2.0
xh = X(H_, tc)
tf = tc + 1.15
for v, gap, dt in ((B_, 75, 0.0), (A_, 165, 0.12)):
    x0 = X(v, tc); d = 1 if x0 > xh else -1
    dist = abs(x0 - (xh + d*gap)); sp_ = max(0.2, dist/((tf - tc - dt)*374))
    v.play(tc + dt, 'run', loop=True, a=0, b=0.8, speed=sp_, x=x0, face=-d, blend=0.25)
H_.play(tf - 0.12, 'spin', a=1.55, b=2.4, speed=2.2, x=xh, blend=0.25)
slow_ramp(tf - 0.2, 0.55, 0.3); WARP.stop(tf, 0.2)
fx('speedlines', tf - 0.1, 0.4, mode='horiz'); post('dark', tf - 0.1, 0.8, 0.75)
for v in (A_, B_):
    d = 1 if X(v, tf) > xh else -1
    fx('slash', tf, 0.45, actor=v, joint='chest', r=110, a0=200, a1=330, w=36, col=ACC['hero'])
    fx('slash', tf + 0.04, 0.45, actor=v, joint='chest', r=110, a0=-30, a1=110, w=36, col=ACC['hero'])
    fx('impact', tf, 0.5, actor=v, joint='chest', col=ACC['hero'], size=1.4)
    knock(v, tf + 0.02, (380 if v is B_ else 280)*d, up=170, lie='faceup' if v is A_ else 'facedown', dur=0.8, slam=1.2)
post('flash', tf, 0.4); post('iframe', tf, 0.08); post('shake', tf, 0.8, 22); post('chroma', tf, 0.6, 8)
sfx(tf, 'cut', 1.0); sfx(tf + 0.05, 'boom', 1.0)
box(H_, tf + 0.55, 1, blend=0.4)
H_.play(tf + 2.3, 'walk', loop=True, a=0, b=1.3, speed=0.8, face=1, blend=0.5)
SWORD = (SWORD[0], tf + 2.0); sfx(tf + 2.0, 'chin', 0.9)
TEXT.append(('fin', tf + 3.0, 2.6)); post('fade', tf + 4.6, 1.0)
ANIM_END = tf + 5.7

# --- automatic hits from the sparring takes: a punch that reaches an opponent's torso lands
def auto_hits():
    for a in ACT.values():
        for g in [q for q in a.segs if q.kind == 'box']:
            nxt = [q.t for q in a.segs if q.t > g.t]; t_end = min(nxt) if nxt else ANIM_END
            ts = np.arange(g.t + g.blend, t_end - 0.05, 1/60)
            for j in ('rhand', 'lhand'):
                reach = []
                for t in ts:
                    J, _ = a.joints(t); reach.append(abs(J[IDX[j]][0] - J[0][0]))
                for i in range(6, len(ts) - 6):
                    if reach[i] < 56 or reach[i] < max(reach[i-6:i+7]): continue
                    t = ts[i]; J, _ = a.joints(t); hx, hy = J[IDX[j]]
                    for v in ACT.values():
                        if v is a: continue
                        Jv, _ = v.joints(t)
                        if abs(Jv[IDX['chest']][0] - hx) < 32 and Jv[IDX['head']][1] - 10 < hy < Jv[0][1]:
                            HITS.append((t, a, j, False, ACC[a.name], None, 0.9))
                            v.flinch(t, 0.32, 0.25).shove(t, 14*(1 if Jv[0][0] > J[0][0] else -1), 0.2)
                            post('shake', t, 0.25, 4)
auto_hits()

# ================================================================= resolve timing
def jpos(a, t, j):
    J, _ = a.joints(t); return J[IDX[j]]
FXR = []
class FXo: pass
for ta, kind, d, layer, kw in FXL:
    e = FXo(); e.kind, e.tr, e.d, e.layer, e.kw = kind, WARP.R(ta), d, layer, dict(kw)
    e.seed = (int(ta*1000)*7919 + sum(map(ord, kind))) % 100003
    if 'actor' in kw and kind not in ('aura',):
        a = kw['actor']; j = kw.get('joint', 'hip'); p = jpos(a, ta, j)
        e.kw['x'] = p[0]; e.kw['y'] = p[1] if kind not in ('dust', 'ring', 'debris') else 0.0
        if kind in ('dust', 'ring', 'debris'): e.kw['x'] = jpos(a, ta + 0.05, 'hip')[0]
    FXR.append(e)
for t, a, j, big, col, snd, size in HITS:
    p = jpos(a, t, j); e = FXo(); e.kind = 'impact' if big else 'spark'; e.tr = WARP.R(t); e.d = 0.45 if big else 0.25
    e.layer = 'front'; e.kw = dict(x=p[0], y=p[1], col=col, size=size); e.seed = int(t*997) % 9973
    FXR.append(e); CUES.append((t, snd or ('bighit' if big else 'block'), 1.0))
POSTR = [(k, WARP.R(t), d, a) for k, t, d, a in POST]
TEXTR = [(e[0], WARP.R(e[1]), e[2]) + tuple(e[3:]) for e in TEXT]
REAL_END = WARP.R(ANIM_END)

# ================================================================= camera (auto framing, precomputed)
SHAKES = [(t, a, d) for k, t, d, a in POSTR if k == 'shake']
CUTS = sorted(WARP.R(t) for t in (3.95, 5.5, 18.5) if t < ANIM_END)
FOCUS = [(0, 'hero'), (2.6, 'hero oni'), (3.9, 'hero kage'), (5.8, 'oni hero'), (9.5, 'hero kage'), (12.0, 'hero oni'),
         (15.3, 'hero oni kage'), (17.2, 'hero'), (up - 0.3, 'hero oni kage'), (up + 0.8, 'hero oni'), (up + 1.9, 'hero kage'),
         (tc - 0.2, 'hero oni kage'), (tf + 0.8, 'hero')]
def cam_target(ta):
    names = [f for t, f in FOCUS if t <= ta][-1].split()
    pts = []
    for n in names:
        J, _ = ACT[n].joints(ta); pts.append((J[:, 0].mean(), J[:, 1].min(), J[:, 1].max()))
    near = pts
    x0 = min(p[0] for p in near); x1 = max(p[0] for p in near)
    y0 = min(p[1] for p in near); y1 = max(p[2] for p in near)
    spread = max(x1 - x0 + 150, (y1 - y0 + 110)*0.6)
    z = clamp(640/spread, 1.25, 3.0)
    return ((x0 + x1)/2, (y0 + y1)/2 - 10, z)
NF = int(DUR*FPS) + 1
CAMS = []
_c = None; _v = None
for i in range(NF):
    tr = i/FPS; ta = min(WARP.A(tr), ANIM_END)
    tx, ty, tz = cam_target(ta)
    cut = any(abs(tr - c) < 0.5/FPS for c in CUTS)
    if _c is None or cut: _c = [tx, ty, tz]
    else:
        k = 1 - math.exp(-6.0/FPS); kz = 1 - math.exp(-3.0/FPS)
        _c = [_c[0] + (tx - _c[0])*k, _c[1] + (ty - _c[1])*k, _c[2] + (tz - _c[2])*kz]
    CAMS.append(tuple(_c))
def view(i, tr):
    cx, cy, z = CAMS[min(i, NF - 1)]
    sx = sy = 0.0
    for t0, amp, d in SHAKES:
        g = tr - t0
        if 0 <= g < d:
            m = amp*(1 - g/d)**2; sx += m*math.sin(g*97 + t0*13); sy += m*math.cos(g*83 + t0*7)
    rot = 2.0*math.sin(tr*0.35)
    return R.View((cx, cy + 105/z*0 , z, sx, sy, rot))

# ================================================================= drawing
def draw_actor(c, g, a, ta, v, flat=None):
    J, Z = a.joints(ta); k = v.k
    col = COL[a.name]; far = shade(col, 0.7)
    S = lambda j: v.ws(*J[IDX[j]])
    lw, tw, hr = 10.5*k, 13.5*k, 14.5*k
    near_r = Z[IDX['rhand']] + Z[IDX['rft']] > Z[IDX['lhand']] + Z[IDX['lft']]
    sides = ('l', 'r') if near_r else ('r', 'l')
    def P(cl): return flat or PT(cl)
    def limb(js, cl):
        for p, q in zip(js, js[1:]): c.drawPath(shape(S(p), S(q), lambda t: lw), P(cl))
    s0, s1 = sides
    limb([s0+'sh', s0+'el', s0+'hand'], far); limb(['hip', s0+'kn', s0+'ft', s0+'toe'], far)
    c.drawPath(shape(S('hip'), S('neck'), lambda t: tw), P(col))
    hc = S('head'); c.drawCircle(hc[0], hc[1], hr, P(col))
    limb(['hip', s1+'kn', s1+'ft', s1+'toe'], col); limb([s1+'sh', s1+'el', s1+'hand'], col)
    if a is H_ and SWORD[0] <= ta < SWORD[1]:
        el, hd = J[IDX['rel']], J[IDX['rhand']]
        d = hd - el; ang = math.atan2(d[1], d[0]) - 0.35*math.copysign(1, d[0] if abs(d[0]) > 1 else 1)
        tip = hd + 88*np.array([math.cos(ang), math.sin(ang)]); pm = hd - 10*np.array([math.cos(ang), math.sin(ang)])
        if flat is None:
            c.drawPath(shape(v.ws(*hd), v.ws(*tip), lambda t: (3.3 - 2.3*t)*k), PT((236, 242, 255)))
            c.drawPath(shape(v.ws(*pm), v.ws(*hd), lambda t: 4.2*k), PT((60, 60, 80)))
            g.drawPath(poly([v.ws(*hd), v.ws(*tip)], False), PT(hexc(ACC['hero']), 170, stroke=8*k, add=True, blur=4*k))
        return (hd, tip)

def sword_pts(ta):
    J, _ = H_.joints(ta); el, hd = J[IDX['rel']], J[IDX['rhand']]
    d = hd - el; ang = math.atan2(d[1], d[0]) - 0.35*math.copysign(1, d[0] if abs(d[0]) > 1 else 1)
    return hd, hd + 88*np.array([math.cos(ang), math.sin(ang)])

def blade_trail(c, g, v, ta):
    if not (SWORD[0] <= ta < SWORD[1]): return
    pts = [tuple(map(lambda p: v.ws(*p), sword_pts(ta - i/240))) for i in range(10)]
    if sum(math.dist(pts[i][1], pts[i+1][1]) for i in range(9)) < 50*v.k: return
    acc = hexc(ACC['hero'])
    for i in range(9):
        q = 1 - i/9; (b0, t0), (b1, t1) = pts[i], pts[i+1]
        c.drawPath(poly([mix(b0, t0, 0.35), t0, t1, mix(b1, t1, 0.35)]), PT((255, 255, 255), int(200*q**1.6)))
        g.drawPath(poly([b0, t0, t1, b1]), PT(acc, int(210*q), add=True))

def draw_aura(c, g, e, age, v, tr, ta):
    J, _ = H_.joints(ta); hip = J[0]; on = clamp(age/0.5)*clamp((e.d - age)/0.5)
    acc = hexc(e.kw['col']); ka = min(v.k, 2.6*SS); r2 = random.Random(e.seed)
    for i in range(16):
        ph = r2.random(); life = r2.uniform(0.4, 0.8); q = ((age/life) + ph) % 1.0
        x_ = hip[0] + r2.uniform(-30, 30)*(1 - q*0.5) + math.sin(q*8 + i)*7; y_ = hip[1] + r2.uniform(-60, 30) - q*120
        p = v.ws(x_, y_); rr = (9*(1 - q) + 3)*ka
        g.drawPath(poly([(p[0] - rr*0.5, p[1]), (p[0], p[1] - rr*2.6), (p[0] + rr*0.5, p[1]), (p[0], p[1] + rr*0.6)]),
                   PT(acc, int(120*(1 - q)*on), add=True, blur=2.5*ka))
    r3 = random.Random(int(tr*20)*31 + 5)
    if on > 0.4 and int(tr*20) % 4 == 0:
        p = (hip[0] + r3.uniform(-40, 40), hip[1] + r3.uniform(-110, 10)); pts = [v.ws(*p)]
        for s in range(5):
            p = (p[0] + r3.uniform(-18, 18), p[1] + r3.uniform(-22, 12)); pts.append(v.ws(*p))
        c.drawPath(poly(pts, False), PT((235, 255, 255), int(220*on), stroke=1.3*v.k))
        g.drawPath(poly(pts, False), PT(acc, int(255*on), stroke=6*v.k, add=True))

def draw_text(arr, tr):
    c = skia.Surface(arr).getCanvas()
    for e in TEXTR:
        kind, t0, dur = e[:3]; age = tr - t0
        if not 0 <= age < dur: continue
        a = clamp(age/0.2)*clamp((dur - age)/0.35)
        if kind in ('title', 'fin'):
            txt = 'ONE  vs  TWO' if kind == 'title' else 'F I N'
            f = R.tfont(R.FONT, 128 if kind == 'title' else 110)
            tw = f.measureText(txt); x, y = WO/2 - tw/2, HO*0.22 + 14*(1 - EASE['out'](clamp(age/0.6)))
            c.drawString(txt, x, y, f, PT((54, 220, 255), int(230*a), blur=22))
            c.drawString(txt, x, y, f, PT((255, 255, 255), int(255*a)))
        else:
            name, who = e[3], e[4]
            sl = EASE['snap'](clamp(age/0.28)); out = EASE['in'](clamp((age - dur + 0.25)/0.25))
            y = HO*0.74 if who != 'hero' else HO*0.15
            off = (1 - sl)*WO - out*WO
            if who == 'kage': off = -off
            ac = hexc(ACC[who])
            c.drawPath(poly([(off - 60, y), (off + WO + 60, y - 90), (off + WO + 60, y + 50), (off - 60, y + 140)]), PT(ac, int(225*a)))
            f = R.tfont(R.FONT, 92); tw = f.measureText(name)
            c.drawString(name, WO/2 - tw/2 + off, y + 46, f, PT((255, 255, 255), int(255*a)))

def frame(fi):
    tr = fi/FPS; ta = min(WARP.A(tr), ANIM_END)
    v = view(fi, tr)
    arr = np.zeros((HO, WO, 4), np.uint8); c = skia.Surface(arr).getCanvas()
    garr = np.zeros((HO//2, WO//2, 4), np.uint8)
    g = skia.Surface(garr, colorType=skia.kRGBA_8888_ColorType, alphaType=skia.kPremul_AlphaType).getCanvas(); g.scale(0.5, 0.5)
    R.draw_bg(c, g, v, tr)
    for kind, t0, dd, amt in POSTR:
        if kind == 'dark' and 0 <= tr - t0 < dd:
            c.drawRect(skia.Rect.MakeWH(WO, HO), PT((5, 3, 12), int(255*amt*clamp((tr - t0)/0.08)*clamp((dd - tr + t0)/0.15))))
    for a in ACT.values():
        J, _ = a.joints(ta); x = J[0][0]; low = J[:, 1].max(); s = clamp(1 - (-low)/400, 0.15, 1)
        p = v.ws(x, 2); rx, ry = 55*v.k*s, 9*v.k*s
        c.drawOval(skia.Rect.MakeLTRB(p[0] - rx, p[1] - ry, p[0] + rx, p[1] + ry), PT((0, 0, 0), 255, shader=radial(p[0], p[1], rx, [((0, 0, 0), int(150*s)), ((0, 0, 0), 0)])))
    active = [(e, tr - e.tr) for e in FXR if 0 <= tr - e.tr < e.d]
    for e, age in active:
        if e.kind == 'aura': draw_aura(c, g, e, age, v, tr, ta)
        elif e.layer == 'back': R.draw_fx(e, age, c, g, v, tr)
    for a in (A_, B_, H_):
        J, _ = a.joints(ta); Jp, _ = a.joints(ta - 1/40)
        vx = (J[0][0] - Jp[0][0])*40
        falling = any(g.kind == 'fall' and g.t <= ta < g.t + g.dur + 0.3 for g in a.segs)
        if abs(vx) > 650 and not falling:
            for j, al in ((3, 45), (2, 80)):
                draw_actor(c, g, a, ta - j*0.025, v, flat=PT(mix(hexc(ACC[a.name]), (255, 255, 255), 0.3), int(al*min(1, abs(vx)/1300)), blur=2*v.k))
        rel = lambda Jx, j: Jx[IDX[j]] - Jx[0]
        for root, end in (('rel', 'rhand'), ('lel', 'lhand'), ('rkn', 'rtoe'), ('lkn', 'ltoe')):
            if np.linalg.norm(rel(J, end) - rel(Jp, end))*v.k < 15*SS: continue
            q = [v.ws(*Jp[IDX[root]]), v.ws(*Jp[IDX[end]]), v.ws(*J[IDX[end]]), v.ws(*J[IDX[root]])]
            c.drawPath(poly(q), PT(COL[a.name], 105, blur=2.2*v.k))
            p0, p1 = mix(q[1], q[0], 0.1), mix(q[2], q[3], 0.1)
            c.drawLine(*p0, *p1, PT((255, 255, 255), 80, stroke=1.2*v.k))
        draw_actor(c, g, a, ta, v)
    blade_trail(c, g, v, ta)
    for e, age in active:
        if e.layer != 'back' and e.kind != 'aura': R.draw_fx(e, age, c, g, v, tr)
    R.draw_fore(c, v, tr); R.draw_embers(c, g, v, tr)
    img = arr[:, :, :3].astype(np.float32)
    gl = Image.fromarray(np.ascontiguousarray(garr[:, :, :3]))
    img += np.asarray(gl.filter(ImageFilter.GaussianBlur(3)).resize((WO, HO), Image.BILINEAR), np.float32)*0.9
    img += np.asarray(gl.filter(ImageFilter.GaussianBlur(14)).resize((WO, HO), Image.BILINEAR), np.float32)*0.75
    sa = np.clip(np.asarray(Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).reduce(4), np.float32) - 170, 0, None).astype(np.uint8)
    img += np.asarray(Image.fromarray(sa).filter(ImageFilter.GaussianBlur(10)).resize((WO, HO), Image.BILINEAR), np.float32)*0.6
    img *= np.array([1.0, 0.985, 1.03], np.float32); img *= R.vignette()
    for kind, t0, dd, amt in POSTR:
        age = tr - t0
        if not 0 <= age < dd: continue
        u = age/dd
        if kind == 'flash': img += (255 - img)*(1 - u)**2*0.85
        elif kind == 'chroma':
            s = int(amt*SS*(1 - u)**2)
            if s: img[:, :, 0] = np.roll(img[:, :, 0], s, 1); img[:, :, 2] = np.roll(img[:, :, 2], -s, 1)
    for kind, t0, dd, amt in POSTR:
        if kind == 'iframe' and 0 <= tr - t0 < dd:
            lum = np.clip(img, 0, 255) @ np.array([0.3, 0.59, 0.11], np.float32)
            m = lum > np.percentile(lum[::4, ::4], 80)
            if int((tr - t0)*30) % 2: m = ~m
            img = np.where(m[:, :, None], np.array([250, 244, 236], np.float32), np.array([16, 10, 28], np.float32))
    img += np.random.default_rng(fi).normal(0, 2.2, (HO, WO, 1)).astype(np.float32)
    for kind, t0, dd, amt in POSTR:
        if kind == 'fade' and tr >= t0: img *= 1 - clamp((tr - t0)/dd)
    if tr < 0.6: img *= tr/0.6
    out = np.ascontiguousarray(np.dstack([np.clip(img, 0, 255).astype(np.uint8), np.full((HO, WO, 1), 255, np.uint8)]))
    draw_text(out, tr)
    return out[:, :, :3]

# ================================================================= audio
def write_audio(path, t0, t1):
    import audio as AU
    SR = AU.SR; out = np.zeros(int(SR*DUR) + SR)
    out[:len(out)] += AU.wind(len(out)/SR)[:len(out)]
    D, F, A3, C3, G = 73.4, 87.3, 110.0, 130.8, 98.0
    AU.place(out, AU.pad(DUR, [D/2, D, A3], 0.18), 0.0)
    for a, b, bpm in ((WARP.R(6.3), WARP.R(16.4), 150), (WARP.R(up + 0.4), WARP.R(tf - 0.1), 165)):
        beat = 60/bpm; t = a; i = 0
        while t < b:
            AU.place(out, AU.taiko(i % 8 == 0)*(0.9 if i % 2 == 0 else 0.55)*0.6, t)
            if i % 2: AU.place(out, AU.hat()*0.6, t + beat/2)
            f = (D, D, F, G, D, D, C3/2, A3/2)[i % 8]/2
            AU.place(out, AU.fade(np.sin(2*np.pi*f*AU.T(beat*0.9))*AU.dec(beat*0.9, 5)*0.18), t)
            t += beat; i += 1
    AU.place(out, AU.pad(DUR - WARP.R(tf), [D/2, D, A3, D*2, F*2], 0.22), WARP.R(tf))
    for ta, name, vol in CUES:
        AU.place(out, AU.LIB[name]()*vol*0.8, WARP.R(ta))
    out = np.tanh(out*0.9)[int(t0*SR):int(t1*SR)]
    st = np.stack([out, np.roll(out, 180)], 1)
    pcm = (st/max(1e-6, np.abs(st).max())*0.92*32767).astype(np.int16)
    with wave.open(path, 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())

def _bytes(fi): return np.ascontiguousarray(frame(fi)).tobytes()

def main():
    cmd = sys.argv[1]
    if cmd == 'still':
        out = sys.argv[2]; os.makedirs(out, exist_ok=True)
        for s in sys.argv[3:]: Image.fromarray(frame(int(round(float(s)*FPS)))).save(os.path.join(out, f'f_{s}.png'))
        return
    out = sys.argv[2]
    t0 = float(sys.argv[3]) if len(sys.argv) > 3 else 0.0
    t1 = float(sys.argv[4]) if len(sys.argv) > 4 else min(DUR, REAL_END)
    wav = os.path.splitext(out)[0] + '.wav'; write_audio(wav, t0, t1)
    from multiprocessing import Pool
    ff = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{WO}x{HO}', '-r', str(FPS),
                           '-i', '-', '-i', wav, '-c:v', 'libx264', '-preset', 'slow', '-crf', '15', '-pix_fmt', 'yuv420p',
                           '-c:a', 'aac', '-b:a', '256k', '-shortest', '-movflags', '+faststart', out], stdin=subprocess.PIPE)
    frames = range(int(t0*FPS), int(t1*FPS))
    with Pool(os.cpu_count()) as pool:
        for i, b in enumerate(pool.imap(_bytes, frames, chunksize=2)):
            ff.stdin.write(b)
            if i % 120 == 0: print(f'frame {i}/{len(frames)}', flush=True)
    ff.stdin.close(); sys.exit(ff.wait())

if __name__ == '__main__':
    print(f'animation real length {REAL_END:.2f}s', file=sys.stderr)
    main()
