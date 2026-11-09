"""3-second fight hook preview for seatbelt-fight (no VO, no text).

Flat 2D stickmen on a purple night backdrop. Hand-keyed poses, eased; legs use
2-bone IK on planted feet; deterministic stepping (60 fps, hit-stop, close-up).
Usage: python videos/seatbelt-fight/src/hook.py [--frames f1,f2,...]
"""
import math, os, subprocess, sys
import numpy as np, cairo, cv2

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
sys.path.insert(0, os.path.join(ROOT, 'videos/new-car-trap/src'))
import sfx  # noqa: E402  (reused synth helpers)

W, H, FPS, NF = 1080, 1920, 60, 180
OUT = os.path.join(ROOT, 'out/seatbelt-fight')
IMPACT_F, HITSTOP = 75, 3          # frames 75-77 frozen
CLOSE = range(75, 82)              # close-up cut on the impact
FLASH = {75: 0.72, 76: 0.30}       # one colour flash, two frames max
STRIKE = (1.15, 1.25)              # fast strike: smear + 4 sub-frame blur


def ta_of(f):
    """Animation time; frozen for the hit-stop."""
    if f < IMPACT_F:
        return f / FPS
    if f < IMPACT_F + HITSTOP:
        return IMPACT_F / FPS
    return (f - HITSTOP + 1) / FPS


def C(h, a=1.0):
    return (int(h[1:3], 16) / 255, int(h[3:5], 16) / 255, int(h[5:7], 16) / 255, a)


def ease(u, k):
    u = min(1.0, max(0.0, u))
    if k == 'lin': return u
    if k == 'in': return u ** 3
    if k == 'out': return 1 - (1 - u) ** 3
    if k == 'snap': return 1 - (1 - u) ** 4
    return u * u * u * (u * (u * 6 - 15) + 10)


# ---------------------------------------------------------------- rig
CH = ['hx', 'hy', 'a', 'hd', 'nsa', 'neb', 'fsa', 'feb', 'nfx', 'ffx']
READY = dict(hx=0, hy=0, a=8, hd=-4, nsa=25, neb=125, fsa=40, feb=105, nfx=-115, ffx=95)
L_T, L_TH, L_SH, ANK, L_UA, L_FA, R_HEAD, NECK, HIP0 = 250, 195, 190, 28, 150, 140, 62, 22, 372
R_HAND, OUTW = 37, 6


def build(keys):
    out, cur = [], dict(READY)
    for k in keys:
        cur = {**cur, **k[2]}
        out.append((k[0], k[1], dict(cur), len(k) > 3 and k[3]))
    return out


def sample(keys, t):
    if t <= keys[0][0]:
        p = dict(keys[0][2]); p['nfx_l'] = p['ffx_l'] = 0; return p
    for i in range(1, len(keys)):
        t1, e, p1, slide = keys[i]
        t0, _, p0, _ = keys[i - 1]
        if t <= t1:
            u = ease((t - t0) / (t1 - t0), e)
            p = {c: p0[c] + (p1[c] - p0[c]) * u for c in CH}
            for c in ('nfx', 'ffx'):
                dx = p1[c] - p0[c]
                p[c + '_l'] = 0 if (slide or abs(dx) < 4) else min(70, .35 * abs(dx)) * math.sin(math.pi * u)
            return p
    p = dict(keys[-1][2]); p['nfx_l'] = p['ffx_l'] = 0; return p


def V(a):
    return np.array([math.sin(a), -math.cos(a)])


def ik(h, a, l1, l2):
    d = a - h; dist = float(np.hypot(*d))
    dc = min(max(dist, 1.0), l1 + l2 - 0.5)
    A = math.acos(max(-1, min(1, (l1 * l1 + dc * dc - l2 * l2) / (2 * l1 * dc))))
    b = math.atan2(d[1], d[0])
    k1 = h + l1 * np.array([math.cos(b - A), math.sin(b - A)])
    k2 = h + l1 * np.array([math.cos(b + A), math.sin(b + A)])
    return k1 if k1[0] > k2[0] else k2, dist > l1 + l2


