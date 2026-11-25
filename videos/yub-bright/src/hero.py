"""Yub's main character as a clean low-poly 3D figure, matched to the flat skit buyer (bmw-heated-seats etc.) and
characters/main-guy: brown skin, dark spiky hair with a fringe and two cowlicks, silver square glasses, navy blazer over
an open white shirt, charcoal trousers, white sneakers. Every part is a bevelled (chamfered) box so the silhouette reads
rounded; glasses, nose and ears are real geometry; the face texture is drawn at 256 px with anti-aliasing.
hero(expr, look, la, ra, head, sit, step, lean, held, wave) faces +z, feet at y=0 (sitting: seat at y=0.5)."""
import math
from functools import lru_cache
import numpy as np
from PIL import Image, ImageDraw
from lowpoly import P, cat, tex, quad, WHITE

SKIN = (192, 134, 96); SKIN_D = (164, 108, 76)
HAIR = (36, 28, 34); HAIR_L = (70, 56, 66)
GLASS = (196, 202, 214)
BLAZER = (38, 56, 118); BLAZER_D = (26, 38, 84)
SHIRT = (248, 248, 252); PANTS = (44, 46, 58); SHOE = (248, 248, 250); SOLE = (206, 206, 214)

# ---------------------------------------------------------------- bevelled box
def bbox(x0, y0, z0, x1, y1, z1, col, b=None, ftex=-1, bcol=None):
    """Chamfered cuboid: 6 inset faces, 12 bevel strips, 8 corner triangles. ftex textures the +z face (uv 0..1)."""
    b = min(x1 - x0, y1 - y0, z1 - z0) * 0.22 if b is None else b
    lo, hi = np.float32([x0, y0, z0]), np.float32([x1, y1, z1])
    def pt(ax, s, u, v):   # point on face (axis ax, side s) at inset-normalised coords u,v in {0,1}
        p = np.zeros(3, np.float32); o = [a for a in range(3) if a != ax]
        p[ax] = hi[ax] if s > 0 else lo[ax]
        p[o[0]] = (lo[o[0]] + b) if u == 0 else (hi[o[0]] - b)
        p[o[1]] = (lo[o[1]] + b) if v == 0 else (hi[o[1]] - b)
        return tuple(p)
    tris, cols, ks, uvs = [], [], [], []
    def add(q, c=col, k=-1, uv=((0, 0),) * 3):
        tris.append(q); cols.append(c); ks.append(k); uvs.append(uv)
    for ax in range(3):
        for s in (-1, 1):
            a, bb, c, d = pt(ax, s, 0, 0), pt(ax, s, 1, 0), pt(ax, s, 1, 1), pt(ax, s, 0, 1)
            if ax == 2 and s > 0 and ftex >= 0:
                # +z face: o = (x, y); uv u = x, v = 1 - y
                add((a, bb, c), (255, 255, 255), ftex, ((0, 1), (1, 1), (1, 0))); add((a, c, d), (255, 255, 255), ftex, ((0, 1), (1, 0), (0, 0)))
            else:
                add((a, bb, c)); add((a, c, d))
    # bevel strips between faces of different axes (a1,s1) and (a2,s2)
    for a1 in range(3):
        for a2 in range(a1 + 1, 3):
            k = 3 - a1 - a2
            for s1 in (-1, 1):
                for s2 in (-1, 1):
                    def ptk(ax, s, other_ax, other_s, kk):
                        o = [a for a in range(3) if a != ax]
                        uv = [0, 0]; uv[o.index(other_ax)] = 0 if other_s < 0 else 1; uv[o.index(k)] = kk
                        return pt(ax, s, *uv)
                    p1, p2 = ptk(a1, s1, a2, s2, 0), ptk(a1, s1, a2, s2, 1)
                    q1, q2 = ptk(a2, s2, a1, s1, 0), ptk(a2, s2, a1, s1, 1)
                    add((p1, p2, q2), bcol or col); add((p1, q2, q1), bcol or col)
    for sx in (-1, 1):
        for sy in (-1, 1):
            for sz in (-1, 1):
                S = (sx, sy, sz)
                corner = []
                for ax in range(3):
                    o = [a for a in range(3) if a != ax]
                    corner.append(pt(ax, S[ax], 0 if S[o[0]] < 0 else 1, 0 if S[o[1]] < 0 else 1))
                add(tuple(corner), bcol or col)
    p = P(np.float32(tris), (255, 255, 255), -1, np.float32(uvs)); p.c = np.float32(cols) / 255.0; p.k = np.int32(ks)
    return p

