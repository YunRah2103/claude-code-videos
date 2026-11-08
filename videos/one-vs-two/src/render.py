"""ONE vs TWO — Skia renderer (1080x1920, 60fps, anti-aliased cel shading). Original characters.

Usage:
  python render.py still OUTDIR t1 t2 ...      # preview PNGs (real seconds)
  python render.py video OUT.mp4 [start end]  # render (real seconds)
"""
import math, os, sys, random, subprocess
import numpy as np
import skia
from PIL import Image, ImageFilter
from story import *

DUR = 36.5
WO, HO = int(W*SS), int(H*SS)
FONT = '/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf'
FONT_L = '/usr/share/fonts/opentype/inter/Inter-SemiBold.otf'
SD = (-0.5, 0.866)            # shadow side (moon light from upper right)
INKC = (14, 10, 26)

# ---------------------------------------------------------------- paint helpers
def C(c, a=255): return skia.Color(int(c[0]), int(c[1]), int(c[2]), int(max(0, min(255, a))))
def PT(c, a=255, stroke=None, blur=None, add=False, shader=None):
    p = skia.Paint(AntiAlias=True); p.setColor(C(c, a))
    if stroke is not None:
        p.setStyle(skia.Paint.kStroke_Style); p.setStrokeWidth(max(0.5, stroke))
        p.setStrokeCap(skia.Paint.kRound_Cap); p.setStrokeJoin(skia.Paint.kRound_Join)
    if blur: p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur))
    if add: p.setBlendMode(skia.BlendMode.kPlus)
    if shader is not None: p.setShader(shader)
    return p
def _cols(cols): return [C(c[0], c[1]) for c in cols]
def radial(x, y, r, cols, pos=None):
    return skia.GradientShader.MakeRadial(skia.Point(x, y), max(0.5, r), _cols(cols), pos)
def linear(p0, p1, cols, pos=None):
    return skia.GradientShader.MakeLinear([skia.Point(*p0), skia.Point(*p1)], _cols(cols), pos)
def poly(pts, close=True):
    p = skia.Path(); p.moveTo(*pts[0])
    for q in pts[1:]: p.lineTo(*q)
    if close: p.close()
    return p
def moved(path, dx, dy):
    q = skia.Path(path); q.offset(dx, dy); return q
def pal(h, dark=0.58, rim=1.35):
    b = hexc(h); return (b, shade(b, dark), tuple(min(255, int(v*rim + 20)) for v in b))
def dim(pl, k): return tuple(shade(c, k) for c in pl)

def shape(a, b, wfun, n=10, caps=True):
    """Tapered limb/torso outline along a->b; wfun(t) gives full width (px)."""
    dx, dy = b[0]-a[0], b[1]-a[1]; L = math.hypot(dx, dy) or 1e-3
    ux, uy = dx/L, dy/L; nx, ny = -uy, ux
    left, right = [], []
    for i in range(n+1):
        t = i/n; w = wfun(t)/2; px, py = a[0]+dx*t, a[1]+dy*t
        left.append((px+nx*w, py+ny*w)); right.append((px-nx*w, py-ny*w))
    pts = list(left)
    if caps:
        r = wfun(1)/2
        for j in range(1, 8):
            an = j/8*math.pi; pts.append((b[0] + (nx*math.cos(an) + ux*math.sin(an))*r, b[1] + (ny*math.cos(an) + uy*math.sin(an))*r))
    pts += right[::-1]
    if caps:
        r = wfun(0)/2
        for j in range(1, 8):
            an = j/8*math.pi; pts.append((a[0] + (-nx*math.cos(an) - ux*math.sin(an))*r, a[1] + (-ny*math.cos(an) - uy*math.sin(an))*r))
    return poly(pts)

def seg_w(wa, wb, bulge=0.0, peak=0.35):
    def f(t):
        s = t/(2*peak) if t < peak else 0.5 + (t-peak)/(2*(1-peak))
        return wa + (wb-wa)*t + bulge*math.sin(math.pi*min(1, s))
    return f

def cel(c, path, pl, wpx, k, outline=True):
    """Three-tone cel shading: shadow strip, base, rim light; then ink line."""
    base, dark, rim = pl
    s, r = wpx*0.30, wpx*0.13
    c.drawPath(path, PT(dark))
    c.save(); c.clipPath(path, skia.ClipOp.kIntersect, True)
    pa = moved(path, -SD[0]*s, -SD[1]*s)
    c.drawPath(pa, PT(rim))
    c.save(); c.clipPath(moved(path, SD[0]*r, SD[1]*r), skia.ClipOp.kIntersect, True)
    c.drawPath(pa, PT(base)); c.restore(); c.restore()
    if outline: c.drawPath(path, PT(INKC, 235, stroke=max(1.0, 1.1*k)))

# ---------------------------------------------------------------- character design (original)
SPEC = {
    'hero': dict(ua=(15, 17, 1.2), fa=(9.5, 8.0, 0.8), hand=6.4, th=(21, 19, 1.0), sn=(18.5, 24, 0), torso=(23, 20, 27, 29),
                 head=14.5, P=dict(top=pal('#eef1fa', 0.66), arm=pal('#f5d9c4', 0.72), pants=pal('#27335a', 0.55, 1.7),
                 skin=pal('#f5d9c4', 0.72), hair=pal('#1b1e3a', 0.6, 2.4), acc=pal('#36d9ff', 0.62))),
    'oni':  dict(ua=(16, 12.5, 2.4), fa=(13.5, 10.5, 1.4), hand=8.2, th=(20, 16, 2.0), sn=(16, 12.5, 1.6), torso=(25, 22, 33, 35),
                 head=15, P=dict(top=pal('#b81f35', 0.55), arm=pal('#8e3027', 0.6), pants=pal('#221419', 0.55, 2.2),
                 skin=pal('#2c0d16', 0.6, 2.6), hair=pal('#efe3d0', 0.68), acc=pal('#ff6a3d', 0.6))),
    'shade':dict(ua=(11.5, 9.5, 1.0), fa=(9.5, 7.6, 0.7), hand=6.0, th=(16.5, 13.5, 1.6), sn=(13.5, 10.5, 1.0), torso=(19, 16, 23, 24),
                 head=13.5, P=dict(top=pal('#6c41a8', 0.56), arm=pal('#4a2c7c', 0.6, 1.8), pants=pal('#1c1434', 0.55, 2.2),
                 skin=pal('#ead3c9', 0.72), hair=pal('#2f1b54', 0.6, 2.2), acc=pal('#c77dff', 0.6))),
}
SHOE = pal('#15111f', 0.6, 3.0)