def skel(p):
    hip = np.array([p['hx'], -HIP0 + p['hy']])
    a = math.radians(p['a'])
    sh = hip + L_T * V(a)
    ha = a + math.radians(p['hd'])
    head = sh + (NECK + R_HEAD) * V(ha)
    s = dict(hip=hip, sh=sh, head=head, ha=ha, over=0)
    for k in 'nf':
        th = a + math.radians(p[k + 'sa'])
        el = sh + L_UA * np.array([math.sin(th), math.cos(th)])
        th2 = th + math.radians(p[k + 'eb'])
        s[k + 'arm'] = (sh, el, el + L_FA * np.array([math.sin(th2), math.cos(th2)]))
        ank = np.array([p[k + 'fx'], -ANK - p.get(k + 'fx_l', 0)])
        knee, over = ik(hip, ank, L_TH, L_SH)
        s[k + 'leg'] = (hip, knee, ank, p.get(k + 'fx_l', 0))
        s['over'] += over
    return s


class Fighter:
    def __init__(s, base, d, keys, hero):
        s.base, s.d, s.keys, s.hero = base, d, build(keys), hero

    def pose(s, ta):
        p = sample(s.keys, ta)
        # overlapping action: lead (far) arm trails the body slightly
        p['fsa'] = sample(s.keys, ta - 0.025)['fsa']
        p['feb'] = sample(s.keys, ta - 0.05)['feb']
        return p

    def sk(s, ta):
        return skel(s.pose(ta))

    def world(s, pt):
        return np.array([s.base + s.d * pt[0], pt[1]])


# Hero (left, faces right). near side = rear arm/leg (power hand).
HERO_KEYS = [
    (0.00, 'io', {}),
    (0.16, 'io', dict(hx=14, hy=14, a=12)),
    (0.30, 'io', dict(hx=6, hy=24, a=14, hd=0, nsa=20, neb=135)),            # anticipation dip
    (0.44, 'snap', dict(hx=-62, hy=50, a=-22, hd=-12, nsa=8, neb=142, fsa=28, feb=128)),  # quick lean
    (0.54, 'io', dict(hx=-68, hy=54, a=-26)),
    (0.80, 'io', dict(hx=-24, hy=26, a=4, hd=-4, nsa=20, neb=130, fsa=40, feb=105)),      # settle
    (1.15, 'io', dict(hx=-38, hy=36, a=-8, hd=0, nsa=-38, neb=128, fsa=58, feb=92, ffx=140)),  # slow wind-up
    (1.25, 'in', dict(hx=100, hy=30, a=22, hd=6, nsa=86, neb=4, fsa=18, feb=132, ffx=190, nfx=-20)),  # strike
    (1.42, 'out', dict(hx=118, hy=38, a=27, nsa=80, neb=10, fsa=14, feb=136)),         # follow-through
    (1.78, 'io', dict(hx=92, hy=20, a=10, hd=-4, nsa=25, neb=125, fsa=40, feb=105)),   # land balanced
    (2.05, 'io', dict(hx=90, hy=14, a=8)),
    (2.30, 'io', dict(hx=40, hy=20, ffx=95)),                                     # reset steps
    (2.52, 'io', dict(hx=0, hy=6, nfx=-115)),
    (2.66, 'io', dict(hy=0)),
]
# Opponent (right, faces left). near side = rear arm (punching hand).
OPP_KEYS = [
    (0.00, 'io', {}),
    (0.14, 'io', dict(hx=-8, hy=14, a=6)),
    (0.30, 'io', dict(hx=-26, hy=22, a=0, nsa=-24, neb=122)),                  # cock the punch
    (0.46, 'in', dict(hx=66, hy=30, a=24, hd=2, nsa=96, neb=4, fsa=32, feb=120, ffx=165)),
    (0.56, 'out', dict(hx=78, a=28, nsa=98, neb=0)),
    (0.84, 'io', dict(hx=40, hy=20, a=12, hd=-4, nsa=30, neb=120, fsa=45, feb=100, nfx=-60)),
    (1.25, 'io', dict(hx=44, hy=16, a=10)),
    (1.34, 'snap', dict(hx=22, hy=30, a=-24, hd=-34, nsa=-40, neb=40, fsa=-22, feb=30)),  # head snaps
    (1.70, 'out', dict(hx=-105, hy=34, a=-30, hd=-18, nfx=-205, ffx=15), True),  # knocked back, slides
    (2.10, 'out', dict(hx=-165, hy=40, a=-14, hd=-6, nsa=-8, neb=60, fsa=0, feb=55,
                       nfx=-275, ffx=-55), True),
    (2.45, 'io', dict(hx=-180, hy=52, a=14, hd=14, nsa=12, neb=40, fsa=18, feb=45, ffx=-85)),  # hunched
    (2.95, 'io', dict(hy=46, a=12)),
]

HERO = Fighter(-290, 1, HERO_KEYS, True)
OPP = Fighter(290, -1, OPP_KEYS, False)


