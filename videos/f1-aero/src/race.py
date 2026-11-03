"""Big F1 circuit: spline centreline, track surface, scenery, and a simulated 6-car race."""
import math
import numpy as np
from engine import C, col, hr, W, H, Iso, noise_tex, backdrop, ease
from scenes import GOLD, tree
import car as CAR

HW = 22.0                                     # half road width (car width is 13 -> ~3.4 cars wide)
CTRL = [(0, 0), (420, -10), (560, 20), (640, 120), (610, 240), (480, 270), (400, 340), (430, 470), (360, 560),
        (160, 580), (40, 520), (30, 400), (140, 330), (150, 220), (40, 170), (-80, 120), (-110, 40)]


def _spline(pts, n=24):
    P = np.array(pts, float); out = []
    for i in range(len(P)):
        p0, p1, p2, p3 = P[i - 1], P[i], P[(i + 1) % len(P)], P[(i + 2) % len(P)]
        for u in np.linspace(0, 1, n, endpoint=False):
            out.append(.5 * ((2 * p1) + (-p0 + p2) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u * u + (-p0 + 3 * p1 - 3 * p2 + p3) * u ** 3))
    return np.array(out)


def _resample(P, step=3.0):
    seg = np.r_[np.hypot(*np.diff(np.vstack([P, P[:1]]), axis=0).T)]
    s = np.r_[0, np.cumsum(seg)]; total = s[-1]
    q = np.arange(0, total, step)
    X = np.interp(q, s, np.r_[P[:, 0], P[0, 0]]); Y = np.interp(q, s, np.r_[P[:, 1], P[0, 1]])
    return np.c_[X, Y], total


PTS, LEN = _resample(_spline(CTRL))
N_PTS = len(PTS)
TAN = np.roll(PTS, -1, 0) - np.roll(PTS, 1, 0); TAN /= np.hypot(*TAN.T)[:, None]
NOR = np.c_[-TAN[:, 1], TAN[:, 0]]
_ang = np.unwrap(np.arctan2(TAN[:, 1], TAN[:, 0]))
KAP = np.gradient(_ang) / 3.0                                       # signed curvature
KAP_S = np.convolve(np.r_[KAP[-20:], KAP, KAP[:20]], np.ones(21) / 21, 'same')[20:-20]
CORNER = np.abs(KAP_S) > 1 / 170


def at(s):
    """Position, heading and curvature at arc length s (+ lateral offset handled by caller)."""
    f = (s % LEN) / 3.0; i = int(f) % N_PTS; j = (i + 1) % N_PTS; u = f - int(f)
    p = PTS[i] * (1 - u) + PTS[j] * u
    tg = TAN[i] * (1 - u) + TAN[j] * u
    return p, math.atan2(tg[1], tg[0]), KAP_S[i], NOR[i]


# ---------------------------------------------------------------- race simulation (precomputed)
V_MAX, V_MIN, A_LAT = 230.0, 85.0, 95.0
VPROF = np.clip(np.sqrt(A_LAT / np.maximum(np.abs(KAP_S), 1e-4)), V_MIN, V_MAX)
VPROF = np.minimum.reduce([np.roll(VPROF, -k) + k * 2.2 for k in range(60)])   # brake before corners
VPROF = np.convolve(np.r_[VPROF[-8:], VPROF, VPROF[:8]], np.ones(17) / 17, 'same')[8:-8]
TEAMS = [('BLU', 'blue'), ('RED', 'red'), ('ORA', 'orange'), ('GRN', 'green'), ('PNK', 'pink'), ('SIL', 'silver')]
START = [-46, 0, -100, -155, -210, -265]                             # hero (blue) starts P2, just behind red
PACE = [1.06, 1.0, .995, .99, .985, .98]
DT, TMAX = 1 / 60, 80.0


def _simulate():
    n = int(TMAX / DT); S = np.zeros((n, 6)); L = np.zeros((n, 6))
    s = np.array(START, float); base = np.array([0, -5, 5, -6, 4, -3], float); lat = base.copy()
    for k in range(n):
        tgt = base.copy()
        for i in range(6):
            for j in range(6):
                if i == j or PACE[i] <= PACE[j]: continue                 # only the faster car changes line
                ahead = (s[j] - s[i]) % LEN; behind = (s[i] - s[j]) % LEN
                if ahead < 70 or behind < 36:
                    tgt[i] = lat[j] + (16 if lat[j] <= 0 else -16)
        tgt = np.clip(tgt, -HW + 7, HW - 7)
        lat += (tgt - lat) * min(1, DT * 3)
        v = np.array([np.interp(si % LEN, np.arange(N_PTS) * 3.0, VPROF) for si in s]) * PACE
        for i in range(6):                                                # no driving through each other
            for j in range(6):
                gap = (s[j] - s[i]) % LEN
                if i != j and 0 < gap < 34 and abs(lat[j] - lat[i]) < 14: v[i] = min(v[i], v[j] * .96)
        s += v * DT; S[k], L[k] = s, lat
    return S, L


SIM_S, SIM_L = _simulate()