def cb(cx, cy, cz, sx, sy, sz, col, **kw): return bbox(cx - sx / 2, cy - sy / 2, cz - sz / 2, cx + sx / 2, cy + sy / 2, cz + sz / 2, col, **kw)

def clean(p):
    """No grime layer on the character: untextured faces sample a plain white texture."""
    p.k = np.where(p.k < 0, WHITE, p.k).astype(np.int32); return p

# ---------------------------------------------------------------- face texture (256 px, drawn 4x and downsampled)
N, SS = 256, 4
EX = (0.31, 0.69); EY = 0.47              # eye centres in face uv (also used to place the 3D glasses)
EXPR = {   # eyes, brows (left dy, right dy, inner tilt), mouth
    "smile": ("norm", (0, 0, 0), "smile"), "grin": ("closed", (-4, -4, 0), "grin"), "shock": ("wide", (-16, -16, 0), "o"),
    "panic": ("wide", (-14, -14, 8), "grit"), "sad": ("norm", (0, 0, -9), "frown"), "smug": ("half", (-12, 2, 0), "smirk"),
    "confused": ("norm", (-14, 4, 0), "squiggle"), "deadpan": ("half", (2, 2, 0), "flat"), "cringe": ("squeeze", (4, 4, 8), "grit"),
    "proud": ("closed", (-6, -6, 0), "smile"), "angry": ("norm", (4, 4, 12), "grit"),
}