def solve_punch():
    """Opponent's punch aims where the hero's head was before the slip."""
    target = HERO.world(HERO.sk(0.30)['head']) + np.array([40, 10])
    k = [i for i, kk in enumerate(OPP_KEYS) if kk[0] == 0.46][0]
    best = None
    for hx in range(60, 300, 3):
        for nsa in range(80, 112, 2):
            OPP_KEYS[k][2].update(hx=hx, nsa=nsa, ffx=hx + 95)
            OPP.keys = build(OPP_KEYS)
            err = float(np.hypot(*(OPP.world(OPP.sk(0.46)['narm'][2]) - target)))
            if best is None or err < best[0]:
                best = (err, hx, nsa)
    _, hx, nsa = best
    OPP_KEYS[k][2].update(hx=hx, nsa=nsa, ffx=hx + 95)
    OPP_KEYS[k + 1][2].update(hx=hx + 12, nsa=nsa + 2)
    OPP_KEYS[k + 2][2].update(hx=hx - 30, nfx=hx - 30 - 150)
    OPP_KEYS[k + 3][2].update(hx=hx - 26)
    OPP.keys = build(OPP_KEYS)
    return best


def solve_impact():
    """Place the hero fist on the opponent's face at the impact key."""
    ti = 1.25
    face = OPP.world(OPP.sk(ti)['head'])
    k = [i for i, kk in enumerate(HERO_KEYS) if kk[0] == ti][0]
    best = None
    for hx in range(-20, 260, 2):
        for nsa in range(70, 106):
            HERO_KEYS[k][2].update(hx=hx, nsa=nsa)
            HERO.keys = build(HERO_KEYS)
            fist = HERO.world(HERO.sk(ti)['narm'][2])
            target = face + np.array([-(R_HEAD + R_HAND - 18), 4])
            err = float(np.hypot(*(fist - target)))
            if best is None or err < best[0]:
                best = (err, hx, nsa)
    _, hx, nsa = best
    HERO_KEYS[k][2].update(hx=hx, nsa=nsa)
    ft = HERO_KEYS[k + 1][2]; ft.update(hx=hx + 16, nsa=nsa - 6)
    HERO.keys = build(HERO_KEYS)
    return best


# ---------------------------------------------------------------- drawing
def cap_path(cr, p0, p1, r0, r1):
    d = p1 - p0; L = float(np.hypot(*d))
    if L < 1e-3 or abs(r0 - r1) >= L:
        cr.new_sub_path(); cr.arc(*(p0 if r0 > r1 else p1), max(r0, r1), 0, 2 * math.pi); return
    ang = math.atan2(d[1], d[0]); phi = math.acos((r0 - r1) / L)
    cr.new_sub_path()
    cr.arc(p0[0], p0[1], r0, ang + phi, ang + 2 * math.pi - phi)
    cr.arc(p1[0], p1[1], r1, ang - phi, ang + phi)
    cr.close_path()


def blob(cr, prims, col, ow=OUTW, oc=C('#0c0716')):
    """Union of capsules/circles/polys: dark outline pass then flat fill."""
    for pas, (c, grow) in enumerate(((oc, ow), (col, 0))):
        if pas == 0 and ow <= 0:
            continue
        cr.set_source_rgba(*c)
        for pr in prims:
            if pr[0] == 'cap':
                cap_path(cr, pr[1], pr[2], pr[3] + grow, pr[4] + grow)
            elif pr[0] == 'circ':
                cr.new_sub_path(); cr.arc(pr[1][0], pr[1][1], pr[2] + grow, 0, 2 * math.pi)
            else:  # poly
                cr.new_sub_path(); cr.move_to(*pr[1][0])
                for q in pr[1][1:]:
                    cr.line_to(*q)
                cr.close_path()
            cr.set_fill_rule(cairo.FILL_RULE_WINDING)
        if pas == 0:
            cr.set_line_width(2 * ow); cr.set_line_join(cairo.LINE_JOIN_ROUND)
            cr.fill_preserve(); cr.stroke()
        else:
            cr.fill()


PAL = {
    True: dict(skin=C('#c08862'), skin2=C('#93603f'), tee=C('#f4f2f7'), shorts=C('#1e1e26'),
               shorts2=C('#121218'), shoe=C('#f2f2f4'), shoe2=C('#bfc0c8'), sole=C('#16161c'),
               hair=C('#221a1e')),
    False: dict(skin=C('#a3212c'), skin2=C('#6d141d'), tee=C('#a3212c'), shorts=C('#a3212c'),
                shorts2=C('#6d141d'), shoe=C('#7c1820'), shoe2=C('#55101a'), sole=C('#3a0b12'),
                hair=C('#a3212c')),
}