def build(F, st, v, ta, vel):
    """Draw items for a fighter, back to front."""
    Wd, tf = F.world(st); lk = F.look; kind = lk['kind']; sp = SPEC[kind]; Pp = sp['P']; f = st['face']; k = v.k
    S = lambda n: v.ws(*Wd[n])
    items = []
    ang = math.radians(st['pose']['t'] + st['pose']['h'] + st['rot'])
    hc = Wd['head']; hr = sp['head']
    def hl(lx, ly):
        s_ = hr/14.5
        x = (lx*math.cos(ang) - ly*math.sin(ang))*s_; y = (lx*math.sin(ang) + ly*math.cos(ang))*s_
        return v.ws(hc[0] + x*f, hc[1] + y)
    tx, ty = -vel[0]*0.6 - 60, -vel[1]*0.4 + 25
    base_ang = math.atan2(ty, tx); wig = 0.22 + min(0.45, math.hypot(*vel)/1000)
    def cloth(pts, w0, w1, pl):
        n = len(pts) - 1; L, R = [], []
        for i, p in enumerate(pts):
            a_, b_ = pts[max(0, i-1)], pts[min(n, i+1)]
            dx, dy = b_[0]-a_[0], b_[1]-a_[1]; ln = math.hypot(dx, dy) or 1; w = lerp(w0, w1, i/n)/2
            L.append((p[0]-dy/ln*w, p[1]+dx/ln*w)); R.append((p[0]+dy/ln*w, p[1]-dx/ln*w))
        items.append(('cel', poly(L + R[::-1]), pl, w0*0.8))
    if kind == 'hero':
        nk = S('neck')
        cloth(chain(nk, 10, 11*k, base_ang + 0.2, ta + 0.6, wig*1.2, speed=11), 8*k, 2*k, dim(Pp['acc'], 0.75))
        cloth(chain(nk, 11, 11*k, base_ang, ta, wig, speed=10), 11*k, 3*k, Pp['acc'])
        cloth(chain(S('hip'), 6, 8*k, base_ang + 0.6, ta + 1.3, wig*0.8, speed=12), 5*k, 2*k, dim(Pp['acc'], 0.85))
    if kind == 'shade':
        cloth(chain(hl(-13, -4), 10, 10*k, base_ang + 0.35, ta + 0.3, wig*1.1, speed=10), 10*k, 2*k, Pp['hair'])
    if kind == 'oni':
        cloth(chain(S('hip'), 6, 9*k, base_ang + 0.5, ta + 0.9, wig, speed=9), 6*k, 3*k, dim(Pp['acc'], 0.9))
    def arm(s_, dk):
        sh, el, hd = S('sh'), S(s_+'el'), S(s_+'hand')
        ua, fa = sp['ua'], sp['fa']
        upal = Pp['arm'] if kind == 'oni' else Pp['top']
        items.append(('cel', shape(sh, el, seg_w(ua[0]*k, ua[1]*k, ua[2]*k)), dim(upal, dk), ua[0]*k))
        fpal = Pp['skin'] if kind == 'hero' else Pp['arm']
        items.append(('cel', shape(el, hd, seg_w(fa[0]*k, fa[1]*k, fa[2]*k)), dim(fpal, dk), fa[0]*k))
        if kind == 'hero':   # wide sleeve cuff over the forearm
            items.append(('cel', shape(mix(sh, el, 0.8), mix(el, hd, 0.14), lambda t: ua[1]*k*1.06), dim(upal, dk*0.96), ua[1]*k))
        hand_pal = Pp['skin'] if kind == 'hero' else (Pp['arm'] if kind == 'oni' else dim(Pp['arm'], 0.8))
        r = sp['hand']*k; dx, dy = hd[0]-el[0], hd[1]-el[1]; L = math.hypot(dx, dy) or 1
        fist = (hd[0] + dx/L*r*0.35, hd[1] + dy/L*r*0.35)
        pth = skia.Path(); pth.addCircle(fist[0], fist[1], r)
        items.append(('cel', pth, dim(hand_pal, dk), r*2))
    def leg(s_, dk):
        hp, kn, ft, toe = S('hip'), S(s_+'kn'), S(s_+'ft'), S(s_+'toe')
        th, sn = sp['th'], sp['sn']
        items.append(('cel', shape(hp, kn, seg_w(th[0]*k, th[1]*k, th[2]*k)), dim(Pp['pants'], dk), th[0]*k))
        items.append(('cel', shape(kn, ft, seg_w(sn[0]*k, sn[1]*k, sn[2]*k, 0.3)), dim(Pp['pants'], dk), sn[0]*k))
        fw = 7.5*k
        items.append(('cel', shape(mix(ft, toe, -0.25), toe, lambda t: fw*(1 - 0.25*t)), dim(SHOE, dk), fw))
    arm('r', 0.72); leg('r', 0.74); leg('f', 1.0)
    hp, sh, nk = S('hip'), S('sh'), S('neck')
    tw = sp['torso']
    def tw_f(t):
        pts = ((0, tw[0]), (0.35, tw[1]), (0.8, tw[2]), (1.0, tw[3]))
        for (t0, w0), (t1, w1) in zip(pts, pts[1:]):
            if t <= t1: return k*lerp(w0, w1, smooth((t - t0)/(t1 - t0)))
        return k*tw[3]
    items.append(('cel', shape(nk, sh, lambda t: 8.5*k), Pp['skin'] if kind == 'hero' else Pp['top'], 8*k))
    tor = shape(hp, sh, tw_f, n=14)
    items.append(('cel', tor, Pp['top'], tw[2]*k))
    belt = shape(mix(hp, sh, 0.08), mix(hp, sh, 0.24), lambda t: tw[0]*k*1.4, caps=False)
    if kind == 'hero':
        items.append(('clipfill', tor, belt, Pp['acc'][0]))
        items.append(('line', [mix(sh, nk, 0.2), mix(hp, sh, 0.32)], (150, 160, 200), 2.2*k))
    elif kind == 'oni':
        items.append(('clipfill', tor, belt, (32, 20, 26)))
    else:
        items.append(('clipfill', tor, belt, Pp['acc'][1]))
    # head
    hcs = v.ws(*hc); r = hr*k
    head = skia.Path(); head.addCircle(hcs[0], hcs[1], r)
    jaw = poly([hl(-9, 3), hl(12, 1), hl(12.5, 8), hl(7, 15), hl(0, 14), hl(-6, 10)])
    head = skia.Op(head, jaw, skia.PathOp.kUnion_PathOp) or head
    if kind == 'shade':
        hood = poly([hl(*q) for q in ((16, -2), (14, -14), (2, -21), (-12, -19), (-26, -9), (-17, 5), (-8, 17), (10, 16))])
        items.append(('cel', skia.Op(hood, head, skia.PathOp.kUnion_PathOp) or hood, Pp['hair'], r*2))
        items.append(('cel', poly([hl(15.5, -6), hl(3, -8), hl(2, 2), hl(14.5, 3)]), Pp['skin'], r*0.6))
    else:
        items.append(('cel', head, Pp['skin'], r*2))
    if kind == 'hero':
        sw = math.sin(ta*7)*1.5
        hair = [(14, -4), (12, -13), (4, -19), (8, -28), (-2, -21), (-8, -31+sw), (-12, -20), (-25, -25+sw), (-19, -13),
                (-34, -11+sw), (-19, -4), (-29, 5+sw), (-15, 5), (-14, 13), (-5, 8), (1, -7), (6, -8)]
        items.append(('cel', poly([hl(*q) for q in hair]), Pp['hair'], r*1.6))
        items.append(('line', [hl(15, -10), hl(-14, -12)], Pp['acc'][0], 3.2*k))
    if kind == 'oni':
        for hp_ in (((3, -12), (11, -33), (13, -10)), ((-6, -13), (-10, -34), (1, -14))):
            items.append(('cel', poly([hl(*q) for q in hp_]), Pp['hair'], r*0.5))
        items.append(('fill', poly([hl(6, 8), hl(8, 13), hl(10, 8)]), (240, 230, 215)))
        items.append(('fill', poly([hl(10, 8), hl(12, 12), hl(13, 8)]), (240, 230, 215)))
    ey = hl(9, -2); glow_eye = kind != 'hero' or lk.get('eyeglow')
    if r > 34 and kind == 'hero':
        items.append(('fill', poly([hl(5, -2.5), hl(8, -5), hl(12.5, -3.5), hl(12, -0.5), hl(7, 0)]), (250, 250, 255)))
        items.append(('fill', poly([hl(8.5, -4.4), hl(11, -4), hl(11, -0.6), hl(8.5, -0.4)]), (30, 170, 230) if lk.get('eyeglow') else (40, 50, 90)))
        items.append(('dot', hl(10.2, -3.4), 0.9*k, (255, 255, 255)))
        items.append(('line', [hl(4.5, -7.5), hl(12.5, -7)], (25, 25, 50), 1.6*k))
        items.append(('line', [hl(9, 9), hl(12, 8.6)], (150, 90, 90), 1.0*k))
    else:
        items.append(('line', [hl(5.5, -2.5), hl(12.5, -2)], hexc(lk['eye']) if glow_eye else (30, 30, 60), 2.6*k))
    if glow_eye: items.append(('glow', ey, 5*k, hexc(lk['eye']), 0.7))
    if F.sheath_from is not None and ta >= F.sheath_from:
        a_, b_ = v.ws(*tf(-4, -6)), v.ws(*tf(-68, 27))
        items.append(('cel', shape(a_, b_, lambda t: (6 - 2*t)*k), pal('#2a1d36', 0.6, 2.2), 5*k))
        items.append(('cel', shape(a_, mix(a_, b_, 0.1), lambda t: 6.6*k), pal('#d9b45c', 0.6), 5*k))
    arm('f', 1.0)
    if 'tip' in Wd:
        items.append(('sword', S('pommel'), S('guardp'), S('tip'), F.glow_from is not None and ta >= F.glow_from))
    return items