def _face(expr="smile", look="c", sweat=False, blush=False):
    eyes, (bl, br, tilt), mouth = EXPR[expr]
    M = N * SS; s = M / 256
    im = Image.new("RGB", (M, M), SKIN); d = ImageDraw.Draw(im)
    def E(x0, y0, x1, y1, **kw): d.ellipse(tuple(v * s for v in (x0, y0, x1, y1)), **kw)
    def L(pts, w, col): d.line([(x * s, y * s) for x, y in pts], fill=col, width=int(w * s), joint="curve")
    def PG(pts, col): d.polygon([(x * s, y * s) for x, y in pts], fill=col)
    lx = {"l": -6, "r": 6, "c": 0, "u": 0}[look]; ly = -5 if look == "u" else 0
    ey = EY * 256
    for i, cx in enumerate((EX[0] * 256, EX[1] * 256)):
        if eyes == "closed":
            L([(cx - 18, ey + 4), (cx, ey - 10), (cx + 18, ey + 4)], 7, HAIR)
        elif eyes == "squeeze":
            sgn = 1 if i == 0 else -1
            L([(cx - 15 * sgn, ey - 12), (cx + 12 * sgn, ey), (cx - 15 * sgn, ey + 12)], 7, HAIR)
        else:
            rw, rh = (21, 24) if eyes == "wide" else (19, 19)
            E(cx - rw, ey - rh, cx + rw, ey + rh, fill=(252, 252, 250), outline=(70, 46, 40), width=int(3 * s))
            pr = 8 if eyes == "wide" else 12
            E(cx + lx - pr, ey + ly - pr, cx + lx + pr, ey + ly + pr, fill=(92, 58, 36))
            E(cx + lx - pr * 0.55, ey + ly - pr * 0.55, cx + lx + pr * 0.55, ey + ly + pr * 0.55, fill=(30, 20, 18))
            E(cx + lx + 2, ey + ly - pr + 2, cx + lx + 7, ey + ly - pr + 7, fill=(255, 255, 255))
            if eyes == "half":
                PG([(cx - rw - 2, ey - rh - 2), (cx + rw + 2, ey - rh - 2), (cx + rw + 2, ey - 1), (cx - rw - 2, ey - 1)], SKIN)
                L([(cx - rw, ey - 1), (cx + rw, ey - 1)], 4, (70, 46, 40))
        dy = bl if i == 0 else br; sg = 1 if i == 0 else -1
        y0 = ey - 36 + dy
        PG([(cx - 24, y0 + sg * tilt + 2), (cx + 24, y0 - sg * tilt - 2), (cx + 24, y0 - sg * tilt + 9), (cx - 24, y0 + sg * tilt + 11)], HAIR)
    if blush:
        for cx in (62, 194): E(cx - 18, 168, cx + 18, 182, fill=(214, 112, 104))
    my = 196; m = (120, 36, 42)
    if mouth == "smile":
        d.chord(tuple(v * s for v in (98, my - 20, 158, my + 22)), 0, 180, fill=m); PG([(104, my + 1), (152, my + 1), (150, my + 7), (106, my + 7)], (252, 252, 252))
    elif mouth == "grin":
        d.chord(tuple(v * s for v in (82, my - 26, 174, my + 30)), 0, 180, fill=m); PG([(88, my + 1), (168, my + 1), (166, my + 9), (90, my + 9)], (252, 252, 252))
        E(110, my + 12, 146, my + 28, fill=(222, 96, 104))
    elif mouth == "o":
        E(110, my - 16, 146, my + 30, fill=(96, 22, 30)); E(118, my + 10, 138, my + 26, fill=(206, 84, 96))
    elif mouth == "grit":
        d.rounded_rectangle(tuple(v * s for v in (86, my - 12, 170, my + 16)), int(8 * s), fill=(252, 252, 252), outline=m, width=int(4 * s))
        L([(88, my + 2), (168, my + 2)], 2, (170, 160, 160))
        for x in range(100, 170, 14): L([(x, my - 10), (x, my + 14)], 2, (180, 170, 170))
    elif mouth == "frown":
        d.arc(tuple(v * s for v in (100, my, 156, my + 34)), 200, 340, fill=m, width=int(6 * s))
    elif mouth == "smirk":
        L([(108, my + 6), (144, my + 6), (162, my - 8)], 6, m)
    elif mouth == "squiggle":
        L([(100, my + 4), (114, my - 4), (128, my + 4), (142, my - 4), (156, my + 4)], 6, m)
    else:
        L([(104, my + 2), (152, my + 2)], 6, m)
    if sweat:
        PG([(236, 40), (224, 76), (248, 76)], (110, 196, 255)); E(222, 64, 250, 92, fill=(110, 196, 255))
    return im.resize((N, N), Image.LANCZOS)

@lru_cache(None)
def face(expr="smile", look="c", sweat=False, blush=False): return tex(_face(expr, look, sweat, blush))

# ---------------------------------------------------------------- parts
HA, HB_, HC, HYC = 0.205, 0.228, 0.19, 1.69     # head half-width, half-height, half-depth, centre height
FS = 0.86                                        # face texture covers +-FS of the head's width/height

def _se(a, b, c, e1=0.62, e2=0.58, seg=18, rings=12, col=SKIN):
    """Superellipsoid mesh centred at the origin (rounded box). Returns P plus per-triangle centroid normals' z."""
    def sp(v, e): return np.sign(v) * np.abs(v) ** e
    th = np.linspace(-math.pi / 2, math.pi / 2, rings + 1); ph = np.linspace(0, 2 * math.pi, seg + 1)
    V = np.zeros((rings + 1, seg + 1, 3), np.float32)
    for i, t in enumerate(th):
        for j, f in enumerate(ph):
            ct = sp(math.cos(t), e1)
            V[i, j] = (a * ct * sp(math.cos(f), e2), b * sp(math.sin(t), e1), c * ct * sp(math.sin(f), e2))
    tris = []
    for i in range(rings):
        for j in range(seg):
            p00, p01, p10, p11 = V[i, j], V[i, j + 1], V[i + 1, j], V[i + 1, j + 1]
            if i > 0: tris.append((p00, p01, p11))
            if i < rings - 1: tris.append((p00, p11, p10))
    return P(np.float32(tris), col)