def shoe(cr, ank, lift, col, sole, hero):
    tilt = -0.25 * min(1, lift / 60)
    cr.save(); cr.translate(*ank); cr.rotate(tilt)
    pts = [(-24, -18), (40, -10), (66, 6), (66, ANK - 4), (-26, ANK - 4)]
    blob(cr, [('poly', pts), ('circ', (-14, 4), 20), ('circ', (52, ANK - 16), 14)], col)
    if hero:
        cr.set_source_rgba(*sole); cr.rectangle(-26, ANK - 13, 92, 9); cr.fill()
    cr.restore()


def leg(cr, L, P, near, hero):
    hip, knee, ank, lift = L
    skin = P['skin'] if near else P['skin2']
    blob(cr, [('cap', hip, knee, 38, 30), ('cap', knee, ank, 29, 19), ('circ', knee, 29)], skin)
    if hero:  # shorts over the thigh
        blob(cr, [('cap', hip, hip + (knee - hip) * 0.72, 40, 33)], P['shorts'] if near else P['shorts2'])
    shoe(cr, ank, lift, P['shoe'] if near else P['shoe2'], P['sole'], hero)


def arm(cr, A, P, near, hero):
    sh, el, hd = A
    skin = P['skin'] if near else P['skin2']
    blob(cr, [('cap', sh, el, 27, 23), ('cap', el, hd, 23, 18), ('circ', el, 23), ('circ', hd, R_HAND)], skin)
    if hero:
        tee = P['tee'] if near else C('#c9c7d2')
        blob(cr, [('cap', sh, sh + (el - sh) * 0.5, 30, 27)], tee)


def head_pts(s, pts):
    ca, sa = math.cos(s['ha']), math.sin(s['ha'])
    return [(s['head'][0] + x * ca - y * sa, s['head'][1] + x * sa + y * ca) for x, y in pts]


def draw_fighter(cr, F, ta, smear=False):
    s = F.sk(ta); P = PAL[F.hero]
    prev = F.sk(ta - 0.05)
    lagh = np.clip((prev['head'] - s['head']) * 0.7, -34, 34)   # hair follow-through
    lagb = np.clip((prev['hip'] - s['hip']) * 0.6, -26, 26)     # shirt hem follow-through
    cr.save(); cr.translate(F.base, 0); cr.scale(F.d, 1)
    # contact shadow
    fx = (s['nleg'][2][0] + s['fleg'][2][0]) / 2
    spread = abs(s['nleg'][2][0] - s['fleg'][2][0])
    cr.save(); cr.translate(fx + 10, 4); cr.scale(spread / 2 + 90, 18)
    cr.arc(0, 0, 1, 0, 2 * math.pi); cr.restore()
    cr.set_source_rgba(0.02, 0.01, 0.05, 0.55); cr.fill()

    arm(cr, s['farm'], P, False, F.hero)
    leg(cr, s['fleg'], P, False, F.hero)
    leg(cr, s['nleg'], P, True, F.hero)
    hip, sh = s['hip'], s['sh']
    if F.hero:
        blob(cr, [('circ', hip, 44)], P['shorts'])
    a = math.atan2(sh[0] - hip[0], hip[1] - sh[1])
    bk = np.array([-math.cos(a), -math.sin(a)])                  # torso "back" direction
    hem = [hip + bk * 46 + np.array([0, 18]), hip + bk * 52 + np.array([0, 34]) + lagb,
           hip + np.array([0, 38]) + lagb * 0.5, hip - bk * 44 + np.array([0, 22])]
    torso = [('cap', hip + np.array([0, 6]), sh, 46, 58), ('circ', sh, 34), ('poly', hem)]
    blob(cr, torso, P['tee'])
    blob(cr, [('cap', sh, s['head'], 19, 18)], P['skin'])
    # head + hair
    hp = [('circ', s['head'], R_HEAD)]
    if F.hero:
        blob(cr, hp, P['skin'])
        lx, ly = lagh[0] * F.d, lagh[1]                         # world lag -> local x
        # rotate lag into head-local axes
        ca, sa = math.cos(-s['ha']), math.sin(-s['ha'])
        lx, ly = lx * ca - ly * sa, lx * sa + ly * ca
        cap = [(-64, 18), (-70, -8), (-60, -40), (-36, -64), (0, -72), (34, -62), (56, -40),
               (60, -14), (44, -26), (34, -18), (20, -34), (-10, -30), (-34, -10), (-44, 22)]
        spikes = [[(-58, -44), (-96 + lx, -60 + ly), (-66, -16)],
                  [(-30, -64), (-52 + lx * .8, -100 + ly * .8), (-4, -70)],
                  [(-66, -4), (-100 + lx * 1.1, 6 + ly), (-62, 22)],
                  [(6, -70), (10 + lx * .5, -98 + ly * .5), (30, -62)]]
        prims = [('poly', head_pts(s, cap))] + [('poly', head_pts(s, sp)) for sp in spikes]
        blob(cr, prims, P['hair'], ow=4)
        # eye + brow
        ex, ey = head_pts(s, [(38, -2)])[0]
        cr.set_source_rgba(*C('#140c10')); cr.arc(ex, ey, 7.5, 0, 2 * math.pi); cr.fill()
        b = head_pts(s, [(24, -18), (52, -14)])
        cr.set_line_width(7); cr.set_line_cap(cairo.LINE_CAP_ROUND)
        cr.move_to(*b[0]); cr.line_to(*b[1]); cr.stroke()
    else:
        blob(cr, hp, P['skin'])
    if smear:
        pts = [F.sk(ta - i * 0.011)['narm'][2] for i in range(7)][::-1]
        for i in range(len(pts) - 1):
            u = (i + 1) / (len(pts) - 1)
            cr.set_source_rgba(*P['skin'][:3], 0.18 + 0.4 * u)
            cap_path(cr, pts[i], pts[i + 1], R_HAND * (0.25 + 0.6 * u - 0.1), R_HAND * (0.25 + 0.6 * u))
            cr.fill()
    arm(cr, s['narm'], P, True, F.hero)
    cr.restore()
    return s