STICK = {'hero': (238, 242, 250), 'oni': (204, 40, 58), 'shade': (128, 78, 200)}

def build_plain(F, st, v, ta, vel):
    """Plain stick figure: one flat colour, round head, thick rounded limbs."""
    Wd, tf = F.world(st); kind = F.look['kind']; k = v.k
    col = STICK[kind]; rear = shade(col, 0.72)
    S = lambda n: v.ws(*Wd[n])
    lw, tw = 11*k, 14*k
    items = []
    def limb(a, b, c_, cl):
        items.append(('fill', shape(S(a), S(b), lambda t: lw), cl))
        items.append(('fill', shape(S(b), S(c_), lambda t: lw), cl))
    limb('sh', 'rel', 'rhand', rear); limb('hip', 'rkn', 'rft', rear)
    limb('hip', 'fkn', 'fft', col)
    items.append(('fill', shape(S('hip'), S('neck'), lambda t: tw), col))
    hc = S('head'); hp = skia.Path(); hp.addCircle(hc[0], hc[1], 15*k)
    items.append(('fill', hp, col))
    limb('sh', 'fel', 'fhand', col)
    if 'tip' in Wd:
        items.append(('sword', S('pommel'), S('guardp'), S('tip'), F.glow_from is not None and ta >= F.glow_from))
    return items

def render_items(c, g, items, k, flat=None):
    for it in items:
        kind = it[0]
        if flat is not None:
            if kind in ('cel', 'fill'): c.drawPath(it[1], flat)
            elif kind == 'sword': c.drawPath(shape(it[2], it[3], lambda t: (3.4 - 2.6*t)*k), flat)
            continue
        if kind == 'cel': cel(c, it[1], it[2], it[3], k)
        elif kind == 'fill': c.drawPath(it[1], PT(it[2]))
        elif kind == 'clipfill':
            c.save(); c.clipPath(it[1], skia.ClipOp.kIntersect, True); c.drawPath(it[2], PT(it[3])); c.restore()
        elif kind == 'line': c.drawPath(poly(it[1], False), PT(it[2], 255, stroke=it[3]))
        elif kind == 'dot': c.drawCircle(it[1][0], it[1][1], it[2], PT(it[3]))
        elif kind == 'glow':
            x, y = it[1]; g.drawCircle(x, y, it[2], PT(it[3], 255, add=True, shader=radial(x, y, it[2], [(it[3], int(255*it[4])), (it[3], 0)])))
        elif kind == 'sword':
            pm, gp, tp, gl = it[1:]
            dx, dy = tp[0]-gp[0], tp[1]-gp[1]; L = math.hypot(dx, dy) or 1; nx, ny = -dy/L, dx/L
            pts = [(gp[0] + dx*i/12 + nx*math.sin(math.pi*i/12)*3*k, gp[1] + dy*i/12 + ny*math.sin(math.pi*i/12)*3*k) for i in range(13)]
            c.drawPath(shape(gp, tp, lambda t: (3.4 - 2.4*t)*k), PT((236, 242, 255)))
            c.drawPath(shape(pm, gp, lambda t: 4.2*k), PT((60, 60, 80)))
            if gl: g.drawPath(poly(pts, False), PT(hexc(LOOK_H['acc']), 200, stroke=9*k, add=True, blur=4*k))