def _sz(x, y):
    """Front surface depth of the head at (x, y-HYC)."""
    q = 1 - (abs(x) / HA) ** (2 / 0.58) ; r = max(0.0, 1 - (abs(y) / HB_) ** (2 / 0.62))
    return HC * max(0.0, r) ** (0.62 / 2) * max(0.0, q) ** (0.58 / 2) if q > 0 else 0.0

def _head_shell(fid):
    h = _se(HA, HB_, HC)
    t = h.t; cz = t[:, :, 2].mean(1)
    front = cz > 0.05
    u = 0.5 + t[..., 0] / (2 * FS * HA); v = 0.5 - t[..., 1] / (2 * FS * HB_)
    h.k[front] = fid; h.c[front] = 1.0
    h.uv[front] = np.stack([np.clip(u, 0.001, 0.999), np.clip(v, 0.001, 0.999)], -1)[front]
    return h.mv(0, HYC, 0)

def _spike(bx, bz, by, tip, w):
    a, b_, c, d = (bx - w, by, bz - w), (bx + w, by, bz - w), (bx + w, by, bz + w), (bx - w, by, bz + w)
    return P([a, b_, tip, b_, c, tip, c, d, tip, d, a, tip], HAIR)

def _tuft(root_l, root_r, tip, depth=0.045):
    """A flat hair lock: two root points on the scalp and a tip, thickened backwards by depth."""
    (ax, ay, az), (bx, by, bz), (tx, ty, tz) = root_l, root_r, tip
    a2, b2 = (ax, ay, az - depth), (bx, by, bz - depth)
    return P([root_l, root_r, tip, a2, b2, tip, root_l, a2, tip, root_r, b2, tip], HAIR)

def _hair():
    """Dark hair with a middle part: a full cap whose front edge forms a curtain fringe (high at the centre part,
    sweeping down to each temple), a scalp line along the part, and a few locks along the fringe edge for texture."""
    sh = _se(HA * 1.09, HB_ * 1.08, HC * 1.11, seg=30, rings=18, col=HAIR).mv(0, HYC + 0.018, -0.006)
    c = sh.t.mean(1); top = HYC + HB_
    ax = np.abs(c[:, 0]) / HA
    front = top - 0.07 - 0.13 * np.clip(ax, 0, 1) ** 1.3          # curtain: high at the part, low at the temples
    tz = np.clip((-c[:, 2] / HC + 0.25) / 1.25, 0, 1)
    yth = front + ((HYC - HB_ + 0.12) - front) * tz
    side = ax > 0.86
    yth = np.where(side, np.minimum(yth, HYC + 0.02), yth)
    keep = c[:, 1] > yth
    q = P.__new__(P); q.t, q.c, q.k, q.uv, q.e = sh.t[keep], sh.c[keep], sh.k[keep], sh.uv[keep], sh.e[keep]
    out = [q]
    ytop = top + 0.018 + HB_ * 0.08
    # (the middle part reads from the curtain's centre V; no separate scalp strip))
    for sg in (-1, 1):                                              # locks along the curtain edge
        for x in (0.03, 0.08, 0.13, 0.175):
            yr = top - 0.06 - 0.13 * (x / HA) ** 1.3
            zr = _sz(x, yr - HYC) + 0.022
            tip = (sg * (x + 0.035), yr - 0.055, _sz(x + 0.035, yr - 0.055 - HYC) + 0.02)
            out.append(_tuft((sg * (x - 0.03), yr + 0.03, zr), (sg * (x + 0.03), yr + 0.02, zr), tip, 0.04))
    for bx, bz, tx, ty, tz_ in ((-0.05, -0.13, -0.08, ytop + 0.02, -0.2), (0.06, -0.14, 0.1, ytop + 0.015, -0.2)):
        out.append(_spike(bx, bz, ytop - 0.04, (tx, ty, tz_), 0.05))
    return out