# ---------------------------------------------------------------- world
LW, LH = 1700, 2700
LC = np.array([850.0, 1350.0])          # layer pixel that sits at screen centre at CAM0
CAM0 = np.array([0.0, -470.0])
SC = np.array([540.0, 960.0])


def peaks(rng, x0, x1, ybase, hmin, hmax, step):
    pts, x = [], x0
    while x < x1:
        pts.append((x, ybase - rng.uniform(hmin, hmax))); x += rng.uniform(*step)
        pts.append((x, ybase - rng.uniform(0, hmin * 0.5))); x += rng.uniform(*step)
    return pts


def pine(cr, x, yb, h, col):
    cr.set_source_rgba(*col)
    w = h * 0.42
    for i, (f, ww) in enumerate(((0.0, 1.0), (0.3, 0.78), (0.56, 0.55))):
        y0 = yb - h * f - h * 0.08
        cr.move_to(x - w * ww, y0); cr.line_to(x, y0 - h * 0.46); cr.line_to(x + w * ww, y0); cr.close_path()
    cr.rectangle(x - h * 0.04, yb - h * 0.1, h * 0.08, h * 0.12)
    cr.fill()


def surf_to_np(surf):
    a = np.ndarray((surf.get_height(), surf.get_width(), 4), np.uint8, surf.get_data()).copy()
    return a[..., [2, 1, 0, 3]].astype(np.float32) / 255.0      # premultiplied RGBA