# ---------------------------------------------------------------- effects
def draw_fx(e, age, c, g, v, tr):
    k = v.k; kw = e.kw; u = age/e.d
    acc = hexc(kw.get('col', '#ffffff')); kind = e.kind
    if kind in ('impact', 'spark'):
        big = kind == 'impact'; x, y = v.ws(kw['x'], kw['y']); sz = kw.get('size', 1.0)*min(k, 2.2*SS)*(1 if big else 0.6)
        if age < 0.12:
            s = 1 - age/0.12; rr = 46*sz*(0.6 + 0.8*(1-s))
            c.drawCircle(x, y, rr, PT((255, 255, 255), 255, shader=radial(x, y, rr, [((255, 255, 255), int(255*s)), ((255, 255, 255), int(190*s)), (acc, 0)], [0, 0.35, 1])))
            g.drawCircle(x, y, rr*1.6, PT(acc, 255, add=True, shader=radial(x, y, rr*1.6, [(acc, int(150*s)), (acc, 0)])))
            r2 = random.Random(e.seed + 1); n = 10 if big else 6; rot = r2.random()*6.3
            for i in range(n):
                a = rot + i*2*math.pi/n + r2.uniform(-0.15, 0.15); L = (85 if big else 38)*sz*r2.uniform(0.6, 1.1)*(0.5 + 0.7*(1-s))
                w = 0.05; r0 = 8*sz
                c.drawPath(poly([(x + math.cos(a-w)*r0, y + math.sin(a-w)*r0), (x + math.cos(a)*L, y + math.sin(a)*L),
                                 (x + math.cos(a+w)*r0, y + math.sin(a+w)*r0)]), PT((255, 255, 255), int(255*s)))
        if big:
            rr = (20 + 150*(1-(1-u)**3))*sz
            c.drawCircle(x, y, rr, PT((255, 255, 255), int(170*(1-u)**2), stroke=3.2*k*(1-u) + 0.5))
        r3 = random.Random(e.seed + 2)
        for i in range(12 if big else 8):
            a = r3.uniform(0, 6.283); spd = r3.uniform(240, 720 if big else 480); life = r3.uniform(0.2, 0.45)
            if age > life: continue
            q = 1 - age/life
            P_ = lambda g_: v.ws(kw['x'] + math.cos(a)*spd*g_, kw['y'] + math.sin(a)*spd*g_ + 520*g_*g_)
            p1, p0 = P_(age), P_(max(0, age - 0.025))
            c.drawLine(*p0, *p1, PT((255, 248, 225), int(255*q), stroke=2.0*k*q + 0.5))
            g.drawLine(*p0, *p1, PT(acc, int(255*q), stroke=5*k*q + 0.5, add=True))
    elif kind == 'slash':
        x, y = v.ws(kw['x'], kw['y']); r = kw.get('r', 90)*k
        a0, a1 = math.radians(kw['a0']), math.radians(kw['a1'])
        grow = EASE['out'](clamp(age/0.06)); fd = 1 - clamp((age - 0.05)/(e.d - 0.05))
        aa = a0 + (a1 - a0)*grow; w = kw.get('w', 26)*k*fd**0.7*0.8; sq = kw.get('squash', 1.0)
        if w > 0.4:
            outer, inner = [], []
            for i in range(33):
                t = i/32; an = a0 + (aa - a0)*t; th = w*math.sin(math.pi*t)**0.9*(0.3 + 0.7*t)
                outer.append((x + math.cos(an)*r, y + math.sin(an)*r*sq)); inner.append((x + math.cos(an)*(r - th), y + math.sin(an)*(r - th)*sq))
            path = poly(outer + inner[::-1])
            g.drawPath(path, PT(acc, int(170*fd), add=True, blur=4*k))
            c.drawPath(path, PT((255, 255, 255), int(235*fd)))
            c.drawPath(poly(outer, False), PT((255, 255, 255), int(255*fd), stroke=1.6*k))
    elif kind == 'ring':
        x, y = v.ws(kw['x'], kw.get('y', 0)); rr = (20 + kw.get('r', 200)*EASE['out'](u))*k; sq = kw.get('squash', 0.2)
        rect = skia.Rect.MakeLTRB(x - rr, y - rr*sq, x + rr, y + rr*sq)
        c.drawOval(rect, PT((255, 240, 225), int(170*(1-u)**1.5), stroke=2.5*k*(1-u) + 0.5))
        g.drawOval(rect, PT(acc, int(160*(1-u)), stroke=6*k*(1-u) + 0.5, add=True))
    elif kind == 'dust':
        n = kw.get('n', 14); dirn = kw.get('dir', 0); spread = kw.get('spread', 1.0); r2 = random.Random(e.seed + 3)
        for i in range(n):
            side = r2.choice((-1, 1)) if dirn == 0 else dirn
            spd = r2.uniform(60, 300)*spread; life = r2.uniform(0.55, 1.0)*e.d
            if age > life: continue
            q = age/life
            x_ = kw['x'] + side*spd*(1-(1-q)**2) + r2.uniform(-15, 15); y_ = -r2.uniform(0, 25) - 55*q*r2.uniform(0.3, 1.2)
            p = v.ws(x_, y_); rr = (12 + 36*q*r2.uniform(0.7, 1.3))*k*kw.get('size', 1); col = (130, 104, 128)
            c.drawCircle(p[0], p[1], rr, PT(col, 255, shader=radial(p[0], p[1], rr, [(col, int(140*(1-q)**1.4)), (col, 0)])))
    elif kind == 'debris':
        r2 = random.Random(e.seed + 4)
        for i in range(kw.get('n', 10)):
            vx = r2.uniform(-330, 330); vy = -r2.uniform(260, 700); y_ = vy*age + 1400*age*age
            if y_ > 0: continue
            p = v.ws(kw['x'] + vx*age, y_); s = r2.uniform(2.5, 6)*k; a = age*r2.uniform(-12, 12)
            c.drawPath(poly([(p[0] + math.cos(a + j*2.1)*s*(1 + 0.3*(j % 2)), p[1] + math.sin(a + j*2.1)*s) for j in range(3)]), PT((58, 42, 70)))
    elif kind == 'crack':
        fade_ = clamp((e.d - age)/0.6); grow = clamp(age/0.12); r2 = random.Random(e.seed + 5)
        for i in range(kw.get('n', 5)):
            a = r2.uniform(-1, 1); p = (kw['x'], 0); pts = [v.ws(*p)]; L = r2.uniform(60, 160)*grow
            for j in range(5):
                p = (p[0] + math.copysign(1, a)*L/5 + r2.uniform(-8, 8), p[1] + r2.uniform(-3, 3)); pts.append(v.ws(*p))
            c.drawPath(poly(pts, False), PT((8, 5, 14), int(210*fade_), stroke=2.4*k))
    elif kind == 'speedlines':
        r2 = random.Random(int(tr*30)*7 + 1); a_in = clamp(age/0.08)*clamp((e.d - age)/0.1)
        if kw.get('mode', 'radial') == 'radial':
            cx, cy = v.ws(*kw['focus']) if kw.get('focus') else (WO/2, HO/2)
            for i in range(44):
                a = r2.uniform(0, 6.283); r0 = r2.uniform(0.42, 0.7)*WO; r1 = 1.5*HO; w = r2.uniform(0.004, 0.012)
                c.drawPath(poly([(cx + math.cos(a)*r0, cy + math.sin(a)*r0), (cx + math.cos(a-w)*r1, cy + math.sin(a-w)*r1),
                                 (cx + math.cos(a+w)*r1, cy + math.sin(a+w)*r1)]), PT((255, 255, 255), int(r2.uniform(35, 95)*a_in)))
        else:
            for i in range(34):
                y = r2.uniform(0, HO); x0 = r2.uniform(-0.2, 1)*WO; ln = r2.uniform(0.2, 0.6)*WO; th = r2.uniform(1, 3.5)*SS
                c.drawPath(poly([(x0, y), (x0 + ln, y - th/2), (x0 + ln, y + th/2)]), PT((255, 255, 255), int(r2.uniform(40, 110)*a_in)))
    elif kind == 'aura':
        Wd, _ = HERO.world(kw['state']); on = clamp(age/0.4)*clamp((e.d - age)/0.5)
        hip = Wd['hip']; ka = min(k, 2.6*SS); r2 = random.Random(e.seed + 6)
        for i in range(16):
            ph = r2.random(); life = r2.uniform(0.4, 0.8); q = ((age/life) + ph) % 1.0
            x_ = hip[0] + r2.uniform(-34, 34)*(1 - q*0.5) + math.sin(q*8 + i)*7; y_ = hip[1] + r2.uniform(-60, 30) - q*120
            p = v.ws(x_, y_); rr = (9*(1-q) + 3)*ka
            g.drawPath(poly([(p[0] - rr*0.55, p[1]), (p[0], p[1] - rr*2.6), (p[0] + rr*0.55, p[1]), (p[0], p[1] + rr*0.6)]),
                       PT(acc, int(105*(1-q)*on), add=True, blur=2.5*ka))
        cx_, cy_ = v.ws(hip[0], hip[1] - 55)
        g.drawCircle(cx_, cy_, 95*ka, PT(acc, 255, add=True, shader=radial(cx_, cy_, 95*ka, [(acc, int(20*on)), (acc, 0)])))
        r3 = random.Random(int(tr*20)*31 + 5)
        if on > 0.4 and int(tr*20) % 4 == 0:
            p = (hip[0] + r3.uniform(-40, 40), hip[1] + r3.uniform(-110, 10)); pts = [v.ws(*p)]
            for s in range(5):
                p = (p[0] + r3.uniform(-18, 18), p[1] + r3.uniform(-22, 12)); pts.append(v.ws(*p))
            c.drawPath(poly(pts, False), PT((235, 255, 255), int(230*on), stroke=1.4*k))
            g.drawPath(poly(pts, False), PT(acc, int(255*on), stroke=6*k, add=True))
    elif kind == 'glint':
        x, y = v.ws(kw['x'], kw['y']); s = math.sin(math.pi*u); L = kw.get('size', 30)*k*s
        for a in (0, math.pi/2):
            c.drawPath(poly([(x - math.cos(a)*L, y - math.sin(a)*L), (x + math.sin(a)*L*0.07, y - math.cos(a)*L*0.07),
                             (x + math.cos(a)*L, y + math.sin(a)*L), (x - math.sin(a)*L*0.07, y + math.cos(a)*L*0.07)]), PT((255, 255, 255), int(255*s)))
        g.drawCircle(x, y, L*0.8 + 1, PT(acc, 255, add=True, shader=radial(x, y, L*0.8 + 1, [(acc, int(255*s)), (acc, 0)])))