GX0, GY0, GS = PTS[:, 0].min() - 400, PTS[:, 1].min() - 400, 2.0
_gx = np.arange(GX0, PTS[:, 0].max() + 400, GS); _gy = np.arange(GY0, PTS[:, 1].max() + 400, GS)
NEAR = np.zeros((len(_gy), len(_gx)), np.int32)
for _r in range(0, len(_gy), 16):
    yy, xx = np.meshgrid(_gy[_r:_r + 16], _gx, indexing='ij')
    NEAR[_r:_r + 16] = np.argmin((xx[..., None] - PTS[:, 0]) ** 2 + (yy[..., None] - PTS[:, 1]) ** 2, axis=-1)


def cars_at(tau):
    k = min(len(SIM_S) - 1, max(0, int(tau / DT)))
    out = []
    for i in range(6):
        s, lat = SIM_S[k, i], SIM_L[k, i]
        p, th, kap, nr = at(s)
        lat2 = SIM_L[min(len(SIM_L) - 1, k + 6), i]
        yaw = math.atan2(lat2 - lat, 12)
        out.append(dict(i=i, s=s, X=p[0] + nr[0] * lat, Y=p[1] + nr[1] * lat, th=th + yaw * .6, kap=kap))
    return out


# ---------------------------------------------------------------- track surface
def ground(X, Y):
    gi = np.clip(((Y - GY0) / GS).astype(int), 0, NEAR.shape[0] - 1); gj = np.clip(((X - GX0) / GS).astype(int), 0, NEAR.shape[1] - 1)
    idx = NEAR[gi, gj]
    ox, oy = X - PTS[idx, 0], Y - PTS[idx, 1]
    d = ox * NOR[idx, 0] + oy * NOR[idx, 1]                       # signed lateral distance
    s = idx * 3.0 + ox * TAN[idx, 0] + oy * TAN[idx, 1]
    kap = KAP_S[idx]; corner = CORNER[idx]; ad = np.abs(d)
    a = noise_tex(X, Y, '#5e9e46', 10)
    a[((np.floor((X + Y) / 14)) % 2).astype(bool)] *= .93                              # mowing stripes
    outside = d * np.sign(kap) < 0
    grav = corner & outside & (ad > HW + 3.5) & (ad < HW + 46); a[grav] = noise_tex(X, Y, '#dcc690', 16)[grav]
    run = ~corner & (ad > HW) & (ad < HW + 9); a[run] = noise_tex(X, Y, '#5a6274', 8)[run]
    road = ad < HW; a[road] = noise_tex(X, Y, '#4a4a56', 8)[road]
    a[road & (np.abs(d + np.sign(kap) * 7) < 5)] *= .9                                  # rubbered racing line
    edge = road & ~corner & (ad > HW - 1.4) & (ad < HW - .4); a[edge] = col('#f0f0f4')
    kerb = corner & (ad >= HW) & (ad < HW + 3.5)
    st = ((np.floor(s / 4)) % 2).astype(bool); a[kerb & st] = col('#e8402a'); a[kerb & ~st] = col('#f4f4f4')
    sl = road & (np.abs(s % LEN - 30) < 2.5)
    a[sl] = np.where(((np.floor(s[sl] * .8) + np.floor(d[sl] * .8)) % 2).astype(bool)[:, None], col('#f4f4f4'), col('#16161c'))
    pit = (idx * 3.0 < 420) & (d < -HW - 16) & (d > -HW - 34); a[pit] = noise_tex(X, Y, '#565664', 8)[pit]
    a[pit & (np.abs(d + HW + 25) < .4)] = col('#f6c84a')
    return a