def make_layers():
    rng = np.random.default_rng(11)
    layers = []
    gy = lambda wy: wy - CAM0[1] + LC[1]                       # world y -> layer y (at CAM0)

    def new():
        s = cairo.ImageSurface(cairo.FORMAT_ARGB32, LW, LH); return s, cairo.Context(s)

    # sky + stars + moon (p ~ 0.03)
    s, cr = new()
    g = cairo.LinearGradient(0, 0, 0, LH)
    g.add_color_stop_rgba(0.0, *C('#120a29')); g.add_color_stop_rgba(0.48, *C('#2a1850'))
    g.add_color_stop_rgba(0.62, *C('#41286e')); g.add_color_stop_rgba(1.0, *C('#41286e'))
    cr.set_source(g); cr.paint()
    for _ in range(26):
        x, y = rng.uniform(0, LW), rng.uniform(250, 1250)
        cr.set_source_rgba(1, 0.96, 0.9, rng.uniform(0.35, 0.85))
        cr.arc(x, y, rng.uniform(1.5, 3.2), 0, 2 * math.pi); cr.fill()
    mx, my, mr = LC[0] + 40, LC[1] - 600, 215
    rg = cairo.RadialGradient(mx, my, mr, mx, my, mr * 1.7)
    rg.add_color_stop_rgba(0, 1, 0.93, 0.78, 0.16); rg.add_color_stop_rgba(1, 1, 0.93, 0.78, 0)
    cr.set_source(rg); cr.arc(mx, my, mr * 1.7, 0, 2 * math.pi); cr.fill()
    cr.set_source_rgba(*C('#f3e5c0')); cr.arc(mx, my, mr, 0, 2 * math.pi); cr.fill()
    cr.set_source_rgba(*C('#e2cf9f'))
    for dx, dy, r in ((-70, -40, 42), (60, 50, 30), (-20, 90, 22), (80, -70, 18)):
        cr.arc(mx + dx, my + dy, r, 0, 2 * math.pi); cr.fill()
    layers.append((surf_to_np(s), 0.03, 0))

    def ridge(col, yb_, hmin, hmax, step, p, blur, rim=None):
        s, cr = new()
        pts = peaks(rng, -100, LW + 100, yb_, hmin, hmax, step)
        cr.move_to(-100, LH)
        for x, y in pts:
            cr.line_to(x, y)
        cr.line_to(LW + 100, LH); cr.close_path(); cr.set_source_rgba(*col); cr.fill()
        if rim:  # moon-side facets, flat lighter tone
            cr.set_source_rgba(*rim)
            for i in range(0, len(pts) - 1, 2):
                (xp, yp), (xv, yv) = pts[i], pts[i + 1]
                cr.move_to(xp, yp); cr.line_to(xv, yv); cr.line_to(xp + (xv - xp) * 0.35, yp + (yv - yp) * 0.9 + 40)
                cr.close_path(); cr.fill()
        a = surf_to_np(s)
        if blur:
            a = cv2.GaussianBlur(a, (0, 0), blur)
        layers.append((a, p, blur))

    ridge(C('#4a3684'), gy(-390), 120, 330, (110, 190), 0.12, 6, C('#58439a'))
    ridge(C('#312460'), gy(-230), 90, 220, (80, 150), 0.3, 3.5, C('#3b2d72'))
    # pine row at the back edge of the ground
    s, cr = new()
    base = gy(-95)
    cr.set_source_rgba(*C('#1c1438')); cr.rectangle(0, base - 20, LW, 160); cr.fill()
    x = -40
    while x < LW + 40:
        h = rng.uniform(150, 290); pine(cr, x, base + 10, h, C('#1c1438')); x += rng.uniform(38, 80)
    layers.append((cv2.GaussianBlur(surf_to_np(s), (0, 0), 1.6), 0.6, 1.6))
    # foreground (sharp): grass lip + corner pine + bush
    s, cr = new()
    col = C('#07040e')
    cr.set_source_rgba(*col)
    cr.move_to(0, LH)
    for i in range(0, LW + 30, 30):
        cr.line_to(i, gy(395) + 22 * math.sin(i * 0.05) + rng.uniform(-6, 6))
        cr.line_to(i + 12, gy(395) - rng.uniform(16, 44))
    cr.line_to(LW, LH); cr.close_path(); cr.fill()
    pine(cr, LC[0] - 640, gy(420), 900, col)
    cr.set_source_rgba(*col)
    for dx, dy, r in ((610, 360, 90), (680, 330, 110), (760, 370, 100)):
        cr.arc(LC[0] + dx, gy(dy), r, 0, 2 * math.pi); cr.fill()
    fg = (surf_to_np(s), 1.35, 0)
    return layers, fg


def layer_matrix(cam, z, rot, shake, p):
    zp = 1 + (z - 1) * p
    sh = (cam - CAM0) * p
    ca, sa = math.cos(rot), math.sin(rot)
    # screen = R*(q - LC - sh)*zp + SC + shake
    A = np.array([[ca * zp, -sa * zp], [sa * zp, ca * zp]])
    t = SC + shake - A @ (LC + sh)
    return np.hstack([A, t[:, None]]).astype(np.float32)


def over(dst, src):
    dst *= (1 - src[..., 3:4]); dst += src[..., :3]


# ---------------------------------------------------------------- camera
CAM_KEYS = [(0.0, (0, -470, 1.0)), (1.22, (-20, -500, 1.11)), (1.42, (40, -490, 1.08)),
            (2.15, (105, -480, 1.05)), (179 / 60, (0, -470, 1.0))]
SHAKE = {75: (14, -9), 76: (-11, 7), 77: (6, -4)}