def blade_trail(c, g, v, ta):
    pts = []
    for i in range(10):
        st = HERO.anim(ta - i/240)
        if st['pose']['sw'] is None: break
        Wd, _ = HERO.world(st); pts.append((v.ws(*Wd['guardp']), v.ws(*Wd['tip'])))
    if len(pts) < 3: return
    if sum(math.dist(pts[i][1], pts[i+1][1]) for i in range(len(pts) - 1)) < 45*v.k: return
    acc = hexc(LOOK_H['acc']); n = len(pts) - 1
    for i in range(n):
        q = 1 - i/n; (b0, t0), (b1, t1) = pts[i], pts[i+1]
        c.drawPath(poly([mix(b0, t0, 0.4), t0, t1, mix(b1, t1, 0.4)]), PT((255, 255, 255), int(190*q**1.6)))
        g.drawPath(poly([b0, t0, t1, b1]), PT(acc, int(200*q), add=True))

# ---------------------------------------------------------------- background
_cache = {}
def sky_image():
    if 'sky' in _cache: return _cache['sky']
    w, h = int(WO*1.3), int(HO*1.5)
    y = np.linspace(0, 1, h, dtype=np.float32)[:, None]
    stops = [(0, (6, 7, 26)), (0.2, (20, 15, 52)), (0.34, (58, 28, 88)), (0.43, (164, 66, 104)), (0.5, (246, 140, 110)), (1, (255, 178, 132))]
    img = np.zeros((h, w, 4), np.float32); img[:, :, 3] = 255
    for (a, ca), (b, cb) in zip(stops, stops[1:]):
        m = ((y >= a) & (y <= b)).astype(np.float32); s = np.clip((y - a)/(b - a), 0, 1)
        for ch in range(3): img[:, :, ch] += m*(ca[ch] + (cb[ch] - ca[ch])*s)
    img[:, :, :3] += np.random.default_rng(1).normal(0, 1.2, (h, w, 1)).astype(np.float32)
    arr = np.ascontiguousarray(np.clip(img, 0, 255).astype(np.uint8))
    c = skia.Surface(arr).getCanvas(); r = random.Random(3)
    for i in range(320):
        x, yy = r.uniform(0, w), r.uniform(0, h*0.42); s = r.uniform(0.5, 1.9)*SS
        c.drawCircle(x, yy, s, PT((255, 246, 255), int(r.uniform(70, 230)*(1 - yy/(h*0.42)))))
    mx, my, mr = w*0.66, h*0.27, 150*SS
    c.drawCircle(mx, my, mr*4, PT((255, 200, 180), 255, shader=radial(mx, my, mr*4, [((255, 200, 180), 70), ((255, 160, 150), 22), ((255, 150, 150), 0)], [0, 0.4, 1])))
    for i in range(7):
        a = math.radians(95 + i*11 + r.uniform(-3, 3)); L = h*0.9; wd = r.uniform(0.02, 0.05)
        c.drawPath(poly([(mx, my), (mx + math.cos(a - wd)*L, my + math.sin(a - wd)*L), (mx + math.cos(a + wd)*L, my + math.sin(a + wd)*L)]),
                   PT((255, 210, 190), 255, shader=radial(mx, my, L, [((255, 214, 196), 34), ((255, 214, 196), 0)])))
    c.drawCircle(mx, my, mr, PT((255, 240, 226), 255, shader=radial(mx - mr*0.3, my - mr*0.3, mr*1.4, [((255, 248, 236), 255), ((246, 222, 208), 255)])))
    for cx, cy, cr in ((-40, -30, 28), (35, 40, 22), (60, -55, 14), (-55, 60, 16), (10, 5, 10)):
        c.drawCircle(mx + cx*SS, my + cy*SS, cr*SS, PT((232, 206, 196), 120, blur=2*SS))
    for i in range(18):
        cx, cy = r.uniform(-0.1, 1.1)*w, r.uniform(0.22, 0.6)*h; cw, ch = r.uniform(180, 520)*SS, r.uniform(12, 30)*SS
        low = cy > h*0.44
        c.drawOval(skia.Rect.MakeLTRB(cx - cw, cy - ch, cx + cw, cy + ch), PT((255, 150, 130) if low else (52, 30, 78), 110 if low else 150, blur=9*SS))
        c.drawOval(skia.Rect.MakeLTRB(cx - cw*0.8, cy - ch*1.1, cx + cw*0.7, cy - ch*0.2), PT((255, 190, 170) if low else (120, 70, 130), 70, blur=6*SS))
    _cache['sky'] = skia.Image.fromarray(arr)
    return _cache['sky']