def _glasses():
    """Silver square frames on the curved face, centred on the eyes drawn in the texture."""
    t = 0.011; g = []; hw, hh = 0.062, 0.044
    ey = -(EY - 0.5) * 2 * FS * HB_
    for u in EX:
        cx = (u - 0.5) * 2 * FS * HA
        z = max(_sz(cx + dx, ey + dy) for dx in (-hw, 0, hw) for dy in (-hh, 0, hh)) + 0.012
        g += [cb(cx, HYC + ey + hh, z, 2 * hw + t, t, t, GLASS, b=0.003), cb(cx, HYC + ey - hh, z, 2 * hw + t, t, t, GLASS, b=0.003),
              cb(cx - hw, HYC + ey, z, t, 2 * hh, t, GLASS, b=0.003), cb(cx + hw, HYC + ey, z, t, 2 * hh, t, GLASS, b=0.003)]
    xb = (EX[1] - 0.5) * 2 * FS * HA - hw
    g.append(cb(0, HYC + ey + 0.015, _sz(0, ey) + 0.016, 2 * xb, t * 0.9, t, GLASS, b=0.003))
    for sg in (-1, 1):
        x = sg * ((EX[1] - 0.5) * 2 * FS * HA + hw)
        z0 = _sz(x, ey) + 0.012
        g.append(cb(x + sg * 0.01, HYC + ey + 0.015, (z0 - 0.08) / 2, t, t, z0 + 0.08, GLASS, b=0.003).rot("y", sg * 8, (x, 0, z0)))
    return g

def _head(expr, look, sweat, blush):
    fid = face(expr, look, sweat, blush)
    hd = _head_shell(fid)
    ny = HYC - 0.06; nz = _sz(0, -0.06)
    nose = P([(-0.022, ny - 0.02, nz - 0.004), (0.022, ny - 0.02, nz - 0.004), (0.0, ny - 0.005, nz + 0.03),
              (0.0, ny + 0.035, nz - 0.004), (-0.022, ny - 0.02, nz - 0.004), (0.0, ny - 0.005, nz + 0.03),
              (0.0, ny + 0.035, nz - 0.004), (0.022, ny - 0.02, nz - 0.004), (0.0, ny - 0.005, nz + 0.03)], SKIN_D)
    ears = [cb(sg * (HA - 0.004), HYC - 0.01, -0.02, 0.05, 0.1, 0.07, SKIN_D, b=0.015) for sg in (-1, 1)]
    neck = cb(0, 1.42, 0, 0.15, 0.12, 0.13, SKIN_D, b=0.02)
    return cat([hd, nose, *ears, neck, *_hair(), *_glasses()])

def _hand(wave=False, fist=False):
    palm = cb(0, -0.06, 0, 0.11, 0.12, 0.07, SKIN, b=0.02)
    if wave:
        f = [cb(-0.04 + 0.027 * i, -0.15 - 0.01 * (i in (1, 2)), 0, 0.024, 0.09 + 0.015 * (i in (1, 2)), 0.05, SKIN, b=0.008) for i in range(4)]
        th = cb(0.07, -0.05, 0.0, 0.035, 0.07, 0.045, SKIN, b=0.01).rot("z", 35, (0.06, -0.02, 0))
    else:
        f = [cb(0, -0.14, 0.008, 0.11, 0.06, 0.07, SKIN, b=0.02)]
        th = cb(0.0, -0.08, 0.05, 0.04, 0.06, 0.04, SKIN, b=0.012)
    return cat([palm, *f, th])