def camera(f):
    t = f / FPS
    if f in CLOSE:
        u = (f - CLOSE[0]) / (len(CLOSE) - 1)
        face = OPP.world(OPP.sk(ta_of(f))['head'])
        c = IMPACT_PT * (1 - 0.8 * u) + face * 0.8 * u
        return c, 2.5 + 0.25 * ease(u, 'out'), math.radians(-6), np.array(SHAKE.get(f, (0, 0)), float)
    for (t0, a), (t1, b) in zip(CAM_KEYS, CAM_KEYS[1:]):
        if t <= t1:
            u = ease((t - t0) / (t1 - t0), 'io')
            v = [a[i] + (b[i] - a[i]) * u for i in range(3)]
            return np.array(v[:2]), v[2], 0.0, np.zeros(2)
    return np.array(CAM_KEYS[-1][1][:2], float), 1.0, 0.0, np.zeros(2)


def draw_ground(cr):
    g = cairo.LinearGradient(0, -100, 0, 700)
    g.add_color_stop_rgba(0, *C('#1d1436')); g.add_color_stop_rgba(1, *C('#0d0820'))
    cr.set_source(g); cr.rectangle(-3000, -100, 6000, 4000); cr.fill()
    cr.set_source_rgba(*C('#271c45')); cr.rectangle(-3000, -100, 6000, 6); cr.fill()
    rng = np.random.default_rng(3)
    for _ in range(26):  # stones/tufts give the ground parallax texture
        x, y = rng.uniform(-1200, 1200), rng.uniform(-80, 260)
        cr.set_source_rgba(*C('#2a1f4a'))
        cr.save(); cr.translate(x, y); cr.scale(rng.uniform(14, 34), rng.uniform(4, 9))
        cr.arc(0, 0, 1, 0, 2 * math.pi); cr.restore(); cr.fill()


def sparks(cr, f):
    if f in CLOSE:
        u = (f - CLOSE[0]) / 7.0
        k = 1.0
    elif 82 <= f < 88:
        u, k = (f - 82) / 6.0, 1.7
    else:
        return
    if u > 1:
        return
    cr.set_line_cap(cairo.LINE_CAP_ROUND)
    for i, ang in enumerate((-150, -115, -70, -30, 15, 55, 100)):
        a = math.radians(ang + 180)                    # away from the hero
        r1, r2 = (16 + 40 * u) * k, (34 + 70 * u) * k * (0.8 + 0.2 * (i % 2))
        cr.set_source_rgba(1, 0.94, 0.7, 1 - u * 0.8)
        cr.set_line_width(max(1.0, 6 * (1 - u)) * (1 if k == 1 else 2.2))
        c = IMPACT_PT
        cr.move_to(c[0] + r1 * math.cos(a), c[1] + r1 * math.sin(a))
        cr.line_to(c[0] + r2 * math.cos(a), c[1] + r2 * math.sin(a)); cr.stroke()


def render_one(f, ta, layers, fg, smear):
    cam, z, rot, shake = camera(f)
    img = np.zeros((H, W, 3), np.float32)
    for a, p, _ in layers:
        M = layer_matrix(cam, z, rot, shake, p)
        warped = cv2.warpAffine(a, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE if p < 0.05 else cv2.BORDER_CONSTANT)
        over(img, warped)
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    cr = cairo.Context(surf)
    cr.translate(*(SC + shake)); cr.rotate(rot); cr.scale(z, z); cr.translate(-cam[0], -cam[1])
    draw_ground(cr)
    draw_fighter(cr, OPP, ta)
    draw_fighter(cr, HERO, ta, smear=smear)
    sparks(cr, f)
    surf.flush()
    over(img, surf_to_np(surf))
    M = layer_matrix(cam, z, rot, shake, fg[1])
    over(img, cv2.warpAffine(fg[0], M, (W, H), flags=cv2.INTER_LINEAR))
    return img


def render(f, layers, fg):
    ta = ta_of(f)
    strike = STRIKE[0] <= ta < STRIKE[1] and f not in CLOSE
    if strike:  # 4 sub-frames -> motion blur on the fast strike only
        img = sum(render_one(f, ta + (k - 1.5) / 240, layers, fg, True) for k in range(4)) / 4
    else:
        img = render_one(f, ta, layers, fg, False)
    if f in FLASH:
        a = FLASH[f]
        img = img * (1 - a) + np.array([1.0, 0.86, 0.5], np.float32) * a
    return (np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8)


# ---------------------------------------------------------------- audio
SR = sfx.SR


