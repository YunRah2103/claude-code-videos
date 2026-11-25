"""Yub, the channel's main character, as a smooth low-poly 3D figure for the cinematic renderer.
Look (from the skit videos and the owner's notes): brown skin, dark hair with a MIDDLE PART falling to both sides,
silver square glasses, plain WHITE T-SHIRT, BLACK JEANS, white sneakers. Big friendly head so expressions read.
yub(expr, look, la, ra, head, sit, step, lean, held, wave, sweat, blush) faces +z, feet at y=0 (sitting: seat y=0.5)."""
import math, os, sys
from functools import lru_cache
_HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (_HERE, os.path.join(_HERE, "..", "..", "lib", "cine3d")):
    if os.path.abspath(_p) not in sys.path: sys.path.insert(0, os.path.abspath(_p))
import numpy as np
from geo import (P, cat, tex, quad, word_tex, PAINT, cb, bbox, capsule, superellipsoid, sphere, lathe, MATTE, SKIN as M_SKIN, CHROME, CLOTH,
                 HAIR as M_HAIR, RUBBER, rgb)
import facedraw as H2D                               # 2D face drawing (expressions), same folder

SKIN = (190, 128, 90); SKIN_D = (160, 104, 72); HAIRC = (30, 24, 28)
TEE = (246, 246, 248); TEE_D = (222, 222, 228); JEANS = (34, 35, 42); SHOE = (248, 248, 250); SOLE = (214, 214, 220)
GLASS = (176, 182, 194)
H2D.SKIN = SKIN; H2D.HAIR = HAIRC

@lru_cache(None)
def face(expr="smile", look="c", sweat=False, blush=False): return tex(H2D._face(expr, look, sweat, blush))

# head geometry
HA, HB, HC, HYC = 0.142, 0.165, 0.138, 1.63         # half width / height / depth, centre height
FS = 0.84
EX, EY = H2D.EX, H2D.EY
EXPR_NAMES = list(H2D.EXPR)                          # smile grin shock panic sad smug confused deadpan cringe proud angry

def _sz(x, y):
    q = 1 - (abs(x) / HA) ** (2 / 0.7); r = 1 - (abs(y) / HB) ** (2 / 0.75)
    return HC * max(r, 0) ** 0.375 * max(q, 0) ** 0.35 if q > 0 and r > 0 else 0.0

def _head(fid):
    h = superellipsoid(HA, HB, HC, 0.75, 0.7, 34, 22, SKIN, M_SKIN)
    c = h.t.mean(1); front = (c[:, 2] > HC * 0.5) & (np.abs(c[:, 1]) < HB * 0.95)
    u = 0.5 + h.t[..., 0] / (2 * FS * HA); v = 0.5 - h.t[..., 1] / (2 * FS * HB)
    h.k[front] = fid; h.c[front] = 1.0
    h.uv[front] = np.stack([np.clip(u, 0.01, 0.99), np.clip(v, 0.01, 0.99)], -1)[front]
    return h.mv(0, HYC, 0)

def _hair():
    """Hair cap whose front edge is a curtain: high at the centre part, sweeping down past the temples. The two halves
    tilt apart slightly so the middle part shows as a scalp line along the top."""
    out = []
    top = HYC + HB
    for sg in (-1, 1):
        sh = superellipsoid(HA * 1.1, HB * 1.1, HC * 1.12, 0.72, 0.68, 26, 16, HAIRC, M_HAIR).mv(0, HYC + 0.012, -0.004)
        c = sh.t.mean(1)
        ax = np.abs(c[:, 0]) / HA
        front = HYC + 0.104 - 0.048 * np.clip(ax / 0.45, 0, 1) ** 0.6 - 0.05 * np.clip((ax - 0.45) / 0.55, 0, 1)
        tz = np.clip((-c[:, 2] / HC + 0.3) / 1.3, 0, 1)
        yth = front + ((HYC - HB + 0.07) - front) * tz
        yth = np.where(ax > 0.9, np.minimum(yth, HYC - 0.01), yth)
        keep = (c[:, 1] > yth) & (c[:, 0] * sg > -0.002)
        sh.keep(keep)
        sh.rot("z", -sg * 5.0, (0, top - 0.02, 0)).mv(sg * 0.006, 0.004, 0)
        out.append(sh)
        # curtain locks along the fringe edge (soft wedges)
        for x in (0.03, 0.075, 0.115):
            ax_ = x / HA; yr = HYC + 0.106 - 0.048 * min(ax_ / 0.45, 1) ** 0.6 - 0.05 * min(max((ax_ - 0.45) / 0.55, 0), 1)
            z0 = _sz(x, yr - HYC) + 0.018
            tip = (sg * (x + 0.02), yr - 0.028, _sz(x + 0.02, yr - 0.028 - HYC) + 0.013)
            a, b = (sg * (x - 0.022), yr + 0.02, z0), (sg * (x + 0.026), yr + 0.012, z0 - 0.004)
            a2, b2 = (a[0], a[1], a[2] - 0.03), (b[0], b[1], b[2] - 0.03)
            out.append(P([a, b, tip, a2, b2, tip, a, a2, tip, b, b2, tip], HAIRC, m=M_HAIR).smooth(40))
    return out