def smooth_ridge(seed, span, hmin, hmax, step):
    r = random.Random(seed); pts = []; x = -span
    while x < span: pts.append((x, -r.uniform(hmin, hmax))); x += r.uniform(*step)
    return pts
RIDGES = [(0.10, smooth_ridge(1, 3600, 140, 430, (90, 200)), (92, 52, 112), (58, 30, 86)),
          (0.28, smooth_ridge(2, 3300, 70, 250, (60, 140)), (60, 30, 82), (34, 17, 56)),
          (0.55, smooth_ridge(3, 3100, 25, 130, (30, 80)), (38, 20, 58), (20, 11, 36))]
PINES = [(random.Random(i).uniform(-2600, 2600), random.Random(i + 50).uniform(70, 160)) for i in range(26)]
TUFTS = [(random.Random(i*3).uniform(-2600, 2600), random.Random(i*3 + 1).uniform(-20, 220), random.Random(i*3 + 2).uniform(0.6, 1.4)) for i in range(220)]
ROCKS = [(random.Random(i*5 + 9).uniform(-2600, 2600), random.Random(i*5 + 10).uniform(-15, 200), random.Random(i*5 + 11).uniform(5, 16)) for i in range(70)]
FORE = [(random.Random(i*7 + 2).uniform(-2600, 2600), random.Random(i*7 + 3).uniform(0.8, 1.6)) for i in range(40)]

def ridge_path(pts, v, p, yoff=-30):
    sp = [v.ws(x, y + yoff, p) for x, y in pts]
    path = skia.Path(); path.moveTo(sp[0][0], HO*3); path.lineTo(*sp[0])
    if p < 0.5:
        for q in sp[1:]: path.lineTo(*q)
    else:
        for a, b in zip(sp, sp[1:]): path.quadTo(a[0], a[1], (a[0] + b[0])/2, (a[1] + b[1])/2)
    path.lineTo(sp[-1][0], HO*3); path.close()
    return path