def scenery(I, cx, cy, radius, t):
    """Objects along the circuit near the camera, added to I for depth sorting."""
    for i in range(0, N_PTS, 6):
        P = PTS[i]
        if abs(P[0] - cx) + abs(P[1] - cy) > radius: continue
        s = i * 3.0; n = NOR[i]; kp = KAP_S[i]; out = -np.sign(kp) if kp else 1
        if CORNER[i]:
            if i % 12 == 0:                                                        # tyre wall on the outside
                X, Y = P + n * out * (HW + 50)
                I.add(X + Y, lambda X=X, Y=Y, k=i: I.box(X - 2, Y - 2, 0, 4, 4, 3.4, '#1c1c22' if k % 24 else '#e8402a'))
        else:
            if i % 18 == 0:                                                        # billboards
                X, Y = P + n * (HW + 12)
                cl = ['#e8402a', '#2a6ad0', '#f6c84a', '#3ac860', '#f4f4f4'][(i // 18) % 5]
                I.add(X + Y, lambda X=X, Y=Y, cl=cl: (I.box(X - 1, Y - 1, 0, 2, 2, 4, '#c8ccd8'), I.box(X - 6, Y - .5, 4, 12, 1, 5, cl)))
            if i % 6 == 0 and s < 420:                                             # pit wall
                X, Y = P + n * (-HW - 12)
                I.add(X + Y, lambda X=X, Y=Y: I.box(X - 9, Y - .8, 0, 18, 1.6, 3, '#e8e8f0'))
            if 60 < s < 380 and i % 24 == 0:                                       # pit garages
                X, Y = P + n * (-HW - 50)
                I.add(X + Y, lambda X=X, Y=Y: I.box(X - 18, Y - 8, 0, 36, 14, 12, '#d8dce6'))
    for kind, X, Y, sc in PROPS:
        if abs(X - cx) + abs(Y - cy) > radius: continue
        if kind == 'stand': I.add(X + Y + 40, lambda X=X, Y=Y: [I.box(X, Y + j * 5, j * 4, 60, 5, 4, '#8a90a2') for j in range(4)])
        else: I.add(X + Y, lambda X=X, Y=Y, sc=sc: tree(I, X, Y, sc))


def _props():
    out = []
    for gx in range(int(GX0), int(GX0 + len(_gx) * GS), 40):
        for gy in range(int(GY0), int(GY0 + len(_gy) * GS), 40):
            k = (gx // 40) * 131 + (gy // 40) * 37
            if hr(k, 3) < .5: continue
            X, Y = gx + hr(k, 4) * 30, gy + hr(k, 5) * 30
            d = np.min(np.hypot(PTS[:, 0] - X, PTS[:, 1] - Y))
            if d < HW + 60: continue
            out.append(('stand' if hr(k, 6) > .93 and d < HW + 110 else 'tree', X, Y, 2.2 + hr(k, 7) * 1.6))
    return out


PROPS = _props()


def view(tau, k=1.7, focus=None, t_anim=None, dim_others=False, extra=None):
    """Broadcast camera following the hero car. Returns (canvas, Iso, cars)."""
    cars = cars_at(tau)
    hero = cars[0] if focus is None else focus
    cx, cy = hero['X'], hero['Y']
    c = C(w=W, h=H)
    ox, oy = W / 2 - (cx - cy) * k, H * .52 - ((cx + cy) / 2) * k
    I = Iso(c, ox, oy, k, GOLD)
    rad = 170 / k * 1.9 + 40
    I.ground(ground)
    scenery(I, cx, cy, rad * 1.5, tau)
    ta = tau if t_anim is None else t_anim
    for cr in cars:
        if abs(cr['X'] - cx) + abs(cr['Y'] - cy) > rad * 2: continue
        I.add(cr['X'] + cr['Y'], lambda cr=cr: CAR.f1h(I, cr['X'], cr['Y'], cr['th'], ta, spin=22,
                                                       livery=TEAMS[cr['i']][1]))
    if extra: extra(I)
    I.draw()
    return c, I, cars


def standings(tau):
    cars = cars_at(tau)
    order = sorted(cars, key=lambda c_: -c_['s'])
    return [TEAMS[c_['i']] for c_ in order]


# ---------------------------------------------------------------- "no aero" corner test on the big circuit
IC = int(np.argmax(np.abs(KAP_S) * (np.arange(N_PTS) * 3.0 > 500)))      # a tight corner away from the start


def corner_view(lt, k=1.4):
    sc = IC * 3.0; v = 105.0
    s_a = sc - 150 + v * max(0, lt - .5)
    pa, tha, _, na = at(s_a)
    sb = sc - 55; pb, thb, kb, nb = at(sb)
    sg = sc - 150 + v * lt
    if sg < sb:
        pg, thg, _, _ = at(sg); yaw = 0
    else:
        dist = (sg - sb) * max(0, 1 - (sg - sb) / 260)
        dirv = np.array([math.cos(thb), math.sin(thb)])
        pg = pb + dirv * min(dist, 120); thg = thb; yaw = min(1.6, (sg - sb) / 60) * math.sin(lt * 3)
    P = (PTS[IC] - NOR[IC] * np.sign(KAP_S[IC]) * 10) * .2 + (pa + pg) / 2 * .8
    P = P + np.array([30, 30])                                # keep the cars above the presenter
    c = C(w=W, h=H)
    I = Iso(c, W / 2 - (P[0] - P[1]) * k, H * .5 - ((P[0] + P[1]) / 2) * k, k, GOLD)
    I.ground(ground)
    scenery(I, P[0], P[1], 260, lt)
    I.add(pg[0] + pg[1], lambda: CAR.f1h(I, pg[0], pg[1], thg + yaw, lt, ghost=True))
    I.add(pa[0] + pa[1], lambda: CAR.f1h(I, pa[0], pa[1], tha, lt, spin=20))
    I.draw()
    dust = sg > sb + 20
    if dust:
        for i in range(12):
            ph = (lt * 2.5 + i / 12) % 1
            q = pg - np.array([math.cos(thb), math.sin(thb)]) * (16 + ph * 14) + np.array([-math.sin(thb), math.cos(thb)]) * (i - 6) * 1.5
            x_, y_ = I.p(q[0], q[1], 1 + ph * 5)
            c.disc(x_, y_, 1 + ph * 3.5, col('#e8d8b0') * (1 - ph * .3))
    return c, I, (pg, pa), dust