def _arm(side, fw, out, bend, held=None, wave=False):
    up = cat([cb(0, -0.16, 0, 0.14, 0.36, 0.14, BLAZER, b=0.04)])
    fore = [cb(0, -0.47, 0, 0.125, 0.32, 0.125, BLAZER, b=0.035), cb(0, -0.64, 0, 0.11, 0.05, 0.11, SHIRT, b=0.015),
            _hand(wave).mv(0, -0.66, 0)]
    fore = cat(fore)
    if held is not None: fore = cat([fore, held.copy().mv(0, -0.76, 0.06)])
    fore.rot("x", -bend, (0, -0.32, 0))
    return cat([up, fore]).rot("x", -fw).rot("z", side * out).mv(side * 0.3, 1.33, 0)

def _shoe(x):
    return cat([bbox(x - 0.085, 0.025, -0.11, x + 0.085, 0.12, 0.17, SHOE, b=0.035), bbox(x - 0.09, 0.0, -0.115, x + 0.09, 0.035, 0.18, SOLE, b=0.012),
                cb(x, 0.1, 0.06, 0.09, 0.02, 0.1, (210, 210, 220), b=0.005)])

def hero(expr="smile", look="c", la=(0, 8, 10), ra=(0, 8, 10), head=(0, 0, 0), sit=False, step=0.0, lean=0.0, held=None,
         wave=None, sweat=False, blush=False, bob=0.0):
    """la/ra = (raise forward deg, out to the side deg, elbow bend deg). head = (yaw, pitch, roll). wave: 'l'/'r' open palm."""
    parts = []
    if sit:
        for sx in (-0.1, 0.1):
            parts += [bbox(sx - 0.085, 0.42, -0.02, sx + 0.085, 0.6, 0.5, PANTS, b=0.04),
                      bbox(sx - 0.08, 0.08, 0.38, sx + 0.08, 0.52, 0.55, PANTS, b=0.035),
                      _shoe(sx).mv(0, 0, 0.42)]
        dy = -0.3
    else:
        for sx, ph in ((-0.1, step), (0.1, -step)):
            parts += [cat([bbox(sx - 0.085, 0.1, -0.085, sx + 0.085, 0.88, 0.085, PANTS, b=0.035), _shoe(sx)]).rot("x", ph, (0, 0.86, 0))]
        dy = 0.0
    up = [bbox(-0.235, 0.82, -0.13, 0.235, 1.38, 0.13, BLAZER, b=0.05),                          # blazer body
          bbox(-0.28, 1.22, -0.12, 0.28, 1.4, 0.12, BLAZER, b=0.07)]                              # shoulders
    z = 0.131
    up.append(P([(-0.11, 1.38, z), (0.11, 1.38, z), (0, 1.07, z)], SHIRT))                        # open white shirt V
    up.append(P([(-0.11, 1.38, z + 0.002), (-0.02, 1.07, z + 0.002), (-0.075, 1.2, z + 0.02)], BLAZER_D))   # lapels
    up.append(P([(0.11, 1.38, z + 0.002), (0.075, 1.2, z + 0.02), (0.02, 1.07, z + 0.002)], BLAZER_D))
    up.append(P([(-0.065, 1.39, z + 0.01), (0.0, 1.32, z + 0.012), (-0.1, 1.31, z + 0.01)], SHIRT))             # collar points
    up.append(P([(0.065, 1.39, z + 0.01), (0.1, 1.31, z + 0.01), (0.0, 1.32, z + 0.012)], SHIRT))
    up += [cb(0.0, y, z + 0.004, 0.028, 0.028, 0.012, (220, 222, 232), b=0.004) for y in (1.0, 0.9)]          # buttons
    up.append(cb(0.14, 1.2, z + 0.004, 0.09, 0.012, 0.01, BLAZER_D, b=0.002))                                  # pocket
    h = _head(expr, look, sweat, blush).rot("z", head[2], (0, 1.45, 0)).rot("x", head[1], (0, 1.45, 0)).rot("y", head[0], (0, 1.45, 0))
    up.append(h)
    for side, a in ((-1, la), (1, ra)):
        up.append(_arm(side, *a, held=held if side == 1 else None, wave=(wave == ("l" if side == -1 else "r"))))
    upper = cat(up).rot("x", lean, (0, 0.85, 0)).mv(0, dy + bob, 0)
    return clean(cat(parts + [upper]))