def _glasses():
    out = []; t = 0.008; hw, hh = 0.042, 0.031
    ey = -(EY - 0.5) * 2 * FS * HB
    for u in EX:
        cx = (u - 0.5) * 2 * FS * HA
        z = max(_sz(cx + dx, ey + dy) for dx in (-hw, 0, hw) for dy in (-hh, 0, hh)) + 0.009
        y = HYC + ey
        out += [cb(cx, y + hh, z, 2 * hw + t, t, t, GLASS, b=0.003, m=CHROME), cb(cx, y - hh, z, 2 * hw + t, t, t, GLASS, b=0.003, m=CHROME),
                cb(cx - hw, y, z, t, 2 * hh, t, GLASS, b=0.003, m=CHROME), cb(cx + hw, y, z, t, 2 * hh, t, GLASS, b=0.003, m=CHROME)]
    xr = (EX[1] - 0.5) * 2 * FS * HA
    out.append(cb(0, HYC + ey + 0.012, _sz(0, ey) + 0.012, 2 * (xr - hw), t * 0.8, t, GLASS, b=0.002, m=CHROME))
    for sg in (-1, 1):
        x = sg * (xr + hw); z0 = _sz(abs(x), ey) + 0.009
        out.append(cb(x + sg * 0.008, HYC + ey + 0.012, (z0 - 0.06) / 2, t, t, z0 + 0.06, GLASS, b=0.002, m=CHROME).rot("y", sg * 10, (x, 0, z0)))
    return out

CAP = (26, 26, 30)
T_LTN = None
def _cap():
    """Black baseball cap with a white LTN logo on the front panel, worn straight; the middle-part curtain shows below."""
    global T_LTN
    if T_LTN is None: T_LTN = word_tex("LTN", 256, 112, (226, 226, 230), CAP, 84, weight="black")
    top = HYC + HB
    cr = superellipsoid(HA * 1.13, HB * 0.82, HC * 1.15, 0.72, 0.7, 26, 14, CAP, MATTE).mv(0, HYC + 0.045, -0.004)
    c = cr.t.mean(1); back = np.clip(-c[:, 2] / HC, 0, 1)
    cr.keep(c[:, 1] > HYC + 0.088 - 0.04 * back)
    # LTN decal: a small curved grid hugging the crown's front
    ca, cbb, cc, cy0 = HA * 1.13, HB * 0.82, HC * 1.15, HYC + 0.045
    def zc(x, y):
        r = max(0.0, 1 - (abs(y - cy0) / cbb) ** (2 / 0.72)) ** (0.72 / 0.7) - (abs(x) / ca) ** (2 / 0.7)
        return cc * max(r, 0.0) ** (0.7 / 2) - 0.004 + 0.006
    xs = np.linspace(-0.078, 0.078, 13); ys = np.linspace(HYC + 0.108, HYC + 0.176, 6); dec = []
    for i in range(12):
        for j in range(5):
            pts = [(xs[i], ys[j]), (xs[i + 1], ys[j]), (xs[i + 1], ys[j + 1]), (xs[i], ys[j + 1])]
            q = [(x, y, zc(x, y)) for x, y in pts]
            uv = [((x + 0.078) / 0.156, 1 - (y - ys[0]) / (ys[-1] - ys[0])) for x, y in pts]
            dec.append(P([q[0], q[1], q[2], q[0], q[2], q[3]], (255, 255, 255), T_LTN, [uv[0], uv[1], uv[2], uv[0], uv[2], uv[3]], m=MATTE))
    decal = cat(dec).smooth(60)
    brim = superellipsoid(HA * 1.05, 0.011, 0.12, 0.5, 0.75, 28, 6, CAP, MATTE)
    bc = brim.t.mean(1); brim.keep(bc[:, 2] > -0.01)
    brim.mv(0, HYC + 0.095, HC * 0.88).rot("x", 10, (0, HYC + 0.095, HC * 0.88))
    btn = sphere(0.014, 10, 6, CAP).mv(0, top + 0.03, -0.01)
    seams = [cb(sg * 0.002, top + 0.0, -0.01, 0.004, 0.03, 0.2, (40, 40, 46), b=0.001).rot("z", sg * 0, (0, top, 0)) for sg in (1,)]
    return [cr, decal, brim, btn]

def _headgroup(expr, look, sweat, blush, hat=True):
    hd = _head(face(expr, look, sweat, blush))
    ny = HYC - 0.045; nz = _sz(0, -0.045)
    nose = superellipsoid(0.013, 0.021, 0.015, 0.8, 0.8, 10, 8, SKIN_D, M_SKIN).mv(0, ny, nz - 0.002)
    ears = [superellipsoid(0.02, 0.036, 0.03, 0.8, 0.8, 10, 8, SKIN_D, M_SKIN).mv(sg * (HA - 0.004), HYC - 0.005, -0.012) for sg in (-1, 1)]
    neck = capsule((0, 1.38, -0.005), (0, 1.5, -0.005), 0.052, 12, SKIN_D, M_SKIN)
    return cat([hd, nose, *ears, neck, *_hair(), *_glasses()] + (_cap() if hat else []))