def audio(path):
    n = int(SR * 3.0); mix = np.zeros(n)
    rng = np.random.default_rng(5)

    def put(sig, t, g=1.0):
        i = int(round(t * SR)); seg = sig[:n - i]; mix[i:i + len(seg)] += seg * g

    put(sfx.whoosh(0.26, 14), 0.30, 0.9)                         # opponent punch
    put(sfx.whoosh(0.16, 34), 0.38, 0.35)                        # hero slip
    d = 0.17; t = np.arange(int(SR * d)) / SR                    # strike whoosh rises into the hit
    nz = sfx.lp(rng.standard_normal(len(t)), 9) * (t / d) ** 2.2
    put(nz * 1.5, 1.25 - d, 1.0)
    hit = sfx.thump(0.32) * 1.3
    crack = sfx.lp(rng.standard_normal(int(SR * 0.03)), 2) * np.exp(-np.arange(int(SR * .03)) / SR * 140)
    hit[:len(crack)] += crack * 1.1
    put(hit, 1.25); put(sfx.boom(0.9), 1.25, 0.95)               # thump + bass hit on flash frame
    put(sfx.thump(0.14), 1.42, 0.3)                              # hero lands
    d = 0.75; t = np.arange(int(SR * d)) / SR                    # knock-back slide scuff
    put(sfx.lp(rng.standard_normal(len(t)), 22) * np.sin(np.pi * t / d) ** 1.5 * np.exp(-t * 2), 1.36, 0.6)
    put(sfx.thump(0.12), 2.28, 0.18); put(sfx.thump(0.12), 2.50, 0.18)
    fade = np.ones(n); fade[-int(SR * .03):] = np.linspace(1, 0, int(SR * .03)); mix *= fade

    def measure(x):
        tmp = path + '.tmp.wav'; write_wav(tmp, x)
        r = subprocess.run(['ffmpeg', '-nostats', '-i', tmp, '-af', 'ebur128=peak=true', '-f', 'null', '-'],
                           capture_output=True, text=True).stderr
        os.remove(tmp)
        I = float(r.split('Integrated loudness:')[1].split('I:')[1].split('LUFS')[0])
        P = float(r.split('True peak:')[1].split('Peak:')[1].split('dBFS')[0])
        return I, P

    g, ceil = 1.0 / np.abs(mix).max(), 10 ** (-2.0 / 20)
    for _ in range(8):
        y = np.tanh(mix * g / ceil) * ceil
        I, P = measure(y)
        if abs(I + 14) < 0.3 and P <= -1.0:
            break
        g *= 10 ** ((-14 - I) / 20)
    write_wav(path, y)
    return I, P


def write_wav(path, x):
    import wave
    st = (np.clip(np.stack([x, x], 1), -1, 1) * 32767).astype('<i2')
    with wave.open(path, 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(st.tobytes())


# ---------------------------------------------------------------- main
def setup():
    global IMPACT_PT
    print('punch fit err %.1f px hx=%d nsa=%d' % solve_punch())
    err = solve_impact()
    IMPACT_PT = (HERO.world(HERO.sk(1.25)['narm'][2]) + OPP.world(OPP.sk(1.25)['head'])) / 2
    return err


def main():
    os.makedirs(OUT, exist_ok=True)
    err = setup()
    print('impact fit err %.1f px hx=%d nsa=%d' % err)
    layers, fg = make_layers()
    if '--frames' in sys.argv:
        fr = [int(x) for x in sys.argv[sys.argv.index('--frames') + 1].split(',')]
        for f in fr:
            cv2.imwrite(os.path.join(OUT, 'f%03d.png' % f), render(f, layers, fg)[..., ::-1])
        return
    wav = os.path.join(OUT, 'hook-sfx.wav')
    I, P = audio(wav)
    print('audio I=%.1f LUFS TP=%.1f dBTP' % (I, P))
    mp4 = os.path.join(OUT, 'hook-preview.mp4')
    cmd = ['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '%dx%d' % (W, H),
           '-r', str(FPS), '-i', '-', '-i', wav, '-map', '0:v', '-map', '1:a',
           '-c:v', 'libx264', '-preset', 'slow', '-crf', '17', '-pix_fmt', 'yuv420p',
           '-vf', 'setsar=1', '-aspect', '9:16', '-c:a', 'aac', '-b:a', '256k', '-t', '3.0',
           '-movflags', '+faststart', mp4]
    pr = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    over_n = 0
    for f in range(NF):
        over_n += HERO.sk(ta_of(f))['over'] + OPP.sk(ta_of(f))['over']
        pr.stdin.write(render(f, layers, fg).tobytes())
    pr.stdin.close(); pr.wait()
    print('leg over-reach frames:', over_n, '->', mp4)


IMPACT_PT = np.zeros(2)
if __name__ == '__main__':
    main()