def draw_bg(c, g, v, tr):
    sky = sky_image(); sw, sh = sky.width(), sky.height()
    ox = sw/2 - WO/2 - v.cx*0.03*SS; oy = sh*0.30 - HO*0.30 + v.cy*0.07*SS
    ox = max(60, min(sw - WO - 60, ox)); oy = max(60, min(sh - HO - 60, oy))
    c.save(); c.translate(WO/2, H*HZ*SS); c.rotate(v.rot*0.6); c.translate(-WO/2, -H*HZ*SS)
    c.drawImageRect(sky, skia.Rect.MakeXYWH(ox - 60, oy - 60, WO + 120, HO + 120), skia.Rect.MakeXYWH(-60, -60, WO + 120, HO + 120))
    c.restore()
    for p, pts, top, bot in RIDGES:
        y0 = v.ws(0, -30 - (430 if p < 0.2 else 250 if p < 0.4 else 130), p)[1]; y1 = v.ws(0, -10, p)[1]
        c.drawPath(ridge_path(pts, v, p), PT(top, 255, shader=linear((0, y0), (0, y1 + 1), [(top, 255), (bot, 255)])))
        if p == 0.55:
            zp = 1 + (v.z - 1)*p
            for x, hh in PINES:
                b = v.ws(x, -26, p); t = v.ws(x, -26 - hh, p); wd = hh*0.3*zp*SS
                for j in range(4):
                    yy = lerp(b[1], t[1], j/4.5); ww = wd*(1 - j/4.4)
                    c.drawPath(poly([(b[0] - ww + (t[0]-b[0])*j/4.5, yy), (lerp(b[0], t[0], (j + 1.7)/4.5), lerp(b[1], t[1], (j + 1.7)/4.5)),
                                     (b[0] + ww + (t[0]-b[0])*j/4.5, yy)]), PT(bot))
        ym = v.ws(0, -24, p)[1]; hm = (60 + 50*p)*SS*(1 + (v.z - 1)*p)
        mc = (200, 110, 130) if p < 0.5 else (90, 50, 100)
        c.drawRect(skia.Rect.MakeLTRB(-50, ym - hm, WO + 50, ym + hm*0.4),
                   PT(mc, 255, shader=linear((0, ym - hm), (0, ym + hm*0.4), [(mc, 0), (mc, 70), (mc, 0)], [0, 0.65, 1])))
    gx0, gx1 = v.cx - 3000, v.cx + 3000
    a0, a1 = v.ws(gx0, -26), v.ws(gx1, -26)
    ya, yb = v.ws(0, -26)[1], v.ws(0, 360)[1]
    c.drawPath(poly([a0, a1, v.ws(gx1, 900), v.ws(gx0, 900)]),
               PT((30, 18, 42), 255, shader=linear((0, ya), (0, yb), [((52, 30, 62), 255), ((24, 14, 36), 255), ((9, 6, 16), 255)], [0, 0.3, 1])))
    c.drawPath(poly([a0, a1], False), PT((255, 160, 130), 120, stroke=1.0*v.k))
    span = 760/v.z
    for x, y, s in ROCKS:
        if abs(x - v.cx) > span: continue
        p = v.ws(x, y); r = s*v.k*(0.7 + y/500)
        cel(c, poly([(p[0] - r, p[1]), (p[0] - r*0.4, p[1] - r*0.75), (p[0] + r*0.5, p[1] - r*0.6), (p[0] + r, p[1])]),
            ((40, 26, 52), (22, 13, 32), (110, 66, 104)), r*2, v.k, outline=False)
    sway = math.sin(tr*1.7)
    for x, y, s in TUFTS:
        if abs(x - v.cx) > span: continue
        p = v.ws(x, y); hgt = 9*s*v.k*(0.7 + y/500)
        for j in (-1, 0, 1):
            tip = (p[0] + j*hgt*0.45 + sway*hgt*0.35, p[1] - hgt*(1 - abs(j)*0.25))
            c.drawPath(poly([(p[0] + j*hgt*0.12 - hgt*0.08, p[1]), tip, (p[0] + j*hgt*0.12 + hgt*0.08, p[1])]), PT((26, 16, 36)))

def draw_fore(c, v, tr):
    sway = math.sin(tr*1.3)
    for x, s in FORE:
        p = v.ws(x, 290, 1.6)
        if not (-300 < p[0] < WO + 300) or p[1] > HO + 500: continue
        hgt = 72*s*SS*(1 + (v.z - 1)*1.6)
        for j in range(-2, 3):
            tip = (p[0] + j*hgt*0.25 + sway*hgt*0.2, p[1] - hgt*(1 - abs(j)*0.18))
            c.drawPath(poly([(p[0] + j*hgt*0.08 - hgt*0.05, p[1] + hgt), tip, (p[0] + j*hgt*0.08 + hgt*0.05, p[1] + hgt)]), PT((8, 5, 14), 245, blur=5*SS))

EMBERS = [(random.Random(i).random(), random.Random(i + 99).random(), random.Random(i + 7).uniform(0.3, 1.3)) for i in range(16)]
def draw_embers(c, g, v, tr):
    for x0, y0, d in EMBERS:
        x = ((x0*W*1.4 + tr*36*d - v.cx*v.z*d*0.5) % (W*1.4) - W*0.2)*SS
        y = ((y0*H - tr*48*d + v.cy*v.z*d*0.3) % H)*SS
        x += math.sin(tr*1.8 + x0*30)*10*SS; r = (0.8 + 1.6*d)*SS
        if d > 1.1:
            c.drawCircle(x, y, r*3, PT((255, 190, 150), 60, blur=r*1.6))
        else:
            c.drawCircle(x, y, r, PT((255, 222, 186), int(150*d)))
            g.drawCircle(x, y, r*2, PT((255, 130, 80), int(70*d), add=True, blur=r))

# ---------------------------------------------------------------- post
_vig = {}
def vignette():
    if 'v' not in _vig:
        y, x = np.mgrid[0:HO, 0:WO].astype(np.float32)
        d = np.sqrt(((x - WO/2)/(WO*0.78))**2 + ((y - HO*0.52)/(HO*0.64))**2)
        _vig['v'] = np.clip(1.12 - d*0.6, 0.38, 1.0)[:, :, None].astype(np.float32)
    return _vig['v']

_tf = {}
def tfont(path, size):
    if (path, size) not in _tf: _tf[(path, size)] = skia.Font(skia.Typeface.MakeFromFile(path), size)
    return _tf[(path, size)]

def draw_text(arr, tr):
    c = skia.Surface(arr).getCanvas()
    for e in TEXTR:
        kind, t0, dur = e[:3]; age = tr - t0
        if not 0 <= age < dur: continue
        a = clamp(age/0.2)*clamp((dur - age)/0.35)
        if kind in ('title', 'fin'):
            txt = 'ONE  vs  TWO' if kind == 'title' else 'F I N'
            f = tfont(FONT, 128 if kind == 'title' else 110)
            tw = f.measureText(txt); x, y = WO/2 - tw/2, HO*0.24 + 14*(1 - EASE['out'](clamp(age/0.6)))
            c.drawString(txt, x, y, f, PT((54, 220, 255), int(230*a), blur=22))
            c.drawString(txt, x + 5, y + 5, f, PT((0, 0, 0), int(150*a), blur=4))
            c.drawString(txt, x, y, f, PT((255, 255, 255), int(255*a)))
            if kind == 'title':
                fs = tfont(FONT_L, 34); sub = 'A   ONE - SWORD   DUEL'
                c.drawString(sub, WO/2 - fs.measureText(sub)/2, y + 70, fs, PT((255, 214, 196), int(230*a)))
        elif kind == 'card':
            name, lk = e[3], e[4]
            sl = EASE['snap'](clamp(age/0.28)); out = EASE['in'](clamp((age - dur + 0.25)/0.25))
            y = HO*0.70 if lk['kind'] != 'hero' else HO*0.17
            off = (1 - sl)*WO - out*WO
            if lk['kind'] == 'shade': off = -off
            ac = hexc(lk['acc'])
            c.drawPath(poly([(off - 60, y), (off + WO + 60, y - 90), (off + WO + 60, y + 50), (off - 60, y + 140)]), PT(ac, int(225*a)))
            c.drawPath(poly([(off - 60, y + 124), (off + WO + 60, y + 34), (off + WO + 60, y + 50), (off - 60, y + 140)]), PT((255, 255, 255), int(210*a)))
            f = tfont(FONT, 92); tw = f.measureText(name)
            c.drawString(name, WO/2 - tw/2 + off + 4, y + 50, f, PT((0, 0, 0), int(160*a), blur=3))
            c.drawString(name, WO/2 - tw/2 + off, y + 46, f, PT((255, 255, 255), int(255*a)))