def _hand(wave=False):
    palm = superellipsoid(0.042, 0.05, 0.022, 0.7, 0.7, 12, 8, SKIN, M_SKIN).mv(0, -0.05, 0)
    if wave:
        fing = [capsule((-0.03 + 0.02 * i, -0.08, 0), (-0.036 + 0.026 * i, -0.13 - 0.012 * (i in (1, 2)), 0), 0.0095, 8, SKIN, M_SKIN) for i in range(4)]
    else:
        fing = [superellipsoid(0.042, 0.03, 0.026, 0.7, 0.7, 12, 8, SKIN, M_SKIN).mv(0, -0.1, 0.006)]
    th = capsule((0.035, -0.03, 0.008), (0.06, -0.075, 0.018), 0.011, 8, SKIN, M_SKIN)
    return cat([palm, *fing, th])

def _arm(side, fw, out, bend, held=None, wave=False):
    up = cat([capsule((0, 0, 0), (0, -0.26, 0), 0.052, 9, SKIN, M_SKIN),
              lathe([(0.0, 0.03), (0.064, 0.02), (0.066, -0.06), (0.062, -0.13), (0.058, -0.14)], 14, TEE, CLOTH)])   # short sleeve
    fore = [capsule((0, -0.27, 0), (0, -0.5, 0), 0.046, 9, SKIN, M_SKIN, r1=0.038), _hand(wave).mv(0, -0.52, 0)]
    fore = cat(fore)
    if held is not None: fore = cat([fore, held.copy().mv(0, -0.6, 0.045)])
    fore.rot("x", -bend, (0, -0.27, 0))
    return cat([up, fore]).rot("x", -fw).rot("z", side * out).mv(side * 0.205, 1.34, 0)

def _shoe():
    body = superellipsoid(0.058, 0.045, 0.125, 0.6, 0.6, 16, 10, SHOE, MATTE).mv(0, 0.055, 0.04)
    sole = superellipsoid(0.062, 0.016, 0.13, 0.5, 0.6, 16, 8, SOLE, RUBBER).mv(0, 0.016, 0.04)
    lace = cb(0, 0.094, 0.06, 0.06, 0.012, 0.08, (236, 236, 240), b=0.004)
    return cat([body, sole, lace])

def yub(expr="smile", look="c", la=(0, 8, 10), ra=(0, 8, 10), head=(0, 0, 0), sit=False, step=0.0, lean=0.0, held=None,
        wave=None, sweat=False, blush=False, bob=0.0, hat=True):
    parts = []
    if sit:
        for sx in (-0.09, 0.09):
            parts += [capsule((sx, 0.55, 0.0), (sx, 0.55, 0.42), 0.075, 9, JEANS, CLOTH),
                      capsule((sx, 0.55, 0.42), (sx, 0.12, 0.46), 0.065, 9, JEANS, CLOTH, r1=0.058),
                      _shoe().mv(sx, 0, 0.44)]
        dy = -0.32
    else:
        for sx, ph in ((-0.09, step), (0.09, -step)):
            leg = cat([capsule((sx, 0.88, 0), (sx, 0.48, 0.01), 0.078, 9, JEANS, CLOTH, r1=0.066),
                       capsule((sx, 0.48, 0.01), (sx, 0.13, 0), 0.064, 9, JEANS, CLOTH, r1=0.058), _shoe().mv(sx, 0, 0)])
            parts.append(leg.rot("x", ph, (0, 0.88, 0)))
        dy = 0.0
    up = [superellipsoid(0.158, 0.1, 0.1, 0.55, 0.7, 20, 9, JEANS, CLOTH).mv(0, 0.9, 0),           # hips
          superellipsoid(0.19, 0.29, 0.115, 0.32, 0.6, 18, 12, TEE, CLOTH).mv(0, 1.165, 0),            # t-shirt torso
          *[sphere(0.07, 14, 10, TEE, CLOTH).sc(1, 0.85, 1).mv(sg * 0.19, 1.36, 0) for sg in (-1, 1)],  # shoulders
          lathe([(0.062, 0.0), (0.068, 0.012), (0.06, 0.02)], 16, TEE_D, CLOTH).mv(0, 1.44, 0.0),      # crew neck
          ]
    h = _headgroup(expr, look, sweat, blush, hat).rot("z", head[2], (0, 1.45, 0)).rot("x", head[1], (0, 1.45, 0)).rot("y", head[0], (0, 1.45, 0))
    up.append(h)
    for side, a in ((-1, la), (1, ra)):
        up.append(_arm(side, *a, held=held if side == 1 else None, wave=(wave == ("l" if side == -1 else "r"))))
    upper = cat(up).rot("x", lean, (0, 0.88, 0)).mv(0, dy + bob, 0)
    return cat(parts + [upper])