# ---------------------------------------------------------------- frame
def frame(fi):
    tr = fi/FPS; ta = min(WARP.A(tr), ANIM_END)
    v = View(CAM.at(ta, tr))
    HERO.look['eyeglow'] = ta >= 17.3
    arr = np.zeros((HO, WO, 4), np.uint8); c = skia.Surface(arr).getCanvas()
    garr = np.zeros((HO//2, WO//2, 4), np.uint8); g = skia.Surface(garr, colorType=skia.kRGBA_8888_ColorType, alphaType=skia.kPremul_AlphaType).getCanvas(); g.scale(0.5, 0.5)
    draw_bg(c, g, v, tr)
    for kind, t0, dd, amt in POSTR:
        if kind == 'dark' and 0 <= tr - t0 < dd:
            a = amt*clamp((tr - t0)/0.08)*clamp((dd - (tr - t0))/0.15)
            c.drawRect(skia.Rect.MakeWH(WO, HO), PT((5, 3, 12), int(255*a)))
    states = {n: F.anim(ta) for n, F in FIGHTERS.items()}
    prev = {n: F.anim(ta - 0.04) for n, F in FIGHTERS.items()}
    for n, st in states.items():
        x, y = v.ws(st['x'], 2); s = max(0.15, 1 - st['alt']/450); rx, ry = 50*v.k*s, 9*v.k*s
        c.drawOval(skia.Rect.MakeLTRB(x - rx, y - ry, x + rx, y + ry), PT((0, 0, 0), 255, shader=radial(x, y, rx, [((0, 0, 0), int(150*s)), ((0, 0, 0), 0)])))
    active = [(e, tr - e.tr) for e in FXR if 0 <= tr - e.tr < e.d]
    for e, age in active:
        if e.kind == 'aura': e.kw['state'] = HERO.anim(ta)
        if e.layer == 'back': draw_fx(e, age, c, g, v, tr)
    for n in ('oni', 'kage', 'hero'):
        F = FIGHTERS[n]; st, pv = states[n], prev[n]
        vel = ((st['x'] - pv['x'])/0.04, -(st['alt'] - pv['alt'])/0.04); spd = math.hypot(*vel)
        acc = hexc(F.look['acc'])
        if spd > 700:
            for j, a in ((3, 50), (2, 85)):
                render_items(c, g, build_plain(F, F.anim(ta - j*0.025), v, ta, vel), v.k,
                             flat=PT(mix(acc, (255, 255, 255), 0.25), int(a*min(1, spd/1400)), blur=2*v.k))
        Wn, _ = F.world(st); Wp, _ = F.world(F.anim(ta - 1/40))
        rel = lambda Wd, j: (Wd[j][0] - Wd['hip'][0], Wd[j][1] - Wd['hip'][1])
        for root, end in (('fel', 'fhand'), ('rel', 'rhand'), ('fkn', 'ftoe'), ('rkn', 'rtoe')):
            if math.dist(rel(Wn, end), rel(Wp, end))*v.k < 16*SS: continue
            q = [v.ws(*Wp[root]), v.ws(*Wp[end]), v.ws(*Wn[end]), v.ws(*Wn[root])]
            c.drawPath(poly(q), PT(STICK[F.look['kind']], 110, blur=2.2*v.k))
            for o in (-0.15, 0.15):
                p0, p1 = mix(q[1], q[0], 0.1 + o), mix(q[2], q[3], 0.1 + o)
                c.drawLine(*p0, *p1, PT((255, 255, 255), 90, stroke=1.2*v.k))
        render_items(c, g, build_plain(F, st, v, ta, vel), v.k)
    blade_trail(c, g, v, ta)
    for e, age in active:
        if e.layer != 'back': draw_fx(e, age, c, g, v, tr)
    draw_fore(c, v, tr)
    draw_embers(c, g, v, tr)
    # ---- post
    img = arr[:, :, :3].astype(np.float32)
    gl = Image.fromarray(np.ascontiguousarray(garr[:, :, :3]))
    img += np.asarray(gl.filter(ImageFilter.GaussianBlur(3)).resize((WO, HO), Image.BILINEAR), np.float32)*0.9
    img += np.asarray(gl.filter(ImageFilter.GaussianBlur(14)).resize((WO, HO), Image.BILINEAR), np.float32)*0.75
    small = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).reduce(4)
    sa = np.clip(np.asarray(small, np.float32) - 170, 0, None).astype(np.uint8)
    img += np.asarray(Image.fromarray(sa).filter(ImageFilter.GaussianBlur(10)).resize((WO, HO), Image.BILINEAR), np.float32)*0.6
    img *= np.array([1.0, 0.985, 1.03], np.float32)
    img *= vignette()
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

def _bytes(fi): return np.ascontiguousarray(frame(fi)).tobytes()

def main():
    cmd = sys.argv[1]
    if cmd == 'still':
        out = sys.argv[2]; os.makedirs(out, exist_ok=True)
        for s in sys.argv[3:]:
            Image.fromarray(frame(int(round(float(s)*FPS)))).save(os.path.join(out, f'f_{s}.png'))
        return
    if cmd == 'video':
        out = sys.argv[2]
        t0 = float(sys.argv[3]) if len(sys.argv) > 3 else 0.0
        t1 = float(sys.argv[4]) if len(sys.argv) > 4 else DUR
        import audio
        wav = os.path.splitext(out)[0] + '.wav'
        audio.write(wav, CUES, WARP, DUR, t0, t1)
        from multiprocessing import Pool
        ff = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{WO}x{HO}',
                               '-r', str(FPS), '-i', '-', '-i', wav, '-c:v', 'libx264', '-preset', 'slow', '-crf', '15',
                               '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '256k', '-shortest', '-movflags', '+faststart', out],
                              stdin=subprocess.PIPE)
        frames = range(int(t0*FPS), int(t1*FPS))
        with Pool(os.cpu_count()) as pool:
            for i, b in enumerate(pool.imap(_bytes, frames, chunksize=2)):
                ff.stdin.write(b)
                if i % 120 == 0: print(f'frame {i}/{len(frames)}', flush=True)
        ff.stdin.close(); sys.exit(ff.wait())

if __name__ == '__main__':
    main()
